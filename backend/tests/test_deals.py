from datetime import date, timedelta

from app import db
from app.deals import find_round_trips
from app.models import DealQuery
from app.providers.base import AwardFare

TODAY = date.today()
D0 = TODAY + timedelta(days=30)


def put(conn, airline, origin, dest, prices: dict[date, int]):
    """Write fares for a route; also gives the route its price history."""
    for day, points in prices.items():
        db.save_month(conn, airline, origin, dest, day, day,
                      [AwardFare(date=day, points=points, taxes_usd=5.6)], db.iso(db.utcnow()))


def normal_route(conn, airline, dest, normal=20_000):
    """Ten days at the normal price in both directions, starting 60 days out."""
    days = {TODAY + timedelta(days=60 + i): normal for i in range(10)}
    put(conn, airline, "AUS", dest, days)
    put(conn, airline, dest, "AUS", days)


def query(**kw):
    base = dict(depart_from=D0, return_by=D0 + timedelta(days=20), min_nights=3, max_nights=7, max_ratio=0.7)
    return DealQuery(**{**base, **kw})


def test_finds_cheap_round_trip_within_nights_window(conn):
    normal_route(conn, "UA", "LHR")
    put(conn, "UA", "AUS", "LHR", {D0: 10_000})
    put(conn, "UA", "LHR", "AUS", {D0 + timedelta(days=5): 10_000, D0 + timedelta(days=12): 8_000})

    res = find_round_trips(conn, query())

    assert len(res.results) == 1
    trip = res.results[0]
    assert trip.destination.code == "LHR"
    assert trip.nights == 5  # the 12-night return is outside max_nights
    assert trip.ratio == 0.5
    assert trip.savings_pct == 50.0
    assert trip.points_by_program == {"MileagePlus": 20_000}


def test_normal_priced_trips_are_excluded(conn):
    normal_route(conn, "UA", "LHR")
    put(conn, "UA", "AUS", "LHR", {D0: 19_000})
    put(conn, "UA", "LHR", "AUS", {D0 + timedelta(days=4): 19_000})
    assert find_round_trips(conn, query()).results == []


def test_mixed_programs_only_when_requested(conn):
    normal_route(conn, "UA", "CDG")
    normal_route(conn, "AC", "CDG")
    put(conn, "UA", "AUS", "CDG", {D0: 8_000})
    put(conn, "AC", "CDG", "AUS", {D0 + timedelta(days=4): 8_000})

    assert find_round_trips(conn, query()).results == []
    mixed = find_round_trips(conn, query(mix_programs=True)).results
    assert len(mixed) == 1 and mixed[0].mixed_programs
    assert mixed[0].points_by_program == {"MileagePlus": 8_000, "Aeroplan": 8_000}


def test_disabled_destinations_and_airline_filter(conn):
    normal_route(conn, "UA", "LHR")
    put(conn, "UA", "AUS", "LHR", {D0: 9_000})
    put(conn, "UA", "LHR", "AUS", {D0 + timedelta(days=4): 9_000})

    assert find_round_trips(conn, query(airlines=["WN"])).results == []
    db.set_destination_enabled(conn, "LHR", False)
    assert find_round_trips(conn, query()).results == []
    assert len(find_round_trips(conn, query(destinations=["LHR"])).results) == 1


def test_no_history_gives_a_note(conn):
    res = find_round_trips(conn, query())
    assert res.results == [] and res.notes


def test_save_month_drops_sold_out_days_and_dedupes_history(conn):
    d1, d2 = D0, D0 + timedelta(days=1)
    stamp = db.iso(db.utcnow())
    db.save_month(conn, "UA", "AUS", "LHR", d1, d2,
                  [AwardFare(d1, 10_000, 5.6), AwardFare(d2, 12_000, 5.6)], stamp)
    db.save_month(conn, "UA", "AUS", "LHR", d1, d2, [AwardFare(d1, 10_000, 5.6)], stamp)

    current = conn.execute("SELECT date FROM fares_current").fetchall()
    assert [r[0] for r in current] == [d1.isoformat()]
    assert conn.execute("SELECT COUNT(*) FROM fare_history").fetchone()[0] == 2
