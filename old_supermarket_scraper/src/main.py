import logging
import asyncio
from datetime import datetime, timezone
import random
import time

from old_supermarket_scraper.src.storage import load_products, save_price_record
from old_supermarket_scraper.src.scraper import WoolworthsScraper
from old_supermarket_scraper.src.parser import extract_price_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

async def run_scraper():
    """Main asynchronous orchestration function for the steak price scraper."""
    logger.info("Starting Woolworths steak price scrape (Playwright mode)...")

    try:
        products = load_products()
    except Exception as e:
        logger.error(f"Failed to load products.json: {e}")
        return

    scraper = WoolworthsScraper()
    await scraper.start()

    timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    try:
        for product in products:
            name = product.get("name")
            stockcode = product.get("stockcode")

            if not stockcode:
                logger.warning(f"Skipping product missing stockcode: {name}")
                continue

            logger.info(f"Fetching price for {name} ({stockcode})...")

            # Fetch data
            details = await scraper.fetch_product_details(product)
            if not details:
                logger.error(f"Could not retrieve details for {name}")
                continue

            # Parse data
            price, special_price = extract_price_data(details)

            if price is None:
                logger.error(f"Could not parse price for {name}")
                continue

            # Save record
            record = {
                "timestamp": timestamp,
                "stockcode": stockcode,
                "name": name,
                "price": price,
                "special_price": special_price
            }
            save_price_record(record)
            logger.info(f"Saved: {name} -> ${price} (Special: ${special_price})")

            # Polite delay between requests
            await asyncio.sleep(random.uniform(1, 3))

    finally:
        await scraper.close()

    logger.info("Scrape completed successfully.")

if __name__ == "__main__":
    try:
        asyncio.run(run_scraper())
    except KeyboardInterrupt:
        pass
