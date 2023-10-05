import pytest

import stock_crawl


@pytest.mark.asyncio
async def test_client_start_and_close():
    client = stock_crawl.StockCrawl()
    await client.start()
    await client.close()


@pytest.mark.asyncio
async def test_client_aenter_aexit():
    async with stock_crawl.StockCrawl():
        pass
