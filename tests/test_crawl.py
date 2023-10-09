import datetime

import pytest

import stock_crawl


@pytest.mark.asyncio
async def test_fetch_stocks():
    client = stock_crawl.StockCrawl(use_cache=False)
    stocks = await client.fetch_stocks()
    assert len(stocks) > 0


@pytest.mark.asyncio
async def test_fetch_main_forces():
    client = stock_crawl.StockCrawl(use_cache=False)
    for recent_day in stock_crawl.RecentDay:
        main_forces = await client.fetch_main_forces(
            "2330", datetime.date(2023, 10, 4), recent_day=recent_day
        )
        assert len(main_forces) > 0, recent_day


@pytest.mark.asyncio
async def test_fetch_force_buy_sells():
    client = stock_crawl.StockCrawl(use_cache=False)
    force_buy_sells = await client.fetch_force_buy_sells(
        "https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco0/zco0.djhtm?a=2330&b=9600&BHID=9600"
    )
    assert len(force_buy_sells) > 0


@pytest.mark.asyncio
async def test_fetch_company_capitals():
    client = stock_crawl.StockCrawl(use_cache=False)
    company_capitals = await client.fetch_company_capitals()
    assert len(company_capitals) > 0


@pytest.mark.asyncio
async def test_fetch_history_trades():
    client = stock_crawl.StockCrawl(use_cache=False)
    history_trades = await client.fetch_history_trades("2330")
    assert len(history_trades) > 0

    history_trades = await client.fetch_history_trades("2330", limit=10)
    assert len(history_trades) == 10


@pytest.mark.asyncio
async def test_fetch_dividend_days():
    client = stock_crawl.StockCrawl(use_cache=False)
    dividend_days = await client.fetch_dividend_days()
    assert len(dividend_days) > 0


@pytest.mark.asyncio
async def test_fetch_punish_stocks():
    client = stock_crawl.StockCrawl(use_cache=False)
    punish_stocks = await client.fetch_punish_stocks()
    assert len(punish_stocks) > 0


@pytest.mark.asyncio
async def test_fetch_news():
    client = stock_crawl.StockCrawl(use_cache=False)
    news = await client.fetch_news()
    assert len(news) > 0


@pytest.mark.asyncio
async def test_fetch_most_recent_trade_day():
    client = stock_crawl.StockCrawl(use_cache=False)
    most_recent_trade_day = await client.fetch_most_recent_trade_day()
    assert isinstance(most_recent_trade_day, datetime.date)
