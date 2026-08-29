# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository shape

A hub of independent scrapers, one folder per project. There is no shared package, no
imports between projects, no dependency manifest and no build step. Each scraper is a
standalone script that can be copied out of the repo and still run.

Dependencies are installed globally as needed:

```bash
pip install requests beautifulsoup4
```

## Commands

Every scraper resolves its input and output paths relative to the current working
directory, so **always run one from inside its own folder** or the CSV lands in the wrong
place. Dashboards live in `dashboards/` and read CSVs out of the scraper folders, so they
resolve paths against their own file instead and can be run from anywhere:

```bash
cd QuoteScraper && python3 QuoteScraper.py
cd WoolworthsScraper && python3 WoolworthsScraper.py
python3 dashboards/woolworths/dashboard.py
```

There is no test suite, linter or CI. Verification is manual: run the scraper and check
the printed output and the regenerated CSV. Because both scrapers hit live sites, a
`git diff` on the CSV after a run is the quickest signal that something changed —
distinguish a real price movement from a parsing regression before assuming a bug.

## Architecture

### Two scraping strategies, deliberately different

`QuoteScraper` parses server-rendered HTML with BeautifulSoup. That approach does **not**
work for Woolworths: their product pages are JavaScript-rendered, so `requests` plus
BeautifulSoup returns an empty page. `WoolworthsScraper` therefore posts to the site's own
internal JSON endpoint (`apis/ui/Search/products`) — the one the search page itself calls.
Do not "fix" the Woolworths scraper by reaching for BeautifulSoup.

Two consequences of using that endpoint:

- `start_session()` must GET the homepage first. The API rejects requests without the
  cookies that sets.
- It is undocumented and can change shape without notice. If results stop returning,
  compare a real request in the browser network tab against the `payload` dict in
  `search()`.

### WoolworthsScraper: the pipeline

`WoolworthsScraper/WoolworthsScraper.py` → `WoolworthsScraper/woolworths_prices.csv` →
`dashboards/woolworths/dashboard.py` → `dashboards/woolworths/dashboard.html`

The CSV is the interface between the two stages, and the folder boundary keeps it that way:
scraping and rendering stay separate, and a dashboard never reaches for the network.
`dashboard.html` is **generated output** — edit `dashboard.py` and re-run it; never
hand-edit the HTML.

`ITEMS` at the top of `WoolworthsScraper.py` is the entire configuration surface; tracking a
new product means adding one dict, no code changes. Each entry's `keywords` list is load-
bearing rather than cosmetic: a raw search for `porterhouse steak` also returns sirloin and
unrelated meal kits, and the keyword filter is what drops them. Matching is case-insensitive
and flattens hyphens so `"t bone"` catches both `T Bone Steak` and `T-Bone Bistecca`.

Committed CSVs are intentional in both projects — they act as the last-known-good snapshot.

### dashboards/woolworths: the two things that will bite

**Per-kilogram normalisation is the point of the dashboard.** Pack sizes span 180g to 1.2kg,
so shelf prices are not comparable across products. `price_per_kg()` parses the site's own
`CupString` (`"$45.00 / 1KG"`, `"$3.40 / 100G"`) into dollars per kilo, and every headline
figure and the chart sort order derive from it. Products with no current per-kilo price
(typically out-of-stock variable-weight cuts) are excluded from the chart and still listed
in the table — keep that distinction if you touch the rendering.

**The chart's gridlines and bars must share one column system.** The tick overlay is
absolutely positioned using the `--label-col`, `--value-col`, `--col-gap` and `--value-gap`
custom properties declared on `.chart`, and bar rows lay out from those same variables. If
you change a column width in one place and not the other, the gridlines silently stop
lining up with the bars and the chart misreports every value. This has already been a bug
once.

Series colours are chosen for colour-blind separation against both the light and dark page
surfaces, and the palette is validated rather than eyeballed. Adding a third tracked item
picks up the next entry in `SERIES_COLOURS`; going beyond three needs a new colour
validated against both surfaces, not an invented hex.

The generated page is fully self-contained — no network, no external assets — so it opens
straight from disk. Keep it that way. It themes off `prefers-color-scheme` with tokens
defined on bare `:root`, so any new colour must be declared as a token in both blocks.

## Conventions

Commit messages follow Conventional Commits (`feat:`, `chore:`, `docs:`, `refactor:`), with
a short subject line and a body explaining the reasoning where it is not obvious.

**Never add co-author trailers, `Generated with` lines, or any other attribution to commits.**
Commits are authored solely by the repository owner.
