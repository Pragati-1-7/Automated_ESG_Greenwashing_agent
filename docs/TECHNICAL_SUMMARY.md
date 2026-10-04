# Automated ESG Greenwashing Detection & Verification Agent: Technical Summary (v2)

**Problem statement:** EY, "Automated ESG Greenwashing Detection & Verification Agent". **Status:** v2, October 2026.
All companies, filings and figures are synthetic; outputs are triage signals for a human reviewer, not legal findings.

## 1. What the system does

A company's sustainability report (PDF) goes in. The system extracts every ESG claim and decides which ones can be checked. It breaks complex claims into atomic sub-claims and retrieves external evidence at runtime from regulator-style data services. A decision engine then judges each claim **ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE** (or **NOT_CHECKABLE** for cheap talk and future targets). Out come a 0-100 Greenwashing Risk Score per claim and per company, a technical report, and a step-by-step audit trail streamed live to the UI.

## 2. Agent design

The pipeline is a LangGraph `StateGraph` (`app/graph/pipeline.py`). Every node is one agent in `app/agents/`. Checkable claims fan out in parallel with the `Send` API into a per-claim sub-graph.

| Stage | Agent | What decides | Grounding (paper) |
|---|---|---|---|
| Ingest | `ingest/pdf.py` | Layout-aware PyMuPDF parsing: pages, sections, column/page-break re-joining, drop caps | - |
| Resolve | `resolver.py` | Registry lookup tool + Jev "same legal entity?" | entity resolution |
| Extract | `extractor.py` | Jev *Noul* "is this a company ESG claim?" + *Choice* over 20 metrics, for every candidate sentence | Stammbach et al., ACL 2023 |
| Triage | `triage.py` | Jev: action *implemented / planning / indeterminate*, vagueness, checkability, materiality | A3CG (Ong et al., 2025) |
| Decompose | `decomposer.py` | Clause split, then Jev types each atomic sub-claim (metric + check type: pct_change, share, zero_events, geo, certificate...) | AFEV (2025), ProgramFC (ACL 2023) |
| Route | `router.py` | One Jev *Noul* per source (8 sources) gives a probability per source; sources above 0.45 are queried | DEFAME (ICML 2025) |
| Investigate | `investigator.py` + `evidence.py` | Calls source tools over HTTP, formats citeable evidence, runs the calculator; Jev "is this sufficient?" and widens for a second round if not | FIRE (NAACL 2025) |
| Judge | `judge.py` | Per evidence: Jev relevance gate + stance (support / contradict / insufficient); then per sub-claim | MiniCheck (EMNLP 2024) |
| Verdict | `judge.py` | Jev *Choice* over the 3 verdicts with source-reliability guidance, plus a severity *Score*; grounding guard + citation validator | EmeraldMind (2025) abstention |
| Risk | `risk.py` | Logistic model over decision-engine outputs, weights fitted on the benchmark | PS: "algorithmic aggregation" |
| Report | `reporter.py` | Markdown summary, per-claim reasoning, full audit trail | - |

**Decision engine: TypeSafe Jev.** Every judgement is a typed question (Noul = probability of yes, Choice = one option with per-option probabilities, Score = ordered scale). Agents never parse free-form model text to decide anything, and every decision carries a probability that the UI shows. The generative LLM slot (`app/llm/providers.py`) only writes text: clause splits, search queries and explanations. It defaults to a deterministic mock that writes **only from facts it is handed**; Groq can be switched on for prose.

**Tools, not rules.** Evidence comes from `mock_sources/`, a separate FastAPI service shaped like real providers (`/sebi/brsr`, `/cpcb/ocems/exceedances`, `/regulatory/actions`, `/gfw/alerts/near`, `/registry/rec`, `/assurance/statements`, `/news/search`). It is also exposed as an MCP server. All arithmetic (percentage change, share, multiple, unit conversion, gap between claimed and filed) runs in a calculator tool whose expression is shown in the audit trail. The decision engine reads those results, so arithmetic is never left to a language model.

**Hallucination control.**

1. Verdict states contain only retrieved evidence.
2. A relevance gate stops off-topic negative evidence from moving a verdict.
3. A grounding guard abstains when no decisive evidence was retrieved.
4. A citation validator asserts every cited evidence id was actually fetched.
5. Report text is generated only from structured facts.

## 3. Prompt methodology

All decision questions are versioned in `app/agents/prompts.py` (`PROMPT_VERSION`).

- Questions are written as typed decisions with explicit option definitions. For example, the verdict options define CONTRADICT as "reliable external evidence shows the claim is false, overstated or misleading; tier 1-2 records outweigh company press releases".
- Each question sees the context it needs as a structured state: claim, period, tier-labelled evidence with endpoints, and calculator output.
- Tolerance and period rules live in the option text ("small rounding differences within about 3% still count as confirmation"; "covers a different period -> insufficient").
- Every answer is recorded (record/replay cassette, keyed by a hash of state + questions). Any run, including the full test suite, can be replayed offline and bit-for-bit.

## 4. Data

`data_gen/` generates one consistent synthetic world from `data_gen/spec.py`:

- 150 fictional Indian listed companies and 422 facilities with coordinates
- 900 BRSR Core-style filings (FY2020-25) and 2,532 facility GHG rows
- 2,000 OCEMS exceedances, 400 regulator actions and 1,500 forest-loss alerts
- 932 REC registry rows, 409 assurance statements and 500 news/PR articles

There are about 9,750 rows in total.

The benchmark is 200 labelled claims (140 train / 60 test) over 15 greenwashing types, ranging from inflated reductions to geo contradictions. Four 23-28 page report PDFs (HTML to PDF via Chromium) carry 46 planted claims:

- a greenwasher (steel)
- a mixed company (cement)
- an honest company (textiles)
- a company absent from every source

## 5. Results

| Evaluation | Result |
|---|---|
| Benchmark, test split (60) | accuracy 1.00, macro-F1 1.00, coverage 1.00, citation precision 0.90 |
| Benchmark, all 200 cases | accuracy 0.98, macro-F1 0.98, citation precision 0.92 |
| **Held-out benchmark (fresh seed, never inspected, 172 cases)** | **accuracy 0.977, macro-F1 0.984**; all 4 errors are honest claims flagged CONTRADICT |
| Hand-written stress set (24 unseen phrasings) | 23/24 |
| Ablation: no retrieval | accuracy 0.35 |
| Ablation: news-only RAG (plain unstructured retrieval) | accuracy 0.45 |
| Demo PDFs end to end | extraction recall 46/46, verdict accuracy 46/46 |
| Company risk score | greenwasher 56 (High) > mixed 45 > honest 34 > unknown company 24 (Low, all insufficient) |
| Relevance gate (PDF ablation) | unrelated claims flagged CONTRADICT in the greenwasher's report: 5 without the gate, 2 with it |
| Risk model | logistic regression, AUC 0.99 train / 1.00 test |

Structured, multi-source retrieval is what makes the system work: going from news-only RAG to the full agent raises accuracy from 0.45 to 1.00. The second investigation round and the relevance gate add nothing on clean single-sentence benchmark claims. Their value shows on full reports, where claims are noisier.

## 6. Limitations (stated plainly)

- **Synthetic, self-built benchmark.** The world, the PDFs and the benchmark come from one generator. High scores show the method works on data whose ground truth is known, not real-world accuracy.
- **Test split was inspected.** The parser and prompt fixes (unit conversion, "than in FYxx" baselines, facility names) were made after looking at errors on all 200 cases, including test. The test score is therefore optimistic. The 13 errors seen before those fixes are listed in `docs/BENCHMARK_NOTES.md`.
- **Label noise.** Some benchmark labels are arguable. For example, a regulator show-cause notice "for stack exceedances" exists while the OCEMS log for the same year is empty.
- **Text and tables only.** Claims made only inside chart images are not read. Jev's context window is 32K tokens, so the states sent to it are compact by design.
- **Live decision engine.** Live runs need the Jev API key. Without it the system replays recorded answers and refuses unseen inputs rather than guessing.
- **Not real-world ready.** Real deployment would need real BRSR/CPCB/NGT data feeds behind the same tool interfaces, plus human review of every CONTRADICT before any external use.
