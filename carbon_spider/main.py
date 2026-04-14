"""
主入口：每日执行一次，抓取所有能源新闻并输出 CSV。

用法：
    python main.py [--no-content] [--all-dates]

选项：
    --no-content   跳过正文抓取（newspaper3k），加快速度
    --all-dates    不过滤日期，保留所有抓到的文章
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

# 将项目根目录加入 sys.path，使 spiders/utils 可以直接 import
sys.path.insert(0, str(Path(__file__).parent))

from spiders.rss_spider import crawl_rss
from spiders.html_spider import crawl_html
from utils.time_parser import is_yesterday

# ── 日志配置 ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ── 路径常量 ────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SITES_YAML = BASE_DIR / "configs" / "sites.yaml"
OUTPUTS_DIR = BASE_DIR / "outputs"

CSV_COLUMNS = ["date", "site", "category", "title", "url", "publish_time", "content"]


# ── 正文抓取（可选）────────────────────────────────────────


def fetch_content(url: str) -> str:
    """使用 newspaper3k 抓取文章正文，失败返回空字符串。"""
    try:
        from newspaper import Article

        article = Article(url)
        article.download()
        article.parse()
        return article.text or ""
    except Exception as e:
        logger.debug("正文抓取失败 [%s]: %s", url, e)
        return ""


# ── 主流程 ──────────────────────────────────────────────────


def load_sites(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("sites", [])


def run(fetch_body: bool = False, all_dates: bool = False) -> Path:
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    yesterday = now - timedelta(days=1)
    # 文件以新闻日期（昨天）命名，方便归档查阅
    date_str = yesterday.strftime("%Y%m%d")

    logger.info("====== 开始抓取 %s（昨日新闻）======", date_str)

    sites = load_sites(SITES_YAML)
    all_articles: list[dict] = []

    for site in sites:
        site_type = site.get("type", "rss")
        if site_type == "rss":
            articles = crawl_rss(site)
        else:
            articles = crawl_html(site)

        # 日期过滤：保留昨天的文章（无日期的也保留，避免漏抓）
        if not all_dates:
            articles = [a for a in articles if is_yesterday(a["publish_time"], now)]

        all_articles.extend(articles)

    logger.info("共抓取 %d 篇文章（过滤后）", len(all_articles))

    # 可选：抓取正文
    if fetch_body and all_articles:
        logger.info("开始抓取正文（共 %d 篇）…", len(all_articles))
        for i, art in enumerate(all_articles, 1):
            logger.info("  [%d/%d] %s", i, len(all_articles), art["url"])
            art["content"] = fetch_content(art["url"])

    # 构建 DataFrame
    rows = []
    for art in all_articles:
        pub = art["publish_time"]
        rows.append(
            {
                "date": date_str,
                "site": art["site"],
                "category": art["category"],
                "title": art["title"],
                "url": art["url"],
                "publish_time": pub.strftime("%Y-%m-%d %H:%M:%S") if pub else "",
                "content": art.get("content", ""),
            }
        )

    df = pd.DataFrame(rows, columns=CSV_COLUMNS)

    # 输出 CSV
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUTS_DIR / f"daily_news_{date_str}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    logger.info("====== 完成！输出文件：%s  共 %d 条 ======", out_path, len(df))
    return out_path


# ── CLI 入口 ─────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="能源新闻每日抓取脚本")
    parser.add_argument(
        "--no-content",
        action="store_true",
        help="跳过正文抓取（newspaper3k），速度更快",
    )
    parser.add_argument(
        "--all-dates",
        action="store_true",
        help="不过滤日期，保留所有抓到的文章",
    )
    args = parser.parse_args()

    run(fetch_body=not args.no_content, all_dates=args.all_dates)


if __name__ == "__main__":
    main()
