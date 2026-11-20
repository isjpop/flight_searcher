"""Finding round trips that cost well below their normal price in points.

Normal price: for each (airline, origin, destination), the median of every price
observed over the last BASELINE_LOOKBACK_DAYS, across all travel dates. Medians
ignore the occasional sale, so a sale stands out against it.

Round trip: an AUS->X leg plus an X->AUS leg whose gap fits the requested nights.
Same program: ratio = total points / total normal points.
Mixed programs (optional): the currencies differ, so ratio = mean of the two leg ratios.
"""
from __future__ import annotations

import json
import sqlite3
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from . import config, db
from .airlines import AIRLINES
from .models import DealQuery, DealsResponse, Destination, Leg, RoundTrip

BaselineKey = tuple[str, str, str]  # (airline, origin, destination)

_baseline_cache: tuple[int, dict[BaselineKey, int]] | None = None


def get_baselines(conn: sqlite3.Connection) -> dict[BaselineKey, int]:
    """Median observed points per route. Cached until new history is written."""
    global _baseline_cache
    version = db.history_version(conn)
    if _baseline_cache and _baseline_cache[0] == version:
        return _baseline_cache[1]

    since = db.iso(db.utcnow() - timedelta(days=config.BASELINE_LOOKBACK_DAYS))
    samples: dict[BaselineKey, list[int]] = defaultdict(list)
    for r in db.history_since(conn, since):
        samples[(r["airline"], r["origin"], r["destination"])].append(r["points"])
    baselines = {
        key: int(statistics.median(points))
        for key, points in samples.items()
        if len(points) >= config.MIN_BASELINE_SAMPLES
    }
    _baseline_cache = (version, baselines)
    return baselines


@dataclass
class _Leg:
    row: sqlite3.Row
    day: date
    normal: int
    ratio: float

    @property
    def airline(self) -> str:
        return self.row["airline"]

    @property
    def points(self) -> int:
        return self.row["points"]

    def to_model(self) -> Leg:
        r = self.row
        return Leg(
            airline=r["airline"], origin=r["origin"], destination=r["destination"], date=self.day,
            points=r["points"], normal_points=self.normal, ratio=round(self.ratio, 3),
            taxes_usd=r["taxes_usd"], cabin=r["cabin"], fare_brand=r["fare_brand"], seats=r["seats"],
            stops=r["stops"], flights=json.loads(r["flights"]), fetched_at=r["fetched_at"],
        )


def _program(code: str) -> str:
    return AIRLINES[code].program if code in AIRLINES else code


def find_round_trips(conn: sqlite3.Connection, q: DealQuery) -> DealsResponse:
    baselines = get_baselines(conn)
    notes: list[str] = []
    if not baselines:
        notes.append("Not enough price history yet to know what's normal. Run a crawl first.")

    all_dests = {d["code"]: d for d in db.list_destinations(conn)}
    if q.destinations:
        wanted = {c.upper() for c in q.destinations}
    else:
        wanted = {c for c, d in all_dests.items() if d["enabled"]}
    if q.regions:
        wanted = {c for c in wanted if c in all_dests and all_dests[c]["region"] in q.regions}
    airlines = {a.upper() for a in q.airlines} if q.airlines else None

    fresh_after = db.iso(db.utcnow() - timedelta(hours=config.FRESH_HOURS))

    def legs(rows: list[sqlite3.Row], far_end: str) -> list[_Leg]:
        out = []
        for r in rows:
            if r[far_end] not in wanted or (airlines and r["airline"] not in airlines):
                continue
            normal = baselines.get((r["airline"], r["origin"], r["destination"]))
            if not normal:
                continue
            ratio = r["points"] / normal
            if ratio <= config.LEG_PREFILTER_RATIO:
                out.append(_Leg(r, date.fromisoformat(r["date"]), normal, ratio))
        return out

    outbound = legs(db.fares_between(conn, "origin", config.ORIGIN, q.depart_from,
                                     q.return_by - timedelta(days=q.min_nights), fresh_after), "destination")
    inbound = legs(db.fares_between(conn, "destination", config.ORIGIN,
                                    q.depart_from + timedelta(days=q.min_nights), q.return_by, fresh_after), "origin")

    returns: dict[tuple[str, date], list[_Leg]] = defaultdict(list)
    for leg in inbound:
        returns[(leg.row["origin"], leg.day)].append(leg)

    matches: list[tuple[float, int, _Leg, _Leg, int]] = []
    for o in outbound:
        dest = o.row["destination"]
        for nights in range(q.min_nights, q.max_nights + 1):
            back = o.day + timedelta(days=nights)
            if back > q.return_by:
                break
            for r in returns.get((dest, back), ()):
                same = r.airline == o.airline
                if not same and not q.mix_programs:
                    continue
                ratio = (o.points + r.points) / (o.normal + r.normal) if same else (o.ratio + r.ratio) / 2
                if ratio > q.max_ratio:
                    continue
                taxes = o.row["taxes_usd"] + r.row["taxes_usd"]
                if q.max_taxes_usd is not None and taxes > q.max_taxes_usd:
                    continue
                matches.append((ratio, o.points + r.points, o, r, nights))

    matches.sort(key=lambda m: (m[0], m[1]))
    per_dest: dict[str, int] = defaultdict(int)
    results: list[RoundTrip] = []
    for ratio, _, o, r, nights in matches:
        dest = o.row["destination"]
        if per_dest[dest] >= q.per_destination:
            continue
        per_dest[dest] += 1
        points: dict[str, int] = defaultdict(int)
        normal: dict[str, int] = defaultdict(int)
        for leg in (o, r):
            points[_program(leg.airline)] += leg.points
            normal[_program(leg.airline)] += leg.normal
        results.append(RoundTrip(
            destination=Destination(**all_dests[dest]),
            outbound=o.to_model(),
            inbound=r.to_model(),
            nights=nights,
            ratio=round(ratio, 3),
            savings_pct=round((1 - ratio) * 100, 1),
            points_by_program=dict(points),
            normal_points_by_program=dict(normal),
            taxes_usd=round(o.row["taxes_usd"] + r.row["taxes_usd"], 2),
            mixed_programs=o.airline != r.airline,
        ))
        if len(results) >= q.limit:
            break

    return DealsResponse(results=results, total_matches=len(matches),
                         data_as_of=db.latest_fetch(conn), notes=notes)
