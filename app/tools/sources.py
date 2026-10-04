"""
app/tools/sources.py

Tool layer over the mock_sources service. Each tool is a thin async function:
HTTP request -> (ToolCall record, JSON payload). Agents only ever reach data
through these tools, so every fact in a verdict has an endpoint behind it.

MOCK_SOURCES_URL=inproc (default) mounts the mock_sources ASGI app in-process
(no second server needed); set it to http://127.0.0.1:8100 to call a real
running service.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.events import emit
from app.core.models import ToolCall


def _client() -> httpx.AsyncClient:
    url = settings().mock_sources_url
    if url == "inproc":
        from mock_sources.app import app as mock_app
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=mock_app), base_url="http://mock-sources",
                                 timeout=30)
    return httpx.AsyncClient(base_url=url, timeout=30)


async def call(tool: str, path: str, params: dict[str, Any], claim_id: str | None = None,
               agent: str = "investigator") -> tuple[ToolCall, dict]:
    params = {k: v for k, v in params.items() if v is not None}
    emit(agent, "tool_call", f"{tool}({', '.join(f'{k}={v}' for k, v in params.items())})", claim_id,
         {"tool": tool, "path": path, "args": params})
    t0 = time.perf_counter()
    try:
        async with _client() as c:
            r = await c.get(path, params=params)
        ms = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 404:
            tc = ToolCall(tool=tool, args=params, status="empty", latency_ms=ms, result_count=0)
            emit(agent, "tool_result", f"{tool}: not found", claim_id, {"status": "empty"})
            return tc, {}
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPError as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        emit(agent, "error", f"{tool} failed: {exc}", claim_id)
        return ToolCall(tool=tool, args=params, status="error", latency_ms=ms, result_count=0), {}
    n = data.get("count", len(data.get("candidates", [])) if "candidates" in data else 1)
    tc = ToolCall(tool=tool, args=params, status="ok" if n else "empty", latency_ms=ms, result_count=n)
    emit(agent, "tool_result", f"{tool}: {n} record(s)", claim_id, {"count": n, "endpoint": data.get("endpoint")})
    return tc, data


# Named tools ---------------------------------------------------------------

async def resolve_company(name: str):
    return await call("resolve_company", "/companies/resolve", {"name": name}, agent="resolver")


async def facilities(company_id: str, claim_id=None):
    return await call("list_facilities", f"/companies/{company_id}/facilities", {}, claim_id, agent="resolver")


async def brsr(company_id: str, fy: str | None = None, claim_id=None):
    return await call("sebi_brsr_filings", "/sebi/brsr", {"company_id": company_id, "fy": fy}, claim_id)


async def facility_ghg(company_id: str, fy: str | None = None, claim_id=None):
    return await call("facility_ghg_registry", "/ghg/facility", {"company_id": company_id, "fy": fy}, claim_id)


async def ocems(company_id: str, fy: str | None = None, claim_id=None):
    return await call("cpcb_ocems_exceedances", "/cpcb/ocems/exceedances", {"company_id": company_id, "fy": fy}, claim_id)


async def regulatory(company_id: str, fy: str | None = None, claim_id=None):
    return await call("regulatory_actions", "/regulatory/actions", {"company_id": company_id, "fy": fy}, claim_id)


async def alerts_company(company_id: str, fy: str | None = None, radius_km: float = 5.0, claim_id=None):
    return await call("gfw_forest_alerts_near_company", "/gfw/alerts/company",
                      {"company_id": company_id, "fy": fy, "radius_km": radius_km}, claim_id)


async def alerts_near(lat: float, lon: float, fy: str | None = None, radius_km: float = 5.0, claim_id=None):
    return await call("gfw_forest_alerts_near_point", "/gfw/alerts/near",
                      {"lat": lat, "lon": lon, "fy": fy, "radius_km": radius_km}, claim_id)


async def rec_registry(company_id: str, vintage: int | None = None, claim_id=None):
    return await call("rec_registry", "/registry/rec", {"company_id": company_id, "vintage": vintage}, claim_id)


async def assurance(company_id: str, fy: str | None = None, claim_id=None):
    return await call("assurance_statements", "/assurance/statements", {"company_id": company_id, "fy": fy}, claim_id)


async def news(q: str, company_id: str | None = None, k: int = 4, date_from: str | None = None,
               date_to: str | None = None, claim_id=None):
    return await call("news_search", "/news/search",
                      {"q": q, "company_id": company_id, "k": k, "date_from": date_from, "date_to": date_to}, claim_id)


async def overview():
    async with _client() as c:
        return (await c.get("/tables")).json()


async def table(name: str, limit: int, offset: int, company_id: str | None):
    async with _client() as c:
        r = await c.get(f"/tables/{name}", params={k: v for k, v in
                                                   {"limit": limit, "offset": offset, "company_id": company_id}.items()
                                                   if v is not None})
        r.raise_for_status()
        return r.json()


async def health() -> bool:
    try:
        async with _client() as c:
            return (await c.get("/health")).status_code == 200
    except Exception:  # noqa: BLE001
        return False
