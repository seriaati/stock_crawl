import asyncio
import logging

from stock_crawl import StockCrawl

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")


async def main():
    stock_crawl = StockCrawl()
    await stock_crawl.start()
    await stock_crawl.close()


asyncio.run(main())
