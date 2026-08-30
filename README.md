# Automated ESG Greenwashing Detection & Verification Agent

## 1. Problem Statement

Companies publish ESG (Environmental, Social, Governance) reports containing
sustainability claims — emission reductions, renewable energy usage, worker
safety records, and more. Some of these claims are accurate; others are
vague, exaggerated, or contradicted by independent evidence ("greenwashing").
Manually checking every claim in every report against regulatory filings,
audits, and news is slow and inconsistent.

This project is based on the EY (Ernst & Young) problem statement:
**"Automated ESG Greenwashing Detection & Verification Agent."**

## 2. Project Objective

Build an agentic AI system that:

1. Extracts falsifiable ESG claims from a company's sustainability report.
2. Determines whether each claim is actually checkable.
3. Plans and runs targeted searches for external evidence.
4. Retrieves evidence using hybrid (keyword + semantic) search, prioritizing
   more reliable source types.
5. Compares each claim against the evidence it finds.
6. Performs numerical checks (unit-aware) in Python rather than trusting an
   LLM to do arithmetic.
7. Classifies each claim as **ALIGN**, **CONTRADICT**, or
   **INSUFFICIENT EVIDENCE**.
8. Aggregates results into a transparent, rule-based **Greenwashing Risk
   Score (0–100)**.
9. Produces a full, explainable audit trail for every claim.
10. Presents everything through a Streamlit interface.

> **Important limitation:** This is a **decision-support / triage system**
> for human reviewers. It is **not** a legal verdict on whether a company is
> greenwashing.

## 3. Planned Architecture

```
Company ESG PDF
        ↓
PDF Parser
        ↓
Claim Extraction Engine
        ↓
Structured ESG Claims
        ↓
Checkability Scorer
        ↓
Query Planning / Search Agent
        ↓
Hybrid Evidence Retrieval (BM25 + ChromaDB)
        ↓
Evidence Relevance Validation
        ↓
Contradiction / Entailment Analysis
        ↓
Numeric Verification (Python, unit-aware)
        ↓
Additional Non-AI Checks (capacity check, year-on-year check)
        ↓
Greenwashing Risk Scoring (rule-based)
        ↓
Explainable Audit Report
        ↓
FastAPI Backend + Streamlit UI
```

## 4. Current Project Status: **Step 1 Complete**

Step 1 built the **repository structure and dataset foundation only**.

**Implemented in Step 1:**
- Modular repository structure (see below).
- Pydantic schemas for Claim, Evidence, and Hard Case records.
- A curated synthetic dataset: 12 claims, 20 evidence records, 10 hard cases.
- An automated dataset validation script.
- Environment configuration templates (`.env.example`).

**NOT implemented yet (future phases):**
- PDF parsing / claim extraction from real documents.
- The query-planning search agent.
- Hybrid BM25 + ChromaDB retrieval.
- LLM-based entailment/contradiction analysis (LLaMA 3 / Mistral via Groq or Ollama).
- Numeric verification logic.
- Capacity check and year-on-year check logic.
- Greenwashing Risk Score calculation.
- FastAPI backend.
- Streamlit frontend.

## 5. Technology Stack

| Layer | Technology | Phase |
|---|---|---|
| Data models | Pydantic | Step 1 (done) |
| Config | python-dotenv | Step 1 (done) |
| PDF parsing | pdfplumber | Phase 2 |
| LLM inference | LLaMA 3 / Mistral via Groq and/or Ollama | Phase 2+ |
| Agent orchestration | LangChain (only where genuinely useful) | Phase 3+ |
| Vector search | ChromaDB + sentence-transformers | Phase 3 |
| Keyword search | rank_bm25 | Phase 3 |
| Storage | SQLite | Phase 3+ |
| Backend API | FastAPI | Phase 4 |
| Frontend | Streamlit | Phase 5 |
| Version control | Git / GitHub | Throughout |

## 6. Repository Structure

```
esg-greenwashing-agent/
├── app/
│   ├── extraction/     # Claim extraction engine (Phase 2)
│   ├── retrieval/      # Query planning + hybrid evidence retrieval (Phase 3)
│   ├── evaluation/     # Entailment/contradiction + numeric verification (Phase 3-4)
│   ├── scoring/        # Greenwashing Risk Score logic (Phase 4)
│   ├── api/            # FastAPI backend (Phase 4)
│   └── utils/          # Pydantic schemas (schemas.py) + shared helpers [ACTIVE]
├── data/
│   ├── claims/         # claims.json — synthetic ESG claims dataset [ACTIVE]
│   ├── evidence/       # evidence.json — synthetic evidence dataset [ACTIVE]
│   └── test/           # hard_cases.json — tricky edge-case dataset [ACTIVE]
├── prompts/             # LLM prompt templates (Phase 2+)
├── tests/               # Automated tests (Phase 2+)
├── scripts/
│   └── validate_dataset.py   # Dataset validation script [ACTIVE]
├── streamlit_app/       # Streamlit UI (Phase 5)
├── docs/
│   └── PROJECT_PROGRESS_STEP_1.md   # Faculty-facing progress documentation
├── requirements.txt      # Step 1 dependencies (future deps commented)
├── .env.example           # Environment variable template (no real keys)
├── .gitignore
└── main.py                # Placeholder entry point, runs the validator
```

## 7. Dataset Description

All data in this repository is **synthetic** — fictional companies and
figures created for development and testing. It is clearly labeled as such
in each file's `_meta` block and must never be presented as real-world data.

- **`data/claims/claims.json`** — 12 ESG claims covering Environmental
  (emissions, renewable energy, waste, water, deforestation), Social
  (workforce diversity, worker safety), and Governance (regulatory
  disclosure) topics. Includes checkable and non-checkable claims, and
  covers all four verdict outcomes (ALIGN, CONTRADICT,
  INSUFFICIENT_EVIDENCE, NOT_APPLICABLE).
- **`data/evidence/evidence.json`** — 20 evidence records spanning all five
  source-reliability tiers (regulatory filing → regulator record → audited
  report → company PR → news), linked to claims via `claim_id`.
- **`data/test/hard_cases.json`** — 10 deliberately tricky cases: vague
  claims, false-but-precise claims, period mismatches, shifted baselines,
  scope confusion, absolute-vs-intensity confusion, boundary mismatches,
  unit mismatches, unsupported future targets, and capacity mismatches.

## 8. Setup Instructions

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd esg-greenwashing-agent

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install Step 1 dependencies
pip install -r requirements.txt

# 4. Create your local environment file (optional at this stage)
cp .env.example .env
```

## 9. How to Validate the Dataset

```bash
python scripts/validate_dataset.py
```

This checks: schema compliance (via Pydantic), ID uniqueness, referential
integrity between evidence and claims, and required-field completeness. It
prints a PASS/FAIL report and a summary of the dataset composition.

You can also run:

```bash
python main.py
```

which prints the current project status and runs the same validation.

## 10. Future Development Phases

- **Phase 2:** PDF parsing + claim extraction engine.
- **Phase 3:** Query planning agent + hybrid (BM25 + ChromaDB) evidence retrieval.
- **Phase 4:** Numeric verification, capacity/year-on-year checks, risk scoring, FastAPI backend.
- **Phase 5:** Streamlit UI.
- **Phase 6:** End-to-end evaluation against the held-out hard-case dataset.

## 11. Important Limitation

This system is a **triage / decision-support tool** intended to help a
human ESG reviewer prioritize which claims deserve closer scrutiny. It does
**not** produce a legal or definitive determination that a company is
greenwashing, and every verdict is meant to be reviewed by a human before
any conclusion is acted on.
