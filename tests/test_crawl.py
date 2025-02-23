import datetime

import pytest

import stock_crawl


@pytest.mark.asyncio
async def test_fetch_stocks() -> None:
    async with stock_crawl.StockCrawl() as client:
        stocks = await client.fetch_stocks()
        assert len(stocks) > 0


@pytest.mark.asyncio
async def test_fetch_main_forces() -> None:
    async with stock_crawl.StockCrawl() as client:
        for recent_day in stock_crawl.RecentDay:
            main_forces = await client.fetch_main_forces(
                "2330", datetime.date(2023, 10, 4), recent_day=recent_day
            )
            assert len(main_forces) > 0, recent_day


@pytest.mark.asyncio
async def test_fetch_force_buy_sells() -> None:
    async with stock_crawl.StockCrawl() as client:
        force_buy_sells = await client.fetch_force_buy_sells(
            "https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco0/zco0.djhtm?a=2330&b=9600&BHID=9600"
        )
        assert len(force_buy_sells) > 0


@pytest.mark.asyncio
async def test_fetch_company_capitals() -> None:
    async with stock_crawl.StockCrawl() as client:
        company_capitals = await client.fetch_company_capitals()
        assert len(company_capitals) > 0


@pytest.mark.asyncio
async def test_fetch_history_trades() -> None:
    async with stock_crawl.StockCrawl() as client:
        history_trades = await client.fetch_history_trades("2330")
        assert len(history_trades) > 0

        history_trades = await client.fetch_history_trades("2330", limit=10)
        assert len(history_trades) == 10


@pytest.mark.asyncio
async def test_fetch_dividend_days() -> None:
    async with stock_crawl.StockCrawl() as client:
        dividend_days = await client.fetch_dividend_days()
        assert len(dividend_days) > 0


@pytest.mark.asyncio
async def test_fetch_punish_stocks() -> None:
    async with stock_crawl.StockCrawl() as client:
        punish_stocks = await client.fetch_punish_stocks()
        assert len(punish_stocks) > 0


@pytest.mark.asyncio
async def test_fetch_news() -> None:
    async with stock_crawl.StockCrawl() as client:
        news = await client.fetch_news()
        assert len(news) > 0


@pytest.mark.asyncio
async def test_fetch_most_recent_trade_day() -> None:
    async with stock_crawl.StockCrawl() as client:
        most_recent_trade_day = await client.fetch_most_recent_trade_day()
        assert isinstance(most_recent_trade_day, datetime.date)


@pytest.mark.asyncio
async def test_fetch_stock() -> None:
    async with stock_crawl.StockCrawl() as client:
        stock = await client.fetch_stock("2330")
        assert stock is not None
        stock = await client.fetch_stock("台積電")
        assert stock is not None
        stock = await client.fetch_stock("0")
        assert stock is None
        stock = await client.fetch_stock("不存在")
        assert stock is None


@pytest.mark.asyncio
async def test_fetch_stock_ids() -> None:
    async with stock_crawl.StockCrawl() as client:
        stock_ids = await client.fetch_stock_ids()
        assert len(stock_ids) > 0


@pytest.mark.asyncio
async def test_fetch_stock_ids_only_four_digits() -> None:
    async with stock_crawl.StockCrawl() as client:
        stock_ids = await client.fetch_stock_ids(only_four_digits=True)
        assert all(len(stock_id) == 4 for stock_id in stock_ids)


@pytest.mark.asyncio
async def test_client_reuse() -> None:
    async with stock_crawl.StockCrawl() as client:
        await client.fetch_history_trades("2330", limit=1)
        await client.fetch_history_trades("2330", limit=1)
        await client.fetch_most_recent_trade_day()
