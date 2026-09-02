"""Scrape today's top headlines from the news.com.au front page.

The front page is server rendered, so BeautifulSoup is enough. Every story is
an <article class="storyblock"> carrying its own headline, link, timestamp and
section, and the order the blocks appear in is the order the editors chose,
which is what "top" means here.

Writes news_com_au_headlines.csv next to this file.
"""

import csv
import datetime
import io
import os
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

# Card images are saved beside the CSV and referenced from it by path, so the
# dashboard never has to go to the network to render one. 128px square is twice
# the size they are displayed at, which keeps them crisp on a retina screen.
THUMBNAIL_DIR = "thumbnails"
THUMBNAIL_PX = 128

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


def image_url(block):
    """The smallest variant the block offers - these get displayed tiny.

    The image CDN only serves the widths listed in the srcset and answers 412
    for anything else, so pick from that list rather than inventing a width.
    Blocks leading with an animation carry a <video> and no image at all; those
    come back empty and simply render without a thumbnail.
    """
    image = block.select_one("img.storyblock_img") or block.find("img")
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
            # The site's own article ID makes a stable thumbnail filename.
            "id": block.get("data-article-id") or url.rstrip("/").rsplit("/", 1)[-1],
            "image": image_url(block),
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
    stories = todays_stories(parse_blocks(fetch_home(session)))

    if not stories:
        print("No headlines found - the front page markup has probably changed.")
        return

    print("\nNEWS.COM.AU - TOP " + str(len(stories)) + " TODAY")
    print("-" * 72)

    for rank, story in enumerate(stories, start=1):
        story["thumbnail"] = save_thumbnail(session, story["image"], story["id"])
        flag = "  [" + story["label"] + "]" if story["label"] else ""
        print("{:>2}. {}{}".format(rank, story["headline"], flag))
        print("    " + (story["section"] or "News") + "  -  "
              + story["published"].strftime("%-d %b %-I:%M%p").lower()
              + ("" if story["thumbnail"] else "  [no image]"))

    prune_thumbnails({story["thumbnail"] for story in stories if story["thumbnail"]})

    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["rank", "headline", "url", "section", "published", "summary", "label",
                        "thumbnail"],
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
                "thumbnail": story["thumbnail"],
            })

    thumbnails = sum(1 for story in stories if story["thumbnail"])
    print("\nSaved " + str(len(stories)) + " headlines to " + CSV_FILE
          + " (" + str(thumbnails) + " thumbnails)")


if __name__ == "__main__":
    main()
