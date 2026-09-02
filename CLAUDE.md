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
cd ArsTechnicaScraper && python3 ArsTechnicaScraper.py
cd NewsComAuScraper && python3 NewsComAuScraper.py
python3 dashboards/woolworths/dashboard.py
python3 dashboards/headlines/dashboard.py
python3 dashboards/headlines/serve.py     # optional, powers the refresh buttons
open dashboards/headlines/start-dashboard.command   # or double-click it in Finder
open dashboards/headlines/stop-dashboard.command    # stops it again
python3 dashboards/headlines/install-app.py         # menu bar app in /Applications
```

There is no test suite, linter or CI. Verification is manual: run the scraper and check
the printed output and the regenerated CSV. Because both scrapers hit live sites, a
`git diff` on the CSV after a run is the quickest signal that something changed —
distinguish a real price movement from a parsing regression before assuming a bug.

## Architecture

### Two scraping strategies, deliberately different

`QuoteScraper`, `ArsTechnicaScraper` and `NewsComAuScraper` parse server-rendered HTML with
BeautifulSoup. That approach does **not** work for Woolworths: their product pages are JavaScript-rendered, so `requests` plus
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

### The headline scrapers: what "today" means

Both front pages are server-rendered, so these are plain BeautifulSoup jobs — no internal API
hunt needed. Each hangs off the site's own card class (`<article>` on Ars, `article.storyblock`
on news.com.au) and keeps DOM order, because that order **is** the editorial ranking. There is
no public popularity count on either site, so front-page prominence is the honest stand-in for
"top"; don't relabel it "most read".

**Neither scraper filters on the local calendar date, and that is deliberate.** Ars publishes on
US Eastern, so run from Australia a strict date match returns nothing for most of the working
day. Instead the newest story on a front page sets that site's clock and `WINDOW_HOURS` (24)
runs back from there. On news.com.au the same rule earns its keep differently: it drops the
evergreen lifestyle promos mixed into the page, some of them a year or two old, without a hand-
maintained list of sections to ignore. If you tighten this to a real date match, check what the
scrapers return at 9am Sydney time before assuming it works.

Both pages repeat their lead stories in later modules, so URLs are deduped keeping the first
appearance — the one that reflects the story's billing.

Each scraper also saves card images into its own `thumbnails/` folder, named by the site's own
article ID, and records the relative path in the CSV. Two rules there:

- **Pick from the card's `srcset`, don't invent a width.** Ars ships fixed WordPress sizes and
  ignores resize query params; the news.com.au CDN answers `412` for any width it didn't list.
- **Pillow is optional.** With it, images are cropped square and scaled to 128px; without it the
  served bytes are stored as-is. Don't make it a hard import — the repo has no dependency
  manifest and the scraper is meant to run on `requests` and `beautifulsoup4` alone.

Each run prunes thumbnails that are no longer in the top 10, so the folder mirrors the CSV.
news.com.au blocks that lead with an animation carry a `<video>` and no image, so they
legitimately have no thumbnail.

### dashboards/headlines

Reads both headline CSVs; `SOURCES` list order is column order, so Ars is left because it is
listed first. A missing CSV renders a placeholder column rather than failing, so one broken
source doesn't take the page down.

Timestamps are rendered in each publisher's own offset with that offset stated in the column
header, never converted to a single timezone. The two columns routinely show different calendar
dates for the same news cycle, and that difference is the point — normalising it away would hide
the thing the page is showing.

Thumbnails are read off disk and **embedded as base64 data URIs, never linked**. The dashboard
does no fetching — that is the scrapers' job — and inlining is what keeps the page self-contained
and openable straight from disk with the network off. A story with no image, or a thumbnail
missing from disk, renders as an empty slot that holds the column alignment.

### The refresh buttons and serve.py

The page has a refresh button top right, plus one per column that scrapes a single source. **A
page on `file://` cannot start a Python process**, so those buttons need `serve.py`: it serves
the same HTML and exposes a `POST /refresh?source=ars|news|all` that runs the scrapers and
rebuilds the page.

This does not weaken the self-contained rule above, and must not be allowed to. The generated
HTML has no external assets either way, still opens from disk, and still renders in full there —
the script checks `location.protocol` and, on `file://`, prints the command to run instead of
firing a fetch at an endpoint that was never there. **Keep that fallback working**; it is what
lets the page stay a file you can email to yourself.

`serve.py` is stdlib-only and deliberately small. Four properties are load-bearing rather than
incidental:

- It binds `127.0.0.1`. The endpoint starts processes; don't make it listen wider.
- Requests name a **source key**, never a path — `SOURCES` maps the key to a folder and script.
  Don't take a script name or path from the request.
- A `threading.Lock` allows one refresh at a time and returns `409` otherwise, so two runs can't
  race for the same CSV.
- A failed scraper returns before the rebuild, so the page is never regenerated from a
  half-written CSV.

`start-dashboard.command` is a double-clickable Finder launcher that runs `serve.py --open`. It
resolves its own folder from `$0` because Finder starts it in the user's home directory, and it
needs its executable bit committed. `--open` opens the browser after the socket is bound; an
`EADDRINUSE` is treated as "already running" and opens that instead of raising.

`stop-dashboard.command` reads the port by importing `serve` rather than hardcoding it, so the
two can't drift apart — keep `serve.py` free of import-time side effects or that breaks. It
kills only a process whose command line contains `serve.py`; port 8000 is popular, and a script
that kills whatever holds the port is a script that will one day kill the wrong thing.

### The menu bar app

`app.py` is a `rumps` menu bar app and `install-app.py` wraps it into
`Headlines Dashboard.app`. It **imports `serve.py` rather than copying it**, and runs the server
in a daemon thread in-process, so the endpoint, the source keys and the refresh lock stay in one
place. Keep it that way.

**Launching it opens a window.** A menu bar app has no Dock icon and no window of its own, so
without this, double-clicking it appears to do nothing at all — which reads as a broken app. It
opens a Chrome app-mode window (`--app=`), which has no tabs or address bar, and falls back to
the default browser. `--no-open` suppresses it, which is what "Restart App" re-execs with, and
what to use when testing so repeated launches don't pile up windows.

Four properties are load-bearing:

- **The bundle wraps, it does not copy.** Its executable runs `app.py` from the repo, so edits
  are live on the next launch and "Restart App" re-execs to pick them up. Don't make the
  installer copy sources in; the whole update story depends on this.
- **The interpreter is pinned at install time.** A Finder-launched app gets a minimal `PATH`
  and would otherwise resolve `python3` to Apple's build, which may lack `rumps`. With no
  Terminal, that failure is invisible — which is also why the launcher tees everything to
  `~/Library/Logs/HeadlinesDashboard.log`.
- **A second launch doesn't start a second instance.** `already_serving()` probes the port
  first; if the app is already up, the new process just opens the dashboard and exits rather
  than adding a duplicate menu bar icon that quietly does nothing.
- **The installer calls `lsregister`.** A freshly built bundle is unknown to LaunchServices, so
  `open` and Spotlight silently do nothing and Finder shows a stale icon. This cost an hour once.

Worker threads never touch the menu. They leave a message behind a lock and a `rumps.Timer` on
the main thread picks it up, because AppKit is not safe to drive from a background thread.

`serve.summarise()` prefers stdout over stderr when reporting a run, since stderr is often just
a deprecation warning and merging the streams surfaces a warning fragment instead of the result.

The client script lives in the `SCRIPT` constant rather than inside `TEMPLATE`, so its braces
don't need doubling for `str.format()`. Same for `REFRESH_ICON`. If you move JS or CSS into the
template itself, every `{` and `}` has to be doubled.

`build_styles()` emits one `--series` token per source into all three theme blocks. Colours come
from the same validated palette as the Woolworths dashboard; a new source needs a `(light, dark)`
pair validated against both surfaces, not an invented hex.

## Conventions

Commit messages follow Conventional Commits (`feat:`, `chore:`, `docs:`, `refactor:`), with
a short subject line and a body explaining the reasoning where it is not obvious.

**Never add co-author trailers, `Generated with` lines, or any other attribution to commits.**
Commits are authored solely by the repository owner.
