import requests
import csv

# ---------------------------------------------------------------------------
# Items to scrape. Add a new dict here to track another product.
#   label        - friendly name used in the output
#   search_term  - what gets typed into the Woolworths search bar
#   keywords     - all of these must appear in the product name (case/hyphen
#                  insensitive) so unrelated search results get filtered out
# ---------------------------------------------------------------------------
ITEMS = [
    {
        "label": "Porterhouse Steak",
        "search_term": "porterhouse steak",
        "keywords": ["porterhouse"],
    },
    {
        "label": "T-Bone Steak",
        "search_term": "t-bone steak",
        "keywords": ["t bone"],
    },
]

SEARCH_URL = "https://www.woolworths.com.au/apis/ui/Search/products"
PRODUCT_URL = "https://www.woolworths.com.au/shop/productdetails/{stockcode}/{slug}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def normalise(text):
    """Lowercase and flatten hyphens so 'T-Bone' matches 'T Bone'."""
    return (text or "").lower().replace("-", " ")


def start_session():
    """Woolworths needs cookies from the homepage before the API will answer."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.woolworths.com.au",
        "Referer": "https://www.woolworths.com.au/shop/search/products",
    })
    session.get("https://www.woolworths.com.au/", timeout=30)
    return session


def search(session, search_term):
    """Return the raw product dicts for a search term."""
    payload = {
        "SearchTerm": search_term,
        "PageNumber": 1,
        "PageSize": 24,
        "SortType": "TraderRelevance",
        "IsSpecial": False,
        "Location": "/shop/search/products",
        "Filters": [],
        "IsRegisteredRewardCardPromotion": False,
        "EnableAdReRanking": False,
        "GroupEdmVariants": True,
        "EnableProductBoostExperiment": False,
    }

    response = session.post(SEARCH_URL, json=payload, timeout=30)
    response.raise_for_status()

    # Results come back as groups of products, so flatten them out.
    products = []
    for group in response.json().get("Products") or []:
        products.extend(group.get("Products") or [])
    return products


def matches(product, keywords):
    name = normalise(product.get("Name"))
    return all(normalise(keyword) in name for keyword in keywords)


def scrape_item(session, item):
    """Return a list of result rows for one entry in ITEMS."""
    rows = []

    for product in search(session, item["search_term"]):
        if not matches(product, item["keywords"]):
            continue

        price = product.get("Price")
        was_price = product.get("WasPrice")

        rows.append({
            "item": item["label"],
            "name": product.get("Name"),
            "price": price,
            "was_price": was_price,
            "on_special": bool(price and was_price and price < was_price),
            "unit_price": product.get("CupString"),
            "package_size": product.get("PackageSize"),
            "in_stock": product.get("IsAvailable"),
            "stockcode": product.get("Stockcode"),
            "url": PRODUCT_URL.format(
                stockcode=product.get("Stockcode"),
                slug=product.get("UrlFriendlyName"),
            ),
        })

    return rows


def format_price(price):
    return "unavailable" if price is None else "${:.2f}".format(price)


def main():
    session = start_session()
    all_rows = []

    for item in ITEMS:
        rows = scrape_item(session, item)
        all_rows.extend(rows)

        print("\n" + item["label"].upper())
        print("-" * 60)

        if not rows:
            print("  no matching products found")
            continue

        for row in rows:
            special = "  (was " + format_price(row["was_price"]) + ")" if row["on_special"] else ""
            stock = "" if row["in_stock"] else "  [out of stock]"
            print("  " + format_price(row["price"]) + special + stock)
            print("    " + row["name"] + "  -  " + str(row["package_size"]))
            print("    " + str(row["unit_price"]))

    with open("woolworths_prices.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(all_rows[0].keys()) if all_rows else ["item"])
        writer.writeheader()
        writer.writerows(all_rows)

    print("\nSaved " + str(len(all_rows)) + " products to woolworths_prices.csv")


if __name__ == "__main__":
    main()
