# Surveybox · 轻量本地问卷统计

一个**零依赖**的问卷采集与统计工具：问卷页、数据看板、后台管理三件套，全部跑在本机。
数据存在一个 `.jsonl` 文件里，不上传、不联网、不依赖任何 pip 包。

> 示例：用它完成过一次北京大气治理的公众感知调查（N=86），
> 问卷原文见 `questionnaire.md`，脱敏数据见 `data/sample_responses.jsonl`。

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

## 三个页面

| 地址 | 是什么 |
|---|---|
| `/` | 问卷页，手机同局域网可填 |
| `/dashboard` | 统计看板，截图就截这页 |
| `/admin?key=…` | 后台：灌数、清空、改题库、拿分享链接（**无 key 返回 404**） |

## 快速开始

```bash
python server.py                          # http://127.0.0.1:8765
python server.py --port 8791              # 换端口
python server.py --host 0.0.0.0           # 手机同局域网可访问
python server.py --empty                  # 空库开始
python server.py --db data/batch2.jsonl   # 换一批数据
python server.py --admin-key mysecret     # 换后台钥匙
python server.py --db2 data/demo_b.jsonl # 开启对比（看板出现“对比”开关）
```

启动后终端会打印四个地址，其中包括带 key 的后台链接。
Windows 可直接双击 `run.bat`。

## 能做什么

- **问卷页**：从 `data/survey.json` 渲染，改题库不用改代码；单选 / 多选 / 量表 / 文本四种题型
- **看板**：频数分布、均值±标准差、文本摘录，手机端自动单列
- **后台**：一键灌 N 份随机答卷、载入示例、清空、直接编辑题库 JSON、导出 CSV / Markdown
- **后门**：`/admin` 不带 key 就是 404；提交接口带 `X-Admin-Key` 头时跳过必答校验
- **二维码**：`/api/qr` 输出问卷页二维码 SVG，后台里直接看、直接下
- **图表**：看板支持条形 / 饼图切换，量表题带均值和分布
- **对比**：`--db2 另一份数据.jsonl` 后，看板可并排比较两批样本
- **导入**：后台粘贴 JSON / JSONL / CSV 即可入库，可把时间摊到过去 N 天

## 目录结构

```
Surveybox/
├── server.py                  # 服务 + 通用统计引擎（仅标准库）
├── bulk_fill.py               # 批量灌数（走真实 HTTP 接口）
├── seed.py                    # 外部 CSV → JSONL（可选）
├── smoke_test.py              # 提交链路自测
├── run.bat                    # Windows 一键启动
├── questionnaire.md           # 18 题问卷原文（示例）
├── docs/使用手册.md            # 从发问卷到导出的全流程
├── web/
│   ├── index.html             # 问卷页（移动端优先）
│   ├── dashboard.html         # 统计看板
│   └── admin.html             # 后台
└── data/
    ├── survey.json            # 题库定义
    ├── sample_responses.jsonl # 示例样本 N=86
    ├── demo_b.jsonl          # 对比用的第二份样本 N=120
    └── responses.jsonl        # 实际采集库（已 gitignore）
```

## 题库格式

```json
{
  "title": "问卷标题",
  "intro": "导语",
  "questions": [
    {"id": "q1", "type": "single", "title": "题干", "options": ["A", "B"], "required": true},
    {"id": "q2", "type": "multi",  "title": "题干", "options": ["A", "B"], "max": 3},
    {"id": "q3", "type": "scale",  "title": "题干", "labels": ["很差", "", "", "", "很好"], "scale_max": 5},
    {"id": "q4", "type": "text",   "title": "题干", "required": false}
  ]
}
```

统计口径：单选/多选算频数，量表算均值±标准差，文本取前五条。

## 接口

| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/survey` | GET / POST | 读 / 写题库（POST 需后台钥匙） |
| `/api/submit` | POST | 提交一份问卷 |
| `/api/stats` | GET | 统计结果 JSON |
| `/api/responses` | GET | 原始数据（需钥匙） |
| `/api/admin/seed?n=` | POST | 灌 n 份随机答卷 |
| `/api/admin/reset` | POST | 清空 |
| `/api/admin/import` | POST | 导入 JSON / JSONL / CSV |
| `/api/compare` | GET | 两个数据集的统计结果 |
| `/api/qr?text=` | GET | 二维码 SVG |
| `/export.csv` · `/export.md` | GET | 导出 |

## 示例数据

`data/sample_responses.jsonl` 是一次调查的脱敏样本（N=86，北京“蓝天”感知），
用于演示看板效果；`python server.py --empty` 可从零开始采集。

## 说明

- 匿名自填，不做身份校验，适合课程作业、社团调研等低风险场景；
- 默认只监听 `127.0.0.1`，要手机访问显式加 `--host 0.0.0.0`；
- 不联网、不上报，所有数据只存在本机文件里。

## License

MIT
