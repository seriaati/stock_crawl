import asyncio
import copy
import datetime
import logging
import os
import pickle
import random
from collections import defaultdict
from typing import Any, DefaultDict, Dict, List

import aiohttp
from bs4 import BeautifulSoup
from FinMind.data import DataLoader as FinMindDataLoader
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError

from .constants import RANDOM_HEADERS, RANDOM_USER_AGENTS
from .endpoints import *
from .enums import RecentDay
from .models import BuySell, HistoryTrade, MainForce, News, PunishStock, Stock
from .utils import (
    bulk_update_or_create,
    get_today,
    get_trade_days,
    roc_to_western_date,
    update_or_create,
)

CACHE_DIR = "cache.pkl"


def cache_decorator(func):
    async def wrapper(self: "StockCrawl", *args, **kwargs):
        if not hasattr(self, "today"):
            return await func(self, *args, **kwargs)
        key = f"{func.__name__}_{args}_{kwargs}_{self.today}"
        if key in self.cache:
            logging.debug(f"Using cache for {key}")
            return self.cache[key]
        result = await func(self, *args, **kwargs)
        self.cache[key] = result
        logging.debug(f"Cached {key}")
        self.save_cache()
        return result

    return wrapper


class StockCrawl:
    def __init__(
        self,
        *,
        use_cache: bool = True,
    ) -> None:
        self.finmind = FinMindDataLoader()
        """FinMind API"""
        self.use_cache = use_cache
        """是否使用快取"""
        self.cache: Dict[str, Any] = {}
        """快取"""
        self.today: datetime.date
        """今天日期"""

    @staticmethod
    def _generate_random_header() -> Dict[str, str]:
        browser = random.choice(list(RANDOM_USER_AGENTS.keys()))
        user_agent = random.choice(RANDOM_USER_AGENTS[browser])
        header = copy.copy(random.choice(RANDOM_HEADERS))
        header["User-Agent"] = user_agent
        return header

    @property
    def session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            headers=self._generate_random_header(),
            connector=aiohttp.TCPConnector(verify_ssl=False),
        )

    def _load_cache(self) -> None:
        if not os.path.exists(CACHE_DIR):
            with open(CACHE_DIR, "wb") as f:
                pickle.dump({}, f)
        with open(CACHE_DIR, "rb") as f:
            self.cache = pickle.load(f)

    def save_cache(self) -> None:
        with open(CACHE_DIR, "wb") as f:
            pickle.dump(self.cache, f)

    def _delete_old_cache(self) -> None:
        recent_three_days = [
            str(self.today - datetime.timedelta(days=i)) for i in range(3)
        ]
        for key in list(self.cache.keys()):
            if not any((day in key for day in recent_three_days)):
                del self.cache[key]
        logging.debug(f"Cache size: {len(self.cache)}")
        self.save_cache()

    async def set_today(self) -> None:
        today = get_today()
        day_trades = await self.fetch_history_trades(
            "2330", today - datetime.timedelta(days=5), today, use_db=False
        )
        self.today = day_trades[-1].date
        logging.debug(f"Today's date is: {self.today}")

    async def start(self) -> None:
        if self.use_cache:
            self._load_cache()

        logging.debug("Initializing Tortoise ORM")
        await Tortoise.init(
            db_url="sqlite://stock_crawl.sqlite3",
            modules={"models": ["stock_crawl.models.database"]},
        )
        await Tortoise.generate_schemas()

        await self.set_today()
        self._delete_old_cache()

    async def close(self) -> None:
        await Tortoise.close_connections()

    async def fetch_stock_ids(self) -> List[str]:
        """
        取得上市公司代號與上櫃公司代號
        """
        stock_ids: List[str] = []
        async with self.session as session:
            async with session.get(TWSE_IDS) as resp:  # 取得所有上市公司代號
                data: List[Dict[str, str]] = await resp.json()
                for d in data:
                    if d["公司代號"].isdigit():
                        stock_id = d["公司代號"]
                        stock_ids.append(stock_id)
                        await update_or_create(Stock(id=stock_id, name=d["公司簡稱"]))

            async with session.get(TPEX_IDS) as resp:  # 取得所有上櫃公司代號
                data: List[Dict[str, str]] = await resp.json()
                for d in data:
                    if d["SecuritiesCompanyCode"].isdigit():
                        stock_id = d["SecuritiesCompanyCode"]
                        stock_ids.append(stock_id)
                        await update_or_create(
                            Stock(id=stock_id, name=d["CompanyName"])
                        )

        return stock_ids

    @cache_decorator
    async def get_stock_name(self, id: str) -> str:
        """
        取得股票名稱
        """
        stock = await Stock.get_or_none(id=id)
        if stock is None:
            await self.fetch_stock_ids()
            stock = await Stock.get(id=id)
        return stock.name

    @cache_decorator
    async def fetch_main_forces(
        self, id: str, day: RecentDay = RecentDay.ONE, retry: int = 0
    ) -> List[MainForce]:
        """
        從富邦 API 取得單個上市上櫃公司的主力進出明細

        參數:
            id: 上市上櫃公司代號

        回傳:
            List[MainForce]: 主力進出明細
        """
        if day is RecentDay.ONE:
            url = FUBON_MAIN_FORCE_DATE.format(
                id=id, date=self.today.strftime("%Y-%m-%d")
            )
        else:
            url = FUBON_MAIN_FORCE.format(id=id, day=day.value)
        async with self.session as session:
            try:
                async with session.get(url) as resp:
                    data = await resp.text(errors="replace")
            except aiohttp.ClientConnectionError as e:
                if retry > 5:
                    raise e

                await asyncio.sleep(5 * (retry + 1))
                return await self.fetch_main_forces(id, day, retry + 1)

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

    @cache_decorator
    async def fetch_force_buy_sells(self, url: str) -> List[BuySell]:
        """
        從富邦 API 取得主力對於單個上市上櫃公司的進出明細表

        參數:
            url: 主力進出明細網址

        回傳:
            List[BuySell]: 主力進出明細表
        """
        async with self.session as session:
            async with session.get(url) as resp:
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

    @cache_decorator
    async def fetch_company_capitals(self) -> Dict[str, int]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司的實收資本額

        回傳:
            Dict[str, int]: 公司代號與實收資本額對應表
        """
        async with self.session as session:
            async with session.get(TWSE_COMPANY_INFO) as resp:
                twse_data = await resp.json()
            async with session.get(TPEX_COMPANY_INFO) as resp:
                tpex_data = await resp.json()

        twse_capital = {d["公司代號"]: int(d["實收資本額"]) for d in twse_data}
        tpex_capital = {
            d["SecuritiesCompanyCode"]: int(d["Paidin.Capital.NTDollars"])
            for d in tpex_data
        }
        return {**twse_capital, **tpex_capital}

    async def fetch_history_trades(
        self, id: str, start: datetime.date, end: datetime.date, *, use_db: bool = True
    ) -> List[HistoryTrade]:
        """
        從 FinMind API 取得上市上櫃公司的歷史交易資訊

        參數:
            id: 上市上櫃公司代號
            start: 起始日期
            end: 結束日期

        回傳:
            List[HistoryTrade]: 歷史交易資訊
        """
        if use_db:
            logging.debug("Getting trade data from db")
            # obtain histroy trades from db that is between start and end date and has the id id
            db_trades = await HistoryTrade.filter(
                date__gte=start, date__lte=end, stock_id=id
            ).all()

            # check if the trade data is complete
            if len(db_trades) == len(await get_trade_days()):
                logging.debug(f"Got {len(db_trades)} trade data from db")
                return db_trades

        # not complete, fetch from FinMind
        logging.debug("Fetching trade data from FinMind")
        trades = await asyncio.to_thread(self._fetch_day_trades, id, start, end)
        await bulk_update_or_create(trades)

        logging.debug(f"Saved {len(trades)} trade data to db")
        return trades

    def _fetch_day_trades(
        self, id: str, start: datetime.date, end: datetime.date
    ) -> List[HistoryTrade]:
        df = self.finmind.taiwan_stock_daily(
            id, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
        )
        stock_prices: List[HistoryTrade] = []
        for _, row in df.iterrows():
            stock_price = HistoryTrade.parse_from_series(row)
            stock_prices.append(stock_price)
        return stock_prices

    @cache_decorator
    async def fetch_dividend_days(self) -> Dict[str, datetime.date]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司除權息日期

        回傳:
            Dict[str, datetime.date]: 公司代號與除權息日期對應表
        """
        async with self.session as session:
            async with session.get(TWSE_DIVIDEND) as resp:
                twse_data = await resp.json()
            async with session.get(TPEX_DIVIDEND) as resp:
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

    @cache_decorator
    async def fetch_stock_cat_map(self) -> Dict[str, List[str]]:
        """
        從 MoneyDJ API 取得股票分類

        回傳:
            Dict[str, List[str]]: 股票分類對應表, key 為股票代號, value 為股票分類
        """
        async with self.session as session:
            async with session.get(MONEYDJ_STOCK_CATEGORY) as resp:
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
            async with self.session as session:
                async with session.get(url) as resp:
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

    @cache_decorator
    async def fetch_punish_stocks(self) -> List[PunishStock]:
        """
        從 TWSE API 與 TPEX API 取得上市公司與上櫃公司的處置股票資訊

        回傳:
            List[PunishStock]: 處置股票
        """
        async with self.session as session:
            async with session.get(TWSE_PUNISH) as resp:
                twse_data = await resp.json()
            async with session.get(TPEX_PUNISH) as resp:
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
        async with self.session as session:
            async with session.get(TWSE_NEWS) as resp:
                text = await resp.text(errors="replace")
        soup = BeautifulSoup(text, "lxml")

        result: List[News] = []
        for tr in soup.find_all("tr", {"class": ["even", "odd"]}):
            tds = tr.find_all("td")
            result.append(News.parse_from_tds(tds))

        return result
