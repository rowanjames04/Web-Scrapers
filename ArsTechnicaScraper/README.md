# Ars Technica Scraper

Pulls today's top 10 headlines from the [Ars Technica](https://arstechnica.com) front page, prints them to the terminal and saves them to `ars_technica_headlines.csv`.

## Requirements

Python 3 plus:

```bash
pip install requests beautifulsoup4
```

Pillow is optional. With it, thumbnails are cropped square and scaled to 128px; without it they
are stored at whatever size Ars served, which still works, just heavier:

```bash
pip install Pillow
```

## Usage

Run it from inside this folder so the CSV lands here:

```bash
cd ArsTechnicaScraper && python3 ArsTechnicaScraper.py
```

Sample output:

```
ARS TECHNICA - TOP 10 TODAY
------------------------------------------------------------------------
 1. Our 10 favorite scenes from T2: Judgment Day
    Culture  -  28 aug 12:44pm
 2. Court rules Kalshi sports bets aren’t “swaps,” just gambling with a different name
    Tech Policy  -  28 aug 6:14pm
 3. Cities terminate Flock contracts at record pace in August
    Tech Policy  -  28 aug 5:33pm
```

## Output

`ars_technica_headlines.csv` has one row per headline:

| Column | Description |
| --- | --- |
| `rank` | 1 to 10, in front page order |
| `headline` | The headline text |
| `url` | Direct link to the article |
| `section` | Ars category, e.g. `Tech Policy`, `AI`, `Space` |
| `published` | Publication time, ISO 8601 with the site's UTC offset |
| `summary` | The card's one line dek, empty when the card has none |
| `thumbnail` | Path to the saved card image, relative to this folder. Empty when the card has none |

Card images are saved to `thumbnails/`, named by the post ID Ars puts on each card so the
filename is stable across runs. Images no longer in the top 10 are deleted on the next run, so
the folder always mirrors the CSV.

The scraper asks for the smallest variant in each card's `srcset` — Ars ships fixed WordPress
sizes and ignores resize query params, so the srcset is the only place to request something
small.

## How it works

The Ars front page is server rendered, so `requests` plus BeautifulSoup is enough — no
JavaScript, no internal API. Every story is an `<article>` card carrying its own headline,
link, `<time datetime>` and `category-*` CSS classes, and cards appear in the order the
editors ranked them, which is what "top" means here.

Lead stories are repeated further down the grid, so only the first appearance of a URL is
kept — that is the one that reflects the story's billing.

### What "today" means

**"Today" is the site's own news day, not the calendar date on this machine.** Ars publishes
on US Eastern time, so from Australia the local date runs a day ahead for most of the working
day and a strict date match returns nothing at all.

So the newest story on the front page sets the clock, and anything published within
`WINDOW_HOURS` (24) of it counts as today's news. That yields the current news cycle whatever
timezone you run it from. Widen or narrow the window by editing that constant.

## Notes

- The front page carries roughly 40 cards covering three days, so there is normally plenty to
  fill a top 10. `TOP_N` at the top of the script sets how many are kept.
- Ars redesigns its front end from time to time. If nothing comes back, check that story cards
  are still `<article>` elements with a `<time datetime>` inside — those are the two things the
  parser leans on.
