import datetime
from typing import List, Sequence

from tortoise.backends.base.client import BaseDBAsyncClient
from tortoise.exceptions import IntegrityError
from tortoise.models import Model as TortoiseModel

from .models.database import HistoryTrade


def roc_to_western_date(roc_date_str: str) -> datetime.date:
    """將民國年轉換成西元年"""
    # format: 1100101
    year = roc_date_str[:3]
    month = roc_date_str[3:5]
    day = roc_date_str[5:]
    return datetime.date(int(year) + 1911, int(month), int(day))


def str_to_float(s: str) -> float:
    try:
        return float(s)
    except ValueError:
        return 0.0


def get_now() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8)))


def get_today() -> datetime.date:
    return get_now().date()


async def get_trade_days() -> List[datetime.date]:
    # get all histroy trades that has distinct date
    trades = await HistoryTrade.all().distinct().values("date")
    return [trade["date"] for trade in trades]


async def is_in_trade_days(date: datetime.date) -> bool:
    return date in await get_trade_days()


async def update_or_create(obj: TortoiseModel, conn: BaseDBAsyncClient) -> None:
    try:
        await obj.save(using_db=conn)
    except IntegrityError:
        pass


async def bulk_update_or_create(
    objs: Sequence[TortoiseModel], conn: BaseDBAsyncClient
) -> None:
    for obj in objs:
        await update_or_create(obj, conn)
