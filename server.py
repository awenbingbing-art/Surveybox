#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""北京大气治理公众感知调查 —— 零依赖本地服务与统计引擎。

用法:
    python server.py                # 启动，默认 http://127.0.0.1:8765
    python server.py --empty        # 不载入示例数据，从空库开始
    python server.py --port 9000

路由:
    /               问卷填写页
    /dashboard      统计看板
    /api/stats      统计结果 JSON
    /api/responses  原始数据 JSON
    /export.csv     导出 CSV
    /export.md      导出 Markdown 表（可直接贴进报告）
"""
import argparse
import csv
import io
import json
import math
import os
import statistics
import datetime
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DB = os.path.join(DATA, "responses.jsonl")
SAMPLE = os.path.join(DATA, "sample_responses.jsonl")
WEB = os.path.join(HERE, "web")

LIKERT = {"q6": "Q6 改善感知", "q7": "北京蓝频次", "q8": "当前满意度",
          "q13": "支持限行", "q14": "支持停工", "q15": "支持煤改电"}
DEMO = {"gender": "性别", "grade": "年级", "major": "专业大类",
        "resid": "在京居住时长", "familia": "家人患病"}
MULTI = {"q10": "污染源认知", "q11": "信息渠道"}
SENIOR = {"10年以上", "土生土长"}
WTP_MID = {"0元": 0, "1—20元": 10, "21—50元": 35, "51—100元": 75, "100元以上": 150}


def load():
    if not os.path.exists(DB):
        return []
    out = []
    with open(DB, encoding="utf-8-sig") as f:  # 容忍 BOM，避免外部编辑后解析失败
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def pct(n, total):
    return round(n / total * 100, 1) if total else 0.0


def freq_block(vals):
    c = Counter(vals)
    total = len(vals)
    return [{"k": k, "n": n, "p": pct(n, total)} for k, n in c.most_common()]


def mean_sd(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals:
        return None
    return {"mean": round(statistics.fmean(vals), 2),
            "sd": round(statistics.stdev(vals), 2) if len(vals) > 1 else 0.0,
            "n": len(vals),
            "dist": [sum(1 for v in vals if v == i) for i in range(1, 6)]}


def welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    na, nb = len(a), len(b)
    se = math.sqrt(va / na + vb / nb)
    if se == 0:
        return None
    t = (ma - mb) / se
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    return {"t": round(t, 2), "df": round(df, 1), "mean_a": round(ma, 2), "sd_a": round(math.sqrt(va), 2),
            "n_a": na, "mean_b": round(mb, 2), "sd_b": round(math.sqrt(vb), 2), "n_b": nb,
            "sig": abs(t) > 1.99}


def chi2_2x2(tab):
    total = sum(sum(r) for r in tab)
    if total == 0:
        return None
    chi = 0.0
    for i in range(2):
        for j in range(2):
            e = sum(tab[i]) * sum(tab[r][j] for r in range(2)) / total
            if e:
                chi += (tab[i][j] - e) ** 2 / e
    return {"chi2": round(chi, 2), "df": 1, "crit": 3.84, "sig": chi > 3.84}


def corr(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if isinstance(a, (int, float)) and isinstance(b, (int, float))]
    if len(pairs) < 3:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    num = sum((a - mx) * (b - my) for a, b in pairs)
    den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
    return round(num / den, 2) if den else None


def compute(rows):
    n = len(rows)
    if n == 0:
        return {"n": 0}
    st = {"n": n, "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    st["demo"] = {DEMO[k]: freq_block([r.get(k, "") for r in rows]) for k in DEMO}
    st["likert"] = {}
    for k, label in LIKERT.items():
        m = mean_sd([r.get(k) for r in rows])
        if m:
            st["likert"][label] = m

    q9 = [r.get("q9", "") for r in rows]
    st["q9"] = {"buckets": freq_block(q9),
                "correct_pct": pct(sum(1 for v in q9 if v == "20—35"), n)}

    for k, label in MULTI.items():
        c = Counter()
        for r in rows:
            for x in r.get(k) or []:
                c[x] += 1
        st[label] = [{"k": kk, "n": v, "p": pct(v, n)} for kk, v in c.most_common()]

    st["q12"] = freq_block([r.get("q12", "") for r in rows])
    st["q17"] = freq_block([r.get("q17", "") for r in rows])

    q16 = [r.get("q16", "") for r in rows]
    mids = [WTP_MID.get(v, 0) for v in q16]
    st["q16"] = {"buckets": freq_block(q16),
                 "mean": round(statistics.fmean(mids), 1) if mids else 0}

    a = [r["q6"] for r in rows if r.get("q6") is not None and r.get("resid") in SENIOR]
    b = [r["q6"] for r in rows if r.get("q6") is not None and r.get("resid") not in SENIOR]
    st["tests"] = {"t_q6": welch(a, b)}

    correct = [r.get("q9") == "20—35" for r in rows]
    unknow = [r.get("q12") == "不知道" for r in rows]
    tab = [[sum(1 for c, u in zip(correct, unknow) if c and u), sum(1 for c, u in zip(correct, unknow) if c and not u)],
           [sum(1 for c, u in zip(correct, unknow) if not c and u), sum(1 for c, u in zip(correct, unknow) if not c and not u)]]
    st["tests"]["chi2_q9_q12"] = chi2_2x2(tab)
    st["tests"]["r_q6_q8"] = corr([r.get("q6") for r in rows], [r.get("q8") for r in rows])
    return st


def to_csv(rows):
    buf = io.StringIO()
    fields = ["id", "ts", "gender", "grade", "major", "resid", "familia", "q6", "q7", "q8",
              "q9", "q10", "q11", "q12", "q13", "q14", "q15", "q16", "q17", "q18"]
    w = csv.writer(buf)
    w.writerow(fields)
    for r in rows:
        w.writerow([(";".join(r[f]) if isinstance(r.get(f), list) else r.get(f, "")) for f in fields])
    return "\ufeff" + buf.getvalue()


def to_md(rows):
    st = compute(rows)
    L = [f"### 附件2 问卷统计结果（N={st['n']}）", ""]
    L.append("| 指标 | 均值 | 标准差 |")
    L.append("|---|---|---|")
    for k, v in st.get("likert", {}).items():
        L.append(f"| {k} | {v['mean']} | {v['sd']} |")
    L += ["", "| 浓度估计 | 人数 | 占比 |", "|---|---|---|"]
    for b in st.get("q9", {}).get("buckets", []):
        L.append(f"| {b['k']} | {b['n']} | {b['p']}% |")
    return "\n".join(L)


class Handler(BaseHTTPRequestHandler):
    server_version = "Surveybox/1.0"

    def log_message(self, fmt, *args):
        pass

    def _send(self, body, ctype="application/json; charset=utf-8", code=200, extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._serve_file("index.html")
        if path in ("/dashboard", "/dashboard.html"):
            return self._serve_file("dashboard.html")
        if path == "/api/stats":
            return self._send(json.dumps(compute(load()), ensure_ascii=False))
        if path == "/api/responses":
            return self._send(json.dumps(load(), ensure_ascii=False))
        if path == "/export.csv":
            return self._send(to_csv(load()), "text/csv; charset=utf-8",
                              extra={"Content-Disposition": "attachment; filename=survey.csv"})
        if path == "/export.md":
            return self._send(to_md(load()), "text/markdown; charset=utf-8")
        return self._send(json.dumps({"error": "not found"}), code=404)

    def do_POST(self):
        if urlparse(self.path).path != "/api/submit":
            return self._send(json.dumps({"error": "not found"}), code=404)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            return self._send(json.dumps({"ok": False, "error": "invalid json"}), code=400)
        rows = load()
        rec["id"] = len(rows) + 1
        rec["ts"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rec.setdefault("q18", "")
        with open(DB, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return self._send(json.dumps({"ok": True, "id": rec["id"]}, ensure_ascii=False))

    def _serve_file(self, name):
        p = os.path.join(WEB, name)
        if not os.path.exists(p):
            return self._send("missing " + name, "text/plain; charset=utf-8", 404)
        with open(p, encoding="utf-8") as f:
            return self._send(f.read(), "text/html; charset=utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--empty", action="store_true", help="不载入示例数据")
    ap.add_argument("--db", default=None,
                    help="指定数据文件（默认 data/responses.jsonl）；换一批数据就换一个文件")
    ap.add_argument("--host", default="127.0.0.1", help="绑定地址，手机访问改为 0.0.0.0")
    args = ap.parse_args()

    global DB
    if args.db:
        DB = os.path.abspath(args.db)
        parent = os.path.dirname(DB)
        if parent:
            os.makedirs(parent, exist_ok=True)

    os.makedirs(DATA, exist_ok=True)
    if not os.path.exists(DB):
        if not args.empty and os.path.exists(SAMPLE):
            with open(SAMPLE, encoding="utf-8") as s, open(DB, "w", encoding="utf-8") as d:
                d.write(s.read())
            print("· 已载入示例数据", SAMPLE)
        else:
            open(DB, "w", encoding="utf-8").close()
            print("· 空数据库已创建")

    n = len(load())
    print(f"· 数据文件 {DB}")
    print(f"· 当前样本 N={n}")
    print(f"· 问卷页   http://{args.host}:{args.port}/")
    print(f"· 统计看板 http://{args.host}:{args.port}/dashboard")
    print("· Ctrl+C 停止")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
