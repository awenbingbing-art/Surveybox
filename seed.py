# -*- coding: utf-8 -*-
"""把问卷星导出的 CSV 转成本工具使用的 JSONL 样本数据。

用法：python seed.py [源CSV路径]
默认读取本目录上一级的 survey_raw.csv；仓库使用者通常无需运行本脚本，
data/sample_responses.jsonl 已包含可直接演示的示例数据。
"""
import csv
import json
import os
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "survey_raw.csv")
OUT = os.path.join(HERE, "data", "sample_responses.jsonl")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

if not os.path.exists(SRC):
    sys.exit("找不到源 CSV：" + SRC + "\n（示例数据已就绪，无需运行本脚本）")

MAP = {
    "性别": "gender", "年级": "grade", "专业大类": "major",
    "在京居住时长": "resid", "家人呼吸/心血管疾病": "familia",
    "Q6_改善感知": "q6", "Q7_北京蓝频次": "q7", "Q8_满意度": "q8",
    "Q9_浓度估计": "q9", "Q10_污染源认知": "q10", "Q11_信息渠道": "q11",
    "Q12_知晓达标": "q12", "Q13_支持限行": "q13", "Q14_支持停工": "q14",
    "Q15_支持煤改电": "q15", "Q16_支付意愿": "q16", "Q17_优先治理": "q17",
}
MULTI = {"q10", "q11"}

base = datetime.datetime(2026, 11, 6, 9, 30)
rows = []
with open(SRC, encoding="utf-8-sig") as f:
    for i, r in enumerate(csv.DictReader(f)):
        rec = {"id": i + 1, "ts": (base + datetime.timedelta(hours=7 * i)).strftime("%Y-%m-%d %H:%M:%S")}
        for cn, en in MAP.items():
            v = r[cn]
            if en in MULTI:
                rec[en] = [x for x in v.split(";") if x]
            elif en.startswith("q") and en[1:].isdigit() and int(en[1:]) in (6, 7, 8, 13, 14, 15):
                rec[en] = int(v)
            else:
                rec[en] = v
        rec["q18"] = ""
        rows.append(rec)

with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print("wrote", len(rows), "records ->", OUT)
