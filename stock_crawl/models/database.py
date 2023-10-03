import typing

import pandas
from tortoise import fields
from tortoise.models import Model


class HistoryTrade(Model):
    date = fields.DateField()
    stock_id = fields.CharField(max_length=10)
    stock_name = fields.CharField(max_length=10)

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
            id=series["stock_id"],
            total_volume=series["Trading_Volume"],
            total_money=series["Trading_money"],
            opening_price=series["open"],
            highest_price=series["max"],
            lowest_price=series["min"],
            closing_price=series["close"],
        )


class Stock(Model):
    id = fields.CharField(max_length=10, pk=True)
    name = fields.CharField(max_length=10)
