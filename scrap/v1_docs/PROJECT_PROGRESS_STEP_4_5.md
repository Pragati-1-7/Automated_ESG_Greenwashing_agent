# Project Progress — Steps 4 & 5: Evidence Retrieval, Verification & Risk Scoring

**Project:** Automated ESG Greenwashing Detection & Verification Agent  
**Author:** Pragati (B.Tech CSE, 2nd Year)  
**Steps:** 4 & 5 (Evidence Retrieval + Verification Engine + Risk Scoring)  

---

## 1. Objectives

Building upon Step 1 (schemas and datasets), Step 2 (PDF parsing and claim extraction), and Step 3 (rule-based claim checkability), Steps 4 & 5 complete the core backend intelligence:

1. **Step 4 (Evidence Retrieval):**
   - Plan targeted keyword queries per checkable claim.
   - Retrieve relevant external evidence using a hybrid approach:
     - Lexical BM25 ranking (offline, fast, deterministic).
     - Semantic vector search with ChromaDB and `sentence-transformers` embeddings.
     - Min-max score normalisation and weighted rank fusion ($0.6 \times \text{BM25} + 0.4 \times \text{Semantic}$).
   - Respect source credibility hierarchy (Tier 1 regulatory filings down to Tier 5 news).

2. **Step 5 (Verification & Risk Scoring):**
   - **Deterministic Numeric Checks:** Perform exact arithmetic in Python rather than letting an LLM hallucinate numbers or tolerance calculations.
   - **Dimensional Validation:** Check for unit mismatches (e.g. MW capacity vs. MWh energy), reporting period discrepancies, and GHG scope divergence.
   - **Verification Decision Engine:** Categorise claims into `ALIGN`, `CONTRADICT`, or `INSUFFICIENT_EVIDENCE`, giving precedence to high-authority sources.
   - **Greenwashing Risk Scorer:** Compute an explainable $0-100$ risk score with human-readable point breakdowns and triage disclaimers.
   - **Full Auditability:** Assemble comprehensive `AuditRecord` objects for complete transparency.

---

## 2. Implemented Modules

### `app/retrieval/query_planner.py`
Generates 2–4 targeted keyword search queries per checkable claim based on company name, metric, reporting period, scope, and baseline year. Uses a deterministic rule-based generator by default, with optional LLM generation support.

### `app/retrieval/bm25_retriever.py`
Indexes external evidence passages using `rank_bm25.BM25Okapi`. Performs tokenisation, stopword removal, and min-max score normalisation into $[0, 1]$. Runs completely offline without external API dependencies.

### `app/retrieval/chroma_retriever.py`
Dense vector retrieval using `chromadb` and `sentence-transformers` (`all-MiniLM-L6-v2`). Persists embeddings locally under `data/chroma_db/`.

### `app/retrieval/hybrid_retriever.py`
Combines BM25 and ChromaDB results using configurable weights:
$$\text{Combined Score} = 0.60 \times \text{BM25} + 0.40 \times \text{Semantic}$$
Sorts evidence by combined score, assigns ranks, and returns structured `RetrievalResult` objects containing `RetrievedEvidence`.

### `app/evaluation/numeric_checks.py`
Deterministic arithmetic and dimensional consistency checks:
- **Percentage reductions & increases:** Verifies relative changes with a configurable $\pm 5\%$ tolerance.
- **Count & incident checks:** Confirms zero-fatality/incident claims against reported numbers or words (e.g., "two fatal accidents").
- **Capacity plausibility checks:** Flags physical impossibilities (e.g., claiming 100,000 tonnes of recycling with an authorized capacity of only 40,000 tonnes).
- **Unit compatibility checks:** Flags dimensional conflicts such as capacity (MW) vs. energy generation (MWh).
- **Scope & Period checks:** Rejects direct numeric comparison when GHG scopes or reporting years differ.

### `app/evaluation/verification.py`
Structured verification engine:
- Evaluates claim against retrieved evidence and numerical check outcomes.
- Implements tier-based weighting: Tier 1 (regulatory filings) and Tier 2 (regulator records) override lower-tier claims (e.g. company press releases).
- Distinguishes between historical result claims and forward-looking commitment/target claims (unverified targets yield `INSUFFICIENT_EVIDENCE` rather than false certainty).
- Produces a clear `Verdict` (`ALIGN`, `CONTRADICT`, or `INSUFFICIENT_EVIDENCE`).

### `app/scoring/risk_score.py`
Calculates an explainable Greenwashing Risk Score from 0 to 100:
- **Scoring Breakdown:**
  - `CONTRADICT` verdict: +40 pts
  - High-authority contradiction (Tier 1/2): +20 pts
  - Low-tier-only evidence (Tier 4/5): +15 pts
  - `INSUFFICIENT_EVIDENCE` verdict: +15 pts
  - Incompatible units or scope mismatch: +10 pts
  - Future target without interim milestones: +10 pts
  - Capacity constraint violation: +20 pts
- **Risk Bands:**
  - `Low`: 0–24
  - `Moderate`: 25–49
  - `High`: 50–74
  - `Very High`: 75–100
- **Disclaimer:** Every output clearly states that scores are triage indicators for human review, not definitive legal determinations.

### `scripts/run_verification.py`
CLI tool to run the entire pipeline end-to-end:
```bash
python scripts/run_verification.py
python scripts/run_verification.py --claim CLM-002
python scripts/run_verification.py --quiet
```

---

## 3. Test Suite Verification

A comprehensive pytest suite covers all new and existing components:
- `tests/test_claim_extractor.py` (9 tests)
- `tests/test_pdf_parser.py` (8 tests)
- `tests/test_retrieval.py` (34 tests)
- `tests/test_numeric_checks.py` (21 tests)
- `tests/test_verification.py` (19 tests)
- `tests/test_risk_score.py` (32 tests)

**Results:**
```
============================= 123 passed in 1.64s =============================
```

All 123 unit and integration tests pass successfully.
Dataset validation (`python scripts/validate_dataset.py`) verifies all 12 claims, 20 evidence items, and 10 hard cases with 0 errors.
