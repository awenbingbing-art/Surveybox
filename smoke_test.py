# -*- coding: utf-8 -*-
import json, urllib.request

rec = {"gender": "男", "grade": "大二", "major": "理工", "resid": "不足1年", "familia": "无",
       "q6": 4, "q7": 4, "q8": 3, "q9": "20—35", "q10": ["机动车"], "q11": ["手机App"],
       "q12": "听说过", "q13": 3, "q14": 3, "q15": 4, "q16": "21—50元",
       "q17": "机动车", "q18": "自动化测试"}
data = json.dumps(rec, ensure_ascii=False).encode("utf-8")
req = urllib.request.Request("http://127.0.0.1:8791/api/submit", data=data,
                             headers={"Content-Type": "application/json"})
print("submit ->", urllib.request.urlopen(req).read().decode())

stats = json.load(urllib.request.urlopen("http://127.0.0.1:8791/api/stats"))
print("N =", stats["n"])
print("correct_pct =", stats["q9"]["correct_pct"])
