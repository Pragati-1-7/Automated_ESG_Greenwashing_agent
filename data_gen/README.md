# data_gen: synthetic "mock world" database

Everything here is fictional. `spec.py` is the single source of truth (metrics, fiscal years, the three in-DB demo
companies, their planted events and news seeds); `schema.sql` is the SQLite contract.

    python3 -m data_gen.build_world          # (re)creates data/world/world.db + data/world/planted_events.json
    python3 -m data_gen.build_world --out X  # build somewhere else
    python3 -m data_gen.validate_world       # invariant checks, non-zero exit on failure
    python3 -m pytest tests/test_world_db.py -q

The build is deterministic (`random.Random` streams derived from `spec.SEED`, one stream per table), offline and LLM-free.

## Files

| file | role |
|---|---|
| `build_world.py` | one `gen_<table>` function per table (returns list of dicts), `make_plan`, `build_planted_events`, `write_db`, `build(out_path)` |
| `world_refs.py` | states / SPCB names / NGT zones, district centroids, sector profiles, facility templates, name banks |
| `world_utils.py` | haversine, FY helpers, Indian money formatting |
| `news_gen.py`, `news_base.py`, `news_tpl.py` | news generator: data context, filler, and 34 article templates |
| `validate_world.py` | invariants (also used by the tests) |

## Tables and row counts (current build)

| table | rows | notes |
|---|---|---|
| companies | 150 | CMP-0001..0003 = spec demo companies; 147 generated (15 per sector), fictional names, CIN pattern, NSE/BSE listing |
| facilities | 422 | FAC-0001..0011 = spec; generated from sector facility templates at jittered real district centroids; ~11% of mining/steel/power facilities `forest_adjacent` |
| brsr_filings | 900 | 6 FYs x 150; demo from spec `true` arrays; generated = sector-scaled smooth trends with noise; assurance only ever progresses none -> limited -> reasonable |
| facility_ghg | 2532 | every facility x 6 FY; facility totals sum to BRSR scope 1 (exactly, to rounding) |
| ocems_exceedances | 2000 | realistic limits (PM 30-50, SO2 100-600, NOx 300-450 mg/Nm3; BOD 30, COD 250, TSS 100 mg/L); readings > limit; heavy-tailed across non-demo heavy facilities |
| regulatory_actions | 400 | NGT, CPCB, 18 state boards, MoEFCC, SEBI; Rs 5 lakh - 25 crore |
| land_alerts | 1500 | clusters near forest-adjacent facilities plus background noise in forested states; `distance_km`/`nearest_facility_id` computed by haversine (NULL beyond 25 km) |
| re_certificates | ~930 | per company/vintage 2020-2024, retired / active / transferred |
| audited_reports | 409 | one per (company, FY) with assurance != none; assurance type and auditor equal the BRSR filing; 120-300 word ISAE 3000 / SSAE style text |
| news_articles | 500 | ~60% tied to a company; 39 tier-4 company press releases and tier-5 news from 17 fictional outlets, 250-600 words |

## How planted scenarios work

**Demo companies (CMP-0001..0003)** get exactly the spec events: Vajra has the two regulatory actions, 37 FY2025 PM/SO2
exceedances at Angul, 14 alerts / 126.4 ha within 5 km of the Keonjhar mine in the spec window, and 310,000 MWh retired /
2,100,000 MWh active 2024-vintage certificates. Sahyadri has one 2023 CPCB direction, 6 FY2025 PM exceedances at Chandrapur
and no alerts within 10 km. Kaveri has nothing adverse. Generic noise (alerts, regulatory actions, exceedances) is rejected
or restricted so it can never land on these companies' ground truth, and no alert lands within 15 km of the Kutch point used
by the (absent) Aurelia scenario. The spec news items are expanded verbatim (outlet, date, headline, tier); 2-5 neutral
extras per demo company are built from templates that only quote true filed values.

**Non-demo planted discrepancies (`data/world/planted_events.json`, 60 companies).** `make_plan` picks distinct generated
companies and the generators create the rows; the file's `true_value` is then recomputed from the final tables:
`regulatory_penalty` (penalty rows in a FY), `ocems` (>= 9 exceedances at one facility in a FY), `land_alerts` (clustered
alerts within 5 km of a forest-adjacent facility in a FY), `rec_unretired` (2024-vintage active volume several times the
retired volume). Each entry lists `company_id, metric, fy, kind, true_value, unit, table, refs` (row ids) and `details`.

**News** articles are generated from real rows: an article about a penalty quotes the amount, date, authority and case
number of an actual `regulatory_actions` row; OCEMS articles count real exceedances; forest articles sum real alerts; filing
based articles quote the BRSR values. Padding paragraphs only use facts known as of the article date.
