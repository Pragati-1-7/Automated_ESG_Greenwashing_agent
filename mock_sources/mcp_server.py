"""
mock_sources/mcp_server.py

The same mock ESG data sources exposed as an MCP server, so any MCP client
(Claude Desktop, other agent frameworks) can use them as tools:

    python -m mock_sources.mcp_server            # stdio transport

Each tool wraps the corresponding REST handler in mock_sources/app.py, so the
REST API and the MCP tools can never disagree.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mock_sources import app as rest

server = MCPServer(name="esg-mock-sources", version="1.0.0",
                   instructions="Synthetic ESG evidence sources (fictional companies): BRSR filings, OCEMS "
                                "exceedances, regulator orders, forest-loss alerts, REC registry, assurance, news.")


@server.tool()
def resolve_company(name: str) -> dict:
    """Find registry companies matching a company name (fuzzy, distinctive-token aware)."""
    return rest.resolve(name=name, limit=5)


@server.tool()
def brsr_filings(company_id: str, fy: str | None = None) -> dict:
    """SEBI BRSR Core style annual filing(s) for a company (Tier 1). fy like 'FY2025'."""
    return rest.brsr(company_id=company_id, fy=fy)


@server.tool()
def ocems_exceedances(company_id: str, fy: str | None = None) -> dict:
    """Continuous emission monitoring exceedance events for the company's plants (Tier 2)."""
    return rest.ocems(company_id=company_id, fy=fy, date_from=None, date_to=None, parameter=None)


@server.tool()
def regulatory_actions(company_id: str, fy: str | None = None) -> dict:
    """NGT / CPCB / state board / SEBI orders and penalties (Tier 2)."""
    return rest.regulatory(company_id=company_id, fy=fy, date_from=None, date_to=None, authority=None)


@server.tool()
def forest_alerts_near_company(company_id: str, fy: str | None = None, radius_km: float = 5.0) -> dict:
    """Satellite forest-loss alerts within radius_km of any of the company's facilities (Tier 3)."""
    return rest.alerts_company(company_id=company_id, radius_km=radius_km, fy=fy, date_from=None, date_to=None)


@server.tool()
def rec_registry(company_id: str, vintage: int | None = None) -> dict:
    """Renewable energy certificates (retired / active) held by the company (Tier 3)."""
    return rest.rec(company_id=company_id, vintage=vintage)


@server.tool()
def assurance_statements(company_id: str, fy: str | None = None) -> dict:
    """Independent assurance statements on BRSR Core (Tier 3)."""
    return rest.assurance(company_id=company_id, fy=fy)


@server.tool()
def news_search(q: str, company_id: str | None = None, k: int = 5) -> dict:
    """BM25 search over news and company press releases (Tier 4/5)."""
    return rest.news(q=q, company_id=company_id, k=k, date_from=None, date_to=None)


if __name__ == "__main__":
    server.run()
