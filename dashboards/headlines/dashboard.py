"""Build a standalone HTML dashboard from both headline scrapers.

Reads ArsTechnicaScraper/ars_technica_headlines.csv and
NewsComAuScraper/news_com_au_headlines.csv, and writes dashboard.html next to
this file, which needs no server, no network and no dependencies.

Unlike the scrapers, a dashboard reads CSVs that live in other folders, so
paths here resolve against this file rather than the working directory.
"""

import base64
import csv
import datetime
import html
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

HTML_FILE = os.path.join(HERE, "dashboard.html")

# Column order on the page is this list's order: Ars Technica left,
# news.com.au right. Colours are (light, dark) and come from the same
# colour-blind-validated palette the Woolworths dashboard uses.
SOURCES = [
    {
        "key": "ars",
        "name": "Ars Technica",
        "home": "https://arstechnica.com/",
        "blurb": "US technology, science and policy",
        "csv": os.path.join(REPO, "ArsTechnicaScraper", "ars_technica_headlines.csv"),
        "scraper": "ArsTechnicaScraper.py",
        "colour": ("#2a78d6", "#3987e5"),  # blue
    },
    {
        "key": "news",
        "name": "news.com.au",
        "home": "https://www.news.com.au/",
        "blurb": "Australian general news",
        "csv": os.path.join(REPO, "NewsComAuScraper", "news_com_au_headlines.csv"),
        "scraper": "NewsComAuScraper.py",
        "colour": ("#eb6834", "#d95926"),  # orange
    },
]


def read_source(source):
    """Rows for one source, plus when its CSV was last written."""
    if not os.path.exists(source["csv"]):
        return None, None

    with open(source["csv"], newline="") as file:
        rows = list(csv.DictReader(file))

    stories = []
    for row in rows:
        published = parse_time(row.get("published"))
        if published is None:
            continue
        stories.append({
            "rank": row.get("rank", ""),
            "headline": row.get("headline", ""),
            "url": row.get("url", ""),
            "section": row.get("section", ""),
            "published": published,
            "summary": row.get("summary", ""),
            # Only news.com.au carries an editorial flag, so treat it as optional.
            "label": row.get("label", ""),
            "thumbnail": thumbnail_uri(source["csv"], row.get("thumbnail", "")),
        })

    stories.sort(key=lambda story: int(story["rank"]) if story["rank"].isdigit() else 999)
    return stories, datetime.datetime.fromtimestamp(os.path.getmtime(source["csv"]))


def thumbnail_uri(csv_path, thumbnail):
    """Inline a scraped thumbnail as a data URI.

    The CSV records a path relative to itself, and the bytes get embedded
    rather than linked so the page stays self-contained and works offline.
    Anything missing renders as an empty slot rather than a broken image.
    """
    if not thumbnail:
        return ""

    path = os.path.join(os.path.dirname(csv_path), thumbnail)
    if not os.path.isfile(path):
        return ""

    with open(path, "rb") as file:
        return "data:image/jpeg;base64," + base64.b64encode(file.read()).decode("ascii")


def parse_time(value):
    try:
        return datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def clock(moment):
    return "{h}:{m:02d}{ampm}".format(
        h=(moment.hour - 1) % 12 + 1,
        m=moment.minute,
        ampm="am" if moment.hour < 12 else "pm",
    )


def stamp(moment):
    return "{d} {mon} {time}".format(d=moment.day, mon=moment.strftime("%b"), time=clock(moment))


def offset_label(moment):
    """'UTC+10', 'UTC-4', 'UTC+9:30' - the site's own timezone, stated plainly."""
    offset = moment.utcoffset()
    if offset is None:
        return ""

    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "−"
    hours, minutes = divmod(abs(minutes), 60)
    return "UTC{}{}{}".format(sign, hours, ":{:02d}".format(minutes) if minutes else "")


def build_styles():
    """One --series token per source, declared in all three theme blocks."""
    def rules(shade, indent):
        return "\n".join(
            "{}.src-{} {{ --series: {}; }}".format(indent, source["key"], source["colour"][shade])
            for source in SOURCES
        )

    return "\n".join([
        rules(0, "  "),
        '  @media (prefers-color-scheme: dark) {',
        '    :root:not([data-theme="light"]) {',
        rules(1, "      "),
        "    }",
        "  }",
        '  :root[data-theme="dark"] {',
        rules(1, "    "),
        "  }",
    ])


def build_story(story):
    meta = []
    if story["label"]:
        meta.append('<span class="flag">{}</span>'.format(html.escape(story["label"])))
    if story["section"]:
        meta.append(html.escape(story["section"]))
    meta.append(stamp(story["published"]))

    thumbnail = (
        '<img class="thumb" src="{}" alt="" loading="lazy" width="56" height="56">'.format(
            story["thumbnail"]
        )
        if story["thumbnail"]
        else '<div class="thumb thumb-empty" aria-hidden="true"></div>'
    )

    return (
        '<li class="story">'
        '<span class="rank">{rank}</span>'
        "{thumbnail}"
        '<div class="story-body">'
        '<a class="story-headline" href="{url}" target="_blank" '
        'rel="noopener noreferrer">{headline}</a>'
        '<div class="story-meta">{meta}</div>'
        "{summary}"
        "</div></li>".format(
            rank=html.escape(story["rank"]),
            thumbnail=thumbnail,
            url=html.escape(story["url"], quote=True),
            headline=html.escape(story["headline"]),
            meta=' <span class="sep">·</span> '.join(meta),
            summary='<p class="story-summary">{}</p>'.format(html.escape(story["summary"]))
            if story["summary"]
            else "",
        )
    )


def build_column(source, stories, scraped):
    if not stories:
        return (
            '<section class="card col src-{key}">'
            '<div class="col-head"><span class="dot"></span>'
            "<h2>{name}</h2></div>"
            '<p class="col-note">No headlines yet. Run <code>{scraper}</code> to fill this '
            "column.</p></section>".format(
                key=source["key"],
                name=html.escape(source["name"]),
                scraper=html.escape(source["scraper"]),
            )
        )

    newest = max(story["published"] for story in stories)
    oldest = min(story["published"] for story in stories)
    sections = {story["section"] for story in stories if story["section"]}

    return (
        '<section class="card col src-{key}">'
        '<div class="col-head">'
        '<span class="dot"></span>'
        '<h2><a href="{home}" target="_blank" rel="noopener noreferrer">{name}</a></h2>'
        '<span class="col-blurb">{blurb}</span>'
        "</div>"
        '<div class="col-stats">'
        "<span><strong>{count}</strong> headlines</span>"
        "<span><strong>{sections}</strong> sections</span>"
        "<span>{oldest} &ndash; {newest}</span>"
        "</div>"
        '<p class="col-note">Times are the site\'s own, {offset}. '
        "Scraped {scraped}.</p>"
        '<ol class="stories">{stories}</ol>'
        "</section>".format(
            key=source["key"],
            home=html.escape(source["home"], quote=True),
            name=html.escape(source["name"]),
            blurb=html.escape(source["blurb"]),
            count=len(stories),
            sections=len(sections),
            oldest=stamp(oldest),
            newest=stamp(newest),
            offset=offset_label(newest) or "timezone unknown",
            scraped=stamp(scraped),
            stories="\n".join(build_story(story) for story in stories),
        )
    )


TEMPLATE = """<title>Today's Headlines: Ars Technica and news.com.au</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    color-scheme: light;
    --plane: #f4f2ee;
    --surface: #fbfaf8;
    --ink: #12120f;
    --ink-2: #52514c;
    --muted: #8a887f;
    --hairline: #e2e0d8;
    --grid: #eae8e0;
    --good: #0ca30c;
    --flag-ink: #8a5a00;
    --flag-bg: #f6efe0;
    --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
    --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      color-scheme: dark;
      --plane: #0e0e0d;
      --surface: #191917;
      --ink: #f6f5f1;
      --ink-2: #c3c2b7;
      --muted: #8a887f;
      --hairline: #2e2e2b;
      --grid: #262624;
      --good: #0ca30c;
      --flag-ink: #e0b45c;
      --flag-bg: #2a2418;
    }}
  }}
  :root[data-theme="dark"] {{
    color-scheme: dark;
    --plane: #0e0e0d;
    --surface: #191917;
    --ink: #f6f5f1;
    --ink-2: #c3c2b7;
    --muted: #8a887f;
    --hairline: #2e2e2b;
    --grid: #262624;
    --good: #0ca30c;
    --flag-ink: #e0b45c;
    --flag-bg: #2a2418;
  }}

  /* Per-source accent, one token each, declared in every theme block. */
{styles}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--plane);
    color: var(--ink);
    font-family: var(--sans);
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{
    max-width: 1120px;
    margin: 0 auto;
    padding: 40px 24px 64px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }}
  a {{ color: inherit; }}

  .eyebrow {{
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--muted);
  }}
  h1 {{
    margin: 6px 0 0;
    font-size: clamp(26px, 4vw, 36px);
    letter-spacing: -0.02em;
    text-wrap: balance;
  }}
  .lede {{
    margin: 10px 0 0;
    max-width: 68ch;
    color: var(--ink-2);
    font-size: 15px;
  }}

  .columns {{
    display: grid;
    gap: 20px;
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }}
  .card {{
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: 4px;
    padding: 20px 22px 24px;
  }}
  .col {{ border-top: 3px solid var(--series); }}

  .col-head {{
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 10px;
  }}
  .dot {{
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--series); display: inline-block; flex: none;
    align-self: center;
  }}
  h2 {{ margin: 0; font-size: 17px; letter-spacing: -0.01em; }}
  h2 a {{ text-decoration: none; }}
  h2 a:hover {{ text-decoration: underline; }}
  .col-blurb {{ font-size: 12.5px; color: var(--muted); }}

  .col-stats {{
    display: flex; flex-wrap: wrap; gap: 4px 16px;
    margin-top: 12px; padding-bottom: 12px;
    border-bottom: 1px solid var(--hairline);
    font-family: var(--mono); font-size: 11px;
    letter-spacing: 0.04em; text-transform: uppercase; color: var(--muted);
  }}
  .col-stats strong {{ color: var(--ink); font-weight: 600; }}
  .col-note {{ margin: 10px 0 4px; font-size: 12.5px; color: var(--muted); }}
  .col-note code {{ font-family: var(--mono); font-size: 12px; color: var(--ink-2); }}

  .stories {{ list-style: none; margin: 0; padding: 0; }}
  .story {{
    display: grid;
    grid-template-columns: 22px 56px 1fr;
    gap: 12px;
    padding: 14px 0;
    border-bottom: 1px solid var(--grid);
  }}
  .thumb {{
    width: 56px; height: 56px;
    border-radius: 3px; object-fit: cover;
    background: var(--grid);
    margin-top: 2px;
  }}
  /* Stories with no card image keep the column, so the text stays aligned.
     A quiet tint reads as "this one had no image" rather than as a broken one. */
  .thumb-empty {{
    background: var(--grid);
  }}
  .story:last-child {{ border-bottom: 0; padding-bottom: 0; }}
  .rank {{
    font-family: var(--mono); font-size: 12.5px; font-variant-numeric: tabular-nums;
    color: var(--series); font-weight: 600; text-align: right; padding-top: 2px;
  }}
  .story-body {{ min-width: 0; }}
  .story-headline {{
    font-size: 15.5px; font-weight: 600; letter-spacing: -0.01em;
    line-height: 1.35; text-decoration: none; text-wrap: balance;
  }}
  .story-headline:hover {{ text-decoration: underline; text-decoration-color: var(--series); }}
  .story-meta {{
    margin-top: 5px;
    font-family: var(--mono); font-size: 10.5px;
    letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted);
  }}
  .story-meta .sep {{ opacity: 0.6; }}
  .story-summary {{
    margin: 7px 0 0; font-size: 13.5px; color: var(--ink-2);
    max-width: 56ch;
  }}
  .flag {{
    font-size: 9.5px; letter-spacing: 0.07em;
    padding: 2px 5px; border-radius: 3px;
    color: var(--flag-ink); background: var(--flag-bg);
  }}
  a:focus-visible {{ outline: 2px solid var(--good); outline-offset: 2px; }}

  footer {{ font-size: 12px; color: var(--muted); border-top: 1px solid var(--hairline); padding-top: 16px; }}
  footer p {{ margin: 0 0 6px; max-width: 76ch; }}

  @media (max-width: 820px) {{
    .columns {{ grid-template-columns: 1fr; }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; }}
  }}
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">Two front pages &middot; side by side</div>
    <h1>Today's headlines</h1>
    <p class="lede">The top {top_n} stories each masthead is leading with, in the order its own
    front page ranks them. Two very different newsrooms, so the interesting bit is rarely the
    overlap &mdash; it is what each one thinks the day is about.</p>
  </header>

  <div class="columns">{columns}</div>

  <footer>
    <p>Rank is front page prominence, not clicks or shares &mdash; neither site publishes a
    public popularity count, so the editors' running order is the honest stand-in.</p>
    <p>&ldquo;Today&rdquo; is each site's own news day rather than this machine's calendar date:
    the newest story on a front page sets that site's clock and the previous 24 hours count as
    today. Ars publishes on US Eastern time, so its day and an Australian one rarely line up.</p>
    <p>Personal news dashboard &mdash; not affiliated with or endorsed by Ars Technica or
    news.com.au. Headlines and summaries are the publishers'; follow a link for the full story.</p>
  </footer>
</div>
"""


def main():
    columns = []
    total = 0
    longest = 0

    for source in SOURCES:
        stories, scraped = read_source(source)
        if stories is None:
            print("Missing " + os.path.relpath(source["csv"], REPO)
                  + " - run " + source["scraper"] + " first.")
            stories, scraped = [], None
        total += len(stories)
        longest = max(longest, len(stories))
        columns.append(build_column(source, stories, scraped))

    if not total:
        print("No headlines in either CSV - nothing to render.")
        return

    page = TEMPLATE.format(
        styles=build_styles(),
        top_n=longest,
        columns="\n".join(columns),
    )

    with open(HTML_FILE, "w") as file:
        file.write(page)

    print("Wrote " + os.path.basename(HTML_FILE) + " (" + str(total) + " headlines)")


if __name__ == "__main__":
    main()
