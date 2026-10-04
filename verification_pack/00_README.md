# Verification pack: check everything by hand

| File / folder | What's inside | How to verify it yourself |
|---|---|---|
| `01_BEFORE_VS_AFTER.md` | v1 vs v2, area by area and file by file | Compare with `git diff` after running the push script |
| `02_HOW_CLAIMS_ARE_DECIDED.md` | every decision step, thresholds, verdict definitions, one traced claim | Open `proof/traced_claim_VAJ-01.json` and follow the events |
| `03_DATA_SOURCES_AND_APIS.md` | every table, every endpoint, the news search, the live Jev API | Open `proof/api_samples/INDEX.md`, then any JSON next to it |
| `04_REFERENCES.md` | sources behind the DB formats, live API docs, report-format references, our 4 reports, papers | Click the links. Items marked "knowledge" need a manual check |
| `05_HONEST_EVALUATION_AND_SCALING.md` | held-out + stress tests, weaknesses, likely jury questions, scaling plan | Numbers come from `benchmark/robustness_latest.json` |
| `reports/` | the 4 demo PDFs + `planted_claims_truth_vs_system.csv` | Open a PDF at the page in the CSV, read the claim, then look up the truth in `db_export/` |
| `db_export/` | every table of the mock world as CSV (9,745 rows) | Open in Excel. For example, filter `land_alerts.csv` by `nearest_facility_id = FAC-0003`, `distance_km <= 5` and dates 2024-04-01 to 2025-03-31: 14 rows, 126.4 ha |
| `benchmark/` | main + held-out benchmark cases, predictions, results, robustness results, fitted risk weights | `heldout_predictions.jsonl`: rows where `pred != label` are the errors |
| `proof/` | API dumps, traced claims, test and eval logs run with the old JSON files moved away | `v2_tests_with_old_json_moved.txt`, `v2_pdf_eval_with_old_json_moved.txt` |
| `screenshots/` | the UI on a live backend: analyze, live trace, results, drill-down, report, data sources, benchmark, verify-a-claim | |

## Five-minute manual check

1. Open `reports/vajra_steel_sr_fy2025.pdf`, page 10: "50% of the electricity ... came from renewable sources".
2. Open `db_export/brsr_filings.csv` and find `CMP-0001`, `FY2025`: `re_pct = 18.0`.
3. Open `db_export/re_certificates.csv` and find `CMP-0001`, vintage 2024: 2,100,000 MWh still `active`, only 310,000 `retired`.
4. Open `reports/planted_claims_truth_vs_system.csv` and find row VAJ-03: the system says CONTRADICT.
5. Do the same for Kaveri Threads (honest). Every claim is ALIGN and matches the CSV values.

## Running it (on your PC)

```powershell
pip install -r requirements.txt
# put TYPESAFE_API_KEY=... in .env   (or JEV_MODE=replay to run the demo reports offline)
.\scripts\run_backend.ps1      # http://127.0.0.1:8000/docs
.\scripts\run_frontend.ps1     # http://localhost:5173
python -m pytest -q            # 85 v2 tests, offline
python -m eval.run_robustness  # held-out + stress tests (needs the key)

```
