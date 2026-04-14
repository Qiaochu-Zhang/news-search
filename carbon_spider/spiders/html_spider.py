"""
HTML 列表页抓取模块：使用 requests + BeautifulSoup 解析各国内新闻站点。
每个站点对应一个独立的解析函数，便于维护和扩展。
"""

import logging
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from utils.time_parser import parse_time

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15  # 秒

# ── 垃圾标题过滤 ────────────────────────────────────────────
# 导航栏目、品牌名、功能入口等不属于新闻正文的标题

_JUNK_TITLE_SET = frozenset({
    # 通用站点功能链接
    "广告服务", "版权声明", "我们的服务", "联系我们", "关于我们", "免责声明",
    "投稿须知", "招聘信息", "网站地图", "友情链接", "返回顶部", "返回首页", "首页",
    # 通用频道/栏目导航
    "电力", "新能源", "油气", "煤炭", "企业", "地方", "科技", "国际",
    "人事", "观点", "观察", "财经", "政策", "市场", "行情", "技术", "项目",
    # 国际能源网系列品牌导航
    "国际能源网", "国际新能源网", "国际太阳能光伏网", "国际电力网", "国际风电网",
    "国际储能网", "国际节能环保网", "国际煤炭网", "国际石油网", "国际燃气网",
    "国际氢能网", "国际充换电网",
    # 能源网服务入口
    "能源商城", "能直播", "能课堂", "能源商圈", "能源会展",
    # 光伏子栏目
    "光伏资讯", "光伏政策", "光伏人物", "光伏企业", "光伏产品", "光伏会展",
    "光伏统计", "光伏电池组件", "光伏系统工程", "光伏逆变器", "光伏原材料及辅料",
    "光伏零部件", "光热发电", "光伏设备", "分布式电站", "光伏财经", "光伏项目",
    "光伏行情", "光伏技术", "首页光伏资讯",
    # 英文导航 / 功能入口
    "Advanced search", "Sectors", "Regions", "Projects", "Companies",
    "Policy & Tenders", "Insights", "Events", "SUBSCRIBE", "Subscribe",
    "More about us", "Other corporate", "Company news",
    "Products technology", "Products & Technology",
    "Sign in", "Sign up", "Log in", "Register", "Search",
    "Home", "About", "Contact", "Advertise", "Newsletter",
    "Privacy Policy", "Terms of Use", "Cookie Policy",
})

# 正则模式：匹配复合导航路径或特定品牌格式
_JUNK_TITLE_PATTERNS = [
    re.compile(r"^首页\s*[>›/]"),            # "首页 > 光伏" 类面包屑
    re.compile(r"^国际[\u4e00-\u9fff]{2,6}网$"),  # 国际XXX网 品牌名
    re.compile(r"^(Advanced\s+search|Advanced Search)$", re.I),
]


def _is_junk_title(title: str) -> bool:
    """
    判断标题是否为导航栏目、品牌名、功能入口等非新闻内容。
    返回 True 表示应丢弃。
    """
    t = title.strip()
    if not t:
        return True
    # 极短标题：中文 ≤ 4 字或英文 ≤ 5 字，几乎不可能是真正的新闻标题
    if len(t) <= 4:
        return True
    if t in _JUNK_TITLE_SET:
        return True
    for pat in _JUNK_TITLE_PATTERNS:
        if pat.search(t):
            return True
    return False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 站点名称 → 解析函数映射
_REGISTRY: dict = {}


def register(name: str):
    """装饰器：将解析函数注册到 _REGISTRY。"""
    def decorator(fn):
        _REGISTRY[name] = fn
        return fn
    return decorator


def crawl_html(site: dict) -> list[dict]:
    """
    HTML 站点入口：根据 site['name'] 分发到对应解析函数。
    """
    name = site["name"]
    fn = _REGISTRY.get(name)
    if fn is None:
        logger.warning("[%s] 没有对应的 HTML 解析函数，跳过", name)
        return []

    logger.info("[%s] 抓取 HTML: %s", name, site["home_url"])
    try:
        articles = fn(site)
    except Exception as e:
        logger.error("[%s] HTML 抓取失败: %s", name, e)
        return []

    before = len(articles)
    articles = [a for a in articles if not _is_junk_title(a["title"])]
    dropped = before - len(articles)
    if dropped:
        logger.info("[%s] 过滤掉 %d 条垃圾标题（导航/栏目名等）", name, dropped)
    return articles


# ── 通用工具 ────────────────────────────────────────────────


def _get(url: str, **kwargs) -> Optional[requests.Response]:
    """带超时和异常处理的 GET 请求。"""
    try:
        resp = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            **kwargs,
        )
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp
    except requests.RequestException as e:
        logger.error("请求失败 [%s]: %s", url, e)
        return None


def _soup(resp: requests.Response) -> BeautifulSoup:
    return BeautifulSoup(resp.text, "html.parser")


def _make_article(
    site: dict,
    title: str,
    url: str,
    publish_time_str: Optional[str] = None,
) -> dict:
    return {
        "site": site["name"],
        "category": site.get("category", ""),
        "title": title.strip(),
        "url": url.strip(),
        "publish_time": parse_time(publish_time_str),
        "content": "",
    }


def _extract_date_from_text(text: str) -> Optional[str]:
    """从任意文本中提取日期片段（yyyy-mm-dd 或 yyyy年mm月dd日）。"""
    patterns = [
        r"\d{4}-\d{1,2}-\d{1,2}",
        r"\d{4}/\d{1,2}/\d{1,2}",
        r"\d{4}年\d{1,2}月\d{1,2}日",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(0)
    return None


# ── 各站点解析函数 ──────────────────────────────────────────


@register("cnnpn_domestic")
@register("cnnpn_international")
def crawl_cnnpn(site: dict) -> list[dict]:
    """
    中国核电信息网 (cnnpn.cn)
    列表页结构示例：
      <ul class="news-list">
        <li>
          <a href="/detail/xxxxx.html">标题</a>
          <span class="date">2024-04-12</span>
        </li>
      </ul>
    """
    resp = _get(site["home_url"])
    if resp is None:
        return []

    soup = _soup(resp)
    articles = []
    base = "https://www.cnnpn.cn"

    # 尝试常见列表结构
    for li in soup.select("ul.news-list li, .list-news li, .article-list li, li"):
        a = li.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = urljoin(base, a["href"])
        if not title or not href.startswith("http"):
            continue

        # 寻找日期
        date_tag = li.find(class_=re.compile(r"date|time|pub", re.I))
        date_str = date_tag.get_text(strip=True) if date_tag else None
        if not date_str:
            date_str = _extract_date_from_text(li.get_text())

        articles.append(_make_article(site, title, href, date_str))

    logger.info("[%s] 获取到 %d 篇文章", site["name"], len(articles))
    return articles


@register("cpnn_energy")
@register("cpnn_tech")
def crawl_cpnn(site: dict) -> list[dict]:
    """
    中国核能行业协会 (cpnn.com.cn)
    列表页结构示例：
      <div class="news-item">
        <a href="/news/xny/xxxxx.html">标题</a>
        <span class="date">2024-04-12</span>
      </div>
    """
    resp = _get(site["home_url"])
    if resp is None:
        return []

    soup = _soup(resp)
    base = "https://cpnn.com.cn"
    articles = []

    for item in soup.select(".news-item, .list-item, .article-item, li"):
        a = item.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = urljoin(base, a["href"])
        if not title or "cpnn.com.cn" not in href:
            continue

        date_tag = item.find(class_=re.compile(r"date|time|pub", re.I))
        date_str = date_tag.get_text(strip=True) if date_tag else None
        if not date_str:
            date_str = _extract_date_from_text(item.get_text())

        articles.append(_make_article(site, title, href, date_str))

    logger.info("[%s] 获取到 %d 篇文章", site["name"], len(articles))
    return articles


@register("sciencenet")
def crawl_sciencenet(site: dict) -> list[dict]:
    """
    科学网新闻 (news.sciencenet.cn)
    列表页结构示例：
      <div class="news-item">
        <a href="http://news.sciencenet.cn/htmlnews/...">标题</a>
        <span>2024-04-12</span>
      </div>
    """
    resp = _get(site["home_url"])
    if resp is None:
        return []

    soup = _soup(resp)
    articles = []

    for a in soup.find_all("a", href=re.compile(r"sciencenet\.cn/htmlnews/")):
        title = a.get_text(strip=True)
        href = a["href"]
        if not title:
            continue

        # 日期通常在同级或父级元素
        parent = a.parent
        date_str = _extract_date_from_text(parent.get_text() if parent else "")

        articles.append(_make_article(site, title, href, date_str))

    logger.info("[%s] 获取到 %d 篇文章", site["name"], len(articles))
    return articles


@register("xinhua_tech")
def crawl_xinhua_tech(site: dict) -> list[dict]:
    """
    新华网科技频道 (www.news.cn/tech)
    文章链接格式：/tech/YYYYMMDD/<hash>/c.html
    日期直接从 URL 路径中提取，不依赖页面文本。
    """
    resp = _get(site["home_url"])
    if resp is None:
        return []

    soup = _soup(resp)
    base = "https://www.news.cn"
    articles = []
    seen = set()

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]
        if not title or len(title) < 5:
            continue
        if not href.startswith("http"):
            href = urljoin(base, href)
        if href in seen:
            continue
        seen.add(href)

        # 从 URL 路径提取日期：/tech/20260413/<hash>/c.html
        m = re.search(r"/(\d{8})/", href)
        date_str = (
            f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}"
            if m else None
        )

        articles.append(_make_article(site, title, href, date_str))

    logger.info("[%s] 获取到 %d 篇文章", site["name"], len(articles))
    return articles


@register("netease_pv")
def crawl_netease_pv(site: dict) -> list[dict]:
    """
    网易号·知光谷（光伏）移动端列表页 (m.163.com)
    桌面版 JS 渲染无法直接解析；移动端为静态 HTML，结构清晰：
      <li class="single-picture-news js-click-news">
        <a href="//m.163.com/news/article/<ID>.html">
          <p class="news-title">标题</p>
          <div class="public-time font">2026-04-01</div>
        </a>
      </li>
    """
    mobile_headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    try:
        resp = requests.get(
            site["home_url"],
            headers=mobile_headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
    except requests.RequestException as e:
        logger.error("请求失败 [%s]: %s", site["home_url"], e)
        return []

    soup = _soup(resp)
    articles = []

    for li in soup.find_all("li", class_=re.compile(r"js-click-news")):
        a = li.find("a", href=True)
        if not a:
            continue

        title_tag = li.find("p", class_="news-title")
        title = title_tag.get_text(strip=True) if title_tag else a.get_text(strip=True)
        if not title:
            continue

        href = a["href"]
        if href.startswith("//"):
            href = "https:" + href
        elif not href.startswith("http"):
            href = "https://m.163.com" + href

        date_tag = li.find(class_=re.compile(r"public.?time|time|date", re.I))
        date_str = date_tag.get_text(strip=True) if date_tag else None

        articles.append(_make_article(site, title, href, date_str))

    logger.info("[%s] 获取到 %d 篇文章", site["name"], len(articles))
    return articles


@register("inen_solar")
def crawl_inen_solar(site: dict) -> list[dict]:
    """
    国际能源网-光伏 (solar.in-en.com)
    列表页示例：
      <ul class="news-list">
        <li><span class="date">04-12</span><a href="/xxxxx.html">标题</a></li>
      </ul>
    """
    resp = _get(site["home_url"])
    if resp is None:
        return []

    soup = _soup(resp)
    base = "https://solar.in-en.com"
    articles = []
    today_year = __import__("datetime").date.today().year

    # 文章链接格式：/html/solar-XXXXXX.html
    article_url_re = re.compile(r"/html/solar-\d+\.html$")

    for li in soup.find_all("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = urljoin(base, a["href"])
        # 只保留符合文章 URL 格式的链接，过滤首页/栏目/外站链接
        if not article_url_re.search(href):
            continue

        date_tag = li.find(class_=re.compile(r"date|time", re.I))
        raw_date = date_tag.get_text(strip=True) if date_tag else ""
        # 补全年份：如 "04-12" → "2024-04-12"
        if re.match(r"^\d{2}-\d{2}$", raw_date):
            raw_date = f"{today_year}-{raw_date}"

        articles.append(_make_article(site, title, href, raw_date or None))

    logger.info("[%s] 获取到 %d 篇文章", site["name"], len(articles))
    return articles


@register("renewablesnow")
def crawl_renewablesnow(site: dict) -> list[dict]:
    """
    RenewablesNow (renewablesnow.com)
    列表页示例：
      <article class="post">
        <h2><a href="https://renewablesnow.com/news/...">标题</a></h2>
        <time datetime="2024-04-12">April 12, 2024</time>
      </article>
    """
    resp = _get(site["home_url"])
    if resp is None:
        return []

    soup = _soup(resp)
    articles = []

    # 文章链接必须在 /news/ 路径下，排除 /sectors/ /companies/ /events/ 等导航页
    news_url_re = re.compile(r"renewablesnow\.com/news/[^/]+/?\s*$")

    for article in soup.find_all(["article", "div"], class_=re.compile(r"post|item|news", re.I)):
        a = article.find("a", href=news_url_re)
        if not a:
            continue

        title = a.get_text(strip=True)
        href = a["href"]
        if not title or not href.startswith("http"):
            continue

        time_tag = article.find("time")
        if time_tag:
            date_str = time_tag.get("datetime") or time_tag.get_text(strip=True)
        else:
            date_str = _extract_date_from_text(article.get_text())

        articles.append(_make_article(site, title, href, date_str))

    logger.info("[%s] 获取到 %d 篇文章", site["name"], len(articles))
    return articles
