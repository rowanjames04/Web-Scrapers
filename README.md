# Web Scrapers Hub

A collection of web scraping projects and experiments. This repository serves as a central hub for the tools I've built to extract, parse, and structure data from across the web, documenting my journey in mastering automated data collection and processing.

## Scrapers

| Project | What it does | Approach |
| --- | --- | --- |
| [QuoteScraper](QuoteScraper) | Pulls quotes and authors from [quotes.toscrape.com](http://quotes.toscrape.com) and writes them to CSV | HTML parsing with BeautifulSoup |
| [WoolworthsScraper](WoolworthsScraper) | Tracks live prices for a configurable list of Woolworths products | Woolworths' internal JSON search API |

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

See each project's own README for configuration and output details.
