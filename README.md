# 北京“蓝天”公众感知调查 · 本地统计工具

一个**零依赖**的问卷采集与统计工具：自带问卷页、本地数据存储、统计看板与 CSV 导出。
单机运行，数据不出本机，适合课堂汇报现场演示，也适合小型调查的前期摸底。

![Python](https://img.shields.io/badge/python-3.9%2B-3776AB)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

## 它做什么

- 网页填问卷（手机同局域网可直接访问）
- 提交即落盘，一条一条写进 `data/responses.jsonl`
- 看板实时计算：频数分布、李克特均值±标准差、正确率、支付意愿加权值、Welch t 检验、卡方检验、相关系数
- 一键导出 CSV / Markdown 表，可直接贴进报告附件

## 快速开始

```bash
python server.py              # 默认 http://127.0.0.1:8765
python server.py --port 8791  # 端口被占用时换一个
python server.py --empty      # 不载入示例数据，从空库开始
```

Windows 可直接双击 `run.bat`。依赖只有 Python 标准库，无需 pip install。

| 地址 | 用途 |
|---|---|
| `/` | 问卷填写页 |
| `/dashboard` | 统计看板 |
| `/export.csv` | 导出全部原始数据 |
| `/export.md` | 导出 Markdown 统计表 |
| `/api/stats` | 统计结果 JSON |
| `/api/responses` | 原始数据 JSON |

## 目录结构

```
survey-tool/
├── server.py                  # HTTP 服务 + 统计引擎（仅标准库）
├── bulk_fill.py               # 批量灌数（走真实 HTTP 接口）
├── seed.py                    # 把外部 CSV 转成 JSONL（可选）
├── smoke_test.py              # 提交链路自测
├── run.bat                    # Windows 一键启动
├── questionnaire.md           # 18 题问卷原文
├── docs/使用手册.md            # 从发问卷到导出的全流程
├── web/
│   ├── index.html             # 问卷页
│   └── dashboard.html         # 统计看板（内联 CSS/JS）
└── data/
    ├── sample_responses.jsonl # 示例样本（N=86）
    └── responses.jsonl        # 实际采集库（首次启动自动生成，已 gitignore）
```

## 指标定义

| 指标 | 计算方式 |
|---|---|
| 频数分布 | 计数 ÷ 有效样本，保留 1 位小数 |
| 李克特均值 | 1—5 分算术平均，标准差取样本标准差（ddof=1） |
| 浓度估计正确率 | 选择「20—35 μg/m³」的比例（2025 年实际值 27.0） |
| 支付意愿加权值 | 区间组中值 0／10／35／75／150 元加权平均 |
| 分组差异 | Welch t 检验（不假设方差齐性），\|t\| > 1.99 视为 p<0.05 |
| 认知关联 | 2×2 卡方检验，χ² > 3.84（df=1）视为显著 |
| 相关 | Pearson 相关系数 |

## 数据格式

每行一条 JSON：

```json
{"id":1,"ts":"2026-11-06 09:30:00","gender":"女","grade":"大二","major":"文法",
 "resid":"10年以上","familia":"无","q6":4,"q7":4,"q8":3,"q9":"20—35",
 "q10":["机动车","燃煤"],"q11":["手机App"],"q12":"听说过",
 "q13":3,"q14":4,"q15":4,"q16":"21—50元","q17":"机动车","q18":""}
```

字段与问卷题号一一对应，见 `questionnaire.md` 的变量对照表。

## 用它做自己的调查

1. 改 `web/index.html` 里的题目与 `OPTS` 选项；
2. 改 `server.py` 顶部的 `LIKERT` / `DEMO` / `MULTI` 字段映射；
3. `python server.py --empty` 从空库开始收集；
4. 结束时 `/export.csv` 导出，或 `/export.md` 直接取表。

## 说明

- 示例样本（N=86）用于界面演示与方法验证，可在 `data/responses.jsonl` 中整体替换；
- 匿名自填，不做身份校验，适合课程作业、社团调研等低风险场景；
- 本工具不联网、不上报，所有数据只存在本机文件里。

## License

MIT

