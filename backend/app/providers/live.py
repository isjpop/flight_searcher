"""Real scrapers, one class per airline. Not written yet - each needs the airline's
network requests captured from DevTools first (see README, "Writing a live scraper").

Enable one with FLIGHTS_LIVE=UA (comma-separated for several). Until a scraper is
implemented its crawl run fails fast with a clear message and mock data is untouched.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .. import config
from .base import AwardFare, Provider, Route
from .browser import BrowserSession


class LiveProvider(Provider):
    min_delay_s = 30.0
    jitter_s = 30.0
    # Notes shown in the NotImplementedError until the scraper exists.
    notes = ""

    def __init__(self) -> None:
        self.browser = BrowserSession(self.code)

    async def fetch_month(self, route: Route, year: int, month: int) -> list[AwardFare]:
        raise NotImplementedError(
            f"{self.code} live scraper is not written yet. {self.notes}".strip()
        )

    def save_raw(self, route: Route, year: int, month: int, payload: Any) -> None:
        """Keep the raw response so parsing bugs can be fixed without re-scraping."""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = config.RAW_DIR / self.code / f"{route.origin}-{route.destination}-{year}-{month:02d}-{stamp}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))

    async def close(self) -> None:
        await self.browser.close()


class UnitedProvider(LiveProvider):
    code = "UA"
    notes = ("Use the united.com award calendar (Book with miles, flexible dates), which "
             "returns a month of prices per request. Report the lowest economy award, "
             "including basic economy if shown.")


class AirCanadaProvider(LiveProvider):
    code = "AC"
    notes = ("Use the aircanada.com Aeroplan search with flexible dates. Includes partner "
             "space (United, etc.). Report the lowest economy price (Standard fare).")


class BritishAirwaysProvider(LiveProvider):
    code = "BA"
    notes = ("Use the ba.com Reward Flight Finder / Avios calendar. Covers BA's AUS-LHR "
             "nonstop and partner flights (American) on other routes. Report the lowest "
             "economy reward price; record taxes, which are high on BA-operated flights.")


class VirginAtlanticProvider(LiveProvider):
    code = "VS"
    notes = ("Use the virginatlantic.com reward-seat calendar. Includes partner space "
             "(Delta). Report the lowest economy reward price.")


class SouthwestProvider(LiveProvider):
    code = "WN"
    # Southwest is strict about automated traffic: go slower than the others.
    min_delay_s = 60.0
    jitter_s = 60.0
    notes = ("Use southwest.com low-fare calendar with 'Points' selected. Report the "
             "cheapest fare bundle shown (e.g. Basic / Wanna Get Away). Points track cash "
             "prices, so deals here are fare sales.")


LIVE_PROVIDERS: dict[str, type[LiveProvider]] = {
    cls.code: cls
    for cls in (UnitedProvider, AirCanadaProvider, BritishAirwaysProvider,
                VirginAtlanticProvider, SouthwestProvider)
}
