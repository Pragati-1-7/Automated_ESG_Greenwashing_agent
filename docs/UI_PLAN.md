# UI Plan — ESG Claim Verification & Greenwashing Risk Analyzer

**Audience for this plan:** the dashboard will be reviewed by an EY senior
partner. That changes the bar: it must read as a serious analytical tool a
partner would trust in a client conversation, not a hackathon demo. This plan
covers who uses it, what each of them needs to see, what's already built,
and exactly what's left to make it "done and dusted."

---

## 1. Who actually uses this, and what they each need

| Persona | What they're trying to do | What breaks trust for them |
|---|---|---|
| **ESG analyst** (first-pass reviewer) | Upload a report, quickly see which claims deserve a closer look | Vague scores with no explanation; can't tell why something was flagged |
| **Compliance / legal reviewer** | Check that a flagged claim's evidence is real and correctly sourced | Any hint the system is "guessing" or that a source is unlabeled/fake |
| **Auditor / EY partner** (evaluator of the *system*, not just the report) | Decide if the *methodology* is sound enough to trust | Inconsistent verdicts, no audit trail, score presented as a probability, synthetic data not disclosed |
| **Technical demo operator** (whoever drives the laptop in the room) | Get through the demo without a crash, error, or dead screen | Backend down with no indication; upload silently doing nothing; long unexplained waits |

The UI plan below is organized around **the auditor/partner persona as the
hardest bar** — if it satisfies them, it satisfies everyone else.

---

## 2. Current UI inventory — what's already built

| Screen / element | Status | Notes |
|---|---|---|
| Landing page: title, subtitle, disclaimer banner | Done | Matches required copy exactly |
| PDF upload + "Use Demo ESG Report" toggle | Done | File name/size shown before analysis |
| Sidebar: backend URL, live health indicator, mode, top-k, semantic toggle | Done | Health check hits `/health` on every rerun |
| Executive summary (6 metrics + average risk score) | Done | Uses `st.metric`, plain columns |
| Claims table with row selection | Done | `st.dataframe`, plain text columns |
| Claim detail — Checkability tab | Done | Satisfied/missing fields, full rule list in expander |
| Claim detail — Evidence tab | Done | Source tier label, all 3 retrieval scores, synthetic-corpus caption |
| Claim detail — Verification tab | Done | Verdict in color, reason, supporting/contradicting IDs |
| Claim detail — Numerical Checks tab | Done | Claimed vs. evidence value, tolerance, PASS/MISMATCH/SKIPPED |
| Claim detail — Risk Score tab | Done | Score, band, factor breakdown, disclaimer |
| Claim detail — Audit Trail tab | Done (fixed this pass) | 10-step human-readable trace + raw JSON expander |
| Full Dataset Demo page | Done | Guarantees all 3 verdict types |
| Error states: no file, non-PDF, empty file, corrupted PDF, no claims | Done | All surfaced as `st.error`, no crashes (re-verified live, §5 of ARCHITECTURE.md) |

**Honest assessment: the UI is functionally complete.** Every required section
from the spec exists and renders real backend data. What's left is **polish and
trust-signaling for a partner-level audience**, not missing functionality.

---

## 3. Gap analysis — what "done and dusted" still needs

### 3a. Must-fix before an EY review (credibility, not cosmetics)

1. **KPI row looks like a generic Streamlit demo, not an analytical tool.**
   Plain `st.metric` in bare columns has no visual weight. → Use bordered
   metric cards in a horizontal container (`dashboards.md` pattern) so the
   executive summary reads as a dashboard, not a script output.
2. **Verdict is only color-coded inside the detail view, not in the table.**
   A partner scanning the claims table should see CONTRADICT rows stand out
   *without* clicking into each one. → Add a visual verdict indicator to the
   table (badge-style column).
3. **No indication of which mode/backend produced a given result once you've
   scrolled past the sidebar.** If a partner asks "wait, is this the demo PDF
   or something you uploaded?" three tabs deep, there's no on-screen answer. →
   Persist a small "Analyzing: `<filename>` via `<mode>`" strip above the
   results.
4. **Synthetic-data disclosure is present but easy to skim past.** For an
   audit-minded audience this is the single most important sentence in the
   app. → Make it visually distinct (not just `st.info`), e.g. a persistent
   band rather than a dismissible-looking info box.

### 3b. Worth doing, lower urgency

5. Material icons instead of plain text section labels (subtle, professional,
   not decorative) — e.g. a small icon next to "Evidence", "Verification".
6. A visible request/response timing indicator during analysis (spinner text
   is generic; a partner watching a live demo benefits from "Parsing PDF...
   Extracting claims... Retrieving evidence..." matching the actual pipeline
   stages, not just one static spinner message).
7. Empty-state polish: what the Evidence tab looks like for a NOT_CHECKABLE
   claim currently says "no evidence retrieval was run" — good — but the same
   treatment should be visually consistent across all 4 result tabs (currently
   each writes its own slightly different sentence).

### 3c. Explicitly out of scope for this pass

- Custom CSS/branding — not requested, and the spec explicitly says
  "functionality over decoration."
- Authentication/login screens — out of scope per the original Step 6 spec.
- Mobile-responsive redesign — this is a laptop-demo tool, not a public app
  (though the existing layout already doesn't break at narrow widths, since
  Streamlit's defaults handle that).

---

## 4. Plan of action

**Phase 1 (this pass, low-risk, additive-only):**
- Bordered KPI cards for the executive summary.
- Verdict badges in the claims table.
- A persistent "Analyzing: X via Y" context strip.
- A more visually distinct synthetic-data disclosure band.

**Phase 2 (only if you want it before the review):**
- Per-stage progress messaging during analysis.
- Consistent empty-state copy across all 4 detail tabs.
- Material icons on section headers.

**Not doing without an explicit ask:** anything touching Steps 1-5 logic, any
new external integration, any authentication, any custom theme/branding.

---

## 5. Pre-demo checklist (run this before the partner sees it)

1. `python -m pytest -q` → must show all tests passing.
2. `python scripts/validate_dataset.py` → must show `RESULT: PASS`.
3. Start FastAPI (`uvicorn app.api.main:app --reload`), confirm
   `http://127.0.0.1:8000/health` returns `200` in a browser tab.
4. Start Streamlit (`streamlit run streamlit_app/app.py`), confirm the sidebar
   shows "Backend status: **online**" — if it says unreachable, the backend
   isn't actually running and the demo will silently fail on "Analyze Report."
5. Run the Full Dataset Demo page once, live, before the meeting — confirms
   all three verdict types render correctly on this machine, not just in CI.
6. Have `data/sample_pdfs/edge_cases/` PDFs ready as a backup if the partner
   wants to see an error path handled gracefully (corrupted file, blank scan).
