"""Scrape today's top headlines from the Ars Technica front page.

Ars serves its front page as plain HTML, so BeautifulSoup is enough. Every
story is an <article> card carrying its own headline, link, timestamp and
category, and the order the cards appear in is the order the editors chose,
which is what "top" means here.

Writes ars_technica_headlines.csv next to this file.
"""

import csv
import datetime

import requests
from bs4 import BeautifulSoup

HOME_URL = "https://arstechnica.com/"
CSV_FILE = "ars_technica_headlines.csv"
TOP_N = 10

# "Today" is the site's own news day, not the calendar date on this machine.
# Ars publishes on US Eastern time, so from Australia the local date is a day
# ahead for most of the working day and a strict date match returns nothing.
# Instead the newest story on the front page sets the clock, and anything
# published within this many hours of it counts as today's news.
WINDOW_HOURS = 24

# Slugs that title-casing would otherwise mangle into "Ai" or "It".
SECTION_ACRONYMS = {"ai": "AI", "it": "IT", "us": "US", "uk": "UK"}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def fetch_home():
    response = requests.get(HOME_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def article_link(card):
    """The story URL, which is the first link on the card pointing at a post."""
    for anchor in card.find_all("a", href=True):
        href = anchor["href"]
        if "arstechnica.com/" in href and "/20" in href:
            return href.split("?")[0]
    return None


def section(card):
    """Ars tags each card with its categories as category-* CSS classes."""
    for name in card.get("class", []):
        if name.startswith("category-"):
            slug = name[len("category-"):]
            return SECTION_ACRONYMS.get(slug, slug.replace("-", " ").title())
    return ""


def parse_time(card):
    stamp = card.find("time")
    if not stamp or not stamp.get("datetime"):
        return None
    try:
        return datetime.datetime.fromisoformat(stamp["datetime"])
    except ValueError:
        return None


def parse_cards(soup):
    """One row per story on the front page, in the order Ars ranked them."""
    stories = []
    seen = set()

    for card in soup.find_all("article"):
        headline = card.find(["h1", "h2", "h3", "h4"])
        url = article_link(card)
        published = parse_time(card)

        # The front page repeats its lead stories further down the grid, so the
        # first appearance of a URL is the one that reflects its billing.
        if not headline or not url or not published or url in seen:
            continue
        seen.add(url)

        summary = card.find("p")
        stories.append({
            "headline": headline.get_text(" ", strip=True),
            "url": url,
            "section": section(card),
            "published": published,
            "summary": summary.get_text(" ", strip=True) if summary else "",
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
    stories = todays_stories(parse_cards(fetch_home()))

    if not stories:
        print("No headlines found - the front page markup has probably changed.")
        return

    print("\nARS TECHNICA - TOP " + str(len(stories)) + " TODAY")
    print("-" * 72)

    for rank, story in enumerate(stories, start=1):
        print("{:>2}. {}".format(rank, story["headline"]))
        print("    " + story["section"] + "  -  " + story["published"].strftime("%-d %b %-I:%M%p").lower())

    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["rank", "headline", "url", "section", "published", "summary"],
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
            })

    print("\nSaved " + str(len(stories)) + " headlines to " + CSV_FILE)


if __name__ == "__main__":
    main()
