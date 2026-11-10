#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Surveybox —— 零依赖本地问卷与统计工具。

    python server.py                          # http://127.0.0.1:8765
    python server.py --host 0.0.0.0           # 手机同局域网可访问
    python server.py --db data/batch2.jsonl   # 换一批数据
    python server.py --empty                  # 空库开始

页面：/  问卷    /dashboard  看板    /admin?key=xxx  后台（无 key 返回 404）
"""
import argparse
import csv
import datetime
import io
import json
import math
import os
import random
import socket
import statistics
import urllib.parse
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
DATA = os.path.join(HERE, "data")

SURVEY = os.path.join(DATA, "survey.json")
DB = os.path.join(DATA, "responses.jsonl")
SAMPLE = os.path.join(DATA, "sample_responses.jsonl")
ADMIN_KEY = "tally2026"

VER = "Surveybox/2.0"


# ---------------------------------------------------------------- 基础读写
def load_survey():
    if not os.path.exists(SURVEY):
        return {"title": "未命名问卷", "intro": "", "questions": []}
    with open(SURVEY, encoding="utf-8-sig") as f:
        return json.load(f)


def save_survey(obj):
    with open(SURVEY, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_db():
    if not os.path.exists(DB):
        return []
    out = []
    with open(DB, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def append_rec(rec):
    rows = load_db()
    rec["id"] = len(rows) + 1
    rec["ts"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DB, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec["id"]


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------------------------------------------------------------- 统计引擎
def pct(n, total):
    return round(n / total * 100, 1) if total else 0.0


def freq(vals):
    c = Counter(vals)
    total = len(vals)
    return [{"k": k, "n": n, "p": pct(n, total)} for k, n in c.most_common()]


def compute():
    survey = load_survey()
    rows = load_db()
    n = len(rows)
    out = {"n": n, "updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "title": survey.get("title", ""), "questions": []}
    if not n:
        return out

    for q in survey.get("questions", []):
        qid, qtype = q["id"], q.get("type", "single")
        raw = [r.get(qid) for r in rows]
        vals = [v for v in raw if v not in (None, "", [], 0)]
        item = {"id": qid, "type": qtype, "title": q.get("title", qid),
                "answered": len(vals), "skipped": n - len(vals)}
        if qtype == "multi":
            c = Counter()
            for v in vals:
                for x in (v if isinstance(v, list) else [v]):
                    c[x] += 1
            item["rows"] = [{"k": k, "n": v, "p": pct(v, len(vals))}
                            for k, v in c.most_common()]
        elif qtype == "scale":
            nums = [float(v) for v in vals if isinstance(v, (int, float))]
            if nums:
                item["mean"] = round(statistics.fmean(nums), 2)
                item["sd"] = round(statistics.stdev(nums), 2) if len(nums) > 1 else 0.0
                lo = int(min(nums)) if nums else 1
                item["scale_min"] = 1
                item["scale_max"] = max(int(max(nums)), 5)
                item["dist"] = [sum(1 for x in nums if int(x) == i)
                                for i in range(1, int(max(nums)) + 1)]
            item["rows"] = freq([str(int(v)) for v in nums])
        elif qtype == "text":
            item["samples"] = [str(v) for v in vals if str(v).strip()][:5]
            item["rows"] = []
        else:
            item["rows"] = freq([str(v) for v in vals])
        out["questions"].append(item)
    return out


def to_csv():
    survey = load_survey()
    qs = [q["id"] for q in survey.get("questions", [])]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "ts"] + [q["title"] for q in survey.get("questions", [])])
    for r in load_db():
        w.writerow([r.get("id", ""), r.get("ts", "")] +
                   [";".join(map(str, r[q])) if isinstance(r.get(q), list) else r.get(q, "")
                    for q in qs])
    return "\ufeff" + buf.getvalue()


def to_md():
    st = compute()
    L = [f"### {st['title']}　统计结果（N={st['n']}）", ""]
    for item in st["questions"]:
        L.append(f"**{item['title']}**")
        if item["type"] == "scale" and "mean" in item:
            L.append(f"- 均值 {item['mean']}，标准差 {item['sd']}，有效 {item['answered']}")
        elif item["type"] == "text":
            L.append("- " + ("；".join(item["samples"][:3]) or "（无文本作答）"))
        else:
            L.append("")
            L.append("| 选项 | 人数 | 占比 |")
            L.append("|---|---|---|")
            for r in item["rows"]:
                L.append(f"| {r['k']} | {r['n']} | {r['p']}% |")
        L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------- 自动灌数
def seed_one(survey, rng):
    rec = {}
    for q in survey.get("questions", []):
        t, qid = q.get("type", "single"), q["id"]
        if t == "multi":
            opts = q.get("options", [])
            k = min(len(opts), q.get("max", 3) or 3, rng.choice([1, 2, 3]))
            rec[qid] = rng.sample(opts, k) if opts else []
        elif t == "scale":
            top = int(q.get("scale_max", 5))
            rec[qid] = max(1, min(top, round(rng.gauss(3.7, 0.7))))
        elif t == "text":
            rec[qid] = ""
        else:
            opts = q.get("options", [])
            rec[qid] = rng.choice(opts) if opts else ""
    return rec


# ---------------------------------------------------------------- HTTP
def html(name):
    p = os.path.join(WEB, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return f.read()


class Handler(BaseHTTPRequestHandler):
    server_version = VER

    def log_message(self, *a):
        pass

    # -- 工具 --
    def _send(self, body, ctype="application/json; charset=utf-8", code=200, extra=None):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200, extra=None):
        self._send(json.dumps(obj, ensure_ascii=False), code=code, extra=extra)

    def _is_admin(self):
        key = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get("key", [""])[0]
        if not key:
            cookie = self.headers.get("Cookie", "")
            for part in cookie.split(";"):
                k, _, v = part.strip().partition("=")
                if k == "tk_admin":
                    key = v
        return key == ADMIN_KEY, key

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    # -- GET --
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(html("index.html") or "missing", "text/html; charset=utf-8")
        if path in ("/dashboard", "/dashboard.html"):
            return self._send(html("dashboard.html") or "missing", "text/html; charset=utf-8")
        if path in ("/admin", "/admin.html"):
            ok, key = self._is_admin()
            admin_ok = ok or self.headers.get("X-Admin-Key", "") == ADMIN_KEY
            if not admin_ok:
                return self._send("Not Found", "text/plain; charset=utf-8", 404)
            extra = {"Set-Cookie": f"tk_admin={ADMIN_KEY}; Path=/; Max-Age=86400"}
            return self._send(html("admin.html") or "missing", "text/html; charset=utf-8", extra=extra)
        if path == "/api/survey":
            return self._json(load_survey())
        if path == "/api/stats":
            return self._json(compute())
        if path == "/api/responses":
            ok, _ = self._is_admin()
            admin_ok = ok or self.headers.get("X-Admin-Key", "") == ADMIN_KEY
            if not admin_ok:
                return self._json({"error": "forbidden"}, 403)
            return self._json(load_db())
        if path == "/api/admin/link":
            ok, _ = self._is_admin()
            admin_ok = ok or self.headers.get("X-Admin-Key", "") == ADMIN_KEY
            if not admin_ok:
                return self._json({"error": "forbidden"}, 403)
            host = self.headers.get("Host", "")
            port = host.split(":")[-1] if ":" in host else "80"
            return self._json({
                "lan": f"http://{lan_ip()}:{port}/",
                "admin": f"/admin?key={ADMIN_KEY}",
                "key": ADMIN_KEY,
                "db": DB, "survey": SURVEY,
                "n": len(load_db()),
            })
        if path == "/export.csv":
            return self._send(to_csv(), "text/csv; charset=utf-8",
                              extra={"Content-Disposition": "attachment; filename=survey.csv"})
        if path == "/export.md":
            return self._send(to_md(), "text/markdown; charset=utf-8")
        return self._send("Not Found", "text/plain; charset=utf-8", 404)

    # -- POST --
    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        ok, _ = self._is_admin()
        surrogate = self.headers.get("X-Admin-Key", "") == ADMIN_KEY
        admin_ok = ok or surrogate

        if path == "/api/submit":
            rec = self._body()
            survey = load_survey()
            if not admin_ok:                   # 后门：带后台钥匙可跳必答校验
                missing = [q["title"] for q in survey.get("questions", [])
                           if q.get("required") and not rec.get(q["id"])]
                if missing:
                    return self._json({"ok": False, "missing": missing}, 400)
            rid = append_rec(rec)
            return self._json({"ok": True, "id": rid})

        if path == "/api/survey":
            if not admin_ok:
                return self._json({"error": "forbidden"}, 403)
            body = self._body()
            if not isinstance(body.get("questions"), list) or not body["questions"]:
                return self._json({"ok": False, "error": "questions 不能为空"}, 400)
            ids = [q.get("id") for q in body["questions"]]
            if any(not i for i in ids) or len(set(ids)) != len(ids):
                return self._json({"ok": False, "error": "题目 id 缺失或重复"}, 400)
            save_survey(body)
            return self._json({"ok": True, "count": len(body["questions"])})

        if path == "/api/admin/seed":
            if not admin_ok:
                return self._json({"error": "forbidden"}, 403)
            n = int(urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                    .get("n", ["20"])[0])
            rng = random.Random(42)
            for _ in range(n):
                append_rec(seed_one(load_survey(), rng))
            return self._json({"ok": True, "n": len(load_db())})

        if path == "/api/admin/reset":
            if not admin_ok:
                return self._json({"error": "forbidden"}, 403)
            open(DB, "w", encoding="utf-8").close()
            return self._json({"ok": True, "n": 0})

        if path == "/api/admin/sample":
            if not admin_ok:
                return self._json({"error": "forbidden"}, 403)
            if os.path.exists(SAMPLE):
                with open(SAMPLE, encoding="utf-8") as s, open(DB, "w", encoding="utf-8") as d:
                    d.write(s.read())
            return self._json({"ok": True, "n": len(load_db())})

        return self._send("Not Found", "text/plain; charset=utf-8", 404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1", help="手机访问改 0.0.0.0")
    ap.add_argument("--db", default=None)
    ap.add_argument("--survey", default=None)
    ap.add_argument("--admin-key", default=None)
    ap.add_argument("--empty", action="store_true")
    args = ap.parse_args()

    global DB, SURVEY, ADMIN_KEY
    if args.db:
        DB = os.path.abspath(args.db)
        os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    if args.survey:
        SURVEY = os.path.abspath(args.survey)
    if args.admin_key:
        ADMIN_KEY = args.admin_key

    os.makedirs(DATA, exist_ok=True)
    if not os.path.exists(SURVEY):
        save_survey({"title": "未命名问卷", "intro": "", "questions": []})
    if not os.path.exists(DB):
        if not args.empty and os.path.exists(SAMPLE):
            with open(SAMPLE, encoding="utf-8") as s, open(DB, "w", encoding="utf-8") as d:
                d.write(s.read())
        else:
            open(DB, "w", encoding="utf-8").close()

    s = load_survey()
    print(f"· {VER}")
    print(f"· 问卷《{s.get('title')}》  {len(s.get('questions', []))} 题")
    print(f"· 数据 {DB}  N={len(load_db())}")
    print(f"· 问卷   http://{args.host}:{args.port}/")
    print(f"· 看板   http://{args.host}:{args.port}/dashboard")
    print(f"· 后台   http://{args.host}:{args.port}/admin?key={ADMIN_KEY}   （无 key 返回 404）")
    if args.host == "0.0.0.0":
        print(f"· 手机   http://{lan_ip()}:{args.port}/")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()

