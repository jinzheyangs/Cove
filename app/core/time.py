"""统一的业务日期口径。

全站按北京时间切天，避免 UTC 导致早上 8 点才换日。
需要“今天”的地方都应从这里取，不要各自写 datetime.now()。
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")


def today() -> date:
    """按北京时间取今天的日期。"""
    return datetime.now(TZ).date()
