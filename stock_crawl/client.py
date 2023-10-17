import asyncio
import datetime
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional

import aiohttp
from asyncache import cached
from bs4 import BeautifulSoup
from cachetools import TTLCache
from fake_useragent import UserAgent

from .endpoints import *
from .enums import RecentDay
from .models import BuySell, HistoryTrade, MainForce, News, PunishStock, Stock
from .utils import roc_to_western_date

ua = UserAgent()


class StockCrawl:
    def __init__(self) -> None:
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            trust_env=True,
        )

    async def close(self) -> None:
        """
        Closes the aiohttp session.

        Returns:
            None
        """
        await self.session.close()

    async def fetch_stocks(self) -> List[Stock]:
        """
        從 Stock API 取得上市上櫃公司的股票代號與名稱

        回傳:
            List[Stock]: 上市上櫃公司的物件
        """
        async with self.session.get(
            STOCK_API_STOCKS, headers={"User-Agent": ua.random}
        ) as resp:
            data = await resp.json()
        return [Stock(**d) for d in data]

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=100))
    async def fetch_stock(self, stock_id_or_name: str) -> Optional[Stock]:
        """
        從 Stock API 取得單個上市上櫃公司的股票代號與名稱

        參數:
            stock_id_or_name: 上市上櫃公司代號或名稱

        回傳:
            Stock: 上市上櫃公司的物件
        """
        if stock_id_or_name.isdigit():
            async with self.session.get(
                f"{STOCK_API_STOCKS}/{stock_id_or_name}",
                headers={"User-Agent": ua.random},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        else:
            async with self.session.get(
                STOCK_API_STOCKS,
                headers={"User-Agent": ua.random},
                params={"name": stock_id_or_name},
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        return Stock(**data)

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_stock_ids(self, only_four_digits: bool = False) -> List[str]:
        """
        從 Stock API 取得上市上櫃公司的股票代號

        參數:
            only_four_digits: 是否只取四位數的股票代號, 預設為 False

        回傳:
            List[str]: 上市上櫃公司的股票代號
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
    ) -> List[MainForce]:
        """
        從富邦 API 取得單個上市上櫃公司的主力進出明細

        參數:
            id: 上市上櫃公司代號

        回傳:
            List[MainForce]: 主力進出明細
        """
        if recent_day is RecentDay.ONE:
            url = FUBON_MAIN_FORCE_DATE.format(id=id, date=date.strftime("%Y-%m-%d"))
        else:
            url = FUBON_MAIN_FORCE.format(id=id, day=recent_day.value)

        try:
            async with self.session.get(url, headers={"User-Agent": ua.random}) as resp:
                data = await resp.text(errors="replace")
        except aiohttp.ClientConnectionError as e:
            if retry > 5:
                raise e

            await asyncio.sleep(5 * (retry + 1))
            return await self.fetch_main_forces(
                id, date, recent_day=recent_day, retry=retry + 1
            )

        soup = BeautifulSoup(data, "lxml")
        rows = soup.find_all("tr")
        main_forces: List[MainForce] = []

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
    async def fetch_force_buy_sells(self, url: str) -> List[BuySell]:
        """
        從富邦 API 取得主力對於單個上市上櫃公司的進出明細表

        參數:
            url: 主力進出明細網址

        回傳:
            List[BuySell]: 主力進出明細表
        """
        async with self.session.get(url, headers={"User-Agent": ua.random}) as resp:
            data = await resp.text(errors="replace")

        soup = BeautifulSoup(data, "lxml")
        rows = soup.find_all("tr")
        buy_sells: List[BuySell] = []

        for row in rows:
            cells = row.find_all("td")
            if len(cells) == 5:
                # 檢查第二個 <td> 是否為數字，如果不是數字，則跳過
                if not cells[1].text.strip().replace(",", "").isdigit():
                    continue
                buy_sells.append(BuySell.parse(cells))

        return buy_sells

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_company_capitals(self) -> Dict[str, int]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司的實收資本額

        回傳:
            Dict[str, int]: 公司代號與實收資本額對應表
        """
        async with self.session.get(
            TWSE_COMPANY_INFO, headers={"User-Agent": ua.random}
        ) as resp:
            twse_data = await resp.json()
        async with self.session.get(
            TPEX_COMPANY_INFO, headers={"User-Agent": ua.random}
        ) as resp:
            tpex_data = await resp.json()

        twse_capital = {d["公司代號"]: int(d["實收資本額"]) for d in twse_data}
        tpex_capital = {
            d["SecuritiesCompanyCode"]: int(d["Paidin.Capital.NTDollars"])
            for d in tpex_data
        }
        return {**twse_capital, **tpex_capital}

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=100))
    async def fetch_history_trades(
        self, id: str, *, limit: Optional[int] = None
    ) -> List[HistoryTrade]:
        """
        從 Stock API 取得上市上櫃公司的歷史交易資訊

        參數:
            id: 上市上櫃公司代號
            start: 起始日期
            end: 結束日期

        回傳:
            List[HistoryTrade]: 歷史交易資訊
        """
        async with self.session.get(
            STOCK_API_HISTORY_TRADES.format(id=id),
            params={"limit": limit} if limit else None,
            headers={"User-Agent": ua.random},
        ) as resp:
            return [HistoryTrade(**d) for d in await resp.json()]

    @cached(TTLCache(ttl=60 * 60 * 24, maxsize=1))
    async def fetch_dividend_days(self) -> Dict[str, datetime.date]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司除權息日期

        回傳:
            Dict[str, datetime.date]: 公司代號與除權息日期對應表
        """
        async with self.session.get(
            TWSE_DIVIDEND, headers={"User-Agent": ua.random}
        ) as resp:
            twse_data = await resp.json()
        async with self.session.get(
            TPEX_DIVIDEND, headers={"User-Agent": ua.random}
        ) as resp:
            tpex_data = await resp.json()

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
    async def fetch_stock_cat_map(self) -> Dict[str, List[str]]:
        """
        從 MoneyDJ API 取得股票分類

        回傳:
            Dict[str, List[str]]: 股票分類對應表, key 為股票代號, value 為股票分類
        """
        async with self.session.get(
            MONEYDJ_STOCK_CATEGORY, headers={"User-Agent": ua.random}
        ) as resp:
            data = await resp.text(errors="replace")

        soup = BeautifulSoup(data, "lxml")
        tables = soup.find_all("table")
        trs = tables[0].find_all("tr")
        tds = trs[0].find_all("td", {"width": "25%"})
        cat_url_map = {
            td.text: f"https://www.moneydj.com{td.a['href']}"
            for td in tds
            if td.text != "\xa0"
        }

        result: DefaultDict[str, List[str]] = defaultdict(list)
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
    async def fetch_punish_stocks(self) -> List[PunishStock]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司的處置股票資訊

        回傳:
            List[PunishStock]: 處置股票
        """
        async with self.session.get(
            TWSE_PUNISH, headers={"User-Agent": ua.random}
        ) as resp:
            twse_data = await resp.json()
        async with self.session.get(
            TPEX_PUNISH, headers={"User-Agent": ua.random}
        ) as resp:
            tpex_data = await resp.json()

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

    async def fetch_news(self) -> List[News]:
        """
        從公開資訊觀測站取得最新的新聞

        回傳:
            List[News]: 新聞
        """
        async with self.session.get(
            TWSE_NEWS, headers={"User-Agent": ua.random}
        ) as resp:
            text = await resp.text(errors="replace")
        soup = BeautifulSoup(text, "lxml")

        result: List[News] = []
        for tr in soup.find_all("tr", {"class": ["even", "odd"]}):
            tds = tr.find_all("td")
            result.append(News.parse_from_tds(tds))

        return result

    async def fetch_most_recent_trade_day(self) -> datetime.date:
        """
        從 Stock API 取得最近的交易日

        回傳:
            datetime.date: 最近的交易日
        """
        history_trades = await self.fetch_history_trades("2330", limit=1)
        return history_trades[0].date
