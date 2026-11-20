"""SQLite storage.

fares_current  one row per (airline, origin, destination, date): the latest cheapest award.
fare_history   append-only, written only when a price changes; used for "normal price".
crawl_runs     one row per airline per crawl, for progress and errors.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Iterator

from . import config
from .providers.base import AwardFare
from .seed import DEFAULT_DESTINATIONS

SCHEMA = """
CREATE TABLE IF NOT EXISTS destinations (
    code     TEXT PRIMARY KEY,
    city     TEXT NOT NULL,
    country  TEXT NOT NULL,
    region   TEXT NOT NULL,
    enabled  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS fares_current (
    airline     TEXT NOT NULL,
    origin      TEXT NOT NULL,
    destination TEXT NOT NULL,
    date        TEXT NOT NULL,
    points      INTEGER NOT NULL,
    taxes_usd   REAL NOT NULL,
    cabin       TEXT NOT NULL,
    fare_brand  TEXT,
    seats       INTEGER,
    stops       INTEGER NOT NULL,
    flights     TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    PRIMARY KEY (airline, origin, destination, date)
);
CREATE INDEX IF NOT EXISTS fares_current_origin_date ON fares_current (origin, date);
CREATE INDEX IF NOT EXISTS fares_current_dest_date ON fares_current (destination, date);

CREATE TABLE IF NOT EXISTS fare_history (
    id          INTEGER PRIMARY KEY,
    airline     TEXT NOT NULL,
    origin      TEXT NOT NULL,
    destination TEXT NOT NULL,
    date        TEXT NOT NULL,
    points      INTEGER NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS fare_history_observed ON fare_history (observed_at);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id           INTEGER PRIMARY KEY,
    airline      TEXT NOT NULL,
    mode         TEXT NOT NULL,
    status       TEXT NOT NULL,          -- running | ok | partial | failed | interrupted
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    jobs_total   INTEGER NOT NULL DEFAULT 0,
    jobs_done    INTEGER NOT NULL DEFAULT 0,
    jobs_failed  INTEGER NOT NULL DEFAULT 0,
    fares_saved  INTEGER NOT NULL DEFAULT 0,
    error        TEXT
);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    try:
        with conn:  # commit on success, roll back on error
            yield conn
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM destinations").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO destinations (code, city, country, region, enabled) VALUES (?, ?, ?, ?, ?)",
            [(c, city, country, region, int(on)) for c, city, country, region, on in DEFAULT_DESTINATIONS],
        )
    # A crawl that was running when the server stopped will never finish.
    conn.execute(
        "UPDATE crawl_runs SET status = 'interrupted', finished_at = ? WHERE status = 'running'",
        (iso(utcnow()),),
    )


# ---------- destinations ----------

def list_destinations(conn: sqlite3.Connection, enabled_only: bool = False) -> list[dict]:
    sql = "SELECT * FROM destinations"
    if enabled_only:
        sql += " WHERE enabled = 1"
    rows = conn.execute(sql + " ORDER BY region, city").fetchall()
    return [{**dict(r), "enabled": bool(r["enabled"])} for r in rows]


def get_destination(conn: sqlite3.Connection, code: str) -> dict | None:
    row = conn.execute("SELECT * FROM destinations WHERE code = ?", (code,)).fetchone()
    return {**dict(row), "enabled": bool(row["enabled"])} if row else None


def add_destination(conn: sqlite3.Connection, code: str, city: str, country: str, region: str, enabled: bool) -> None:
    conn.execute(
        "INSERT INTO destinations (code, city, country, region, enabled) VALUES (?, ?, ?, ?, ?)",
        (code, city, country, region, int(enabled)),
    )


def set_destination_enabled(conn: sqlite3.Connection, code: str, enabled: bool) -> bool:
    cur = conn.execute("UPDATE destinations SET enabled = ? WHERE code = ?", (int(enabled), code))
    return cur.rowcount > 0


def delete_destination(conn: sqlite3.Connection, code: str) -> bool:
    return conn.execute("DELETE FROM destinations WHERE code = ?", (code,)).rowcount > 0


# ---------- fares ----------

def save_month(
    conn: sqlite3.Connection,
    airline: str,
    origin: str,
    destination: str,
    start: date,
    end: date,
    fares: list[AwardFare],
    fetched_at: str,
) -> int:
    """Replace the current fares for one route between start and end (inclusive).

    Dates missing from `fares` had no award space, so their old rows are removed.
    History only gets a row when a date's price is new or has changed.
    """
    key = (airline, origin, destination, start.isoformat(), end.isoformat())
    where = "airline = ? AND origin = ? AND destination = ? AND date BETWEEN ? AND ?"
    previous = {r[0]: r[1] for r in conn.execute(f"SELECT date, points FROM fares_current WHERE {where}", key)}
    conn.execute(f"DELETE FROM fares_current WHERE {where}", key)
    conn.executemany(
        """INSERT INTO fares_current (airline, origin, destination, date, points, taxes_usd, cabin,
                                      fare_brand, seats, stops, flights, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (airline, origin, destination, f.date.isoformat(), f.points, f.taxes_usd, f.cabin,
             f.fare_brand, f.seats, f.stops, json.dumps(list(f.flights)), fetched_at)
            for f in fares
        ],
    )
    conn.executemany(
        "INSERT INTO fare_history (airline, origin, destination, date, points, observed_at) VALUES (?, ?, ?, ?, ?, ?)",
        [
            (airline, origin, destination, f.date.isoformat(), f.points, fetched_at)
            for f in fares
            if previous.get(f.date.isoformat()) != f.points
        ],
    )
    return len(fares)


def fares_between(conn: sqlite3.Connection, column: str, value: str, start: date, end: date, fresh_after: str) -> list[sqlite3.Row]:
    assert column in ("origin", "destination")
    return conn.execute(
        f"SELECT * FROM fares_current WHERE {column} = ? AND date BETWEEN ? AND ? AND fetched_at >= ?",
        (value, start.isoformat(), end.isoformat(), fresh_after),
    ).fetchall()


def latest_fetch(conn: sqlite3.Connection) -> str | None:
    return conn.execute("SELECT MAX(fetched_at) FROM fares_current").fetchone()[0]


def history_version(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COALESCE(MAX(id), 0) FROM fare_history").fetchone()[0]


def history_since(conn: sqlite3.Connection, since: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT airline, origin, destination, points FROM fare_history WHERE observed_at >= ?",
        (since,),
    ).fetchall()


# ---------- crawl runs ----------

def start_run(conn: sqlite3.Connection, airline: str, mode: str, jobs_total: int) -> int:
    cur = conn.execute(
        "INSERT INTO crawl_runs (airline, mode, status, started_at, jobs_total) VALUES (?, ?, 'running', ?, ?)",
        (airline, mode, iso(utcnow()), jobs_total),
    )
    return cur.lastrowid


def update_run(conn: sqlite3.Connection, run_id: int, done: int, failed: int, saved: int, error: str | None) -> None:
    conn.execute(
        "UPDATE crawl_runs SET jobs_done = ?, jobs_failed = ?, fares_saved = ?, error = ? WHERE id = ?",
        (done, failed, saved, error, run_id),
    )


def finish_run(conn: sqlite3.Connection, run_id: int, status: str) -> None:
    conn.execute(
        "UPDATE crawl_runs SET status = ?, finished_at = ? WHERE id = ?",
        (status, iso(utcnow()), run_id),
    )


def latest_runs(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM crawl_runs WHERE id IN (SELECT MAX(id) FROM crawl_runs GROUP BY airline)"
    ).fetchall()
    return [dict(r) for r in rows]


def last_finished_at(conn: sqlite3.Connection) -> datetime | None:
    value = conn.execute("SELECT MAX(finished_at) FROM crawl_runs WHERE status != 'running'").fetchone()[0]
    return datetime.fromisoformat(value) if value else None
