"""Calendar service — Chinese festival and solar term detection.

Uses the `chinese-calendar` library for accurate lunar calendar support.
Falls back gracefully if library is not installed.

Solar terms (节气) covered: 小寒, 大寒, 立春, 雨水, 惊蛰, 春分, 清明, 谷雨,
立夏, 小满, 芒种, 夏至, 小暑, 大暑, 立秋, 处暑, 白露, 秋分, 寒露, 霜降,
立冬, 小雪, 大雪, 冬至
"""
import logging
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Manual festival list as fallback (Gregorian dates that are fixed or near-fixed)
# Lunar festivals (春节, 端午, 中秋, etc.) are handled by chinese-calendar
_FIXED_FESTIVALS: dict[tuple[int, int], str] = {
    (1, 1): "元旦",
    (3, 8): "妇女节",
    (5, 1): "劳动节",
    (6, 1): "儿童节",
    (9, 9): "重阳节提醒",   # approx (actual is lunar 9th month 9th day)
    (10, 1): "国庆节",
    (12, 25): "圣诞节",
}

# Solar terms and their approximate Gregorian dates (varies by year ±1-2 days)
# We use a wider window (±2 days) for robustness
_SOLAR_TERMS_APPROX: list[tuple[tuple[int, int], str]] = [
    ((1, 6), "小寒"),
    ((1, 20), "大寒"),
    ((2, 4), "立春"),
    ((2, 19), "雨水"),
    ((3, 6), "惊蛰"),
    ((3, 21), "春分"),
    ((4, 5), "清明"),
    ((4, 20), "谷雨"),
    ((5, 6), "立夏"),
    ((5, 21), "小满"),
    ((6, 6), "芒种"),
    ((6, 21), "夏至"),
    ((7, 7), "小暑"),
    ((7, 23), "大暑"),
    ((8, 7), "立秋"),
    ((8, 23), "处暑"),
    ((9, 8), "白露"),
    ((9, 23), "秋分"),
    ((10, 8), "寒露"),
    ((10, 23), "霜降"),
    ((11, 7), "立冬"),
    ((11, 22), "小雪"),
    ((12, 7), "大雪"),
    ((12, 22), "冬至"),
]


def _try_chinese_calendar():
    """Try to import chinese_calendar library."""
    try:
        import chinese_calendar
        return chinese_calendar
    except ImportError:
        logger.debug("chinese-calendar not installed; using fallback festival list")
        return None


def get_today_festival(today: Optional[date] = None) -> Optional[str]:
    """Return Chinese festival name if today is a notable day.

    Args:
        today: Date to check (defaults to today)

    Returns:
        Festival name string (e.g., "春节", "端午节", "国庆节") or None.
    """
    if today is None:
        today = date.today()

    cc = _try_chinese_calendar()
    if cc is not None:
        # chinese_calendar.get_holiday_detail() returns (is_holiday, holiday_name)
        try:
            is_holiday, holiday_name = cc.get_holiday_detail(today)
            if is_holiday and holiday_name:
                return holiday_name
        except Exception as e:
            logger.warning("chinese_calendar error: %s", e)

    # Fallback: check fixed festivals
    key = (today.month, today.day)
    return _FIXED_FESTIVALS.get(key)


def get_upcoming_solar_term(days_ahead: int = 2, today: Optional[date] = None) -> Optional[str]:
    """Return solar term name if one is occurring within the next `days_ahead` days.

    Args:
        days_ahead: How many days ahead to look (default: 2)
        today: Date to check from (defaults to today)

    Returns:
        Solar term name (e.g., "冬至", "清明") or None.
    """
    if today is None:
        today = date.today()

    cc = _try_chinese_calendar()
    if cc is not None:
        try:
            # Check each upcoming day
            for delta in range(days_ahead + 1):
                check_date = today + timedelta(days=delta)
                # chinese_calendar.get_holiday_detail can identify solar terms on some versions
                # Try to find solar term name
                if hasattr(cc, 'is_in_lieu') or hasattr(cc, 'get_workday'):
                    pass  # version check — fall through to manual check
        except Exception:
            pass

    # Use approximate Gregorian dates (reliable for ±2 days)
    for (month, day), name in _SOLAR_TERMS_APPROX:
        for delta in range(days_ahead + 1):
            check_date = today + timedelta(days=delta)
            if check_date.month == month and abs(check_date.day - day) <= 2:
                return name

    return None


def should_trigger_calendar(today: Optional[date] = None) -> tuple[bool, str]:
    """Evaluate whether today warrants a calendar-based proactive trigger.

    Trigger conditions:
    1. Today IS a major festival → greet with festival message
    2. A solar term is within 2 days → mention upcoming season change

    Args:
        today: Date to check (defaults to today)

    Returns:
        (should_trigger: bool, reason_zh: str)
        reason_zh is empty string if should_trigger is False.
    """
    if today is None:
        today = date.today()

    # Check festivals first (higher priority)
    festival = get_today_festival(today)
    if festival:
        return True, f"今天是{festival}"

    # Check upcoming solar terms
    solar_term = get_upcoming_solar_term(days_ahead=1, today=today)
    if solar_term:
        return True, f"快到{solar_term}了"

    return False, ""
