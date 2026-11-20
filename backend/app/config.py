"""Runtime settings. Every value can be overridden with an environment variable."""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent
DATA_DIR = Path(os.getenv("FLIGHTS_DATA_DIR", BACKEND_DIR / "data"))
DB_PATH = DATA_DIR / "flights.db"
RAW_DIR = DATA_DIR / "raw"                       # raw JSON saved by live scrapers
BROWSER_PROFILE_DIR = DATA_DIR / "browser-profiles"
FRONTEND_DIST = REPO_DIR / "frontend" / "dist"   # served at / if it has been built

ORIGIN = "AUS"

# How far ahead to crawl. Most programs open their schedule ~330-355 days out.
HORIZON_DAYS = int(os.getenv("FLIGHTS_HORIZON_DAYS", "330"))

# Background crawler.
SCHEDULER_ENABLED = os.getenv("FLIGHTS_SCHEDULER", "1") == "1"
CRAWL_INTERVAL_HOURS = float(os.getenv("FLIGHTS_CRAWL_INTERVAL_HOURS", "12"))

# A fare older than this is treated as stale and left out of results.
FRESH_HOURS = float(os.getenv("FLIGHTS_FRESH_HOURS", "72"))

# "Normal price" = median of observed prices for the route over this window.
BASELINE_LOOKBACK_DAYS = int(os.getenv("FLIGHTS_BASELINE_LOOKBACK_DAYS", "90"))
MIN_BASELINE_SAMPLES = int(os.getenv("FLIGHTS_MIN_BASELINE_SAMPLES", "20"))

# Round-trip pairing only considers legs at or below this fraction of normal.
# Keeps pairing fast; a great round trip almost never includes an overpriced leg.
LEG_PREFILTER_RATIO = 1.0

# Airlines that use their real scraper instead of mock data, e.g. FLIGHTS_LIVE=UA,AC
LIVE_AIRLINES = {
    code.strip().upper()
    for code in os.getenv("FLIGHTS_LIVE", "").split(",")
    if code.strip()
}
