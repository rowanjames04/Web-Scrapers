import logging
import os
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

class WoolworthsScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    async def start(self):
        """
        Launches the browser and prepares a page.
        Applies stealth plugins to bypass bot detection.
        """
        playwright = await async_playwright().start()
        # Headless=True is usually okay with stealth, but if it fails,
        # headless=False is the gold standard for bypassing blocks.
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )
        self.page = await self.context.new_page()

        # APPLY STEALTH: This hides the 'navigator.webdriver' flag and other bot signals
        stealth_config = Stealth()
        await stealth_config.apply_stealth_async(self.page)

        try:
            logger.info("Establishing session on Woolworths home page...")
            await self.page.goto("https://www.woolworths.com.au/", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning(f"Home page load failed: {e}. Attempting API calls regardless.")

    async def fetch_product_details(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetches product details by navigating to the product page and
        scraping the price directly from the DOM.
        """
        url = product.get("url")
        name = product.get("name")
        stockcode = product.get("stockcode")

        if not url:
            logger.error(f"No URL provided for product {name}")
            return None

        try:
            logger.info(f"Navigating to page: {url}")
            await self.page.goto(url, wait_until="networkidle", timeout=60000)

            # Heuristic search for price-like text
            price_js = """
            () => {
                const priceElements = Array.from(document.querySelectorAll('span, div, p'))
                    .filter(el => {
                        const text = el.innerText;
                        return text && text.includes('$') && /\\d+\\.\\d{2}/.test(text) && el.children.length === 0;
                    });

                if (priceElements.length === 0) return null;
                return priceElements[0].innerText;
            }
            """

            price = await self.page.evaluate(price_js)

            if not price:
                logger.warning(f"Price not found for {name}. Saving diagnostics...")
                screenshot_path = f"failure_{stockcode}.png"
                html_path = f"failure_{stockcode}.html"
                await self.page.screenshot(path=screenshot_path, full_page=True)
                content = await self.page.content()
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return None

            logger.info(f"Found price for {name}: {price}")

            return {
                "product": {
                    "price": price,
                    "specialPrice": None
                }
            }

        except Exception as e:
            logger.error(f"Error scraping page for {name}: {e}")
            return None

    async def close(self):
        """Closes the browser and context."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
