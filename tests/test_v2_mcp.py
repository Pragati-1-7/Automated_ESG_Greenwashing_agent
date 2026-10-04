"""The MCP server exposes the same data as the REST service."""

import asyncio

import pytest

mcp_server = pytest.importorskip("mock_sources.mcp_server")


def test_mcp_tools_listed_and_callable():
    async def go():
        tools = {t.name for t in await mcp_server.server.list_tools()}
        assert {"brsr_filings", "regulatory_actions", "forest_alerts_near_company", "news_search"} <= tools
        return await mcp_server.server.call_tool("rec_registry", {"company_id": "CMP-0001", "vintage": 2024})
    out = asyncio.run(go())
    assert "2100000" in str(out) or "2,100,000" in str(out)
