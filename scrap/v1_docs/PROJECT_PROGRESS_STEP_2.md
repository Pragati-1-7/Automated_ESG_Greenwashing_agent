# Project Progress — Step 2: PDF Parsing + ESG Claim Extraction Engine

**Project:** Automated ESG Greenwashing Detection & Verification Agent
**Author:** Pragati (B.Tech CSE, 2nd Year)
**Step:** 2 of the overall project plan (builds directly on Step 1)

---

## 1. Step 2 Objective

In Step 1, I set up the repository structure, the Pydantic data schemas,
and a small synthetic dataset so I had something concrete to validate the
project's data model against. Step 1 did not touch any real documents — it
was pure scaffolding.

The objective of Step 2 was narrow and specific: **take a PDF sustainability
report and turn it into structured, validated ESG claims.** Nothing more.
I deliberately did not touch retrieval, verification, scoring, or the UI —
those are later phases and depend on Step 2 working correctly first.

## 2. What I Implemented

- A page-aware **PDF parser** using `pdfplumber` that reads a PDF and
  returns one `PageText` object per page, preserving page number and
  source filename.
- A **claim extraction engine** that sends each page's text to an LLM
  (or a mock stand-in) with a carefully constrained prompt, parses the
  JSON it returns, and validates every claim against my existing
  `ClaimRecord` Pydantic schema from Step 1.
- A **provider-agnostic LLM architecture**: I built a small abstract
  `BaseLLMProvider` interface with three implementations — `GroqLLMProvider`,
  `OllamaLLMProvider`, and `MockLLMProvider` — so the extraction code never
  has to know or care which backend is actually being used.
- A **deterministic mock mode** that returns pre-written, clearly-labelled
  responses instead of calling any real LLM, which is what my automated
  tests run against.
- A **synthetic ESG PDF** (`synthetic_esg_report.pdf`) for a fictional
  company, "GreenLeaf Industries Ltd.", containing 10 claims that
  deliberately cover the variety of cases my system needs to handle:
  numeric emissions figures, percentages, vague commitments, future
  targets, a claim with no stated baseline, Scope 1/2/3 references, and
  claims with an explicit reporting period.
- A **claim extraction prompt** written as its own Markdown file rather
  than buried in Python, so it can be read and edited independently of code.
- A **minimal, justified schema extension** to `ClaimRecord` (details below).
- An **evaluation script** that computes precision/recall on claim
  identification and per-field accuracy on the fields that matter most
  (metric, value, unit, scope, reporting_period, baseline_year).
- **17 automated tests** covering the parser and the extractor, including
  malformed JSON, invalid enum values, empty pages, and character-offset
  lookup.

## 3. PDF Parsing Methodology

`app/extraction/pdf_parser.py` opens the PDF with `pdfplumber` and walks
through every page individually, calling `page.extract_text()` on each one.
I made a deliberate design choice here: **a page with no extractable text
still gets a `PageText` entry with an empty string**, instead of being
silently skipped. If I dropped empty pages, every page number after that
one would become misaligned, and page-number traceability (which the
whole downstream pipeline depends on) would be wrong. A single malformed
page also doesn't crash the whole parse — I catch extraction errors per
page and record an empty page rather than losing the entire document.

## 4. Why pdfplumber Was Selected

The Step 1 project plan already named `pdfplumber` as the intended parser,
and after comparing it briefly against alternatives (PyPDF2/pypdf), I kept
it because it preserves reading order and plain paragraph text more
reliably for report-style PDFs, which matters a lot when I need to hand
clean sentences to an LLM.

## 5. LLM Claim Extraction

`app/extraction/claim_extractor.py` is the core of Step 2. For each page:

1. It builds a system + user prompt from `prompts/claim_extraction_prompt.md`.
2. It sends that prompt to whichever `BaseLLMProvider` was passed in.
3. It parses the provider's raw text response as JSON (stripping markdown
   code fences defensively, since some LLMs add them even when told not to).
4. It validates every extracted claim dict against `ClaimRecord`.
5. If the JSON is malformed, it retries **once** with an added instruction
   to return valid JSON — never more than once, to avoid infinite retry loops.
6. If a claim still fails Pydantic validation after that, I record the
   error and move on rather than crashing the whole page.

I understand this makes the pipeline more of a "best effort with a clear
error trail" than a system that guarantees success on every page — that is
intentional. A ClaimRecord that fails validation should never be silently
force-fitted into the schema.

## 6. Prompt Engineering Methodology

The prompt in `prompts/claim_extraction_prompt.md` was the part I iterated
on most carefully, because the single biggest risk in this whole project is
an LLM inventing facts. The prompt repeatedly instructs the model to:

- return `null` for any field it cannot support directly from the text,
- never invent a value, unit, year, scope, baseline, or boundary,
- preserve the claim's exact original wording rather than paraphrasing,
- distinguish a past/present *result* from a future *target*, and
- classify checkability based on whether enough specific information
  (a number, a unit, a period) is present to make the claim verifiable.

I kept the prompt in its own file instead of embedding it as a Python
string so that it stays reviewable and editable on its own, and so future
phases (or a professor reviewing my prompt design) don't have to dig
through extraction code to find it.

## 7. Claim Schema

I used the existing `ClaimRecord` schema from Step 1 rather than creating a
second, competing schema, exactly as the Step 2 brief required. I inspected
every field before touching anything.

## 8. Pydantic Validation

Every single claim returned by an LLM (real or mock) passes through
`ClaimRecord(**record_dict)` before it is accepted anywhere downstream.
Malformed JSON, invalid enum values (e.g. an invented `claim_type`), and
missing required fields are all caught explicitly by `pydantic.ValidationError`
and reported — I never wrap them in a bare `except: pass` that would hide
the problem.

## 9. Source Traceability

Every `ClaimRecord` extracted in Step 2 preserves `source_document` and
`page_number`. I also added optional `char_start`/`char_end` fields so a
claim can be traced to its exact character span within the page text. One
practical wrinkle I ran into: `pdfplumber` inserts a newline wherever a
PDF line-wraps, which can land in the middle of a sentence. My offset
lookup normalizes runs of whitespace to single spaces on both the page
text and the claim text before searching, so offsets are computed against
the *normalized* text, not the raw byte-for-byte PDF output. If a claim's
exact wording can't be found (e.g. the LLM paraphrased slightly instead of
quoting verbatim), I return `(None, None)` rather than guessing at an
offset — a missing offset is honest; a wrong one is worse than none.

## 10. LLM Provider Architecture

I built three provider classes behind one shared interface
(`BaseLLMProvider.complete(system_prompt, user_prompt) -> str`):

- `GroqLLMProvider` calls Groq's OpenAI-compatible chat completions endpoint
  using plain `requests` calls (no SDK dependency).
- `OllamaLLMProvider` calls a local Ollama server's `/api/chat` endpoint,
  the same way.
- `MockLLMProvider` returns deterministic, pre-written responses with no
  network call at all.

Both real providers raise a clear `LLMConfigurationError` if their required
environment variables (`GROQ_API_KEY`, `OLLAMA_BASE_URL`, `LLM_MODEL_NAME`)
are missing, instead of failing silently or falling back to mock behaviour.

## 11. Mock / Test Mode

`MockLLMProvider` exists specifically so my automated tests never require a
live API key. Every mock-produced `ClaimRecord` has `extraction_method`
set to the literal string `"mock"` and a `claim_id` prefixed `CLM-MOCK-`,
so mock output can never be mistaken for a real LLM result, either
programmatically or by a human skimming a file.

## 12. Test Cases

17 tests across two files:

- `tests/test_pdf_parser.py` — normal parsing, multi-page parsing, empty
  page handling, a zero/garbage-content PDF, a genuinely malformed PDF, a
  missing file, a wrong file extension, and source/page preservation on
  the real sample PDF.
- `tests/test_claim_extractor.py` — the full mock pipeline against the
  sample PDF, valid LLM output, malformed JSON, an invalid enum value,
  a non-list `claims` field, a vague/non-checkable claim, empty-page
  short-circuiting (the LLM is never called for a blank page), and both
  the found and not-found cases for character-offset lookup.

All 17 currently pass.

## 13. Evaluation Methodology

`scripts/evaluate_extraction.py` runs mock-mode extraction on the sample
PDF and compares it against a hand-written answer key
(`data/sample_pdfs/expected_claims.json`). It reports:

- **Precision** = matched claims / predicted claims
- **Recall** = matched claims / expected claims
- **Field accuracy** on `metric`, `value`, `unit`, `scope`,
  `reporting_period`, `baseline_year`, computed only over matched claims.

A predicted claim is "matched" to an expected claim if they're on the same
page and have identical normalized `original_text`.

## 14. Results

Running the evaluation script gives 100% precision, recall, and field
accuracy. I want to be transparent about what that number does and does
not mean: this evaluates the deterministic mock provider against itself,
so a perfect score is expected by construction, not evidence that a real
LLM would perform this well. It exists to prove the evaluation *mechanism*
works correctly and to act as a regression guard if the sample PDF or the
mock data ever drift out of sync with each other.

## 15. Limitations

- I have not yet run real-LLM extraction (Groq or Ollama) end-to-end,
  since that requires a live API key or a local Ollama installation that
  I don't have configured in this environment. The provider code is
  written and structurally sound, but only mock mode has actually been
  exercised here.
- The evaluation dataset is a single 4-page synthetic PDF with 10 claims —
  this is an initial sanity check on the pipeline, not a statistically
  meaningful benchmark of extraction quality.
- Character offsets are computed against whitespace-normalized text, so
  they don't map 1:1 onto raw byte offsets in the original PDF content
  stream — they're accurate for locating the claim within the page's
  logical text, not for byte-level PDF forensics.
- The extraction prompt has not been tested against messy real-world PDFs
  (scanned pages, multi-column layouts, tables) — the sample PDF is clean,
  single-column text.

## 16. Files Created

See the **Files Created** section at the end of this handoff for the full
list.

## 17. Files Modified

Only `app/utils/schemas.py`, `requirements.txt`, `.env.example`, and
`README.md` were modified. `scripts/validate_dataset.py`, `main.py`, and
all Step 1 dataset files were left untouched.

## 18. What I Learned

- Why you never let an LLM's raw output flow downstream un-validated —
  Pydantic validation is what turns "the model said something" into "the
  model said something my system can trust the shape of."
- Why page-level (not whole-document) processing matters for traceability:
  if I lose track of which page a claim came from, I can never point a
  human reviewer back to the original source.
- Why a mock mode isn't a shortcut but a real engineering requirement —
  without it, my test suite would either need a live API key (bad for
  CI/reproducibility) or would have to skip testing the extraction logic
  entirely.
- Schema evolution has to be backward-compatible: I couldn't just add
  fields wherever I wanted, I had to check that every one of Step 1's 12
  existing claim records still validated after my change, every time.

## 19. What Remains Incomplete

Everything described in the README's "NOT implemented yet" list: query
planning, retrieval (BM25 + ChromaDB), evidence-based verification,
numeric/capacity/year-on-year checks, the Greenwashing Risk Score,
FastAPI, and Streamlit. Real-LLM extraction (Groq/Ollama) is implemented
but not yet live-tested end to end.

## 20. Step 2 Conclusion

Step 2 delivers exactly what it set out to: a working, tested pipeline
that turns a PDF into validated, source-traceable `ClaimRecord` objects,
built on top of my existing Step 1 schema without breaking any of the
existing dataset. It's deliberately narrow in scope so I can be confident
this specific piece is solid before Step 3 builds retrieval on top of it.

---

## Understanding Step 2 (Beginner-Friendly)

**What is PDF parsing?**
A PDF file doesn't store text the way a `.txt` file does — it stores
drawing instructions ("put this letter at this x,y position"). A PDF
parser is a library that reads those instructions and reconstructs
readable text from them, page by page.

**What is claim extraction?**
Given a page of text, "claim extraction" means picking out the specific
sentences that make a factual ESG assertion (e.g. "we cut emissions by
18%") and pulling out the structured pieces of that sentence — the metric,
the number, the unit, the year — into separate fields a computer can
compare and check later.

**Why can't we simply send the whole PDF to an LLM?**
A few reasons: (1) reports can be dozens of pages, which may exceed what
a model can process reliably in one go; (2) if the model returns one big
blob of claims for the whole document, we lose track of exactly which
page each claim came from, which breaks traceability; (3) processing one
page at a time makes it much easier to catch and isolate errors — if page
7 produces bad output, pages 1-6 and 8+ are unaffected.

**What does LLaMA do?**
LLaMA (and Mistral) are open-weight large language models — they can read
natural-language text and follow instructions, similar to ChatGPT, but can
be run through a fast hosted API (Groq) or on your own machine (Ollama)
instead of only through one company's product. In this project, I'm using
one of them to read ESG report text and identify + structure the claims
in it.

**Why do we need structured JSON?**
A downstream Python program can't reliably work with "the claim is about
a 40% reduction in emissions" as a free-text sentence — it needs
`{"metric": "emissions", "value": 40, "unit": "%"}` so it can later compare
that number against evidence, do arithmetic, or filter by scope. JSON is
just a simple, computer-readable way to package that structure.

**What does Pydantic do?**
Pydantic checks that a piece of data actually matches the shape we expect
before we trust it — right types, required fields present, values from an
allowed list. If the LLM returns something malformed, Pydantic raises a
clear error immediately instead of that bad data quietly causing confusing
bugs three steps later in the pipeline.

**Why does source/page traceability matter?**
If my system eventually tells a human reviewer "this claim looks
contradicted by evidence," that reviewer needs to be able to open the
original PDF and see the claim in context — which page, which sentence —
to actually verify the finding. Without traceability, the tool becomes a
black box no one can audit.

**What is mock mode?**
Instead of calling a real (and possibly costly, possibly rate-limited, possibly
unavailable) LLM every time I run a test, mock mode returns fixed,
pre-written answers instantly and for free. It lets me test all the
*plumbing* around the LLM call (parsing, validation, error handling)
without needing the LLM itself to be involved every single time.

**Why do we evaluate precision and recall?**
Precision asks "of the claims my system found, how many were actually
real claims?" (not false alarms). Recall asks "of the real claims that
exist in the document, how many did my system actually find?" (not
missed). Both matter — a system with perfect precision but low recall is
missing things; a system with perfect recall but low precision is crying
wolf. Reporting both, rather than just one, gives a much more honest
picture of extraction quality.
