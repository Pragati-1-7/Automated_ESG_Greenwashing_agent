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
