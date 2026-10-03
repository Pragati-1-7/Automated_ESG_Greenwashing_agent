"""
conftest.py

Shared test fixtures. Points every test's SQLite storage at a throwaway file
so running the test suite never writes into the real storage/app.db.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_sqlite_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_run.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_file))
    yield db_file
