# Web Scrapers Hub

A collection of web scraping projects and experiments. This repository serves as a central hub for the tools I've built to extract, parse, and structure data from across the web, documenting my journey in mastering automated data collection and processing.

## Scrapers

| Project | What it does | Approach |
| --- | --- | --- |
| [QuoteScraper](QuoteScraper) | Pulls quotes and authors from [quotes.toscrape.com](http://quotes.toscrape.com) and writes them to CSV | HTML parsing with BeautifulSoup |
| [WoolworthsScraper](WoolworthsScraper) | Tracks live prices for a configurable list of Woolworths products | Woolworths' internal JSON search API |
| [ArsTechnicaScraper](ArsTechnicaScraper) | Today's top 10 headlines from the Ars Technica front page | HTML parsing with BeautifulSoup |
| [NewsComAuScraper](NewsComAuScraper) | Today's top 10 headlines from the news.com.au front page | HTML parsing with BeautifulSoup |

## Dashboards

[`dashboards/`](dashboards) turns those CSVs into self contained HTML pages — no server, no
network, no external assets, so they open straight from disk.

| Dashboard | Reads | Shows |
| --- | --- | --- |
| [woolworths](dashboards/woolworths) | WoolworthsScraper | Steak prices normalised to dollars per kilogram |
| [headlines](dashboards/headlines) | ArsTechnicaScraper, NewsComAuScraper | Today's top 10 from each masthead, side by side |

## Requirements

Python 3 plus:

```bash
pip install requests beautifulsoup4
```

## Usage

Each scraper is self contained and writes its CSV output next to itself, so run it from inside its own folder:

```bash
cd WoolworthsScraper && python3 WoolworthsScraper.py
```

Dashboards read the CSVs out of the scraper folders and resolve their paths against their own
file, so they can be run from anywhere:

```bash
python3 dashboards/headlines/dashboard.py
```

See each project's own README for configuration and output details.
