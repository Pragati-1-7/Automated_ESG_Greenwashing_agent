"""
data_gen/build_benchmark.py

Builds the 200-case labelled benchmark for the ESG claim-verification system.

    python3 -m data_gen.build_benchmark

Outputs (data/benchmark/):
    cases.jsonl          one case per line (the public benchmark)
    verification.jsonl   machine-checkable facts per case (used by tests/test_benchmark.py to
                         recompute every ALIGN / CONTRADICT value claim from the world DB)
    stats.json           composition counts
    README.md            composition tables

Every number in a claim is computed from data/world/world.db with SQL / haversine. The DB is opened
read-only. Generated companies only (CMP-0004..CMP-0150); demo companies CMP-0001..0003 are excluded.
Deterministic: random.Random(20261004), pools are built in sorted order.
ALL COMPANIES AND FIGURES ARE FICTIONAL.
"""

from __future__ import annotations

import json
import os
import math
import random
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

from . import spec
from .world_utils import haversine_km

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "world" / "world.db"
PLANTED = ROOT / "data" / "world" / "planted_events.json"
OUT_DIR = Path(os.environ.get("BENCH_OUT", ROOT / "data" / "benchmark"))

SEED = int(os.environ.get("BENCH_SEED", spec.SEED))  # default 20261004; override for a fresh held-out set
FYS = spec.FISCAL_YEARS
DEMO_IDS = {"CMP-0001", "CMP-0002", "CMP-0003"}
CIDS = [f"CMP-{i:04d}" for i in range(4, 151)]

TARGET = {"ALIGN": 60, "CONTRADICT": 70, "INSUFFICIENT_EVIDENCE": 40, "NOT_CHECKABLE": 30}

# --------------------------------------------------------------------------------------
# DB access (read-only) and caches
# --------------------------------------------------------------------------------------
conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row


def fy_of(date_iso: str) -> str:
    y, m = int(date_iso[:4]), int(date_iso[5:7])
    return f"FY{y + 1 if m >= 4 else y}"


COMP = {r["company_id"]: dict(r) for r in conn.execute("SELECT * FROM companies")}
BRSR: dict[str, dict[str, dict]] = defaultdict(dict)
for r in conn.execute("SELECT * FROM brsr_filings ORDER BY company_id, fy"):
    BRSR[r["company_id"]][r["fy"]] = dict(r)
FAC: dict[str, list[dict]] = defaultdict(list)
FACD: dict[str, dict] = {}
for r in conn.execute("SELECT * FROM facilities ORDER BY facility_id"):
    FAC[r["company_id"]].append(dict(r))
    FACD[r["facility_id"]] = dict(r)
OCE: dict[tuple[str, str], list[str]] = defaultdict(list)  # (facility, fy) -> event ids
for r in conn.execute("SELECT event_id, facility_id, date FROM ocems_exceedances ORDER BY event_id"):
    OCE[(r["facility_id"], fy_of(r["date"]))].append(r["event_id"])
REG: dict[tuple[str, str], list[dict]] = defaultdict(list)  # (company, fy) -> rows
for r in conn.execute("SELECT * FROM regulatory_actions ORDER BY action_id"):
    REG[(r["company_id"], fy_of(r["date"]))].append(dict(r))
ALERTS = [dict(r) for r in conn.execute("SELECT * FROM land_alerts ORDER BY alert_id")]
RECS: dict[str, list[dict]] = defaultdict(list)
for r in conn.execute("SELECT * FROM re_certificates ORDER BY cert_id"):
    RECS[r["company_id"]].append(dict(r))
AUDIT = {(r["company_id"], r["fy"]): r["report_id"] for r in conn.execute("SELECT * FROM audited_reports")}
PLANT = json.load(open(PLANTED))

_alert_cache: dict[tuple[str, str, float], list[dict]] = {}


def alerts_near(fid: str, fy: str, radius: float = 5.0) -> list[dict]:
    """Forest-loss alerts within `radius` km (haversine) of the facility, dated inside the FY."""
    key = (fid, fy, radius)
    if key not in _alert_cache:
        f = FACD[fid]
        _alert_cache[key] = [a for a in ALERTS if fy_of(a["alert_date"]) == fy
                             and haversine_km(f["lat"], f["lon"], a["lat"], a["lon"]) <= radius]
    return _alert_cache[key]


def nearest_alerts(fid: str, fy: str, radius: float = 5.0) -> list[dict]:
    return [a for a in ALERTS if a["nearest_facility_id"] == fid and a["distance_km"] is not None
            and a["distance_km"] <= radius and fy_of(a["alert_date"]) == fy]


def comp_ocems(cid: str, fy: str) -> list[str]:
    out: list[str] = []
    for f in FAC[cid]:
        out += OCE.get((f["facility_id"], fy), [])
    return sorted(out)


def v(cid: str, fy: str, m: str) -> float:
    r = BRSR[cid][fy]
    if m == "waste_recovery_pct":
        return r["waste_recovered_t"] / r["waste_generated_t"] * 100
    return r[m]


def chg(cid: str, m: str, fy: str, base: str) -> float:
    return (v(cid, fy, m) - v(cid, base, m)) / v(cid, base, m) * 100


def bref(cid: str, *fys: str) -> list[str]:
    return [f"brsr_filings:{BRSR[cid][fy]['filing_id']}" for fy in fys]


# --------------------------------------------------------------------------------------
# Randomness / selection helpers
# --------------------------------------------------------------------------------------
rng = random.Random(SEED)
USED: Counter = Counter()
TEMPLATES: set[str] = set()


def pick(cands: list, key=lambda x: x[0], n: int = 1) -> list:
    """Pick n candidates preferring least-used companies, random tie-break (deterministic)."""
    order = sorted(cands, key=lambda c: (USED[key(c)], rng.random()))
    seen, out = set(), []
    for c in order:
        k = key(c)
        if k in seen:
            continue
        seen.add(k)
        out.append(c)
        if len(out) == n:
            break
    assert len(out) == n, f"pool too small: wanted {n}, got {len(out)}"
    for c in out:
        USED[key(c)] += 1
    return out


def rfy(lo: int = 2022) -> str:
    return rng.choice([f for f in FYS if int(f[2:]) >= lo] + ["FY2025", "FY2025", "FY2024"])


def fyt(fy: str) -> str:
    y = int(fy[2:])
    return rng.choice([fy, f"FY{y - 1}-{str(y)[2:]}", f"FY {y - 1}-{str(y)[2:]}",
                       f"the financial year {y - 1}-{str(y)[2:]}", f"FY{y - 1}-{str(y)[2:]}"])


def fyt_plain(fy: str) -> str:
    y = int(fy[2:])
    return rng.choice([fy, fy, f"FY{y - 1}-{str(y)[2:]}"])


def nice(x: float) -> int:
    return max(1, int(round(x))) if x < 10 else int(5 * round(x / 5))


def indian(n: float) -> str:
    s = str(int(round(n)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def sig3(x: float) -> float:
    return float(f"{x:.3g}")


def sig3s(x: float) -> str:
    s = sig3(x)
    dec = max(0, 2 - int(math.floor(math.log10(abs(s))))) if s else 0
    return f"{s:,.{dec}f}" if s >= 1000 else f"{s:.{dec}f}"


def qty(value: float, kind: str, style: str | None = None) -> dict:
    """Format a DB-unit quantity in a claim style. Returns text/literal/claimed/mult."""
    opts = ["raw", "indian"]
    if value >= 1e5:
        opts.append("lakh")
    if value >= 1e6:
        opts.append("million")
    if value >= 1e7:
        opts.append("crore")
    if kind == "kl" and value >= 1e3:
        opts.append("ML")
    if kind == "gj" and value >= 1e4:
        opts.append("TJ")
    style = style if style in opts else rng.choice(opts)
    unit = {"tco2e": "tCO2e", "kl": "kL", "gj": "GJ"}[kind]
    if kind == "tco2e" and style == "raw" and rng.random() < 0.25:
        unit = "tonnes of CO2e"
    mult = {"raw": 1.0, "indian": 1.0, "lakh": 1e5, "million": 1e6, "crore": 1e7, "ML": 1e3, "TJ": 1e3}[style]
    if style in ("raw", "indian"):
        n = round(value)
        lit = f"{n:,}" if style == "raw" else indian(n)
        claimed = float(n)
        text = f"{lit} {unit}"
    else:
        lit = sig3s(value / mult)
        claimed = float(lit.replace(",", ""))
        if style in ("ML", "TJ"):
            text = f"{lit} {style}"
        elif style == "million":
            text = f"{lit} million {unit}"
        else:
            text = f"{lit} {style} {unit}"
    return {"text": text, "literal": lit, "claimed": claimed, "mult": mult}


def pct_claim(y: float) -> tuple[float, int]:
    """Round a true percentage so the claim is within ~3% relative of it."""
    r0 = round(y)
    if r0 != 0 and abs(r0 - y) / abs(y) <= 0.03:
        return float(r0), 0
    return round(y, 1), 1


def pctt(x: float, dec: int) -> tuple[str, str]:
    lit = f"{abs(x):.{dec}f}"
    return lit, (f"{lit} per cent" if rng.random() < 0.25 else f"{lit}%")


def money(inr: float) -> dict:
    pre = rng.choice(["Rs ", "Rs ", "INR ", "Rs. "])
    if inr >= 1e7:
        lit = sig3s(inr / 1e7)
        return {"text": f"{pre}{lit} crore", "literal": lit, "claimed": float(lit), "mult": 1e7}
    lit = sig3s(inr / 1e5)
    return {"text": f"{pre}{lit} lakh", "literal": lit, "claimed": float(lit), "mult": 1e5}


# --------------------------------------------------------------------------------------
# Check items (machine-checkable facts recomputed by the test)
# --------------------------------------------------------------------------------------
def it_value(cid, fy, metric, claimed, mult=1.0, expect="match"):
    return {"kind": "brsr_value", "company_id": cid, "fy": fy, "metric": metric,
            "claimed": claimed, "mult": mult, "expect": expect}


def it_change(cid, metric, fy, base, claimed, expect="match"):
    return {"kind": "brsr_change", "company_id": cid, "metric": metric, "fy": fy,
            "baseline_fy": base, "claimed": claimed, "expect": expect}


def it_ocems(cid, fac, fy, claimed, expect="match"):
    return {"kind": "ocems_count", "company_id": cid, "facility_id": fac, "fy": fy,
            "claimed": claimed, "expect": expect}


def it_reg(cid, fy, claimed, penalty_only, expect="match"):
    return {"kind": "reg_count", "company_id": cid, "fy": fy, "claimed": claimed,
            "penalty_only": penalty_only, "expect": expect}


def it_pen(cid, fy, claimed_inr, expect="match"):
    return {"kind": "reg_penalty_inr", "company_id": cid, "fy": fy, "claimed": claimed_inr, "expect": expect}


def it_alerts(fac, fy, claimed, what="count", expect="match", radius=5.0):
    return {"kind": "alerts", "facility_id": fac, "fy": fy, "radius_km": radius,
            "what": what, "claimed": claimed, "expect": expect}


def it_rec(cid, vintage, what, claimed, expect="match"):
    return {"kind": "rec", "company_id": cid, "vintage": vintage, "what": what,
            "claimed": claimed, "expect": expect}


def it_cat(cid, fy, claimed, expect="match"):
    return {"kind": "assurance", "company_id": cid, "fy": fy, "claimed": claimed, "expect": expect}


# --------------------------------------------------------------------------------------
# Case factory
# --------------------------------------------------------------------------------------
CASES: list[dict] = []


def mk(label, gw, diff, cid, metric, fy, base, text, note, refs, tid, items=None, literals=None, name=None):
    assert label in spec.LABELS and gw in spec.GREENWASHING_TYPES, (label, gw)
    assert metric is None or metric in spec.METRICS, metric
    assert "—" not in text and "–" not in text, text
    TEMPLATES.add(tid)
    refs = list(dict.fromkeys(refs))
    CASES.append({
        "case": {
            "case_id": None,
            "company_id": cid,
            "company_name": name if cid is None else COMP[cid]["name"],
            "claim_text": text,
            "metric": metric,
            "fy": fy,
            "baseline_fy": base,
            "label": label,
            "gw_type": gw,
            "difficulty": diff,
            "truth_note": note,
            "evidence_refs": refs,
            "split": None,
        },
        "ver": {"case_id": None, "template_id": tid, "items": items or [], "literals": literals or []},
    })


def fnum(x: float) -> str:
    return f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.4g}"


def co(cid: str) -> str:
    return COMP[cid]["short_name"]


# ======================================================================================
# ALIGN (60)
# ======================================================================================
def build_align():
    def pick_cf(ok=lambda cid, fy: True, lo=2022):
        cands = [(cid, fy) for cid in CIDS for fy in FYS if int(fy[2:]) >= lo and ok(cid, fy)]
        return pick(cands)[0]

    # ---- A1 direct value claims (22) -------------------------------------------------
    def emis(metric, kind, tpl_list, n, big=False):
        for i in range(n):
            ok = (lambda cid, fy: v(cid, fy, metric) >= 1e5) if big else (lambda cid, fy: True)
            cid, fy = pick_cf(ok)
            q = qty(v(cid, fy, metric), kind)
            tid, tpl = tpl_list[i % len(tpl_list)]
            text = tpl.format(co=co(cid), fy=fyt(fy), q=q["text"])
            mk("ALIGN", "none", "easy", cid, metric, fy, None, text,
               f"Filed {metric} for {fy} = {v(cid, fy, metric):,.0f} {spec.METRICS[metric]['unit']}; claim {q['text']} is within rounding.",
               bref(cid, fy), tid, [it_value(cid, fy, metric, q["claimed"], q["mult"])], [q["literal"]])

    emis("scope1_tco2e", "tco2e", [
        ("al_s1_a", "Our Scope 1 emissions for {fy} stood at {q}."),
        ("al_s1_b", "{co} reported Scope 1 GHG emissions of {q} in {fy}."),
        ("al_s1_c", "Direct (Scope 1) emissions during {fy} were {q}, as disclosed in our BRSR filing."),
    ], 3, big=True)
    emis("scope2_tco2e", "tco2e", [
        ("al_s2_a", "Scope 2 emissions from purchased electricity came to {q} in {fy}."),
        ("al_s2_b", "In {fy}, {co}'s Scope 2 footprint was {q}."),
    ], 2, big=True)
    for tid, tpl in [("al_gi_a", "GHG emission intensity was {x} tCO2e per Rs crore of turnover in {fy}."),
                     ("al_gi_b", "Our Scope 1 and 2 emissions intensity for {fy} was {x} tCO2e/Rs crore of revenue.")]:
        cid, fy = pick_cf()
        lit = sig3s(v(cid, fy, "ghg_intensity"))
        mk("ALIGN", "none", "easy", cid, "ghg_intensity", fy, None, tpl.format(x=lit, fy=fyt(fy)),
           f"Filed intensity {v(cid, fy, 'ghg_intensity')} tCO2e/Rs cr in {fy}.", bref(cid, fy), tid,
           [it_value(cid, fy, "ghg_intensity", float(lit.replace(',', '')))], [lit])
    emis("energy_gj", "gj", [
        ("al_en_a", "Total energy consumed across our operations in {fy} was {q}."),
        ("al_en_b", "{co} consumed {q} of energy during {fy}."),
    ], 2, big=True)
    for tid, tpl in [("al_re_a", "{p} of the electricity we consumed in {fy} came from renewable sources."),
                     ("al_re_b", "Renewable energy accounted for {p} of {co}'s electricity mix in {fy}."),
                     ("al_re_c", "Our renewable electricity share stood at {p} in {fy}.")]:
        cid, fy = pick_cf()
        y = v(cid, fy, "re_pct")
        r, dec = pct_claim(y)
        lit, p = pctt(r, dec)
        mk("ALIGN", "none", "easy", cid, "re_pct", fy, None, tpl.format(p=p, fy=fyt(fy), co=co(cid)),
           f"Filed renewable share {y}% in {fy}.", bref(cid, fy), tid, [it_value(cid, fy, "re_pct", r)], [lit])
    emis("water_withdrawal_kl", "kl", [
        ("al_ww_a", "We withdrew {q} of water in {fy}."),
        ("al_ww_b", "Total water withdrawal at {co} was {q} during {fy}."),
    ], 2)
    for tid, tpl in [("al_wr_a", "We recovered or recycled {p} of the waste generated in {fy}."),
                     ("al_wr_b", "Waste recovery rate at {co} in {fy} was {p}.")]:
        cid, fy = pick_cf()
        y = v(cid, fy, "waste_recovery_pct")
        r, dec = pct_claim(y)
        lit, p = pctt(r, dec)
        b = BRSR[cid][fy]
        mk("ALIGN", "none", "medium", cid, "waste_recovered_t", fy, None, tpl.format(p=p, fy=fyt(fy), co=co(cid)),
           f"Recovered {b['waste_recovered_t']:,.0f} t of {b['waste_generated_t']:,.0f} t generated = {y:.1f}% in {fy}.",
           bref(cid, fy), tid, [it_value(cid, fy, "waste_recovery_pct", r)], [lit])
    for tid, tpl in [("al_lt_a", "Our LTIFR was {x} per million person-hours in {fy}."),
                     ("al_lt_b", "{co} recorded a Lost Time Injury Frequency Rate of {x} in {fy}.")]:
        cid, fy = pick_cf()
        x = v(cid, fy, "ltifr")
        lit = f"{x:.2f}"
        mk("ALIGN", "none", "easy", cid, "ltifr", fy, None, tpl.format(x=lit, fy=fyt(fy), co=co(cid)),
           f"Filed LTIFR {x} in {fy}.", bref(cid, fy), tid, [it_value(cid, fy, "ltifr", float(lit))], [lit])
    cid, fy = pick_cf()
    y = v(cid, fy, "women_wage_pct")
    r, dec = pct_claim(y)
    lit, p = pctt(r, dec)
    mk("ALIGN", "none", "easy", cid, "women_wage_pct", fy, None,
       f"Women received {p} of total gross wages paid in {fyt(fy)}.", f"Filed {y}% in {fy}.", bref(cid, fy),
       "al_ww_women", [it_value(cid, fy, "women_wage_pct", r)], [lit])
    for tid, tpl in [("al_ms_a", "{p} of our input materials were sourced from MSMEs in {fy}."),
                     ("al_ms_b", "In {fy}, MSMEs accounted for {p} of {co}'s input material sourcing.")]:
        cid, fy = pick_cf()
        y = v(cid, fy, "msme_sourcing_pct")
        r, dec = pct_claim(y)
        lit, p = pctt(r, dec)
        mk("ALIGN", "none", "easy", cid, "msme_sourcing_pct", fy, None, tpl.format(p=p, fy=fyt(fy), co=co(cid)),
           f"Filed {y}% in {fy}.", bref(cid, fy), tid, [it_value(cid, fy, "msme_sourcing_pct", r)], [lit])
    cid, fy = pick_cf(lambda c, f: BRSR[c][f]["fatalities"] > 0)
    n = BRSR[cid][fy]["fatalities"]
    word = "fatality" if n == 1 else "fatalities"
    mk("ALIGN", "none", "easy", cid, "fatalities", fy, None,
       f"We deeply regret that {n} work-related {word} occurred at our sites in {fyt(fy)}.",
       f"Filed fatalities {n} in {fy}.", bref(cid, fy), "al_fat_n", [it_value(cid, fy, "fatalities", float(n))], [str(n)])

    # ---- A2 percentage change / two-year comparisons (8) ------------------------------
    def change_case(tid, tpl, metric, cands, diff="medium", base="FY2020", fy="FY2025"):
        cid = pick([(c,) for c in cands])[0][0]
        y = chg(cid, metric, fy, base)
        r, dec = pct_claim(abs(y))
        lit, p = pctt(r, dec)
        text = tpl.format(p=p, b=fyt_plain(base), fy=fyt(fy), co=co(cid))
        mk("ALIGN", "none", diff, cid, metric, fy, base, text,
           f"{metric}: {fnum(v(cid, base, metric))} ({base}) -> {fnum(v(cid, fy, metric))} ({fy}) = {y:+.1f}%.",
           bref(cid, fy, base), tid, [it_change(cid, metric, fy, base, math.copysign(r, y))], [lit])

    for tid, tpl in [("al_ci_a", "We brought down GHG emission intensity by {p} between {b} and {fy}."),
                     ("al_ci_b", "{co} has reduced its Scope 1 and 2 emission intensity by {p} compared with {b}.")]:
        change_case(tid, tpl, "ghg_intensity", [c for c in CIDS if chg(c, "ghg_intensity", "FY2025", "FY2020") <= -8])
    change_case("al_s2_red", "Scope 2 emissions came down by {p} from {b} levels as we shifted to cleaner grid power.",
                "scope2_tco2e", [c for c in CIDS if chg(c, "scope2_tco2e", "FY2025", "FY2020") <= -6])
    change_case("al_lt_red", "Our Lost Time Injury Frequency Rate improved by {p} over {b}.",
                "ltifr", [c for c in CIDS if chg(c, "ltifr", "FY2025", "FY2020") <= -8])
    cid = pick([(c,) for c in CIDS if chg(c, "energy_gj", "FY2025", "FY2020") >= 8
                and chg(c, "revenue_cr", "FY2025", "FY2020") >= 8])[0][0]
    ey, ry = chg(cid, "energy_gj", "FY2025", "FY2020"), chg(cid, "revenue_cr", "FY2025", "FY2020")
    er, ed = pct_claim(ey)
    rr, rd = pct_claim(ry)
    el, et = pctt(er, ed)
    rl, rt = pctt(rr, rd)
    mk("ALIGN", "none", "medium", cid, "energy_gj", "FY2025", "FY2020",
       f"Total energy consumption in FY2025 was {et} higher than in FY2020, against revenue growth of {rt}.",
       f"Energy {ey:+.1f}%, revenue {ry:+.1f}% FY2020->FY2025.", bref(cid, "FY2025", "FY2020"), "al_en_rev",
       [it_change(cid, "energy_gj", "FY2025", "FY2020", er), it_change(cid, "revenue_cr", "FY2025", "FY2020", rr)],
       [el, rl])
    cid = pick([(c,) for c in CIDS])[0][0]
    a, b = v(cid, "FY2021", "re_pct"), v(cid, "FY2025", "re_pct")
    mk("ALIGN", "none", "medium", cid, "re_pct", "FY2025", "FY2021",
       f"Our renewable electricity share rose from {a:g}% in FY2021 to {b:g}% in FY2025.",
       f"Filed re_pct {a}% (FY2021) and {b}% (FY2025).", bref(cid, "FY2025", "FY2021"), "al_re_rise",
       [it_value(cid, "FY2021", "re_pct", a), it_value(cid, "FY2025", "re_pct", b)], [f"{a:g}", f"{b:g}"])
    cid = pick([(c,) for c in CIDS if chg(c, "water_withdrawal_kl", "FY2025", "FY2024") >= 3])[0][0]
    y = chg(cid, "water_withdrawal_kl", "FY2025", "FY2024")
    r, dec = pct_claim(y)
    lit, p = pctt(r, dec)
    mk("ALIGN", "none", "medium", cid, "water_withdrawal_kl", "FY2025", "FY2024",
       f"Water withdrawal at {co(cid)} rose by {p} over the previous year, in line with higher production.",
       f"Withdrawal {v(cid, 'FY2024', 'water_withdrawal_kl'):,.0f} -> {v(cid, 'FY2025', 'water_withdrawal_kl'):,.0f} kL = {y:+.1f}%.",
       bref(cid, "FY2025", "FY2024"), "al_ww_yoy", [it_change(cid, "water_withdrawal_kl", "FY2025", "FY2024", r)], [lit])
    cid = pick([(c,) for c in CIDS if chg(c, "ghg_intensity", "FY2025", "FY2024") <= -3])[0][0]
    y = chg(cid, "ghg_intensity", "FY2025", "FY2024")
    r, dec = pct_claim(abs(y))
    lit, p = pctt(r, dec)
    mk("ALIGN", "none", "medium", cid, "ghg_intensity", "FY2025", "FY2024",
       f"GHG emission intensity improved by {p} year on year in FY2024-25.",
       f"Intensity {v(cid, 'FY2024', 'ghg_intensity')} -> {v(cid, 'FY2025', 'ghg_intensity')} = {y:+.1f}%.",
       bref(cid, "FY2025", "FY2024"), "al_ci_yoy", [it_change(cid, "ghg_intensity", "FY2025", "FY2024", -r)], [lit])

    # ---- A3 honest intensity claims while absolute rose (3) ----------------------------
    c3 = [(c,) for c in CIDS if chg(c, "ghg_intensity", "FY2025", "FY2020") <= -10 and chg(c, "scope1_tco2e", "FY2025", "FY2020") >= 10]
    for tid, tpl in [("al_ai_a", "While absolute Scope 1 emissions rose {a} between {b} and {fy}, emission intensity per Rs crore of turnover fell {i}."),
                     ("al_ai_b", "Our GHG intensity fell {i} from {b} to {fy}; absolute Scope 1 emissions, however, went up {a} on the back of higher output."),
                     ("al_ai_c", "Intensity improved {i} since {b}, although {co}'s absolute Scope 1 emissions increased by {a}.")]:
        cid = pick(c3)[0][0]
        iy, ay = chg(cid, "ghg_intensity", "FY2025", "FY2020"), chg(cid, "scope1_tco2e", "FY2025", "FY2020")
        ir, idc = pct_claim(abs(iy))
        ar, adc = pct_claim(ay)
        il, it_ = pctt(ir, idc)
        al, at = pctt(ar, adc)
        mk("ALIGN", "none", "hard", cid, "ghg_intensity", "FY2025", "FY2020",
           tpl.format(a=at, i=it_, b=fyt_plain("FY2020"), fy=fyt("FY2025"), co=co(cid)),
           f"Intensity {iy:+.1f}% but absolute Scope 1 {ay:+.1f}% (FY2020->FY2025): both statements are true.",
           bref(cid, "FY2025", "FY2020"), tid,
           [it_change(cid, "ghg_intensity", "FY2025", "FY2020", -ir), it_change(cid, "scope1_tco2e", "FY2025", "FY2020", ar)],
           [il, al])

    # ---- A4 assurance (4) ---------------------------------------------------------------
    a_pool = defaultdict(list)
    for c in CIDS:
        for fy in FYS[2:]:
            a_pool[BRSR[c][fy]["assurance_type"]].append((c, fy))
    for typ, tid, tpl in [
        ("limited", "al_as_lim", "Our BRSR Core disclosures for {fy} were subjected to limited assurance by an independent auditor."),
        ("limited", "al_as_lim2", "{co} obtained limited assurance on its BRSR Core indicators for {fy}."),
        ("reasonable", "al_as_rea", "In {fy}, our BRSR Core indicators received reasonable assurance from an external assurance provider."),
        ("none", "al_as_none", "The BRSR Core indicators reported by {co} for {fy} have not yet been externally assured."),
    ]:
        cid, fy = pick(a_pool[typ])[0]
        refs = bref(cid, fy) + ([f"audited_reports:{AUDIT[(cid, fy)]}"] if (cid, fy) in AUDIT else [])
        mk("ALIGN", "none", "medium", cid, "assurance_type", fy, None, tpl.format(fy=fyt(fy), co=co(cid)),
           f"Filing records assurance_type = {typ} for {fy}.", refs, tid, [it_cat(cid, fy, typ)], [])

    # ---- Period traps (5) -------------------------------------------------------------
    pen_planted = [e for e in PLANT if e["kind"] == "regulatory_penalty" and e["company_id"] not in DEMO_IDS]
    cand = []
    for e in pen_planted:
        for fy2 in FYS[1:]:
            if fy2 != e["fy"] and not REG[(e["company_id"], fy2)]:
                cand.append((e["company_id"], e["fy"], fy2, e))
    for tid, tpl in [("al_pt_pen_a", "No environmental penalties, fines or compensation orders were imposed on {co} during {fy}."),
                     ("al_pt_pen_b", "There was no regulatory penalty of any kind against our company in {fy}.")]:
        cid, fyx, fyy, e = pick(cand)[0]
        rows = REG[(cid, fyx)]
        mk("ALIGN", "none", "hard", cid, "regulatory_actions", fyy, None, tpl.format(co=co(cid), fy=fyt(fyy)),
           f"Period trap: the company has {len(rows)} action(s) in {fyx} (Rs {sum(r['penalty_inr'] for r in rows) / 1e7:.2f} cr) but none in {fyy}.",
           [f"regulatory_actions:{r['action_id']}" for r in rows] + [f"facilities:{f['facility_id']}" for f in FAC[cid][:3]],
           tid, [it_reg(cid, fyy, 0, False)], [])
    oc_planted = [e for e in PLANT if e["kind"] == "ocems" and e["company_id"] not in DEMO_IDS]
    cand = []
    for e in oc_planted:
        for fy2 in FYS[1:]:
            if fy2 != e["fy"] and not comp_ocems(e["company_id"], fy2):
                cand.append((e["company_id"], e["fy"], fy2, e))
    for tid, tpl in [("al_pt_oc_a", "Our online continuous emission monitoring systems recorded zero exceedances in {fy}."),
                     ("al_pt_oc_b", "All {co} plants stayed within prescribed stack and effluent limits throughout {fy}, with no OCEMS exceedance reported.")]:
        cid, fyx, fyy, e = pick(cand)[0]
        mk("ALIGN", "none", "hard", cid, "ocems_exceedances", fyy, None, tpl.format(co=co(cid), fy=fyt(fyy)),
           f"Period trap: {len(comp_ocems(cid, fyx))} exceedances occurred in {fyx}, but 0 in {fyy}.",
           [f"ocems_exceedances:{x}" for x in comp_ocems(cid, fyx)[:10]] + [f"facilities:{f['facility_id']}" for f in FAC[cid][:3]],
           tid, [it_ocems(cid, None, fyy, 0)], [])
    la_planted = [e for e in PLANT if e["kind"] == "land_alerts" and e["company_id"] not in DEMO_IDS]
    cand = []
    for e in la_planted:
        fid = e["details"]["facility_id"]
        for fy2 in FYS[1:]:
            if fy2 != e["fy"] and not alerts_near(fid, fy2) and not nearest_alerts(fid, fy2, 25):
                cand.append((e["company_id"], fid, e["fy"], fy2))
    cid, fid, fyx, fyy = pick(cand)[0]
    fn = FACD[fid]["name"]
    mk("ALIGN", "none", "hard", cid, "deforestation_ha", fyy, None,
       f"No forest loss was recorded within 5 km of our {fn} during {fyt(fyy)}.",
       f"Period trap: {len(alerts_near(fid, fyx))} alerts ({sum(a['area_ha'] for a in alerts_near(fid, fyx)):.1f} ha) in {fyx}, none in {fyy}.",
       [f"land_alerts:{a['alert_id']}" for a in alerts_near(fid, fyx)[:8]] + [f"facilities:{fid}"],
       "al_pt_geo", [it_alerts(fid, fyy, 0)], [])

    # ---- no penalty at all (3) ----------------------------------------------------------
    cand = [(c, fy) for c in CIDS for fy in FYS[1:] if not REG[(c, fy)]
            and COMP[c]["sector"] in ("Steel", "Cement", "Power", "Chemicals", "Mining", "Textiles")]
    for tid, tpl in [("al_np_a", "There were no environmental penalties, show-cause notices or closure directions against {co} in {fy}."),
                     ("al_np_b", "We did not receive any regulatory notice or penalty from CPCB, the NGT or any State Pollution Control Board during {fy}."),
                     ("al_np_c", "{co} had a clean regulatory record in {fy}, with no environmental action initiated against any of its sites.")]:
        cid, fy = pick(cand)[0]
        mk("ALIGN", "none", "medium", cid, "regulatory_actions", fy, None, tpl.format(co=co(cid), fy=fyt(fy)),
           f"No regulatory_actions rows for the company in {fy}.", [f"facilities:{f['facility_id']}" for f in FAC[cid][:3]],
           tid, [it_reg(cid, fy, 0, False)], [])

    # ---- zero exceedances true (4) --------------------------------------------------------
    cand = [(c, fy) for c in CIDS for fy in FYS[1:] if not comp_ocems(c, fy)
            and COMP[c]["sector"] in ("Steel", "Cement", "Power", "Chemicals", "Mining")]
    for tid, tpl in [("al_ze_a", "{co} recorded no OCEMS exceedances at any of its plants in {fy}."),
                     ("al_ze_b", "Stack emissions at all our units remained within the prescribed limits throughout {fy}."),
                     ("al_ze_c", "Zero exceedances of CPCB emission norms were reported by our continuous monitoring systems in {fy}."),
                     ("al_ze_d", "During {fy}, our online monitoring showed that every plant of ours operated within consent limits.")]:
        cid, fy = pick(cand)[0]
        mk("ALIGN", "none", "medium", cid, "ocems_exceedances", fy, None, tpl.format(co=co(cid), fy=fyt(fy)),
           f"0 OCEMS exceedance rows across {len(FAC[cid])} facilities in {fy}.",
           [f"facilities:{f['facility_id']}" for f in FAC[cid]], tid, [it_ocems(cid, None, fy, 0)], [])

    # ---- no forest loss true (4) ----------------------------------------------------------
    cand = []
    for f in FACD.values():
        cid = f["company_id"]
        if cid in DEMO_IDS or not f["forest_adjacent"]:
            continue
        for fy in FYS[1:]:
            if not alerts_near(f["facility_id"], fy) and not alerts_near(f["facility_id"], fy, 10.0):
                cand.append((cid, f["facility_id"], fy))
    for tid, tpl in [("al_fz_a", "Our {fn} recorded no forest loss within its 5 km buffer zone during {fy}."),
                     ("al_fz_b", "Satellite forest-loss alerts show no clearing within 5 km of {co}'s {fn} in {fy}."),
                     ("al_fz_c", "There was zero deforestation around our {fn} in {fy}."),
                     ("al_fz_d", "No tree cover loss was detected within 5 km of the {fn} during {fy}.")]:
        cid, fid, fy = pick(cand)[0]
        mk("ALIGN", "none", "hard", cid, "deforestation_ha", fy, None,
           tpl.format(fn=FACD[fid]["name"], co=co(cid), fy=fyt(fy)),
           f"Forest-adjacent facility with 0 alerts within 5 km (haversine) in {fy}.", [f"facilities:{fid}"],
           tid, [it_alerts(fid, fy, 0)], [])

    # ---- RECs honest (3) ---------------------------------------------------------------------
    cand = []
    for c in CIDS:
        rows = [r for r in RECS[c] if r["vintage_year"] == 2024]
        if rows and all(r["status"] == "retired" for r in rows):
            cand.append((c, rows))
    for tid, tpl, mode in [
        ("al_rc_a", "All renewable energy certificates of 2024 vintage procured by {co} have been retired in our name.", "all"),
        ("al_rc_b", "We retired {q} MWh of renewable energy certificates of 2024 vintage.", "vol"),
        ("al_rc_c", "Every REC we purchased for the 2024 vintage stands retired on the registry; none remains active.", "all"),
    ]:
        cid, rows = pick(cand)[0]
        tot = sum(r["mwh"] for r in rows)
        refs = [f"re_certificates:{r['cert_id']}" for r in rows]
        if mode == "all":
            mk("ALIGN", "none", "hard", cid, "rec_retirement", "FY2025", None, tpl.format(co=co(cid)),
               f"2024-vintage certificates: {tot:,.0f} MWh, all status=retired.", refs, tid,
               [it_rec(cid, 2024, "all_retired", True)], [])
        else:
            lit = f"{round(tot):,}"
            mk("ALIGN", "none", "hard", cid, "rec_retirement", "FY2025", None, tpl.format(q=lit),
               f"2024-vintage certificates retired: {tot:,.0f} MWh.", refs, tid,
               [it_rec(cid, 2024, "retired_mwh", float(round(tot)))], [lit])

    # ---- zero fatalities (2) -----------------------------------------------------------------
    cand = [(c, fy) for c in CIDS for fy in FYS[2:] if BRSR[c][fy]["fatalities"] == 0]
    for tid, tpl, lit in [("al_fz0_a", "We recorded zero work-related fatalities across our operations in {fy}.", "zero"),
                          ("al_fz0_b", "There were no fatalities at any {co} site in {fy}.", "no fatalities")]:
        cid, fy = pick(cand)[0]
        mk("ALIGN", "none", "easy", cid, "fatalities", fy, None, tpl.format(fy=fyt(fy), co=co(cid)),
           f"Filed fatalities = 0 in {fy}.", bref(cid, fy), tid, [it_value(cid, fy, "fatalities", 0.0)], [lit])

    # ---- penalty amount (1) and exceedance count (1) ----------------------------------------
    cand = [(e["company_id"], e) for e in pen_planted if len(REG[(e["company_id"], e["fy"])]) == 1
            and REG[(e["company_id"], e["fy"])][0]["penalty_inr"] > 0]
    cid, e = pick(cand)[0]
    row = REG[(cid, e["fy"])][0]
    m_ = money(row["penalty_inr"])
    mk("ALIGN", "none", "medium", cid, "regulatory_actions", e["fy"], None,
       f"In {fyt(e['fy'])}, {row['authority']} directed us to pay {m_['text']} as environmental compensation, which we have disclosed in full.",
       f"Single action {row['action_id']} ({row['order_type']}), penalty Rs {row['penalty_inr']:,.0f} on {row['date']}.",
       [f"regulatory_actions:{row['action_id']}"], "al_pen_amt",
       [it_pen(cid, e["fy"], m_["claimed"] * m_["mult"]), it_reg(cid, e["fy"], 1, False)], [m_["literal"]])
    cid, e = pick([(x["company_id"], x) for x in oc_planted])[0]
    fid = e["details"]["facility_id"]
    n = len(OCE[(fid, e["fy"])])
    mk("ALIGN", "none", "medium", cid, "ocems_exceedances", e["fy"], None,
       f"Our {FACD[fid]['name']} logged {n} emission-limit exceedances on the CPCB online monitoring portal in {fyt(e['fy'])}, and corrective action has been initiated.",
       f"{n} OCEMS exceedance rows at {fid} in {e['fy']}.", [f"ocems_exceedances:{x}" for x in OCE[(fid, e['fy'])]],
       "al_oc_cnt", [it_ocems(cid, fid, e["fy"], n)], [str(n)])


# ======================================================================================
# CONTRADICT (70)
# ======================================================================================
def build_contradict():
    # ---- inflated_reduction (8) -------------------------------------------------------
    def infl(tid, tpl, metric, cands, claims, fy="FY2025", base="FY2020"):
        cid = pick([(c,) for c in cands])[0][0]
        act = chg(cid, metric, fy, base)
        x = rng.choice(claims)
        lit, p = pctt(x, 0)
        mk("CONTRADICT", "inflated_reduction", "medium", cid, metric, fy, base,
           tpl.format(p=p, b=fyt_plain(base), fy=fyt(fy), co=co(cid)),
           f"{metric} moved {act:+.1f}% ({fnum(v(cid, base, metric))} -> {fnum(v(cid, fy, metric))}); the claim is a {x}% reduction.",
           bref(cid, fy, base), tid, [it_change(cid, metric, fy, base, -float(x), "mismatch")], [lit])

    def up(m):
        return [c for c in CIDS if chg(c, m, "FY2025", "FY2020") >= 8]

    infl("ci_ir_s1_a", "We have reduced our absolute Scope 1 emissions by {p} against our {b} baseline.", "scope1_tco2e", up("scope1_tco2e"), [15, 20, 25, 30, 40])
    infl("ci_ir_s1_b", "Scope 1 emissions are down {p} since {b}.", "scope1_tco2e", up("scope1_tco2e"), [12, 18, 22, 35])
    infl("ci_ir_s1_c", "{co} cut its direct emissions by {p} between {b} and {fy}.", "scope1_tco2e", up("scope1_tco2e"), [10, 15, 25, 45])
    infl("ci_ir_ww_a", "We cut freshwater withdrawal by {p} compared with {b}.", "water_withdrawal_kl", up("water_withdrawal_kl"), [15, 20, 25, 30])
    infl("ci_ir_ww_b", "Water withdrawal at {co} has come down {p} since {b}.", "water_withdrawal_kl", up("water_withdrawal_kl"), [10, 18, 28])
    infl("ci_ir_en", "Our total energy consumption in {fy} is {p} lower than in {b}.", "energy_gj", up("energy_gj"), [8, 12, 20])
    cands = [c for c in CIDS if -22 <= chg(c, "ghg_intensity", "FY2025", "FY2020") <= -5]
    cid = pick([(c,) for c in cands])[0][0]
    act = chg(cid, "ghg_intensity", "FY2025", "FY2020")
    x = nice(abs(act) * rng.choice([2.0, 2.5, 3.0]))
    lit, p = pctt(x, 0)
    mk("CONTRADICT", "inflated_reduction", "medium", cid, "ghg_intensity", "FY2025", "FY2020",
       f"We have reduced GHG emission intensity by {p} between FY2020 and FY2025.",
       f"Filed intensity {v(cid, 'FY2020', 'ghg_intensity')} -> {v(cid, 'FY2025', 'ghg_intensity')} = {act:+.1f}%, not -{x}%.",
       bref(cid, "FY2025", "FY2020"), "ci_ir_gi", [it_change(cid, "ghg_intensity", "FY2025", "FY2020", -float(x), "mismatch")], [lit])
    cands = [c for c in CIDS if -14 <= chg(c, "scope2_tco2e", "FY2025", "FY2020") <= -5]
    cid = pick([(c,) for c in cands])[0][0]
    act = chg(cid, "scope2_tco2e", "FY2025", "FY2020")
    x = nice(abs(act) * rng.choice([2.5, 3.0, 4.0]))
    lit, p = pctt(x, 0)
    mk("CONTRADICT", "inflated_reduction", "medium", cid, "scope2_tco2e", "FY2025", "FY2020",
       f"Scope 2 emissions have fallen by {p} since FY2020 on the back of our green power purchases.",
       f"Filed Scope 2 {v(cid, 'FY2020', 'scope2_tco2e'):,.0f} -> {v(cid, 'FY2025', 'scope2_tco2e'):,.0f} tCO2e = {act:+.1f}%, not -{x}%.",
       bref(cid, "FY2025", "FY2020"), "ci_ir_s2", [it_change(cid, "scope2_tco2e", "FY2025", "FY2020", -float(x), "mismatch")], [lit])

    # ---- cherry_picked_year (5) ---------------------------------------------------------------
    best = {}
    for metric in ("scope2_tco2e", "ltifr"):
        for c in CIDS:
            for y in range(2021, 2025):
                fyp = f"FY{y}"
                rp = -chg(c, metric, "FY2025", fyp)
                r0 = -chg(c, metric, "FY2025", "FY2020")
                if rp >= 7 and (rp - r0) >= max(4, 0.25 * abs(rp)) and round(rp) != round(r0):
                    if (c, metric) not in best or rp > best[(c, metric)][3]:
                        best[(c, metric)] = (c, metric, fyp, rp, r0)
    pool = sorted(best.values())
    s2 = [t for t in pool if t[1] == "scope2_tco2e"]
    lt = [t for t in pool if t[1] == "ltifr"]
    chosen = [pick(s2) for _ in range(4)] + [pick(lt)]
    chosen = [x[0] for x in chosen]
    tpls = [("ci_cp_s2_a", "Scope 2 emissions are down {p} since {b}."),
            ("ci_cp_s2_b", "{co} has lowered its Scope 2 emissions by {p} over the period {b} to {fy}."),
            ("ci_cp_s2_c", "Since {b}, we have steadily reduced Scope 2 emissions, now {p} lower."),
            ("ci_cp_s2_d", "Our Scope 2 emissions fell by {p} against the {b} baseline, driven by renewable power sourcing."),
            ("ci_cp_lt", "Our Lost Time Injury Frequency Rate has improved by {p} since {b}.")]
    s2_i = 0
    for (c, metric, fyp, rp, r0) in chosen:
        if metric == "ltifr":
            tid, tpl = tpls[4]
        else:
            tid, tpl = tpls[s2_i]
            s2_i += 1
        r, rdec = pct_claim(rp)
        lit, p = pctt(r, rdec)
        mk("CONTRADICT", "cherry_picked_year", "hard", c, metric, "FY2025", "FY2020",
           tpl.format(p=p, b=fyt_plain("FY2020"), fy=fyt("FY2025"), co=co(c)),
           f"The {r:g}% fall only holds against {fyp} ({fnum(v(c, fyp, metric))} -> {fnum(v(c, 'FY2025', metric))}); against FY2020 ({fnum(v(c, 'FY2020', metric))}) it is {chg(c, metric, 'FY2025', 'FY2020'):+.1f}%.",
           bref(c, "FY2025", "FY2020", fyp), tid,
           [it_change(c, metric, "FY2025", "FY2020", -float(r), "mismatch"),
            it_change(c, metric, "FY2025", fyp, -float(r), "match")], [lit])

    # ---- baseline_shift (5) ------------------------------------------------------------------
    cfg = [("scope1_tco2e", "tco2e", "Scope 1 emissions fell from {b} in {bfy} to {c} in {fy}, a reduction of {p}."),
           ("scope1_tco2e", "tco2e", "Our Scope 1 footprint has shrunk by {p}, from a {bfy} baseline of {b} to {c} in {fy}."),
           ("scope1_tco2e", "tco2e", "Starting from {b} in {bfy}, {co} brought Scope 1 emissions down to {c} by {fy}, a {p} cut."),
           ("energy_gj", "gj", "Total energy consumption declined from {b} in {bfy} to {c} in {fy}, a drop of {p}."),
           ("water_withdrawal_kl", "kl", "Water withdrawal fell {p}, from {b} in {bfy} to {c} in {fy}.")]
    for i, (metric, kind, tpl) in enumerate(cfg):
        floor = 3e5 if metric == "scope1_tco2e" else 2e6
        cid = pick([(c,) for c in CIDS if v(c, "FY2020", metric) >= floor and chg(c, metric, "FY2025", "FY2020") >= 0])[0][0]
        base_true, cur_true = v(cid, "FY2020", metric), v(cid, "FY2025", metric)
        f = rng.choice([1.2, 1.3, 1.5])
        style = rng.choice(["raw", "lakh", "indian"])
        qb = qty(cur_true * f, kind, style)
        qc = qty(cur_true, kind, style)
        assert qb["mult"] == qc["mult"]
        bval, cval = qb["claimed"] * qb["mult"], qc["claimed"] * qc["mult"]
        r = round((bval - cval) / bval * 100)
        lit, p = pctt(r, 0)
        mk("CONTRADICT", "baseline_shift", "hard", cid, metric, "FY2025", "FY2020",
           tpl.format(b=qb["text"], c=qc["text"], bfy=fyt_plain("FY2020"), fy=fyt("FY2025"), p=p, co=co(cid)),
           f"Filed FY2020 {metric} = {base_true:,.0f}, not {bval:,.0f} as claimed (baseline overstated by {bval / base_true - 1:.0%}); FY2025 = {cur_true:,.0f} matches. True change {chg(cid, metric, 'FY2025', 'FY2020'):+.1f}%.",
           bref(cid, "FY2025", "FY2020"), f"ci_bs_{i}",
           [it_value(cid, "FY2020", metric, qb["claimed"], qb["mult"], "mismatch"),
            it_value(cid, "FY2025", metric, qc["claimed"], qc["mult"], "match"),
            it_change(cid, metric, "FY2025", "FY2020", -float(r), "mismatch")],
           [qb["literal"], qc["literal"]])

    # ---- scope_swap (5) ---------------------------------------------------------------------
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if min(v(c, fy, "scope1_tco2e"), v(c, fy, "scope2_tco2e")) >= 1e5
            and abs(v(c, fy, "scope1_tco2e") - v(c, fy, "scope2_tco2e")) / max(v(c, fy, "scope1_tco2e"), v(c, fy, "scope2_tco2e")) >= 0.3]
    for tid, claimed_m, src_m, tpl in [
            ("ci_ss_a", "scope1_tco2e", "scope2_tco2e", "Our Scope 1 emissions for {fy} were {q}."),
            ("ci_ss_b", "scope1_tco2e", "scope2_tco2e", "{co} reported direct Scope 1 emissions of {q} in {fy}."),
            ("ci_ss_c", "scope1_tco2e", "scope2_tco2e", "Scope 1 emissions at {co} stood at {q} during {fy}."),
            ("ci_ss_d", "scope2_tco2e", "scope1_tco2e", "Scope 2 emissions from our purchased electricity were {q} in {fy}."),
            ("ci_ss_e", "scope2_tco2e", "scope1_tco2e", "In {fy}, our indirect (Scope 2) emissions came to {q}.")]:
        cid, fy = pick(pool)[0]
        q = qty(v(cid, fy, src_m), "tco2e", rng.choice(["lakh", "raw", "indian"]))
        mk("CONTRADICT", "scope_swap", "hard", cid, claimed_m, fy, None, tpl.format(q=q["text"], co=co(cid), fy=fyt(fy)),
           f"Claimed figure equals filed {src_m} ({v(cid, fy, src_m):,.0f}); filed {claimed_m} for {fy} is {v(cid, fy, claimed_m):,.0f} tCO2e.",
           bref(cid, fy), tid,
           [it_value(cid, fy, claimed_m, q["claimed"], q["mult"], "mismatch"),
            it_value(cid, fy, src_m, q["claimed"], q["mult"], "match")], [q["literal"]])

    # ---- absolute_vs_intensity (5) ---------------------------------------------------------
    pool = [(c,) for c in CIDS if chg(c, "ghg_intensity", "FY2025", "FY2020") <= -12 and chg(c, "scope1_tco2e", "FY2025", "FY2020") >= 8]
    for tid, tpl in [("ci_av_a", "Our absolute Scope 1 emissions have fallen by {p} since {b}."),
                     ("ci_av_b", "Total direct emissions at {co} are {p} lower than in {b}."),
                     ("ci_av_c", "We have cut absolute Scope 1 emissions by {p} between {b} and {fy}."),
                     ("ci_av_d", "{co} has delivered a {p} reduction in absolute emissions (Scope 1) over {b} to {fy}."),
                     ("ci_av_e", "In absolute terms, our Scope 1 GHG emissions declined {p} against the {b} base year.")]:
        cid = pick(pool)[0][0]
        iy, ay = chg(cid, "ghg_intensity", "FY2025", "FY2020"), chg(cid, "scope1_tco2e", "FY2025", "FY2020")
        x, xdec = pct_claim(abs(iy))
        lit, p = pctt(x, xdec)
        mk("CONTRADICT", "absolute_vs_intensity", "hard", cid, "scope1_tco2e", "FY2025", "FY2020",
           tpl.format(p=p, b=fyt_plain("FY2020"), fy=fyt("FY2025"), co=co(cid)),
           f"The {x:g}% fall is in emission INTENSITY ({iy:+.1f}%); absolute Scope 1 actually rose {ay:+.1f}% ({v(cid, 'FY2020', 'scope1_tco2e'):,.0f} -> {v(cid, 'FY2025', 'scope1_tco2e'):,.0f} tCO2e).",
           bref(cid, "FY2025", "FY2020"), tid,
           [it_change(cid, "scope1_tco2e", "FY2025", "FY2020", -float(x), "mismatch"),
            it_change(cid, "ghg_intensity", "FY2025", "FY2020", -float(x), "match")], [lit])

    # ---- unit_error (5) ----------------------------------------------------------------------
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if v(c, fy, "scope1_tco2e") >= 1.5e6]
    cid, fy = pick(pool)[0]
    val = v(cid, fy, "scope1_tco2e")
    lit = sig3s(val / 1e7)
    mk("CONTRADICT", "unit_error", "hard", cid, "scope1_tco2e", fy, None,
       f"Our Scope 1 emissions in {fyt(fy)} were {lit} lakh tCO2e.",
       f"Filed Scope 1 = {val:,.0f} tCO2e = {val / 1e7:.2f} crore, but the claim reads {lit} lakh (100x too low).",
       bref(cid, fy), "ci_ue_lakh_crore_a", [it_value(cid, fy, "scope1_tco2e", float(lit), 1e5, "mismatch")], [lit])
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if 2e5 <= v(c, fy, "scope1_tco2e") <= 9e5]
    cid, fy = pick(pool)[0]
    val = v(cid, fy, "scope1_tco2e")
    lit = sig3s(val / 1e5)
    mk("CONTRADICT", "unit_error", "hard", cid, "scope1_tco2e", fy, None,
       f"{co(cid)} reported Scope 1 emissions of {lit} crore tCO2e for {fyt(fy)}.",
       f"Filed Scope 1 = {val:,.0f} tCO2e = {lit} lakh; the claim says crore (100x too high).",
       bref(cid, fy), "ci_ue_lakh_crore_b", [it_value(cid, fy, "scope1_tco2e", float(lit), 1e7, "mismatch")], [lit])
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if v(c, fy, "water_withdrawal_kl") >= 2e6]
    cid, fy = pick(pool)[0]
    val = v(cid, fy, "water_withdrawal_kl")
    lit = f"{round(val):,}"
    mk("CONTRADICT", "unit_error", "hard", cid, "water_withdrawal_kl", fy, None,
       f"Total water withdrawal during {fyt(fy)} was {lit} ML.",
       f"Filed withdrawal = {val:,.0f} kL (= {val / 1e3:,.0f} ML); the claim attaches ML to the kL figure (1000x too high).",
       bref(cid, fy), "ci_ue_kl_ml_a", [it_value(cid, fy, "water_withdrawal_kl", float(round(val)), 1e3, "mismatch")], [lit])
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if v(c, fy, "water_withdrawal_kl") >= 1e6]
    cid, fy = pick(pool)[0]
    val = v(cid, fy, "water_withdrawal_kl")
    lit = f"{round(val / 1e3):,}"
    mk("CONTRADICT", "unit_error", "hard", cid, "water_withdrawal_kl", fy, None,
       f"{co(cid)} withdrew {lit} kL of water in {fyt(fy)}, a significant saving.",
       f"Filed withdrawal = {val:,.0f} kL = {val / 1e3:,.0f} ML; the claim writes the ML figure as kL (1000x too low).",
       bref(cid, fy), "ci_ue_kl_ml_b", [it_value(cid, fy, "water_withdrawal_kl", float(round(val / 1e3)), 1.0, "mismatch")], [lit])
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if v(c, fy, "energy_gj") >= 2e6]
    cid, fy = pick(pool)[0]
    val = v(cid, fy, "energy_gj")
    lit = f"{round(val):,}"
    mk("CONTRADICT", "unit_error", "hard", cid, "energy_gj", fy, None,
       f"We consumed {lit} TJ of energy across our operations in {fyt(fy)}.",
       f"Filed energy = {val:,.0f} GJ (= {val / 1e3:,.0f} TJ); the claim attaches TJ to the GJ figure (1000x too high).",
       bref(cid, fy), "ci_ue_gj_tj", [it_value(cid, fy, "energy_gj", float(round(val)), 1e3, "mismatch")], [lit])

    # ---- future_target_as_achievement (5) ----------------------------------------------------
    pool = [(c,) for c in CIDS if v(c, "FY2025", "re_pct") <= 40]
    for tid, tpl, claim in [
        ("ci_ft_re100", "We now source {p} of our electricity from renewable sources.", 100.0),
        ("ci_ft_re75", "{co} has transitioned to {p} renewable power across its operations.", 75.0),
        ("ci_ft_re50", "We have already achieved our 2030 goal of meeting {p} of our electricity needs from renewables.", 50.0),
    ]:
        cid = pick(pool)[0][0]
        lit, p = pctt(claim, 0)
        mk("CONTRADICT", "future_target_as_achievement", "easy", cid, "re_pct", "FY2025", None,
           tpl.format(co=co(cid), p=p),
           f"Filed renewable electricity share in FY2025 is {v(cid, 'FY2025', 're_pct')}%, so this is still a target, not an achievement.",
           bref(cid, "FY2025"), tid, [it_value(cid, "FY2025", "re_pct", claim, 1.0, "mismatch")], [lit])
    cid = pick([(c,) for c in CIDS])[0][0]
    mk("CONTRADICT", "future_target_as_achievement", "medium", cid, "scope1_tco2e", "FY2025", "FY2020",
       "We have already achieved our goal of halving Scope 1 emissions against the FY2020 baseline.",
       f"Filed Scope 1 {v(cid, 'FY2020', 'scope1_tco2e'):,.0f} -> {v(cid, 'FY2025', 'scope1_tco2e'):,.0f} tCO2e = {chg(cid, 'scope1_tco2e', 'FY2025', 'FY2020'):+.1f}%.",
       bref(cid, "FY2025", "FY2020"), "ci_ft_half", [it_change(cid, "scope1_tco2e", "FY2025", "FY2020", -50.0, "mismatch")], ["halving"])
    cid = pick([(c,) for c in CIDS])[0][0]
    mk("CONTRADICT", "future_target_as_achievement", "medium", cid, "scope1_tco2e", "FY2025", None,
       f"{co(cid)} is now net zero for direct (Scope 1) emissions.",
       f"Filed Scope 1 in FY2025 is {v(cid, 'FY2025', 'scope1_tco2e'):,.0f} tCO2e, not zero.",
       bref(cid, "FY2025"), "ci_ft_netzero", [it_value(cid, "FY2025", "scope1_tco2e", 0.0, 1.0, "mismatch")], ["net zero"])

    # ---- unretired_certificates (6) --------------------------------------------------------
    rec_pl = sorted([e for e in PLANT if e["kind"] == "rec_unretired" and e["company_id"] not in DEMO_IDS
                     and e["details"]["active_mwh"] >= 3 * e["details"]["retired_mwh"]], key=lambda e: e["company_id"])
    for tid, tpl, mode in [
        ("ci_uc_all_a", "All renewable energy certificates counted towards our renewable energy claims have been retired in our name.", "all"),
        ("ci_uc_all_b", "Every REC {co} bought for the 2024 vintage has been retired on the registry.", "all"),
        ("ci_uc_vol_a", "We retired {q} MWh of renewable energy certificates of 2024 vintage.", "vol"),
        ("ci_uc_vol_b", "{co} has retired a total of {q} MWh of 2024-vintage RECs to back its green power claims.", "vol"),
        ("ci_uc_re_a", "Backed by certificates, {p} of the electricity we consumed in FY2024-25 was renewable.", "re"),
        ("ci_uc_re_b", "{co} met {p} of its power needs from renewable sources in FY2025, supported by REC purchases.", "re"),
    ]:
        pl = [x for x in rec_pl if v(x["company_id"], "FY2025", "re_pct") <= 55] if mode == "re" else rec_pl
        e = pick([(x["company_id"], x) for x in pl])[0][1]
        cid = e["company_id"]
        d = e["details"]
        refs = [f"re_certificates:{r}" for r in e["refs"]] + bref(cid, "FY2025")
        if mode == "all":
            mk("CONTRADICT", "unretired_certificates", "hard", cid, "rec_retirement", "FY2025", None,
               tpl.format(co=co(cid)),
               f"2024-vintage RECs: only {d['retired_mwh']:,.0f} MWh retired vs {d['active_mwh']:,.0f} MWh still active.",
               refs, tid, [it_rec(cid, 2024, "all_retired", True, "mismatch")], [])
        elif mode == "vol":
            tot = d["retired_mwh"] + d["active_mwh"]
            lit = f"{round(tot):,}"
            mk("CONTRADICT", "unretired_certificates", "hard", cid, "rec_retirement", "FY2025", None,
               tpl.format(co=co(cid), q=lit),
               f"Only {d['retired_mwh']:,.0f} MWh of 2024-vintage RECs are retired; {d['active_mwh']:,.0f} MWh are still active (the claim counts them all).",
               refs, tid, [it_rec(cid, 2024, "retired_mwh", float(round(tot)), "mismatch")], [lit])
        else:
            act = v(cid, "FY2025", "re_pct")
            x = min(100, max(nice(act * 2.2), 30))
            assert x >= act * 1.3, (act, x)
            lit, p = pctt(x, 0)
            mk("CONTRADICT", "unretired_certificates", "hard", cid, "re_pct", "FY2025", None,
               tpl.format(co=co(cid), p=p),
               f"Filed renewable share is {act}%; the claim leans on {d['active_mwh']:,.0f} MWh of RECs that are still active (only {d['retired_mwh']:,.0f} MWh retired).",
               refs, tid, [it_value(cid, "FY2025", "re_pct", float(x), 1.0, "mismatch"),
                           it_rec(cid, 2024, "all_retired", True, "mismatch")], [lit])

    # ---- geo_contradiction (6) -----------------------------------------------------------------
    geo_pool, seen = [], set()
    for e in PLANT:
        if e["kind"] == "land_alerts" and e["company_id"] not in DEMO_IDS:
            geo_pool.append((e["company_id"], e["details"]["facility_id"], e["fy"]))
            seen.add((e["details"]["facility_id"], e["fy"]))
    for f in FACD.values():
        if f["company_id"] in DEMO_IDS or not f["forest_adjacent"]:
            continue
        for fy in FYS[1:]:
            if (f["facility_id"], fy) not in seen and len(alerts_near(f["facility_id"], fy)) >= 3:
                geo_pool.append((f["company_id"], f["facility_id"], fy))
    geo_pool = [g for g in geo_pool if len(alerts_near(g[1], g[2])) == len(nearest_alerts(g[1], g[2]))
                and len(alerts_near(g[1], g[2])) >= 3]
    for tid, tpl, mode in [
            ("ci_geo_a", "Our {fn} operations caused zero deforestation during {fy}.", "zero"),
            ("ci_geo_b", "No forest loss was recorded within 5 km of {co}'s {fn} in {fy}.", "zero"),
            ("ci_geo_c", "{co} maintained a strict no-deforestation policy at the {fn}, and none occurred in {fy}.", "zero"),
            ("ci_geo_d", "Forest cover around our {fn} remained fully intact through {fy}.", "zero"),
            ("ci_geo_e", "Tree cover loss within 5 km of our {fn} was limited to just {h} hectares in {fy}.", "ha"),
            ("ci_geo_f", "Only {h} hectares of forest were affected near the {fn} in {fy}, and these were fully compensated.", "ha")]:
        cid, fid, fy = pick(geo_pool)[0]
        al = alerts_near(fid, fy)
        ha = sum(a["area_ha"] for a in al)
        refs = [f"land_alerts:{a['alert_id']}" for a in al[:15]] + [f"facilities:{fid}"]
        fn = FACD[fid]["name"]
        if mode == "zero":
            mk("CONTRADICT", "geo_contradiction", "hard", cid, "deforestation_ha", fy, None,
               tpl.format(fn=fn, co=co(cid), fy=fyt(fy)),
               f"{len(al)} forest-loss alerts totalling {ha:.1f} ha within 5 km of {fn} in {fy}.", refs, tid,
               [it_alerts(fid, fy, 0, "count", "mismatch")], [])
        else:
            h = round(max(0.5, ha * rng.choice([0.08, 0.12, 0.2])), 1)
            lit = f"{h:g}"
            mk("CONTRADICT", "geo_contradiction", "hard", cid, "deforestation_ha", fy, None,
               tpl.format(fn=fn, co=co(cid), fy=fyt(fy), h=lit),
               f"{len(al)} forest-loss alerts totalling {ha:.1f} ha within 5 km of {fn} in {fy}, not {lit} ha.", refs, tid,
               [it_alerts(fid, fy, h, "ha", "mismatch")], [lit])

    # ---- hidden_regulatory_penalty (10) -----------------------------------------------------
    pen_pl = sorted([e for e in PLANT if e["kind"] == "regulatory_penalty" and e["company_id"] not in DEMO_IDS],
                    key=lambda e: e["company_id"])
    for tid, tpl in [("ci_hp_a", "There were no environmental violations or penalties at any of our sites during {fy}."),
                     ("ci_hp_b", "{co} was not subject to any monetary penalty or environmental compensation order in {fy}."),
                     ("ci_hp_c", "We had zero fines or penalties from regulators in {fy}, reflecting our compliance culture.")]:
        e = pick([(x["company_id"], x) for x in pen_pl])[0][1]
        cid, fy = e["company_id"], e["fy"]
        rows = [r for r in REG[(cid, fy)] if r["penalty_inr"] > 0]
        tot = sum(r["penalty_inr"] for r in rows)
        mk("CONTRADICT", "hidden_regulatory_penalty", "hard", cid, "regulatory_actions", fy, None,
           tpl.format(co=co(cid), fy=fyt(fy)),
           f"{len(rows)} penalty action(s) in {fy} totalling Rs {tot:,.0f} ({', '.join(r['authority'] + ' ' + r['date'] for r in rows)}).",
           [f"regulatory_actions:{r['action_id']}" for r in rows], tid, [it_reg(cid, fy, 0, True, "mismatch")], [])
    big_pen = [(x["company_id"], x) for x in pen_pl if sum(r["penalty_inr"] for r in REG[(x["company_id"], x["fy"])]) >= 2e6]
    for tid, tpl in [("ci_hp_d", "{co} paid a modest penalty of {q} in {fy}, a one-off matter now closed."),
                     ("ci_hp_e", "Environmental compensation of just {q} was levied on us in {fy}.")]:
        e = pick(big_pen)[0][1]
        cid, fy = e["company_id"], e["fy"]
        rows = [r for r in REG[(cid, fy)] if r["penalty_inr"] > 0]
        tot = sum(r["penalty_inr"] for r in rows)
        m_ = money(tot * rng.choice([0.2, 0.3, 0.4]))
        mk("CONTRADICT", "hidden_regulatory_penalty", "hard", cid, "regulatory_actions", fy, None,
           tpl.format(co=co(cid), fy=fyt(fy), q=m_["text"]),
           f"Penalties in {fy} total Rs {tot:,.0f} ({tot / 1e7:.2f} crore), far above the {m_['text']} claimed.",
           [f"regulatory_actions:{r['action_id']}" for r in rows], tid,
           [it_pen(cid, fy, m_["claimed"] * m_["mult"], "mismatch")], [m_["literal"]])
    oc_pl = sorted([e for e in PLANT if e["kind"] == "ocems" and e["company_id"] not in DEMO_IDS], key=lambda e: e["company_id"])
    for tid, tpl, mode in [
        ("ci_hp_oc_a", "Our continuous emission monitoring systems recorded zero exceedances in {fy}.", "zero"),
        ("ci_hp_oc_b", "Stack emissions at all our plants remained within prescribed limits throughout {fy}.", "zero"),
        ("ci_hp_oc_c", "{co} reported only {n} emission-limit exceedances across its plants in {fy}, all minor.", "low"),
        ("ci_hp_oc_d", "The {fn} operated within its consent emission limits for the whole of {fy}.", "zero_fac"),
        ("ci_hp_oc_e", "No OCEMS exceedance was flagged at any {co} facility during {fy}.", "zero"),
    ]:
        e = pick([(x["company_id"], x) for x in oc_pl])[0][1]
        cid, fy, fid = e["company_id"], e["fy"], e["details"]["facility_id"]
        allr = comp_ocems(cid, fy)
        facr = OCE[(fid, fy)]
        refs = [f"ocems_exceedances:{x}" for x in (facr if mode == "zero_fac" else allr)[:40]]
        if mode == "low":
            n = max(2, len(allr) // 10)
            mk("CONTRADICT", "hidden_regulatory_penalty", "hard", cid, "ocems_exceedances", fy, None,
               tpl.format(co=co(cid), n=n, fy=fyt(fy)), f"{len(allr)} exceedances recorded in {fy}, not {n}.", refs, tid,
               [it_ocems(cid, None, fy, n, "mismatch")], [str(n)])
        elif mode == "zero_fac":
            mk("CONTRADICT", "hidden_regulatory_penalty", "hard", cid, "ocems_exceedances", fy, None,
               tpl.format(fn=FACD[fid]["name"], fy=fyt(fy)), f"{len(facr)} exceedances at {fid} in {fy}.", refs, tid,
               [it_ocems(cid, fid, fy, 0, "mismatch")], [])
        else:
            mk("CONTRADICT", "hidden_regulatory_penalty", "hard", cid, "ocems_exceedances", fy, None,
               tpl.format(co=co(cid), fy=fyt(fy)),
               f"{len(allr)} OCEMS exceedances in {fy} ({', '.join(e['details']['parameters'])}).",
               refs, tid, [it_ocems(cid, None, fy, 0, "mismatch")], [])

    # ---- overstated_safety (5) ----------------------------------------------------------------
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if v(c, fy, "ltifr") >= 0.3]
    for tid, tpl, f in [("ci_os_lt_a", "Our Lost Time Injury Frequency Rate improved to {x} in {fy}.", 0.35),
                        ("ci_os_lt_b", "{co} achieved an LTIFR of {x} per million person-hours in {fy}, among the best in its sector.", 0.5)]:
        cid, fy = pick(pool)[0]
        x = round(v(cid, fy, "ltifr") * f, 2)
        mk("CONTRADICT", "overstated_safety", "easy", cid, "ltifr", fy, None, tpl.format(x=f"{x:.2f}", fy=fyt(fy), co=co(cid)),
           f"Filed LTIFR for {fy} is {v(cid, fy, 'ltifr')}, not {x:.2f}.", bref(cid, fy), tid,
           [it_value(cid, fy, "ltifr", x, 1.0, "mismatch")], [f"{x:.2f}"])
    pool = [(c, fy) for c in CIDS for fy in FYS[3:] if BRSR[c][fy]["fatalities"] >= 1]
    for tid, tpl in [("ci_os_fa_a", "We recorded zero work-related fatalities across our operations in {fy}."),
                     ("ci_os_fa_b", "{co} maintained an unblemished safety record with no fatalities in {fy}.")]:
        cid, fy = pick(pool)[0]
        mk("CONTRADICT", "overstated_safety", "easy", cid, "fatalities", fy, None, tpl.format(fy=fyt(fy), co=co(cid)),
           f"Filed fatalities for {fy}: {BRSR[cid][fy]['fatalities']}.", bref(cid, fy), tid,
           [it_value(cid, fy, "fatalities", 0.0, 1.0, "mismatch")], [])
    cands = [c for c in CIDS if -30 <= chg(c, "ltifr", "FY2025", "FY2020") <= -5]
    cid = pick([(c,) for c in cands])[0][0]
    act = chg(cid, "ltifr", "FY2025", "FY2020")
    x = nice(abs(act) * 3)
    lit, p = pctt(x, 0)
    mk("CONTRADICT", "overstated_safety", "medium", cid, "ltifr", "FY2025", "FY2020",
       f"Our LTIFR has come down by {p} since FY2020.",
       f"LTIFR {v(cid, 'FY2020', 'ltifr')} -> {v(cid, 'FY2025', 'ltifr')} = {act:+.1f}%, not -{x}%.", bref(cid, "FY2025", "FY2020"),
       "ci_os_lt_red", [it_change(cid, "ltifr", "FY2025", "FY2020", -float(x), "mismatch")], [lit])

    # ---- overstated_assurance (5) -------------------------------------------------------------
    a_pool = defaultdict(list)
    for c in CIDS:
        for fy in FYS[2:]:
            a_pool[BRSR[c][fy]["assurance_type"]].append((c, fy))
    for typ, claim, tid, tpl in [
        ("limited", "reasonable", "ci_oa_a", "Our BRSR Core disclosures for {fy} received reasonable assurance from an independent provider."),
        ("limited", "reasonable", "ci_oa_b", "{co}'s BRSR Core indicators for {fy} were reasonably assured by an external auditor."),
        ("none", "reasonable", "ci_oa_c", "For {fy}, our sustainability disclosures carry reasonable assurance, the highest level available."),
        ("none", "assured", "ci_oa_d", "All BRSR Core indicators reported by {co} for {fy} have been independently assured."),
        ("none", "limited", "ci_oa_e", "Limited assurance over our BRSR Core data for {fy} was obtained from an independent assurance firm."),
    ]:
        cid, fy = pick(a_pool[typ])[0]
        refs = bref(cid, fy) + ([f"audited_reports:{AUDIT[(cid, fy)]}"] if (cid, fy) in AUDIT else [])
        mk("CONTRADICT", "overstated_assurance", "easy", cid, "assurance_type", fy, None, tpl.format(fy=fyt(fy), co=co(cid)),
           f"Filing records assurance_type = {typ} for {fy}.", refs, tid, [it_cat(cid, fy, claim, "mismatch")], [])


# ======================================================================================
# INSUFFICIENT_EVIDENCE (40)
# ======================================================================================
FICTIONAL = ["Zephyrine Textiles Pvt Ltd", "Quillon Polymers Ltd", "Orvanta Cements Ltd", "Tessaly Pharma Ltd",
             "Nandivar Alloys Ltd", "Kavalur Agro Foods Ltd", "Brisalin Power Corporation Ltd", "Marudhan Motors Ltd",
             "Ilavarasi Chemicals Ltd", "Sundarbhoomi Minerals Ltd", "Vyomaka Digital Services Ltd", "Thelmar Pharmaceuticals Ltd"]


def fictional_names(n=10):
    known = set()
    for c in COMP.values():
        for s in [c["name"], c["short_name"], *json.loads(c["aliases"])]:
            known.add(s.lower())
    out = []
    for name in FICTIONAL:
        first = name.split()[0].lower()
        if name.lower() not in known and not any(first in k for k in known):
            out.append(name)
    assert len(out) >= n
    return out[:n]


def build_insufficient():
    cem = [c for c in CIDS if COMP[c]["sector"] == "Cement"]

    def ins(cid, tid, text, metric, fy, note, diff="medium", base=None):
        mk("INSUFFICIENT_EVIDENCE", "data_not_disclosed", diff, cid, metric, fy, base, text, note, [], tid)

    # scope 3 (7)
    for tid, tpl in [("in_s3_a", "Our Scope 3 emissions declined by {p} year on year in {fy}."),
                     ("in_s3_b", "{co}'s value chain (Scope 3) emissions stood at {q} in {fy}."),
                     ("in_s3_c", "We have reduced Scope 3 emissions from purchased goods and services by {p} since {b}."),
                     ("in_s3_d", "Upstream transportation emissions across our supply chain fell {p} in {fy}."),
                     ("in_s3_e", "Business travel and employee commuting at {co} generated {q} in {fy}."),
                     ("in_s3_f", "Our Scope 3 footprint is {p} lower than in {b}."),
                     ("in_s3_g", "Downstream use-of-sold-products emissions were {q} in {fy}.")]:
        cid = pick([(c,) for c in CIDS])[0][0]
        fy = rfy()
        base = "FY2020" if "{b}" in tpl else None
        text = tpl.format(co=co(cid), fy=fyt(fy), b=fyt_plain("FY2020"), p=pctt(rng.choice([6, 9, 12, 15, 18]), 0)[1],
                          q=qty(rng.uniform(2e5, 6e6), "tco2e", rng.choice(["lakh", "million"]))["text"])
        ins(cid, tid, text, "scope3_tco2e", fy, "No table in the world DB carries Scope 3 data (BRSR Core filings hold Scope 1 and 2 only).",
            "medium", base)
    # clinker factor (5)
    for tid, tpl in [("in_ck_a", "Our clinker-to-cement ratio improved to {r} in {fy}."),
                     ("in_ck_b", "{co} lowered its clinker factor to {r} in {fy}, among the best in the industry."),
                     ("in_ck_c", "Blended cements now dominate our product mix, taking the clinker factor down to {r} in {fy}."),
                     ("in_ck_d", "The clinker factor at our plants stood at {r} during {fy}."),
                     ("in_ck_e", "We reduced the clinker-to-cement ratio from {r0} to {r} between {b} and {fy}.")]:
        cid = pick([(c,) for c in cem])[0][0]
        fy = rfy()
        r = round(rng.uniform(0.62, 0.74), 2)
        text = tpl.format(co=co(cid), fy=fyt(fy), r=f"{r:.2f}", r0=f"{r + 0.06:.2f}", b=fyt_plain("FY2020"))
        ins(cid, tid, text, "clinker_factor", fy, "Clinker-to-cement ratio is not reported in any table of the world DB.", "medium",
            "FY2020" if "{b}" in tpl else None)
    # supply-chain wages (4)
    for tid, tpl in [("in_sw_a", "All workers in our tier-1 supply chain were paid at or above the statutory minimum wage in {fy}."),
                     ("in_sw_b", "{co} ensured a living wage for every contract worker in its value chain during {fy}."),
                     ("in_sw_c", "Women employed at our supplier units received {p} of the total wages paid at those units in {fy}."),
                     ("in_sw_d", "Average wages paid by our top 50 suppliers rose by {p} in {fy}.")]:
        cid = pick([(c,) for c in CIDS])[0][0]
        fy = rfy()
        ins(cid, tid, tpl.format(co=co(cid), fy=fyt(fy), p=pctt(rng.choice([8, 11, 14, 22]), 0)[1]), None, fy,
            "BRSR filings carry only the company's own wage data, nothing on supplier or contract workers.")
    # water replenishment (4)
    for tid, tpl in [("in_wr_a", "We replenished {p} of the freshwater we consumed in {fy} through watershed projects."),
                     ("in_wr_b", "{co} is water positive, having returned {n} million kL to local aquifers in {fy}."),
                     ("in_wr_c", "Our rainwater harvesting structures recharged {n} lakh kL of groundwater in {fy}."),
                     ("in_wr_d", "We replenished more water than we withdrew at all our manufacturing sites in {fy}.")]:
        cid = pick([(c,) for c in CIDS])[0][0]
        fy = rfy()
        ins(cid, tid, tpl.format(co=co(cid), fy=fyt(fy), p=pctt(rng.choice([110, 120, 135, 150]), 0)[1], n=rng.choice([1.2, 2.5, 3.8, 6.4])),
            None, fy, "The world DB records withdrawal and discharge only; no source carries water replenishment or recharge data.")
    # biodiversity (4)
    for tid, tpl in [("in_bd_a", "Our biodiversity programme protected {n} threatened species across our mine lease areas in {fy}."),
                     ("in_bd_b", "{co} planted {m} saplings in {fy}, with a survival rate of {p}."),
                     ("in_bd_c", "A faunal survey around our sites in {fy} recorded {n} species of birds, including {k} that are endangered."),
                     ("in_bd_d", "{h} hectares of degraded land were restored by {co} in {fy}.")]:
        cid = pick([(c,) for c in CIDS])[0][0]
        fy = rfy()
        ins(cid, tid, tpl.format(co=co(cid), fy=fyt(fy), n=rng.choice([14, 23, 31, 47]), k=rng.choice([3, 4, 6]),
                                 m=f"{rng.choice([2, 3, 5])},{rng.choice([10, 25, 60])},000", p=pctt(rng.choice([72, 81, 88]), 0)[1],
                                 h=rng.choice([45, 120, 310])),
            None, fy, "No source in the world DB holds species counts, plantation survival or land-restoration data (land_alerts only holds forest-loss alerts).")
    # FY outside DB coverage (3)
    for tid, tpl, metric, fy in [("in_fy_a", "Our Scope 1 emissions in FY2026 were {q}.", "scope1_tco2e", "FY2026"),
                                 ("in_fy_b", "In FY2019, {co} reported Scope 1 emissions of {q}.", "scope1_tco2e", "FY2019"),
                                 ("in_fy_c", "{co} recorded an LTIFR of {x} for FY2019.", "ltifr", "FY2019")]:
        cid = pick([(c,) for c in CIDS if v(c, "FY2020", "scope1_tco2e") >= 1e5])[0][0]
        base = v(cid, "FY2025" if fy == "FY2026" else "FY2020", "scope1_tco2e")
        q = qty(base * rng.uniform(0.9, 1.05), "tco2e", "lakh")["text"]
        ins(cid, tid, tpl.format(co=co(cid), q=q, x=f"{v(cid, 'FY2020', 'ltifr') * 1.1:.2f}"), metric, fy,
            f"The world DB holds BRSR filings for FY2020 to FY2025 only; no source covers {fy}.", "hard")
    # misc (3)
    for tid, tpl in [("in_ms_a", "{co} employees completed an average of {h} hours of ESG training in {fy}."),
                     ("in_ms_b", "We invested Rs {x} crore in pollution control equipment across our plants in {fy}."),
                     ("in_ms_c", "Our internal carbon price of Rs {n} per tonne of CO2e shaped every capex decision in {fy}.")]:
        cid = pick([(c,) for c in CIDS])[0][0]
        fy = rfy()
        ins(cid, tid, tpl.format(co=co(cid), fy=fyt(fy), h=rng.choice([6, 9, 14]), x=rng.choice([42, 85, 160]), n=rng.choice([750, 1200, 2000])),
            None, fy, "Training hours, environmental capex and internal carbon pricing are not in any table of the world DB.")
    # fictional companies (10)
    names = fictional_names(10)
    fc = [("in_fc_a", "Scope 1 emissions at {n} were {q} in {fy}.", "scope1_tco2e"),
          ("in_fc_b", "{n} sourced {p} of its electricity from renewable sources in {fy}.", "re_pct"),
          ("in_fc_c", "{n} reported zero fatalities across its operations in {fy}.", "fatalities"),
          ("in_fc_d", "There were no environmental penalties against {n} during {fy}.", "regulatory_actions"),
          ("in_fc_e", "{n} cut its GHG emission intensity by {p} between FY2020 and {fy}.", "ghg_intensity"),
          ("in_fc_f", "The LTIFR at {n} improved to {x} in {fy}.", "ltifr"),
          ("in_fc_g", "{n} withdrew {w} of water in {fy}.", "water_withdrawal_kl"),
          ("in_fc_h", "{n} recorded zero OCEMS exceedances in {fy}.", "ocems_exceedances"),
          ("in_fc_i", "All renewable energy certificates bought by {n} have been retired.", "rec_retirement"),
          ("in_fc_j", "The BRSR Core data of {n} for {fy} received reasonable assurance.", "assurance_type")]
    for (tid, tpl, metric), nm in zip(fc, names):
        fy = rfy()
        text = tpl.format(n=nm, fy=fyt(fy), q=qty(rng.uniform(2e5, 4e6), "tco2e", "lakh")["text"],
                          p=pctt(rng.choice([18, 27, 35, 44]), 0)[1], x=f"{rng.uniform(0.2, 0.7):.2f}",
                          w=qty(rng.uniform(1e6, 9e6), "kl", "million")["text"])
        fy_f = None if tid == "in_fc_i" else fy
        mk("INSUFFICIENT_EVIDENCE", "data_not_disclosed", "easy", None, metric, fy_f, "FY2020" if "FY2020" in tpl else None,
           text, f"'{nm}' does not match any company name or alias in the world DB, so there is nothing to verify against.",
           [], tid, name=nm)


# ======================================================================================
# NOT_CHECKABLE (30)
# ======================================================================================
def build_not_checkable():
    vague = [
        "We remain deeply committed to a greener, cleaner tomorrow for all our stakeholders.",
        "Sustainability is at the heart of everything {co} does.",
        "Our people are our greatest strength, and we care for the planet as much as we care for them.",
        "We strive to be a responsible corporate citizen and a true partner in India's growth story.",
        "At {co}, we believe in doing business the right way, for the environment and for the communities around us.",
        "Our journey towards a sustainable future is well underway.",
        "We are passionate about protecting nature for the generations to come.",
        "{co} continues to integrate environmental stewardship into its DNA.",
        "Green is not just a colour for us, it is a way of life.",
        "We take our environmental responsibilities very seriously.",
        "Together with our partners, we are building a better and more sustainable world.",
        "Our commitment to responsible growth has never been stronger.",
        "We aspire to be a leader in sustainable manufacturing.",
        "{co} is proud of the significant strides it has made in caring for the environment.",
        "Every employee at {co} is a sustainability champion.",
        "We continue to make meaningful progress on our ESG journey.",
        "Our operations are designed with the planet in mind.",
        "We believe good governance and environmental care go hand in hand, and we act on it every day.",
    ]
    targets = [
        ("We will achieve net zero emissions across our operations by 2050.", "scope1_tco2e"),
        ("{co} aims to source 100% of its electricity from renewable sources by FY2030.", "re_pct"),
        ("We are committed to reducing our Scope 1 and 2 emissions by 45 per cent by 2030 against a FY2020 baseline.", "scope1_tco2e"),
        ("By FY2028, we plan to become water positive across all our manufacturing sites.", "water_withdrawal_kl"),
        ("Our goal is zero fatalities across all sites by 2027.", "fatalities"),
        ("We intend to cut GHG emission intensity by 35% by FY2032.", "ghg_intensity"),
        ("{co} will retire certificates covering every unit of green power it claims, starting next year.", "rec_retirement"),
        ("We target zero waste to landfill by FY2030.", "waste_generated_t"),
        ("By 2035, women will account for 25% of our total wage bill.", "women_wage_pct"),
        ("We have set a science-based target to halve our absolute emissions by 2032.", "scope1_tco2e"),
        ("{co} plans to commission 200 MW of captive solar capacity over the next three years.", "re_pct"),
        ("Our ambition is to reach 50% renewable electricity by FY2029.", "re_pct"),
    ]
    for i, t in enumerate(vague):
        cid = pick([(c,) for c in CIDS])[0][0]
        mk("NOT_CHECKABLE", "vague_claim", "easy", cid, None, None, None, t.format(co=co(cid)),
           "Aspirational cheap talk with no measurable, falsifiable content.", [], f"nc_vague_{i}")
    for i, (t, m) in enumerate(targets):
        cid = pick([(c,) for c in CIDS])[0][0]
        mk("NOT_CHECKABLE", "none", "medium", cid, m, None, None, t.format(co=co(cid)),
           "Forward-looking target or plan; it cannot be verified against historical data.", [], f"nc_target_{i}")


# ======================================================================================
# Assemble, split, write
# ======================================================================================
def build():
    build_align()
    build_contradict()
    build_insufficient()
    build_not_checkable()

    counts = Counter(c["case"]["label"] for c in CASES)
    assert dict(counts) == TARGET, counts
    assert all(c["case"]["company_id"] not in DEMO_IDS for c in CASES)
    texts = [c["case"]["claim_text"] for c in CASES]
    assert len(set(texts)) == len(texts), "duplicate claim text"

    order = list(range(len(CASES)))
    random.Random(SEED + 1).shuffle(order)
    cases = [CASES[i] for i in order]
    for n, c in enumerate(cases, 1):
        cid = f"BM-{n:03d}"
        c["case"]["case_id"] = cid
        c["ver"]["case_id"] = cid

    srng = random.Random(SEED)
    by_label: dict[str, list] = defaultdict(list)
    for c in cases:
        by_label[c["case"]["label"]].append(c)
    n_test = {k: round(len(v_) * 60 / 200) for k, v_ in by_label.items()}
    assert sum(n_test.values()) == 60, n_test
    for lab in sorted(by_label):
        grp = sorted(by_label[lab], key=lambda c: c["case"]["case_id"])
        srng.shuffle(grp)
        for j, c in enumerate(grp):
            c["case"]["split"] = "test" if j < n_test[lab] else "train"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "cases.jsonl", "w") as f:
        for c in cases:
            f.write(json.dumps(c["case"], ensure_ascii=False) + "\n")
    with open(OUT_DIR / "verification.jsonl", "w") as f:
        for c in cases:
            f.write(json.dumps(c["ver"], ensure_ascii=False) + "\n")
    write_stats([c["case"] for c in cases])
    return [c["case"] for c in cases]


def table(rows: list[list], header: list[str]) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


def write_stats(cs: list[dict]):
    labels = spec.LABELS
    gwt = spec.GREENWASHING_TYPES
    by_label = Counter(c["label"] for c in cs)
    by_gw = Counter(c["gw_type"] for c in cs)
    by_diff = Counter(c["difficulty"] for c in cs)
    by_split = Counter(c["split"] for c in cs)
    lab_gw = Counter((c["label"], c["gw_type"]) for c in cs)
    lab_diff = Counter((c["label"], c["difficulty"]) for c in cs)
    lab_split = Counter((c["label"], c["split"]) for c in cs)
    by_metric = Counter(c["metric"] or "null" for c in cs)
    stats = {
        "total": len(cs), "seed": SEED, "n_templates": len(TEMPLATES),
        "by_label": {k: by_label[k] for k in labels},
        "by_gw_type": {k: by_gw[k] for k in gwt},
        "by_difficulty": dict(by_diff), "by_split": dict(by_split),
        "label_x_split": {f"{a}|{b}": n for (a, b), n in sorted(lab_split.items())},
        "label_x_difficulty": {f"{a}|{b}": n for (a, b), n in sorted(lab_diff.items())},
        "label_x_gw_type": {f"{a}|{b}": n for (a, b), n in sorted(lab_gw.items())},
        "by_metric": dict(sorted(by_metric.items())),
        "distinct_companies": len({c["company_id"] for c in cs if c["company_id"]}),
        "fictional_company_cases": sum(1 for c in cs if c["company_id"] is None),
    }
    json.dump(stats, open(OUT_DIR / "stats.json", "w"), indent=2)

    parts = ["# ESG claim-verification benchmark (200 cases)", "",
             "Fictional, deterministic (seed 20261004) benchmark generated from `data/world/world.db` by "
             "`python3 -m data_gen.build_benchmark`. Every number in a claim was computed from the DB; "
             "demo companies CMP-0001..0003 are excluded (reserved for the demo PDFs).", "",
             "## Files", "",
             "| file | content |", "|---|---|",
             "| `cases.jsonl` | the 200 cases (schema below) |",
             "| `verification.jsonl` | machine-checkable facts per case, used by `tests/test_benchmark.py` to recompute ALIGN/CONTRADICT value claims from the DB |",
             "| `stats.json` | composition counts |", "",
             "Case fields: `case_id, company_id, company_name, claim_text, metric, fy, baseline_fy, label, gw_type, difficulty, truth_note, evidence_refs, split`.",
             "`evidence_refs` are `table:row_id` strings. Labels: ALIGN (value within ~3% relative, or exact for counts/zero-claims/categories), "
             "CONTRADICT (>= 15% relative error, or wrong count/category), INSUFFICIENT_EVIDENCE (no DB source, or company not in DB), "
             "NOT_CHECKABLE (vague or future target).", "",
             "## Label x split", ""]
    parts.append(table([[l, by_label[l], lab_split[(l, 'train')], lab_split[(l, 'test')]] for l in labels] +
                       [["**total**", len(cs), by_split["train"], by_split["test"]]], ["label", "n", "train", "test"]))
    parts += ["", "## Label x greenwashing type", ""]
    rows = [[g] + [lab_gw[(l, g)] for l in labels] + [by_gw[g]] for g in gwt if by_gw[g]]
    parts.append(table(rows, ["gw_type"] + labels + ["total"]))
    parts += ["", "## Label x difficulty", ""]
    parts.append(table([[l] + [lab_diff[(l, d)] for d in ("easy", "medium", "hard")] for l in labels], ["label", "easy", "medium", "hard"]))
    parts += ["", "## Metric coverage", ""]
    parts.append(table([[m, n] for m, n in sorted(by_metric.items(), key=lambda t: -t[1])], ["metric", "cases"]))
    parts += ["", "## Design notes", "",
              f"- {len(TEMPLATES)} distinct claim templates; FY written as `FY2025`, `FY2024-25`, `FY 2024-25` or `the financial year 2024-25`; "
              "emissions in raw, Indian-grouped, lakh, crore or million tCO2e; `%` and `per cent`.",
              "- Difficulty: easy = direct value; medium = percentage change or two-year comparison; hard = traps "
              "(period trap, scope swap, absolute vs intensity, unit error, certificates, geo, baseline restatement).",
              "- ALIGN cases always carry `gw_type = none` (including the honest reverse cases: true intensity claims while absolute emissions rose, "
              "period traps, true zero-exceedance / no-forest-loss / no-penalty claims). INSUFFICIENT_EVIDENCE uses `data_not_disclosed`; "
              "NOT_CHECKABLE uses `vague_claim` (cheap talk) or `none` (future targets).",
              "- In this world Scope 1 grows for almost every company while intensity falls, so honest reduction claims are about intensity, "
              "Scope 2 or LTIFR, and absolute Scope 1 reduction claims are contradictions.",
              "- Forest-loss claims use alerts within 5 km (haversine from facility coordinates) dated inside the fiscal year; "
              "a contradiction is only used when haversine and the DB's nearest-facility distance agree.",
              "- Penalty claims count `regulatory_actions` by action date inside the FY; 'no penalty' claims against planted events use rows with `penalty_inr > 0`.",
              "- Splits are stratified by label (30% test, rounded): 140 train, 60 test.", ""]
    (OUT_DIR / "README.md").write_text("\n".join(parts))


if __name__ == "__main__":
    out = build()
    c = Counter(x["label"] for x in out)
    print(f"wrote {len(out)} cases: {dict(c)}; templates={len(TEMPLATES)}")
