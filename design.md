# �� 多源能源新闻抓取系统（简化版设计文档）

## 1. 项目目标

构建一个轻量级新闻抓取脚本，每天运行一次，从多个能源/科技网站抓取新闻，并输出为 CSV 文件。

抓取内容包括：

* 标题
* 来源站点
* 分类
* 发布时间（如有）
* 原文链接
* 正文（可选）

输出文件：

```
outputs/daily_news_YYYYMMDD.csv
```

---

## 2. 总体策略（核心思路）

系统采用**简单稳定优先策略**：

> RSS优先 → HTML列表页补充 → newspaper3k提正文（可选）

避免复杂工程（数据库 / Playwright / 分布式），确保：

* 可快速上线
* 易维护
* 易扩展

---

## 3. 数据源类型

### 3.1 RSS 源（优先）

适用于：

* 有 RSS feed 的网站

方式：

* 使用 `feedparser` 抓取

优点：

* 稳定
* 结构化好
* 开发成本低

风险：

* 部分站点可能被反爬（Cloudflare等）
* RSS偶尔失效

---

### 3.2 HTML 列表页

适用于：

* 无 RSS 的国内网站

方式：

* `requests + BeautifulSoup`

提取内容：

* 标题
* URL
* 时间（如果有）

特点：

* 每个网站需要单独解析规则
* 但稳定性较高

---

## 4. 抓取流程

### Step 1：读取 sites.yaml

```python
for site in sites:
    if site.type == "rss":
        crawl_rss(site)
    else:
        crawl_html(site)
```

---

### Step 2：抓取文章列表（Discovery）

#### 4.1 RSS 抓取

使用：

```python
feedparser.parse(site.rss_url)
```

提取字段：

* title
* link
* published

异常处理：

* RSS失败 → fallback到HTML（可选）

---

#### 4.2 HTML 抓取

使用：

```python
requests + BeautifulSoup
```

每个网站写独立函数，例如：

```python
def crawl_cnnpn():
def crawl_cpnn():
```

提取：

* title
* url
* publish_time（如有）

---

### Step 3：过滤“当天新闻”

规则：

```python
if publish_date == today:
    keep
```

特殊情况：

* 如果没有时间 → 默认保留（避免漏抓）

---

### Step 4：抓正文（可选）

使用：

```python
from newspaper import Article
```

流程：

```python
article = Article(url)
article.download()
article.parse()
content = article.text
```

异常处理：

* 失败 → content 为空
* 不影响整体流程

---

### Step 5：写入 CSV

使用：

```python
pandas.DataFrame.to_csv()
```

字段：

```
date
site
category
title
url
publish_time
content
```

---

## 5. 项目结构

```
carbon_spider/
├── configs/
│   └── sites.yaml
├── spiders/
│   ├── rss_spider.py
│   ├── html_spider.py
├── utils/
│   ├── time_parser.py
├── outputs/
│   └── daily_news_YYYYMMDD.csv
└── main.py
```

---

## 6. sites.yaml 说明

每个站点定义：

```
name: 唯一标识
category: 分类（电池/氢/光伏等）
home_url: 网站入口
rss_url: RSS地址（可选）
type: rss 或 html
```

---

## 7. 异常处理策略

### 7.1 RSS失败

处理方式：

* try/except
* 记录日志
* 可选 fallback 到 HTML

---

### 7.2 HTML解析失败

处理方式：

* 跳过该站点
* 不影响其他站点

---

### 7.3 正文抓取失败

处理方式：

* content设为空
* 记录失败即可

---

## 8. 不做的事情（当前阶段）

为了保持简单，本版本不做：

* ❌ Playwright（动态渲染）
* ❌ 数据库存储
* ❌ 多线程/分布式
* ❌ 复杂去重
* ❌ 登录抓取
* ❌ AI分类/分析

---

## 9. 后续扩展方向（可选）

当系统稳定后可以逐步增加：

* 增加 Playwright（处理反爬）
* 增加 SQLite/PostgreSQL
* 增加去重逻辑
* 增加自动摘要（LLM）
* 增加定时任务（cron / EC2）

---

## 10. 运行方式

每日执行：

```bash
python main.py
```

输出：

```
outputs/daily_news_YYYYMMDD.csv
```

---

## 11. 核心设计原则

1. 简单优先
2. 能跑优先
3. 出错不影响整体
4. 每个站点独立处理
5. 可逐步增强

---

## 12. 一句话总结

> 用最简单的方式，把几十个新闻源每天抓一遍，先跑起来，再逐步优化。

