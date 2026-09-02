"""Scrape today's top headlines from the Ars Technica front page.

Ars serves its front page as plain HTML, so BeautifulSoup is enough. Every
story is an <article> card carrying its own headline, link, timestamp and
category, and the order the cards appear in is the order the editors chose,
which is what "top" means here.

Writes ars_technica_headlines.csv next to this file.
"""

import csv
import datetime
import io
import os

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

# Card images are saved beside the CSV and referenced from it by path, so the
# dashboard never has to go to the network to render one. 128px square is twice
# the size they are displayed at, which keeps them crisp on a retina screen.
THUMBNAIL_DIR = "thumbnails"
THUMBNAIL_PX = 128

# Slugs that title-casing would otherwise mangle into "Ai" or "It".
SECTION_ACRONYMS = {"ai": "AI", "it": "IT", "us": "US", "uk": "UK"}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


def start_session():
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def fetch_home(session):
    response = session.get(HOME_URL, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def image_url(card):
    """The smallest variant the card offers - these get displayed tiny.

    Ars ships fixed WordPress sizes in a srcset and ignores resize query
    params, so the srcset is the only place to ask for something small.
    """
    image = card.find("img")
    if not image:
        return ""

    smallest = None
    for candidate in (image.get("srcset") or "").split(","):
        parts = candidate.split()
        if len(parts) == 2 and parts[1].endswith("w"):
            width = int(parts[1][:-1])
            if smallest is None or width < smallest[0]:
                smallest = (width, parts[0])

    return smallest[1] if smallest else (image.get("src") or "")


def shrink(data):
    """Centre-crop to a square and scale down.

    Pillow is optional. Without it the image is stored at whatever size the
    site served, which still renders, just heavier.
    """
    try:
        from PIL import Image
    except ImportError as error:
        # Say so rather than silently storing a full-size image: a page four
        # times heavier than it should be is not an obvious symptom.
        print("  [Pillow unavailable, storing image as served: " + str(error) + "]")
        return data

    image = Image.open(io.BytesIO(data))
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    square = image.crop((left, top, left + side, top + side))
    square = square.convert("RGB").resize((THUMBNAIL_PX, THUMBNAIL_PX), Image.LANCZOS)

    buffer = io.BytesIO()
    square.save(buffer, "JPEG", quality=80, optimize=True)
    return buffer.getvalue()


def save_thumbnail(session, url, name):
    """Fetch one card image. Returns the path to record in the CSV, or ""."""
    if not url:
        return ""

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    path = os.path.join(THUMBNAIL_DIR, name + ".jpg")
    with open(path, "wb") as file:
        file.write(shrink(response.content))
    return path


def prune_thumbnails(keep):
    """Drop thumbnails from earlier runs so the folder tracks the current top N."""
    if not os.path.isdir(THUMBNAIL_DIR):
        return

    for name in os.listdir(THUMBNAIL_DIR):
        path = os.path.join(THUMBNAIL_DIR, name)
        if name.endswith(".jpg") and path not in keep:
            os.remove(path)


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
            # Ars puts the post ID on the card, which makes a stable filename.
            "id": card.get("data-id") or url.strip("/").rsplit("/", 1)[-1],
            "image": image_url(card),
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
    session = start_session()
    stories = todays_stories(parse_cards(fetch_home(session)))

    if not stories:
        print("No headlines found - the front page markup has probably changed.")
        return

    print("\nARS TECHNICA - TOP " + str(len(stories)) + " TODAY")
    print("-" * 72)

    for rank, story in enumerate(stories, start=1):
        story["thumbnail"] = save_thumbnail(session, story["image"], story["id"])
        print("{:>2}. {}".format(rank, story["headline"]))
        print("    " + story["section"] + "  -  "
              + story["published"].strftime("%-d %b %-I:%M%p").lower()
              + ("" if story["thumbnail"] else "  [no image]"))

    prune_thumbnails({story["thumbnail"] for story in stories if story["thumbnail"]})

    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["rank", "headline", "url", "section", "published", "summary", "thumbnail"],
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
                "thumbnail": story["thumbnail"],
            })

    thumbnails = sum(1 for story in stories if story["thumbnail"])
    print("\nSaved " + str(len(stories)) + " headlines to " + CSV_FILE
          + " (" + str(thumbnails) + " thumbnails)")


if __name__ == "__main__":
    main()
