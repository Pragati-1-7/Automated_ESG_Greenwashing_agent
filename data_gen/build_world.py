"""
data_gen/build_world.py

Deterministic generator for the synthetic "mock world" SQLite database
(data/world/world.db) plus data/world/planted_events.json.

    python3 -m data_gen.build_world [--out PATH]

One function per table (gen_*) returning a list of dicts, plus write_db().
No network, no LLM. ALL COMPANIES / FIGURES / EVENTS ARE FICTIONAL.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from . import spec
from .news_base import BOARD_NAME
from .world_refs import (ASSURERS, DISTRICTS, FAC_TEMPLATES, FOREST_BOXES, PREFIXES, SECTOR_NOUNS, SECTOR_PROFILE,
                         SECTOR_TAG, STATES)
from .world_utils import (fmt_date, fy_of, fy_range, haversine_km, inr, offset_point, rand_date)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB = ROOT / "data" / "world" / "world.db"

FYS = spec.FISCAL_YEARS
TODAY_CAP = date(2026, 9, 30)  # nothing is dated after this

KUTCH = (23.7337, 69.8597)  # Aurelia's (non-DB) solar park location: keep alerts away
DEMO_IDS = {"CMP-0001", "CMP-0002", "CMP-0003"}
DEMO_BAND = {"CMP-0001": "Large", "CMP-0002": "Mid", "CMP-0003": "Small"}
DEMO_GHG_WEIGHTS = {
    "FAC-0001": 0.70, "FAC-0002": 0.25, "FAC-0004": 0.04, "FAC-0003": 0.01,
    "FAC-0005": 0.50, "FAC-0006": 0.33, "FAC-0007": 0.05, "FAC-0008": 0.12,
    "FAC-0009": 0.28, "FAC-0010": 0.70, "FAC-0011": 0.02,
}
TARGETS = dict(companies=150, facilities=420, brsr_filings=900, facility_ghg=2500, ocems_exceedances=2000,
               regulatory_actions=400, land_alerts=1500, re_certificates=800, audited_reports=450, news_articles=500)


def _rng(name: str) -> random.Random:
    """Independent deterministic stream per table (string seeding is stable across runs)."""
    return random.Random(f"{spec.SEED}:{name}")


def _demo_points() -> list[tuple[float, float]]:
    pts = [KUTCH]
    for d in spec.DEMO_COMPANIES:
        for f in d["facilities"]:
            pts.append((f["lat"], f["lon"]))
    return pts


DEMO_POINTS = _demo_points()


def _lognorm_between(rng, lo, hi, u=None):
    u = rng.random() if u is None else u
    return math.exp(math.log(lo) + u * (math.log(hi) - math.log(lo)))


def _poisson(rng, lam: float) -> int:
    if lam <= 0:
        return 0
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L:
            return k
        k += 1


def template_for(sector: str, ftype: str):
    for t in FAC_TEMPLATES[sector]:
        if t[0] == ftype:
            return t
    raise KeyError((sector, ftype))


# ---------------------------------------------------------------------------
# companies
# ---------------------------------------------------------------------------

def gen_companies(rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    used_cin: set[str] = set()
    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        rows.append(dict(company_id=d["company_id"], cin=d["cin"], name=d["name"], short_name=d["short_name"],
                         aliases=json.dumps(d["aliases"]), sector=d["sector"], hq_city=d["hq_city"],
                         hq_state=d["hq_state"], listing=d["listing"], market_cap_band=DEMO_BAND[d["company_id"]]))
        used_cin.add(d["cin"])
    counts = {s: 15 for s in spec.SECTORS}
    for r in rows:
        counts[r["sector"]] -= 1
    seq = [s for s in spec.SECTORS for _ in range(counts[s])]
    rng.shuffle(seq)
    prefixes = list(dict.fromkeys(PREFIXES))
    assert len(prefixes) >= len(seq), "not enough name prefixes"
    prefixes = [p for p in prefixes if p.lower() not in {"aurelia", "vajra", "sahyadri", "kaveri"}]
    rng.shuffle(prefixes)
    used_bse: set[int] = set()
    n_demo = len(rows)
    for i, sector in enumerate(seq):
        prefix = prefixes[i]
        prof = SECTOR_PROFILE[sector]
        noun = rng.choice(SECTOR_NOUNS[sector])
        name = f"{prefix} {noun}" + ("" if noun.endswith("Ltd") else " Ltd")
        short = f"{prefix} {noun.split()[0]}"
        bare = name[:-4]
        initials = "".join(w[0] for w in re.findall(r"[A-Za-z]+", bare)) + "L"
        aliases = list(dict.fromkeys([short, bare, initials.upper()]))
        city, state = rng.choice(prof["hq"])
        band = rng.choices(["Large", "Mid", "Small"], weights=[0.2, 0.35, 0.45])[0]
        ticker = (prefix[:5] + SECTOR_TAG[sector]).upper()
        r = rng.random()
        if r < 0.06:
            listed, listing = False, "Unlisted"
        elif r < 0.22:
            listed, listing = True, f"NSE, BSE: {ticker}"
        else:
            listed, listing = True, f"NSE: {ticker}"
        while True:
            cin = (f"{'L' if listed else 'U'}{rng.choice(prof['nic'])}{STATES[state]['cin']}"
                   f"{rng.randint(1962, 2012)}PLC{rng.randint(1000, 499999):06d}")
            if cin not in used_cin:
                used_cin.add(cin)
                break
        rows.append(dict(company_id=f"CMP-{n_demo + i + 1:04d}", cin=cin, name=name, short_name=short,
                         aliases=json.dumps(aliases), sector=sector, hq_city=city, hq_state=state,
                         listing=listing, market_cap_band=band))
    return rows


# ---------------------------------------------------------------------------
# facilities
# ---------------------------------------------------------------------------

NAME_ALIAS = {"Gautam Buddha Nagar": "Noida", "Kanpur Nagar": "Kanpur", "Bengaluru Urban": "Bengaluru",
              "Paschim Bardhaman": "Durgapur", "Purba Medinipur": "Haldia", "West Singhbhum": "Chaibasa",
              "East Singhbhum": "Jamshedpur", "Dakshina Kannada": "Mangaluru", "Bhadradri Kothagudem": "Kothagudem",
              "Udham Singh Nagar": "Rudrapur", "Paschim Medinipur": "Medinipur"}

TYPE_STATES = {
    "Solar park": ["Rajasthan", "Gujarat", "Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana"],
    "Wind farm": ["Gujarat", "Tamil Nadu", "Karnataka", "Rajasthan", "Maharashtra", "Andhra Pradesh"],
    "Captive wind farm": ["Tamil Nadu", "Gujarat", "Karnataka", "Maharashtra", "Rajasthan"],
    "Hydro power station": ["Himachal Pradesh", "Uttarakhand", "Karnataka", "Odisha"],
    "Open-cast coal mine": ["Chhattisgarh", "Odisha", "Jharkhand", "Madhya Pradesh"],
    "Open-cast iron ore mine": ["Odisha", "Jharkhand", "Chhattisgarh", "Karnataka", "Goa"],
    "Bauxite mine": ["Odisha", "Chhattisgarh", "Jharkhand", "Gujarat"],
    "Manganese mine": ["Odisha", "Madhya Pradesh", "Maharashtra", "Karnataka"],
}
RENEWABLE_TYPES = ("Solar park", "Wind farm", "Hydro power station", "Biomass power plant")
THERMAL_TYPES = ("Coal-fired thermal power plant", "Gas-based power plant")


def _locate(rng, state: str, forest_only: bool = False):
    cand = [d for d in DISTRICTS[state] if (d[3] or not forest_only)]
    if not cand:
        return None
    for _ in range(40):
        d = rng.choice(cand)
        lat = round(d[1] + rng.uniform(-0.15, 0.15), 4)
        lon = round(d[2] + rng.uniform(-0.15, 0.15), 4)
        if all(haversine_km(lat, lon, p[0], p[1]) > 25 for p in DEMO_POINTS):
            return d[0], lat, lon
    return None


def _capacity(rng, lo, hi):
    v = rng.uniform(lo, hi)
    if hi >= 10000:
        return float(round(v, -3))
    if hi >= 100:
        return float(round(v / 10) * 10)
    if hi >= 10:
        return float(round(v))
    return round(v, 1)


def gen_facilities(rng: random.Random, companies: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        board = STATES[d["hq_state"]]["board"]
        for f in d["facilities"]:
            fb = STATES[f["state"]]["board"]
            rows.append(dict(facility_id=f["facility_id"], company_id=d["company_id"], name=f["name"], type=f["type"],
                             district=f["district"], state=f["state"], lat=f["lat"], lon=f["lon"],
                             capacity_value=f["capacity_value"], capacity_unit=f["capacity_unit"],
                             consent_no=f"{fb}/CTO/{rng.randint(2014, 2023)}/{rng.randint(1000, 99999):05d}",
                             forest_adjacent=int(f["forest_adjacent"])))
    next_id = len(rows) + 1
    for c in companies:
        if c["company_id"] in DEMO_IDS:
            continue
        sector = c["sector"]
        prof = SECTOR_PROFILE[sector]
        T = FAC_TEMPLATES[sector]
        renewable_power = sector == "Power" and rng.random() < 0.25
        if renewable_power:
            T = [t for t in T if t[0] in RENEWABLE_TYPES]
            anchor = [t for t in T if t[0] in ("Solar park", "Wind farm")][rng.randint(0, 1)]
        else:
            anchor = [t for t in T if t[6]][0]
        rest = [t for t in T if t is not anchor]
        if sector == "Power" and not renewable_power:
            rest = [t for t in rest if t[0] != "Biomass power plant" or rng.random() < 0.3]
        n = rng.randint(*prof["n_fac"])
        chosen = [anchor]
        pool = rest[:]
        while len(chosen) < n and pool:
            if renewable_power or sector == "Power":
                t = rng.choices(rest, weights=[x[3] + 0.15 for x in rest])[0]  # may repeat
            else:
                t = rng.choices(pool, weights=[x[3] + 0.1 for x in pool])[0]
                pool.remove(t)
            chosen.append(t)
        primary = c["hq_state"] if c["hq_state"] in prof["states"] else rng.choice(prof["states"])
        names: set[str] = set()
        for t in chosen:
            allowed = TYPE_STATES.get(t[0], prof["states"])
            if primary in allowed and rng.random() < 0.65:
                state = primary
            else:
                state = rng.choice(allowed)
            fa = bool(t[8]) and rng.random() < 0.11
            loc = _locate(rng, state, forest_only=True) if fa else None
            if loc is None:
                fa = False
                for st in [state] + rng.sample(allowed, len(allowed)):
                    loc = _locate(rng, st)
                    if loc:
                        state = st
                        break
            district, lat, lon = loc
            base = f"{NAME_ALIAS.get(district, district)} {t[7]}"
            nm, k = base, 1
            while nm in names:
                k += 1
                nm = f"{base} {'I' * k if k < 4 else k}"
            names.add(nm)
            rows.append(dict(facility_id=f"FAC-{next_id:04d}", company_id=c["company_id"], name=nm, type=t[0],
                             district=district, state=state, lat=lat, lon=lon,
                             capacity_value=_capacity(rng, *t[2]), capacity_unit=t[1],
                             consent_no=f"{STATES[state]['board']}/CTO/{rng.randint(2014, 2023)}/{rng.randint(1000, 99999):05d}",
                             forest_adjacent=int(fa)))
            next_id += 1
    # top-up so that forest-adjacent facilities are not too rare (~10% of mining/steel/power)
    csec = {c["company_id"]: c["sector"] for c in companies}
    forested = {(s, d[0]) for s, ds in DISTRICTS.items() for d in ds if d[3]}
    n_fa = sum(1 for r in rows if r["forest_adjacent"] and r["company_id"] not in DEMO_IDS)
    if n_fa < 16:
        for r in rows:
            if n_fa >= 16:
                break
            if (r["company_id"] not in DEMO_IDS and not r["forest_adjacent"]
                    and csec[r["company_id"]] in ("Mining", "Steel", "Power")
                    and template_for(csec[r["company_id"]], r["type"])[8] and (r["state"], r["district"]) in forested):
                r["forest_adjacent"] = 1
                n_fa += 1
    return rows


# ---------------------------------------------------------------------------
# BRSR filings
# ---------------------------------------------------------------------------

def _assurance_plan(rng) -> tuple[list[str], str | None]:
    kind = rng.choices(["never", "late", "mid", "early"], weights=[0.25, 0.35, 0.25, 0.15])[0]
    plan = ["none"] * 6
    if kind == "late":
        s = rng.choice([3, 4])
        up = 5 if (s == 3 and rng.random() < 0.4) else 99
        for i in range(s, 6):
            plan[i] = "reasonable" if i >= up else "limited"
    elif kind == "mid":
        s = rng.choice([2, 3])
        up = s + rng.choice([2, 3])
        for i in range(s, 6):
            plan[i] = "reasonable" if i >= up else "limited"
    elif kind == "early":
        up = rng.choice([2, 3])
        for i in range(0, 6):
            plan[i] = "reasonable" if i >= up else "limited"
    provider = rng.choice(ASSURERS) if kind != "never" else None
    return plan, provider


def gen_brsr(rng: random.Random, companies: list[dict], facilities: list[dict]) -> list[dict]:
    fac_by_c = defaultdict(list)
    for f in facilities:
        fac_by_c[f["company_id"]].append(f)
    rows: list[dict] = []
    for c in companies:
        cid, sector = c["company_id"], c["sector"]
        if cid in DEMO_IDS:
            t = spec.demo_by_id(cid)["true"]
            for i, fy in enumerate(FYS):
                rev = float(t["revenue_cr"][i])
                s1, s2 = float(t["scope1_tco2e"][i]), float(t["scope2_tco2e"][i])
                filed = date(int(fy[2:]), rng.randint(7, 9), rng.randint(1, 28)).isoformat()
                if cid == "CMP-0001" and fy == "FY2025":
                    filed = "2025-07-03"
                rows.append(dict(
                    filing_id=f"BRSR-{cid}-{fy}", company_id=cid, fy=fy, revenue_cr=rev, scope1_tco2e=s1,
                    scope2_tco2e=s2, ghg_intensity=round((s1 + s2) / rev, 1), energy_gj=float(t["energy_gj"][i]),
                    re_pct=float(t["re_pct"][i]), water_withdrawal_kl=float(t["water_withdrawal_kl"][i]),
                    water_discharge_kl=float(t["water_discharge_kl"][i]), waste_generated_t=float(t["waste_generated_t"][i]),
                    waste_recovered_t=float(t["waste_recovered_t"][i]), ltifr=float(t["ltifr"][i]),
                    fatalities=int(t["fatalities"][i]), women_wage_pct=float(t["women_wage_pct"][i]),
                    msme_sourcing_pct=float(t["msme_sourcing_pct"][i]), assurance_type=t["assurance_type"][i],
                    assurance_provider=t["assurance_provider"][i], filed_on=filed))
            continue
        prof = SECTOR_PROFILE[sector]
        band_u = {"Large": (0.67, 1.0), "Mid": (0.33, 0.67), "Small": (0.0, 0.33)}[c["market_cap_band"]]
        rev25 = _lognorm_between(rng, *prof["rev"], u=rng.uniform(*band_u))
        types = {f["type"] for f in fac_by_c[cid]}
        renewable_power = sector == "Power" and not (types & set(THERMAL_TYPES))
        s1_int = _lognorm_between(rng, 0.3, 5) if renewable_power else _lognorm_between(rng, *prof["s1_int"])
        s2_ratio = rng.uniform(*prof["s2_ratio"]) if not renewable_power else rng.uniform(0.3, 2.0)
        en_int = (s1_int * 10.5 if not renewable_power else rng.uniform(150, 600)) if prof["en_int"] is None \
            else _lognorm_between(rng, *prof["en_int"])
        wat_int = _lognorm_between(rng, *prof["wat_int"]) * (0.05 if renewable_power else 1.0)
        waste_int = _lognorm_between(rng, *prof["waste_int"]) * (0.02 if renewable_power else 1.0)
        disch = rng.uniform(*prof["disch"])
        recov0 = rng.uniform(*prof["recov"]) - 0.06
        d_s1, d_s2 = rng.uniform(0.0, 0.045), rng.uniform(0.02, 0.09)
        d_en, d_wat = rng.uniform(-0.005, 0.02), rng.uniform(-0.01, 0.025)
        re0 = rng.uniform(*prof["re0"]) if not renewable_power else rng.uniform(55, 85)
        re_step = rng.uniform(*prof["re_gain"])
        l25 = rng.uniform(*prof["ltifr"])
        d_l = rng.uniform(0.02, 0.10)
        w25 = rng.uniform(*prof["women"])
        w_step = rng.uniform(0.2, 0.8) * (prof["women"][1] - prof["women"][0]) / 10 + 0.1
        m25 = rng.uniform(*prof["msme"])
        m_step = rng.uniform(0.3, 1.2)
        g = [None, rng.gauss(-0.06, 0.05), rng.gauss(0.22, 0.06), rng.gauss(0.14, 0.05), rng.gauss(0.08, 0.05), rng.gauss(0.07, 0.04)]
        rev = [0.0] * 6
        rev[5] = rev25
        for t in range(5, 0, -1):
            rev[t - 1] = rev[t] / (1 + g[t])
        plan, provider = _assurance_plan(rng)
        re_pct = []
        r = re0
        for t in range(6):
            re_pct.append(min(r, 98.0))
            r += max(0.0, re_step + rng.gauss(0, 0.8))
        for t, fy in enumerate(FYS):
            k = 5 - t
            nz = lambda s=0.02: 1 + rng.gauss(0, s)
            covid = 1.07 if t == 1 else 1.0
            s1 = rev[t] * s1_int * (1 + d_s1) ** k * covid * nz()
            s2 = rev[t] * s1_int * s2_ratio * (1 + d_s2) ** k * covid * nz(0.025)
            energy = rev[t] * en_int * (1 + d_en) ** k * covid * nz()
            wat = rev[t] * wat_int * (1 + d_wat) ** k * nz()
            dis = wat * min(0.95, disch * nz(0.05))
            waste = rev[t] * waste_int * (1 + d_en) ** k * nz(0.03)
            rec = min(0.99, max(0.1, recov0 + 0.012 * t + rng.gauss(0, 0.01)))
            ltifr = min(1.2, max(0.05, l25 * (1 + d_l) ** k * nz(0.05)))
            lam = prof["fat_rate"] * math.sqrt(rev[t] / 10000.0) * (0.92 ** t)
            fat = _poisson(rng, lam)
            women = max(0.5, w25 - w_step * k + rng.gauss(0, 0.2))
            msme = max(1.0, m25 - m_step * k + rng.gauss(0, 0.3))
            atype = plan[t]
            filed = date(int(fy[2:]), rng.randint(7, 9), rng.randint(1, 28)).isoformat()
            revr = float(round(rev[t]))
            s1r, s2r = float(round(s1)), float(round(s2))
            rows.append(dict(
                filing_id=f"BRSR-{cid}-{fy}", company_id=cid, fy=fy, revenue_cr=revr, scope1_tco2e=s1r, scope2_tco2e=s2r,
                ghg_intensity=round((s1r + s2r) / revr, 1), energy_gj=float(round(energy)), re_pct=round(re_pct[t], 1),
                water_withdrawal_kl=float(round(wat)), water_discharge_kl=float(round(dis)),
                waste_generated_t=float(round(waste)), waste_recovered_t=float(round(waste * rec)),
                ltifr=round(ltifr, 2), fatalities=fat, women_wage_pct=round(women, 1), msme_sourcing_pct=round(msme, 1),
                assurance_type=atype, assurance_provider=provider if atype != "none" else None, filed_on=filed))
    return rows


# ---------------------------------------------------------------------------
# facility GHG
# ---------------------------------------------------------------------------

def gen_facility_ghg(rng: random.Random, companies: list[dict], facilities: list[dict], brsr: list[dict]) -> list[dict]:
    csec = {c["company_id"]: c["sector"] for c in companies}
    fac_by_c = defaultdict(list)
    for f in facilities:
        fac_by_c[f["company_id"]].append(f)
    brsr_by = {(b["company_id"], b["fy"]): b for b in brsr}
    rows: list[dict] = []
    n = 0
    for c in companies:
        cid = c["company_id"]
        facs = fac_by_c[cid]
        for fy in FYS:
            b = brsr_by[(cid, fy)]
            ws = []
            for f in facs:
                t = template_for(csec[cid], f["type"])
                base = DEMO_GHG_WEIGHTS.get(f["facility_id"], t[3])
                ws.append(base * math.exp(rng.gauss(0, 0.004 if cid in DEMO_IDS else 0.03)))
            tot_w = sum(ws)
            totals = [round(b["scope1_tco2e"] * w / tot_w, 1) for w in ws]
            diff = round(b["scope1_tco2e"] - sum(totals), 1)
            totals[max(range(len(totals)), key=lambda i: totals[i])] += diff
            for f, total in zip(facs, totals):
                t = template_for(csec[cid], f["type"])
                coal_mine = "coal mine" in f["type"].lower()
                ch4 = round(total * (rng.uniform(0.03, 0.07) if coal_mine else rng.uniform(0.002, 0.012)), 1)
                n2o = round(total * rng.uniform(0.002, 0.008), 1)
                co2 = round(total - ch4 - n2o, 1)
                n += 1
                rows.append(dict(row_id=f"FGHG-{n:05d}", facility_id=f["facility_id"], fy=fy, co2_t=co2, ch4_tco2e=ch4,
                                 n2o_tco2e=n2o, total_tco2e=round(co2 + ch4 + n2o, 1), method=t[4],
                                 verified=int(b["assurance_type"] != "none")))
    return rows


# ---------------------------------------------------------------------------
# planted-scenario plan (non-demo companies)
# ---------------------------------------------------------------------------

def make_plan(rng: random.Random, companies, facilities, brsr) -> dict:
    """Decide which ~60 generated companies carry a planted discrepancy and its parameters."""
    csec = {c["company_id"]: c["sector"] for c in companies}
    fac_by_c = defaultdict(list)
    for f in facilities:
        fac_by_c[f["company_id"]].append(f)
    gen = [c["company_id"] for c in companies if c["company_id"] not in DEMO_IDS]
    used: set[str] = set()
    plan: dict[str, list[dict]] = {"land_alerts": [], "ocems": [], "regulatory_penalty": [], "rec_unretired": []}

    fa_cos = [cid for cid in gen if any(f["forest_adjacent"] for f in fac_by_c[cid])]
    rng.shuffle(fa_cos)
    for cid in fa_cos[:15]:
        fac = rng.choice([f for f in fac_by_c[cid] if f["forest_adjacent"]])
        plan["land_alerts"].append(dict(company_id=cid, facility_id=fac["facility_id"], fy=rng.choice(FYS[3:]),
                                        n=rng.randint(7, 19)))
        used.add(cid)
    heavy = [cid for cid in gen if cid not in used and csec[cid] in ("Steel", "Cement", "Power", "Chemicals", "Mining", "Pharmaceuticals", "Textiles")
             and any(template_for(csec[cid], f["type"])[5] for f in fac_by_c[cid])]
    rng.shuffle(heavy)
    for cid in heavy[:15]:
        fac = rng.choice([f for f in fac_by_c[cid] if template_for(csec[cid], f["type"])[5]])
        plan["ocems"].append(dict(company_id=cid, facility_id=fac["facility_id"], fy=rng.choice(FYS[3:]), n=rng.randint(9, 28)))
        used.add(cid)
    reg_pool = [cid for cid in gen if cid not in used and csec[cid] not in ("IT Services",)]
    rng.shuffle(reg_pool)
    for cid in reg_pool[:15]:
        facs = [f for f in fac_by_c[cid] if template_for(csec[cid], f["type"])[5] or "mine" in f["type"]] or fac_by_c[cid]
        plan["regulatory_penalty"].append(dict(company_id=cid, facility_id=rng.choice(facs)["facility_id"],
                                               fy=rng.choice(FYS[3:]), penalty=round(rng.uniform(0.5e7, 1.2e8), -5)))
        used.add(cid)
    rec_pool = [cid for cid in gen if cid not in used]
    rng.shuffle(rec_pool)
    n_rec = max(15, 60 - sum(len(v) for v in plan.values()))
    for cid in rec_pool[:n_rec]:
        plan["rec_unretired"].append(dict(company_id=cid, retired_share=rng.uniform(0.06, 0.2), active_mult=rng.uniform(3, 8)))
        used.add(cid)
    return plan


# ---------------------------------------------------------------------------
# regulatory actions
# ---------------------------------------------------------------------------

ZONE_NAME = {"EZ": "Eastern Zone", "WZ": "Western Zone", "SZ": "Southern Zone", "CZ": "Central Zone", "PB": "Principal Bench"}
AIR_ISSUES = ["stack emission exceedances recorded by the online continuous emission monitoring system",
              "operating without a functional air pollution control device on one stack",
              "fugitive dust emissions from raw material handling yards",
              "non-compliance with particulate matter limits stipulated in the consent to operate"]
WATER_ISSUES = ["discharge of inadequately treated effluent beyond the prescribed BOD and COD norms",
                "a non-functional effluent treatment plant during part of the year",
                "release of untreated effluent into a nearby drain",
                "failure to maintain zero liquid discharge as required under the consent conditions"]
MINE_ISSUES = ["mining beyond the permitted lease boundary", "felling of trees outside the area covered by forest clearance",
               "dumping of overburden outside the designated dump yard", "extraction in excess of the environmental clearance limit"]
POWER_ISSUES = ["fly ash utilisation below the prescribed norm and a breach of the ash dyke",
                "delay in commissioning flue gas desulphurisation units within the stipulated timeline",
                "stack emission exceedances recorded by the online monitoring system"]
GENERIC_ISSUES = ["unauthorised groundwater extraction", "improper storage and disposal of hazardous waste",
                  "non-compliance with conditions of the environmental clearance", "operating without valid consent for an expansion"]
SEBI_ISSUES_EARLY = ["delay in submitting the Business Responsibility Report to the stock exchanges with the annual report",
                     "non-compliance with the disclosure requirements under Regulation 34(2)(f) of the LODR Regulations"]
SEBI_ISSUES_MID = SEBI_ISSUES_EARLY + ["delay in submitting the Business Responsibility and Sustainability Report to the stock exchanges"]
SEBI_ISSUES_LATE = ["delay in submitting the Business Responsibility and Sustainability Report to the stock exchanges",
                    "incomplete disclosure of BRSR Core indicators in the annual report",
                    "non-compliance with the disclosure requirements under Regulation 34(2)(f) of the LODR Regulations"]


def sebi_issue(rng, iso: str) -> str:
    pool = SEBI_ISSUES_EARLY if iso < "2022-04-01" else SEBI_ISSUES_MID if iso < "2023-04-01" else SEBI_ISSUES_LATE
    return rng.choice(pool)


def _issue_for(rng, sector: str, ftype: str) -> str:
    t = template_for(sector, ftype)
    if "mine" in ftype.lower():
        return rng.choice(MINE_ISSUES)
    if sector == "Power" and t[5] == "air":
        return rng.choice(POWER_ISSUES)
    if t[5] == "air":
        return rng.choice(AIR_ISSUES)
    if t[5] == "water":
        return rng.choice(WATER_ISSUES)
    return rng.choice(GENERIC_ISSUES)


def _reg_summary(rng, c, fac, authority, otype, penalty, issue, zone) -> str:
    name = c["name"]
    where = f"{fac['name']} in {fac['district']}, {fac['state']}" if fac else "its operations"
    pen = inr(penalty) if penalty else ""
    if authority == "SEBI":
        if otype == "penalty":
            return (f"SEBI adjudicating officer imposed a monetary penalty of {pen} on {name} for {issue}. "
                    f"The company has been directed to ensure timely compliance in future.")
        return f"SEBI issued an administrative warning letter to {name} for {issue}."
    if authority == "NGT":
        zn = ZONE_NAME[zone]
        if otype == "environmental_compensation":
            return (f"The National Green Tribunal ({zn}) directed {name} to pay environmental compensation of {pen} "
                    f"for {issue} at {where}, applying the polluter pays principle.")
        if otype == "penalty":
            return (f"The National Green Tribunal ({zn}) imposed a penalty of {pen} on {name} for {issue} at {where} "
                    f"and directed the State Pollution Control Board to monitor compliance.")
        if otype == "closure_direction":
            return (f"The National Green Tribunal ({zn}) directed closure of operations at {where} until {name} "
                    f"demonstrates compliance on {issue}.")
        return f"The National Green Tribunal ({zn}) cautioned {name} over {issue} at {where} and sought a compliance report."
    if authority == "MoEFCC":
        return (f"The Ministry of Environment, Forest and Climate Change issued a {otype.replace('_', ' ')} to {name} "
                f"over {issue} at {where}." + (f" A penalty of {pen} was levied." if penalty else ""))
    who = "Central Pollution Control Board" if authority == "CPCB" else BOARD_NAME.get(authority, authority)
    if otype == "show_cause":
        return f"The {who} issued a show-cause notice to {name} for {issue} at {where}; the company was asked to respond within 15 days."
    if otype == "closure_direction":
        return (f"The {who} issued a closure direction under Section 5 of the Environment (Protection) Act to {name} "
                f"for {issue} at {where}.")
    if otype == "consent_revoked":
        return f"The {who} revoked the consent to operate of {where} operated by {name} for {issue}."
    if otype == "warning":
        return f"The {who} issued a warning to {name} regarding {issue} at {where} and directed corrective action."
    return (f"The {who} directed {name} to pay {'environmental compensation' if otype == 'environmental_compensation' else 'a penalty'} "
            f"of {pen} for {issue} at {where}.")


def _case_no(rng, authority, state, otype, year, used, district):
    while True:
        n = rng.randint(12, 899)
        if authority == "NGT":
            cn = f"O.A. No. {n}/{year} ({STATES[state]['zone']})"
        elif authority == "CPCB":
            cn = f"CPCB/IPC-{rng.choice(['I', 'II', 'III', 'IV'])}/{STATES[state]['cin']}/{year}/{n:03d}"
        elif authority == "SEBI":
            cn = f"SEBI/AO/{year}-{str(year + 1)[2:]}/{rng.randint(1000, 29999)}"
        elif authority == "MoEFCC":
            cn = f"MoEFCC/FC/{STATES[state]['cin']}/{year}/{n:03d}"
        else:
            code = {"show_cause": "SCN", "closure_direction": "CLD", "consent_revoked": "REV", "warning": "WRN",
                    "penalty": "PEN", "environmental_compensation": "ENV"}[otype]
            cn = f"{authority}/{district[:3].upper()}/{code}/{year}/{n:03d}"
        if cn not in used:
            used.add(cn)
            return cn


def _status_for(rng, otype, authority, iso):
    d = date.fromisoformat(iso)
    if otype in ("environmental_compensation", "penalty"):
        if authority == "SEBI":
            return rng.choice(["paid", "paid", "settled", "appealed_SAT"])
        return rng.choice(["paid", "paid", "paid_under_protest", "appealed", "pending_payment", "stayed_by_court"])
    if otype == "show_cause":
        return rng.choice(["reply_filed", "reply_filed", "closed", "pending"])
    if otype in ("closure_direction", "consent_revoked"):
        pre = "revoked" if otype == "closure_direction" else "restored"
        if rng.random() < 0.8:
            e = d + timedelta(days=rng.randint(14, 150))
            if e <= date(2026, 6, 30):
                return f"{pre}_{e.isoformat()}"
        return rng.choice(["in_force", "stayed_by_court"])
    return rng.choice(["closed", "complied", "closed"])


def _sample_penalty(rng, lo=5e5, hi=2.5e8):
    u = rng.random() ** 1.7
    return float(max(lo, round(math.exp(math.log(lo) + u * (math.log(hi) - math.log(lo))), -5)))


def gen_regulatory_actions(rng: random.Random, companies, facilities, plan) -> list[dict]:
    cmap = {c["company_id"]: c for c in companies}
    fac_by_c = defaultdict(list)
    for f in facilities:
        fac_by_c[f["company_id"]].append(f)
    fmap = {f["facility_id"]: f for f in facilities}
    used_cases: set[str] = set()
    rows: list[dict] = []
    # demo: exactly the spec events
    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        for ev in d["events"]["regulatory_actions"]:
            rows.append(dict(company_id=d["company_id"], facility_id=ev["facility_id"], authority=ev["authority"],
                             case_no=ev["case_no"], order_type=ev["order_type"], date=ev["date"],
                             penalty_inr=float(ev["penalty_inr"]), status=ev["status"], summary=ev["summary"]))
            used_cases.add(ev["case_no"])

    def make(cid, fid, authority, otype, iso, penalty, issue=None):
        c = cmap[cid]
        fac = fmap.get(fid) if fid else None
        state = fac["state"] if fac else c["hq_state"]
        zone = STATES[state]["zone"]
        year = int(iso[:4])
        issue = issue or (_issue_for(rng, c["sector"], fac["type"]) if fac else sebi_issue(rng, iso))
        return dict(company_id=cid, facility_id=fid, authority=authority,
                    case_no=_case_no(rng, authority, state, otype, year, used_cases, fac["district"] if fac else "HQ"),
                    order_type=otype, date=iso, penalty_inr=float(penalty), status=_status_for(rng, otype, authority, iso),
                    summary=_reg_summary(rng, c, fac, authority, otype, penalty, issue, zone))

    # planted penalties
    for p in plan["regulatory_penalty"]:
        fac = fmap[p["facility_id"]]
        a, b = fy_range(p["fy"])
        iso = rand_date(rng, a + timedelta(days=30), b - timedelta(days=15)).isoformat()
        authority = rng.choice(["NGT", "NGT", "CPCB", STATES[fac["state"]]["board"]])
        otype = "environmental_compensation" if authority in ("NGT", "CPCB") else rng.choice(["environmental_compensation", "penalty"])
        rows.append(make(p["company_id"], p["facility_id"], authority, otype, iso, p["penalty"]))
    # random actions
    gen_ids = [c["company_id"] for c in companies if c["company_id"] not in DEMO_IDS]
    wts = [SECTOR_PROFILE[cmap[i]["sector"]]["reg_w"] * (1.6 if cmap[i]["market_cap_band"] == "Large" else 1.0) for i in gen_ids]
    n_rand = TARGETS["regulatory_actions"] - len(rows)
    fy_w = [0.09, 0.10, 0.15, 0.19, 0.22, 0.21, 0.04]
    for _ in range(n_rand):
        cid = rng.choices(gen_ids, weights=wts)[0]
        c = cmap[cid]
        r = rng.random()
        authority = ("SEBI" if (r < 0.07 or c["sector"] == "IT Services") else
                     "NGT" if r < 0.23 else "CPCB" if r < 0.38 else "MoEFCC" if r < 0.42 else "SPCB")
        fac = None
        if authority != "SEBI":
            facs = fac_by_c[cid]
            fw = [3.0 if template_for(c["sector"], f["type"])[5] or "mine" in f["type"] else 0.7 for f in facs]
            fac = rng.choices(facs, weights=fw)[0]
            if authority == "SPCB":
                authority = STATES[fac["state"]]["board"]
        k = rng.choices(range(7), weights=fy_w)[0]
        if k < 6:
            a, b = fy_range(FYS[k])
        else:
            a, b = date(2025, 4, 1), date(2025, 9, 30)
        iso = rand_date(rng, a, b).isoformat()
        if authority == "SEBI":
            otype = rng.choices(["warning", "penalty"], weights=[0.45, 0.55])[0]
        elif authority == "NGT":
            otype = rng.choices(["environmental_compensation", "penalty", "closure_direction", "warning"], weights=[0.65, 0.15, 0.1, 0.1])[0]
        elif authority == "CPCB":
            otype = rng.choices(["show_cause", "environmental_compensation", "closure_direction", "warning"], weights=[0.35, 0.3, 0.2, 0.15])[0]
        elif authority == "MoEFCC":
            otype = rng.choices(["show_cause", "penalty", "warning"], weights=[0.5, 0.3, 0.2])[0]
        else:
            otype = rng.choices(["show_cause", "warning", "closure_direction", "consent_revoked", "penalty", "environmental_compensation"],
                                weights=[0.40, 0.15, 0.15, 0.08, 0.12, 0.10])[0]
        if otype in ("penalty", "environmental_compensation"):
            penalty = _sample_penalty(rng, 5e5, 6e7) if authority == "SEBI" else _sample_penalty(rng)
            if authority == "SEBI":
                penalty = min(penalty, 6e6)
        else:
            penalty = 0.0
        rows.append(make(cid, fac["facility_id"] if fac else None, authority, otype, iso, penalty))
    rows.sort(key=lambda r: (r["date"], r["company_id"], r["case_no"]))
    for i, r in enumerate(rows, 1):
        r["action_id"] = f"REG-{i:05d}"
    return [dict(action_id=r["action_id"], **{k: v for k, v in r.items() if k != "action_id"}) for r in rows]


# ---------------------------------------------------------------------------
# OCEMS exceedances
# ---------------------------------------------------------------------------

def facility_limits(f: dict, sector: str) -> dict[str, tuple[float, str]]:
    """Deterministic per-facility prescribed limits (parameter -> (limit, unit))."""
    r = random.Random(f"{spec.SEED}:limits:{f['facility_id']}")
    kind = template_for(sector, f["type"])[5]
    if kind == "air":
        pm = 30.0 if (sector == "Cement" or r.random() < 0.4) else 50.0
        so2 = r.choice([100.0, 200.0, 200.0, 400.0, 600.0])
        nox = r.choice([300.0, 350.0, 450.0])
        return {"PM": (pm, "mg/Nm3"), "SO2": (so2, "mg/Nm3"), "NOx": (nox, "mg/Nm3")}
    if kind == "water":
        return {"BOD": (30.0, "mg/L"), "COD": (250.0, "mg/L"), "TSS": (100.0, "mg/L")}
    return {}


def _ocems_row(rng, fac, limits, param, iso):
    limit, unit = limits[param]
    reading = round(limit * (1.03 + min(rng.expovariate(1 / 0.35), 2.2)), 1)
    if reading <= limit:
        reading = round(limit + 0.1, 1)
    spcb = STATES[fac["state"]]["board"]
    return dict(facility_id=fac["facility_id"], date=iso, parameter=param, limit_value=limit, reading=reading, unit=unit,
                duration_h=round(min(72.0, rng.expovariate(1 / 6.0) + 0.25), 1),
                reported_to=rng.choice(["CPCB", spcb, spcb]))


def gen_ocems(rng: random.Random, companies, facilities, plan) -> list[dict]:
    csec = {c["company_id"]: c["sector"] for c in companies}
    fmap = {f["facility_id"]: f for f in facilities}
    out: list[dict] = []

    def pick_param(limits, sector, fac):
        names = list(limits)
        if names[0] == "PM":
            w = [0.55, 0.2, 0.25] if sector != "Power" else [0.4, 0.3, 0.3]
            if sector == "Cement":
                w = [0.65, 0.05, 0.3]
            return rng.choices(names, weights=w)[0]
        return rng.choices(names, weights=[0.35, 0.4, 0.25])[0]

    def add(fid, iso, param=None):
        fac = fmap[fid]
        lim = facility_limits(fac, csec[fac["company_id"]])
        p = param or pick_param(lim, csec[fac["company_id"]], fac)
        out.append(_ocems_row(rng, fac, lim, p, iso))

    def day_in(fy, lo_off=0, hi_off=0):
        a, b = fy_range(fy)
        return rand_date(rng, a + timedelta(days=lo_off), b - timedelta(days=hi_off)).isoformat()

    # demo companies
    for d in spec.DEMO_COMPANIES:
        if not d["in_db"]:
            continue
        ev = d["events"]["ocems_exceedances"]
        for i in range(ev["count"]):
            add(ev["facility_id"], day_in(ev["fy"]), ev["parameters"][0 if i < ev["count"] * 0.6 else -1])
    # allowed earlier-FY events for Vajra and Sahyadri (none for Kaveri; none in FY2025 elsewhere)
    for _ in range(3):
        add("FAC-0001", day_in("FY2023"), "PM")
    for _ in range(5):
        add("FAC-0002", day_in("FY2024"), rng.choice(["PM", "SO2"]))
    for _ in range(4):
        add("FAC-0006", rand_date(rng, date(2022, 11, 1), date(2023, 2, 5)).isoformat(), "PM")  # dust episode before CPCB direction
    for _ in range(2):
        add("FAC-0005", day_in("FY2024"), "PM")
    n_demo = len(out)
    # planted
    planted_n = 0
    for p in plan["ocems"]:
        for _ in range(p["n"]):
            add(p["facility_id"], day_in(p["fy"]))
            planted_n += 1
    planted_keys = {(p["facility_id"], p["fy"]) for p in plan["ocems"]}
    # background across non-demo heavy facilities
    cand = [f for f in facilities if f["company_id"] not in DEMO_IDS and template_for(csec[f["company_id"]], f["type"])[5]]
    fw = {f["facility_id"]: (0.0 if rng.random() < 0.38 else math.exp(rng.gauss(0, 1.0))) for f in cand}
    pairs, weights = [], []
    fy_w = [0.12, 0.14, 0.16, 0.18, 0.20, 0.20]
    for f in cand:
        for fy, w in zip(FYS, fy_w):
            if (f["facility_id"], fy) in planted_keys:
                continue
            pairs.append((f["facility_id"], fy))
            weights.append(fw[f["facility_id"]] * w)
    n_bg = TARGETS["ocems_exceedances"] - len(out)
    for fid, fy in rng.choices(pairs, weights=weights, k=n_bg):
        add(fid, day_in(fy))
    out.sort(key=lambda r: (r["date"], r["facility_id"], r["parameter"]))
    return [dict(event_id=f"OCE-{i:06d}", **r) for i, r in enumerate(out, 1)]


# ---------------------------------------------------------------------------
# land alerts
# ---------------------------------------------------------------------------

def gen_land_alerts(rng: random.Random, companies, facilities, plan) -> list[dict]:
    fpts = [(f["facility_id"], f["lat"], f["lon"]) for f in facilities]
    sk_pts = [(f["lat"], f["lon"]) for f in facilities if f["company_id"] in ("CMP-0002", "CMP-0003")]
    vaj_other = [(f["lat"], f["lon"]) for f in facilities if f["company_id"] == "CMP-0001" and f["facility_id"] != "FAC-0003"]
    fac3 = next(f for f in facilities if f["facility_id"] == "FAC-0003")
    out: list[dict] = []

    def nearest(lat, lon):
        best = min(((haversine_km(lat, lon, a, b), fid) for fid, a, b in fpts))
        return best

    def allowed(lat, lon, near_fac3_ok=False):
        if haversine_km(lat, lon, *KUTCH) < 15.5:
            return False
        if any(haversine_km(lat, lon, a, b) < 10.5 for a, b in sk_pts + vaj_other):
            return False
        if not near_fac3_ok and haversine_km(lat, lon, fac3["lat"], fac3["lon"]) < 5.5:
            return False
        return True

    def area():
        return round(max(0.1, min(40.0, rng.lognormvariate(math.log(1.8), 0.9))), 1)

    def emit(lat, lon, iso, ha):
        dist, fid = nearest(lat, lon)
        out.append(dict(lat=round(lat, 5), lon=round(lon, 5), alert_date=iso, area_ha=ha,
                        confidence=rng.choices(["nominal", "high", "highest"], weights=[0.35, 0.4, 0.25])[0],
                        source=rng.choice(["GLAD-L", "GLAD-S2", "RADD"]),
                        nearest_facility_id=fid if dist <= 25 else None,
                        distance_km=round(dist, 2) if dist <= 25 else None))

    # --- Vajra: exactly 14 alerts within 5 km of FAC-0003, summing to 126.4 ha, inside the spec window
    ev = spec.demo_by_id("CMP-0001")["events"]["land_alerts"]
    n = ev["count"]
    w = [rng.expovariate(1.0) + 0.25 for _ in range(n)]
    areas = [round(ev["total_ha"] * x / sum(w), 1) for x in w]
    areas[-1] = round(ev["total_ha"] - sum(areas[:-1]), 1)
    dates = [ev["from"]] + [rand_date(rng, date.fromisoformat(ev["from"]), date.fromisoformat(ev["to"])).isoformat() for _ in range(n - 2)] + [ev["to"]]
    rng.shuffle(dates)
    for ha, iso in zip(areas, dates):
        lat, lon = offset_point(fac3["lat"], fac3["lon"], 4.9 * math.sqrt(rng.random()) + 0.2, rng.uniform(0, 360))
        emit(lat, lon, iso, ha)
    # earlier / wider-ring alerts around Keonjhar (6-20 km away so they never count inside 5 km)
    for fy in FYS[:5]:
        a, b = fy_range(fy)
        for _ in range(rng.randint(2, 5)):
            lat, lon = offset_point(fac3["lat"], fac3["lon"], rng.uniform(6.0, 20.0), rng.uniform(0, 360))
            emit(lat, lon, rand_date(rng, a, b).isoformat(), area())
    for _ in range(3):
        lat, lon = offset_point(fac3["lat"], fac3["lon"], rng.uniform(6.0, 20.0), rng.uniform(0, 360))
        emit(lat, lon, rand_date(rng, date(2024, 4, 1), date(2025, 3, 31)).isoformat(), area())
    # --- planted clusters for generated companies
    planted_keys = {(p["facility_id"], p["fy"]) for p in plan["land_alerts"]}
    fmap = {f["facility_id"]: f for f in facilities}
    for p in plan["land_alerts"]:
        f = fmap[p["facility_id"]]
        a, b = fy_range(p["fy"])
        for _ in range(p["n"]):
            for _try in range(30):
                lat, lon = offset_point(f["lat"], f["lon"], 4.6 * math.sqrt(rng.random()) + 0.2, rng.uniform(0, 360))
                if allowed(lat, lon):
                    break
            emit(lat, lon, rand_date(rng, a, b).isoformat(), area())
    # --- baseline alerts around the other forest-adjacent facilities
    for f in facilities:
        if not f["forest_adjacent"] or f["company_id"] in DEMO_IDS:
            continue
        lam = rng.uniform(1.5, 6.5)
        for fy in FYS:
            if (f["facility_id"], fy) in planted_keys:
                continue
            a, b = fy_range(fy)
            for _ in range(_poisson(rng, lam)):
                for _try in range(30):
                    lat, lon = offset_point(f["lat"], f["lon"], min(24.0, rng.expovariate(1 / 6.0) + 0.4), rng.uniform(0, 360))
                    if allowed(lat, lon):
                        break
                emit(lat, lon, rand_date(rng, a, b).isoformat(), area())
    # --- background noise across forested states
    total_w = sum(bx[5] for bx in FOREST_BOXES)
    n_bg = max(0, TARGETS["land_alerts"] - len(out))
    while n_bg > 0:
        bx = rng.choices(FOREST_BOXES, weights=[b[5] for b in FOREST_BOXES])[0]
        lat, lon = rng.uniform(bx[1], bx[2]), rng.uniform(bx[3], bx[4])
        if not allowed(lat, lon):
            continue
        k = rng.choices(range(6), weights=[0.14, 0.15, 0.16, 0.17, 0.19, 0.19])[0]
        a, b = fy_range(FYS[k])
        emit(lat, lon, rand_date(rng, a, b).isoformat(), area())
        n_bg -= 1
    out.sort(key=lambda r: (r["alert_date"], r["lat"], r["lon"]))
    return [dict(alert_id=f"LA-{i:06d}", **r) for i, r in enumerate(out, 1)]


# ---------------------------------------------------------------------------
# RE certificates
# ---------------------------------------------------------------------------

ELEC_SHARE = {s: SECTOR_PROFILE[s]["elec_share"] for s in SECTOR_PROFILE}


def _split(rng, total: float, k: int, quantum: float = 100.0) -> list[float]:
    w = [rng.uniform(0.5, 1.5) for _ in range(k)]
    parts = [round(total * x / sum(w) / quantum) * quantum for x in w]
    parts[-1] = total - sum(parts[:-1])
    return parts


def gen_re_certificates(rng: random.Random, companies, brsr, plan) -> list[dict]:
    brsr_by = {(b["company_id"], b["fy"]): b for b in brsr}
    out: list[dict] = []

    def ret_date(v):
        a, b = date(v + 1, 1, 15), min(date(v + 1, 9, 30), date(2026, 6, 30))
        return rand_date(rng, a, b).isoformat()

    def add(cid, registry, mwh, v, status, retired_on=None):
        out.append(dict(company_id=cid, registry=registry, mwh=float(mwh), vintage_year=v, status=status, retired_on=retired_on))

    # demo companies
    for cid in sorted(DEMO_IDS):
        ev = spec.demo_by_id(cid)["events"]["re_certificates"]
        reg = rng.choice(["I-REC", "REC Registry India"])
        for v, vol in {"CMP-0001": [(2021, 80000), (2022, 120000), (2023, 200000)],
                       "CMP-0002": [(2022, 150000), (2023, 190000)], "CMP-0003": [(2021, 40000), (2022, 60000), (2023, 80000)]}[cid]:
            add(cid, reg, vol, v, "retired", ret_date(v))
        for part in _split(rng, ev["retired_mwh"], 3 if cid != "CMP-0003" else 2, 5000.0):
            add(cid, reg, part, ev["vintage"], "retired", ret_date(ev["vintage"]))
        if ev["active_mwh"]:
            for part in _split(rng, ev["active_mwh"], 4, 10000.0):
                add(cid, reg, part, ev["vintage"], "active")
    planted = {p["company_id"]: p for p in plan["rec_unretired"]}
    for c in companies:
        cid = c["company_id"]
        if cid in DEMO_IDS:
            continue
        if cid not in planted and rng.random() > 0.72:
            continue
        reg_pref = "I-REC" if c["sector"] in ("IT Services", "FMCG", "Automotive", "Pharmaceuticals") else "REC Registry India"
        for v in range(2020, 2025):
            if cid not in planted and rng.random() > 0.85:
                continue
            b = brsr_by[(cid, f"FY{v + 1}")]
            elec = b["energy_gj"] * ELEC_SHARE[c["sector"]] / 3.6
            re_mwh = elec * b["re_pct"] / 100.0
            total = max(500.0, round(re_mwh * rng.uniform(0.1, 0.7) / 100) * 100)
            registry = reg_pref if rng.random() < 0.8 else ("REC Registry India" if reg_pref == "I-REC" else "I-REC")
            if cid in planted and v == 2024:
                p = planted[cid]
                retired = max(500.0, round(re_mwh * p["retired_share"] / 100) * 100)
                active = round(retired * p["active_mult"] / 100) * 100
                for part in _split(rng, retired, 2):
                    add(cid, registry, part, v, "retired", ret_date(v))
                for part in _split(rng, active, 2):
                    add(cid, registry, part, v, "active")
                continue
            k = rng.choice([1, 1, 2, 2, 3])
            for part in _split(rng, total, k):
                if part <= 0:
                    continue
                r = rng.random()
                st = ("retired" if r < (0.88 if v <= 2022 else 0.8) else
                      "transferred" if r < (0.94 if v <= 2022 else 0.9) else "active")
                if cid in planted and v < 2024:
                    st = "retired"
                add(cid, registry, part, v, st, ret_date(v) if st == "retired" else None)
    out.sort(key=lambda r: (r["company_id"], r["vintage_year"], r["status"], r["mwh"]))
    return [dict(cert_id=f"REC-{i:06d}", **r) for i, r in enumerate(out, 1)]


# ---------------------------------------------------------------------------
# audited reports (assurance statements)
# ---------------------------------------------------------------------------

STANDARDS = [
    "ISAE 3000 (Revised), Assurance Engagements Other than Audits or Reviews of Historical Financial Information, and ISAE 3410, Assurance Engagements on Greenhouse Gas Statements, issued by the IAASB",
    "SAE 3000 and the ICAI Guidance Note on Reporting on BRSR Core, which are consistent with ISAE 3000 (Revised)",
    "ISAE 3000 (Revised) and, for the attestation of controls over reported data, the principles of SSAE No. 21 issued by the AICPA",
]
SCOPES_LIMITED = [
    "BRSR Core: GHG footprint (Scope 1 and 2), water, energy, waste, employee safety and gender diversity KPIs",
    "BRSR Core: GHG footprint, energy, water, waste management and safety indicators",
    "BRSR Core: GHG, water and energy footprint, waste, employee safety and inclusive development KPIs",
]
SCOPES_REASONABLE = [
    "BRSR Core: all nine attributes, including Scope 1 and 2 emissions, water, energy, waste, safety, gender diversity and openness of business",
    "BRSR Core: the full set of nine ESG attributes, including Scope 1 and 2 emissions, water, energy, waste and safety",
]
QUALIFIED = [
    "Water withdrawal data for one captive unit were derived from estimates because meter calibration records were not available for part of the year",
    "Fugitive emissions were estimated using default emission factors without site-specific verification for one facility",
    "Waste recovered at one facility could not be reconciled to third-party weighbridge records for the full period",
    "Lost-time injury data for contract workers at one site were compiled from incomplete records",
    "Scope 2 location-based emissions for two sites used grid emission factors from a superseded publication",
]


def _audit_text(rng, c, fy, b, facility_names, auditor, atype, opinion, scope, qualified) -> str:
    year = int(fy[2:])
    name = c["name"]
    std = rng.choice(STANDARDS)
    lim = atype == "limited"
    p = []
    p.append(f"Independent {'Limited' if lim else 'Reasonable'} Assurance Report to the Board of Directors of {name}. "
             f"We were engaged by {name} (the Company) to perform a {atype} assurance engagement on the BRSR Core "
             f"information for the year ended 31 March {year} (the Subject Matter Information), as reported in its BRSR. The scope of our engagement covered {scope}.")
    p.append(f"Management is responsible for preparing the Subject Matter Information under the SEBI BRSR Core framework and for related internal controls. "
             f"Our responsibility is to express a {'limited' if lim else 'reasonable'} assurance conclusion. We performed the engagement in accordance with "
             f"{std}, and complied with the applicable independence and quality control requirements.")
    site = rng.choice(facility_names)
    if lim:
        proc = (f"A limited assurance engagement is substantially less in extent than a reasonable assurance engagement. Our procedures "
                f"comprised inquiries of management, analytical procedures, a visit to {site}, and testing of a sample of "
                f"supporting records. We reconciled reported Scope 1 emissions of {b['scope1_tco2e']:,.0f} tCO2e and Scope 2 emissions "
                f"of {b['scope2_tco2e']:,.0f} tCO2e to the underlying calculation workbooks.")
    else:
        proc = (f"Our procedures included evaluating the design and operating effectiveness of controls over data collection, "
                f"visits to {site} and other selected sites, re-performance of calculations, and substantive testing of source records. "
                f"We tested reported Scope 1 emissions of {b['scope1_tco2e']:,.0f} tCO2e and Scope 2 emissions of "
                f"{b['scope2_tco2e']:,.0f} tCO2e against meter readings, fuel records and utility invoices.")
    p.append(proc)
    if opinion == "unmodified":
        if lim:
            p.append(f"Conclusion: based on our procedures, nothing has come to our attention that causes us to believe that the Subject "
                     f"Matter Information for {fy_label(fy)} is not prepared, in all material respects, in accordance with the BRSR Core framework.")
        else:
            p.append(f"Opinion: in our opinion, the Subject Matter Information for {fy_label(fy)} is prepared, in all material respects, "
                     f"in accordance with the BRSR Core framework.")
    else:
        p.append(f"Basis for qualified conclusion: {qualified}. Except for the effect of this matter, "
                 f"{'nothing has come to our attention that causes us to believe that' if lim else 'in our opinion,'} the Subject Matter "
                 f"Information for {fy_label(fy)} {'is not' if lim else 'is'} prepared, in all material respects, in accordance with the BRSR Core framework.")
    p.append(f"Inherent limitations apply to non-financial data and emission estimates. This report is intended solely for the Board of Directors and for "
             f"submission to the stock exchanges. {auditor}, Chartered Accountants.")
    return "\n\n".join(p)


def fy_label(fy: str) -> str:
    y = int(fy[2:])
    return f"FY{y - 1}-{str(y)[2:]}"


def gen_audited_reports(rng: random.Random, companies, facilities, brsr) -> list[dict]:
    fac_names = defaultdict(list)
    for f in facilities:
        fac_names[f["company_id"]].append(f["name"])
    cmap = {c["company_id"]: c for c in companies}
    out = []
    for b in brsr:
        if b["assurance_type"] == "none":
            continue
        c = cmap[b["company_id"]]
        opinion = "unmodified" if (b["company_id"] in DEMO_IDS or rng.random() > 0.14) else "qualified"
        qualified = rng.choice(QUALIFIED) if opinion == "qualified" else None
        scope = rng.choice(SCOPES_LIMITED if b["assurance_type"] == "limited" else SCOPES_REASONABLE)
        text = _audit_text(rng, c, b["fy"], b, fac_names[c["company_id"]], b["assurance_provider"], b["assurance_type"],
                           opinion, scope, qualified)
        out.append(dict(report_id=f"AUD-{b['company_id']}-{b['fy']}", company_id=b["company_id"], fy=b["fy"],
                        auditor=b["assurance_provider"], assurance_type=b["assurance_type"], opinion=opinion,
                        scope_covered=scope, qualified_items=qualified, text=text))
    return out


# ---------------------------------------------------------------------------
# planted events file
# ---------------------------------------------------------------------------

def build_planted_events(tables: dict[str, list[dict]], plan: dict) -> list[dict]:
    cmap = {c["company_id"]: c for c in tables["companies"]}
    fmap = {f["facility_id"]: f for f in tables["facilities"]}
    out: list[dict] = []
    for p in plan["regulatory_penalty"]:
        a, b = fy_range(p["fy"])
        rows = [r for r in tables["regulatory_actions"] if r["company_id"] == p["company_id"] and a.isoformat() <= r["date"] <= b.isoformat()]
        out.append(dict(company_id=p["company_id"], company_name=cmap[p["company_id"]]["name"], metric="regulatory_actions",
                        fy=p["fy"], kind="regulatory_penalty", true_value=sum(r["penalty_inr"] for r in rows), unit="INR",
                        refs=[r["action_id"] for r in rows], table="regulatory_actions",
                        details=dict(n_actions=len(rows), facility_id=p["facility_id"])))
    for p in plan["ocems"]:
        a, b = fy_range(p["fy"])
        fids = {f["facility_id"] for f in tables["facilities"] if f["company_id"] == p["company_id"]}
        rows = [r for r in tables["ocems_exceedances"] if r["facility_id"] in fids and a.isoformat() <= r["date"] <= b.isoformat()]
        out.append(dict(company_id=p["company_id"], company_name=cmap[p["company_id"]]["name"], metric="ocems_exceedances",
                        fy=p["fy"], kind="ocems", true_value=len(rows), unit="count", refs=[r["event_id"] for r in rows],
                        table="ocems_exceedances",
                        details=dict(facility_id=p["facility_id"], parameters=sorted({r["parameter"] for r in rows}))))
    for p in plan["land_alerts"]:
        a, b = fy_range(p["fy"])
        f = fmap[p["facility_id"]]
        rows = [r for r in tables["land_alerts"] if a.isoformat() <= r["alert_date"] <= b.isoformat()
                and haversine_km(f["lat"], f["lon"], r["lat"], r["lon"]) <= 5.0]
        out.append(dict(company_id=p["company_id"], company_name=cmap[p["company_id"]]["name"], metric="deforestation_ha",
                        fy=p["fy"], kind="land_alerts", true_value=round(sum(r["area_ha"] for r in rows), 1), unit="ha",
                        refs=[r["alert_id"] for r in rows], table="land_alerts",
                        details=dict(facility_id=p["facility_id"], radius_km=5, n_alerts=len(rows))))
    for p in plan["rec_unretired"]:
        rows = [r for r in tables["re_certificates"] if r["company_id"] == p["company_id"] and r["vintage_year"] == 2024]
        retired = sum(r["mwh"] for r in rows if r["status"] == "retired")
        active = sum(r["mwh"] for r in rows if r["status"] == "active")
        out.append(dict(company_id=p["company_id"], company_name=cmap[p["company_id"]]["name"], metric="rec_retirement",
                        fy="FY2025", kind="rec_unretired", true_value=retired, unit="MWh", refs=[r["cert_id"] for r in rows],
                        table="re_certificates", details=dict(vintage=2024, retired_mwh=retired, active_mwh=active)))
    return out


# ---------------------------------------------------------------------------
# write + main
# ---------------------------------------------------------------------------

TABLE_ORDER = ["companies", "facilities", "brsr_filings", "facility_ghg", "ocems_exceedances", "regulatory_actions",
               "land_alerts", "re_certificates", "audited_reports", "news_articles"]


def write_db(path: Path, tables: dict[str, list[dict]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA_PATH.read_text())
        for t in TABLE_ORDER:
            rows = tables[t]
            if not rows:
                continue
            cols = list(rows[0].keys())
            con.executemany(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                            [tuple(r[c] for c in cols) for r in rows])
        con.commit()
    finally:
        con.close()


def build_tables() -> tuple[dict[str, list[dict]], dict]:
    from .news_gen import gen_news_articles  # local import: news depends on every other table

    companies = gen_companies(_rng("companies"))
    facilities = gen_facilities(_rng("facilities"), companies)
    brsr = gen_brsr(_rng("brsr"), companies, facilities)
    ghg = gen_facility_ghg(_rng("facility_ghg"), companies, facilities, brsr)
    plan = make_plan(_rng("plan"), companies, facilities, brsr)
    regs = gen_regulatory_actions(_rng("regulatory"), companies, facilities, plan)
    ocems = gen_ocems(_rng("ocems"), companies, facilities, plan)
    alerts = gen_land_alerts(_rng("land_alerts"), companies, facilities, plan)
    recs = gen_re_certificates(_rng("rec"), companies, brsr, plan)
    audits = gen_audited_reports(_rng("audits"), companies, facilities, brsr)
    tables = dict(companies=companies, facilities=facilities, brsr_filings=brsr, facility_ghg=ghg,
                  ocems_exceedances=ocems, regulatory_actions=regs, land_alerts=alerts, re_certificates=recs,
                  audited_reports=audits)
    tables["news_articles"] = gen_news_articles(_rng("news"), tables, plan)
    return tables, plan


def build(out_path: str | Path | None = None, verbose: bool = True) -> dict[str, int]:
    out = Path(out_path) if out_path else DEFAULT_DB
    tables, plan = build_tables()
    write_db(out, tables)
    planted = build_planted_events(tables, plan)
    (out.parent / "planted_events.json").write_text(json.dumps(planted, indent=2))
    counts = {t: len(tables[t]) for t in TABLE_ORDER}
    if verbose:
        print(f"wrote {out}")
        for t, n in counts.items():
            print(f"  {t:20s} {n:6d}")
        print(f"  planted_events.json  {len(planted):6d} (companies: {len({p['company_id'] for p in planted})})")
    return counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the synthetic ESG world database")
    ap.add_argument("--out", default=None, help="output sqlite path (default data/world/world.db)")
    args = ap.parse_args(argv)
    build(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
