import datetime
from typing import List

from bs4 import Tag
from pandas import Series
from pydantic import BaseModel, validator

from ..utils import roc_to_western_date, str_to_float


class MainForce(BaseModel):
    """主力"""

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

    def __str__(self) -> str:
        return f"{self.name} 買進: {self.buy} 賣出: {self.sell} 買超: {self.overbought} 佔成交比重: {self.proportion}%"

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

    def __str__(self) -> str:
        return f"{self.date} 買進: {self.buy} 賣出: {self.sell} 買賣總額: {self.total} 買賣超: {self.overbought}"

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


class RecommendStock(BaseModel):
    """推薦股票"""

    id: str
    """股票代號"""
    name: str
    """股票名稱"""
    closing_price: float
    """收盤價"""
    strongest_buy: str
    """最強買進主力"""
    date: datetime.date
    """日期"""


class ForceSubscribe(BaseModel):
    """訂閱主力買賣情況"""

    force_name: str
    """卷商名稱"""
    force_url: str
    """主力進出明細網址"""
    stock_name: str
    """股票名稱"""
    stock_id: str
    """股票代號"""


class TradeLog(BaseModel):
    """交易紀錄"""

    stock_id: str
    """股票代號"""
    stock_name: str
    """股票名稱"""
    price: float
    """價格"""
    quantity: int
    """張數"""
    is_buy: bool
    """是否為買進, false 則為賣出"""
    date: datetime.date
    """日期"""

    @validator("is_buy", pre=True)
    def _convert_is_buy(cls, v: int) -> bool:
        return bool(v)

    @validator("date", pre=True)
    def _convert_date(cls, v: str) -> datetime.date:
        return datetime.datetime.strptime(v, "%Y-%m-%d").date()


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

    @validator("date", pre=True)
    def _convert_date(cls, v: str) -> datetime.date:
        return roc_to_western_date(v)


class News(BaseModel):
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
            title=tds[4].text,
            date_time=datetime.datetime.combine(
                western_date, datetime.datetime.strptime(time_, "%H:%M:%S").time()
            ),
        )
