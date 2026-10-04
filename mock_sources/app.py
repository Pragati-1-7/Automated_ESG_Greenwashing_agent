"""
mock_sources/app.py

A separate FastAPI service shaped like the external APIs a real ESG analyst
would hit. Run it with:

    uvicorn mock_sources.app:app --port 8100

Every response carries `source`, `tier` and `endpoint` so the calling agent
can cite exactly where a fact came from. All data is synthetic.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from mock_sources import db

app = FastAPI(
    title="Mock ESG Data Sources",
    description="Synthetic stand-ins for SEBI BRSR, CPCB OCEMS, NGT/SPCB orders, GFW alerts, REC registry, "
                "assurance statements and news. ALL DATA IS FICTIONAL.",
    version="1.0.0",
)

FY_RANGE = {f"FY{y}": (f"{y - 1}-04-01", f"{y}-03-31") for y in range(2018, 2027)}


def _envelope(source: str, endpoint: str, rows: list[dict], **meta) -> dict:
    return {"source": source, "tier": db.TABLES.get(source, {}).get("tier"), "endpoint": endpoint,
            "count": len(rows), "rows": rows, **meta}


def _window(fy: Optional[str], date_from: Optional[str], date_to: Optional[str]) -> tuple[str, str]:
    if fy:
        if fy not in FY_RANGE:
            raise HTTPException(400, f"Unknown fiscal year {fy!r}; use FY2020..FY2025")
        return FY_RANGE[fy]
    return date_from or "1900-01-01", date_to or "2999-12-31"


def _company_or_404(company_id: str) -> dict:
    c = db.one("SELECT * FROM companies WHERE company_id = ?", (company_id,))
    if not c:
        raise HTTPException(404, f"Unknown company_id {company_id}")
    return c


@app.get("/health")
def health():
    counts = {t: db.one(f"SELECT COUNT(*) AS n FROM {t}")["n"] for t in db.TABLES}
    return {"status": "ok", "tables": counts}


# ---------------------------------------------------------------- companies
@app.get("/companies/resolve")
def resolve(name: str = Query(..., min_length=2), limit: int = 5):
    return {"query": name, "candidates": db.resolve_company(name, limit)}


@app.get("/companies/{company_id}")
def company(company_id: str):
    return _company_or_404(company_id)


@app.get("/companies/{company_id}/facilities")
def facilities(company_id: str):
    _company_or_404(company_id)
    rows = db.rows("SELECT * FROM facilities WHERE company_id = ? ORDER BY facility_id", (company_id,))
    return _envelope("facilities", f"/companies/{company_id}/facilities", rows)


# ---------------------------------------------------------------- SEBI BRSR (tier 1)
@app.get("/sebi/brsr")
def brsr(company_id: str, fy: Optional[str] = None):
    _company_or_404(company_id)
    if fy:
        rows = db.rows("SELECT * FROM brsr_filings WHERE company_id = ? AND fy = ?", (company_id, fy))
    else:
        rows = db.rows("SELECT * FROM brsr_filings WHERE company_id = ? ORDER BY fy", (company_id,))
    return _envelope("brsr_filings", f"/sebi/brsr?company_id={company_id}" + (f"&fy={fy}" if fy else ""), rows)


@app.get("/ghg/facility")
def facility_ghg(company_id: str, fy: Optional[str] = None):
    _company_or_404(company_id)
    sql = ("SELECT g.*, f.name AS facility_name FROM facility_ghg g JOIN facilities f USING(facility_id) "
           "WHERE f.company_id = ?")
    params: tuple = (company_id,)
    if fy:
        sql += " AND g.fy = ?"
        params += (fy,)
    rows = db.rows(sql + " ORDER BY g.fy, g.facility_id", params)
    return _envelope("facility_ghg", f"/ghg/facility?company_id={company_id}" + (f"&fy={fy}" if fy else ""), rows)


# ---------------------------------------------------------------- CPCB OCEMS (tier 2)
@app.get("/cpcb/ocems/exceedances")
def ocems(company_id: str, fy: Optional[str] = None, date_from: Optional[str] = None,
          date_to: Optional[str] = None, parameter: Optional[str] = None):
    _company_or_404(company_id)
    lo, hi = _window(fy, date_from, date_to)
    sql = ("SELECT e.*, f.name AS facility_name FROM ocems_exceedances e JOIN facilities f USING(facility_id) "
           "WHERE f.company_id = ? AND e.date BETWEEN ? AND ?")
    params: tuple = (company_id, lo, hi)
    if parameter:
        sql += " AND e.parameter = ?"
        params += (parameter,)
    rows = db.rows(sql + " ORDER BY e.date", params)
    return _envelope("ocems_exceedances", f"/cpcb/ocems/exceedances?company_id={company_id}&from={lo}&to={hi}",
                     rows, window={"from": lo, "to": hi})


# ---------------------------------------------------------------- NGT / CPCB / SPCB / SEBI (tier 2)
@app.get("/regulatory/actions")
def regulatory(company_id: str, fy: Optional[str] = None, date_from: Optional[str] = None,
               date_to: Optional[str] = None, authority: Optional[str] = None):
    _company_or_404(company_id)
    lo, hi = _window(fy, date_from, date_to)
    sql = "SELECT * FROM regulatory_actions WHERE company_id = ? AND date BETWEEN ? AND ?"
    params: tuple = (company_id, lo, hi)
    if authority:
        sql += " AND authority = ?"
        params += (authority,)
    rows = db.rows(sql + " ORDER BY date", params)
    return _envelope("regulatory_actions", f"/regulatory/actions?company_id={company_id}&from={lo}&to={hi}",
                     rows, window={"from": lo, "to": hi})


# ---------------------------------------------------------------- GFW alerts (tier 3)
@app.get("/gfw/alerts/near")
def alerts_near(lat: float, lon: float, radius_km: float = 5.0, fy: Optional[str] = None,
                date_from: Optional[str] = None, date_to: Optional[str] = None):
    lo, hi = _window(fy, date_from, date_to)
    d = radius_km / 111.0 * 1.5
    cand = db.rows("SELECT * FROM land_alerts WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? "
                   "AND alert_date BETWEEN ? AND ?", (lat - d, lat + d, lon - d * 1.2, lon + d * 1.2, lo, hi))
    rows = []
    for a in cand:
        km = db.haversine_km(lat, lon, a["lat"], a["lon"])
        if km <= radius_km:
            rows.append({**a, "distance_from_point_km": round(km, 2)})
    rows.sort(key=lambda r: r["alert_date"])
    return _envelope("land_alerts", f"/gfw/alerts/near?lat={lat}&lon={lon}&radius_km={radius_km}&from={lo}&to={hi}",
                     rows, total_area_ha=round(sum(r["area_ha"] for r in rows), 2), window={"from": lo, "to": hi})


@app.get("/gfw/alerts/company")
def alerts_company(company_id: str, radius_km: float = 5.0, fy: Optional[str] = None,
                   date_from: Optional[str] = None, date_to: Optional[str] = None):
    _company_or_404(company_id)
    out = []
    for f in db.rows("SELECT * FROM facilities WHERE company_id = ?", (company_id,)):
        res = alerts_near(f["lat"], f["lon"], radius_km, fy, date_from, date_to)
        for r in res["rows"]:
            out.append({**r, "facility_id": f["facility_id"], "facility_name": f["name"]})
    lo, hi = _window(fy, date_from, date_to)
    return _envelope("land_alerts", f"/gfw/alerts/company?company_id={company_id}&radius_km={radius_km}&from={lo}&to={hi}",
                     out, total_area_ha=round(sum(r["area_ha"] for r in out), 2), window={"from": lo, "to": hi})


# ---------------------------------------------------------------- REC registry (tier 3)
@app.get("/registry/rec")
def rec(company_id: str, vintage: Optional[int] = None):
    _company_or_404(company_id)
    sql, params = "SELECT * FROM re_certificates WHERE company_id = ?", (company_id,)
    if vintage:
        sql += " AND vintage_year = ?"
        params += (vintage,)
    rows = db.rows(sql + " ORDER BY vintage_year, cert_id", params)
    totals: dict[str, float] = {}
    for r in rows:
        totals[r["status"]] = totals.get(r["status"], 0) + r["mwh"]
    return _envelope("re_certificates", f"/registry/rec?company_id={company_id}" + (f"&vintage={vintage}" if vintage else ""),
                     rows, totals_mwh=totals)


# ---------------------------------------------------------------- assurance (tier 3)
@app.get("/assurance/statements")
def assurance(company_id: str, fy: Optional[str] = None):
    _company_or_404(company_id)
    sql, params = "SELECT * FROM audited_reports WHERE company_id = ?", (company_id,)
    if fy:
        sql += " AND fy = ?"
        params += (fy,)
    rows = db.rows(sql + " ORDER BY fy", params)
    return _envelope("audited_reports", f"/assurance/statements?company_id={company_id}" + (f"&fy={fy}" if fy else ""), rows)


# ---------------------------------------------------------------- news wire (tier 4/5)
@app.get("/news/search")
def news(q: str = Query(..., min_length=2), company_id: Optional[str] = None, k: int = 5,
         date_from: Optional[str] = None, date_to: Optional[str] = None):
    hits = db.text_search(q, company_id=company_id, k=k, kind="news", date_from=date_from, date_to=date_to)
    return _envelope("news_articles", f"/news/search?q={q}" + (f"&company_id={company_id}" if company_id else ""), hits)


# ---------------------------------------------------------------- generic table browser
@app.get("/tables")
def tables():
    return {"tables": [{"name": t, "rows": db.one(f"SELECT COUNT(*) AS n FROM {t}")["n"], **meta}
                       for t, meta in db.TABLES.items()]}


@app.get("/tables/{table}")
def table_rows(table: str, limit: int = Query(50, le=500), offset: int = 0, company_id: Optional[str] = None):
    if table not in db.TABLES:
        raise HTTPException(404, f"Unknown table {table}")
    has_company = table not in ("land_alerts", "ocems_exceedances", "facility_ghg")
    where, params = "", ()
    if company_id and has_company:
        where, params = " WHERE company_id = ?", (company_id,)
    total = db.one(f"SELECT COUNT(*) AS n FROM {table}{where}", params)["n"]
    rows = db.rows(f"SELECT * FROM {table}{where} LIMIT ? OFFSET ?", params + (limit, offset))
    return {"table": table, "total": total, "rows": rows}
