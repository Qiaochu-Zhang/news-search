# 数据源配置说明

本文件说明 `carbon_spider/configs/sites.yaml` 中各站点的配置。共 26 个站点（14 RSS + 12 HTML）。

---

## RSS 源（14 个）

| name | category | RSS URL | 说明 |
|------|----------|---------|------|
| electrive_battery | 电池 | `https://www.electrive.com/category/battery-fuel-cell/feed/` | 标准 RSS |
| ess_news | 储能 | `https://www.ess-news.com/category/projects-applications/feed/` | 标准 RSS |
| batteries_international | 电池 | `https://www.batteriesinternational.com/news-test/news/feed/` | 低频，约 1 周一篇 |
| pv_magazine | 光伏 | `https://www.pv-magazine.com/category/installations/commercial-industrial-pv/feed/` | 标准 RSS |
| ammonia_energy | 氨 | `https://ammoniaenergy.org/articles/feed/` | 低频，约 1-2 周一篇 |
| h2_view | 氢 | Google News RSS `q=site:h2-view.com` | 原 feed Cloudflare 403，改用 Google News 聚合；约 5 天延迟 |
| hydrogen_tech_world | 氢 | `https://hydrogentechworld.com/feed/` | 低频，约每周更新 |
| batteries_news | 电池 | `https://batteriesnews.com/feed/` | 低频，约 2-3 天一篇 |
| bnef_press | 新能源 | `https://about.bnef.com/feed/?post_type=insights&type=press` | 月报为主 |
| techreview_climate | 新能源 | `https://www.technologyreview.com/topic/climate-change/feed/` | 每日约 1 篇 |
| electrek | 新能源/EV | `https://electrek.co/feed/` | 日更活跃，约 10+ 篇 |
| scitechdaily | 综合科技 | `https://scitechdaily.com/feed/` | 日更约 15 篇 |
| interesting_engineering | 综合科技 | `https://interestingengineering.com/feed` | 日更约 10 篇 |
| perovskite_info | 光伏/钙钛矿 | Google News RSS `q=site:perovskite-info.com` | 直接访问需登录，改用 Google News；约 1 天延迟 |

---

## HTML 列表页（12 个）

| name | category | home_url | 解析函数 | 关键说明 |
|------|----------|----------|----------|----------|
| netease_pv | 光伏 | `https://m.163.com/news/sub/T1632726077385.html` | `crawl_netease_pv` | 移动端静态 HTML；iPhone UA；知光谷频道更新慢约 2 周 |
| cnnpn_domestic | 核电国内 | `https://www.cnnpn.cn/channel/1.html?&page=1` | `crawl_cnnpn` | `ul li` 结构，约一半文章无日期标签 |
| cnnpn_international | 核电国外 | `https://www.cnnpn.cn/channel/4.html` | `crawl_cnnpn` | 同上 |
| cpnn_energy | 新能源 | `https://cpnn.com.cn/news/xny/` | `crawl_cpnn` | 相对路径用 `resp.url` 做 base；日期从 URL `/YYYYMM/tYYYYMMDD_ID.html` 提取 |
| cpnn_tech | 综合科技 | `https://cpnn.com.cn/news/kj/` | `crawl_cpnn` | 同上 |
| sciencenet | 综合科技 | `https://news.sciencenet.cn/morenews-V-1.aspx` | `crawl_sciencenet` | 只抓相对路径链接；日期在父 `<tr>` 文本（格式 `2026/4/14 10:14:39`） |
| xinhua_tech | 综合科技 | `https://www.news.cn/tech/index.html` | `crawl_xinhua_tech` | 只保留 `/tech/YYYYMMDD/hash/c.html` 格式；日期从 URL 提取 |
| inen_solar | 光伏 | `https://solar.in-en.com/news/` | `crawl_inen_solar` | 标题在 `<h5 a>`；日期为相对时间（X天前/X小时前），运行时实时计算 |
| renewablesnow | 新能源 | `https://renewablesnow.com/news/` | `crawl_renewablesnow` | React 渲染；标题从 `img alt` 提取；日期英文月份格式 |
| solarbe_tech | 光伏 | `https://news.solarbe.com/` | `crawl_solarbe` | URL 格式 `/YYYYMM/DD/ID.html`，日期从 URL 提取；日更约 100+ 篇 |
| tgs4c | 风电 | `https://www.tgs4c.com/news/` | `crawl_tgs4c` | 4C Offshore；URL 格式 `slug-nidXXXX.html`；日期格式 "DD Month YYYY" |
| china_nengyuan | 新能源 | `http://www.china-nengyuan.com/news/` | `crawl_china_nengyuan` | URL 格式 `/news/ID.html`；列表页无日期，全部 pass-through |

---

## 未能接入的来源（记录备查）

| 来源 | 问题 | 说明 |
|------|------|------|
| WeChat 公众号（7 个） | 需登录 | 中粉固态电池/风电世界/起点钠电/能源学人/钙钛矿工厂/钙钛矿学习xx平台/地热能在线 |
| esplaza.com.cn | Connection refused | 网站无法访问 |
| volta.foundation/battery-news | 月更 | 更新频率约每月一篇 |
| batterytechonline.com | HTTP 403 | 屏蔽爬虫；Google News RSS 覆盖不全 |
| supplychaindigital.com | HTTP 403 | 屏蔽爬虫；内容能源相关性低 |
| nachrichten.idw-online.de | 德语无 RSS | 无结构化 RSS |
| smartbrief BCI | 邮件通讯 | 无公开列表页 |
