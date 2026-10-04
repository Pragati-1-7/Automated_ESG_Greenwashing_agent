"""mock_sources service contract and the planted demo-company facts."""

from fastapi.testclient import TestClient

from mock_sources.app import app

c = TestClient(app)


def test_health_and_tables():
    h = c.get("/health").json()
    assert h["status"] == "ok" and h["tables"]["companies"] == 150
    t = {x["name"]: x for x in c.get("/tables").json()["tables"]}
    assert t["brsr_filings"]["tier"] == 1 and t["news_articles"]["rows"] >= 400


def test_resolve_distinctive_names_only():
    top = c.get("/companies/resolve", params={"name": "Vajra Steel & Power Limited"}).json()["candidates"][0]
    assert top["company_id"] == "CMP-0001" and top["match_score"] >= 0.9
    aur = c.get("/companies/resolve", params={"name": "Aurelia Renewables Pvt Ltd"}).json()["candidates"][0]
    assert aur["match_score"] < 0.5   # shares only generic words with registry names


def test_brsr_envelope():
    r = c.get("/sebi/brsr", params={"company_id": "CMP-0001", "fy": "FY2025"}).json()
    assert r["source"] == "brsr_filings" and r["tier"] == 1 and r["endpoint"].startswith("/sebi/brsr")
    assert r["rows"][0]["scope1_tco2e"] == 10_856_000


def test_planted_events():
    assert c.get("/gfw/alerts/company", params={"company_id": "CMP-0001", "fy": "FY2025"}).json()["total_area_ha"] == 126.4
    assert c.get("/registry/rec", params={"company_id": "CMP-0001", "vintage": 2024}).json()["totals_mwh"] == \
        {"active": 2_100_000, "retired": 310_000}
    assert c.get("/cpcb/ocems/exceedances", params={"company_id": "CMP-0002", "fy": "FY2025"}).json()["count"] == 6
    assert c.get("/regulatory/actions", params={"company_id": "CMP-0002", "fy": "FY2025"}).json()["count"] == 0
    assert c.get("/regulatory/actions", params={"company_id": "CMP-0002"}).json()["count"] == 1
    assert c.get("/gfw/alerts/near", params={"lat": 23.7337, "lon": 69.8597, "radius_km": 10}).json()["count"] == 0


def test_news_search_is_ranked_and_filtered():
    rows = c.get("/news/search", params={"q": "Vajra renewable certificates unretired", "company_id": "CMP-0001"}).json()["rows"]
    assert rows and all(r["company_id"] == "CMP-0001" for r in rows)
    assert rows[0]["score"] == 1.0


def test_errors():
    assert c.get("/sebi/brsr", params={"company_id": "CMP-9999"}).status_code == 404
    assert c.get("/regulatory/actions", params={"company_id": "CMP-0001", "fy": "FY1999"}).status_code == 400
    assert c.get("/tables/not_a_table").status_code == 404
