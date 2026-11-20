"""FastAPI app. Run with: uvicorn app.main:app --host 127.0.0.1 --port 8000"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import config, db
from .airlines import AIRLINES
from .crawler import Crawler
from .deals import find_round_trips
from .models import (AirlineInfo, CrawlRequest, CrawlRun, CrawlStatus, DealQuery, DealsResponse,
                     Destination, DestinationCreate, DestinationUpdate)
from .providers import provider_mode
from .scheduler import next_due, scheduler_loop

crawler = Crawler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with db.connect() as conn:
        db.init_db(conn)
    scheduler = asyncio.create_task(scheduler_loop(crawler)) if config.SCHEDULER_ENABLED else None
    yield
    if scheduler:
        scheduler.cancel()
    await crawler.stop()


app = FastAPI(title="AUS Award Finder", lifespan=lifespan)


def _csv(value: str | None) -> list[str] | None:
    items = [v.strip() for v in value.split(",") if v.strip()] if value else []
    return items or None


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/airlines", response_model=list[AirlineInfo])
def airlines() -> list[AirlineInfo]:
    return [AirlineInfo(**a.__dict__, mode=provider_mode(a.code)) for a in AIRLINES.values()]


# ---------- destinations ----------

@app.get("/api/destinations", response_model=list[Destination])
def list_destinations() -> list[dict]:
    with db.connect() as conn:
        return db.list_destinations(conn)


@app.post("/api/destinations", response_model=Destination, status_code=201)
def add_destination(body: DestinationCreate) -> dict:
    code = body.code.upper()
    if code == config.ORIGIN:
        raise HTTPException(400, f"{config.ORIGIN} is the origin")
    with db.connect() as conn:
        try:
            db.add_destination(conn, code, body.city, body.country, body.region, body.enabled)
        except sqlite3.IntegrityError:
            raise HTTPException(409, f"{code} is already in the list")
        return db.get_destination(conn, code)


@app.patch("/api/destinations/{code}", response_model=Destination)
def update_destination(code: str, body: DestinationUpdate) -> dict:
    with db.connect() as conn:
        if not db.set_destination_enabled(conn, code.upper(), body.enabled):
            raise HTTPException(404, "unknown destination")
        return db.get_destination(conn, code.upper())


@app.delete("/api/destinations/{code}", status_code=204)
def delete_destination(code: str) -> Response:
    with db.connect() as conn:
        if not db.delete_destination(conn, code.upper()):
            raise HTTPException(404, "unknown destination")
    return Response(status_code=204)


# ---------- crawling ----------

@app.get("/api/crawl", response_model=CrawlStatus)
def crawl_status() -> CrawlStatus:
    with db.connect() as conn:
        runs = db.latest_runs(conn)
        last = db.last_finished_at(conn)
    due = next_due(last)
    return CrawlStatus(
        running=crawler.running,
        interval_hours=config.CRAWL_INTERVAL_HOURS,
        last_finished_at=db.iso(last) if last else None,
        next_due_at=db.iso(due) if due and config.SCHEDULER_ENABLED else None,
        runs=[CrawlRun(**{k: r[k] for k in CrawlRun.model_fields}) for r in runs],
    )


@app.post("/api/crawl", status_code=202)
def start_crawl(body: CrawlRequest | None = None) -> dict:
    codes = [c.upper() for c in body.airlines] if body and body.airlines else None
    if codes and (unknown := set(codes) - set(AIRLINES)):
        raise HTTPException(400, f"unknown airlines: {', '.join(sorted(unknown))}")
    if not crawler.start(codes):
        raise HTTPException(409, "a crawl is already running")
    return {"started": True}


# ---------- deals ----------

@app.get("/api/deals", response_model=DealsResponse)
def deals(
    depart_from: date,
    return_by: date,
    min_nights: int = 3,
    max_nights: int = 10,
    max_ratio: float = 0.7,
    airlines: str | None = Query(None, description="comma-separated airline codes"),
    destinations: str | None = Query(None, description="comma-separated airport codes"),
    regions: str | None = Query(None, description="comma-separated regions"),
    mix_programs: bool = False,
    max_taxes_usd: float | None = None,
    per_destination: int = 3,
    limit: int = 100,
) -> DealsResponse:
    try:
        q = DealQuery(
            depart_from=depart_from, return_by=return_by, min_nights=min_nights, max_nights=max_nights,
            max_ratio=max_ratio, airlines=_csv(airlines), destinations=_csv(destinations),
            regions=_csv(regions), mix_programs=mix_programs, max_taxes_usd=max_taxes_usd,
            per_destination=per_destination, limit=limit,
        )
    except ValidationError as exc:
        raise HTTPException(422, [e["msg"] for e in exc.errors()])
    with db.connect() as conn:
        return find_round_trips(conn, q)


# Serve the built frontend (npm run build) from the same localhost server.
if config.FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="frontend")
