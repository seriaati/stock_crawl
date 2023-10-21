import datetime
from typing import List

from bs4 import Tag
from pydantic import BaseModel, field_validator

from .utils import roc_to_western_date, str_to_float


class MainForce(BaseModel):
    """
    主力

    屬性:
        name: 卷商名稱
        buy: 買進
        sell: 賣出
        overbought: 買超/賣超
        proportion: 佔成交比重
        url: 主力進出明細網址
        is_buy_force: 是否為買超主力, False 則為賣超主力
    """

    name: str
    """卷商名稱"""
    buy: int
    """買進"""
    sell: int
    """賣出"""
    overbought: int
    """買超/賣超"""
    proportion: float
    """佔成交比重"""
    url: str
    """主力進出明細網址"""
    is_buy_force: bool
    """是否為買超主力, False 則為賣超主力"""

    @classmethod
    def parse(cls, cells: List[Tag], is_buy_force: bool) -> "MainForce":
        """解析 HTML 的 <td> 標籤"""
        return cls(
            name=cells[0].text,
            buy=int(cells[1].text.replace(",", "")),
            sell=int(cells[2].text.replace(",", "")),
            overbought=int(cells[3].text.replace(",", "")),
            proportion=str_to_float(cells[4].text.replace("%", "")),
            url=f"https://fubon-ebrokerdj.fbs.com.tw{cells[0].a['href']}",  # type: ignore
            is_buy_force=is_buy_force,
        )


class BuySell(BaseModel):
    """
    進出明細

    屬性:
        date: 日期
        buy: 買進(張)
        sell: 賣出(張)
        total: 買賣總額(張)
        overbought: 買賣超(張)
    """

    date: datetime.date
    """日期"""
    buy: int
    """買進(張)"""
    sell: int
    """賣出(張)"""
    total: int
    """買賣總額(張)"""
    overbought: int
    """買賣超(張)"""

    @classmethod
    def parse(cls, cells: List[Tag]) -> "BuySell":
        """解析 HTML 的 <td> 標籤"""
        return cls(
            date=datetime.datetime.strptime(cells[0].text, "%Y/%m/%d").date(),
            buy=int(cells[1].text.replace(",", "")),
            sell=int(cells[2].text.replace(",", "")),
            total=int(cells[3].text.replace(",", "")),
            overbought=int(cells[4].text.replace(",", "")),
        )


class PunishStock(BaseModel):
    """
    處置股

    屬性:
        name: 股票名稱
        id: 股票代號
        date: 股票公告遭處置日期
    """

    name: str
    """股票名稱"""
    id: str
    """股票代號"""
    date: datetime.date
    """股票公告遭處置日期"""

    @field_validator("date", mode="before")
    def _convert_date(cls, v: str) -> datetime.date:
        return roc_to_western_date(v)


class News(BaseModel):
    """
    新聞

    屬性:
        stock_id: 股票代號
        stock_name: 股票名稱
        title: 新聞標題
        date_time: 新聞發布時間
    """

    stock_id: str
    """股票代號"""
    stock_name: str
    """股票名稱"""
    title: str
    """新聞標題"""
    date_time: datetime.datetime
    """新聞發布時間"""

    @classmethod
    def parse_from_tds(cls, tds: List[Tag]) -> "News":
        """解析 HTML 的 <td> 標籤"""
        roc_date = tds[2].text
        western_date = roc_to_western_date(roc_date.replace("/", ""))
        time_ = tds[3].text
        return cls(
            stock_id=tds[0].text,
            stock_name=tds[1].text,
            title=tds[4].text.replace("\n", ""),
            date_time=datetime.datetime.combine(
                western_date, datetime.datetime.strptime(time_, "%H:%M:%S").time()
            ),
        )


class HistoryTrade(BaseModel):
    """
    歷史交易資料

    屬性:
        id: 交易序號
        date: 日期
        stock_id: 股票代號
        total_volume: 總成交量
        total_value: 總成交值
        open_price: 開盤價
        high_price: 最高價
        low_price: 最低價
        close_price: 收盤價
    """

    id: int
    """交易序號"""
    date: datetime.date
    """日期"""
    stock_id: str
    """股票代號"""
    total_volume: int
    """總成交量"""
    total_value: int
    """總成交值"""
    open_price: int
    """開盤價"""
    high_price: int
    """最高價"""
    low_price: int
    """最低價"""
    close_price: int
    """收盤價"""

    @field_validator("date", mode="before")
    def _convert_date(cls, v: str) -> datetime.date:
        return datetime.datetime.strptime(v, "%Y-%m-%d").date()


class Stock(BaseModel):
    """
    股票

    屬性:
        id: 股票代號
        name: 股票名稱
    """

    id: str
    """股票代號"""
    name: str
    """股票名稱"""
