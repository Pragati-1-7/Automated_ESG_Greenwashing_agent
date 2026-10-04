"""Read-only access to data/world/world.db plus a BM25 index for text search.

Pure functions over a sqlite connection; no business logic about claims.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import threading
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "world" / "world.db"

TABLES = {
    "companies": {"tier": None, "description": "Listed-company master (fictional), CIN, sector, HQ"},
    "facilities": {"tier": None, "description": "Plants, mines and sites with coordinates and SPCB consent numbers"},
    "brsr_filings": {"tier": 1, "description": "SEBI BRSR Core style annual filings FY2020-FY2025"},
    "facility_ghg": {"tier": 1, "description": "Facility-level GHG reporting (CO2, CH4, N2O)"},
    "ocems_exceedances": {"tier": 2, "description": "CPCB online continuous emission monitoring exceedance events"},
    "regulatory_actions": {"tier": 2, "description": "NGT, CPCB, state board and SEBI orders and penalties"},
    "land_alerts": {"tier": 3, "description": "GFW-style integrated forest-loss alerts with coordinates"},
    "re_certificates": {"tier": 3, "description": "Renewable energy certificate registry (I-REC / REC India)"},
    "audited_reports": {"tier": 3, "description": "Independent assurance statements on BRSR Core"},
    "news_articles": {"tier": 5, "description": "News wire and company press releases (tier 4 for PR)"},
}


def db_path() -> Path:
    return Path(os.environ.get("WORLD_DB_PATH", DEFAULT_DB))


_local = threading.local()


def conn() -> sqlite3.Connection:
    """One read-only connection per thread (FastAPI runs sync endpoints in a thread pool)."""
    path = str(db_path())
    cache = getattr(_local, "conns", None)
    if cache is None:
        cache = _local.conns = {}
    if path not in cache:
        c = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        c.row_factory = sqlite3.Row
        cache[path] = c
    return cache[path]


def rows(sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn().execute(sql, params).fetchall()]


def one(sql: str, params: tuple = ()) -> dict | None:
    r = conn().execute(sql, params).fetchone()
    return dict(r) if r else None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Company name resolution (entity resolution over name + aliases + CIN)
# ---------------------------------------------------------------------------

_SUFFIX = re.compile(r"\b(ltd|limited|pvt|private|inc|plc|co|company|industries|the)\b\.?", re.I)


def _norm(name: str) -> str:
    s = name.lower().replace("&", " and ")
    s = _SUFFIX.sub(" ", s)
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", s)).strip()


_GENERIC = {"steel", "power", "cement", "cements", "renewable", "renewables", "energy", "textiles", "textile",
            "threads", "foods", "agro", "chemicals", "chemical", "pharma", "pharmaceuticals", "auto", "components",
            "mining", "minerals", "technologies", "systems", "solutions", "and", "india", "group", "polymers",
            "infra", "metals", "global", "services", "labs", "motors", "beverages", "dyes", "paper", "mills"}


def _name_score(q: str, nn: str) -> float:
    """Similarity that weights DISTINCTIVE tokens: two companies that only share
    generic words ('Renewable', 'Power') must not match."""
    qt, nt = set(q.split()), set(nn.split())
    qd, nd = qt - _GENERIC, nt - _GENERIC
    if not qd or not nd:
        return 0.6 * SequenceMatcher(None, q, nn).ratio()
    distinct = len(qd & nd) / len(qd | nd)
    if distinct == 0:
        return min(0.45, 0.5 * SequenceMatcher(None, q, nn).ratio())
    generic = len((qt & nt) - qd) / max(1, len((qt | nt) - (qd | nd)))
    return round(min(1.0, 0.75 * distinct + 0.15 * generic + 0.1 * SequenceMatcher(None, q, nn).ratio()), 3)


def resolve_company(query: str, limit: int = 5) -> list[dict]:
    q = _norm(query)
    if not q:
        return []
    out = []
    for c in rows("SELECT * FROM companies"):
        names = [c["name"], c["short_name"], *json.loads(c["aliases"] or "[]")]
        best = 0.0
        for n in names:
            nn = _norm(n)
            if not nn:
                continue
            score = _name_score(q, nn)
            best = max(best, score)
        if query.strip().upper() == c["cin"]:
            best = 1.0
        out.append({**c, "aliases": json.loads(c["aliases"] or "[]"), "match_score": round(best, 3)})
    out.sort(key=lambda r: r["match_score"], reverse=True)
    return out[:limit]


# ---------------------------------------------------------------------------
# BM25 text search over news + assurance statements
# ---------------------------------------------------------------------------

def _tok(t: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", t.lower()) if w]


@lru_cache(maxsize=2)
def _text_index(path: str):
    docs = []
    for r in rows("SELECT * FROM news_articles"):
        docs.append({"kind": "news", "id": r["article_id"], "company_id": r["company_id"],
                     "tier": r["outlet_tier"], "date": r["published_on"], "title": r["headline"],
                     "outlet": r["outlet"], "text": r["body"]})
    for r in rows("SELECT * FROM audited_reports"):
        docs.append({"kind": "assurance", "id": r["report_id"], "company_id": r["company_id"],
                     "tier": 3, "date": r["fy"], "title": f"{r['auditor']} - {r['assurance_type']} assurance {r['fy']}",
                     "outlet": r["auditor"], "text": r["text"]})
    bm = BM25Okapi([_tok(d["title"] + " " + d["text"]) for d in docs])
    return docs, bm


def text_search(q: str, company_id: str | None = None, k: int = 5, kind: str | None = None,
                date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    docs, bm = _text_index(str(db_path()))
    scores = bm.get_scores(_tok(q))
    ranked = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)
    top = max(scores) if len(scores) else 0
    out = []
    for i in ranked:
        d = docs[i]
        if scores[i] <= 0:
            break
        if company_id and d["company_id"] != company_id:
            continue
        if kind and d["kind"] != kind:
            continue
        if d["kind"] == "news" and date_from and d["date"] < date_from:
            continue
        if d["kind"] == "news" and date_to and d["date"] > date_to:
            continue
        out.append({**d, "score": round(scores[i] / top, 4) if top else 0.0})
        if len(out) >= k:
            break
    return out
