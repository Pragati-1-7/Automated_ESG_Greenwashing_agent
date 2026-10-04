# Honest evaluation and how to scale it

Short version: the pipeline is sound, and it works on data it has never seen **from the same generator**. It has not been tested on real company reports or real regulator data, and that is the gap that matters. Numbers come from `benchmark/robustness_latest.json`, `benchmark/results_latest.json` and `benchmark/reports_eval.json`.

## 1. Results

| Test | What it checks | Result |
|---|---|---|
| Main benchmark, 200 cases | the set I tuned on (I saw these errors while fixing) | 196/200 = 0.98 |
| **Held-out benchmark, 172 fresh cases** | new seed, never looked at, overlapping texts removed | **0.977 accuracy, macro-F1 0.984** |
| **Hand-written stress set, 24 claims** | phrasings the generator never makes: paraphrase, "a third", "half", lakh units, negation, typo'd and look-alike company names, compound claims, unit traps, period traps | **23/24** |
| 4 demo PDFs, end to end | extraction + verdicts on 23-28 page reports | 46/46 found, 46/46 correct |
| Bad inputs | blank/scanned, corrupted, non-ESG, renamed PDFs | errors are clean (no crash); non-ESG gives 0 claims; unknown company gives only INSUFFICIENT / NOT_CHECKABLE |
| Decision-engine stability | same 8 questions asked 3 times live, no cache | 8/8 identical labels, max probability wobble 0.08 |
| Cost and speed, cold | one 28-page report, nothing cached | 33 s, 450 Jev calls, ~377K input tokens, about $0.02 |
| Ablations | what each part is worth | no retrieval 0.35, news-only RAG 0.45, full system 1.00 (test split) |

## 2. What the errors tell us

- **Every held-out error is the same kind:** an honest claim called CONTRADICT (4 of 172). ALIGN recall is 0.93, CONTRADICT precision 0.94. The system leans suspicious. For a triage tool that's the safer side, but it still means false alarms.
- **The stress miss:** "emissions per crore have come down by roughly 14% over five years". "Five years" is not turned into FY2020, so there is no baseline, the comparison goes wrong, and the verdict is CONTRADICT.
- **Full reports:** the greenwasher's report also gets 2 extra CONTRADICTs on broad statements ("mine plans are reviewed..."). They are defensible but noisy.

## 3. Fundamentals: be ready for these questions

1. **"Isn't the data made up?"** Yes. The world, the PDFs and both benchmarks come from one generator, so the system knows the schema the data uses. The high scores prove the method works where truth is known, not real-world accuracy.
2. **"Where is the intelligence vs rules?"** Every judgement is a Jev probability: claim or not, action type, metric, sources, relevance, stance, verdict, severity. Code still has deterministic parts:
    - thresholds (0.6 / 0.45 / 0.5)
    - a regex period/number/unit parser
    - a regex clause splitter
    - one evidence builder per source

    These are tools and plumbing. A jury may still call the parser "rules", and that's fair.
3. **"Why not just ask an LLM 'is this true?'"** With no retrieval it gets 0.35. A plain news RAG gets 0.45. Structured multi-source retrieval plus calculator plus decision engine gets 0.98.
4. **"How do you stop hallucination?"** Three mechanisms:
    - verdicts only see fetched evidence
    - off-topic evidence is gated out
    - with nothing decisive the system abstains, and the citation validator checks every cited id

    Arithmetic is done in code.
5. **"Is it reproducible?"** Yes. Every engine answer is recorded; replay mode reruns all 85 tests offline.
6. **"What doesn't it read?"** Charts, images and table rows (skipped on purpose). Claims outside the 20-metric catalogue end up INSUFFICIENT.
7. **"What does the risk score mean?"** A logistic model over engine outputs, fitted on 140 cases. It treats vague cheap talk as risky, which is why the honest company still scores 34 (Moderate).

## 4. Known weaknesses (not fixed tonight)

- **Claim precision not measured:** around 30 extra statements per report are extracted. Most become NOT_CHECKABLE or INSUFFICIENT, which is noise for an analyst.
- **Fixed metric catalogue:** 20 metrics, and a new metric needs a new column, a new builder and new prompt options.
- **No restatement check:** the DB has 6 years, but the system doesn't detect a company quietly restating earlier years.
- **Name-only entity resolution:** no CIN/LEI lookup from the report itself.
- **Regex time phrases:** "five years", "last decade" and "since our IPO" aren't understood.
- **Label noise:** a few generated labels are arguable (see `docs/BENCHMARK_NOTES.md`).
- **Limited context:** the Jev context is 32K tokens, so long evidence is trimmed to snippets.

## 5. Scaling it to real use

**Data (biggest lever)**

- Replace each mock endpoint with a real connector behind the SAME tool interface:
    - BRSR XBRL filings from NSE/BSE
    - the CPCB OCEMS portal
    - NGT judgments, CPCB/SPCB orders (scrape + parse)
    - the Global Forest Watch API
    - I-REC / REC Registry India
    - a news API such as GDELT or a licensed feed
- Resolve companies by CIN/LEI first, with names only as a fallback.
- Cache every source response with a timestamp, so a verdict can be reproduced later.

**Retrieval**

- Move news to OpenSearch / Elasticsearch with BM25 + dense vectors + a reranker.
- Put structured data in Postgres with time-series indexes.
- Add a document-level index of the report itself, so claims can be checked against the company's own tables (internal consistency).

**Extraction**

- Table and chart parsing (e.g. Docling / Camelot + a vision model for charts).
- An LLM-based decomposer and time-expression normaliser to replace the regex parser.
- Cross-page context: a claim plus its footnote or methodology note.

**Decision quality**

- Build a real labelled set: actual Indian reports + enforcement cases. Examples: ASCI guidelines on environmental claims, CCPA greenwashing guidelines. These are references to verify.
- Calibrate thresholds on a validation split, and report precision at fixed recall.
- Add a human review queue for every CONTRADICT, and learn from reviewer overrides.
- Use a second judge (LLM-as-judge) on disagreements, with escalation when they differ.
- Run drift monitoring per sector.

**Engineering**

- A job queue (Temporal / Celery / Arq) and a worker pool.
- Rate-limit-aware batching of Jev calls (450 calls per report today).
- A LangGraph Postgres checkpointer, so long runs resume after a crash.
- OpenTelemetry / LangSmith tracing.
- Auth + multi-tenant storage, and an immutable audit log.
- CI running the offline replay suite on every push.

**Product**

- Track the same company across years (restatements, missed targets).
- Peer benchmarks per sector.
- Alerts when a new filing contradicts an old claim.
- Export to the formats regulators and auditors use.
