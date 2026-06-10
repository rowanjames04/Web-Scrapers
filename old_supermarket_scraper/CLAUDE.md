# Woolworths Steak Price Scraper

A project to track steak prices from Woolworths weekly on Mondays.

## Goal
Automate the collection of price and special-price data for specific steak products and store them in a time-series CSV for trend analysis.

## Current Stack
- **Language**: Python 3.13
- **Automation**: Playwright (Chromium)
- **Scheduling**: GitHub Actions (Cron: `0 0 * * 1`)
- **Data Storage**: `products.json` (input), `price_history.csv` (output)

## The "Bot Detection" Battle Log
Woolworths uses extremely aggressive bot protection (Akamai/Edgesuite). The following methods were attempted and failed:

| Method | Tool | Result | Root Cause |
| :--- | :--- | :--- | :--- |
| **Direct API** | `httpx` | ⏳ Timeout | Server "tarpitting" (ignored request). |
| **TLS Mimicry** | `curl_cffi` | ❌ HTTP/2 Error | Protocol mismatch / TLS fingerprinting. |
| **Headless Browser** | `Playwright` | 🚫 403 Forbidden | Detected as automated browser. |
| **In-Browser JS** | `page.evaluate` | 🚫 403 Forbidden | Naked API calls within browser still flagged. |
| **DOM Scraping** | `page.goto` | 🚫 Access Denied | Akamai identified "automated" behavior. |
| **Stealth Mode** | `playwright-stealth`| 🚫 Access Denied | IP reputation flagged; behavioral detection. |

## Current State
- **Status**: Blocked by Akamai (Edgesuite).
- **Observation**: The local IP address has likely been flagged as suspicious due to repeated automated attempts.
- **Next Potential Steps**: 
    - **Headful Mode**: `headless=False` to allow manual CAPTCHA solving.
    - **Residential Proxies**: Using a paid service to rotate IP addresses.

## Project Structure
- `products.json`: List of target stockcodes and URLs.
- `src/main.py`: Orchestration loop.
- `src/scraper.py`: Browser/API interaction logic.
- `src/parser.py`: Price extraction and cleaning.
- `src/storage.py`: CSV/JSON I/O.
- `price_history.csv`: The resulting time-series data.
