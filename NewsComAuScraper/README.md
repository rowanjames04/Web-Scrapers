# news.com.au Scraper

Pulls today's top 10 headlines from the [news.com.au](https://www.news.com.au) front page, prints them to the terminal and saves them to `news_com_au_headlines.csv`.

## Requirements

Python 3 plus:

```bash
pip install requests beautifulsoup4
```

## Usage

Run it from inside this folder so the CSV lands here:

```bash
cd NewsComAuScraper && python3 NewsComAuScraper.py
```

Sample output:

```
NEWS.COM.AU - TOP 10 TODAY
------------------------------------------------------------------------
 1. ‘BABY DIED IN AGONY’: US rocked by deaths as outbreak spreads  [Analysis]
    News  -  29 aug 4:06pm
 2. NRL world in tears as Arrow returns to field
    NRL  -  29 aug 4:47pm
 3. 616 now dead, sad twist in hunt for Aussies  [LIVE]
    Incidents  -  28 aug 9:59pm
```

## Output

`news_com_au_headlines.csv` has one row per headline:

| Column | Description |
| --- | --- |
| `rank` | 1 to 10, in front page order |
| `headline` | The headline text |
| `url` | Direct link to the article |
| `section` | Site section, e.g. `NRL`, `Markets`, `Incidents`. Empty on blocks that carry a label instead |
| `published` | Publication time, ISO 8601 with the site's UTC offset |
| `summary` | The block's standfirst, empty when it has none |
| `label` | Editorial flag the site puts on the block: `LIVE`, `Analysis`, `Exclusive`. Usually empty |

## How it works

The front page is server rendered, so `requests` plus BeautifulSoup is enough — no JavaScript,
no internal API. Every story is an `<article class="storyblock">` and its parts are all
namespaced off that class: `.storyblock_title_link` for the headline and URL,
`.storyblock_datetime` for the timestamp, `.storyblock_section`, `.storyblock_standfirst` and
`.storyblock_label`. Blocks appear in the order the editors ranked them, which is what "top"
means here.

Lead stories are repeated in later modules, so only the first appearance of a URL is kept —
that is the one that reflects the story's billing.

### What "today" means

**"Today" is the site's own news day, not the calendar date on this machine.** The newest story
on the front page sets the clock, and anything published within `WINDOW_HOURS` (24) of it counts
as today's news.

That matters more here than the timezone does: the front page mixes evergreen lifestyle and
promo blocks in among the news, some of them a year or two old, and the window drops them
without needing a hand written list of sections to ignore.

## Notes

- The page carries around 90 story blocks, so there is normally plenty to fill a top 10. `TOP_N`
  at the top of the script sets how many are kept.
- Blocks with no `.storyblock_datetime` are skipped outright. Those are ad and navigation
  modules dressed up in the same class, not stories.
- A block's timestamp is its original publication time, which for a rolling `LIVE` story can be
  well behind the "37 minutes ago" the page displays. The CSV records the timestamp, not the
  rendered text.
