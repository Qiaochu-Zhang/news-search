"""
时间解析工具：将各种格式的时间字符串统一解析为 datetime 对象。
"""

import re
import logging
from datetime import datetime, timezone
from typing import Optional

import dateutil.parser

logger = logging.getLogger(__name__)

# 中文月份映射
CN_MONTH_MAP = {
    "一月": 1, "二月": 2, "三月": 3, "四月": 4,
    "五月": 5, "六月": 6, "七月": 7, "八月": 8,
    "九月": 9, "十月": 10, "十一月": 11, "十二月": 12,
}

# 常见中文日期格式：2024年04月12日、2024-04-12、2024/04/12
CN_DATE_PATTERNS = [
    r"(\d{4})年(\d{1,2})月(\d{1,2})日",
    r"(\d{4})-(\d{1,2})-(\d{1,2})",
    r"(\d{4})/(\d{1,2})/(\d{1,2})",
    r"(\d{4})\.(\d{1,2})\.(\d{1,2})",
]


def parse_time(time_str: Optional[str]) -> Optional[datetime]:
    """
    尝试解析时间字符串，返回 datetime（带 UTC 时区）或 None。
    """
    if not time_str:
        return None

    time_str = time_str.strip()

    # 尝试中文日期格式
    for pattern in CN_DATE_PATTERNS:
        m = re.search(pattern, time_str)
        if m:
            try:
                year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return datetime(year, month, day, tzinfo=timezone.utc)
            except ValueError:
                pass

    # 尝试 dateutil 通用解析（处理 RSS 里的 RFC 2822 等格式）
    try:
        dt = dateutil.parser.parse(time_str, fuzzy=True)
        # 如果没有时区信息，假设 UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass

    logger.debug("无法解析时间：%s", time_str)
    return None


def is_today(dt: Optional[datetime], today: Optional[datetime] = None) -> bool:
    """
    判断 datetime 是否为今天（按 UTC 日期比较）。
    dt 为 None 时返回 True（不过滤无时间文章）。
    """
    if dt is None:
        return True
    if today is None:
        today = datetime.now(timezone.utc)
    return dt.date() == today.date()
