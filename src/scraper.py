import httpx
import logging
import time
import random
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Browser-like headers to minimize bot detection
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9,en-GB;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.woolworths.com.au/",
    "Connection": "keep-alive",
}

class WoolworthsScraper:
    def __init__(self):
        self.base_url = "https://www.woolworths.com.au/apis/ui/product/detail"
        # Increased timeout to 30s and using the enhanced headers
        self.client = httpx.Client(headers=DEFAULT_HEADERS, timeout=30.0)

    def fetch_product_details(self, stockcode: str) -> Optional[Dict[str, Any]]:
        """
        Fetches product details for a given stockcode.
        Implements basic retries and error handling.
        """
        url = f"{self.base_url}/{stockcode}"

        for attempt in range(3):
            try:
                response = self.client.get(url)

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 403:
                    logger.error(f"403 Forbidden for {stockcode}. Bot detection may be active.")
                    break # Retrying 403 usually doesn't help without different headers/cookies

                if response.status_code == 429:
                    logger.warning(f"429 Too Many Requests for {stockcode}. Backing off...")
                    time.sleep(2 ** attempt + random.uniform(1, 3))
                    continue

                response.raise_for_status()

            except httpx.RequestError as e:
                logger.warning(f"Attempt {attempt+1} failed for {stockcode}: {e}")
                time.sleep(2 ** attempt + random.uniform(1, 3))

        logger.error(f"Failed to fetch product {stockcode} after 3 attempts.")
        return None

    def close(self):
        self.client.close()
