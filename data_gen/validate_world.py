"""
data_gen/validate_world.py

Invariant checks for data/world/world.db.   python3 -m data_gen.validate_world [DB_PATH]
Exits non-zero if any invariant fails.  Also importable: validate(path) -> list[str] of errors.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import spec
from .build_world import DEFAULT_DB, KUTCH, TARGETS
from .world_utils import fy_range, haversine_km, wc

CIN_RE = re.compile(r"^[LU]\d{5}[A-Z]{2}\d{4}(PLC|PTC)\d{6}$")
TOPICS = {"emissions", "energy", "water", "waste", "biodiversity", "regulatory", "safety", "diversity", "governance",
          "assurance", "results"}


def _q(con, sql, *a):
    return con.execute(sql, a).fetchall()


def check_integrity(con) -> list[str]:
    errs = []
    for t, rowid, parent, fk in _q(con, "PRAGMA foreign_key_check"):
        errs.append(f"FK violation: {t} rowid {rowid} -> {parent}")
    return errs


def check_counts(con) -> list[str]:
    errs = []
    for t, target in TARGETS.items():
        n = _q(con, f"SELECT COUNT(*) FROM {t}")[0][0]
        if not (0.75 * target <= n <= 1.25 * target):
            errs.append(f"count {t}={n} outside +-25% of {target}")
    return errs


def check_companies(con) -> list[str]:
    errs = []
    rows = _q(con, "SELECT company_id,cin,name,short_name,aliases,sector,listing,market_cap_band FROM companies")
    ids = [r[0] for r in rows]
    if ids != [f"CMP-{i:04d}" for i in range(1, 151)]:
        errs.append("company ids are not CMP-0001..CMP-0150")
    sec = Counter(r[5] for r in rows)
    for s in spec.SECTORS:
        if not (13 <= sec[s] <= 17):
            errs.append(f"sector {s} has {sec[s]} companies")
    for cid, cin, name, short, aliases, sector, listing, band in rows:
        if not CIN_RE.match(cin):
            errs.append(f"bad CIN {cin}")
        if "aurelia" in name.lower():
            errs.append("aurelia company")
        if not isinstance(json.loads(aliases), list):
            errs.append(f"aliases not JSON array for {cid}")
        if band not in ("Large", "Mid", "Small"):
            errs.append(f"bad band {cid}")
        if sector not in spec.SECTORS:
            errs.append(f"bad sector {cid}")
        if listing != "Unlisted" and not re.match(r"^(NSE|BSE|NSE, BSE): \S+$", listing):
            errs.append(f"bad listing {listing}")
    if len({r[2] for r in rows}) != 150:
        errs.append("duplicate company names")
    return errs


def check_brsr(con) -> list[str]:
    errs = []
    n = _q(con, "SELECT company_id, COUNT(*) FROM brsr_filings GROUP BY company_id")
    if len(n) != 150 or any(c != 6 for _, c in n):
        errs.append("brsr: not exactly 6 filings per company")
    for r in _q(con, "SELECT filing_id,company_id,fy,revenue_cr,scope1_tco2e,scope2_tco2e,ghg_intensity,re_pct,ltifr,fatalities,"
                     "women_wage_pct,msme_sourcing_pct,assurance_type,assurance_provider,filed_on,waste_generated_t,waste_recovered_t,"
                     "water_withdrawal_kl,water_discharge_kl FROM brsr_filings"):
        (fid, cid, fy, rev, s1, s2, gi, re_, ltifr, fat, women, msme, at, prov, filed, wg, wr, ww, wd) = r
        if abs(round((s1 + s2) / rev, 1) - gi) > 1e-9:
            errs.append(f"{fid}: intensity {gi} != {(s1 + s2) / rev:.2f}")
        if not 0 <= re_ <= 100:
            errs.append(f"{fid}: re_pct {re_}")
        if not 0.05 <= ltifr <= 1.2:
            errs.append(f"{fid}: ltifr {ltifr}")
        if at not in ("none", "limited", "reasonable"):
            errs.append(f"{fid}: assurance_type {at}")
        if (at == "none") != (prov is None):
            errs.append(f"{fid}: assurance provider inconsistent")
        if not (filed[:4] == fy[2:] and filed[5:7] in ("07", "08", "09")):
            errs.append(f"{fid}: filed_on {filed} not Jul-Sep after FY end")
        if wr > wg or wd > ww or fat < 0 or not (0 <= women <= 100) or not (0 <= msme <= 100):
            errs.append(f"{fid}: implausible waste/water/people values")
    # assurance progression: never regress reasonable -> limited -> none for generated companies
    rank = {"none": 0, "limited": 1, "reasonable": 2}
    by = defaultdict(dict)
    for cid, fy, at in _q(con, "SELECT company_id, fy, assurance_type FROM brsr_filings"):
        by[cid][fy] = rank[at]
    for cid, d in by.items():
        seq = [d[f] for f in spec.FISCAL_YEARS]
        if any(b < a for a, b in zip(seq, seq[1:])):
            errs.append(f"{cid}: assurance regresses")
    return errs


def check_facilities(con) -> list[str]:
    errs = []
    for fid, lat, lon, state, fa, ftype in _q(con, "SELECT facility_id,lat,lon,state,forest_adjacent,type FROM facilities"):
        if not (6.5 <= lat <= 37.5 and 68 <= lon <= 97.5):
            errs.append(f"{fid}: coordinates outside India")
    ids = [r[0] for r in _q(con, "SELECT facility_id FROM facilities ORDER BY facility_id")]
    if ids != [f"FAC-{i:04d}" for i in range(1, len(ids) + 1)]:
        errs.append("facility ids not contiguous")
    n_fa = _q(con, "SELECT COUNT(*) FROM facilities WHERE forest_adjacent=1")[0][0]
    if n_fa < 10:
        errs.append(f"too few forest-adjacent facilities: {n_fa}")
    # every company has at least one facility
    if _q(con, "SELECT COUNT(*) FROM companies c WHERE NOT EXISTS (SELECT 1 FROM facilities f WHERE f.company_id=c.company_id)")[0][0]:
        errs.append("company without facility")
    return errs


def check_ghg(con) -> list[str]:
    errs = []
    nf = _q(con, "SELECT COUNT(*) FROM facilities")[0][0]
    if _q(con, "SELECT COUNT(*) FROM facility_ghg")[0][0] != nf * 6:
        errs.append("facility_ghg is not facility x 6 FY")
    q = """SELECT b.company_id, b.fy, b.scope1_tco2e, SUM(g.total_tco2e) FROM brsr_filings b
           JOIN facilities f ON f.company_id=b.company_id JOIN facility_ghg g ON g.facility_id=f.facility_id AND g.fy=b.fy
           GROUP BY b.company_id, b.fy"""
    rows = _q(con, q)
    if len(rows) != 900:
        errs.append(f"facility_ghg join covers {len(rows)} company-years, expected 900")
    for cid, fy, s1, tot in rows:
        if abs(tot - s1) > 0.005 * s1:
            errs.append(f"{cid} {fy}: facility sum {tot:.0f} vs scope1 {s1:.0f}")
    for r in _q(con, "SELECT row_id, co2_t, ch4_tco2e, n2o_tco2e, total_tco2e FROM facility_ghg"):
        if abs(r[1] + r[2] + r[3] - r[4]) > 0.2 or min(r[1:]) < 0:
            errs.append(f"{r[0]}: gas components do not add up")
    return errs


def check_ocems(con) -> list[str]:
    errs = []
    for r in _q(con, "SELECT event_id, limit_value, reading, parameter, unit FROM ocems_exceedances"):
        if not r[2] > r[1]:
            errs.append(f"{r[0]}: reading {r[2]} <= limit {r[1]}")
        if (r[3] in ("PM", "SO2", "NOx")) != (r[4] == "mg/Nm3"):
            errs.append(f"{r[0]}: parameter/unit mismatch")
    return errs


def check_regs(con) -> list[str]:
    errs = []
    for r in _q(con, "SELECT action_id, company_id, penalty_inr, authority, order_type FROM regulatory_actions"):
        if r[1] not in ("CMP-0001", "CMP-0002", "CMP-0003") and r[2] > 0 and not (5e5 <= r[2] <= 2.5e8):
            errs.append(f"{r[0]}: penalty {r[2]} outside Rs 5 lakh - 25 crore")
        if r[3] == "SEBI" and r[4] not in ("warning", "penalty"):
            errs.append(f"{r[0]}: SEBI order type {r[4]}")
    return errs


def check_alerts(con) -> list[str]:
    errs = []
    fac = {r[0]: (r[1], r[2]) for r in _q(con, "SELECT facility_id, lat, lon FROM facilities")}
    for aid, lat, lon, nf, dist in _q(con, "SELECT alert_id,lat,lon,nearest_facility_id,distance_km FROM land_alerts"):
        if haversine_km(lat, lon, *KUTCH) < 15:
            errs.append(f"{aid}: within 15 km of Kutch")
        best = min((haversine_km(lat, lon, a, b), fid) for fid, (a, b) in fac.items())
        if best[0] <= 25:
            if nf != best[1] or dist is None or abs(dist - best[0]) > 0.02:
                errs.append(f"{aid}: nearest facility mismatch ({nf}, {dist}) vs {best}")
        elif nf is not None or dist is not None:
            errs.append(f"{aid}: should have NULL nearest facility")
    return errs


def check_audits(con) -> list[str]:
    errs = []
    brsr = {(c, fy): (at, prov) for c, fy, at, prov in _q(con, "SELECT company_id, fy, assurance_type, assurance_provider FROM brsr_filings")}
    seen = set()
    for rid, cid, fy, auditor, at, op, text, qi in _q(con, "SELECT report_id,company_id,fy,auditor,assurance_type,opinion,text,qualified_items FROM audited_reports"):
        seen.add((cid, fy))
        if brsr[(cid, fy)][0] != at or brsr[(cid, fy)][1] != auditor:
            errs.append(f"{rid}: assurance type/auditor differs from BRSR")
        if not 120 <= wc(text) <= 300:
            errs.append(f"{rid}: {wc(text)} words")
        if (op == "qualified") != (qi is not None):
            errs.append(f"{rid}: qualified_items inconsistent")
    expected = {k for k, v in brsr.items() if v[0] != "none"}
    if seen != expected:
        errs.append("audited_reports are not exactly the (company, FY) pairs with assurance != none")
    return errs


def check_news(con) -> list[str]:
    errs = []
    co = {r[0]: r for r in _q(con, "SELECT company_id,name,short_name,aliases FROM companies")}
    tied = 0
    rows = _q(con, "SELECT article_id,company_id,outlet,outlet_tier,published_on,headline,body,topics FROM news_articles")
    for aid, cid, outlet, tier, pub, head, body, topics in rows:
        if not 250 <= wc(body) <= 600:
            errs.append(f"{aid}: {wc(body)} words")
        tp = json.loads(topics)
        if not tp or not set(tp) <= TOPICS:
            errs.append(f"{aid}: bad topics {tp}")
        if tier not in (4, 5):
            errs.append(f"{aid}: tier {tier}")
        if (tier == 4) != outlet.endswith("(press release)"):
            errs.append(f"{aid}: tier/outlet mismatch")
        if pub > "2026-10-04":
            errs.append(f"{aid}: dated in the future")
        if cid:
            tied += 1
            _, name, short, aliases = co[cid]
            names = [name, short] + json.loads(aliases)
            if not any(n in head or n in body for n in names[:2]):
                errs.append(f"{aid}: company name not in headline/body")
    if not 0.5 <= tied / len(rows) <= 0.7:
        errs.append(f"tied share {tied / len(rows):.2f}")
    if len({r[2] for r in rows if r[3] == 5}) < 12:
        errs.append("fewer than 12 distinct news outlets")
    # an article about a penalty must reference a real regulatory_actions row (same amount/date)
    for aid, cid, outlet, tier, pub, head, body, topics in rows:
        if cid and "regulatory" in json.loads(topics) and re.search(r"(dated|order is dated) \d{1,2} \w+ \d{4}", body):
            m = re.search(r"dated (\d{1,2}) (\w+) (\d{4})", body)
            if m:
                from .world_utils import MONTHS
                iso = f"{m.group(3)}-{MONTHS.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}"
                if not _q(con, "SELECT 1 FROM regulatory_actions WHERE company_id=? AND date=?", cid, iso):
                    errs.append(f"{aid}: cites order date {iso} not in regulatory_actions")
    return errs


def check_no_aurelia(con) -> list[str]:
    errs = []
    tables = [r[0] for r in _q(con, "SELECT name FROM sqlite_master WHERE type='table'")]
    for t in tables:
        cols = [r[1] for r in _q(con, f"PRAGMA table_info({t})") if r[2].upper() == "TEXT"]
        for c in cols:
            n = _q(con, f"SELECT COUNT(*) FROM {t} WHERE lower({c}) LIKE '%aurelia%'")[0][0]
            if n:
                errs.append(f"'aurelia' found in {t}.{c}")
    return errs


def check_demo(con) -> list[str]:
    errs = []

    def one(sql, *a):
        return _q(con, sql, *a)[0][0]

    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        cid = d["company_id"]
        row = _q(con, "SELECT cin,name,short_name,aliases,sector,hq_city,hq_state,listing,market_cap_band FROM companies WHERE company_id=?", cid)[0]
        exp = (d["cin"], d["name"], d["short_name"], json.dumps(d["aliases"]), d["sector"], d["hq_city"], d["hq_state"], d["listing"],
               {"CMP-0001": "Large", "CMP-0002": "Mid", "CMP-0003": "Small"}[cid])
        if row != exp:
            errs.append(f"{cid}: company row differs from spec")
        for f in d["facilities"]:
            fr = _q(con, "SELECT company_id,name,type,district,state,lat,lon,capacity_value,capacity_unit,forest_adjacent FROM facilities WHERE facility_id=?", f["facility_id"])
            if not fr or fr[0] != (cid, f["name"], f["type"], f["district"], f["state"], f["lat"], f["lon"], f["capacity_value"], f["capacity_unit"], int(f["forest_adjacent"])):
                errs.append(f"{f['facility_id']}: facility row differs from spec")
        if one("SELECT COUNT(*) FROM facilities WHERE company_id=?", cid) != len(d["facilities"]):
            errs.append(f"{cid}: wrong facility count")
        # BRSR truth
        t = d["true"]
        for i, fy in enumerate(spec.FISCAL_YEARS):
            r = _q(con, "SELECT revenue_cr,scope1_tco2e,scope2_tco2e,ghg_intensity,energy_gj,re_pct,water_withdrawal_kl,water_discharge_kl,waste_generated_t,"
                        "waste_recovered_t,ltifr,fatalities,women_wage_pct,msme_sourcing_pct,assurance_type,assurance_provider FROM brsr_filings WHERE company_id=? AND fy=?", cid, fy)[0]
            keys = ["revenue_cr", "scope1_tco2e", "scope2_tco2e"]
            exp = [t[k][i] for k in keys] + [round((t["scope1_tco2e"][i] + t["scope2_tco2e"][i]) / t["revenue_cr"][i], 1)] + \
                  [t[k][i] for k in ["energy_gj", "re_pct", "water_withdrawal_kl", "water_discharge_kl", "waste_generated_t", "waste_recovered_t", "ltifr",
                                     "fatalities", "women_wage_pct", "msme_sourcing_pct", "assurance_type", "assurance_provider"]]
            if list(r) != exp:
                errs.append(f"{cid} {fy}: BRSR row differs from spec")
        # regulatory actions: exactly spec
        got = _q(con, "SELECT facility_id,authority,order_type,date,penalty_inr,status,case_no,summary FROM regulatory_actions WHERE company_id=? ORDER BY date", cid)
        want = sorted([(e["facility_id"], e["authority"], e["order_type"], e["date"], float(e["penalty_inr"]), e["status"], e["case_no"], e["summary"])
                       for e in d["events"]["regulatory_actions"]], key=lambda x: x[3])
        if got != want:
            errs.append(f"{cid}: regulatory_actions differ from spec")
        # ocems
        ev = d["events"]["ocems_exceedances"]
        a, b = (x.isoformat() for x in fy_range(ev["fy"]))
        fac_ids = [f["facility_id"] for f in d["facilities"]]
        ph = ",".join("?" * len(fac_ids))
        rows = _q(con, f"SELECT facility_id, parameter FROM ocems_exceedances WHERE facility_id IN ({ph}) AND date BETWEEN ? AND ?", *fac_ids, a, b)
        if len(rows) != ev["count"] or any(r[0] != ev["facility_id"] for r in rows) or not {r[1] for r in rows} <= set(ev["parameters"]) \
                or (ev["count"] and {r[1] for r in rows} != set(ev["parameters"])):
            errs.append(f"{cid}: FY2025 exceedances differ from spec ({len(rows)} vs {ev['count']})")
        if cid == "CMP-0003" and one(f"SELECT COUNT(*) FROM ocems_exceedances WHERE facility_id IN ({ph})", *fac_ids) != 0:
            errs.append("Kaveri has exceedances")
        # land alerts
        la = d["events"]["land_alerts"]
        fac = {f["facility_id"]: f for f in d["facilities"]}[la["facility_id"]]
        alerts = _q(con, "SELECT lat, lon, alert_date, area_ha FROM land_alerts")
        near = [x for x in alerts if haversine_km(fac["lat"], fac["lon"], x[0], x[1]) <= la["radius_km"]]
        if cid == "CMP-0001":
            if len(near) != la["count"] or any(not (la["from"] <= x[2] <= la["to"]) for x in near) or abs(sum(x[3] for x in near) - la["total_ha"]) > 1e-6:
                errs.append(f"CMP-0001: Keonjhar alerts {len(near)} / {sum(x[3] for x in near):.2f} ha differ from spec")
        else:
            a0, b0 = (x.isoformat() for x in fy_range("FY2025"))
            for f in d["facilities"]:
                bad = [x for x in alerts if a0 <= x[2] <= b0 and haversine_km(f["lat"], f["lon"], x[0], x[1]) <= 10]
                if bad:
                    errs.append(f"{f['facility_id']}: {len(bad)} FY2025 alerts within 10 km")
        # RECs
        rc = d["events"]["re_certificates"]
        ret = one("SELECT COALESCE(SUM(mwh),0) FROM re_certificates WHERE company_id=? AND vintage_year=? AND status='retired'", cid, rc["vintage"])
        act = one("SELECT COALESCE(SUM(mwh),0) FROM re_certificates WHERE company_id=? AND vintage_year=? AND status='active'", cid, rc["vintage"])
        if ret != rc["retired_mwh"] or act != rc["active_mwh"]:
            errs.append(f"{cid}: REC totals {ret}/{act} differ from spec")
        # news
        for n in d["news"]:
            r = _q(con, "SELECT outlet_tier, headline, published_on FROM news_articles WHERE company_id=? AND outlet=? AND published_on=? AND headline=?",
                   cid, n["outlet"], n["date"], n["headline"])
            if not r or r[0][0] != n["tier"]:
                errs.append(f"{cid}: spec news '{n['headline']}' missing or wrong tier")
        extra = one("SELECT COUNT(*) FROM news_articles WHERE company_id=?", cid) - len(d["news"])
        if not 2 <= extra <= 5:
            errs.append(f"{cid}: {extra} extra news articles (want 2-5)")
    # Sahyadri: exactly 6 FY2025 events at FAC-0005 and none at other facilities in FY2025 (covered above). No Aurelia in DB.
    return errs


def check_planted(con, planted_path: Path) -> list[str]:
    errs = []
    if not planted_path.exists():
        return [f"missing {planted_path}"]
    planted = json.loads(planted_path.read_text())
    if not 45 <= len({p["company_id"] for p in planted}) <= 75:
        errs.append(f"planted events cover {len({p['company_id'] for p in planted})} companies")
    idcol = {"regulatory_actions": "action_id", "ocems_exceedances": "event_id", "land_alerts": "alert_id", "re_certificates": "cert_id"}
    for p in planted:
        if p["company_id"] in ("CMP-0001", "CMP-0002", "CMP-0003"):
            errs.append("planted event on a demo company")
        if not p["refs"]:
            errs.append(f"planted {p['kind']} {p['company_id']} has no refs")
        for ref in p["refs"]:
            if not _q(con, f"SELECT 1 FROM {p['table']} WHERE {idcol[p['table']]}=?", ref):
                errs.append(f"planted ref {ref} missing in {p['table']}")
        if p["kind"] == "regulatory_penalty" and not p["true_value"] > 0:
            errs.append(f"planted penalty for {p['company_id']} is zero")
        if p["kind"] == "ocems" and p["true_value"] < 5:
            errs.append(f"planted ocems for {p['company_id']} too small")
        if p["kind"] == "land_alerts" and p["true_value"] <= 0:
            errs.append(f"planted land alerts for {p['company_id']} empty")
        if p["kind"] == "rec_unretired" and not p["details"]["active_mwh"] > p["details"]["retired_mwh"]:
            errs.append(f"planted rec for {p['company_id']}: active <= retired")
    return errs


def validate(db_path: str | Path | None = None) -> list[str]:
    path = Path(db_path) if db_path else DEFAULT_DB
    con = sqlite3.connect(path)
    try:
        errs: list[str] = []
        for fn in (check_integrity, check_counts, check_companies, check_brsr, check_facilities, check_ghg, check_ocems, check_regs,
                   check_alerts, check_audits, check_news, check_no_aurelia, check_demo):
            errs += [f"[{fn.__name__}] {e}" for e in fn(con)]
        errs += [f"[check_planted] {e}" for e in check_planted(con, path.parent / "planted_events.json")]
        return errs
    finally:
        con.close()


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else DEFAULT_DB
    errs = validate(path)
    if errs:
        print(f"VALIDATION FAILED: {len(errs)} problem(s)")
        for e in errs[:60]:
            print("  -", e)
        return 1
    print(f"OK: all invariants hold for {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
