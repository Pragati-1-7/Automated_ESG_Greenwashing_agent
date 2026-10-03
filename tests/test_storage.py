"""
test_storage.py

STEP 6 tests: SQLite persistence layer (app/storage.py).

Each test points SQLITE_DB_PATH at a throwaway file via monkeypatch so these
tests never touch the real storage/app.db, and never leave files behind.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import storage


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    yield db_file


def _fake_result(status="ok", total_claims=3, align=1, contradict=1, insufficient=1):
    return {
        "status": status,
        "source_document": "example.pdf",
        "company": "Example Co",
        "summary": {
            "total_claims": total_claims,
            "checkable_claims": total_claims,
            "not_checkable_claims": 0,
            "align_count": align,
            "contradict_count": contradict,
            "insufficient_evidence_count": insufficient,
            "average_risk_score": 42.5,
            "claims_scored": total_claims,
        },
        "audit_records": [],
    }


def test_save_and_get_run_round_trips_full_result():
    result = _fake_result()
    run_id = storage.save_run(source_type="pdf", mode="mock", result=result)
    fetched = storage.get_run(run_id)
    assert fetched == result


def test_get_run_returns_none_for_unknown_id():
    assert storage.get_run("does-not-exist") is None


def test_list_runs_orders_newest_first():
    id1 = storage.save_run(source_type="pdf", mode="mock", result=_fake_result(total_claims=1))
    id2 = storage.save_run(source_type="dataset", mode="n/a", result=_fake_result(total_claims=2))
    runs = storage.list_runs()
    assert [r["run_id"] for r in runs] == [id2, id1]


def test_list_runs_does_not_include_full_result_payload():
    storage.save_run(source_type="pdf", mode="mock", result=_fake_result())
    runs = storage.list_runs()
    assert "result_json" not in runs[0]
    assert "audit_records" not in runs[0]


def test_list_runs_respects_limit():
    for i in range(5):
        storage.save_run(source_type="pdf", mode="mock", result=_fake_result(total_claims=i))
    runs = storage.list_runs(limit=2)
    assert len(runs) == 2


def test_delete_run_removes_it():
    run_id = storage.save_run(source_type="pdf", mode="mock", result=_fake_result())
    assert storage.delete_run(run_id) is True
    assert storage.get_run(run_id) is None


def test_delete_run_returns_false_for_unknown_id():
    assert storage.delete_run("does-not-exist") is False


def test_summary_fields_persisted_correctly():
    result = _fake_result(total_claims=7, align=3, contradict=2, insufficient=2)
    run_id = storage.save_run(source_type="dataset", mode="n/a", result=result)
    runs = storage.list_runs()
    row = next(r for r in runs if r["run_id"] == run_id)
    assert row["total_claims"] == 7
    assert row["align_count"] == 3
    assert row["contradict_count"] == 2
    assert row["insufficient_evidence_count"] == 2
    assert row["average_risk_score"] == 42.5
