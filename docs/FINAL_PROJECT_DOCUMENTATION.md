# Automated ESG Greenwashing Detection & Verification Agent - Final Project Documentation

## 1. Problem Statement

Companies publish ESG (Environmental, Social, Governance) reports containing sustainability
claims - emission reductions, renewable energy usage, worker safety records, and more. Some
of these claims are accurate; others are vague, exaggerated, or contradicted by independent
evidence ("greenwashing"). Manually cross-checking every claim in every report against
regulatory filings, audits, and news is slow, expensive, and inconsistent between reviewers.

This project addresses the EY problem statement: **"Automated ESG Greenwashing Detection &
Verification Agent."**

## 2. Project Objective

Build a decision-support system that takes a company's ESG report (PDF) and, for each
falsifiable claim it contains, produces an explainable, evidence-based triage signal that
helps a human reviewer decide where to focus scrutiny - without pretending to replace that
reviewer's judgment.

## 3. Why Greenwashing Detection Matters

Greenwashing erodes trust in sustainability disclosures, misleads investors and consumers,
and undermines genuine climate/ESG progress. Regulators increasingly require substantiation
of ESG claims. An automated first-pass triage tool lets human auditors and analysts prioritize
their limited review time on the claims most likely to need it, instead of reading every claim
with equal depth.

## 4. Proposed Solution

A modular, fully explainable, deterministic-where-it-matters pipeline:

1. Extract claims from the report text (LLM-assisted, but never allowed to fabricate fields).
2. Decide, with a transparent **rule engine** (not an LLM), whether each claim is specific
   enough to be checked at all.
3. For checkable claims, generate targeted search queries and retrieve evidence using hybrid
   (keyword + semantic) search.
4. Compare the claim to its evidence using **rule-based verification** plus **deterministic
   Python arithmetic** (never LLM arithmetic) for numeric claims.
5. Aggregate everything into an explainable 0–100 **Greenwashing Risk Score**, with every point
   traceable to a named factor.
6. Present the full chain of reasoning as an audit trail so a human can verify *why* the system
   reached its conclusion.

## 5. Complete System Workflow

```
Company ESG PDF
      -> PDF Parsing (pdfplumber, page-aware)
      -> ESG Claim Extraction (LLM: Mock / Groq / Ollama)
      -> Claim Checkability (rule-based)
      -> Query Planning (deterministic)
      -> Evidence Retrieval (BM25 + ChromaDB hybrid)
      -> Evidence Verification (rule-based, tier-weighted)
      -> Deterministic Numerical Checks (Python arithmetic)
      -> ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE verdict
      -> 0-100 Greenwashing Risk Score (explainable, additive factors)
      -> Explainable Audit Trail
      -> FastAPI Backend
      -> Streamlit Dashboard
```

## 6. Step 1 - Dataset / Foundation

- Pydantic schemas (`app/utils/schemas.py`) define every data structure used by every later
  phase: `ClaimRecord`, `EvidenceRecord`, `CheckabilityResult`, `RetrievalResult`,
  `VerificationResult`, `RiskScoreResult`, `AuditRecord`, and more.
- A curated synthetic dataset: 12 ESG claims (`data/claims/claims.json`), 20 evidence records
  spanning all five source-reliability tiers (`data/evidence/evidence.json`), and 10
  deliberately tricky "hard cases" (`data/test/hard_cases.json`) covering vague claims,
  false-but-precise claims, period/baseline/scope/unit mismatches, and more.
- `scripts/validate_dataset.py` enforces schema compliance, ID uniqueness, and referential
  integrity between claims and evidence.

## 7. Step 2 - PDF Parsing & Claim Extraction

- `app/extraction/pdf_parser.py` uses `pdfplumber` to turn a PDF into page-aware text, keeping
  every page (even empty ones) so page numbers never drift.
- `app/extraction/claim_extractor.py` sends each page's text to an LLM provider (Groq, Ollama,
  or a deterministic Mock) with a strict prompt (`prompts/claim_extraction_prompt.md`) that
  forbids inventing field values. Output is parsed as JSON and validated against
  `ClaimRecord` - anything invalid is reported and skipped, never silently guessed.
- The Mock provider is deterministic and offline: it is used for the bundled sample PDF
  (`data/sample_pdfs/synthetic_esg_report.pdf`, a fictional "GreenLeaf Industries Ltd." report)
  and for automated tests, so the whole system is runnable with zero API keys.

## 8. Step 3 - Checkability

`app/evaluation/checkability.py` answers exactly one question per claim: *does this claim
contain enough specific information (metric, value, unit, scope, reporting period, etc.) to be
worth sending to evidence retrieval at all?* This is a **rule-based** engine, not an LLM call -
by the time a claim reaches this stage its fields are already structured and already `None`
when genuinely absent, so checkability reduces to a structural completeness question that a
deterministic rule set answers more reliably, cheaply, and reproducibly than an LLM would.
Every decision traces to a named rule (`RuleCheckResult`) with a human-readable reason.

## 9. Step 4 - Evidence Retrieval

- **Query Planner** (`app/retrieval/query_planner.py`): deterministically builds 2-4 targeted
  search queries per checkable claim from its structured fields.
- **BM25 Retriever** (`app/retrieval/bm25_retriever.py`): fast, offline lexical search - good
  at exact matches on company names, years, scope labels, and units.
- **ChromaDB Retriever** (`app/retrieval/chroma_retriever.py`): semantic search using the local
  `all-MiniLM-L6-v2` sentence-transformers embedding model - good at paraphrased evidence.
- **Hybrid Retriever** (`app/retrieval/hybrid_retriever.py`): normalizes both scores to [0,1]
  and combines them as `0.6 * BM25 + 0.4 * semantic`, deduplicating by evidence ID and
  re-ranking. Every score (BM25, semantic, combined) is kept visible for auditability.

## 10. Step 5 - Verification & Risk Scoring

- **Deterministic Numerical Checks** (`app/evaluation/numeric_checks.py`): all arithmetic
  (percentage-reduction comparisons, capacity checks, unit/scope validation) is plain Python,
  never an LLM guess, with a documented tolerance (default 5%).
- **Verification Engine** (`app/evaluation/verification.py`): aggregates retrieved evidence,
  weighting higher-authority source tiers more heavily (a Tier 1 regulatory filing can override
  several lower-tier sources), and produces one of `ALIGN`, `CONTRADICT`, or
  `INSUFFICIENT_EVIDENCE` with a plain-English reason.
- **Risk Scoring** (`app/scoring/risk_score.py`): an explainable, additive 0–100 score. Every
  point is attributed to a named factor (e.g. numerical inconsistency, scope mismatch, weak
  evidence, baseline mismatch) with its own reason string, banded into Low / Moderate / High /
  Very High. This is a **triage indicator**, never described as a probability or legal verdict.

## 11. Step 6 - Final Application

Step 6 adds the application layer around the unchanged Steps 1–5 backend:

- **`app/api/pipeline.py`** - the orchestration layer. `build_audit_records()` runs every
  existing stage (checkability -> retrieval -> verification -> risk scoring) over a list of
  claims and returns one `AuditRecord` per claim, including `NOT_CHECKABLE` claims (with only a
  checkability result, so the UI can explain why a claim was excluded). `analyze_pdf_file()`
  wires in PDF parsing and claim extraction ahead of that. `analyze_dataset()` runs the curated
  `data/claims/claims.json` dataset directly, which reliably demonstrates all three verdict
  types since its evidence corpus was authored to match it.
- **`app/api/main.py`** - a thin FastAPI layer (`/health`, `/analyze`, `/demo/dataset`,
  `/claims/{claim_id}`) that validates input and shapes HTTP responses; it contains no
  pipeline logic of its own.
- **`streamlit_app/app.py`** - a professional dashboard that calls the FastAPI backend over
  HTTP and renders exactly what it returns: executive summary, claims table, per-claim detail
  (checkability / evidence / verification / numerical checks / risk score / full audit trail).
  No verdicts or scores are computed in the frontend.

## 12. System Architecture

```
Streamlit (streamlit_app/app.py)
        | HTTP (requests)
FastAPI (app/api/main.py)
        |
Pipeline orchestration (app/api/pipeline.py)
        |
PDF Parser -> Claim Extractor -> Checkability -> Query Planner
   -> Hybrid Retriever (BM25 + ChromaDB) -> Verification
   -> Numerical Checks -> Risk Scoring -> Audit Trail
```

## 13. Technology Stack

| Layer | Technology |
|---|---|
| Data models | Pydantic |
| PDF parsing | pdfplumber |
| LLM inference | Groq / Ollama / deterministic Mock |
| Checkability | Rule-based Python engine |
| Keyword search | rank_bm25 |
| Vector search | ChromaDB + sentence-transformers |
| Numeric checks | Deterministic Python arithmetic |
| Verification & risk scoring | Rule-based Python engines |
| Backend API | FastAPI |
| Frontend | Streamlit |
| Testing | pytest |

## 14. BM25 Explanation

BM25 (Best Matching 25) is a classic keyword-ranking function that scores how well a document
matches a query based on term frequency, inverse document frequency, and document length
normalization. It excels at exact-term matches (company names, "Scope 1", "FY2024",
"tCO2e") which are common and important in ESG text, is fully deterministic, and requires no
model download - making it the reliable offline default in this project.

## 15. ChromaDB Explanation

ChromaDB is a lightweight vector database. Evidence text is embedded into a dense vector using
a local sentence-transformers model (`all-MiniLM-L6-v2`), and queries are embedded the same
way; retrieval ranks evidence by cosine similarity. This captures meaning-level similarity even
when exact wording differs (e.g. "carbon emissions" vs. "GHG discharge"), complementing BM25's
exact-match strength.

## 16. Hybrid Retrieval Explanation

Both retrievers' scores are normalized to `[0, 1]` and combined as
`combined_score = 0.6 * bm25_score + 0.4 * semantic_score` (weights documented and tunable in
`hybrid_retriever.py`). Results are deduplicated by evidence ID (keeping the best combined
score) and re-ranked. When semantic retrieval is disabled (the offline default), semantic
scores are 0 and the combined score equals the BM25 score - the same formula, just with a zero
semantic contribution.

## 17. Verification Methodology

For each checkable claim, retrieved evidence is grouped by its expected relationship to the
claim (supports / contradicts / partial / unrelated, informed by numeric checks and field
comparisons such as company, period, scope, unit, and boundary matches). Higher source-reliability
tiers are weighted more heavily - a single Tier 1 regulatory filing can outweigh several lower-tier
sources. The engine returns `ALIGN` when evidence supports the claim, `CONTRADICT` when
higher-authority evidence conflicts with it, and `INSUFFICIENT_EVIDENCE` when there isn't enough
reliable evidence either way. Every verdict carries a human-readable `reason` string generated
from the actual comparison, not a templated guess.

## 18. Numerical Verification

Numeric claims (e.g. "reduced Scope 1 emissions by 40%") are never verified by asking an LLM to
do arithmetic. Instead, `app/evaluation/numeric_checks.py` performs the actual Python
calculation (e.g. computing the percentage change implied by the evidence's reported before/after
values) and compares it to the claimed value within a documented tolerance (default 5%). Checks
that cannot be meaningfully applied (e.g. mismatched units) are marked `skipped` with a reason,
never silently passed or failed.

## 19. Risk Scoring Methodology

The Greenwashing Risk Score is a deterministic, additive 0–100 score. Each contributing factor
(e.g. numerical inconsistency, scope mismatch, weak/low-tier evidence, unsupported baseline) has
a documented maximum point contribution and a specific reason for why it applied to this claim.
The total is clamped to `[0, 100]` and banded: 0–29 Low, 30–59 Moderate, 60–79 High, 80–100 Very
High. It is explicitly **not** a probability and **not** a legal determination - see the
disclaimer carried on every `RiskScoreResult`.

## 20. Audit Trail

Every claim's `AuditRecord` links the full chain of intermediate results: the original claim
text, the checkability decision and its rule-by-rule breakdown, the search queries generated,
every piece of evidence retrieved with its individual and combined scores, the verification
verdict and its supporting/contradicting evidence, the numerical checks performed, and the final
risk score with its factor breakdown. Nothing in this chain is invented by the frontend - the
Streamlit "Audit Trail" tab renders the exact JSON the backend produced.

## 21. Testing Results

The project maintains a fully offline automated test suite (no external API calls). As of Step 6:

- Steps 1–5: 123 pre-existing tests (PDF parsing, claim extraction, checkability, retrieval,
  numerical checks, verification, risk scoring).
- Step 6 additions: pipeline orchestration tests (`tests/test_pipeline.py`) and FastAPI endpoint
  tests (`tests/test_api.py`), covering the health check, demo-mode analysis, PDF upload
  validation, the curated-dataset endpoint, single-claim lookup, and the "no claims extracted"
  and "unknown claim id" error paths.

Run `python -m pytest -q` to reproduce.

## 22. Current Limitations

- The evidence corpus is **synthetic** - authored for development/testing, not real regulatory
  or news data. This is clearly labeled throughout the UI and API responses.
- Claim extraction quality depends on the chosen LLM provider; the offline Mock provider only
  produces claims for the bundled sample PDF (by design - it must never fabricate matching
  content for an arbitrary uploaded document).
- Verification and risk scoring are rule-based triage signals, not adjudications; every result
  is meant for human review before any conclusion is acted on.
- Uploaded PDFs from companies outside the curated dataset will typically return
  `INSUFFICIENT_EVIDENCE` for most claims, since the synthetic evidence corpus only covers the
  dataset's fictional companies - this is expected behavior for an academic prototype, not a bug.

## 23. Future Scope

- Connect the retrieval layer to real, verified external ESG/regulatory data sources.
- Expand the evidence corpus and formally benchmark against the 10 held-out hard cases.
- Add support for additional claim types and multi-document (multi-year) comparison.
- Persist analysis runs so a report can be revisited without re-uploading the PDF.
