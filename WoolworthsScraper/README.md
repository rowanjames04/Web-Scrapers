# Woolworths Scraper

Scrapes live product prices from [Woolworths](https://www.woolworths.com.au) for a configurable list of items, prints them to the terminal and saves them to `woolworths_prices.csv`.

Ships tracking porterhouse and T-bone steak.

## Requirements

Python 3 plus:

```bash
pip install requests
```

## Usage

Run it from inside this folder so the CSV lands here:

```bash
cd WoolworthsScraper && python3 WoolworthsScraper.py
```

Sample output:

```
PORTERHOUSE STEAK
------------------------------------------------------------
  $9.00
    Woolworths Beef Porterhouse Steak  -  180g
    $50.00 / 1KG
  $16.00
    Macro Grass Fed Beef Porterhouse Steak  -  270g
    $59.26 / 1KG

T-BONE STEAK
------------------------------------------------------------
  $24.50
    Woolworths Beef T Bone Steak Medium  -  250g - 700g
    $35.00 / 1KG
```

## Adding more items

Products live in the `ITEMS` list at the top of `WoolworthsScraper.py`. Add a dict to track another one:

```python
{
    "label": "Scotch Fillet",
    "search_term": "scotch fillet steak",
    "keywords": ["scotch fillet"],
},
```

| Key | Purpose |
| --- | --- |
| `label` | Friendly name used in the terminal output and the CSV `item` column |
| `search_term` | What gets typed into the Woolworths search bar |
| `keywords` | Every keyword must appear in the product name for it to be kept |

`keywords` is the noise filter. A raw search for `porterhouse steak` also returns a sirloin sharing steak and an air fryer meal kit, so requiring `"porterhouse"` in the name drops them. Matching ignores case and flattens hyphens, so `"t bone"` matches both `T Bone Steak` and `T-Bone Bistecca`.

## Output

`woolworths_prices.csv` has one row per matching product:

| Column | Description |
| --- | --- |
| `item` | The `label` from `ITEMS` |
| `name` | Full Woolworths product name |
| `price` | Current price in AUD, empty if unavailable |
| `was_price` | Pre discount price |
| `on_special` | `True` when `price` is below `was_price` |
| `unit_price` | Price per kg or 100g, as shown on the site |
| `package_size` | Pack size, a range for variable weight cuts |
| `in_stock` | Availability flag |
| `stockcode` | Woolworths product ID |
| `url` | Direct link to the product page |

## How it works

Woolworths product pages are rendered with JavaScript, so `requests` plus BeautifulSoup would come back empty. This scraper instead posts to the site's own JSON search endpoint, `apis/ui/Search/products`, which is what the search page itself calls.

The endpoint rejects requests without a valid session, so `start_session()` fetches the homepage first to pick up cookies before searching.

## Notes

- Prices are national online prices and can differ from your local store.
- Variable weight butcher cuts sometimes return a null price when out of stock. Those are kept in the output with an empty `price` and `in_stock` set to `False`.
- This is an undocumented internal endpoint, so the payload or response shape can change without warning. If results stop coming back, compare the request in your browser's network tab against the `payload` dict in `search()`.
