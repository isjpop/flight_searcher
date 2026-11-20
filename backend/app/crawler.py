"""Walks every (airline, destination, direction, month) and stores the results.

Airlines run concurrently; requests within one airline run one at a time with the
provider's own delay, so each site sees slow, human-paced traffic.
"""
from __future__ import annotations

import asyncio
import calendar
import logging
from datetime import date, timedelta

from . import config, db
from .providers import Provider, Route, build_providers, cheapest_per_day, provider_mode

log = logging.getLogger(__name__)

PROGRESS_EVERY = 10  # write progress to the DB every N jobs


def months_between(start: date, end: date) -> list[tuple[int, int]]:
    months, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def month_window(year: int, month: int, first: date, last: date) -> tuple[date, date]:
    start = max(date(year, month, 1), first)
    end = min(date(year, month, calendar.monthrange(year, month)[1]), last)
    return start, end


class Crawler:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None

    @property
    def running(self) -> bool:
        return self._lock.locked()

    def start(self, airlines: list[str] | None = None) -> bool:
        """Start a crawl in the background. Returns False if one is already running."""
        if self.running:
            return False
        self._task = asyncio.create_task(self.run(airlines))
        return True

    async def run(self, airlines: list[str] | None = None) -> None:
        async with self._lock:
            with db.connect() as conn:
                destinations = db.list_destinations(conn, enabled_only=True)
            providers = build_providers(airlines)
            await asyncio.gather(*(self._crawl_airline(p, destinations) for p in providers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _crawl_airline(self, provider: Provider, destinations: list[dict]) -> None:
        first = date.today()
        last = first + timedelta(days=config.HORIZON_DAYS)
        routes = [
            route
            for d in destinations
            if provider.serves(d["code"], d["region"])
            for route in (Route(config.ORIGIN, d["code"], d["region"]),
                          Route(d["code"], config.ORIGIN, d["region"]))
        ]
        jobs = [(r, y, m) for r in routes for (y, m) in months_between(first, last)]

        with db.connect() as conn:
            run_id = db.start_run(conn, provider.code, provider_mode(provider.code), len(jobs))

        done = failed = saved = 0
        status, error = "ok", None
        try:
            for i, (route, year, month) in enumerate(jobs, 1):
                start, end = month_window(year, month, first, last)
                try:
                    fares = cheapest_per_day(await provider.fetch_month(route, year, month))
                    fares = [f for f in fares if start <= f.date <= end]
                    with db.connect() as conn:
                        saved += db.save_month(conn, provider.code, route.origin, route.destination,
                                               start, end, fares, db.iso(db.utcnow()))
                    done += 1
                except NotImplementedError as exc:
                    status, error = "failed", str(exc)
                    break
                except Exception as exc:  # one bad page must not stop the crawl
                    failed += 1
                    error = f"{route.origin}->{route.destination} {year}-{month:02d}: {exc}"
                    log.warning("%s %s", provider.code, error)

                if i % PROGRESS_EVERY == 0 or i == len(jobs):
                    with db.connect() as conn:
                        db.update_run(conn, run_id, done, failed, saved, error)
                await provider.pause()

            if status == "ok" and failed:
                status = "failed" if done == 0 else "partial"
        except asyncio.CancelledError:
            status = "interrupted"
            raise
        finally:
            await provider.close()
            with db.connect() as conn:
                db.update_run(conn, run_id, done, failed, saved, error)
                db.finish_run(conn, run_id, status)
            log.info("%s crawl %s: %d/%d jobs, %d fares", provider.code, status, done, len(jobs), saved)
