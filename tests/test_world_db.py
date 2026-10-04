"""Tests for the synthetic world database generator (data_gen/build_world.py)."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3

import pytest

from data_gen import build_world, news_tpl, spec, validate_world
from data_gen.world_utils import fy_range, haversine_km, inr, wc

FY25 = tuple(x.isoformat() for x in fy_range("FY2025"))


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    d = tmp_path_factory.mktemp("world")
    path = d / "world.db"
    counts = build_world.build(path, verbose=False)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    yield dict(path=path, con=con, counts=counts, dir=d)
    con.close()


def q(world, sql, *args):
    return world["con"].execute(sql, args).fetchall()


def one(world, sql, *args):
    return q(world, sql, *args)[0][0]


# ---------------------------------------------------------------- global invariants

def test_validator_passes(world):
    assert validate_world.validate(world["path"]) == []


def test_row_counts_within_25_percent(world):
    for table, target in build_world.TARGETS.items():
        n = world["counts"][table]
        assert 0.75 * target <= n <= 1.25 * target, (table, n, target)
    assert world["counts"]["companies"] == 150
    assert world["counts"]["brsr_filings"] == 900


def test_foreign_keys(world):
    assert q(world, "PRAGMA foreign_key_check") == []


def test_brsr_six_rows_per_company_and_intensity(world):
    assert all(n == 6 for _, n in q(world, "SELECT company_id, COUNT(*) FROM brsr_filings GROUP BY company_id"))
    for fid, rev, s1, s2, gi in q(world, "SELECT filing_id, revenue_cr, scope1_tco2e, scope2_tco2e, ghg_intensity FROM brsr_filings"):
        assert gi == round((s1 + s2) / rev, 1), fid


def test_brsr_ranges_and_filing_dates(world):
    for fid, fy, re_, ltifr, filed in q(world, "SELECT filing_id, fy, re_pct, ltifr, filed_on FROM brsr_filings"):
        assert 0 <= re_ <= 100 and 0.05 <= ltifr <= 1.2, fid
        assert filed[:4] == fy[2:] and filed[5:7] in ("07", "08", "09"), (fid, filed)


def test_sector_scales(world):
    rows = dict(q(world, "SELECT c.sector, AVG(b.scope1_tco2e) FROM brsr_filings b JOIN companies c USING(company_id) WHERE fy='FY2025' GROUP BY c.sector"))
    assert rows["Steel"] > 1e6 and rows["Cement"] > 1e6 and rows["Power"] > 1e6
    assert rows["IT Services"] < 1e5 and rows["FMCG"] < 2e5
    w = dict(q(world, "SELECT c.sector, AVG(b.women_wage_pct) FROM brsr_filings b JOIN companies c USING(company_id) WHERE fy='FY2025' GROUP BY c.sector"))
    assert 25 <= w["IT Services"] <= 40 and 25 <= w["Textiles"] <= 45
    assert w["Mining"] < 7 and w["Steel"] < 7


def test_facility_ghg_matches_scope1(world):
    assert one(world, "SELECT COUNT(*) FROM facility_ghg") == one(world, "SELECT COUNT(*) FROM facilities") * 6
    rows = q(world, """SELECT b.company_id, b.fy, b.scope1_tco2e, SUM(g.total_tco2e) FROM brsr_filings b
                       JOIN facilities f ON f.company_id=b.company_id JOIN facility_ghg g ON g.facility_id=f.facility_id AND g.fy=b.fy
                       GROUP BY b.company_id, b.fy""")
    assert len(rows) == 900
    for cid, fy, s1, tot in rows:
        assert abs(tot - s1) <= 0.005 * s1, (cid, fy)


def test_ocems_reading_above_limit(world):
    assert q(world, "SELECT 1 FROM ocems_exceedances WHERE reading <= limit_value") == []
    params = {p: (lo, hi) for p, lo, hi in q(world, "SELECT parameter, MIN(limit_value), MAX(limit_value) FROM ocems_exceedances GROUP BY parameter")}
    assert 30 <= params["PM"][0] and params["PM"][1] <= 50
    assert params["BOD"] == (30.0, 30.0) and params["COD"] == (250.0, 250.0) and params["TSS"] == (100.0, 100.0)


def test_audited_reports_match_brsr(world):
    assert q(world, """SELECT 1 FROM audited_reports a JOIN brsr_filings b ON a.company_id=b.company_id AND a.fy=b.fy
                       WHERE a.assurance_type != b.assurance_type OR a.auditor != b.assurance_provider""") == []
    n_assured = one(world, "SELECT COUNT(*) FROM brsr_filings WHERE assurance_type != 'none'")
    assert one(world, "SELECT COUNT(*) FROM audited_reports") == n_assured
    for (text,) in q(world, "SELECT text FROM audited_reports"):
        assert 120 <= wc(text) <= 300


def test_news_articles(world):
    rows = q(world, "SELECT article_id, company_id, outlet, outlet_tier, headline, body, topics FROM news_articles")
    names = {cid: (n, s) for cid, n, s in q(world, "SELECT company_id, name, short_name FROM companies")}
    tied = 0
    for aid, cid, outlet, tier, head, body, topics in rows:
        assert 250 <= wc(body) <= 600, aid
        assert tier in (4, 5) and (tier == 4) == outlet.endswith("(press release)")
        assert set(json.loads(topics)) <= validate_world.TOPICS
        if cid:
            tied += 1
            assert names[cid][0] in head + body or names[cid][1] in head + body, aid
    assert 0.5 <= tied / len(rows) <= 0.7
    assert len({r[2] for r in rows if r[3] == 5}) >= 15
    assert len(news_tpl.TEMPLATE_NAMES) >= 25


def test_penalty_articles_reference_real_rows(world):
    # every headline that quotes a rupee amount for a company must match that company's regulatory action amount
    n = 0
    for cid, head in q(world, "SELECT company_id, headline FROM news_articles WHERE company_id IS NOT NULL AND headline GLOB '*Rs [0-9]*' AND topics LIKE '%regulatory%'"):
        m = re.search(r"Rs [\d.]+ (crore|lakh)", head)
        amounts = {inr(a) for (a,) in q(world, "SELECT penalty_inr FROM regulatory_actions WHERE company_id=? AND penalty_inr>0", cid)}
        assert m.group(0) in amounts, head
        n += 1
    assert n >= 10


def test_no_aurelia_anywhere(world):
    for (t,) in q(world, "SELECT name FROM sqlite_master WHERE type='table'"):
        for col in [r[1] for r in q(world, f"PRAGMA table_info({t})") if r[2].upper() == "TEXT"]:
            assert one(world, f"SELECT COUNT(*) FROM {t} WHERE lower({col}) LIKE '%aurelia%'") == 0, (t, col)


def test_cin_and_listing_format(world):
    for cin, listing in q(world, "SELECT cin, listing FROM companies"):
        assert re.match(r"^[LU]\d{5}[A-Z]{2}\d{4}(PLC|PTC)\d{6}$", cin), cin
        assert listing == "Unlisted" or re.match(r"^(NSE|BSE|NSE, BSE): \S+$", listing), listing


def test_forest_adjacent_share(world):
    n = one(world, "SELECT COUNT(*) FROM facilities f JOIN companies c USING(company_id) WHERE c.sector IN ('Mining','Steel','Power') AND f.forest_adjacent=1")
    tot = one(world, "SELECT COUNT(*) FROM facilities f JOIN companies c USING(company_id) WHERE c.sector IN ('Mining','Steel','Power')")
    assert 0.06 <= n / tot <= 0.2


def test_alert_nearest_facility_and_kutch(world):
    fac = [(f, a, b) for f, a, b in q(world, "SELECT facility_id, lat, lon FROM facilities")]
    for aid, lat, lon, nf, dist in q(world, "SELECT alert_id, lat, lon, nearest_facility_id, distance_km FROM land_alerts"):
        assert haversine_km(lat, lon, 23.7337, 69.8597) >= 15, aid
        d, f = min((haversine_km(lat, lon, a, b), fid) for fid, a, b in fac)
        if d <= 25:
            assert nf == f and abs(dist - d) < 0.02, aid
        else:
            assert nf is None and dist is None, aid
    assert one(world, "SELECT COUNT(*) FROM land_alerts WHERE nearest_facility_id IS NULL") > 300  # background noise exists


# ---------------------------------------------------------------- demo companies

def test_demo_company_and_facility_rows_match_spec(world):
    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        row = q(world, "SELECT cin, name, short_name, aliases, sector, hq_city, hq_state, listing, market_cap_band FROM companies WHERE company_id=?", d["company_id"])[0]
        band = {"CMP-0001": "Large", "CMP-0002": "Mid", "CMP-0003": "Small"}[d["company_id"]]
        assert row == (d["cin"], d["name"], d["short_name"], json.dumps(d["aliases"]), d["sector"], d["hq_city"], d["hq_state"], d["listing"], band)
        assert isinstance(json.loads(row[3]), list)
        for f in d["facilities"]:
            fr = q(world, "SELECT company_id, name, type, district, state, lat, lon, capacity_value, capacity_unit, forest_adjacent FROM facilities WHERE facility_id=?", f["facility_id"])[0]
            assert fr == (d["company_id"], f["name"], f["type"], f["district"], f["state"], f["lat"], f["lon"], f["capacity_value"], f["capacity_unit"], int(f["forest_adjacent"]))
        assert one(world, "SELECT COUNT(*) FROM facilities WHERE company_id=?", d["company_id"]) == len(d["facilities"])


def test_demo_brsr_matches_spec_true_values(world):
    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        t = d["true"]
        for i, fy in enumerate(spec.FISCAL_YEARS):
            r = q(world, "SELECT * FROM brsr_filings WHERE company_id=? AND fy=?", d["company_id"], fy)
            cols = [c[1] for c in q(world, "PRAGMA table_info(brsr_filings)")]
            r = dict(zip(cols, r[0]))
            for k in ("revenue_cr", "scope1_tco2e", "scope2_tco2e", "energy_gj", "re_pct", "water_withdrawal_kl", "water_discharge_kl", "waste_generated_t",
                      "waste_recovered_t", "ltifr", "fatalities", "women_wage_pct", "msme_sourcing_pct", "assurance_type", "assurance_provider"):
                assert r[k] == t[k][i], (d["company_id"], fy, k)
            assert r["ghg_intensity"] == round((t["scope1_tco2e"][i] + t["scope2_tco2e"][i]) / t["revenue_cr"][i], 1)


def test_vajra_facility_split_and_regulatory(world):
    w = dict(q(world, "SELECT facility_id, total_tco2e FROM facility_ghg WHERE fy='FY2025' AND facility_id IN ('FAC-0001','FAC-0002','FAC-0003','FAC-0004')"))
    tot = sum(w.values())
    assert abs(w["FAC-0001"] / tot - 0.70) < 0.02 and abs(w["FAC-0002"] / tot - 0.25) < 0.02
    assert abs(w["FAC-0004"] / tot - 0.04) < 0.01 and abs(w["FAC-0003"] / tot - 0.01) < 0.005
    got = q(world, "SELECT facility_id, authority, order_type, date, penalty_inr, status, case_no, summary FROM regulatory_actions WHERE company_id='CMP-0001' ORDER BY date")
    want = [(e["facility_id"], e["authority"], e["order_type"], e["date"], float(e["penalty_inr"]), e["status"], e["case_no"], e["summary"])
            for e in spec.demo_by_id("CMP-0001")["events"]["regulatory_actions"]]
    assert got == sorted(want, key=lambda x: x[3])


def test_vajra_ocems(world):
    rows = q(world, "SELECT facility_id, parameter, date FROM ocems_exceedances WHERE facility_id IN ('FAC-0001','FAC-0002','FAC-0003','FAC-0004') AND date BETWEEN ? AND ?", *FY25)
    assert len(rows) == 37 and {r[0] for r in rows} == {"FAC-0002"} and {r[1] for r in rows} == {"PM", "SO2"}


def test_vajra_land_alerts(world):
    f = q(world, "SELECT lat, lon FROM facilities WHERE facility_id='FAC-0003'")[0]
    near = [r for r in q(world, "SELECT lat, lon, alert_date, area_ha FROM land_alerts") if haversine_km(f[0], f[1], r[0], r[1]) <= 5]
    assert len(near) == 14
    assert all("2024-04-10" <= r[2] <= "2025-03-05" for r in near)
    assert round(sum(r[3] for r in near), 6) == 126.4


def test_vajra_recs(world):
    assert one(world, "SELECT SUM(mwh) FROM re_certificates WHERE company_id='CMP-0001' AND vintage_year=2024 AND status='retired'") == 310_000
    assert one(world, "SELECT SUM(mwh) FROM re_certificates WHERE company_id='CMP-0001' AND vintage_year=2024 AND status='active'") == 2_100_000
    assert one(world, "SELECT COUNT(*) FROM re_certificates WHERE company_id='CMP-0001' AND vintage_year=2024") >= 4


def test_sahyadri_truths(world):
    ids = ["FAC-0005", "FAC-0006", "FAC-0007", "FAC-0008"]
    ph = ",".join("?" * 4)
    rows = q(world, f"SELECT facility_id, parameter FROM ocems_exceedances WHERE facility_id IN ({ph}) AND date BETWEEN ? AND ?", *ids, *FY25)
    assert len(rows) == 6 and {r[0] for r in rows} == {"FAC-0005"} and {r[1] for r in rows} == {"PM"}
    regs = q(world, "SELECT authority, order_type, date FROM regulatory_actions WHERE company_id='CMP-0002'")
    assert regs == [("CPCB", "closure_direction", "2023-02-09")]
    assert one(world, "SELECT SUM(mwh) FROM re_certificates WHERE company_id='CMP-0002' AND vintage_year=2024 AND status='retired'") == 240_000
    assert one(world, "SELECT COUNT(*) FROM re_certificates WHERE company_id='CMP-0002' AND vintage_year=2024 AND status!='retired'") == 0
    for fid, lat, lon in q(world, "SELECT facility_id, lat, lon FROM facilities WHERE company_id='CMP-0002'"):
        for alat, alon, adate in q(world, "SELECT lat, lon, alert_date FROM land_alerts WHERE alert_date BETWEEN ? AND ?", *FY25):
            assert haversine_km(lat, lon, alat, alon) > 10, fid


def test_kaveri_truths(world):
    ids = [r[0] for r in q(world, "SELECT facility_id FROM facilities WHERE company_id='CMP-0003'")]
    ph = ",".join("?" * len(ids))
    assert one(world, f"SELECT COUNT(*) FROM ocems_exceedances WHERE facility_id IN ({ph})", *ids) == 0
    assert one(world, "SELECT COUNT(*) FROM regulatory_actions WHERE company_id='CMP-0003'") == 0
    assert one(world, "SELECT SUM(mwh) FROM re_certificates WHERE company_id='CMP-0003' AND vintage_year=2024 AND status='retired'") == 95_000
    assert one(world, "SELECT COUNT(*) FROM re_certificates WHERE company_id='CMP-0003' AND vintage_year=2024 AND status!='retired'") == 0
    for fid, lat, lon in q(world, "SELECT facility_id, lat, lon FROM facilities WHERE company_id='CMP-0003'"):
        for alat, alon in q(world, "SELECT lat, lon FROM land_alerts WHERE alert_date BETWEEN ? AND ?", *FY25):
            assert haversine_km(lat, lon, alat, alon) > 10, fid


def test_demo_news_from_spec_present_with_extras(world):
    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        for n in d["news"]:
            r = q(world, "SELECT outlet_tier, body FROM news_articles WHERE company_id=? AND outlet=? AND published_on=? AND headline=?", d["company_id"], n["outlet"], n["date"], n["headline"])
            assert len(r) == 1 and r[0][0] == n["tier"], n["headline"]
            assert 250 <= wc(r[0][1]) <= 500
        extra = one(world, "SELECT COUNT(*) FROM news_articles WHERE company_id=?", d["company_id"]) - len(d["news"])
        assert 2 <= extra <= 5


def test_demo_news_never_contradicts_truth(world):
    bad = re.compile(r"(zero|no|without any) (environmental )?(penalt|violation|fine)", re.I)
    for (body,) in q(world, "SELECT body FROM news_articles WHERE company_id='CMP-0001'"):
        assert not bad.search(body)


# ---------------------------------------------------------------- planted events and determinism

def test_planted_events(world):
    planted = json.loads((world["dir"] / "planted_events.json").read_text())
    assert 50 <= len({p["company_id"] for p in planted}) <= 70
    assert {p["kind"] for p in planted} == {"regulatory_penalty", "ocems", "land_alerts", "rec_unretired"}
    idcol = {"regulatory_actions": "action_id", "ocems_exceedances": "event_id", "land_alerts": "alert_id", "re_certificates": "cert_id"}
    for p in planted:
        assert p["company_id"] not in ("CMP-0001", "CMP-0002", "CMP-0003")
        assert p["refs"] and p["fy"] in spec.FISCAL_YEARS and p["metric"] in spec.METRICS
        for ref in p["refs"]:
            assert one(world, f"SELECT COUNT(*) FROM {p['table']} WHERE {idcol[p['table']]}=?", ref) == 1
        if p["kind"] == "regulatory_penalty":
            assert p["true_value"] == sum(one(world, "SELECT penalty_inr FROM regulatory_actions WHERE action_id=?", r) for r in p["refs"]) > 0
        if p["kind"] == "ocems":
            assert p["true_value"] == len(p["refs"]) >= 5
        if p["kind"] == "land_alerts":
            assert round(sum(one(world, "SELECT area_ha FROM land_alerts WHERE alert_id=?", r) for r in p["refs"]), 1) == p["true_value"]
        if p["kind"] == "rec_unretired":
            assert p["details"]["active_mwh"] > p["details"]["retired_mwh"] > 0


def test_build_is_deterministic(tmp_path):
    def digest(path):
        con = sqlite3.connect(path)
        h = hashlib.sha256()
        for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            for row in con.execute(f"SELECT * FROM {t} ORDER BY 1"):
                h.update(repr(row).encode())
        con.close()
        return h.hexdigest()

    a, b = tmp_path / "a" / "w.db", tmp_path / "b" / "w.db"
    build_world.build(a, verbose=False)
    build_world.build(b, verbose=False)
    assert digest(a) == digest(b)
    assert (a.parent / "planted_events.json").read_text() == (b.parent / "planted_events.json").read_text()
