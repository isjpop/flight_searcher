"""The interface every airline data source implements, mock or live."""
from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class Route:
    origin: str
    destination: str
    region: str  # region of the non-AUS end, see seed.REGIONS


@dataclass(frozen=True)
class AwardFare:
    """The cheapest bookable award for one route on one day.

    Providers must report the lowest price in the CHEAPEST cabin the program sells
    on that day - basic economy or its equivalent when offered - not premium cabins.
    """

    date: date
    points: int
    taxes_usd: float
    cabin: str = "economy"
    fare_brand: str | None = None      # e.g. "Wanna Get Away", "Economy Saver"
    seats: int | None = None           # None when the site does not show a count
    stops: int = 0
    flights: tuple[str, ...] = field(default_factory=tuple)  # e.g. ("UA1234", "UA567")


def cheapest_per_day(fares: Iterable[AwardFare]) -> list[AwardFare]:
    """Keep one fare per date: fewest points, then lowest taxes."""
    best: dict[date, AwardFare] = {}
    for f in fares:
        cur = best.get(f.date)
        if cur is None or (f.points, f.taxes_usd) < (cur.points, cur.taxes_usd):
            best[f.date] = f
    return [best[d] for d in sorted(best)]


class Provider(ABC):
    code: str
    # Pause between requests. Live scrapers must go slowly to avoid being blocked.
    min_delay_s: float = 0.0
    jitter_s: float = 0.0

    def serves(self, destination: str, region: str) -> bool:
        """Whether this program can plausibly book AUS <-> destination."""
        return True

    @abstractmethod
    async def fetch_month(self, route: Route, year: int, month: int) -> list[AwardFare]:
        """Return award fares for every available day of the given month.

        Prefer the site's calendar / flexible-dates view: one request per month
        instead of one per day. Days without award space are simply omitted.
        """

    async def pause(self) -> None:
        await asyncio.sleep(self.min_delay_s + random.uniform(0, self.jitter_s))

    async def close(self) -> None:
        """Release browsers or sessions."""
