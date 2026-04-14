# 代码逻辑说明

能源新闻每日抓取系统，代码在 `carbon_spider/` 目录，输出归档在 `daily-news/`。

**技术栈：** feedparser（RSS）、requests + BeautifulSoup（HTML）、pandas（CSV输出）

**运行方式：**
```bash
cd carbon_spider
python3 main.py --no-content        # 跳过正文，约60秒完成
python3 main.py --no-content --all-dates  # 调试用，不过滤日期
```

**数据源：** 19 个站点，10 RSS + 9 HTML，覆盖电池/储能/光伏/氢/氨/核电/科技分类。

**输出：** `carbon_spider/outputs/daily_news_YYYYMMDD.csv`，其中 YYYYMMDD 是**新闻日期（昨天）**，而非运行日期。手动复制到 `daily-news/` 后 push。

---

## 核心逻辑

### main.py
1. 加载 `configs/sites.yaml` 中所有站点
2. 按站点类型分发给 `crawl_rss()` 或 `crawl_html()`
3. 用 `is_yesterday()` 过滤昨日文章（`publish_time` 为 None 的也保留，避免漏抓）
4. 输出 CSV，文件名以新闻日期（昨日）命名

### spiders/rss_spider.py
通用 RSS 抓取，feedparser 解析 `published/updated/created` 字段，统一交给 `utils/time_parser.parse_time()` 解析。

### spiders/html_spider.py
核心模块，每个站点一个 `@register("name")` 装饰的解析函数。
`crawl_html()` 是统一入口，调用完各站点函数后，集中过滤垃圾标题（`_is_junk_title()`）。

**垃圾标题过滤（`_is_junk_title()`）：**
- 精确黑名单：导航词、品牌名（国际能源网系列）、英文导航（Sectors/Events/SUBSCRIBE）
- 正则：`^首页\s*[>›/]`（面包屑）、`^国际[\u4e00-\u9fff]{2,6}网$`（品牌名格式）
- 最短长度 ≤ 4 字符

### utils/time_parser.py
- `parse_time(str)` → datetime：支持 yyyy-mm-dd / yyyy/mm/dd / yyyy年mm月dd日 / RFC 2822
- `is_today(dt, today)` / `is_yesterday(dt, today)`：None 时返回 True（宽松过滤）

---

## 各站点解析要点

| 站点 | 类型 | 关键解析细节 |
|------|------|-------------|
| electrive_battery | RSS | 标准 RSS，无特殊处理 |
| ess_news | RSS | 标准 RSS |
| batteries_international | RSS | 低频，最新约 1 周前 |
| pv_magazine | RSS | 标准 RSS |
| ammonia_energy | RSS | 低频，最新约 2 周前 |
| h2_view | RSS | Cloudflare 封锁，用 Google News RSS 替代 |
| hydrogen_tech_world | RSS | 低频，最新约 4 天前 |
| batteries_news | RSS | 低频，最新约 2 天前 |
| bnef_press | RSS | 低频，最新约 1 月前 |
| techreview_climate | RSS | 标准 RSS，每日 1 篇左右 |
| netease_pv | HTML | 移动端 m.163.com；频道 T1632726077385（知光谷）更新慢，约2周延迟 |
| cnnpn_domestic/international | HTML | 核电国内/国外；`ul li` 结构，日期在 class=date 标签，约一半文章无日期标签 |
| cpnn_energy/cpnn_tech | HTML | 链接为相对路径 `./YYYYMM/tID.html`，**必须用 `resp.url` 做 base**，否则 404；日期从 URL 提取 |
| sciencenet | HTML | 正文列表用相对链接 `/htmlnews/YYYY/M/ID.shtm`；日期在父 `<tr>` 文本（格式 `2026/4/14 10:14:39`）；侧栏排行用绝对链接，无日期，需排除 |
| xinhua_tech | HTML | 只保留 `/tech/YYYYMMDD/<hash>/c.html` 格式文章 URL；日期从 URL 提取 |
| inen_solar | HTML | 标题在 `<h5 a>`（非图片链接）；日期为相对时间 `<i>X天前/X小时前</i>`，运行时实时计算；文章 URL 格式 `/html/solar-\d+\.shtml` |
| renewablesnow | HTML | `/news/` 页；React 渲染无 h 标签，**标题从 `img alt` 提取**；日期从容器文本英文月份匹配；URL 需含数字 ID |

**设计原则：** 简单优先，每站点独立处理，出错不影响整体。

**新增站点：** RSS 站点只改 yaml；HTML 站点需在 `html_spider.py` 中写解析函数并用 `@register("name")` 注册。
