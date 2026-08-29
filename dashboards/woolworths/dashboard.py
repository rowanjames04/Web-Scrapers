"""Build a standalone HTML dashboard from the scraped Woolworths prices.

Reads WoolworthsScraper/woolworths_prices.csv (produced by WoolworthsScraper.py)
and writes dashboard.html next to this file, which needs no server, no network
and no dependencies.

Unlike the scrapers, a dashboard reads a CSV that lives in another folder, so
paths here resolve against this file rather than the working directory.
"""

import csv
import datetime
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

CSV_FILE = os.path.join(REPO, "WoolworthsScraper", "woolworths_prices.csv")
HTML_FILE = os.path.join(HERE, "dashboard.html")

# Categorical colours, one per item label, as (light, dark).
# Validated for colour-blind separation against both page surfaces.
SERIES_COLOURS = [
    ("#2a78d6", "#3987e5"),  # blue
    ("#eb6834", "#d95926"),  # orange
    ("#1baf7a", "#199e70"),  # aqua
]

UNIT_PRICE_PATTERN = re.compile(r"\$([\d.]+)\s*/\s*([\d.]*)\s*(KG|G)\b", re.IGNORECASE)
WEIGHT_PATTERN = re.compile(r"([\d.]+)\s*(kg|g)\b", re.IGNORECASE)


def weights_in_grams(package_size):
    """Every weight mentioned in a pack size, in grams ('250g - 700g' -> [250, 700])."""
    grams = []
    for amount, unit in WEIGHT_PATTERN.findall(package_size or ""):
        grams.append(float(amount) * (1000 if unit.lower() == "kg" else 1))
    return grams


def format_grams(grams):
    return "{:g}kg".format(grams / 1000) if grams >= 1000 else "{:g}g".format(grams)


def read_rows():
    with open(CSV_FILE, newline="") as file:
        return list(csv.DictReader(file))


def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def price_per_kg(unit_price):
    """Turn '$45.00 / 1KG' or '$3.40 / 100G' into a plain dollars-per-kg float."""
    match = UNIT_PRICE_PATTERN.search(unit_price or "")
    if not match:
        return None

    amount = float(match.group(1))
    quantity = float(match.group(2)) if match.group(2) else 1.0
    if quantity == 0:
        return None

    per_unit = amount / quantity
    return per_unit * 1000 if match.group(3).upper() == "G" else per_unit


def prepare(rows):
    """Attach derived fields and a stable colour per item label."""
    labels = []
    for row in rows:
        if row["item"] not in labels:
            labels.append(row["item"])

    products = []
    for row in rows:
        colour_index = labels.index(row["item"]) % len(SERIES_COLOURS)
        products.append({
            "item": row["item"],
            "name": row["name"],
            "price": to_float(row["price"]),
            "was_price": to_float(row["was_price"]),
            "on_special": row["on_special"] == "True",
            "per_kg": price_per_kg(row["unit_price"]),
            "package_size": row["package_size"],
            "in_stock": row["in_stock"] == "True",
            "stockcode": row["stockcode"],
            "url": row["url"],
            "colour": SERIES_COLOURS[colour_index],
        })

    return labels, products


def money(value, suffix=""):
    return "—" if value is None else "${:,.2f}{}".format(value, suffix)


def axis_scale(values):
    """Pick a clean step that lands the top of the scale close to the largest bar."""
    top = max(values)
    for step in (1, 2, 5, 10, 15, 20, 25, 50, 100, 250):
        divisions = -(-top // step)  # ceiling division
        if 3 <= divisions <= 5:
            return step * divisions, step
    return top, top / 4


def build_bars(products, axis_max):
    """Sorted horizontal bars: the honest comparison is dollars per kilo."""
    chartable = sorted(
        [p for p in products if p["per_kg"] is not None],
        key=lambda p: p["per_kg"],
    )

    # The cheapest product of each cut gets a "best value" marker.
    best = {}
    for product in chartable:
        if product["item"] not in best:
            best[product["item"]] = product["name"]

    bars = []
    for product in chartable:
        is_best = best.get(product["item"]) == product["name"]
        tooltip = "{} — {} per kg · {} for {}".format(
            product["name"],
            money(product["per_kg"]),
            money(product["price"]),
            product["package_size"],
        )
        bars.append(
            '<div class="bar-row{best_class}">'
            '<div class="bar-name" title="{tooltip}">'
            '{best_tag}<span class="bar-name-text">{name}</span></div>'
            '<div class="bar-track">'
            '<div class="bar-area">'
            '<div class="bar-fill" style="width:{width:.2f}%;--series:{colour}" '
            'title="{tooltip}"></div></div>'
            '<div class="bar-value">{value}</div>'
            "</div></div>".format(
                best_class=" is-best" if is_best else "",
                tooltip=html.escape(tooltip, quote=True),
                name=html.escape(product["name"]),
                best_tag='<span class="best-tag">best value</span>' if is_best else "",
                width=product["per_kg"] / axis_max * 100,
                colour=product["colour"][0],
                value=money(product["per_kg"]),
            )
        )
    return "\n".join(bars), chartable


def build_ticks(axis_max, step):
    ticks = []
    value = 0
    while value <= axis_max + 1e-9:
        ticks.append(
            '<div class="tick" style="left:{:.2f}%"><span>${:,.0f}</span></div>'.format(
                value / axis_max * 100, value
            )
        )
        value += step
    return "\n".join(ticks)


def build_legend(labels):
    swatches = []
    for index, label in enumerate(labels):
        colour = SERIES_COLOURS[index % len(SERIES_COLOURS)][0]
        swatches.append(
            '<span class="key"><span class="dot" style="--series:{}"></span>{}</span>'.format(
                colour, html.escape(label)
            )
        )
    return "".join(swatches)


def build_tiles(labels, products):
    tiles = []
    for index, label in enumerate(labels):
        priced = [p for p in products if p["item"] == label and p["per_kg"] is not None]
        colour = SERIES_COLOURS[index % len(SERIES_COLOURS)][0]

        if not priced:
            tiles.append(
                '<div class="tile"><span class="dot" style="--series:{}"></span>'
                '<div class="tile-label">{}</div>'
                '<div class="tile-value">—</div>'
                '<div class="tile-note">nothing in stock</div></div>'.format(
                    colour, html.escape(label)
                )
            )
            continue

        cheapest = min(priced, key=lambda p: p["per_kg"])
        dearest = max(priced, key=lambda p: p["per_kg"])
        tiles.append(
            '<div class="tile"><span class="dot" style="--series:{colour}"></span>'
            '<div class="tile-label">{label} · cheapest per kg</div>'
            '<div class="tile-value">{value}</div>'
            '<div class="tile-note">{name}</div>'
            '<div class="tile-note muted">{count} products · up to {top} per kg</div>'
            "</div>".format(
                colour=colour,
                label=html.escape(label),
                value=money(cheapest["per_kg"]),
                name=html.escape(cheapest["name"]),
                count=len(priced),
                top=money(dearest["per_kg"]),
            )
        )
    return "\n".join(tiles)


def build_table(products):
    rows = []
    for product in sorted(products, key=lambda p: (p["item"], p["per_kg"] or 9e9)):
        flags = []
        if product["on_special"]:
            flags.append('<span class="flag special">on special</span>')
        if not product["in_stock"]:
            flags.append('<span class="flag out">out of stock</span>')

        rows.append(
            "<tr>"
            '<td><span class="dot" style="--series:{colour}"></span>'
            '<a href="{url}" target="_blank" rel="noopener noreferrer">{name}</a>{flags}</td>'
            '<td class="num">{price}</td>'
            '<td class="num">{size}</td>'
            '<td class="num strong">{per_kg}</td>'
            '<td class="num code">{stockcode}</td>'
            "</tr>".format(
                colour=product["colour"][0],
                url=html.escape(product["url"], quote=True),
                name=html.escape(product["name"]),
                flags=" " + " ".join(flags) if flags else "",
                price=money(product["price"]),
                size=html.escape(product["package_size"]),
                per_kg=money(product["per_kg"]),
                stockcode=html.escape(product["stockcode"]),
            )
        )
    return "\n".join(rows)


TEMPLATE = """<title>Woolworths Steak Price Tracker</title>
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
    --good-ink: #006300;
    --warn-ink: #8a5a00;
    --warn-bg: #f6efe0;
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
      --good-ink: #4cc44c;
      --warn-ink: #e0b45c;
      --warn-bg: #2a2418;
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
    --good-ink: #4cc44c;
    --warn-ink: #e0b45c;
    --warn-bg: #2a2418;
  }}

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
    max-width: 1040px;
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
    max-width: 62ch;
    color: var(--ink-2);
    font-size: 15px;
  }}

  .hero {{
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: 4px;
    padding: 22px 24px;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 20px;
  }}
  .hero-figure {{
    font-family: var(--mono);
    font-size: clamp(40px, 7vw, 58px);
    font-weight: 600;
    letter-spacing: -0.03em;
    line-height: 1;
  }}
  .hero-unit {{ font-size: 0.42em; color: var(--muted); font-weight: 400; }}
  .hero-side {{ color: var(--ink-2); font-size: 14px; max-width: 40ch; }}
  .hero-side strong {{ color: var(--ink); font-weight: 600; }}

  .tiles {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); }}
  .tile {{
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: 4px;
    padding: 16px 18px;
  }}
  .tile-label {{ font-size: 12px; color: var(--ink-2); display: inline; }}
  .tile-value {{
    font-family: var(--mono);
    font-size: 28px;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin-top: 6px;
  }}
  .tile-note {{ font-size: 12.5px; color: var(--ink-2); margin-top: 3px; }}
  .tile-note.muted {{ color: var(--muted); font-family: var(--mono); font-size: 11px; }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--hairline);
    border-radius: 4px;
    padding: 22px 24px 26px;
  }}
  .card-head {{
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: baseline;
    gap: 10px 20px;
    margin-bottom: 4px;
  }}
  h2 {{ margin: 0; font-size: 16px; letter-spacing: -0.01em; }}
  .card-note {{ margin: 4px 0 22px; font-size: 13px; color: var(--ink-2); max-width: 68ch; }}

  .legend {{ display: flex; gap: 16px; flex-wrap: wrap; }}
  .key {{ display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--ink-2); }}
  .dot {{
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--series); display: inline-block; flex: none;
  }}

  /* The tick overlay and the bars share one column system, so a gridline
     always falls exactly where that value falls on a bar. */
  .chart {{
    position: relative;
    --label-col: 310px;
    --value-col: 62px;
    --col-gap: 14px;
    --value-gap: 10px;
  }}
  .ticks {{
    position: absolute; top: 0; bottom: 18px; pointer-events: none;
    left: calc(var(--label-col) + var(--col-gap));
    right: calc(var(--value-col) + var(--value-gap));
  }}
  .tick {{ position: absolute; top: 0; bottom: 0; border-left: 1px solid var(--grid); }}
  .tick:first-child {{ border-left-color: var(--hairline); }}
  .tick span {{
    position: absolute; bottom: -19px; left: 0; transform: translateX(-50%);
    font-family: var(--mono); font-size: 10.5px; color: var(--muted);
  }}
  .bars {{ position: relative; display: flex; flex-direction: column; gap: 2px; padding-bottom: 18px; }}
  .bar-row {{
    display: grid; align-items: center; gap: var(--col-gap);
    grid-template-columns: minmax(0, var(--label-col)) 1fr;
  }}
  .bar-track {{
    display: grid; align-items: center; gap: var(--value-gap);
    grid-template-columns: 1fr var(--value-col);
  }}
  .bar-area {{ position: relative; height: 18px; min-width: 0; }}
  .bar-name {{
    display: flex; align-items: baseline; justify-content: flex-end; gap: 7px;
    font-size: 12.5px; color: var(--ink-2); min-width: 0;
  }}
  .bar-name-text {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .is-best .bar-name {{ color: var(--ink); font-weight: 600; }}
  .best-tag {{
    font-family: var(--mono); font-size: 9.5px; text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--good-ink); font-weight: 500;
    flex: none; order: -1;
  }}
  .bar-fill {{
    position: absolute; left: 0; top: 0; height: 18px;
    background: var(--series);
    border-radius: 0 4px 4px 0; transition: filter 0.12s ease;
  }}
  .bar-row:hover .bar-fill {{ filter: brightness(1.08); }}
  .bar-value {{
    font-family: var(--mono); font-size: 12.5px; font-variant-numeric: tabular-nums;
    color: var(--ink); white-space: nowrap;
  }}

  .table-scroll {{ overflow-x: auto; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; min-width: 620px; }}
  th {{
    text-align: left; font-family: var(--mono); font-size: 10.5px; font-weight: 500;
    letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted);
    padding: 0 12px 8px 0; border-bottom: 1px solid var(--hairline);
  }}
  td {{ padding: 10px 12px 10px 0; border-bottom: 1px solid var(--grid); vertical-align: top; }}
  td .dot {{ margin-right: 8px; vertical-align: middle; }}
  .num {{ text-align: right; font-family: var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }}
  .num.strong {{ font-weight: 600; }}
  .code {{ color: var(--muted); font-size: 12px; }}
  th.num {{ text-align: right; }}
  tbody tr:hover td {{ background: var(--grid); }}
  td a {{ text-decoration: none; border-bottom: 1px solid var(--hairline); }}
  td a:hover {{ border-bottom-color: currentColor; }}
  a:focus-visible, tr:focus-visible {{ outline: 2px solid var(--good); outline-offset: 2px; }}

  .flag {{
    font-family: var(--mono); font-size: 9.5px; text-transform: uppercase;
    letter-spacing: 0.07em; padding: 2px 6px; border-radius: 3px;
    white-space: nowrap; margin-left: 6px;
  }}
  .flag.special {{ color: var(--good-ink); border: 1px solid var(--good); }}
  .flag.out {{ color: var(--warn-ink); background: var(--warn-bg); }}

  footer {{ font-size: 12px; color: var(--muted); border-top: 1px solid var(--hairline); padding-top: 16px; }}
  footer p {{ margin: 0 0 6px; max-width: 70ch; }}

  @media (max-width: 620px) {{
    .chart {{ --label-col: 0px; --col-gap: 0px; }}
    .bar-row {{ grid-template-columns: 1fr; gap: 3px; }}
    .bar-name {{ justify-content: flex-start; }}
    .ticks {{ display: none; }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    * {{ transition: none !important; }}
  }}
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">Woolworths · price tracker</div>
    <h1>Steak, by the kilo</h1>
    <p class="lede">Shelf price alone can't tell you which steak is better value here &mdash; the packs
    run from {smallest} to {largest}. Every figure below is normalised to dollars per kilogram.</p>
  </header>

  <section class="hero">
    <div class="hero-figure">{hero_value}<span class="hero-unit"> / kg</span></div>
    <div class="hero-side">Best value on the board: <strong>{hero_name}</strong>,
    {hero_price} for {hero_size}.</div>
  </section>

  <section class="tiles">{tiles}</section>

  <section class="card">
    <div class="card-head">
      <h2>Price per kilogram</h2>
      <div class="legend">{legend}</div>
    </div>
    <p class="card-note">Sorted cheapest first. {excluded_note}</p>
    <div class="chart">
      <div class="ticks">{ticks}</div>
      <div class="bars">{bars}</div>
    </div>
  </section>

  <section class="card">
    <div class="card-head"><h2>Every product</h2></div>
    <p class="card-note">Shelf price is what you pay at the register; the per-kilo column is what
    makes the packs comparable.</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Product</th>
            <th class="num">Shelf price</th>
            <th class="num">Pack size</th>
            <th class="num">Per kg</th>
            <th class="num">Stockcode</th>
          </tr>
        </thead>
        <tbody>{table}</tbody>
      </table>
    </div>
  </section>

  <footer>
    <p>Prices scraped from woolworths.com.au on {scraped}. These are national online prices and
    may differ from your local store. Variable-weight cuts are priced on a range, so the per-kilo
    figure is the site's own.</p>
    <p>Personal price tracker &mdash; not affiliated with or endorsed by Woolworths.</p>
  </footer>
</div>
"""


def main():
    rows = read_rows()
    if not rows:
        print("No rows in " + os.path.relpath(CSV_FILE, REPO) + " - run WoolworthsScraper.py first.")
        return

    labels, products = prepare(rows)
    axis_max, axis_step = axis_scale([p["per_kg"] for p in products if p["per_kg"] is not None])
    bars, chartable = build_bars(products, axis_max)

    excluded = len(products) - len(chartable)
    excluded_note = (
        "All {} products shown.".format(len(chartable))
        if not excluded
        else "{} product{} without a current per-kilo price {} left out of the chart and listed "
        "in the table below.".format(
            excluded, "" if excluded == 1 else "s", "is" if excluded == 1 else "are"
        )
    )

    best = min(chartable, key=lambda p: p["per_kg"])
    grams = [g for p in products for g in weights_in_grams(p["package_size"])]
    scraped = datetime.datetime.fromtimestamp(os.path.getmtime(CSV_FILE))

    page = TEMPLATE.format(
        smallest=format_grams(min(grams)),
        largest=format_grams(max(grams)),
        hero_value=money(best["per_kg"]),
        hero_name=html.escape(best["name"]),
        hero_price=money(best["price"]),
        hero_size=html.escape(best["package_size"]),
        tiles=build_tiles(labels, products),
        legend=build_legend(labels),
        ticks=build_ticks(axis_max, axis_step),
        bars=bars,
        excluded_note=html.escape(excluded_note),
        table=build_table(products),
        scraped="{d} {t} at {h}:{m:02d}{ampm}".format(
            d=scraped.day,
            t=scraped.strftime("%B %Y"),
            h=(scraped.hour - 1) % 12 + 1,
            m=scraped.minute,
            ampm="am" if scraped.hour < 12 else "pm",
        ),
    )

    with open(HTML_FILE, "w") as file:
        file.write(page)

    print("Wrote " + os.path.basename(HTML_FILE) + " (" + str(len(chartable)) + " products charted)")


if __name__ == "__main__":
    main()
