# Project Progress Report — Step 1
## Automated ESG Greenwashing Detection & Verification Agent

---

## 1. Project Title

**Automated ESG Greenwashing Detection & Verification Agent** — an agentic
AI system for triaging ESG sustainability claims against external evidence.

## 2. Introduction

For this project, I am working on the EY (Ernst & Young) problem statement
on automated ESG greenwashing detection. Companies increasingly publish
sustainability reports containing claims about emissions reductions,
renewable energy adoption, waste management, worker safety, and governance
practices. Some of these claims are well-supported, but others are vague,
exaggerated, or directly contradicted by regulatory data. My project aims
to build a system that helps a human reviewer quickly identify which claims
deserve closer scrutiny.

## 3. Problem Understanding

I identified the core problem as follows: ESG reports are long, and manually
cross-checking every claim against regulatory filings, audits, and news is
slow and inconsistent between reviewers. The goal is not to replace human
judgment, but to build a **decision-support tool** that:

- Pulls out claims that can actually be checked against evidence.
- Finds relevant external evidence for each claim.
- Compares the claim to the evidence in a structured, explainable way.
- Flags claims that look risky (contradicted, unsupported, or
  inconsistent) so a human reviewer can prioritize them.

I deliberately avoided treating this as a simple "ask an LLM if this is
greenwashing" task, because that approach would not be verifiable, would
be prone to hallucination, and would not produce an audit trail a reviewer
could trust.

## 4. Project Objective

My objective is to build a pipeline that:

1. Extracts falsifiable ESG claims from a report.
2. Scores whether each claim is actually checkable.
3. Plans targeted search queries per claim.
4. Retrieves evidence using both keyword and semantic search.
5. Verifies numeric claims using Python rather than LLM arithmetic.
6. Classifies each claim as ALIGN, CONTRADICT, or INSUFFICIENT EVIDENCE.
7. Produces a transparent, rule-based Greenwashing Risk Score (0–100).
8. Documents every step in an explainable audit trail.
9. Presents results through a Streamlit interface.

## 5. Why Greenwashing Detection Is Needed

I chose to frame this project around the idea that greenwashing erodes
trust in genuine sustainability progress and makes it harder for
investors, regulators, and the public to tell which companies are actually
reducing their environmental and social impact. A tool that can quickly
triage claims — flagging the ones most likely to be misleading — gives
human reviewers (auditors, journalists, regulators, ESG analysts) a way to
focus their limited time where it matters most, rather than reading every
report cover to cover.

## 6. Proposed Solution

My proposed solution treats claim verification as a structured pipeline
rather than a single AI judgment call. Each claim is broken down into its
component parts (metric, value, unit, scope, boundary, time period) before
any evidence is retrieved. This way, when I compare a claim to evidence, I
am comparing specific, structured fields — not just asking "does this
sound right?" I also decided that wherever a check can be done with plain
deterministic code (such as comparing two numbers, or checking a claimed
quantity against a registered capacity limit), it should be done that way
instead of relying on the LLM, because deterministic checks are more
reliable and easier to explain in an audit trail.

## 7. Planned Architecture

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

## 8. Step 1 Objectives

For this first step, I decided not to jump straight into building the AI
pipeline. Instead, I focused on laying a solid foundation:

- Set up a clean, modular repository structure that separates extraction,
  retrieval, evaluation, scoring, the API, and the dataset.
- Define structured data schemas (using Pydantic) for claims, evidence,
  and hard test cases, so every later phase of the project works with
  consistent, validated data.
- Build a small, carefully designed synthetic dataset that covers a range
  of real-world greenwashing patterns, rather than downloading a large,
  unfocused dataset that wouldn't actually test the system's reasoning.
- Write an automated validation script so I can check the dataset's
  integrity at any point as the project grows.

## 9. Repository Structure

I organized the repository as follows, keeping each concern in its own
folder so the project stays maintainable as it grows:

```
esg-greenwashing-agent/
├── app/
│   ├── extraction/     # Will hold the PDF parsing + claim extraction logic
│   ├── retrieval/      # Will hold the search agent + hybrid retrieval logic
│   ├── evaluation/     # Will hold entailment analysis + numeric verification
│   ├── scoring/        # Will hold the Greenwashing Risk Score logic
│   ├── api/            # Will hold the FastAPI backend
│   └── utils/          # Holds schemas.py — my Pydantic data models
├── data/
│   ├── claims/         # claims.json — my synthetic claims dataset
│   ├── evidence/       # evidence.json — my synthetic evidence dataset
│   └── test/           # hard_cases.json — my hard-case test dataset
├── prompts/             # Will hold LLM prompt templates
├── tests/               # Will hold automated tests
├── scripts/
│   └── validate_dataset.py   # My dataset validation script
├── streamlit_app/       # Will hold the Streamlit UI
├── docs/
│   └── PROJECT_PROGRESS_STEP_1.md   # This document
├── requirements.txt
├── .env.example
├── .gitignore
└── main.py
```

## 10. Technology Choices Made So Far

For Step 1, I only installed what I actually needed:

- **Pydantic** — to define strict, self-validating data models for claims,
  evidence, and hard cases. I chose Pydantic over plain dictionaries or
  dataclasses because it gives me automatic type checking and clear error
  messages when a record doesn't match the expected shape, which will be
  very useful once I start extracting claims automatically from PDFs.
- **python-dotenv** — to load configuration (like future API keys) from a
  `.env` file, keeping secrets out of the codebase and out of GitHub.

I deliberately postponed installing FastAPI, Streamlit, LangChain,
ChromaDB, BM25, sentence-transformers, pdfplumber, and the LLM provider
SDKs, because none of them are needed yet, and installing them now would
make the environment heavier and slower to set up without any benefit at
this stage.

## 11. Dataset Design

I designed three datasets, all clearly synthetic:

- **`claims.json`** (12 claims) — covers all three ESG pillars:
  Environmental (carbon emissions, renewable energy, waste/recycling,
  water, deforestation), Social (workforce diversity, worker safety), and
  Governance (regulatory disclosure). I included claims that should
  resolve to each of the four possible outcomes (ALIGN, CONTRADICT,
  INSUFFICIENT_EVIDENCE, and NOT_APPLICABLE for non-checkable claims), so
  that later evaluation isn't biased toward any single verdict.
- **`evidence.json`** (20 records) — I built evidence at every source-
  reliability tier described in the project plan: statutory/regulatory
  filings (Tier 1), regulator or tribunal records (Tier 2), audited
  reports (Tier 3), company PR (Tier 4), and news (Tier 5). Each evidence
  record is linked to a specific claim by `claim_id`. I also deliberately
  included a case (EVD-004/EVD-018) where a news article simply repeats a
  company's own press release, to later test that the system doesn't treat
  a derivative news story as an independent second source.
- **`hard_cases.json`** (10 cases) — I built cases that are specifically
  designed to expose weaknesses in a naive verification approach.

## 12. Dataset Examples

An example ALIGN case (`CLM-001`): GreenLeaf Renewables claims a 40%
reduction in Scope 1 emissions in FY2024 versus an FY2023 baseline. Both a
regulatory BRSR filing and an independent audit confirm this figure, so the
expected verdict is ALIGN.

An example CONTRADICT case (`CLM-005`): EcoCycle Waste Management claims it
processed 100,000 tonnes of plastic waste, but its regulatory
consent-to-operate certificate authorizes only 50,000 tonnes/year at that
facility — a direct capacity violation, so the expected verdict is
CONTRADICT.

An example INSUFFICIENT_EVIDENCE case (`CLM-004`): GreenLeaf's target of
100% renewable energy by 2030 is a future commitment with no independently
verified progress data yet, so there isn't enough evidence to say it will
or won't be achieved.

## 13. Hard-Case Design

I designed the hard cases around specific failure modes I anticipated for
a naive system:

- **True-but-vague** and **false-but-precise** claims, to test that the
  system doesn't confuse how confident/specific a claim sounds with
  whether it is actually true.
- **Period mismatches** and **baseline shifts**, to test that the system
  checks that evidence actually refers to the same reporting period and
  baseline year as the claim, not just the same company and metric.
- **Scope confusion** (Scope 1 vs. Scope 3) and **absolute vs. intensity**
  confusion, which are two of the most common real-world greenwashing
  patterns, where a technically true intensity or scope-limited figure is
  presented in a way that implies a broader improvement than actually
  occurred.
- **Boundary mismatches** (plant-level vs. company-wide), **unit
  mismatches** (MW vs. MWh), **unsupported future targets**, and
  **capacity mismatches**, each targeting a specific, realistic way a
  claim can look legitimate while being misleading.

## 14. Validation Methodology

I wrote `scripts/validate_dataset.py` to automatically check:

1. Every claim, evidence, and hard-case record matches its Pydantic schema
   (correct types, required fields present, valid enum values).
2. `claim_id`, `evidence_id`, and `case_id` values are unique within their
   respective files.
3. Every evidence record's `claim_id` actually points to a claim that
   exists (referential integrity).
4. Every hard case has a non-empty explanation of why it is difficult.
5. Checkability and expected verdict are logically consistent (a
   non-checkable claim cannot have a resolvable verdict, and a checkable
   claim cannot be marked "not applicable").

I ran the validator against my dataset and it passed all checks on the
first run, confirming 12 claims, 20 evidence records, and 10 hard cases are
structurally sound and ready to be used in later phases.

## 15. Files Created

- `app/utils/schemas.py`
- `data/claims/claims.json`
- `data/evidence/evidence.json`
- `data/test/hard_cases.json`
- `scripts/validate_dataset.py`
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `README.md`
- `main.py`
- `docs/PROJECT_PROGRESS_STEP_1.md` (this file)
- Package `__init__.py` files and placeholder folders for
  `app/extraction`, `app/retrieval`, `app/evaluation`, `app/scoring`,
  `app/api`, `prompts`, `tests`, and `streamlit_app`.

## 16. What I Learned

Working on Step 1 taught me the importance of designing data schemas
*before* writing pipeline logic. By defining exactly what a "claim" and a
piece of "evidence" look like up front, using Pydantic, I have a stable
contract that every future phase of the project (extraction, retrieval,
scoring) can rely on. I also learned why source reliability matters in
verification systems — not all evidence is equal, and a system that treats
a news article the same as a regulatory filing would be easy to mislead. Finally,
building the hard-case dataset helped me think concretely about the
specific ways greenwashing claims can be misleading (scope confusion,
baseline shifts, unit mismatches) rather than treating greenwashing
detection as one generic problem.

## 17. Current Limitations

- No PDF parsing or automated claim extraction exists yet — all claims in
  the dataset were written by hand as structured JSON, not extracted from
  real PDF reports.
- No retrieval, LLM reasoning, numeric verification, or risk scoring logic
  has been implemented yet — the `expected_verdict` field in the dataset
  is a hand-labeled ground truth for future evaluation, not something the
  system has computed itself.
- The dataset is entirely synthetic; real company data has not been
  collected or verified yet.
- There is no API or user interface yet.

## 18. What I Will Implement Next

In Step 2, I plan to begin building the claim extraction engine: parsing a
sample ESG PDF and using an LLM (with a carefully constrained prompt) to
extract claims into the same `ClaimRecord` schema I have already defined,
so the output of extraction plugs directly into the rest of the pipeline
without needing a schema change.

## 19. Step 1 Conclusion

Step 1 established the technical foundation for the rest of the project: a
clean, modular repository, validated Pydantic data schemas, and a small,
carefully designed synthetic dataset covering realistic greenwashing
patterns. Nothing in this step depended on an LLM or external API, which
means the foundation is fully reproducible and testable before any AI
components are introduced. I now have a stable base to build the
extraction and retrieval pipeline on top of in Step 2.

---

## Appendix: Understanding Step 1 (For My Own Reference)

This section explains the core concepts behind Step 1 in plain language,
for my own study and in case I am asked about them.

**What is a claim?**
A claim is one specific, extractable statement from an ESG report — for
example, "we reduced Scope 1 emissions by 40% in FY2024." In this project,
I don't just store the claim as raw text; I break it down into structured
fields (metric, value, unit, scope, time period) so the system can compare
it precisely against evidence later.

**What is evidence?**
Evidence is any external document or data point that can support or
contradict a claim — a regulatory filing, a regulator's inspection record,
an independent audit, a company's own press release, or a news article.
Each piece of evidence in my dataset is tagged with a source tier (1 =
most reliable, 5 = least reliable) because not all sources should be
trusted equally.

**Why do we need structured data?**
If claims and evidence were just blocks of free text, comparing them would
require the AI to do all the reasoning itself, with no way to check its
work. By extracting structured fields, most of the comparison (does the
company match, does the year match, does the number match) can be done
with simple, transparent, deterministic code — which is more reliable and
easier to explain than pure AI judgment.

**Why are hard cases important?**
Easy cases (a claim that is clearly true or clearly false) don't tell me
much about whether the system is actually reasoning correctly. The hard
cases are designed so that a system which only pattern-matches on
"company name + number" would get the wrong answer, while a system that
correctly checks scope, boundary, period, baseline, and units would get it
right. They are my way of testing the system's reasoning, not just its
memory.

**Why are we creating synthetic data?**
Building a dataset from real company reports would take much more time
than is available for this phase, and would require me to be certain
every fact I use is accurate and properly sourced. By using clearly
labeled synthetic data, I can design cases that cover the exact patterns
(scope confusion, baseline shifts, capacity mismatches, and so on) I want
the system to handle, without making unverified claims about real
companies.

**Why do we need validation?**
As the project grows, it becomes easy to accidentally introduce a typo, a
missing field, a duplicate ID, or an evidence record that points to a
claim that no longer exists. An automated validator catches these
mistakes immediately, rather than letting them silently break a later
phase of the pipeline.

**Why are we separating modules (extraction, retrieval, evaluation,
scoring)?**
Each of these stages solves a different problem and can be built, tested,
and even swapped out independently. For example, I could later replace
BM25 keyword search with a different retrieval method without needing to
touch the scoring logic, as long as the data passed between them still
matches the schemas I've defined.

**How does this dataset eventually feed into the AI pipeline?**
The `claims.json` dataset represents what the extraction engine *should*
eventually be able to produce automatically from a real PDF. The
`evidence.json` dataset represents what the retrieval agent *should*
eventually be able to find on its own. The `expected_verdict` field in
both `claims.json` and `hard_cases.json` is the ground truth I will use in
Step 6 to measure how accurately the finished system performs, by
comparing its computed verdicts against these hand-labeled expected
outcomes.
