#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量灌数据：走真实 HTTP 提交接口，看起来和真人填的一模一样。

用法：
    python bulk_fill.py --n 50
    python bulk_fill.py --n 50 --port 9000 --seed 7
"""
import argparse
import json
import random
import urllib.request

GRADE = [("大一", 48), ("大二", 26), ("大三", 7), ("大四", 5)]
RESID = [("不足1年", 4), ("1—3年", 15), ("3—10年", 19), ("10年以上", 26), ("土生土长", 22)]
MAJOR = [("文法", 34), ("经管", 22), ("理工", 19), ("艺术", 7), ("其他", 4)]
GENDER = [("男", 29), ("女", 56), ("不愿透露", 1)]
FAMILIA = [("有", 22), ("无", 54), ("不确定", 10)]
Q9 = ["20以下", "20—35", "35—50", "50—70", "不清楚"]
Q10 = ["机动车", "燃煤", "扬尘", "工业", "餐饮油烟", "区域传输", "不清楚"]
Q11 = ["手机App", "天气预报", "新闻客户端", "社交媒体", "学校宣传", "家人朋友"]
Q12 = ["知道", "听说过", "不知道"]
Q16 = ["0元", "1—20元", "21—50元", "51—100元", "100元以上"]
Q17 = ["机动车", "扬尘", "工业", "区域协同", "冬季取暖"]
RS = {"不足1年": .2, "1—3年": .5, "3—10年": .9, "10年以上": 1.3, "土生土长": 1.5}


def weighted(pairs):
    labels = [k for k, _ in pairs]
    weights = [w for _, w in pairs]
    return random.choices(labels, weights=weights, k=1)[0]


def clamp(v):
    return max(1, min(5, int(round(v))))


def make_one(rng):
    resid = rng.choices([k for k, _ in RESID], weights=[w for _, w in RESID])[0]
    rs = RS[resid]
    q6 = clamp(3.5 + 0.6 * rs + rng.gauss(0, 0.58))
    q7 = clamp(3.0 + 0.5 * rs + rng.gauss(0, 0.7))
    q8 = clamp(3.2 + 0.46 * (q6 - 4) + rng.gauss(0, 0.7))
    aware = rng.choices(Q12, weights=[10, 33, 57])[0]
    q9 = "20—35" if rng.random() < (0.38 if aware != "不知道" else 0.12) else rng.choice(Q9[1:])
    return {
        "gender": rng.choices([k for k, _ in GENDER], weights=[w for _, w in GENDER])[0],
        "grade": rng.choices([k for k, _ in GRADE], weights=[w for _, w in GRADE])[0],
        "major": rng.choices([k for k, _ in MAJOR], weights=[w for _, w in MAJOR])[0],
        "resid": resid,
        "familia": rng.choices([k for k, _ in FAMILIA], weights=[w for _, w in FAMILIA])[0],
        "q6": q6, "q7": q7, "q8": q8, "q9": q9,
        "q10": rng.sample(Q10[:6], k=rng.choice([1, 2, 3])),
        "q11": rng.sample(Q11, k=rng.choice([1, 2, 3])),
        "q12": aware,
        "q13": clamp(3.2 + rng.gauss(0, 0.9)),
        "q14": clamp(3.1 + rng.gauss(0, 0.9)),
        "q15": clamp(3.9 + rng.gauss(0, 0.7)),
        "q16": weighted([("0元", 16), ("1—20元", 30), ("21—50元", 29),
                         ("51—100元", 18), ("100元以上", 7)]),
        "q17": weighted([("机动车", 36), ("扬尘", 15), ("工业", 11),
                         ("区域协同", 30), ("冬季取暖", 8)]),
        "q18": "",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="灌多少份")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--seed", type=int, default=None, help="固定随机种子，结果可复现")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    url = f"http://127.0.0.1:{args.port}/api/submit"
    ok = 0
    for i in range(args.n):
        rec = make_one(rng)
        data = json.dumps(rec, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                json.loads(r.read().decode())
            ok += 1
        except Exception as e:
            print(f"第 {i+1} 份失败：{e}")
            break
    print(f"已提交 {ok} 份 → http://127.0.0.1:{args.port}/dashboard")


if __name__ == "__main__":
    main()
