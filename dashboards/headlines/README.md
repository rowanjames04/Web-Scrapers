# Headlines Dashboard

Renders today's top 10 headlines from [ArsTechnicaScraper](../../ArsTechnicaScraper) and [NewsComAuScraper](../../NewsComAuScraper) side by side as a single self contained `dashboard.html` — Ars Technica on the left, news.com.au on the right.

## Usage

Scrape both sources first, then render. The dashboard resolves its paths against its own
file, so it can be run from anywhere:

```bash
cd ArsTechnicaScraper && python3 ArsTechnicaScraper.py
cd ../NewsComAuScraper && python3 NewsComAuScraper.py
cd .. && python3 dashboards/headlines/dashboard.py
```

`dashboard.html` is **generated output** — edit `dashboard.py` and re-run it, never hand-edit
the HTML. It needs no server, no network and no dependencies, so open it straight from disk.

If a CSV is missing, that column renders a "run the scraper" placeholder instead of failing,
so one broken source does not take the page down with it.

## What it shows

Each column heads with the masthead, its headline count, how many distinct sections those
headlines span, and the time range they cover. Then the ten stories in the site's own front
page order: rank, headline linking to the article, section, publication time and the standfirst.

`SOURCES` at the top of `dashboard.py` is the whole configuration surface. **List order is
column order**, so Ars sits left because it is listed first. Adding a third source means adding
a dict and a colour, and changing the `.columns` grid, which is fixed at two columns.

## The two things worth knowing

**Rank is front page prominence, not popularity.** Neither site publishes a public read or
share count, so there is nothing to sort by that actually measures what people clicked. What
both sites do expose is the order their own editors put stories in, and that is what the rank
column means. Do not relabel it "most read" — it isn't.

**Times are each site's own, and the two columns rarely share a date.** Every timestamp is
rendered in the offset the publisher used, with that offset stated in the column header rather
than converted to a single timezone. Ars publishes on US Eastern and news.com.au on Australian
Eastern, so the columns routinely lead with different calendar dates for the same news cycle.
Normalising them to one timezone would hide that rather than explain it — see each scraper's
README for what "today" means.

## Colours

Each source gets one entry from the same colour-blind-validated palette the Woolworths
dashboard uses: blue for Ars, orange for news.com.au. Colours are `(light, dark)` pairs and
`build_styles()` emits a `--series` token per source into all three theme blocks — bare
`:root`, the `prefers-color-scheme: dark` media query, and the explicit `[data-theme="dark"]`
override. A new source needs a pair validated against both page surfaces, not an invented hex.
