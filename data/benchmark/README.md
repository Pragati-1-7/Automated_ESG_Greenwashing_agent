# ESG claim-verification benchmark (200 cases)

Fictional, deterministic (seed 20261004) benchmark generated from `data/world/world.db` by `python3 -m data_gen.build_benchmark`. Every number in a claim was computed from the DB; demo companies CMP-0001..0003 are excluded (reserved for the demo PDFs).

## Files

| file | content |
|---|---|
| `cases.jsonl` | the 200 cases (schema below) |
| `verification.jsonl` | machine-checkable facts per case, used by `tests/test_benchmark.py` to recompute ALIGN/CONTRADICT value claims from the DB |
| `stats.json` | composition counts |

Case fields: `case_id, company_id, company_name, claim_text, metric, fy, baseline_fy, label, gw_type, difficulty, truth_note, evidence_refs, split`.
`evidence_refs` are `table:row_id` strings. Labels: ALIGN (value within ~3% relative, or exact for counts/zero-claims/categories), CONTRADICT (>= 15% relative error, or wrong count/category), INSUFFICIENT_EVIDENCE (no DB source, or company not in DB), NOT_CHECKABLE (vague or future target).

## Label x split

| label | n | train | test |
|---|---|---|---|
| ALIGN | 60 | 42 | 18 |
| CONTRADICT | 70 | 49 | 21 |
| INSUFFICIENT_EVIDENCE | 40 | 28 | 12 |
| NOT_CHECKABLE | 30 | 21 | 9 |
| **total** | 200 | 140 | 60 |

## Label x greenwashing type

| gw_type | ALIGN | CONTRADICT | INSUFFICIENT_EVIDENCE | NOT_CHECKABLE | total |
|---|---|---|---|---|---|
| none | 60 | 0 | 0 | 12 | 72 |
| vague_claim | 0 | 0 | 0 | 18 | 18 |
| inflated_reduction | 0 | 8 | 0 | 0 | 8 |
| cherry_picked_year | 0 | 5 | 0 | 0 | 5 |
| baseline_shift | 0 | 5 | 0 | 0 | 5 |
| scope_swap | 0 | 5 | 0 | 0 | 5 |
| absolute_vs_intensity | 0 | 5 | 0 | 0 | 5 |
| unit_error | 0 | 5 | 0 | 0 | 5 |
| future_target_as_achievement | 0 | 5 | 0 | 0 | 5 |
| unretired_certificates | 0 | 6 | 0 | 0 | 6 |
| geo_contradiction | 0 | 6 | 0 | 0 | 6 |
| hidden_regulatory_penalty | 0 | 10 | 0 | 0 | 10 |
| overstated_safety | 0 | 5 | 0 | 0 | 5 |
| overstated_assurance | 0 | 5 | 0 | 0 | 5 |
| data_not_disclosed | 0 | 0 | 40 | 0 | 40 |

## Label x difficulty

| label | easy | medium | hard |
|---|---|---|---|
| ALIGN | 22 | 23 | 15 |
| CONTRADICT | 12 | 11 | 47 |
| INSUFFICIENT_EVIDENCE | 10 | 27 | 3 |
| NOT_CHECKABLE | 18 | 12 | 0 |

## Metric coverage

| metric | cases |
|---|---|
| null | 33 |
| scope1_tco2e | 27 |
| ocems_exceedances | 13 |
| re_pct | 13 |
| regulatory_actions | 12 |
| ghg_intensity | 11 |
| deforestation_ha | 11 |
| water_withdrawal_kl | 10 |
| assurance_type | 10 |
| scope2_tco2e | 10 |
| rec_retirement | 9 |
| ltifr | 9 |
| fatalities | 7 |
| scope3_tco2e | 7 |
| energy_gj | 6 |
| clinker_factor | 5 |
| women_wage_pct | 2 |
| msme_sourcing_pct | 2 |
| waste_recovered_t | 2 |
| waste_generated_t | 1 |

## Design notes

- 200 distinct claim templates; FY written as `FY2025`, `FY2024-25`, `FY 2024-25` or `the financial year 2024-25`; emissions in raw, Indian-grouped, lakh, crore or million tCO2e; `%` and `per cent`.
- Difficulty: easy = direct value; medium = percentage change or two-year comparison; hard = traps (period trap, scope swap, absolute vs intensity, unit error, certificates, geo, baseline restatement).
- ALIGN cases always carry `gw_type = none` (including the honest reverse cases: true intensity claims while absolute emissions rose, period traps, true zero-exceedance / no-forest-loss / no-penalty claims). INSUFFICIENT_EVIDENCE uses `data_not_disclosed`; NOT_CHECKABLE uses `vague_claim` (cheap talk) or `none` (future targets).
- In this world Scope 1 grows for almost every company while intensity falls, so honest reduction claims are about intensity, Scope 2 or LTIFR, and absolute Scope 1 reduction claims are contradictions.
- Forest-loss claims use alerts within 5 km (haversine from facility coordinates) dated inside the fiscal year; a contradiction is only used when haversine and the DB's nearest-facility distance agree.
- Penalty claims count `regulatory_actions` by action date inside the FY; 'no penalty' claims against planted events use rows with `penalty_inr > 0`.
- Splits are stratified by label (30% test, rounded): 140 train, 60 test.
