"""Runs one analysis through the LangGraph pipeline with an event sink."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.events import EventSink, emit, use_sink
from app.core.models import Analysis
from app.decision.jev import JevEngine, engine
from app.llm.providers import get_llm


def new_analysis(source_document: str) -> Analysis:
    return Analysis(analysis_id=uuid.uuid4().hex[:12], source_document=source_document,
                    created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))


async def run_analysis(pdf_path: str | Path, analysis: Analysis, sink: EventSink, max_claims: int | None = None,
                       jev: JevEngine | None = None) -> tuple[Analysis, str]:
    from app.graph.pipeline import GRAPH

    jev = jev or engine()
    llm = get_llm()
    token = use_sink(sink)
    analysis.status = "running"
    analysis.engines = {"decision": "TypeSafe Jev", "decision_mode": jev.mode, "llm": llm.name,
                        "orchestrator": "LangGraph"}
    report = ""
    try:
        emit("system", "start", f"Analysis {analysis.analysis_id} started")
        state = await GRAPH.ainvoke({"pdf_path": str(pdf_path), "analysis": analysis,
                                     "env": {"jev": jev, "llm": llm, "sink": sink, "max_claims": max_claims}},
                                    {"recursion_limit": 100})
        report = state.get("report_md", "")
        analysis.engines["decision"] = f"TypeSafe {jev.model_version}"
        analysis.status = "done"
        emit("system", "done", f"Analysis finished: {analysis.summary.total_claims if analysis.summary else 0} claims",
             data={"jev_calls": jev.stats.calls, "jev_cache_hits": jev.stats.cache_hits})
    except Exception as exc:  # noqa: BLE001 - any failure becomes a visible error state
        analysis.status = "error"
        analysis.error = f"{type(exc).__name__}: {exc}"
        emit("system", "error", analysis.error)
    finally:
        analysis.finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        sink.close()
        from app.core.events import _current
        _current.reset(token)
    return analysis, report
