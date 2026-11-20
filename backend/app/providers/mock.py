"""Realistic fake award data so the whole app runs before any scraper exists.

Prices are deterministic for a given route and date, vary by season, weekday and
region, and a small random share of dates "go on sale" for each crawl day, so the
deal finder has something real to detect and history builds up across crawls.
"""
from __future__ import annotations

import calendar
import random
from dataclasses import dataclass
from datetime import date

from .. import config
from .base import AwardFare, Provider, Route

REGION_BASE = {
    "domestic": 12_000,
    "canada": 15_000,
    "mexico_caribbean": 17_000,
    "central_america": 20_000,
    "south_america": 30_000,
    "europe": 40_000,
    "asia": 45_000,
    "oceania": 55_000,
    "middle_east_africa": 48_000,
}
ALL_REGIONS = frozenset(REGION_BASE)


@dataclass(frozen=True)
class Profile:
    factor: float              # price level relative to REGION_BASE
    regions: frozenset[str]
    availability: float        # share of days with award space
    round_to: int
    nonstops: frozenset[str]
    fare_brand: str
    partner: dict[str, str]    # region -> operating partner prefix for flight numbers
    intl_taxes: float
    europe_taxes: float
    shows_seats: bool = True


PROFILES: dict[str, Profile] = {
    "UA": Profile(1.0, ALL_REGIONS, 0.8, 500, frozenset({"DEN", "ORD", "SFO", "LAX"}),
                  "Economy Saver", {}, 45, 60),
    "AC": Profile(0.9, ALL_REGIONS, 0.8, 500, frozenset({"YYZ"}),
                  "Economy Standard", {"domestic": "UA", "mexico_caribbean": "UA"}, 45, 70),
    "BA": Profile(0.85, ALL_REGIONS - {"oceania"}, 0.75, 250, frozenset({"LHR"}),
                  "Economy Reward", {"domestic": "AA", "mexico_caribbean": "AA",
                                     "central_america": "AA", "south_america": "AA", "canada": "AA"}, 90, 220),
    "VS": Profile(0.8, ALL_REGIONS - {"oceania", "middle_east_africa"}, 0.75, 500, frozenset(),
                  "Economy Classic", {r: "DL" for r in ALL_REGIONS - {"europe"}}, 60, 160),
    "WN": Profile(0.75, frozenset({"domestic", "mexico_caribbean", "central_america"}), 0.95, 1,
                  frozenset({"DEN", "LAS", "MCO", "LAX", "SAN", "MSY", "BOS", "CUN", "SJD"}),
                  "Wanna Get Away", {}, 55, 55, shows_seats=False),
}

SALE_CHANCE = 0.025


class MockProvider(Provider):
    def __init__(self, code: str, today: date | None = None):
        self.code = code
        self.profile = PROFILES[code]
        self.today = today or date.today()

    def serves(self, destination: str, region: str) -> bool:
        return region in self.profile.regions

    async def fetch_month(self, route: Route, year: int, month: int) -> list[AwardFare]:
        days = calendar.monthrange(year, month)[1]
        fares = (self._fare(route, date(year, month, d)) for d in range(1, days + 1))
        return [f for f in fares if f is not None]

    def _fare(self, route: Route, day: date) -> AwardFare | None:
        p = self.profile
        far_end = route.destination if route.origin == config.ORIGIN else route.origin
        seed = f"{self.code}|{route.origin}|{route.destination}|{day.isoformat()}"
        rng = random.Random(seed)
        if rng.random() > p.availability:
            return None

        route_level = random.Random(f"{self.code}|{far_end}").uniform(0.85, 1.15)
        peak = day.month in (6, 7, 8) or (day.month == 12 and day.day >= 15) or (day.month == 1 and day.day <= 5)
        season = 1.25 if peak else 1.0
        weekday = {4: 1.12, 6: 1.12, 1: 0.92, 2: 0.92}.get(day.weekday(), 1.0)
        noise = rng.uniform(0.9, 1.12)

        # A sale is re-rolled each crawl day, so prices move between crawls.
        sale_rng = random.Random(f"{seed}|{self.today.isoformat()}")
        sale = sale_rng.uniform(0.4, 0.65) if sale_rng.random() < SALE_CHANCE else 1.0

        raw = REGION_BASE[route.region] * p.factor * route_level * season * weekday * noise * sale
        points = max(p.round_to, int(round(raw / p.round_to)) * p.round_to)

        if route.region == "domestic":
            taxes = 5.60
        elif route.region == "europe":
            taxes = p.europe_taxes
        else:
            taxes = p.intl_taxes

        stops = 0 if far_end in p.nonstops else (2 if route.region in ("oceania", "asia") and rng.random() < 0.3 else 1)
        carrier = p.partner.get(route.region, self.code)
        flights = tuple(f"{carrier}{rng.randint(100, 2999)}" for _ in range(stops + 1))

        return AwardFare(
            date=day,
            points=points,
            taxes_usd=taxes,
            cabin="economy",
            fare_brand=p.fare_brand,
            seats=rng.randint(1, 9) if p.shows_seats else None,
            stops=stops,
            flights=flights,
        )
