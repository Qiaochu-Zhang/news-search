# 多源能源新闻抓取系统

每日从 19 个能源/科技网站抓取新闻，输出为 CSV 文件。覆盖电池、储能、光伏、氢能、氨能、核电、综合科技等分类。

---

## 目录结构

```
news-search/
├── carbon_spider/              # 抓取程序
│   ├── configs/
│   │   └── sites.yaml          # 站点配置（19 个数据源）
│   ├── spiders/
│   │   ├── rss_spider.py       # RSS 抓取模块
│   │   └── html_spider.py      # HTML 列表页抓取模块
│   ├── utils/
│   │   └── time_parser.py      # 时间解析工具
│   ├── outputs/                # 本地临时输出（不入库）
│   ├── main.py                 # 主入口
│   └── requirements.txt
├── daily-news/                 # 每日 CSV 归档（入库）
│   └── daily_news_YYYYMMDD.csv
├── design.md                   # 系统设计文档
└── sites.md                    # 数据源原始配置
```

---

## 快速开始

```bash
cd carbon_spider
pip install -r requirements.txt

# 默认运行：只保留今天的文章，同时抓取正文
python3 main.py

# 跳过正文抓取（更快，约 30 秒完成）
python3 main.py --no-content

# 不过滤日期，保留所有抓到的文章（调试 / 补抓历史用）
python3 main.py --no-content --all-dates
```

CSV 输出到 `carbon_spider/outputs/daily_news_YYYYMMDD.csv`，手动复制到 `daily-news/` 后 push 入库。

---

## 数据源列表

### RSS 源（11 个）

| 站点名 | 分类 | 状态 |
|--------|------|------|
| electrive_battery | 电池 | 正常 |
| ess_news | 储能 | 正常 |
| batteries_international | 电池 | 正常 |
| pv_magazine | 光伏 | 正常 |
| ammonia_energy | 氨 | 正常 |
| h2_view | 氢 | 正常（Google News RSS 聚合） |
| hydrogen_tech_world | 氢 | 正常 |
| batteries_news | 电池 | 正常 |
| bnef_press | 新能源 | 正常 |
| techreview_climate | 新能源 | 正常 |

### HTML 列表页（8 个）

| 站点名 | 分类 | 解析函数 |
|--------|------|----------|
| cnnpn_domestic | 核电国内 | `crawl_cnnpn` |
| cnnpn_international | 核电国外 | `crawl_cnnpn` |
| cpnn_energy | 新能源 | `crawl_cpnn` |
| cpnn_tech | 综合科技 | `crawl_cpnn` |
| sciencenet | 综合科技 | `crawl_sciencenet` |
| xinhua_tech | 综合科技 | `crawl_xinhua_tech` |
| inen_solar | 光伏 | `crawl_inen_solar` |
| renewablesnow | 新能源 | `crawl_renewablesnow` |
| netease_pv | 光伏 | `crawl_netease_pv` |

---

## CSV 字段说明

| 字段 | 说明 |
|------|------|
| `date` | 运行日期，格式 `YYYYMMDD` |
| `site` | 站点名称（对应 sites.yaml 中的 `name`） |
| `category` | 新闻分类（电池 / 光伏 / 氢 / 核电 等） |
| `title` | 文章标题 |
| `url` | 原文链接 |
| `publish_time` | 发布时间，格式 `YYYY-MM-DD HH:MM:SS`，无法获取时为空 |
| `content` | 正文内容（默认为空，启用 `--no-content` 时跳过抓取） |

---

## 代码逻辑

### 主流程（main.py）

```
读取 sites.yaml
    ↓
遍历每个站点
    ├── type=rss  → rss_spider.crawl_rss()
    └── type=html → html_spider.crawl_html()
    ↓
日期过滤（保留今天 / publish_time 为空的文章）
    ↓
可选：逐篇用 newspaper3k 抓正文
    ↓
写入 CSV（pandas to_csv，utf-8-sig 编码）
```

### RSS 抓取（rss_spider.py）

使用 `feedparser` 解析 RSS/Atom feed，提取 `title` / `link` / `published`。

- 时间字段按优先级尝试：`published` → `updated` → `created` → `published_parsed`（struct_time 转字符串）
- feed 格式异常（`bozo=True`）时记录警告但继续提取，不中断
- 所有站点共用同一个通用函数，无需为每个 RSS 站写专门代码

### HTML 抓取（html_spider.py）

每个站点有独立解析函数，通过 `@register("site_name")` 装饰器注册到分发表 `_REGISTRY`。`crawl_html()` 根据 `site['name']` 查表调用对应函数，找不到则跳过。

各站点解析策略：

| 站点 | 解析策略 |
|------|----------|
| cnnpn | 遍历 `<li>`，找 `<a>` 取标题/链接，找 class 含 `date/time/pub` 的元素取日期 |
| cpnn | 遍历 `.news-item / .list-item / li`，过滤非 `cpnn.com.cn` 域名的链接 |
| sciencenet | 直接匹配 href 包含 `sciencenet.cn/htmlnews/` 的 `<a>` 标签 |
| xinhua_tech | 匹配 href 含 `news.cn` 的 `<a>`，URL 去重 |
| inen_solar | 遍历 `<li>`，日期补全年份（`04-12` → `2026-04-12`） |
| renewablesnow | 遍历 `article/div[class~=post]`，优先读 `<time datetime>` 属性 |

### 时间解析（utils/time_parser.py）

三层解析，依次尝试：

1. 中文日期正则：`2024年04月12日` / `2024-04-12` / `2024/04/12` / `2024.04.12`
2. `dateutil.parser.parse(fuzzy=True)`：处理 RSS 中的 RFC 2822 格式（`Mon, 13 Apr 2026 08:00:00 +0000`）
3. 均失败 → 返回 `None`

`is_today(dt)` 在 `dt=None` 时返回 `True`，保留无时间戳的文章，避免漏抓。

---

## 新增站点

**RSS 站点**：在 `configs/sites.yaml` 中加一条 `type: rss` 配置即可，无需改代码。

**HTML 站点**：
1. 在 `sites.yaml` 中加配置（`type: html`）
2. 在 `html_spider.py` 中写解析函数并注册：

```python
@register("new_site_name")
def crawl_new_site(site: dict) -> list[dict]:
    resp = _get(site["home_url"])
    if resp is None:
        return []
    soup = _soup(resp)
    articles = []
    for ...:
        articles.append(_make_article(site, title, url, date_str))
    return articles
```

---

## 历史问题及修复记录

| 站点 | 问题 | 根因 | 修复方案 | 修复后 |
|------|------|------|----------|--------|
| h2_view | RSS 返回 0 条 | 站点套 Cloudflare，RSS 和 HTML 均返回 403 | 改用 Google News RSS（`site:h2-view.com`）作为数据源 | 正常，可获取 ~100 条 |
| netease_pv | RSS 返回 0 条 | RSSHub 返回含非法字符的 XML，feedparser 解析失败；桌面版页面 JS 渲染 | 改抓移动端静态 HTML（`m.163.com/news/sub/...`），结构规整 | 正常，可获取 ~20 条 |
| xinhua_tech | 部分文章无发布时间 | 原逻辑从父元素文本中正则匹配日期，但日期不在文本里 | 改从 URL 路径提取（`/tech/YYYYMMDD/<hash>/c.html`） | 90% 文章有日期（无日期为外链文章）|
