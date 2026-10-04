"""
tests/test_benchmark.py

Validates data/benchmark/cases.jsonl (the 200-case claim-verification benchmark):
schema, composition, split, demo exclusion, evidence refs, and an INDEPENDENT recomputation (own SQL,
own haversine) of the label-supporting fact for every ALIGN / CONTRADICT value case, using the
machine-checkable facts in data/benchmark/verification.jsonl.
"""

from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from data_gen import spec

ROOT = Path(__file__).resolve().parent.parent
BM = ROOT / "data" / "benchmark"
DB = ROOT / "data" / "world" / "world.db"

FIELDS = ["case_id", "company_id", "company_name", "claim_text", "metric", "fy", "baseline_fy", "label",
          "gw_type", "difficulty", "truth_note", "evidence_refs", "split"]
PK = {"companies": "company_id", "facilities": "facility_id", "brsr_filings": "filing_id", "facility_ghg": "row_id",
      "ocems_exceedances": "event_id", "regulatory_actions": "action_id", "land_alerts": "alert_id",
      "re_certificates": "cert_id", "audited_reports": "report_id", "news_articles": "article_id"}
DEMO = {"CMP-0001", "CMP-0002", "CMP-0003"}


def _load(p):
    return [json.loads(x) for x in open(p) if x.strip()]


@pytest.fixture(scope="module")
def cases():
    return _load(BM / "cases.jsonl")


@pytest.fixture(scope="module")
def ver():
    return {v["case_id"]: v for v in _load(BM / "verification.jsonl")}


@pytest.fixture(scope="module")
def db():
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


# ------------------------------------------------------------------ schema / composition
def test_schema_and_enums(cases):
    assert len(cases) == 200
    ids = [c["case_id"] for c in cases]
    assert ids == [f"BM-{i:03d}" for i in range(1, 201)]
    for c in cases:
        assert list(c.keys()) == FIELDS, c["case_id"]
        assert c["label"] in spec.LABELS
        assert c["gw_type"] in spec.GREENWASHING_TYPES
        assert c["difficulty"] in ("easy", "medium", "hard")
        assert c["split"] in ("train", "test")
        assert c["metric"] is None or c["metric"] in spec.METRICS
        assert c["fy"] is None or c["fy"] in spec.FISCAL_YEARS + ["FY2019", "FY2026"]
        assert c["baseline_fy"] is None or c["baseline_fy"] in spec.FISCAL_YEARS
        assert isinstance(c["claim_text"], str) and len(c["claim_text"]) > 20
        assert "—" not in c["claim_text"], "em dash in copy"
        assert isinstance(c["truth_note"], str) and c["truth_note"]
        assert isinstance(c["evidence_refs"], list)
        assert all(isinstance(r, str) and r.count(":") == 1 for r in c["evidence_refs"])
    assert len({c["claim_text"] for c in cases}) == 200


def test_label_counts(cases):
    n = Counter(c["label"] for c in cases)
    assert n == {"ALIGN": 60, "CONTRADICT": 70, "INSUFFICIENT_EVIDENCE": 40, "NOT_CHECKABLE": 30}


def test_split_sizes_and_stratification(cases):
    assert Counter(c["split"] for c in cases) == {"train": 140, "test": 60}
    for lab in spec.LABELS:
        tot = sum(1 for c in cases if c["label"] == lab)
        te = sum(1 for c in cases if c["label"] == lab and c["split"] == "test")
        assert abs(te - tot * 0.3) <= 1, (lab, te, tot)


def test_gw_type_coverage(cases):
    n = Counter(c["gw_type"] for c in cases)
    for g in spec.GREENWASHING_TYPES:
        assert n[g] >= 5, (g, n[g])
    # typed greenwashing only on CONTRADICT; ALIGN is honest
    assert all(c["gw_type"] == "none" for c in cases if c["label"] == "ALIGN")
    assert all(c["gw_type"] != "none" for c in cases if c["label"] == "CONTRADICT")
    assert all(c["gw_type"] == "data_not_disclosed" for c in cases if c["label"] == "INSUFFICIENT_EVIDENCE")


def test_difficulty_mix(cases):
    n = Counter(c["difficulty"] for c in cases)
    assert all(n[d] >= 20 for d in ("easy", "medium", "hard"))
    hard_types = {"scope_swap", "absolute_vs_intensity", "unit_error", "unretired_certificates", "geo_contradiction",
                  "baseline_shift", "cherry_picked_year", "hidden_regulatory_penalty"}
    assert all(c["difficulty"] == "hard" for c in cases if c["gw_type"] in hard_types)


def test_template_diversity():
    stats = json.load(open(BM / "stats.json"))
    assert stats["n_templates"] >= 40
    assert stats["total"] == 200
    assert (BM / "README.md").read_text().startswith("# ESG claim-verification benchmark")


def test_claim_phrasing_variants(cases):
    txt = " ".join(c["claim_text"] for c in cases)
    for needle in ("FY2024-25", "per cent", "lakh", "crore", "tCO2e"):
        assert needle in txt, needle


# ------------------------------------------------------------------ companies
def test_company_rules(cases, db):
    comp = {r["company_id"]: r for r in db.execute("SELECT * FROM companies")}
    known = set()
    for r in comp.values():
        known |= {r["name"].lower(), r["short_name"].lower()} | {a.lower() for a in json.loads(r["aliases"])}
    fict = 0
    for c in cases:
        cid = c["company_id"]
        assert cid not in DEMO
        if cid is None:
            fict += 1
            assert c["label"] == "INSUFFICIENT_EVIDENCE"
            name = c["company_name"].lower()
            first = name.split()[0]
            assert name not in known and not any(first in k for k in known), name
            assert c["company_name"] in c["claim_text"]
            assert c["evidence_refs"] == []
        else:
            assert "CMP-0004" <= cid <= "CMP-0150"
            assert cid in comp and c["company_name"] == comp[cid]["name"]
    assert fict >= 10


def test_evidence_refs_exist(cases, db):
    n = 0
    for c in cases:
        for ref in c["evidence_refs"]:
            table, rid = ref.split(":")
            assert table in PK, ref
            hit = db.execute(f"SELECT 1 FROM {table} WHERE {PK[table]}=?", (rid,)).fetchone()
            assert hit, f"{c['case_id']}: missing {ref}"
            n += 1
    assert n > 200
    for c in cases:
        if c["label"] in ("ALIGN", "CONTRADICT"):
            assert c["evidence_refs"], c["case_id"]
        if c["company_id"] and c["label"] == "CONTRADICT":
            pass


def test_insufficient_cases_really_have_no_source(cases, db):
    cols = {r["name"] for r in db.execute("PRAGMA table_info(brsr_filings)")}
    for c in cases:
        if c["label"] != "INSUFFICIENT_EVIDENCE":
            continue
        if c["metric"] in ("scope3_tco2e", "clinker_factor"):
            assert c["metric"] not in cols
        if c["fy"] in ("FY2019", "FY2026"):
            assert db.execute("SELECT COUNT(*) FROM brsr_filings WHERE fy=?", (c["fy"],)).fetchone()[0] == 0
    n = Counter(c["metric"] for c in cases if c["label"] == "INSUFFICIENT_EVIDENCE")
    assert n["scope3_tco2e"] >= 5 and n["clinker_factor"] >= 3


def test_not_checkable_have_no_evidence(cases):
    for c in cases:
        if c["label"] == "NOT_CHECKABLE":
            assert c["evidence_refs"] == [] and c["fy"] is None


# ------------------------------------------------------------------ independent recomputation
def fy_range(fy):
    y = int(fy[2:])
    return f"{y - 1}-04-01", f"{y}-03-31"


def hav(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def brsr(db, cid, fy, metric):
    r = db.execute("SELECT * FROM brsr_filings WHERE company_id=? AND fy=?", (cid, fy)).fetchone()
    assert r, (cid, fy)
    if metric == "waste_recovery_pct":
        return 100.0 * r["waste_recovered_t"] / r["waste_generated_t"]
    return r[metric]


def actual(db, it):
    k = it["kind"]
    if k == "brsr_value":
        return brsr(db, it["company_id"], it["fy"], it["metric"])
    if k == "brsr_change":
        a, b = brsr(db, it["company_id"], it["fy"], it["metric"]), brsr(db, it["company_id"], it["baseline_fy"], it["metric"])
        return (a / b - 1.0) * 100.0
    if k == "ocems_count":
        lo, hi = fy_range(it["fy"])
        if it["facility_id"]:
            q, args = "SELECT COUNT(*) FROM ocems_exceedances WHERE facility_id=? AND date BETWEEN ? AND ?", (it["facility_id"], lo, hi)
        else:
            q = ("SELECT COUNT(*) FROM ocems_exceedances o JOIN facilities f ON f.facility_id=o.facility_id "
                 "WHERE f.company_id=? AND o.date BETWEEN ? AND ?")
            args = (it["company_id"], lo, hi)
        return db.execute(q, args).fetchone()[0]
    if k == "reg_count":
        lo, hi = fy_range(it["fy"])
        q = "SELECT COUNT(*) FROM regulatory_actions WHERE company_id=? AND date BETWEEN ? AND ?"
        if it["penalty_only"]:
            q += " AND penalty_inr>0"
        return db.execute(q, (it["company_id"], lo, hi)).fetchone()[0]
    if k == "reg_penalty_inr":
        lo, hi = fy_range(it["fy"])
        return db.execute("SELECT COALESCE(SUM(penalty_inr),0) FROM regulatory_actions WHERE company_id=? AND date BETWEEN ? AND ?",
                          (it["company_id"], lo, hi)).fetchone()[0]
    if k == "alerts":
        lo, hi = fy_range(it["fy"])
        f = db.execute("SELECT lat, lon FROM facilities WHERE facility_id=?", (it["facility_id"],)).fetchone()
        rows = [r for r in db.execute("SELECT * FROM land_alerts WHERE alert_date BETWEEN ? AND ?", (lo, hi))
                if hav(f["lat"], f["lon"], r["lat"], r["lon"]) <= it["radius_km"]]
        return len(rows) if it["what"] == "count" else sum(r["area_ha"] for r in rows)
    if k == "rec":
        rows = db.execute("SELECT status, mwh FROM re_certificates WHERE company_id=? AND vintage_year=?",
                          (it["company_id"], it["vintage"])).fetchall()
        retired = sum(r["mwh"] for r in rows if r["status"] == "retired")
        if it["what"] == "retired_mwh":
            return retired
        return bool(rows) and all(r["status"] == "retired" for r in rows)
    if k == "assurance":
        return db.execute("SELECT assurance_type FROM brsr_filings WHERE company_id=? AND fy=?",
                          (it["company_id"], it["fy"])).fetchone()[0]
    raise AssertionError(k)


def judge(db, it):
    """Return (matches, strongly_mismatches) for one item."""
    k, claimed = it["kind"], it["claimed"]
    act = actual(db, it)
    if k == "brsr_value":
        cb = claimed * it["mult"]
        rel = (0.0 if cb == act else math.inf) if act == 0 else abs(cb - act) / abs(act)
        return rel <= 0.03, rel >= 0.15
    if k == "brsr_change":
        d = abs(claimed - act)
        return d <= max(0.05, 0.03 * abs(act)), (d >= 0.15 * abs(act) and d >= 2.0)
    if k in ("ocems_count", "reg_count"):
        return claimed == act, claimed != act
    if k == "alerts":
        if it["what"] == "count":
            return claimed == act, claimed != act
        rel = abs(claimed - act) / act if act else (0.0 if claimed == 0 else math.inf)
        return rel <= 0.03, rel >= 0.15
    if k == "reg_penalty_inr":
        rel = abs(claimed - act) / act if act else (0.0 if claimed == 0 else math.inf)
        return rel <= 0.03, rel >= 0.15
    if k == "rec":
        if it["what"] == "retired_mwh":
            rel = abs(claimed - act) / act if act else (0.0 if claimed == 0 else math.inf)
            return rel <= 0.03, rel >= 0.15
        return claimed == act, claimed != act
    if k == "assurance":
        if claimed == "assured":
            return act in ("limited", "reasonable"), act == "none"
        return claimed == act, claimed != act
    raise AssertionError(k)


def test_every_align_contradict_case_recomputed(cases, ver, db):
    checked = Counter()
    for c in cases:
        v = ver[c["case_id"]]
        assert v["case_id"] == c["case_id"]
        for lit in v["literals"]:
            assert lit in c["claim_text"], (c["case_id"], lit)
        if c["label"] not in ("ALIGN", "CONTRADICT"):
            assert v["items"] == []
            continue
        assert v["items"], c["case_id"]
        any_strong = False
        for it in v["items"]:
            ok, strong = judge(db, it)
            if it["expect"] == "match":
                assert ok, (c["case_id"], it, actual(db, it))
            else:
                assert it["expect"] == "mismatch" and strong and not ok, (c["case_id"], it, actual(db, it))
                any_strong = True
            checked[it["kind"]] += 1
        if c["label"] == "ALIGN":
            assert all(i["expect"] == "match" for i in v["items"]), c["case_id"]
        else:
            assert any_strong, c["case_id"]
    assert sum(checked.values()) >= 130
    for kind in ("brsr_value", "brsr_change", "ocems_count", "reg_count", "alerts", "rec", "assurance", "reg_penalty_inr"):
        assert checked[kind] > 0, kind


def test_trap_cases_are_real_traps(cases, ver, db):
    """Period traps: events exist in another FY; scope swaps equal the other scope; cherry picks hold for another year."""
    by = {c["case_id"]: c for c in cases}
    n_period = n_swap = n_cherry = n_abs = 0
    for cid, v in ver.items():
        c = by[cid]
        t = v["template_id"]
        if t.startswith("al_pt_pen") or t.startswith("al_pt_oc") or t == "al_pt_geo":
            n_period += 1
            assert c["label"] == "ALIGN" and c["difficulty"] == "hard" and "Period trap" in c["truth_note"]
        if c["gw_type"] == "scope_swap":
            n_swap += 1
            m1, m2 = v["items"][0], v["items"][1]
            assert m1["metric"] != m2["metric"]
        if c["gw_type"] == "cherry_picked_year":
            n_cherry += 1
            assert v["items"][1]["baseline_fy"] != c["baseline_fy"]
        if c["gw_type"] == "absolute_vs_intensity":
            n_abs += 1
            assert v["items"][1]["metric"] == "ghg_intensity" and v["items"][0]["metric"] == "scope1_tco2e"
    assert n_period == 5 and n_swap >= 5 and n_cherry >= 5 and n_abs >= 5


def test_benchmark_is_deterministic(cases, tmp_path):
    """Rebuilding gives byte-identical cases (seed 20261004); the DB is opened read-only."""
    import hashlib
    import importlib

    before = hashlib.sha256((BM / "cases.jsonl").read_bytes()).hexdigest()
    bb = importlib.import_module("data_gen.build_benchmark")
    importlib.reload(bb)
    bb.build()
    after = hashlib.sha256((BM / "cases.jsonl").read_bytes()).hexdigest()
    assert before == after
