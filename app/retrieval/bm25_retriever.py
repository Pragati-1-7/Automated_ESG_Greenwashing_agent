"""
bm25_retriever.py

STEP 4: BM25 keyword-based evidence retriever.

WHY BM25?
---------
BM25 (Best Match 25) is a well-understood, deterministic keyword-ranking
algorithm used in production search engines (Elasticsearch, Lucene, etc.).
It is particularly effective for ESG evidence retrieval because:

  - ESG claims contain highly specific terms: company names, years, scope
    labels (Scope 1, Scope 2), metric names, and units.
  - These exact terms matter greatly: "FY2024" and "FY2023" are very different,
    and BM25's exact-term matching picks up this difference.
  - It is fast, fully offline, and completely deterministic -- the same query
    always produces the same ranking for the same corpus.

HOW IT WORKS
------------
  1. Load evidence.json on initialisation (or accept a pre-loaded list).
  2. Build a tokenised corpus from the evidence text fields most likely to
     contain matching terms (retrieved_text, source, company, reporting_period,
     source_type).
  3. For each query, score every evidence document with rank_bm25.BM25Okapi.
  4. Return the top-k results, sorted by score descending.
  5. Normalise scores to [0, 1] so they can be combined with semantic scores
     in the hybrid retriever without one scale dominating.

OFFLINE / TESTABLE
------------------
The retriever loads the corpus once and keeps it in memory. No network access.
No API keys. Safe to call in CI.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from app.utils.schemas import EvidenceRecord, RetrievedEvidence

# Default path to the evidence corpus relative to the project root.
_DEFAULT_EVIDENCE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "evidence" / "evidence.json"
)


def _tokenise(text: str) -> list[str]:
    """Lower-case and split on non-alphanumeric characters, remove empty tokens."""
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]


def _build_document_text(ev: EvidenceRecord) -> str:
    """Combine all searchable fields of one evidence record into a single string."""
    parts = [
        ev.retrieved_text,
        ev.source,
        ev.company,
        ev.source_type,
        ev.reporting_period or "",
    ]
    return " ".join(p for p in parts if p)


class BM25Retriever:
    """BM25-based evidence retriever backed by the local evidence.json corpus.

    Usage:
        retriever = BM25Retriever()        # loads data/evidence/evidence.json
        results = retriever.retrieve("GreenLeaf Scope 1 emissions FY2024", top_k=5)
    """

    def __init__(
        self,
        evidence_path: Optional[Path] = None,
        records: Optional[list[EvidenceRecord]] = None,
    ) -> None:
        """Initialise the retriever.

        Args:
            evidence_path: Path to evidence.json. Defaults to data/evidence/evidence.json.
            records: Pre-loaded list of EvidenceRecord objects. If supplied,
                     evidence_path is ignored. Useful for testing.
        """
        if records is not None:
            self._records = records
        else:
            path = evidence_path or _DEFAULT_EVIDENCE_PATH
            self._records = _load_evidence(path)

        # Build the BM25 index once.
        corpus_texts = [_build_document_text(ev) for ev in self._records]
        tokenised_corpus = [_tokenise(text) for text in corpus_texts]
        self._bm25 = BM25Okapi(tokenised_corpus)

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidence]:
        """Retrieve the top-k most relevant evidence records for a query.

        Args:
            query: A keyword search string (e.g. "GreenLeaf Scope 1 FY2024").
            top_k: Maximum number of results to return.

        Returns:
            List of RetrievedEvidence objects sorted by BM25 score descending.
            The semantic_score field is always 0.0 (filled in by hybrid retriever).
        """
        if not query.strip():
            return []

        tokens = _tokenise(query)
        raw_scores: list[float] = list(self._bm25.get_scores(tokens))

        # Normalise scores to [0, 1] range.
        max_score = max(raw_scores) if raw_scores else 0.0
        if max_score > 0:
            normalised = [s / max_score for s in raw_scores]
        else:
            normalised = raw_scores  # all zeros, nothing matched

        # Pair each record with its normalised score, sort descending, take top_k.
        scored = sorted(
            zip(self._records, normalised),
            key=lambda pair: pair[1],
            reverse=True,
        )
        top = scored[:top_k]

        results: list[RetrievedEvidence] = []
        for rank, (ev, norm_score) in enumerate(top, start=1):
            results.append(
                RetrievedEvidence.from_evidence_record(
                    ev,
                    rank=rank,
                    bm25_score=round(norm_score, 4),
                    semantic_score=0.0,
                    combined_score=round(norm_score, 4),
                )
            )
        return results

    def retrieve_multi_query(
        self, queries: list[str], top_k: int = 5
    ) -> list[RetrievedEvidence]:
        """Retrieve evidence using multiple queries and return the merged, deduplicated top-k.

        Each query is run independently. Results are merged by keeping the highest
        BM25 score seen for each unique evidence_id, then re-ranked.

        Args:
            queries: List of search query strings.
            top_k: Maximum results to return.

        Returns:
            Merged, deduplicated, re-ranked list of RetrievedEvidence.
        """
        best: dict[str, RetrievedEvidence] = {}  # evidence_id → best result so far

        for q in queries:
            for item in self.retrieve(q, top_k=top_k):
                eid = item.evidence_id
                if eid not in best or item.bm25_score > best[eid].bm25_score:
                    best[eid] = item

        merged = sorted(best.values(), key=lambda r: r.bm25_score, reverse=True)
        # Re-assign ranks after merging.
        for i, ev in enumerate(merged[:top_k], start=1):
            ev.rank = i
        return merged[:top_k]

    @property
    def records(self) -> list[EvidenceRecord]:
        """Read-only access to the loaded evidence records."""
        return list(self._records)


# ---------------------------------------------------------------------------
# Internal loader
# ---------------------------------------------------------------------------

def _load_evidence(path: Path) -> list[EvidenceRecord]:
    """Parse evidence.json and return validated EvidenceRecord objects."""
    if not path.exists():
        raise FileNotFoundError(f"Evidence corpus not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    records: list[EvidenceRecord] = []
    for item in raw.get("evidence", []):
        records.append(EvidenceRecord(**item))
    return records
