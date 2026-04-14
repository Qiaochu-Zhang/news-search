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
