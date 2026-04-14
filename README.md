# 多源能源新闻抓取系统

每日从 26 个能源/科技网站自动抓取前一天新闻，输出为 CSV 文件，并通过 GitHub Actions 在北京时间每天中午 12 点自动运行、自动 push。覆盖电池、储能、光伏、氢能、氨能、核电、风电、综合科技等分类。

---

## 目录结构

```
news-search/
├── .github/
│   └── workflows/
│       └── daily_scrape.yml    # GitHub Actions 定时任务
├── carbon_spider/              # 抓取程序
│   ├── configs/
│   │   └── sites.yaml          # 站点配置（26 个数据源）
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
├── docs/
│   ├── code_logic.md           # 代码逻辑详解
│   └── fixes.md                # 历次修复记录
└── sites.md                    # 数据源配置说明
```

---

## 自动化调度

系统通过 GitHub Actions 实现全自动运行，无需手动操作：

| 项目 | 说明 |
|------|------|
| 触发时间 | 每天北京时间 12:00（UTC 04:00） |
| 执行内容 | 抓取前一天新闻 → 写入 CSV → push 到 `daily-news/` |
| 配置文件 | `.github/workflows/daily_scrape.yml` |
| 手动触发 | GitHub → Actions → Daily News Scrape → Run workflow |

---

## 手动运行

```bash
cd carbon_spider
pip install -r requirements.txt

# 跳过正文抓取（推荐，约 60 秒完成）
python3 main.py --no-content

# 调试用：不过滤日期，保留所有抓到的文章
python3 main.py --no-content --all-dates
```

CSV 输出到 `carbon_spider/outputs/daily_news_YYYYMMDD.csv`（YYYYMMDD 为**新闻日期，即昨天**）。

---

## 数据源列表

### RSS 源（14 个）

| 站点名 | 分类 | 说明 |
|--------|------|------|
| electrive_battery | 电池 | 标准 RSS |
| ess_news | 储能 | 标准 RSS |
| batteries_international | 电池 | 低频，约 1 周一篇 |
| pv_magazine | 光伏 | 标准 RSS |
| ammonia_energy | 氨 | 低频，约 1-2 周一篇 |
| h2_view | 氢 | Cloudflare 封锁，改用 Google News RSS 聚合 |
| hydrogen_tech_world | 氢 | 低频，约每周更新 |
| batteries_news | 电池 | 低频，约 2-3 天一篇 |
| bnef_press | 新能源 | 月报为主 |
| techreview_climate | 新能源 | 每日约 1 篇 |
| electrek | 新能源/EV | 日更活跃，约 10+ 篇 |
| scitechdaily | 综合科技 | 日更约 15 篇 |
| interesting_engineering | 综合科技 | 日更约 10 篇 |
| perovskite_info | 光伏/钙钛矿 | 直接访问需登录，改用 Google News RSS；约 1 天延迟 |

### HTML 列表页（12 个）

| 站点名 | 分类 | 解析函数 | 关键细节 |
|--------|------|----------|----------|
| netease_pv | 光伏 | `crawl_netease_pv` | 移动端 m.163.com；知光谷频道更新慢约 2 周 |
| cnnpn_domestic | 核电国内 | `crawl_cnnpn` | 标准列表页 |
| cnnpn_international | 核电国外 | `crawl_cnnpn` | 标准列表页 |
| cpnn_energy | 新能源 | `crawl_cpnn` | 相对路径用 `resp.url` 做 base；日期从 URL 提取 |
| cpnn_tech | 综合科技 | `crawl_cpnn` | 同上 |
| sciencenet | 综合科技 | `crawl_sciencenet` | 相对路径链接；日期在父 `<tr>` 文本 |
| xinhua_tech | 综合科技 | `crawl_xinhua_tech` | 日期从 URL `/tech/YYYYMMDD/hash/c.html` 提取 |
| inen_solar | 光伏 | `crawl_inen_solar` | 相对时间（X天前/X小时前），运行时计算 |
| renewablesnow | 新能源 | `crawl_renewablesnow` | React 渲染，标题从 `img alt` 提取 |
| solarbe_tech | 光伏 | `crawl_solarbe` | 日期从 URL `/YYYYMM/DD/ID.html` 提取 |
| tgs4c | 风电 | `crawl_tgs4c` | 4C Offshore；URL 格式 `slug-nidXXXX.html`；日期格式 "DD Month YYYY" |
| china_nengyuan | 新能源 | `crawl_china_nengyuan` | 列表页无日期，全部 pass-through |

---

## CSV 字段说明

| 字段 | 说明 |
|------|------|
| `site` | 站点名称（对应 sites.yaml 中的 `name`） |
| `category` | 新闻分类（电池 / 光伏 / 氢 / 核电 等） |
| `title` | 文章标题 |
| `url` | 原文链接 |
| `publish_time` | 发布时间，格式 `YYYY-MM-DD HH:MM:SS+00:00`；无法获取时为空 |
| `content` | 正文内容（默认为空，`--no-content` 时跳过抓取） |

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
日期过滤：保留昨天发布的文章（publish_time 为空的也保留，避免漏抓）
    ↓
可选：逐篇用 newspaper3k 抓正文
    ↓
写入 CSV（pandas to_csv，utf-8-sig 编码，文件名为昨日日期）
```

### RSS 抓取（rss_spider.py）

使用 `feedparser` 解析 RSS/Atom feed，提取 `title` / `link` / `published`。

- 时间字段按优先级尝试：`published` → `updated` → `created` → `published_parsed`
- feed 格式异常（`bozo=True`）时记录警告但继续提取，不中断
- 所有站点共用同一通用函数

### HTML 抓取（html_spider.py）

每个站点有独立解析函数，通过 `@register("site_name")` 装饰器注册。`crawl_html()` 负责：
1. 分发到对应解析函数
2. 集中过滤垃圾标题（导航词、品牌名、功能入口等）

### 时间解析（utils/time_parser.py）

- `parse_time(str)` → datetime：支持 `yyyy-mm-dd` / `yyyy/mm/dd` / `yyyy年mm月dd日` / RFC 2822
- `is_yesterday(dt, today)`：`dt=None` 时返回 `True`，宽松过滤避免漏抓

---

## 新增站点

**RSS 站点**：在 `configs/sites.yaml` 中加一条 `type: rss` 配置即可，无需改代码。

**HTML 站点**：
1. 在 `sites.yaml` 中加配置（`type: html`）
2. 在 `html_spider.py` 中写解析函数并用 `@register("name")` 注册：

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

## 历史修复记录

详见 `docs/fixes.md`。简要摘要：

| 站点 | 问题 | 修复方案 |
|------|------|----------|
| h2_view | Cloudflare 403 | 改用 Google News RSS 聚合 |
| netease_pv | RSSHub 非法 XML / JS 渲染 | 改抓移动端静态 HTML |
| xinhua_tech | 无日期 | 从 URL 路径 `/tech/YYYYMMDD/hash/c.html` 提取 |
| sciencenet | 只抓到侧栏排行（无日期） | 改用相对路径链接 + `find_parent("tr")` 取日期 |
| inen_solar | URL 正则错误 / 相对时间 | 修正 `.shtml` 正则；解析 "X天前/X小时前" |
| renewablesnow | React 渲染无标题标签 | 标题从 `img alt` 属性提取 |
| cpnn | 相对路径 404 | 改用 `resp.url` 作为 `urljoin` base |
