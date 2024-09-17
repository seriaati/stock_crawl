import asyncio
import datetime
from collections import defaultdict
from typing import Any, Literal

import aiohttp
from asyncache import cached
from bs4 import BeautifulSoup
from bs4.element import Tag
from cachetools import TTLCache
from fake_useragent import UserAgent

from .endpoints import (
    FUBON_MAIN_FORCE,
    FUBON_MAIN_FORCE_DATE,
    MONEYDJ_STOCK_CATEGORY,
    MOPS_NEWS,
    STOCK_API_HISTORY_TRADES,
    STOCK_API_STOCKS,
    TPEX_COMPANY_INFO,
    TPEX_DIVIDEND,
    TPEX_PUNISH,
    TWSE_COMPANY_INFO,
    TWSE_DIVIDEND,
    TWSE_PUNISH,
)
from .enums import RecentDay
from .models import BuySell, HistoryTrade, MainForce, News, PunishStock, Stock
from .utils import roc_to_western_date

__all__ = ("StockCrawl",)

ua = UserAgent()


class StockCrawl:
    def __init__(self, *, proxy: str | None = None) -> None:
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False), trust_env=True
        )
        self.proxy = proxy

    async def __aenter__(self) -> "StockCrawl":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def _request(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        return_type: Literal["json", "text"] = "json",
    ) -> Any:
        async with self.session.get(
            url, params=params, headers={"User-Agent": ua.random}, proxy=self.proxy
        ) as resp:
            if resp.status != 200:
                return None
            if return_type == "json":
                return await resp.json()
            return await resp.text(errors="replace")

    async def close(self) -> None:
        """
        Closes the aiohttp session.

        Returns:
            None
        """
        await self.session.close()

    async def fetch_stocks(self) -> list[Stock]:
        """
        從 Stock API 取得上市上櫃公司的股票代號與名稱

        回傳:
            list[Stock]: 上市上櫃公司的物件
        """
        data = await self._request(STOCK_API_STOCKS)
        return [Stock(**d) for d in data]

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=100))
    async def fetch_stock(self, stock_id_or_name: str) -> Stock | None:
        """
        從 Stock API 取得單個上市上櫃公司的股票代號與名稱

        參數:
            stock_id_or_name: 上市上櫃公司代號或名稱

        回傳:
            Stock | None: 上市上櫃公司的物件, 如果找不到則回傳 None
        """
        if stock_id_or_name.isdigit():
            data = await self._request(f"{STOCK_API_STOCKS}/{stock_id_or_name}")
        else:
            data = await self._request(
                STOCK_API_STOCKS, params={"name": stock_id_or_name}
            )
        if data is not None:
            return Stock(**data)
        return None

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_stock_ids(self, only_four_digits: bool = False) -> list[str]:
        """
        從 Stock API 取得上市上櫃公司的股票代號

        參數:
            only_four_digits: 是否只取四位數的股票代號, 預設為 False

        回傳:
            list[str]: 上市上櫃公司的股票代號
        """
        stocks = await self.fetch_stocks()
        return [
            stock.id for stock in stocks if not only_four_digits or len(stock.id) == 4
        ]

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=100))
    async def fetch_main_forces(
        self,
        id: str,
        date: datetime.date,
        *,
        recent_day: RecentDay = RecentDay.ONE,
        retry: int = 0,
    ) -> list[MainForce]:
        """
        從富邦 API 取得單個上市上櫃公司的主力進出明細

        參數:
            id: 上市上櫃公司代號

        回傳:
            list[MainForce]: 主力進出明細
        """
        if recent_day is RecentDay.ONE:
            url = FUBON_MAIN_FORCE_DATE.format(id=id, date=date.strftime("%Y-%m-%d"))
        else:
            url = FUBON_MAIN_FORCE.format(id=id, day=recent_day.value)

        try:
            data = await self._request(url, return_type="text")
        except aiohttp.ClientConnectionError as e:
            if retry > 5:
                raise e

            await asyncio.sleep(5 * (retry + 1))
            return await self.fetch_main_forces(
                id, date, recent_day=recent_day, retry=retry + 1
            )

        soup = BeautifulSoup(data, "lxml")
        rows = soup.find_all("tr")
        main_forces: list[MainForce] = []

        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 10:
                # 檢查第二個 <td> 是否為數字，如果不是數字，則跳過
                if not cells[1].text.strip().replace(",", "").isdigit():
                    continue

                cells_1 = cells[:5]
                main_forces.append(MainForce.parse(cells_1, is_buy_force=True))
                cells_2 = cells[5:]
                if not cells_2[1].text.strip().replace(",", "").isdigit():
                    continue
                main_forces.append(MainForce.parse(cells_2, is_buy_force=False))

        return main_forces

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=100))
    async def fetch_force_buy_sells(self, url: str) -> list[BuySell]:
        """
        從富邦 API 取得主力對於單個上市上櫃公司的進出明細表

        參數:
            url: 主力進出明細網址

        回傳:
            list[BuySell]: 主力進出明細表
        """
        data = await self._request(url, return_type="text")
        soup = BeautifulSoup(data, "lxml")
        rows = soup.find_all("tr")
        buy_sells: list[BuySell] = []

        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 5:
                # 檢查第二個 <td> 是否為數字，如果不是數字，則跳過
                if not cells[1].text.strip().replace(",", "").isdigit():
                    continue
                buy_sells.append(BuySell.parse(cells))

        return buy_sells

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_company_capitals(self) -> dict[str, int]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司的實收資本額

        回傳:
            dict[str, int]: 公司代號與實收資本額對應表
        """
        twse_data = await self._request(TWSE_COMPANY_INFO)
        twse_capital = {d["公司代號"]: int(d["實收資本額"]) for d in twse_data}

        tpex_data = await self._request(TPEX_COMPANY_INFO)
        tpex_capital = {
            d["SecuritiesCompanyCode"]: int(d["Paidin.Capital.NTDollars"])
            for d in tpex_data
        }
        return {**twse_capital, **tpex_capital}

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=100))
    async def fetch_history_trades(
        self, id: str, *, limit: int | None = None
    ) -> list[HistoryTrade]:
        """
        從 Stock API 取得上市上櫃公司的歷史交易資訊

        參數:
            id: 上市上櫃公司代號
            start: 起始日期
            end: 結束日期

        回傳:
            list[HistoryTrade]: 歷史交易資訊
        """
        data = await self._request(
            STOCK_API_HISTORY_TRADES.format(id=id),
            params={"limit": limit} if limit else None,
        )
        return [HistoryTrade(**d) for d in data]

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_dividend_days(self) -> dict[str, datetime.date]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司除權息日期

        回傳:
            dict[str, datetime.date]: 公司代號與除權息日期對應表
        """
        twse_data = await self._request(TWSE_DIVIDEND)
        tpex_data = await self._request(TPEX_DIVIDEND)
        twse_dividend_days = {
            d["Code"]: roc_to_western_date(d["Date"]) for d in twse_data
        }
        tpex_dividend_days = {
            d["SecuritiesCompanyCode"]: roc_to_western_date(
                d["ExRrightsExDividendDate"]
            )
            for d in tpex_data
        }
        return {**twse_dividend_days, **tpex_dividend_days}

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_stock_cat_map(self) -> dict[str, list[str]]:
        """
        從 MoneyDJ API 取得股票分類

        回傳:
            dict[str, list[str]]: 股票分類對應表, key 為股票代號, value 為股票分類
        """
        data = await self._request(MONEYDJ_STOCK_CATEGORY, return_type="text")
        soup = BeautifulSoup(data, "lxml")
        tables = soup.find_all("table")
        trs = tables[0].find_all("tr")
        tds = trs[0].find_all("td", {"width": "25%"})
        cat_url_map = {
            td.text: f"https://www.moneydj.com{td.a['href']}"
            for td in tds
            if td.text != "\xa0"
        }

        result: defaultdict[str, list[str]] = defaultdict(list)
        for cat, url in cat_url_map.items():
            async with self.session.get(url, headers={"User-Agent": ua.random}) as resp:
                data = await resp.text(errors="replace")
            soup = BeautifulSoup(data, "lxml")
            tables = soup.find_all("table")
            trs = tables[1].find_all("tr")
            for tr in trs:
                tds = tr.find_all("td")
                if len(tds) != 10:
                    continue
                stock_id = tds[0].text[:4]
                if not stock_id.isdigit():
                    continue
                result[stock_id].append(cat)

        return result

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_punish_stocks(self) -> list[PunishStock]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司的處置股票資訊

        回傳:
            list[PunishStock]: 處置股票
        """
        twse_data = await self._request(TWSE_PUNISH)
        tpex_data = await self._request(TPEX_PUNISH)
        twse_punish_stocks = [
            PunishStock(
                name=d["Name"],
                id=d["Code"],
                date=d["Date"],
            )
            for d in twse_data
        ]
        tpex_punish_stocks = [
            PunishStock(
                name=d["CompanyName"],
                id=d["SecuritiesCompanyCode"],
                date=d["Date"],
            )
            for d in tpex_data
        ]
        return twse_punish_stocks + tpex_punish_stocks

    async def fetch_news(self) -> list[News]:
        """
        取得上市公司與上櫃公司的每日重大訊息

        回傳:
            list[News]: 新聞
        """
        result: list[News] = []

        data = await self._request(MOPS_NEWS, return_type="text")
        soup = BeautifulSoup(data, "lxml")
        table = soup.find(
            "table", {"class": "hasBorder", "align": "center", "border": "1"}
        )
        if not isinstance(table, Tag):
            return result
        for row in table.find_all("tr")[1:]:
            cells = [cell.text.strip() for cell in row.find_all("td")]
            if len(cells) != 6:
                continue
            result.append(News.parse_from_cells(cells))

        return result

    async def fetch_most_recent_trade_day(self) -> datetime.date:
        """
        從 Stock API 取得最近的交易日

        回傳:
            datetime.date: 最近的交易日
        """
        history_trades = await self.fetch_history_trades("2330", limit=1)
        return history_trades[0].date

    async def fetch_stock_last_close_price(self, id: str) -> float:
        """
        從 Stock API 取得上市上櫃公司的最後收盤價

        參數:
            id: 上市上櫃公司代號

        回傳:
            float: 最後收盤價
        """
        history_trades = await self.fetch_history_trades(id, limit=1)
        return history_trades[0].close_price
