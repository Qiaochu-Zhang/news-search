# 数据源修复记录

## 批次一：初始修复（commit 3e2d9c8）

### h2_view（氢能）
**根因：** 站点套 Cloudflare，RSS feed 返回 403。
**修复：** `rss_url` 改为 Google News RSS：`https://news.google.com/rss/search?q=site:h2-view.com&...`
**注意：** Google News RSS 有约 5 天延迟，最新文章通常到不了昨日。

### netease_pv（光伏，网易号）
**根因：** RSSHub 返回含非法字符的 XML；桌面版页面完全 JS 渲染。
**修复：** 改用移动端 `m.163.com`，iPhone UA 抓取，解析 `<li class="js-click-news">`。
**注意：** 频道 T1632726077385（知光谷）更新缓慢，文章通常落后 2 周，难以拿到昨日新闻。

### xinhua_tech（新华网科技）
**根因：** 日期不在 HTML 文本中，正则提取失败。
**修复（初版）：** 改从 URL 路径 `/tech/YYYYMMDD/<hash>/c.html` 提取日期。

---

## 批次二：大规模改进（commit 9efc1a6 + 6a499fb）

### 全局：垃圾标题过滤（commit 9efc1a6）

在 `html_spider.py` 的 `crawl_html()` 中统一过滤，调用 `_is_junk_title(title)`：
- `_JUNK_TITLE_SET`：精确黑名单，覆盖导航词（首页/电力/国际能源网系列/光伏子栏目/Sectors/SUBSCRIBE 等）
- `_JUNK_TITLE_PATTERNS`：正则，匹配 `^首页\s*[>›/]`（面包屑）和 `^国际[\u4e00-\u9fff]{2,6}网$`（品牌名）
- 最短长度：≤ 4 字符直接丢弃

同时收紧各爬虫 URL 过滤：
- `inen_solar`：只接受 `/html/solar-\d+\.shtml$` 格式
- `renewablesnow`：只接受 `renewablesnow.com/news/[^/]+-\d+` 含数字 ID 的文章 URL

### 全局：日期过滤从"今天"改为"昨天"（commit 6a499fb）

**根因：** `is_today` 把昨天发布的 RSS 文章全部过滤掉，导致所有 RSS 站点输出 0 条。
**修复：**
- `utils/time_parser.py` 新增 `is_yesterday(dt, today)` 函数
- `main.py` 改用 `is_yesterday`；输出文件名改为昨日日期（新闻日期）

### sciencenet（科学网）

**根因：** 原正则 `sciencenet\.cn/htmlnews/` 只能匹配侧栏"一周排行"的绝对 URL（10条，无日期）；正文列表 30 条用相对路径 `/htmlnews/YYYY/M/ID.shtm`，被漏掉。
**修复：**
- 改用 `re.compile(r"^/htmlnews/\d{4}/")`，只抓相对路径链接
- 用 `urljoin("https://news.sciencenet.cn", href)` 补全绝对路径
- 日期在父 `<tr>` 文本中（格式 `2026/4/14 10:14:39`），用 `a.find_parent("tr")` 取
- 效果：0 → 17 篇昨日文章

### inen_solar（国际能源网-光伏）

**根因一：** URL 正则写 `.html$` 但实际是 `.shtml$`，导致 0 篇。
**根因二：** `li.find("a")` 找到图片链接（无文本），实际标题在 `<h5 a>` 里。
**根因三：** 日期用相对时间 `<i>1天前</i>` / `<i>X小时前</i>`，无绝对日期。
**修复：**
- URL 正则改为 `/html/solar-\d+\.shtml$`
- 优先从 `li.find("h5").find("a")` 取标题
- 解析 `<i>` 标签中的相对时间（`(\d+)天前` / `(\d+)小时前`），`now - timedelta(...)` 得到实际日期
- 页面从 `/SolarTech/` 改为 `/news/`（覆盖更广）
- 效果：0 → 7 篇昨日文章

### renewablesnow（RenewablesNow）

**根因一：** 页面在子栏目 `/company-news/products-technology/`，文章少；URL 正则过宽，匹配到 `/news/wind/` 等栏目页。
**根因二：** 页面用 React 渲染，无 `<h2>/<h3>` 标题标签，`a.get_text()` 拿到空字符串。
**修复：**
- 页面改为 `/news/`（主新闻列表）
- **标题从 `img alt` 属性提取**——React 页面文章图片的 alt 就是完整标题
- URL 正则改为 `renewablesnow\.com/news/[^/]+-\d+/?$`，要求末尾含数字 ID
- 日期从容器文本中用英文月份正则提取：`(Jan|Feb|...|Dec)\s+\d+,\s+\d{4}`
- 效果：2 → 10 篇昨日文章

### cpnn_energy / cpnn_tech（中国核能行业协会）

**根因：** 文章链接是相对路径 `./YYYYMM/tID.html`，原代码用 `"https://cpnn.com.cn"` 做 base，解析结果为 `https://cpnn.com.cn/YYYYMM/tID.html`（404）。正确路径应为 `https://cpnn.com.cn/news/xny/YYYYMM/tID.html`。
**修复：**
- 用 `resp.url` 代替硬编码 base，`urljoin(resp.url, href)` 自动正确解析
- 直接从 URL 路径提取日期（`/202604/t20260413_...` → `2026-04-13`），不依赖 HTML 文本
- URL 过滤改为正则 `/\d{6}/t\d{8}_\d+\.html$`
- 效果：URL 404 → 全部 200；no_date → 全部有日期

### xinhua_tech（补充修复）

**根因：** 原解析抓到栏目索引页（`/tech/sjbgt/index.html`、`/tech/zt/.../index.html`），这些 URL 无 8 位日期，导致 no_date 文章混入。
**修复：** 添加 URL 正则过滤 `/tech/\d{8}/[0-9a-f]+/c\.html$`，只保留真实文章页。
**效果：** 4 条 no_date 消除；总量从 40 → 36（去掉 4 个栏目页）

---

## 批次三：新增数据源（当前版本）

### 新增 RSS 站点（仅加 yaml，无需写解析函数）

| 站点 | RSS URL | 说明 |
|------|---------|------|
| electrek | `https://electrek.co/feed/` | 新能源/EV，日更约 10+ 篇 |
| scitechdaily | `https://scitechdaily.com/feed/` | 综合科技，日更约 15 篇 |
| interesting_engineering | `https://interestingengineering.com/feed` | 综合科技 |
| perovskite_info | Google News RSS `q=site:perovskite-info.com` | 直接访问需登录，改 Google News 聚合；约 1 天延迟 |

### 新增 HTML 站点

#### solarbe_tech（索比光伏网）

**URL：** `https://news.solarbe.com/`
**解析：** 文章 URL 格式 `/YYYYMM/DD/ID.html`，日期直接从 URL 提取。
**效果：** 约 100+ 篇/次，日更活跃。

#### tgs4c（4C Offshore）

**URL：** `https://www.tgs4c.com/news/`
**解析：** 文章 URL 格式 `/news/<slug>-nidXXXX.html`；标题从 `a` 文本取（过滤空链接和 "Read more"）；日期从父容器文本匹配 `DD Month YYYY` 格式（英文月份）。
**效果：** 约 3 篇/次（低频站，离岸风电专业站）。

#### china_nengyuan（中国能源网）

**URL：** `http://www.china-nengyuan.com/news/`
**解析：** 文章 URL 格式 `/news/ID.html`；列表页无日期，`publish_time = None`，`is_yesterday(None)` 返回 True 全部保留。
**效果：** 约 170 篇/次，全部无日期（pass-through）。

---

## 未能接入的数据源（记录备查）

| 来源 | 问题 | 说明 |
|------|------|------|
| WeChat 公众号（7 个） | 需登录 | 中粉固态电池/风电世界/起点钠电/能源学人/钙钛矿工厂/钙钛矿学习xx平台/地热能在线，微信公众号无公开 RSS，需登录后抓取 |
| esplaza.com.cn | Connection refused | 网站无法访问 |
| volta.foundation/battery-news | 月更 RSS | 更新频率约每月一篇，无法提供每日新闻 |
| batterytechonline.com | HTTP 403 | 网站屏蔽爬虫；Google News RSS 延迟且覆盖不全 |
| supplychaindigital.com | HTTP 403 | 网站屏蔽爬虫；内容以供应链综合为主，能源相关性低 |
| nachrichten.idw-online.de | 德语无 RSS | 德语站，无结构化 RSS，内容为学术新闻 |
| smartbrief BCI | 邮件通讯 | 无可抓取的公开列表页，内容为邮件推送 |

---

## 站点局限（无法解决，记录备查）

| 站点 | 问题 | 说明 |
|------|------|------|
| batteries_international | HTTP 403 | 文章页屏蔽爬虫，URL 本身正确 |
| h2_view | Google News 延迟 | 最新文章通常落后 5 天，昨日新闻为 0 |
| hydrogen_tech_world | 低频 | 每周更新，昨日通常为 0 |
| batteries_news | 低频 | 更新频率约 2-3 天一篇 |
| ammonia_energy | 低频 | 更新频率约 1-2 周一篇 |
| bnef_press | 低频 | 月报为主，最新约 1 月前 |
| netease_pv | 频道偏科研 | 知光谷频道更新缓慢，约 2 周延迟 |
| renewablesnow | 文章页 403 | 列表页可抓（URL 正确），文章页 WAF 拦截 Python requests，浏览器直接打开正常 |
| perovskite_info | Google News 延迟 | 最新文章通常落后 1 天，昨日新闻偶有 0 |
| tgs4c | 低频 | 离岸风电专业站，约 3 篇/日 |
| china_nengyuan | 无日期 | 列表页不含日期，全部 pass-through，含历史旧文章 |
