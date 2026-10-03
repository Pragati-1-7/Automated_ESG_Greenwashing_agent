"""
test_api.py

STEP 6 tests: FastAPI backend (app/api/main.py).

Uses FastAPI's TestClient (in-process, no real network/socket needed) and
only offline mock/synthetic data -- no external API keys required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "disclaimer" in body


def test_analyze_requires_file_or_demo():
    resp = client.post("/analyze", data={})
    assert resp.status_code == 400


def test_analyze_with_demo_flag_runs_pipeline():
    resp = client.post("/analyze", data={"use_demo": "true"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "no_claims")
    assert "summary" in body
    assert "disclaimer" in body


def test_analyze_rejects_non_pdf_upload():
    resp = client.post(
        "/analyze",
        data={"use_demo": "false"},
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 400


def test_analyze_rejects_empty_pdf_upload():
    resp = client.post(
        "/analyze",
        data={"use_demo": "false"},
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert resp.status_code == 400


def test_demo_dataset_endpoint():
    resp = client.get("/demo/dataset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["summary"]["total_claims"] == 12
    assert len(body["audit_records"]) == 12


def test_get_claim_found():
    resp = client.get("/claims/CLM-001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["audit_record"]["claim_id"] == "CLM-001"


def test_get_claim_not_found():
    resp = client.get("/claims/CLM-NOPE-999")
    assert resp.status_code == 404


def test_analyze_persists_a_run_and_it_is_retrievable():
    resp = client.post("/analyze", data={"use_demo": "true"})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    assert run_id

    list_resp = client.get("/runs")
    assert list_resp.status_code == 200
    run_ids = [r["run_id"] for r in list_resp.json()["runs"]]
    assert run_id in run_ids

    get_resp = client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["source_document"] == "synthetic_esg_report.pdf"


def test_demo_dataset_persists_a_run():
    resp = client.get("/demo/dataset")
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    get_resp = client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["summary"]["total_claims"] == 12


def test_get_run_not_found():
    resp = client.get("/runs/does-not-exist")
    assert resp.status_code == 404


def test_delete_run_then_it_is_gone():
    analyze_resp = client.post("/analyze", data={"use_demo": "true"})
    run_id = analyze_resp.json()["run_id"]

    delete_resp = client.delete(f"/runs/{run_id}")
    assert delete_resp.status_code == 200

    get_resp = client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 404


def test_delete_run_not_found():
    resp = client.delete("/runs/does-not-exist")
    assert resp.status_code == 404
