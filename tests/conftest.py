"""
conftest.py

Shared test fixtures. Points every test's SQLite storage at a throwaway file
so running the test suite never writes into the real storage/app.db.
"""

from __future__ import annotations

import os

import pytest

# v2: every decision-engine (Jev) answer in the test suite is REPLAYED from the
# recorded cassette in data/cassettes/jev/. No network, no API key needed.
os.environ["JEV_MODE"] = "replay"
os.environ.pop("TYPESAFE_API_KEY", None)
os.environ.pop("JEV_API_KEY", None)
os.environ["LLM_PROVIDER"] = "mock"
os.environ["MOCK_SOURCES_URL"] = "inproc"


@pytest.fixture(autouse=True)
def isolated_sqlite_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_run.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    yield db_file
