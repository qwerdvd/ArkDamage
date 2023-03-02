import decimal
from typing import Any

decimal.getcontext().rounding = "ROUND_HALF_UP"


async def get_attribute(
        frames: dict | list[Any], level: decimal.Decimal, min_level: int, attr: str
) -> decimal.Decimal:
    level = decimal.Decimal(level)
    min_level = decimal.Decimal(min_level)
    ret = decimal.Decimal(level - min_level) / decimal.Decimal(
        frames[1].level - frames[0].level) * decimal.Decimal(
        frames[1].data.get(attr) - frames[0].data.get(attr)) + decimal.Decimal(frames[0].data.get(attr))
    # frames[1].data.'attr' - frames[0].data[attr]) + decimal.Decimal(frames[0].data[attr])
    if attr != "baseAttackTime":
        return decimal.Decimal(ret)
    else:
        return ret
