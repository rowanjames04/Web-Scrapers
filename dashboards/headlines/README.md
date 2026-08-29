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

## Refresh buttons

The page has a **Refresh both feeds** button at the top right, and a smaller one at the top right
of each column that scrapes only that source.

Those buttons need [`serve.py`](serve.py), because **a page on `file://` cannot start a Python
process**. It serves the same `dashboard.html` and exposes one endpoint that runs the scrapers
and rebuilds the page:

```bash
python3 dashboards/headlines/serve.py
```

Then open <http://127.0.0.1:8000/>. A click scrapes, regenerates the HTML and reloads.

Opened straight from disk the page still renders in full — the buttons just explain what to run
instead of failing against an endpoint that was never there. **The server is optional and adds
nothing to the page; the generated HTML stays self-contained either way.**

Four things worth knowing about the server:

- It binds to `127.0.0.1`. The endpoint starts processes, so it has no business listening on
  anything the rest of the network can reach.
- A request names a source key (`ars`, `news`, `all`), never a path. Anything else is a `400`.
- One refresh runs at a time. A second request while one is in flight gets a `409` rather than
  racing it for the same CSV.
- If a scraper fails, the page is left alone rather than rebuilt from a half-written CSV, and the
  error comes back to the status line next to the button.

## What it shows

Each column heads with the masthead, its headline count, how many distinct sections those
headlines span, and the time range they cover. Then the ten stories in the site's own front
page order: rank, headline linking to the article, section, publication time and the standfirst.

`SOURCES` at the top of `dashboard.py` is the whole configuration surface. **List order is
column order**, so Ars sits left because it is listed first. Adding a third source means adding
a dict and a colour, and changing the `.columns` grid, which is fixed at two columns.

## Thumbnails

Card images are **embedded as base64 data URIs, never linked**. The scrapers do the fetching and
save the images beside their CSVs; the dashboard reads those files off disk and inlines the
bytes. That is what keeps the page self-contained — it renders identically with the network off,
and no publisher's CDN gets pinged when you open it.

At 128px square per image the whole page lands around 120KB, which is the reason the scrapers
downscale rather than storing what the sites serve. Stories with no card image, and any
thumbnail missing from disk, render as an empty slot that keeps the column aligned rather than a
broken image.

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
