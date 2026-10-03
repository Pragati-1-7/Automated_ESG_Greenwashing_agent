# Demo Flow - Presenting to the Professor

This document describes exactly how to demonstrate the completed project.

## 0. Start the application

Terminal 1:
```bash
uvicorn app.api.main:app --reload
```

Terminal 2:
```bash
streamlit run streamlit_app/app.py
```

Open the URL Streamlit prints (typically `http://localhost:8501`).

## 1. Open the application

Show the landing page: title "ESG Claim Verification & Greenwashing Risk Analyzer", the
subtitle, and the disclaimer banner explaining this is a triage / decision-support tool, not a
legal determination.

## 2. Upload the synthetic ESG PDF

Check "Use Demo ESG Report" (or upload `data/sample_pdfs/synthetic_esg_report.pdf` manually).
This runs entirely offline using the deterministic Mock LLM provider - no API key needed.

## 3. Show extracted claims

Click "Analyze Report". Point out the Executive Summary metrics (total claims, checkable vs.
not checkable, verdict counts, average risk score).

## 4. Show checkability

In the Claim Analysis table, select a claim. Open the **Checkability** tab: show the
CHECKABLE/NOT_CHECKABLE decision, the completeness score, and the satisfied/missing field
list - explain this is a rule-based decision, not an LLM guess.

## 5. Select a claim

Pick a claim that is CHECKABLE (has evidence). Walk through its tabs in order.

## 6. Show retrieved evidence

Open the **Evidence** tab. Point out the "Development / synthetic evidence corpus" notice,
the generated search queries, and for each evidence item: its source, source tier, and the
BM25 / semantic / combined retrieval scores.

## 7. Show source tier

Explain the five-tier hierarchy shown next to each evidence item:
`Tier 1 - Regulatory filing`, `Tier 2 - Regulator/tribunal`, `Tier 3 - Audited report`,
`Tier 4 - Company PR`, `Tier 5 - News`. Higher tiers are weighted more heavily during
verification.

## 8. Show verification

Open the **Verification** tab: the ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE verdict, its
supporting/contradicting evidence IDs, and the plain-English reason.

## 9. Show numerical check

Open the **Numerical Checks** tab for a claim with a percentage or quantity claim: claimed
value vs. evidence value vs. tolerance, and the PASS/MISMATCH/SKIPPED result - emphasize this
arithmetic is done in Python, never by an LLM.

## 10. Show risk score

Open the **Risk Score** tab: the 0–100 score, its band, and the factor-by-factor breakdown
(each with points and a reason). Read the disclaimer aloud: this is a triage indicator, not a
probability, not a legal verdict.

## 11. Open the audit trail

Open the **Audit Trail** tab: the full underlying JSON for that claim, so the professor can see
that nothing shown earlier was invented by the frontend - it is exactly what the backend
returned.

## 12. Explain why the result was generated

Summarize the chain for the selected claim: PDF -> extracted text -> checkability rules ->
search queries -> retrieved evidence -> verification comparison -> numerical check ->
risk factors -> final score.

## Guaranteed ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE examples

The bundled sample PDF's claims may not all have matching synthetic evidence (it is a
freestanding fictional company). To reliably show all three verdict types in one place, switch
to the **"Full Dataset Demo"** page in the sidebar and click **"Run Dataset Demo"**. This runs
the curated `data/claims/claims.json` dataset (12 claims) against its purpose-built
`data/evidence/evidence.json` corpus (20 records across all five tiers), which was authored to
guarantee:

- At least one **ALIGN** example (evidence supports the claim as stated).
- At least one **CONTRADICT** example (a higher-authority source conflicts with the claim,
  e.g. a claimed 40% reduction vs. an audited 25% reduction).
- At least one **INSUFFICIENT_EVIDENCE** example (no reliable evidence either way).

Use the Claim Analysis table's "Verification" column to point out one row of each type, then
open each one's Verification tab to show the reasoning.
