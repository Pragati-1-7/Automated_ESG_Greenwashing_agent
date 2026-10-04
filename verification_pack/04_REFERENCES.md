# Reference list

Status column: **opened** = I read the page while designing. **search** = seen in search results only, used for the format/name. **knowledge** = from general domain knowledge, not opened in this project. Verify the "knowledge" items yourself before quoting them to a jury.

## A. Formats the mock databases copy

| DB table | Real-world source it imitates | Link | Status |
|---|---|---|---|
| brsr_filings | SEBI BRSR Core, 9 attributes and KPIs | https://greensutra.in/question/brsr-core-nine-kpis-explained/ | opened |
| brsr_filings | SEBI circular on BRSR Core (12 Jul 2023) | https://ca2013.com/wp-content/uploads/2023/07/SEBI-Circular_12.07.2023.pdf | search |
| brsr_filings | India Briefing: BRSR Core and ESG rating rules | https://www.india-briefing.com/news/india-brsr-core-esg-rating-provider-regulation-29062.html | search |
| ocems_exceedances | CPCB / SPCB OCEMS guidelines (parameters, limits) | https://thesustainabilitycloud.com/cpcb-and-spcb-guidelines-rules | search |
| ocems_exceedances | CPCB notice on OCEMS remote calibration | https://www.cpcb.nic.in/upload/thrust-area/Notice_for_remote_calibration_25.06.2018.pdf | search |
| facility_ghg | US EPA GHGRP reported-data tables by subpart | https://19january2021snapshot.epa.gov/sites/static/files/2015-07/documents/ghgrp-table-reported-data-direct-emitters-subparts.pdf | search |
| land_alerts | Global Forest Watch integrated deforestation alerts dataset | https://data-api.globalforestwatch.org/dataset/gfw_integrated_alerts | search |
| land_alerts | GFW blog: drivers of deforestation alerts | https://www.globalforestwatch.org/blog/data-and-tools/drivers-deforestation-alerts/ | search |
| regulatory_actions | NGT orders, CPCB Section 5 directions, SPCB show-cause notices (format) | https://greentribunal.gov.in | knowledge |
| re_certificates | I-REC Standard / REC Registry India (retired vs active certificates) | https://www.trackingstandard.org , https://www.recregistryindia.nic.in | knowledge |
| audited_reports | ISAE 3000 limited vs reasonable assurance | https://www.iaasb.org | knowledge |

## B. Live APIs and frameworks

| What | Link | Status |
|---|---|---|
| TypeSafe Jev quick start (endpoint, auth, request/response) | https://docs.typesafe.ai/introduction/quickstart | opened |
| TypeSafe Python SDK usage (Noul / Choice / Score) | https://docs.typesafe.ai/sdk/python/usage | opened |
| Jev on OpenRouter (model ids, output types) | https://openrouter.ai/docs/guides/community/jev | opened |
| Groq models list | https://console.groq.com/docs/models | opened |
| Groq structured outputs | https://console.groq.com/docs/structured-outputs | opened |
| Groq free-tier limits (third-party summary) | https://tokenmix.ai/blog/groq-api-access-2026-free-tier-rate-limits | opened |
| LangGraph workflows and agents (Send, orchestrator-worker) | https://docs.langchain.com/oss/python/langgraph/workflows-agents | opened |
| MCP vs A2A guidance | https://ecorpit.com/mcp-vs-a2a-enterprise-agent-protocol-decision-2026/ | opened |

## C. Real company reports used as format references

We did NOT copy any real company's report. Our 4 PDFs follow the public structure of an Indian BRSR / sustainability report:

- chairman's letter
- company at a glance
- materiality
- environment, social and governance chapters
- BRSR Core table
- GRI content index
- assurance statement

| Reference | Link | Status |
|---|---|---|
| Endurance Technologies, BRSR FY2024-25 (example of a real filed BRSR) | https://www.endurancegroup.com/wp-content/uploads/2025/07/Business-Responsibility-and-Sustainability-Report-for-FY-2024-25.pdf | search |
| SEBI BRSR format (Annexure to the 2021 / 2023 circulars) | https://www.sebi.gov.in | knowledge |
| GRI Standards 2021 content index layout | https://www.globalreporting.org/standards/ | knowledge |

## D. Our generated reports (all fictional, in `reports/`)

| File | Company | Pages | Profile | Planted claims |
|---|---|---|---|---|
| vajra_steel_sr_fy2025.pdf | Vajra Steel & Power Ltd (CMP-0001) | 27 | greenwasher | 16 |
| sahyadri_cement_iar_fy2025.pdf | Sahyadri Cement Industries Ltd (CMP-0002) | 28 | mixed | 12 |
| kaveri_threads_brsr_fy2025.pdf | Kaveri Threads & Textiles Ltd (CMP-0003) | 28 | honest | 12 |
| aurelia_renewables_sr_2025.pdf | Aurelia Renewables Pvt Ltd (not in any DB) | 23 | unknown company | 6 |

Every planted claim, its page, the expected verdict, the system's verdict and the ground-truth numbers are in `reports/planted_claims_truth_vs_system.csv`. Rebuild with `python -m report_gen.build_reports`.

## E. Research papers behind the agent design

| Paper | Link | Status |
|---|---|---|
| EmeraldMind: KG-augmented greenwashing detection (2025) | https://arxiv.org/html/2512.11506v1 | opened |
| A3CG: aspect-action greenwashing dataset (Ong et al., 2025) | https://arxiv.org/pdf/2502.15821 | opened |
| COGLM: robust greenwashing detection (2026) | https://arxiv.org/html/2601.21722 | opened |
| DeepGreen: LLM greenwashing monitoring (2025) | https://arxiv.org/html/2504.07733v2 | opened |
| Fact in Fragments / AFEV (2025) | https://arxiv.org/abs/2506.07446 | opened |
| DEFAME, ICML 2025 | https://arxiv.org/html/2412.10510v4 | opened |
| Climate Finance Bench (2025) | https://arxiv.org/abs/2505.22752 | opened |
| VERDI: confidence for LLM judges (2026) | https://arxiv.org/pdf/2605.11334 | opened |
| Environmental Claim Detection, ACL 2023 | https://aclanthology.org/2023.acl-short.91 | search |
| ProgramFC, ACL 2023 | https://aclanthology.org/2023.acl-long.386 | search |
| SAFE / LongFact, NeurIPS 2024 | https://arxiv.org/abs/2403.18802v2 | search |
| FIRE, NAACL Findings 2025 | https://preview.aclanthology.org/dashboard/2025.findings-naacl.158 | search |
| MiniCheck, EMNLP 2024 | https://aclanthology.org/2024.emnlp-main.499 | search |
| Cheap Talk and Cherry-Picking (ClimateBERT) | https://cris.fau.de/publications/270188240 | search |
