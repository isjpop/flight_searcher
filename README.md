# flight_searcher

Finds me the best round-trip award flights from AUS to any city, as long as the points price is well below normal.

A localhost-only app: a Python backend crawls five loyalty programs in the background into SQLite, and a React UI searches the results.

| Airline | Program | Currency |
|---|---|---|
| British Airways | British Airways Club | Avios |
| Air Canada | Aeroplan | Aeroplan points |
| United | MileagePlus | miles |
| Virgin Atlantic | Flying Club | Virgin Points |
| Southwest | Rapid Rewards | points |

> **Status:** every airline currently uses **mock data**. The whole app works end to end, but real prices need the live scrapers in `backend/app/providers/live.py` to be written, one airline at a time (see below).

## Run it

```bash
make setup     # Python venv + npm install (once)
make crawl     # fill the database (mock data takes ~10 seconds)
make dev       # API on 127.0.0.1:8000, UI on http://127.0.0.1:5173
```

Or run `make build` once and then only `make backend`: the API serves the built UI at http://127.0.0.1:8000.

Both servers bind to `127.0.0.1`, so nothing is reachable from other machines. The database lives in `backend/data/` and is git-ignored.

## How it works

```
scheduler (every 12h) ─▶ crawler ─▶ provider per airline ─▶ SQLite ─▶ deal finder ─▶ FastAPI ─▶ React UI
                                     (mock or live)
```

- **Crawler** (`app/crawler.py`): for each airline, enabled destination, direction (AUS→X and X→AUS) and month in the next 330 days, it asks the provider for a month of prices. Airlines run in parallel; requests to one airline go one at a time with a delay (30–60 s for live scrapers, 60–120 s for Southwest).
- **Cheapest cabin only**: providers report one fare per day, the lowest price in the cheapest cabin sold (basic economy or Wanna Get Away when offered).
- **Storage** (`app/db.py`): `fares_current` holds the latest price per route and date. `fare_history` gets a row only when a price changes. Dates that sell out are removed from `fares_current`.
- **Normal price** (`app/deals.py`): the median of all prices seen for that airline and route over the last 90 days, across all travel dates. A route needs 20 observations before it counts.
- **Round trips**: an outbound and a return leg whose gap fits your nights range, ranked by price ÷ normal price. By default both legs use the same program. "Allow a different program each way" pairs across programs and ranks by the average of the two legs' ratios, because the currencies differ.
- **Freshness**: fares last checked more than 72 hours ago are left out of results.

## Settings

Environment variables (see `backend/app/config.py`):

| Variable | Default | |
|---|---|---|
| `FLIGHTS_LIVE` | *(empty)* | Airlines that use their real scraper, e.g. `UA,AC` |
| `FLIGHTS_CRAWL_INTERVAL_HOURS` | `12` | How often the background crawl runs |
| `FLIGHTS_HORIZON_DAYS` | `330` | How far ahead to search |
| `FLIGHTS_FRESH_HOURS` | `72` | Ignore fares older than this |
| `FLIGHTS_BASELINE_LOOKBACK_DAYS` | `90` | Window for the normal price |
| `FLIGHTS_SCHEDULER` | `1` | Set `0` to only crawl when you click "Crawl now" |

## Writing a live scraper

1. `make setup-live` installs Playwright and Chromium.
2. Open the airline's award search in Chrome with DevTools → Network → Fetch/XHR. Search AUS → somewhere with flexible dates and find the request that returns the price calendar as JSON. Note its URL and response shape.
3. Implement `fetch_month` on that airline's class in `backend/app/providers/live.py`. Use `self.browser.capture_json(search_page_url, "<part of the JSON request URL>")`, call `self.save_raw(...)`, and turn the JSON into `AwardFare`s for the cheapest cabin.
4. Run `FLIGHTS_LIVE=UA make crawl AIRLINES=UA` with a single destination enabled first. A real, visible browser window opens; the profile in `backend/data/browser-profiles/` keeps cookies between runs.

Scraping goes against these sites' terms of service. Keep it personal, slow and small: don't log in unless required, and don't share the data.

**Request budget:** live crawls are slow by design. Each enabled destination costs about 2 directions × 11 months = 22 requests per airline, so 30 destinations ≈ 660 requests ≈ 8 hours per airline at 45 s each. Airlines run in parallel, but keep the destination list short.

## Tests

```bash
make test
```
