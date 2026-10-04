# Demo flow (v2), about 8 minutes

1. **Start.** Run `.\scripts\run_backend.ps1` and `.\scripts\run_frontend.ps1`, then open http://localhost:5173. The header shows the engine (Jev, live or replay), the LLM slot (mock) and the sources status.
2. **Data sources page.** Show that the evidence is real data behind APIs: 10 tables with tiers. Browse `brsr_filings` for CMP-0001 (Vajra Steel).
3. **Analyze: Vajra Steel (greenwasher).** Open the PDF first (27 pages, glossy). Then click Run analysis and stay on **Live trace**. Point out:
    - the resolver matching the company
    - the extractor screening about 140 sentences
    - triage labelling claims implemented / planning / indeterminate
    - the router choosing sources with probabilities
    - tool calls to `/sebi/brsr`, `/gfw/alerts/near`, `/registry/rec`
    - the judge and verdict decisions
4. **Results.** Risk 56 (High) with 12 contradictions. Open these claims:
    - **"50% renewable"**: the BRSR filing (Tier 1) says 18%. The company's own press release (Tier 4) "supports" it, but tier-1 evidence wins, and the REC registry shows 2.1 million MWh of certificates unretired.
    - **"zero deforestation at Keonjhar"**: 14 forest-loss alerts covering 126.4 ha within 5 km, found by coordinates.
    - **"no penalties in FY2024-25"**: an NGT Rs 4.2 crore order. Show the relevance tags too.
    - **"intensity fell 38%"**: ALIGN. The system is not just flagging everything, since this greenwasher's intensity claim is true.
5. **Kaveri Threads (honest).** 0 contradictions, risk 34, mostly ALIGN.
6. **Sahyadri Cement (mixed).** Open "No regulatory penalties in FY2024-25". It is ALIGN even though a CPCB closure direction exists, because that order is dated Feb 2023, outside the claim period (period reasoning).
7. **Aurelia Renewables (not in any source).** The company is not resolved, every claim is INSUFFICIENT_EVIDENCE and the risk is low. The system abstains instead of guessing.
8. **Verify a claim.** Type a claim live, for example "We cut our Scope 1 emissions by 40% since FY2020." for Vajra. The result is CONTRADICT, with the calculator showing -8.0%.
9. **Benchmark page.** 200 cases: accuracy, confusion matrix, per greenwashing type. The ablations are the key slide: news-only RAG gets 0.45 and the full agent 1.00. Be upfront about the caveats in the technical summary.
10. **Report tab.** The technical summary and audit trail for the analysis, ready to export.
