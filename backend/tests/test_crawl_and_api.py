import asyncio
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app import db
from app.crawler import Crawler, months_between
from app.main import app
from app.providers import MockProvider, Route


def test_months_between_spans_year_end():
    assert months_between(date(2026, 11, 20), date(2027, 2, 1)) == [(2026, 11), (2026, 12), (2027, 1), (2027, 2)]


def test_mock_is_deterministic_and_respects_regions():
    p = MockProvider("WN", today=date(2026, 1, 1))
    route = Route("AUS", "DEN", "domestic")
    a = asyncio.run(p.fetch_month(route, 2026, 3))
    b = asyncio.run(p.fetch_month(route, 2026, 3))
    assert a == b and a
    assert not p.serves("LHR", "europe")


def test_crawl_then_deals_and_api(conn):
    for d in db.list_destinations(conn):
        db.set_destination_enabled(conn, d["code"], d["code"] in ("LHR", "CUN"))
    conn.commit()

    asyncio.run(Crawler().run(["UA", "WN"]))

    with TestClient(app) as client:
        runs = {r["airline"]: r for r in client.get("/api/crawl").json()["runs"]}
        assert runs["UA"]["status"] == "ok" and runs["UA"]["fares_saved"] > 0
        assert runs["WN"]["status"] == "ok"

        start = date.today() + timedelta(days=7)
        res = client.get("/api/deals", params={
            "depart_from": start.isoformat(),
            "return_by": (start + timedelta(days=300)).isoformat(),
            "min_nights": 3, "max_nights": 10, "max_ratio": 0.9,
        })
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["results"], "mock sales should produce at least one deal"
        assert all(r["ratio"] <= 0.9 for r in body["results"])
        assert {r["destination"]["code"] for r in body["results"]} <= {"LHR", "CUN"}

        bad = client.get("/api/deals", params={"depart_from": start.isoformat(),
                                               "return_by": start.isoformat()})
        assert bad.status_code == 422

        assert client.post("/api/destinations", json={"code": "aus", "city": "x", "country": "y",
                                                      "region": "domestic"}).status_code == 400
        created = client.post("/api/destinations", json={"code": "ktm", "city": "Kathmandu",
                                                         "country": "Nepal", "region": "asia"})
        assert created.status_code == 201 and created.json()["code"] == "KTM"
        assert client.delete("/api/destinations/KTM").status_code == 204


def test_unwritten_live_scraper_fails_cleanly(conn, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "LIVE_AIRLINES", {"BA"})
    for d in db.list_destinations(conn):
        db.set_destination_enabled(conn, d["code"], d["code"] == "LHR")
    conn.commit()

    asyncio.run(Crawler().run(["BA"]))

    run = db.latest_runs(conn)[0]
    assert run["status"] == "failed" and "not written yet" in run["error"]
