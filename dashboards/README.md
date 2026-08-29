# Dashboards

Each folder here turns scraped CSVs into a self contained `dashboard.html` — no server, no
network, no external assets, so the page opens straight from disk.

| Dashboard | Reads | Shows |
| --- | --- | --- |
| [woolworths](woolworths) | [WoolworthsScraper](../WoolworthsScraper) | Steak prices normalised to dollars per kilogram |
| [headlines](headlines) | [ArsTechnicaScraper](../ArsTechnicaScraper), [NewsComAuScraper](../NewsComAuScraper) | Today's top 10 from each masthead, side by side |

## Conventions

- **The CSV is the interface.** A dashboard reads CSVs and nothing else. It never fetches, so
  it always renders whatever the last scrape left behind.
- **The HTML is generated output.** Edit `dashboard.py` and re-run it; never hand-edit the HTML.
- **Paths resolve against the script, not the working directory.** Dashboards read CSVs out of
  other folders, so unlike the scrapers they can be run from anywhere.
- **One shared visual language.** Same colour tokens, same type scale, same card treatment, and
  the same colour-blind-validated series palette across every dashboard.

```bash
python3 dashboards/woolworths/dashboard.py
python3 dashboards/headlines/dashboard.py
```

The headlines dashboard also ships an optional [`serve.py`](headlines/serve.py) that serves the
page and wires up its refresh buttons, plus a double-clickable
[`start-dashboard.command`](headlines/start-dashboard.command) that starts it and opens the page.
Both are additions, not requirements — the generated HTML is self-contained either way.
