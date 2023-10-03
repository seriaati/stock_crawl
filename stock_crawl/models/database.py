import typing

import pandas
from tortoise import fields
from tortoise.models import Model


class HistoryTrade(Model):
    date = fields.DateField()
    stock_id = fields.CharField(max_length=10)

    total_volume = fields.IntField()
    total_value = fields.IntField()

    open_price = fields.IntField()
    high_price = fields.IntField()
    low_price = fields.IntField()
    close_price = fields.IntField()

    class Meta:
        unique_together = ("date", "stock_id")

    @classmethod
    def parse_from_series(cls, series: pandas.Series) -> typing.Self:
        return cls(
            date=series["date"],
            stock_id=series["stock_id"],
            total_volume=series["Trading_Volume"],
            total_value=series["Trading_money"],
            open_price=series["open"],
            high_price=series["max"],
            low_price=series["min"],
            close_price=series["close"],
        )


class Stock(Model):
    id = fields.CharField(max_length=10, pk=True)
    name = fields.CharField(max_length=10)
