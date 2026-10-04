# How a claim is classified and decided

Every judgement below is a question to the **Jev decision engine** (TypeSafe), which returns probabilities:

- **Noul:** P(yes)
- **Choice:** one option + a probability per option
- **Score:** a level on a scale

The exact question texts are in `app/agents/prompts.py`. Code never parses free text to decide anything. Python only fetches data, does arithmetic, and applies the thresholds listed here.

## Step by step

| # | Agent | Question to Jev (short) | How the answer is used |
|---|---|---|---|
| 0 | ingest | (no decision) | PDF to sentences with page + section. Back matter (GRI index, glossary, contents) and flattened table rows are skipped |
| 1 | resolver | Noul: "do the report company and this registry record refer to the same legal entity?" | Resolved only if P >= 0.5. Unresolved companies get no company-specific sources, so their claims end up INSUFFICIENT |
| 2 | extractor | Noul: "is this sentence a claim about THIS company's ESG performance, record, compliance, certification or commitment?" + Choice over 20 metrics | Kept as a claim if P >= 0.6 |
| 3 | triage | Choice: action = implemented / planning / indeterminate (A3CG). Noul: vague? Noul: checkable? Score: materiality | **NOT_CHECKABLE** if the action is planning (future target) or indeterminate, or P(vague) >= 0.6. Otherwise it goes to investigation |
| 4 | decomposer | Clause split, then per clause: Choice metric + Choice check type (pct_change, point_value, share, zero_events, compliance, geo, certificate, assurance) | Each clause becomes an atomic sub-claim with period and baseline |
| 5 | router | 8 Nouls: "would source X help check this?" (BRSR, facility GHG, OCEMS, regulatory, forest alerts, REC registry, assurance, news) | Sources with P >= 0.45 are queried |
| 6 | investigator | Tool calls (HTTP) + calculator, then Noul: "is the evidence sufficient?" | If P < 0.5, a second round widens to skipped sources and a wider news window |
| 7 | judge | Per evidence item: Noul relevance + Choice stance (support / contradict / insufficient) | Relevance < 0.5 means the item is excluded from the verdict ("off-topic") |
| 8 | verdict | Choice: **ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE**, with the option definitions shown below. Score: severity | Grounding guard: if no relevant evidence takes a side, the verdict is forced to INSUFFICIENT. A citation validator checks every cited id was really fetched |
| 9 | risk | (no decision) | Score = 100 x sigmoid(b + w . features), weights in `benchmark/risk_weights.json` |

## Verdict definitions given to Jev

- **ALIGN:** reliable external evidence confirms the claim. Rounding within about 3% still counts.
- **CONTRADICT:** reliable external evidence shows the claim is false, overstated or misleading. Regulatory filings and regulator records (tiers 1-2) outweigh company press releases (tier 4).
- **INSUFFICIENT_EVIDENCE:** no reliable external evidence addresses the claim (or it covers a different period).
- **NOT_CHECKABLE:** set by triage, for cheap talk or future targets.

## Source tiers

1. Regulatory filing (BRSR, facility GHG)
2. Regulator record (OCEMS, NGT/SPCB orders)
3. Third-party dataset (forest alerts, REC registry, assurance)
4. Company PR
5. News

## Real traced example (`proof/traced_claim_VAJ-01.json`)

Claim from page 4 of the Vajra Steel report: *"We have reduced our absolute Scope 1 emissions by 40% against our FY2020 baseline."*

1. **Resolver:** "Vajra Steel & Power Ltd", registry match `CMP-0001`, P(same) = 0.93.
2. **Triage:** implemented, checkable (P = 0.84).
3. **Decomposer:** 1 sub-claim, check type `pct_change`, metric `scope1_tco2e`, period FY2025, baseline FY2020.
4. **Router:** facility_ghg 0.94, brsr 0.90, assurance 0.86, news 0.84, ocems 0.55.
5. **Investigator:**
    - `GET /sebi/brsr?company_id=CMP-0001` returns Scope 1 FY2020 11,800,000 and FY2025 10,856,000 tCO2e.
    - Calculator: (10,856,000 - 11,800,000) / 11,800,000 = **-8.0%**.
    - The facility GHG registry sum confirms -8.0%.
6. **Judge:** BRSR and facility GHG both contradict (tier 1); a news item is insufficient.
7. **Verdict:** **CONTRADICT, confidence 1.00**, severity severe, risk score 90.

Open `proof/traced_claim_VAJ-06.json` for the geo example: "zero deforestation". The forest-alerts API is queried at the Keonjhar mine's coordinates (21.629, 85.581) and returns 14 alerts covering 126.4 ha in FY2025, so the verdict is CONTRADICT.
