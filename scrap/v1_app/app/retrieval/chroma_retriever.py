"""
chroma_retriever.py

STEP 4: ChromaDB-backed semantic (vector) evidence retriever.

WHY SEMANTIC RETRIEVAL?
------------------------
BM25 is excellent at exact-term matching but misses semantically similar
phrases. For example, BM25 might not equate "hazardous effluent discharge"
with "chemical discharge into water bodies" unless both share exact tokens.
A sentence-transformer embedding model can capture this meaning similarity.

ChromaDB is used as the local vector store because:
  - It runs entirely on disk, with no server process needed.
  - It is easy to reset between test runs (ephemeral in-memory mode).
  - It integrates with sentence-transformers out of the box.

OFFLINE DESIGN
--------------
The class works in two modes:

  1. FULL mode (use_semantic=True, default):
     Loads `sentence-transformers/all-MiniLM-L6-v2` (22 MB, downloaded once
     and cached by Hugging Face). Uses a persistent ChromaDB collection.

  2. STUB mode (use_semantic=False):
     Skips all embedding and ChromaDB work. Returns an empty list immediately.
     All tests use this mode so no network access or model download is needed.

The hybrid_retriever automatically falls back to BM25-only scoring when
use_semantic=False, so the overall pipeline still works correctly offline.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from app.utils.schemas import EvidenceRecord, RetrievedEvidence

_DEFAULT_EVIDENCE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "legacy" / "v1_data" / "evidence" / "evidence.json"
)

# Default ChromaDB persistence directory (inside the project, gitignored).
_DEFAULT_CHROMA_DIR = (
    Path(__file__).resolve().parent.parent.parent / ".chroma_db"
)

_COLLECTION_NAME = "esg_evidence"


def _build_document_text(ev: EvidenceRecord) -> str:
    parts = [
        ev.retrieved_text,
        ev.source,
        ev.company,
        ev.source_type,
        ev.reporting_period or "",
    ]
    return " ".join(p for p in parts if p)


class ChromaRetriever:
    """Semantic evidence retriever backed by ChromaDB + sentence-transformers.

    Usage (full semantic mode):
        retriever = ChromaRetriever()
        results = retriever.retrieve("Company reduced Scope 1 emissions", top_k=5)

    Usage (offline/stub mode — no model download, no ChromaDB):
        retriever = ChromaRetriever(use_semantic=False)
        results = retriever.retrieve("...", top_k=5)  # always returns []
    """

    def __init__(
        self,
        evidence_path: Optional[Path] = None,
        chroma_dir: Optional[Path] = None,
        records: Optional[list[EvidenceRecord]] = None,
        use_semantic: bool = True,
        embedding_model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._use_semantic = use_semantic
        self._collection = None
        self._records_by_id: dict[str, EvidenceRecord] = {}

        if not use_semantic:
            return  # stub mode: do nothing

        # ---- Load evidence records ----
        if records is not None:
            loaded_records = records
        else:
            path = evidence_path or _DEFAULT_EVIDENCE_PATH
            loaded_records = _load_evidence(path)

        self._records_by_id = {ev.evidence_id: ev for ev in loaded_records}

        # ---- Initialise ChromaDB ----
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError as e:
            raise ImportError(
                "chromadb is required for semantic retrieval. "
                "Run: pip install chromadb sentence-transformers"
            ) from e

        persist_dir = str(chroma_dir or _DEFAULT_CHROMA_DIR)
        self._client = chromadb.PersistentClient(path=persist_dir)

        emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model_name
        )

        # Get or create the collection.
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=emb_fn,
            metadata={"hnsw:space": "cosine"},
        )

        # Upsert evidence records that are not yet in the collection.
        self._upsert_records(loaded_records)

    def _upsert_records(self, records: list[EvidenceRecord]) -> None:
        """Add any evidence records not yet in the ChromaDB collection."""
        if not self._collection:
            return

        existing_ids: set[str] = set()
        try:
            existing = self._collection.get(include=[])
            existing_ids = set(existing["ids"])
        except Exception:
            pass  # first run — nothing there yet

        new_records = [ev for ev in records if ev.evidence_id not in existing_ids]
        if not new_records:
            return

        self._collection.upsert(
            ids=[ev.evidence_id for ev in new_records],
            documents=[_build_document_text(ev) for ev in new_records],
            metadatas=[{"source_tier": int(ev.source_tier)} for ev in new_records],
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidence]:
        """Retrieve the top-k semantically most similar evidence records.

        Returns an empty list when use_semantic=False (offline/test mode).
        Semantic scores are cosine similarities normalised to [0, 1].

        Args:
            query: A natural-language or keyword query string.
            top_k: Maximum results to return.

        Returns:
            List of RetrievedEvidence, ranked by semantic similarity descending.
        """
        if not self._use_semantic or self._collection is None:
            return []

        if not query.strip():
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, len(self._records_by_id)),
                include=["distances"],
            )
        except Exception:
            return []

        ids = results["ids"][0] if results["ids"] else []
        distances = results["distances"][0] if results["distances"] else []

        output: list[RetrievedEvidence] = []
        for rank, (eid, dist) in enumerate(zip(ids, distances), start=1):
            ev = self._records_by_id.get(eid)
            if ev is None:
                continue
            # ChromaDB cosine distance is in [0, 2]; similarity = 1 - dist/2
            semantic_sim = max(0.0, 1.0 - dist / 2.0)
            output.append(
                RetrievedEvidence.from_evidence_record(
                    ev,
                    rank=rank,
                    bm25_score=0.0,
                    semantic_score=round(semantic_sim, 4),
                    combined_score=round(semantic_sim, 4),
                )
            )
        return output

    def retrieve_multi_query(
        self, queries: list[str], top_k: int = 5
    ) -> list[RetrievedEvidence]:
        """Retrieve and merge results across multiple queries."""
        if not self._use_semantic:
            return []

        best: dict[str, RetrievedEvidence] = {}
        for q in queries:
            for item in self.retrieve(q, top_k=top_k):
                eid = item.evidence_id
                if eid not in best or item.semantic_score > best[eid].semantic_score:
                    best[eid] = item

        merged = sorted(best.values(), key=lambda r: r.semantic_score, reverse=True)
        for i, ev in enumerate(merged[:top_k], start=1):
            ev.rank = i
        return merged[:top_k]


# ---------------------------------------------------------------------------
# Internal loader
# ---------------------------------------------------------------------------

def _load_evidence(path: Path) -> list[EvidenceRecord]:
    if not path.exists():
        raise FileNotFoundError(f"Evidence corpus not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [EvidenceRecord(**item) for item in raw.get("evidence", [])]
