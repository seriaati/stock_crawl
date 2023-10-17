import datetime

import pytest

import stock_crawl


@pytest.mark.asyncio
async def test_fetch_stocks():
    client = stock_crawl.StockCrawl()
    stocks = await client.fetch_stocks()
    assert len(stocks) > 0
    await client.close()


@pytest.mark.asyncio
async def test_fetch_main_forces():
    client = stock_crawl.StockCrawl()
    for recent_day in stock_crawl.RecentDay:
        main_forces = await client.fetch_main_forces(
            "2330", datetime.date(2023, 10, 4), recent_day=recent_day
        )
        assert len(main_forces) > 0, recent_day
    await client.close()


@pytest.mark.asyncio
async def test_fetch_force_buy_sells():
    client = stock_crawl.StockCrawl()
    force_buy_sells = await client.fetch_force_buy_sells(
        "https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco0/zco0.djhtm?a=2330&b=9600&BHID=9600"
    )
    assert len(force_buy_sells) > 0
    await client.close()


@pytest.mark.asyncio
async def test_fetch_company_capitals():
    client = stock_crawl.StockCrawl()
    company_capitals = await client.fetch_company_capitals()
    assert len(company_capitals) > 0
    await client.close()


@pytest.mark.asyncio
async def test_fetch_history_trades():
    client = stock_crawl.StockCrawl()
    history_trades = await client.fetch_history_trades("2330")
    assert len(history_trades) > 0

    history_trades = await client.fetch_history_trades("2330", limit=10)
    assert len(history_trades) == 10

    await client.close()


@pytest.mark.asyncio
async def test_fetch_dividend_days():
    client = stock_crawl.StockCrawl()
    dividend_days = await client.fetch_dividend_days()
    assert len(dividend_days) > 0
    await client.close()


@pytest.mark.asyncio
async def test_fetch_punish_stocks():
    client = stock_crawl.StockCrawl()
    punish_stocks = await client.fetch_punish_stocks()
    assert len(punish_stocks) > 0
    await client.close()


@pytest.mark.asyncio
async def test_fetch_news():
    client = stock_crawl.StockCrawl()
    news = await client.fetch_news()
    assert len(news) > 0
    await client.close()


@pytest.mark.asyncio
async def test_fetch_most_recent_trade_day():
    client = stock_crawl.StockCrawl()
    most_recent_trade_day = await client.fetch_most_recent_trade_day()
    assert isinstance(most_recent_trade_day, datetime.date)
    await client.close()


@pytest.mark.asyncio
async def test_fetch_stock():
    client = stock_crawl.StockCrawl()
    stock = await client.fetch_stock("2330")
    assert stock is not None
    stock = await client.fetch_stock("台積電")
    assert stock is not None
    stock = await client.fetch_stock("0")
    assert stock is None
    stock = await client.fetch_stock("不存在")
    assert stock is None
    await client.close()


@pytest.mark.asyncio
async def test_fetch_stock_ids():
    client = stock_crawl.StockCrawl()
    stock_ids = await client.fetch_stock_ids()
    assert len(stock_ids) > 0
    await client.close()


@pytest.mark.asyncio
async def test_fetch_stock_ids_only_four_digits():
    client = stock_crawl.StockCrawl()
    stock_ids = await client.fetch_stock_ids(only_four_digits=True)
    assert all(len(stock_id) == 4 for stock_id in stock_ids)
    await client.close()


@pytest.mark.asyncio
async def test_client_reuse():
    client = stock_crawl.StockCrawl()
    await client.fetch_history_trades("2330", limit=1)
    await client.fetch_history_trades("2330", limit=1)
    await client.fetch_most_recent_trade_day()
