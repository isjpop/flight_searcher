"""Runs a full crawl whenever the last one finished more than CRAWL_INTERVAL_HOURS ago."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from . import config, db
from .crawler import Crawler

log = logging.getLogger(__name__)

CHECK_EVERY_S = 300


def next_due(last: datetime | None) -> datetime | None:
    return last + timedelta(hours=config.CRAWL_INTERVAL_HOURS) if last else None


async def scheduler_loop(crawler: Crawler) -> None:
    while True:
        try:
            with db.connect() as conn:
                due = next_due(db.last_finished_at(conn))
            if not crawler.running and (due is None or db.utcnow() >= due):
                log.info("scheduled crawl starting")
                await crawler.run()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("scheduled crawl failed")
        await asyncio.sleep(CHECK_EVERY_S)
