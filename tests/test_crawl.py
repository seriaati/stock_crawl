import datetime

import pytest

import stock_crawl


@pytest.mark.asyncio
async def test_fetch_stock_ids():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        stock_ids = await client.fetch_stock_ids()
        assert len(stock_ids) > 0
        assert isinstance(stock_ids[0], str)


@pytest.mark.asyncio
async def test_get_stock_name():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        stock_name = await client.get_stock_name("2330")
        assert stock_name == "台積電"


@pytest.mark.asyncio
async def test_fetch_main_forces():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        for recent_day in stock_crawl.RecentDay:
            main_forces = await client.fetch_main_forces("2330", recent_day)
            assert len(main_forces) > 0, recent_day


@pytest.mark.asyncio
async def test_fetch_force_buy_sells():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        force_buy_sells = await client.fetch_force_buy_sells(
            "https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco0/zco0.djhtm?a=2330&b=9600&BHID=9600"
        )
        assert len(force_buy_sells) > 0


@pytest.mark.asyncio
async def test_fetch_company_capitals():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        company_capitals = await client.fetch_company_capitals()
        assert len(company_capitals) > 0


@pytest.mark.asyncio
async def test_fetch_history_trades():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        history_trades = await client.fetch_history_trades(
            "2330", datetime.date(2021, 1, 1), datetime.date(2021, 1, 31)
        )
        assert len(history_trades) > 0


@pytest.mark.asyncio
async def test_fetch_dividend_days():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        dividend_days = await client.fetch_dividend_days()
        assert len(dividend_days) > 0


@pytest.mark.asyncio
async def test_fetch_punish_stocks():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        punish_stocks = await client.fetch_punish_stocks()
        assert len(punish_stocks) > 0


@pytest.mark.asyncio
async def test_fetch_news():
    async with stock_crawl.StockCrawl(use_cache=False) as client:
        news = await client.fetch_news()
        assert len(news) > 0
