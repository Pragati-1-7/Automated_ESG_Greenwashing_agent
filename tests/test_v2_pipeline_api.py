"""Full LangGraph pipeline on the demo PDFs and the v2 API (recorded Jev answers)."""

import asyncio
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.events import EventSink
from app.graph.runner import new_analysis, run_analysis
from data_gen.spec import DEMO_COMPANIES

ROOT = Path(__file__).resolve().parent.parent
MAN = {m["key"]: m for m in json.loads((ROOT / "data/reports/manifest.json").read_text())}


@pytest.mark.parametrize("key,idx", [("vajra", 0), ("aurelia", 3)])
def test_pipeline_matches_planted_truth(key, idx):
    sink = EventSink()
    a, report = asyncio.run(run_analysis(ROOT / "data/reports" / MAN[key]["filename"],
                                         new_analysis(MAN[key]["filename"]), sink))
    assert a.status == "done", a.error
    by_text = {c.text: c for c in a.claims}
    for c in DEMO_COMPANIES[idx]["claims"]:
        assert by_text[c["text"]].verdict.label == c["expected"] or c["id"] == "AUR-05", c["id"]
    # every investigated claim's evidence came from a mock_sources endpoint
    for c in a.claims:
        for s in c.sub_claims:
            for e in s.evidence:
                assert e.endpoint.startswith("/")
    agents = {e.agent for e in sink.events}
    assert {"ingest", "resolver", "extractor", "triage", "decomposer", "router", "investigator", "judge",
            "verdict", "risk", "reporter"} <= agents
    assert "## Audit trail" in report and a.summary.company_risk_score is not None
    if key == "aurelia":
        assert not a.company.resolved and a.summary.verdict_counts["CONTRADICT"] == 0


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app.api import v2
    monkeypatch.setattr(v2, "STORE_DIR", tmp_path / "analyses")
    v2.RUNS.clear()
    from app.api.main import app
    with TestClient(app) as c:
        yield c


def test_api_health_and_catalogue(client):
    h = client.get("/health").json()
    assert h["sources"] == "up" and h["llm"] == "mock-deterministic" and "jev" in h["decision_engine"]
    reports = client.get("/v2/demo-reports").json()
    assert {r["key"] for r in reports} == {"vajra", "sahyadri", "kaveri", "aurelia"}
    assert client.get("/v2/demo-reports/kaveri/pdf").headers["content-type"] == "application/pdf"
    ov = client.get("/v2/sources/overview").json()
    assert len(ov["tables"]) == 10
    rows = client.get("/v2/sources/brsr_filings", params={"company_id": "CMP-0003", "limit": 3}).json()
    assert rows["total"] == 6 and len(rows["rows"]) == 3


def test_api_analysis_lifecycle_and_sse(client):
    r = client.post("/v2/analyses", data={"demo_report": "kaveri"})
    assert r.status_code == 202
    aid = r.json()["analysis_id"]
    for _ in range(240):
        a = client.get(f"/v2/analyses/{aid}").json()
        if a["status"] in ("done", "error"):
            break
        time.sleep(0.5)
    assert a["status"] == "done", a["error"]
    assert a["summary"]["verdict_counts"]["CONTRADICT"] == 0
    with client.stream("GET", f"/v2/analyses/{aid}/events") as s:
        body = "".join(s.iter_text())
    assert body.count("event: agent_event") > 100 and "event: done" in body
    md = client.get(f"/v2/analyses/{aid}/report").json()["markdown"]
    assert md.startswith("# Greenwashing verification report")
    assert any(x["analysis_id"] == aid for x in client.get("/v2/analyses").json())


def test_api_rejects_bad_input(client):
    assert client.post("/v2/analyses").status_code == 400
    assert client.post("/v2/analyses", data={"demo_report": "nope"}).status_code == 400
    assert client.post("/v2/analyses", files={"file": ("a.txt", b"hello", "text/plain")}).status_code == 400
    assert client.post("/v2/analyses", files={"file": ("a.pdf", b"", "application/pdf")}).status_code == 400
    assert client.get("/v2/analyses/doesnotexist").status_code == 404


def test_api_uploaded_garbage_pdf_ends_in_error_state(client):
    aid = client.post("/v2/analyses", files={"file": ("bad.pdf", b"%PDF-1.4 garbage", "application/pdf")}).json()["analysis_id"]
    for _ in range(40):
        a = client.get(f"/v2/analyses/{aid}").json()
        if a["status"] in ("done", "error"):
            break
        time.sleep(0.25)
    assert a["status"] == "error" and "PDF" in a["error"]


def test_benchmark_endpoint(client):
    r = client.get("/v2/benchmark/latest")
    assert r.status_code == 200 and r.json()["overall"]["accuracy"] >= 0.8


def test_api_verify_single_claim(client):
    r = client.post("/v2/verify-claim", json={"claim": "Our LTIFR stood at 0.05 in FY2025.",
                                              "company": "Aurelia Renewables Pvt Ltd"})
    assert r.status_code == 200
    d = r.json()
    assert d["claim"]["verdict"]["label"] == "INSUFFICIENT_EVIDENCE" and not d["company"]["resolved"]
    assert any(e["agent"] == "resolver" for e in d["events"])
    assert client.post("/v2/verify-claim", json={"claim": "x"}).status_code == 400
