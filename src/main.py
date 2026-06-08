import logging
from datetime import datetime, timezone
import time
import random

from storage import load_products, save_price_record
from scraper import WoolworthsScraper
from parser import extract_price_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def run_scraper():
    """Main orchestration function for the steak price scraper."""
    logger.info("Starting Woolworths steak price scrape...")

    try:
        products = load_products()
    except Exception as e:
        logger.error(f"Failed to load products.json: {e}")
        return

    scraper = WoolworthsScraper()
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
            details = scraper.fetch_product_details(stockcode)
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
            time.sleep(random.uniform(1, 3))

    finally:
        scraper.close()

    logger.info("Scrape completed successfully.")

if __name__ == "__main__":
    run_scraper()
