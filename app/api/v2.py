"""
app/api/v2.py

v2 HTTP layer (contract: docs/API_V2_CONTRACT.md). No business logic: it
starts graph runs as background tasks, streams their AgentEvents over SSE,
persists finished analyses as JSON, and proxies the mock sources browser.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.core.config import ROOT
from app.core.events import EventSink
from app.core.models import Analysis
from app.graph.runner import new_analysis, run_analysis
from app.tools import sources

router = APIRouter(prefix="/v2", tags=["v2"])

REPORTS_DIR = ROOT / "data" / "reports"
STORE_DIR = ROOT / "storage" / "analyses"
BENCH_PATH = ROOT / "data" / "benchmark" / "results_latest.json"


class Run:
    def __init__(self, analysis: Analysis, sink: EventSink):
        self.analysis = analysis
        self.sink = sink
        self.report_md = ""
        self.task: asyncio.Task | None = None


RUNS: dict[str, Run] = {}


def _manifest() -> list[dict]:
    p = REPORTS_DIR / "manifest.json"
    return json.loads(p.read_text()) if p.exists() else []


def _save(run: Run) -> None:
    STORE_DIR.mkdir(parents=True, exist_ok=True)
    (STORE_DIR / f"{run.analysis.analysis_id}.json").write_text(json.dumps({
        "analysis": run.analysis.model_dump(), "report_md": run.report_md,
        "events": [e.model_dump() for e in run.sink.events]}))


def _load(analysis_id: str) -> Run | None:
    if analysis_id in RUNS:
        return RUNS[analysis_id]
    p = STORE_DIR / f"{analysis_id}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    from app.core.models import AgentEvent
    sink = EventSink()
    sink.events = [AgentEvent(**e) for e in d["events"]]
    sink.closed = True
    run = Run(Analysis(**d["analysis"]), sink)
    run.report_md = d["report_md"]
    RUNS[analysis_id] = run
    return run


async def _execute(run: Run, pdf: Path, max_claims: int | None, cleanup: bool) -> None:
    try:
        run.analysis, run.report_md = await run_analysis(pdf, run.analysis, run.sink, max_claims)
        _save(run)
    finally:
        if cleanup:
            shutil.rmtree(pdf.parent, ignore_errors=True)


# ---------------------------------------------------------------------------- demo reports
@router.get("/demo-reports")
def demo_reports() -> list[dict]:
    return [{k: m[k] for k in ("key", "title", "company", "filename", "pages", "profile")} for m in _manifest()]


@router.get("/demo-reports/{key}/pdf")
def demo_pdf(key: str):
    m = next((m for m in _manifest() if m["key"] == key), None)
    if not m:
        raise HTTPException(404, f"Unknown demo report {key}")
    return FileResponse(REPORTS_DIR / m["filename"], media_type="application/pdf", filename=m["filename"])


# ---------------------------------------------------------------------------- analyses
@router.post("/analyses", status_code=202)
async def create_analysis(file: Optional[UploadFile] = File(default=None), demo_report: Optional[str] = Form(default=None),
                          max_claims: Optional[int] = Form(default=None)) -> dict:
    if demo_report:
        m = next((m for m in _manifest() if m["key"] == demo_report), None)
        if not m:
            raise HTTPException(400, f"Unknown demo report {demo_report!r}")
        pdf, name, cleanup = REPORTS_DIR / m["filename"], m["filename"], False
    elif file is not None:
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, "Upload must be a .pdf file")
        data = await file.read()
        if not data:
            raise HTTPException(400, "Uploaded file is empty")
        if len(data) > 40 * 1024 * 1024:
            raise HTTPException(413, "PDF larger than 40 MB")
        tmp = Path(tempfile.mkdtemp(prefix="esg_upload_"))
        pdf = tmp / Path(file.filename).name
        pdf.write_bytes(data)
        name, cleanup = Path(file.filename).name, True
    else:
        raise HTTPException(400, "Provide a PDF file or a demo_report key")
    analysis = new_analysis(name)
    run = Run(analysis, EventSink())
    RUNS[analysis.analysis_id] = run
    run.task = asyncio.create_task(_execute(run, pdf, max_claims, cleanup))
    return {"analysis_id": analysis.analysis_id, "status": "queued"}


@router.get("/analyses")
def list_analyses() -> list[dict]:
    ids = set(RUNS)
    if STORE_DIR.exists():
        ids |= {p.stem for p in STORE_DIR.glob("*.json")}
    out = []
    for i in ids:
        r = _load(i)
        if r:
            a = r.analysis
            out.append({"analysis_id": a.analysis_id, "status": a.status, "source_document": a.source_document,
                        "company_name": a.company.name if a.company else None, "created_at": a.created_at,
                        "company_risk_score": a.summary.company_risk_score if a.summary else None})
    return sorted(out, key=lambda r: r["created_at"], reverse=True)


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str) -> dict:
    r = _load(analysis_id)
    if not r:
        raise HTTPException(404, "Unknown analysis")
    return r.analysis.model_dump()


@router.get("/analyses/{analysis_id}/report")
def get_report(analysis_id: str) -> dict:
    r = _load(analysis_id)
    if not r:
        raise HTTPException(404, "Unknown analysis")
    if r.analysis.status != "done":
        raise HTTPException(409, f"Analysis is {r.analysis.status}")
    return {"markdown": r.report_md}


@router.get("/analyses/{analysis_id}/events")
async def events(analysis_id: str):
    r = _load(analysis_id)
    if not r:
        raise HTTPException(404, "Unknown analysis")

    async def gen():
        q = None if r.sink.closed else r.sink.subscribe()
        sent = 0
        try:
            for ev in list(r.sink.events):
                sent = ev.seq
                yield {"event": "agent_event", "data": ev.model_dump_json()}
            if q is not None:
                while True:
                    ev = await q.get()
                    if ev is None:
                        break
                    if ev.seq <= sent:
                        continue
                    yield {"event": "agent_event", "data": ev.model_dump_json()}
            yield {"event": "done", "data": json.dumps({"status": r.analysis.status})}
        finally:
            if q is not None:
                r.sink.unsubscribe(q)

    return EventSourceResponse(gen())


# ---------------------------------------------------------------------------- single claim
@router.post("/verify-claim")
async def verify_single_claim(payload: dict) -> dict:
    """Verify one claim sentence for a named company: {"claim": "...", "company": "...", "fy": "FY2025"}."""
    from app.decision.jev import engine
    from app.graph.claims import verify_claim
    from app.llm.providers import get_llm

    text, company = (payload.get("claim") or "").strip(), (payload.get("company") or "").strip()
    if len(text) < 10 or len(company) < 2:
        raise HTTPException(400, "Provide 'claim' (a sentence) and 'company' (a name)")
    sink = EventSink()
    from app.core.events import use_sink, _current
    token = use_sink(sink)
    try:
        claim, match = await verify_claim(text, company, engine(), get_llm(), doc_fy=payload.get("fy") or "FY2025")
    finally:
        _current.reset(token)
    return {"company": match.model_dump(), "claim": claim.model_dump(), "events": [e.model_dump() for e in sink.events]}


# ---------------------------------------------------------------------------- sources + benchmark
@router.get("/sources/overview")
async def sources_overview() -> dict:
    return await sources.overview()


@router.get("/sources/{table}")
async def sources_table(table: str, limit: int = 50, offset: int = 0, company_id: Optional[str] = None) -> dict:
    try:
        return await sources.table(table, limit, offset, company_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(404, str(exc)) from exc


@router.get("/benchmark/latest")
def benchmark_latest() -> dict:
    if not BENCH_PATH.exists():
        raise HTTPException(404, "Benchmark not run yet: python -m eval.run_benchmark")
    return json.loads(BENCH_PATH.read_text())
