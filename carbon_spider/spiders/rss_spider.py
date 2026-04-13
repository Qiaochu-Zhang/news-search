"""
RSS 抓取模块：使用 feedparser 解析 RSS/Atom feed，提取文章列表。
"""

import logging
from typing import Optional

import feedparser

from utils.time_parser import parse_time

logger = logging.getLogger(__name__)

# 请求头，避免部分站点直接拒绝无 UA 的请求
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; CarbonSpider/1.0; +https://github.com/example)"
    )
}


def crawl_rss(site: dict) -> list[dict]:
    """
    抓取单个 RSS 站点，返回文章列表。
    每篇文章为 dict，包含：title / url / publish_time / site / category。
    """
    name = site["name"]
    rss_url = site.get("rss_url", "")
    category = site.get("category", "")

    if not rss_url:
        logger.warning("[%s] 没有 rss_url，跳过", name)
        return []

    logger.info("[%s] 抓取 RSS: %s", name, rss_url)

    try:
        feed = feedparser.parse(
            rss_url,
            request_headers=HEADERS,
            agent=HEADERS["User-Agent"],
        )
    except Exception as e:
        logger.error("[%s] RSS 请求异常: %s", name, e)
        return []

    if feed.bozo and feed.bozo_exception:
        # bozo=True 表示 feed 格式有问题，但通常还能提取到条目
        logger.warning("[%s] RSS 格式异常: %s", name, feed.bozo_exception)

    articles = []
    for entry in feed.entries:
        title = _get_field(entry, "title")
        url = _get_field(entry, "link")
        pub_raw = _get_published(entry)
        publish_time = parse_time(pub_raw)

        if not title or not url:
            continue

        articles.append(
            {
                "site": name,
                "category": category,
                "title": title.strip(),
                "url": url.strip(),
                "publish_time": publish_time,
                "content": "",
            }
        )

    logger.info("[%s] 获取到 %d 篇文章", name, len(articles))
    return articles


# ── 内部工具 ────────────────────────────────────────────────


def _get_field(entry, field: str) -> Optional[str]:
    return getattr(entry, field, None) or None


def _get_published(entry) -> Optional[str]:
    """尝试多个字段获取发布时间字符串。"""
    for attr in ("published", "updated", "created"):
        val = getattr(entry, attr, None)
        if val:
            return val
    # feedparser 有时把时间放在 published_parsed（struct_time），转回字符串
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            import time
            return time.strftime("%Y-%m-%d %H:%M:%S", parsed)
    return None
