import logging

logger = logging.getLogger(__name__)

def clean_price(price_value):
    """
    Converts a price value to a float.
    Handles cases where it might be a string with currency symbols or None.
    """
    if price_value is None:
        return None

    if isinstance(price_value, (int, float)):
        return float(price_value)

    if isinstance(price_value, str):
        # Remove currency symbols and commas
        cleaned = price_value.replace('$', '').replace(',', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            logger.error(f"Could not parse price string: {price_value}")
            return None

    return None

def extract_price_data(json_response):
    """
    Extracts standard and special prices from the Woolworths product detail JSON.
    Returns a tuple (price, special_price).
    """
    try:
        # Based on common patterns in Woolworths internal API:
        # The response is usually a JSON object with a top-level 'price' or similar structure
        # If it's nested under 'Product' or 'Price', we adjust.

        # Most internal endpoints for 'detail' put the data at the root or under a 'product' key
        data = json_response
        if "product" in json_response:
            data = json_response["product"]

        price = data.get("price")
        special_price = data.get("specialPrice")

        return clean_price(price), clean_price(special_price)

    except Exception as e:
        logger.error(f"Error extracting price data: {e}")
        return None, None
