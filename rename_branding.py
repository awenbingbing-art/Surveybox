# -*- coding: utf-8 -*-
"""把项目文案统一改成 Surveybox。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))

REPL = [
    ("README.md", [
        ("# 北京“蓝天”公众感知调查 · 本地统计工具", "# Surveybox · 轻量本地问卷统计"),
        ("一个**零依赖**的问卷采集与统计工具：自带问卷页、本地数据存储、统计看板与 CSV 导出。",
         "一个**零依赖**的问卷采集与统计工具：自带问卷页、本地数据存储、统计看板与 CSV 导出。\n\n"
         "> 示例：用它完成过一次北京大气治理的公众感知调查（N=86），"
         "问卷原文见 `questionnaire.md`，脱敏数据见 `data/sample_responses.jsonl`。"),
        ("## 说明", "## 示例数据\n\n"
                  "`data/sample_responses.jsonl` 是一次调查的脱敏样本（N=86，北京“蓝天”感知），"
                  "用于演示看板效果；`python server.py --empty` 可从零开始采集。\n\n## 说明"),
    ]),
    ("docs/使用手册.md", [
        ("# tinytally 使用手册", "# Surveybox 使用手册"),
        ("https://github.com/awenbingbing-art/beijing-air-survey",
         "https://github.com/awenbingbing-art/Surveybox"),
        ("按这份手册用 tinytally 起一个问卷", "按这份手册用 Surveybox 起一个问卷"),
    ]),
    ("server.py", [
        ('server_version = "BJAirSurvey/1.0"', 'server_version = "Surveybox/1.0"'),
    ]),
    ("web/dashboard.html", [
        ("<title>统计看板 · 北京大气治理公众感知调查</title>",
         "<title>统计看板 · Surveybox</title>"),
    ]),
]

for path, pairs in REPL:
    full = os.path.join(HERE, path)
    with io.open(full, encoding="utf-8") as f:
        text = f.read()
    hit = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new)
            hit += 1
        else:
            print(f"  ! 未命中：{path} :: {old[:28]}")
    with io.open(full, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"{path}: 替换 {hit}/{len(pairs)}")

# 校验
import ast
ast.parse(io.open(os.path.join(HERE, "server.py"), encoding="utf-8").read())
print("server.py 语法 OK")
