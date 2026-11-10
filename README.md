# Surveybox

本地问卷与统计工具。一条命令起一个网站：问卷页填、后台灌数、看板出图，数据只存在你电脑的一个文件里。

---

## 开始（三步）

**第一步：确认有 Python 3.9+**

```bash
python --version
```

**第二步：启动**

```bash
python server.py --port 8791 --host 0.0.0.0
```

没有任何依赖要装，没有 `pip install`。

**第三步：打开浏览器**

```
http://127.0.0.1:8791/                      问卷（给别人填）
http://127.0.0.1:8791/dashboard             看板（出数据）
http://127.0.0.1:8791/admin?key=tally2026   后台（改题、灌数、导数据）
```

启动时终端会把这三个地址连后台密钥一起打印出来，直接复制即可。

**手机要填？** 保持 `--host 0.0.0.0`，用终端打印的局域网地址（形如 `http://192.168.1.5:8791/`），手机连同一 WiFi 打开。打不开就是 Windows 防火墙没放行：

```powershell
New-NetFirewallRule -DisplayName "Surveybox" -Direction Inbound -LocalPort 8791 -Protocol TCP -Action Allow
```

---

## 几个常见用法

```bash
python server.py --port 8791                 # 换端口（8765 常被别的项目占）
python server.py --db data/第二份.jsonl       # 换一个数据文件，两批数据互不干扰
python server.py --db2 data/对比.jsonl        # 同时加载两份，看板出现「对比」开关
python server.py --admin-key 我的密码          # 换后台钥匙
```

---

## 三个页面

| 地址 | 是什么 |
|---|---|
| `/` | 问卷页，从 `data/survey.json` 渲染，手机友好 |
| `/dashboard` | 统计看板：条形 / 饼图切换，量表题给均值±标准差 |
| `/admin?key=…` | 后台：改题库、灌数、导入、导出、二维码（**无 key 返回 404**） |

## 能做什么

- **题库可换**：四种题型（单选/多选/量表/文本），后台改 JSON 直接生效，不碰代码
- **模板**：内置「校园咖啡调查（8 题，四种题型齐全）」「示例问卷」「空白问卷」，一键载入
- **出数**：频数、均值±标准差、文本摘录；条形与饼图切换
- **对比**：`--db2` 后两库并排，标出每个选项的百分比差值
- **导入**：后台粘贴 JSON / JSONL / CSV，表头写题干也能对上，时间可摊到过去 N 天
- **二维码**：`/api/qr` 输出问卷页 SVG，手机扫码即填（本地生成，不联网）
- **后门**：`/admin` 不带 key 是 404；提交接口带 `X-Admin-Key` 头可跳过必答校验

## 目录结构

```
Surveybox/
├── server.py                  # 服务 + 通用统计引擎（仅标准库）
├── bulk_fill.py               # 批量灌数（走真实 HTTP 接口）
├── seed.py                    # 外部 CSV → JSONL（可选）
├── run.bat                    # Windows 一键启动
├── docs/使用手册.md            # 从发问卷到导出的全流程（13 章）
├── vendor/qrcode/             # 内嵌二维码编码器（纯 Python）
├── web/
│   ├── index.html             # 问卷页
│   ├── dashboard.html         # 统计看板
│   └── admin.html             # 后台
└── data/
    ├── templates/             # 题库模板（进版本库）
    │   ├── campus-coffee.survey.json   # 校园咖啡调查，8 题
    │   ├── generic.survey.json         # 四题型示例
    │   ├── blank.survey.json           # 空白
    │   └── _archive/                   # 归档，不显示在后台
    ├── survey.json            # 当前题库（运行时生成，不进版本库）
    └── responses.jsonl        # 当前数据（运行时生成，不进版本库）
```

首次启动会自动从 `generic.survey.json` 装一份示例题库。想换成北京那份：后台「题库 → 载入模板」，勾上「同时载入模板配套数据」。

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

口径：单选/多选算频数，量表算均值±标准差，文本取前五条。

## 接口

| 接口 | 方法 | 用途 |
|---|---|---|
| `/api/survey` | GET / POST | 读 / 写题库 |
| `/api/submit` | POST | 提交一份问卷 |
| `/api/stats` | GET | 统计结果 |
| `/api/compare` | GET | 两库对比结果 |
| `/api/qr?text=` | GET | 二维码 SVG |
| `/api/admin/templates` | GET | 模板清单 |
| `/api/admin/load-template?name=&data=` | POST | 载入模板（可带配套数据） |
| `/api/admin/seed?n=` | POST | 灌 n 份随机答卷 |
| `/api/admin/import` | POST | 导入 JSON / JSONL / CSV |
| `/api/admin/reset` | POST | 清空 |
| `/export.csv` · `/export.md` | GET | 导出 |

后台相关接口都需要 `?key=` 或 `X-Admin-Key` 头。

## 安全说明

- 默认只监听 `127.0.0.1`，加 `--host 0.0.0.0` 才对局域网开放；
- 后台默认钥匙是 `tally2026`，公网使用前务必用 `--admin-key` 换掉；
- 不联网、不上报，所有数据都在本机文件里。

## License

MIT
