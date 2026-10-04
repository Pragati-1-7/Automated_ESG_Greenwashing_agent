"""
app/api/main.py

FastAPI entry point. Run with:  uvicorn app.api.main:app --port 8000

All routes live in app/api/v2.py (analyses, live event stream, reports,
single-claim verification, data-source browser, benchmark). This file only
creates the app, enables CORS for the React UI and exposes /health.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v2 import router as v2_router
from app.core.config import settings  # noqa: F401  (loads .env)
from app.core.models import DISCLAIMER

app = FastAPI(
    title="ESG Greenwashing Detection & Verification Agent",
    description="Agentic claim verification: LangGraph agents, Jev decision engine, evidence from mock data "
                "services. Decision support only, not a legal determination of greenwashing.",
    version="2.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(v2_router)


@app.get("/health")
async def health() -> dict:
    from app.decision.jev import engine
    from app.llm.providers import get_llm
    from app.tools import sources

    jev = engine()
    return {
        "status": "ok",
        "service": "esg-greenwashing-agent-api",
        "decision_engine": f"jev ({jev.mode})" if jev.mode != "off" else "offline",
        "llm": get_llm().name,
        "sources": "up" if await sources.health() else "down",
        "disclaimer": DISCLAIMER,
    }
