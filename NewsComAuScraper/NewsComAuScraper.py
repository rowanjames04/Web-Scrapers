"""Scrape today's top headlines from the news.com.au front page.

The front page is server rendered, so BeautifulSoup is enough. Every story is
an <article class="storyblock"> carrying its own headline, link, timestamp and
section, and the order the blocks appear in is the order the editors chose,
which is what "top" means here.

Writes news_com_au_headlines.csv next to this file.
"""

import csv
import datetime
import urllib.parse

import requests
from bs4 import BeautifulSoup

HOME_URL = "https://www.news.com.au/"
CSV_FILE = "news_com_au_headlines.csv"
TOP_N = 10

# "Today" is the site's own news day rather than the calendar date on this
# machine, so the scraper behaves the same wherever it runs. The newest story
# on the front page sets the clock and anything published within this many
# hours of it counts as today's news. It also does the useful work of dropping
# the evergreen lifestyle promos the page mixes in, some of them years old.
WINDOW_HOURS = 24

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def fetch_home():
    response = requests.get(HOME_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def text_of(block, selector):
    found = block.select_one(selector)
    return found.get_text(" ", strip=True) if found else ""


def parse_time(block):
    stamp = block.select_one(".storyblock_datetime")
    if not stamp or not stamp.get("datetime"):
        return None
    try:
        return datetime.datetime.fromisoformat(stamp["datetime"])
    except ValueError:
        return None


def parse_blocks(soup):
    """One row per story on the front page, in the order news.com.au ranked them."""
    stories = []
    seen = set()

    for block in soup.select("article.storyblock"):
        link = block.select_one("a.storyblock_title_link")
        published = parse_time(block)

        if not link or not link.get("href") or not published:
            continue

        url = urllib.parse.urljoin(HOME_URL, link["href"]).split("?")[0]

        # The page repeats its lead stories in later modules, so the first
        # appearance of a URL is the one that reflects its billing.
        if url in seen:
            continue
        seen.add(url)

        stories.append({
            "headline": link.get_text(" ", strip=True),
            "url": url,
            "section": text_of(block, ".storyblock_section"),
            "published": published,
            "summary": text_of(block, ".storyblock_standfirst"),
            "label": text_of(block, ".storyblock_label"),
        })

    return stories


def todays_stories(stories):
    """Keep the stories from the site's latest news day, best billed first."""
    if not stories:
        return []

    newest = max(story["published"] for story in stories)
    cutoff = newest - datetime.timedelta(hours=WINDOW_HOURS)
    return [story for story in stories if story["published"] >= cutoff][:TOP_N]


def main():
    stories = todays_stories(parse_blocks(fetch_home()))

    if not stories:
        print("No headlines found - the front page markup has probably changed.")
        return

    print("\nNEWS.COM.AU - TOP " + str(len(stories)) + " TODAY")
    print("-" * 72)

    for rank, story in enumerate(stories, start=1):
        flag = "  [" + story["label"] + "]" if story["label"] else ""
        print("{:>2}. {}{}".format(rank, story["headline"], flag))
        print("    " + (story["section"] or "News") + "  -  "
              + story["published"].strftime("%-d %b %-I:%M%p").lower())

    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["rank", "headline", "url", "section", "published", "summary", "label"],
        )
        writer.writeheader()
        for rank, story in enumerate(stories, start=1):
            writer.writerow({
                "rank": rank,
                "headline": story["headline"],
                "url": story["url"],
                "section": story["section"],
                "published": story["published"].isoformat(),
                "summary": story["summary"],
                "label": story["label"],
            })

    print("\nSaved " + str(len(stories)) + " headlines to " + CSV_FILE)


if __name__ == "__main__":
    main()
