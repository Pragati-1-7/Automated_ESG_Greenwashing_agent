# System Architecture & Module Reality Check

**Purpose of this file:** give you (or anyone reviewing this project — including a
senior partner) a complete, accurate mental model of the system: what each piece
does, whether its logic is real or a placeholder, where it can silently degrade,
and proof that the backend actually runs rather than being simulated.

Every claim below was re-verified live while writing this file (see §5). Nothing
here is carried over from memory or an earlier session without re-checking.

---

## 1. System at a glance

```
        ┌─────────────────────┐
        │   Streamlit (8501)  │   streamlit_app/app.py
        │   dashboard/UI      │   -- pure renderer, computes nothing
        └──────────┬───────────┘
                   │ HTTP (requests library)
        ┌──────────▼───────────┐
        │   FastAPI (8000)     │   app/api/main.py
        │   /health /analyze   │   -- validates input, shapes HTTP responses,
        │   /demo/dataset      │      contains NO pipeline logic itself
        │   /claims/{id}       │
        └──────────┬───────────┘
                   │ Python function calls (same process)
        ┌──────────▼───────────┐
        │  Orchestration       │   app/api/pipeline.py
        │  (Step 6)            │   -- wires every stage below together
        └──────────┬───────────┘
                   │
   ┌───────────────┼────────────────────────────────────────────┐
   │               │                                            │
┌──▼────────┐ ┌────▼──────────┐ ┌──────────────┐ ┌──────────────▼─┐
│PDF parsing│ │Claim           │ │Checkability  │ │Query planning   │
│pdfplumber │ │extraction      │ │(rule engine) │ │(deterministic)  │
│(Step 2)   │ │Mock/Groq/Ollama│ │(Step 3)      │ │(Step 4)         │
└───────────┘ │(Step 2)        │ └──────────────┘ └────────┬────────┘
              └────────────────┘                            │
   ┌──────────────────────────────────────────────────────┐│
   │  Hybrid retrieval (Step 4): BM25 (always) + ChromaDB  ◄┘
   │  semantic (opt-in, off by default)                    │
   └───────────────────────────┬────────────────────────────┘
                                │
   ┌────────────────────────────▼───────────────────────────┐
   │  Verification + deterministic numeric checks (Step 5)   │
   │  -> ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE           │
   └────────────────────────────┬───────────────────────────┘
                                │
   ┌────────────────────────────▼───────────────────────────┐
   │  Risk scoring (Step 5): explainable 0-100, additive     │
   └────────────────────────────┬───────────────────────────┘
                                │
                    AuditRecord (full trace) -> JSON -> Streamlit
```

**One-sentence summary:** the system takes an ESG PDF, extracts claims, decides
which are specific enough to check, retrieves synthetic evidence for them,
compares claim vs. evidence with deterministic Python (never LLM arithmetic),
and returns an explainable risk score plus a full audit trail for human review.

---

## 2. Request lifecycle (what actually happens on "Analyze Report")

1. **Streamlit** (`streamlit_app/app.py`) sends a `multipart/form-data` POST to
   `http://<backend>/analyze` with the PDF bytes (or `use_demo=true`).
2. **FastAPI** (`app/api/main.py::analyze`) validates: is there a file or
   `use_demo`? Is it a real `.pdf`? Is it non-empty? Saves the upload to a
   `NamedTemporaryFile` on disk.
3. **Pipeline** (`app/api/pipeline.py::analyze_pdf_file`):
   a. `pdf_parser.parse_pdf()` — real `pdfplumber` extraction, page-by-page.
   b. If zero pages have extractable text → returns `status: "no_claims"` with an
      honest message (no fabricated claims).
   c. Picks an extraction provider: `mock` (offline, canned responses **only**
      for the exact bundled sample filename), or `groq`/`ollama` (real HTTP
      calls, configured via `.env`).
   d. `claim_extractor.extract_claims_from_pages()` — sends each page to the
      provider, parses JSON, validates against the `ClaimRecord` Pydantic
      schema. Invalid output is discarded and reported, never guessed.
   e. `build_audit_records()` runs, for **every** extracted claim:
      - `checkability.assess_checkability()` — rule-based CHECKABLE/NOT_CHECKABLE.
      - If CHECKABLE: `query_planner.generate_query_plan()` →
        `HybridRetriever.retrieve_for_claim()` (BM25 always; ChromaDB only if
        `use_semantic=True`) → `verification.verify_claim()` (rule-based
        ALIGN/CONTRADICT/INSUFFICIENT_EVIDENCE, using
        `numeric_checks.run_numeric_check()` for arithmetic) →
        `risk_score.calculate_risk_score()`.
      - If NOT_CHECKABLE: only the checkability result is attached; no
        retrieval, verification, or score is computed (there is nothing to
        verify against).
4. **FastAPI** returns one JSON object: `status`, `summary`, `audit_records[]`,
   plus the synthetic-data notice and disclaimer on every response.
5. **Streamlit** renders that JSON — executive summary, claims table, and
   per-claim tabs. It computes nothing itself.

---

## 3. Module-by-module reality check

This is the section you asked for explicitly: what's real, what's a documented
stub, and what silently degrades.

| Module | What it does | Real logic or stub? | Fails loud or silent? |
|---|---|---|---|
| `pdf_parser.py` | PDF → page-aware text via `pdfplumber` | **Real** | Loud — raises `PDFParsingError` on any unreadable/corrupt PDF |
| `claim_extractor.py` | Sends page text to an LLM provider, validates JSON output | **Real** | Loud — invalid claims are dropped and reported in `extraction_errors`, never silently kept |
| `llm_providers.py` — Mock | Deterministic canned responses | **Documented stub**, not hidden — returns canned claims *only* for the exact bundled sample filename; zero claims for anything else | N/A by design |
| `llm_providers.py` — Groq | Real HTTP call to `api.groq.com` | **Real** | Loud — raises `LLMConfigurationError`/`LLMProviderError` on missing key or API failure; never falls back to mock silently |
| `llm_providers.py` — Ollama | Real HTTP call to a local Ollama server | **Real** | Loud — same as Groq |
| `checkability.py` | Rule-based CHECKABLE/NOT_CHECKABLE decision | **Real**, fully deterministic | N/A (pure function, no I/O) |
| `query_planner.py` | Builds 2-4 search queries from claim fields | **Real**, fully deterministic | N/A |
| `bm25_retriever.py` | Keyword search via `rank_bm25` | **Real** | N/A (pure computation over local JSON) |
| `chroma_retriever.py` | Semantic search via ChromaDB + sentence-transformers | **Real when `use_semantic=True`**; a documented no-op stub (`return []`) when `use_semantic=False` (the default) | **Silent on internal failure — see §4, this is the one real finding** |
| `hybrid_retriever.py` | Merges/dedupes BM25 + semantic scores | **Real** | N/A |
| `numeric_checks.py` | Deterministic Python arithmetic (percent change, capacity, unit checks) | **Real** — never an LLM doing math | Loud where it matters; unapplicable checks are marked `skipped` with a reason, never silently passed |
| `verification.py` | Aggregates evidence into ALIGN/CONTRADICT/INSUFFICIENT_EVIDENCE | **Real**, rule-based | One narrow, *documented* simplification and one silent-on-corrupt-file spot — see §4 |
| `risk_score.py` | Explainable additive 0-100 score | **Real**, deterministic, hand-re-derivable from the factor table in its own docstring | N/A |
| `pipeline.py` (Step 6) | Orchestrates all of the above | **Real** | Loud — raises `PipelineError` with a specific message on any stage failure |
| `main.py` (Step 6) | FastAPI HTTP layer | **Real** | Loud — every failure maps to a specific HTTP status (400/404/422/500), never a silent 200 with fake data |

**Bottom line on fakery:** there is no module in this system that fabricates a
verdict, invents a number, or returns a fake "success" when something actually
failed. The Mock LLM provider is the one intentionally-fake component, and it
is the *opposite* of hidden fakery — it is deliberately restrictive (zero
claims for anything but the exact bundled file) specifically so it can never be
mistaken for a real result.

---

## 4. The two real fallback/transparency findings (not fixed yet — need your call)

### 4a. Silent semantic-retrieval failure (`chroma_retriever.py`, only matters if `use_semantic=True`)

```python
def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedEvidence]:
    ...
    try:
        results = self._collection.query(...)
    except Exception:
        return []          # <-- any internal failure looks identical to "no match"
```

If ChromaDB or the embedding model breaks internally (corrupted local index,
out-of-memory, a bad model download) while `use_semantic=True`, this returns an
empty list — indistinguishable from "genuinely no semantically similar
evidence." The pipeline keeps running (BM25 still works), so nothing crashes,
but a broken semantic layer and a working-but-unmatching one look the same in
the UI.

**Impact today:** none, because `use_semantic=False` is the default everywhere
(API, Streamlit sidebar default, and every test). This only becomes relevant if
someone explicitly turns semantic retrieval on.

**Recommended fix (not applied — this is Step 4/frozen code, flagging for your
sign-off rather than silently patching it):** log the exception and/or surface
a `semantic_retrieval_error` flag on the result so the UI can show "semantic
search failed, falling back to keyword-only" instead of silence.

### 4b. Silent corpus-relationship load failure (`verification.py`, import time)

```python
def _load_corpus_relationships() -> dict[str, ExpectedRelationship]:
    ...
    try:
        ...
    except Exception:
        return {}          # <-- a corrupted evidence.json is invisible here
```

If `data/evidence/evidence.json` were ever corrupted, this fails *safe* (an
empty mapping means the system treats relationships as unknown rather than
inventing SUPPORTS/CONTRADICTS), but it fails **silently** — nothing tells you
the corpus didn't load correctly. `scripts/validate_dataset.py` would actually
catch a corrupted `evidence.json` separately, so in practice this is
low-risk, but it's still a silent path worth knowing about.

**Recommended fix:** log a warning (not an exception) when this returns `{}`
instead of a populated mapping.

### 4c. One documented simplification, not a bug

`verification.py::_scope_matches()` ends with `return True  # default: give
benefit of the doubt at this step` when it can't confidently determine a
scope mismatch. This is called out in an inline comment in the source — it is
a known, intentional simplification (scope-ambiguity is explicitly listed as an
un-solved hard case, `HC-005`, in the dataset), not concealed behavior.

---

## 5. Live validation proof (re-run just now, not from memory)

```
$ python -m pytest -q
155 passed, 2 warnings in 2.07s

$ python scripts/validate_dataset.py
RESULT: PASS - dataset is structurally valid and ready for use.

$ python -m uvicorn app.api.main:app --port 8000     [separate real process, PID confirmed via tasklist]

$ curl http://127.0.0.1:8000/health
{"status":"ok","service":"esg-greenwashing-agent-api", ...}          HTTP 200

$ curl http://127.0.0.1:8000/demo/dataset
{"status":"ok", "summary": {"total_claims":12, "align_count":5,
 "contradict_count":2, "insufficient_evidence_count":3, ...}}         HTTP 200

$ curl -X POST http://127.0.0.1:8000/analyze -F "use_demo=false" \
    -F "file=@data/sample_pdfs/edge_cases/corrupted_not_a_real_pdf.pdf"
{"detail":"Could not read this PDF: Failed to open/parse PDF ... No /Root object!"}   HTTP 422

$ curl -X POST http://127.0.0.1:8000/analyze -F "use_demo=false" \
    -F "file=@data/sample_pdfs/edge_cases/blank_scanned_report.pdf"
{"status":"no_claims", "source_document":"blank_scanned_report.pdf", ...}  HTTP 200

$ curl http://127.0.0.1:8000/claims/DOES-NOT-EXIST
{"detail":"Claim 'DOES-NOT-EXIST' not found in the curated dataset."}      HTTP 404

$ curl http://127.0.0.1:8501    (Streamlit, pointed at the live backend above)
HTTP 200
```

**A real bug was found and fixed during this exact live test pass:** the
`/analyze` response for a non-demo upload was echoing the server's internal
temp-file name (e.g. `tmph7m_tdvs.pdf`) instead of the filename the user
actually uploaded. Root cause: `app/api/main.py` only overrode
`source_document` for the bundled-demo path. Fixed in `main.py`, and a
regression test was added
(`tests/test_edge_cases.py::test_analyze_response_echoes_original_filename_not_tempfile_name`)
so it cannot silently reappear. Re-verified live after the fix (shown above).
This is exactly the kind of thing that only surfaces when you actually hit the
running server over HTTP instead of trusting an in-process test client — which
is why this pass was done that way.

---

## 6. What "no fallback" means for this system, honestly, today

- **Steps 1, 2, 3, 5, and 6 are fully fail-loud.** Bad input produces a
  specific error (400/404/422/500) or an honest `"no_claims"` status with a
  human-readable reason — never a fabricated success.
- **Step 4's BM25 path is fully fail-loud** (pure computation, no network).
- **Step 4's semantic (ChromaDB) path has one silent-degrade spot** (§4a),
  but it is off by default and has never been exercised in production use of
  this app so far.
- **The Mock LLM provider is intentionally restrictive**, not intentionally
  deceptive: it only ever produces claims for the one file it was built for.

If you want, the next step is applying the two narrow logging fixes in §4 —
they're small, isolated, and don't touch any scoring/verdict logic, just make
existing silent paths visible.
