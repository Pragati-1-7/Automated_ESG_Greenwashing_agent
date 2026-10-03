"""
storage.py

STEP 6: SQLite persistence for analysis runs.

WHY THIS EXISTS
---------------
Every /analyze and /demo/dataset call was previously stateless: close the
browser tab and the result is gone, with no way to revisit a past run. This
was flagged as a known gap (see docs/PROJECT_STATUS_AND_VALIDATION.md). The
original project plan also named SQLite for this purpose (see
.env.example's SQLITE_DB_PATH, present since Step 1 but never wired up).

WHAT THIS DOES NOT DO
----------------------
This module stores and retrieves completed pipeline results. It does not
re-run, modify, or validate them -- that already happened in
app/api/pipeline.py before a result ever reaches this module. Nothing here
computes a verdict or a score.

Uses the Python standard library's sqlite3 module only, no ORM, consistent
with the project's existing "nothing paid, runs on a laptop" stance.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "storage" / "app.db"


def _db_path() -> Path:
    configured = os.getenv("SQLITE_DB_PATH")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path
    return DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            source_type TEXT NOT NULL,
            source_document TEXT NOT NULL,
            company TEXT NOT NULL,
            mode TEXT NOT NULL,
            status TEXT NOT NULL,
            total_claims INTEGER NOT NULL,
            checkable_claims INTEGER NOT NULL,
            align_count INTEGER NOT NULL,
            contradict_count INTEGER NOT NULL,
            insufficient_evidence_count INTEGER NOT NULL,
            average_risk_score REAL,
            result_json TEXT NOT NULL
        )
        """
    )
    return conn


def save_run(source_type: str, mode: str, result: dict) -> str:
    """Persist one completed /analyze or /demo/dataset result. Returns the
    generated run_id. Called only after the pipeline already produced a
    result -- this function never alters it."""
    run_id = str(uuid.uuid4())
    summary = result.get("summary", {})
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO analysis_runs (
                run_id, created_at, source_type, source_document, company, mode,
                status, total_claims, checkable_claims, align_count,
                contradict_count, insufficient_evidence_count, average_risk_score,
                result_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                datetime.now(timezone.utc).isoformat(),
                source_type,
                result.get("source_document", "unknown"),
                result.get("company", "unknown"),
                mode,
                result.get("status", "unknown"),
                summary.get("total_claims", 0),
                summary.get("checkable_claims", 0),
                summary.get("align_count", 0),
                summary.get("contradict_count", 0),
                summary.get("insufficient_evidence_count", 0),
                summary.get("average_risk_score"),
                json.dumps(result),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return run_id


def list_runs(limit: int = 50) -> list[dict]:
    """Return the most recent runs, newest first, WITHOUT the full result
    payload (summary fields only -- callers needing full detail should use
    get_run)."""
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT run_id, created_at, source_type, source_document, company, mode,
                   status, total_claims, checkable_claims, align_count,
                   contradict_count, insufficient_evidence_count, average_risk_score
            FROM analysis_runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def get_run(run_id: str) -> Optional[dict]:
    """Return the full stored result for one run_id, or None if not found."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT result_json FROM analysis_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return json.loads(row["result_json"])


def delete_run(run_id: str) -> bool:
    """Delete one stored run. Returns True if a row was actually deleted."""
    conn = _connect()
    try:
        cursor = conn.execute("DELETE FROM analysis_runs WHERE run_id = ?", (run_id,))
        conn.commit()
    finally:
        conn.close()
    return cursor.rowcount > 0
