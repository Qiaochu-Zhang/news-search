# 多源能源新闻抓取系统（设计文档）

## 1. 项目目标

构建一个轻量级新闻抓取系统，每天自动运行一次，从 26 个能源/科技网站抓取前一天新闻，输出为 CSV 文件并自动 push 到 git 仓库。

抓取字段：

| 字段 | 说明 |
|------|------|
| site | 站点名称 |
| category | 新闻分类 |
| title | 文章标题 |
| url | 原文链接 |
| publish_time | 发布时间（无法获取时为空） |
| content | 正文（可选，默认跳过） |

输出文件：`daily-news/daily_news_YYYYMMDD.csv`（YYYYMMDD 为新闻日期，即昨天）

---

## 2. 总体架构

```
GitHub Actions (每天 UTC 04:00 = 北京时间 12:00)
    ↓
python3 main.py --no-content
    ↓
读取 configs/sites.yaml
    ↓
遍历 26 个站点
    ├── type=rss  → rss_spider.crawl_rss()     # 14 个站点
    └── type=html → html_spider.crawl_html()   # 12 个站点
    ↓
is_yesterday() 过滤（publish_time 为空的也保留）
    ↓
写入 carbon_spider/outputs/daily_news_YYYYMMDD.csv
    ↓
cp 到 daily-news/
    ↓
git commit & push
```

**核心策略：简单稳定优先。**RSS 优先，无 RSS 则抓 HTML 列表页。不用 Playwright、不用数据库、不用多线程，保证可维护性。

---

## 3. 数据源策略

### 3.1 RSS 源（14 个，优先）

- 使用 `feedparser` 解析，所有站点共用同一通用函数
- 时间字段按优先级尝试：`published` → `updated` → `created` → `published_parsed`
- `bozo=True`（非标准 XML）时记录警告但继续提取

**特殊处理：**
- `h2_view`、`perovskite_info`：原站点有访问限制，改用 Google News RSS 聚合（`q=site:xxx.com`），有约 1-5 天延迟

### 3.2 HTML 列表页（12 个）

- 使用 `requests + BeautifulSoup`
- 每站点一个 `@register("name")` 装饰的独立解析函数
- `crawl_html()` 统一入口：分发 + 集中过滤垃圾标题

**各站点主要解析难点：**

| 站点 | 难点 | 解法 |
|------|------|------|
| cpnn | 相对路径 `./YYYYMM/tID.html` | 用 `resp.url` 作 `urljoin` base |
| sciencenet | 两类链接混杂（有无日期） | 只取相对路径链接，日期从父 `<tr>` 取 |
| xinhua_tech | 日期不在文本 | 从 URL `/tech/YYYYMMDD/hash/c.html` 提取 |
| inen_solar | 相对时间（X天前） | `now - timedelta(days=N)` 实时计算 |
| renewablesnow | React 渲染，无 h 标签 | 标题从 `img alt` 提取 |
| solarbe_tech | — | URL 格式 `/YYYYMM/DD/ID.html`，直接提取日期 |
| tgs4c | 多个链接指向同一文章 | 过滤空文本和 "Read more" 链接 |
| china_nengyuan | 列表页无日期 | pass-through（`is_yesterday(None)` = True） |
| netease_pv | 桌面版 JS 渲染 | 改抓移动端 `m.163.com`，iPhone UA |

---

## 4. 垃圾标题过滤

`crawl_html()` 在调用各站点解析函数后，统一过滤非新闻内容：

```python
_JUNK_TITLE_SET      # 精确黑名单：导航词、品牌名、功能入口
_JUNK_TITLE_PATTERNS # 正则：面包屑（首页 > X）、品牌名格式（国际XX网）
# 最短长度 ≤ 4 字符直接丢弃
```

---

## 5. 日期过滤

目标：保留**前一天**（昨天）发布的文章。

```python
# utils/time_parser.py
def is_yesterday(dt, today=None) -> bool:
    if dt is None:
        return True   # 无日期时宽松保留
    return dt.date() == (today - timedelta(days=1)).date()
```

运行时以 UTC 时间计算昨日日期，与输出文件名保持一致。

---

## 6. 自动化调度（GitHub Actions）

配置文件：`.github/workflows/daily_scrape.yml`

```yaml
on:
  schedule:
    - cron: '0 4 * * *'   # UTC 04:00 = 北京时间 12:00
  workflow_dispatch:        # 支持手动触发
```

执行步骤：
1. Checkout 仓库
2. 安装 Python 3.10 + 依赖
3. `python3 main.py --no-content`
4. 复制输出到 `daily-news/`
5. `git commit && git push`（无新内容时跳过 commit）

---

## 7. 项目结构

```
news-search/
├── .github/workflows/daily_scrape.yml   # 定时任务
├── carbon_spider/
│   ├── configs/sites.yaml               # 26 个站点配置
│   ├── spiders/
│   │   ├── rss_spider.py
│   │   └── html_spider.py
│   ├── utils/time_parser.py
│   ├── main.py
│   └── requirements.txt
├── daily-news/                          # 每日 CSV 归档
└── docs/
    ├── code_logic.md                    # 代码逻辑详解
    └── fixes.md                         # 历次修复记录
```

---

## 8. 异常处理策略

| 场景 | 处理方式 |
|------|----------|
| RSS 请求失败 | try/except，记录日志，返回空列表，不影响其他站点 |
| HTML 解析失败 | 同上 |
| 正文抓取失败 | content 置空，不影响整体流程 |
| 无新文章（当日） | git diff 为空，跳过 commit |
| 站点日期格式变化 | `publish_time=None`，宽松过滤保留文章 |

---

## 9. 不做的事情（当前阶段）

- Playwright（动态渲染，除非 requests 完全无法访问）
- 数据库存储
- 多线程/分布式
- 复杂去重（同一 URL 只抓一次，当前通过 `seen` set 去重）
- 登录抓取（WeChat 公众号等无法接入）
- AI 摘要/分类

---

## 10. 扩展方式

**新增 RSS 站点**：`configs/sites.yaml` 加一条 `type: rss` 即可。

**新增 HTML 站点**：
1. `sites.yaml` 加配置
2. `html_spider.py` 写解析函数，用 `@register("name")` 注册

**注意**：目前 `solarbe_tech`（约 100+ 篇/日）和 `china_nengyuan`（约 170 篇/日）产量较大，且 `china_nengyuan` 无日期过滤，如需精确过滤可在文章页提取日期。
