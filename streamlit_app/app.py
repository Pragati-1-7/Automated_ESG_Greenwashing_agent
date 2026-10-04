"""
streamlit_app/app.py

STEP 6: Streamlit dashboard for the ESG Claim Verification & Greenwashing
Risk Analyzer.

This file contains NO backend logic. It only calls the FastAPI backend
(app/api/main.py) over HTTP and displays the results it returns. All
verdicts, risk scores, and explanations shown here are exactly what the
Step 1-5 backend produced -- nothing is computed in this file.

Run:
    uvicorn app.api.main:app --reload
    streamlit run streamlit_app/app.py
"""

from __future__ import annotations

import requests
import streamlit as st

st.set_page_config(
    page_title="ESG Claim Verification & Greenwashing Risk Analyzer",
    layout="wide",
)

DEFAULT_BACKEND = "http://127.0.0.1:8000"

SOURCE_TIER_LABELS = {
    1: "Tier 1 - Regulatory filing",
    2: "Tier 2 - Regulator / tribunal",
    3: "Tier 3 - Audited report",
    4: "Tier 4 - Company PR",
    5: "Tier 5 - News",
}

VERDICT_COLORS = {
    "ALIGN": "#1a7f37",
    "CONTRADICT": "#b42318",
    "INSUFFICIENT_EVIDENCE": "#946800",
    "NOT_APPLICABLE": "#6b7280",
}

# Order matters: must match VERDICT_BADGE_OPTIONS <-> VERDICT_BADGE_COLORS index-for-index.
VERDICT_BADGE_OPTIONS = ["ALIGN", "CONTRADICT", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE", "-"]
VERDICT_BADGE_COLORS = ["green", "red", "orange", "gray", "gray"]


# ---------------------------------------------------------------------------
# Backend calls
# ---------------------------------------------------------------------------


def backend_url() -> str:
    return st.session_state.get("backend_url", DEFAULT_BACKEND).rstrip("/")


def call_analyze(
    file_bytes: bytes | None,
    filename: str | None,
    use_demo: bool,
    company: str,
    mode: str,
    top_k: int,
    use_semantic: bool,
) -> dict:
    data = {
        "use_demo": str(use_demo).lower(),
        "company": company or "",
        "mode": mode,
        "top_k": str(top_k),
        "use_semantic": str(use_semantic).lower(),
    }
    files = {"file": (filename, file_bytes, "application/pdf")} if file_bytes else None
    resp = requests.post(f"{backend_url()}/analyze", data=data, files=files, timeout=120)
    if resp.status_code >= 400:
        raise RuntimeError(resp.json().get("detail", resp.text))
    return resp.json()


def call_demo_dataset(top_k: int, use_semantic: bool) -> dict:
    resp = requests.get(
        f"{backend_url()}/demo/dataset",
        params={"top_k": top_k, "use_semantic": use_semantic},
        timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(resp.json().get("detail", resp.text))
    return resp.json()


def check_health() -> bool:
    try:
        r = requests.get(f"{backend_url()}/health", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def render_disclaimer_banner(result: dict) -> None:
    st.warning(
        f"**Synthetic evidence corpus:** {result.get('synthetic_evidence_notice', '')}\n\n"
        f"{result.get('disclaimer', '')}",
        icon=":material/policy:",
    )


def render_analysis_context(result: dict, mode: str) -> None:
    """Persistent strip so it's always clear, no matter how deep into the
    tabs someone is, exactly what was analyzed and how."""
    with st.container(border=True, horizontal=True):
        st.markdown(f"**Analyzing:** {result.get('source_document', 'unknown')}")
        st.markdown(f"**Company:** {result.get('company', 'unknown')}")
        st.markdown(f"**Extraction mode:** {mode}")


def render_executive_summary(summary: dict) -> None:
    st.subheader("Executive summary")
    with st.container(horizontal=True):
        st.metric("Total claims", summary["total_claims"], border=True)
        st.metric("Checkable", summary["checkable_claims"], border=True)
        st.metric("Not checkable", summary["not_checkable_claims"], border=True)
        st.metric("Aligned", summary["align_count"], border=True)
        st.metric("Contradicted", summary["contradict_count"], border=True)
        st.metric("Insufficient evidence", summary["insufficient_evidence_count"], border=True)

    if summary["average_risk_score"] is not None:
        st.metric(
            "Average greenwashing risk score (checkable claims)",
            f"{summary['average_risk_score']:.1f} / 100",
            border=True,
        )
        st.caption(
            "The risk score is a rule-based triage indicator used to prioritize claims "
            "for human review. It is not a probability of greenwashing."
        )


def render_claims_table(records: list[dict]) -> None:
    st.subheader("Claim Analysis")
    if not records:
        st.warning("No claims to display.")
        return

    rows = []
    for r in records:
        cr = r.get("checkability_result") or {}
        vr = r.get("verification_result") or {}
        rs = r.get("risk_score_result") or {}
        rows.append(
            {
                "Claim ID": r["claim_id"],
                "Claim": (
                    (r["claim_text"][:90] + "...") if len(r["claim_text"]) > 90 else r["claim_text"]
                ),
                "Checkability": cr.get("checkability", "-"),
                "Verification": [vr.get("verdict", "-")],
                "Risk Score": rs.get("risk_score", None),
                "Risk Band": rs.get("risk_band", "-"),
            }
        )
    st.dataframe(
        rows,
        hide_index=True,
        column_config={
            "Verification": st.column_config.MultiselectColumn(
                "Verification",
                options=VERDICT_BADGE_OPTIONS,
                color=VERDICT_BADGE_COLORS,
            ),
        },
    )

    claim_ids = [r["claim_id"] for r in records]
    selected = st.selectbox("Select a claim to inspect in detail", claim_ids)
    selected_record = next(r for r in records if r["claim_id"] == selected)
    render_claim_detail(selected_record)


def _audit_step(number: int, title: str, icon: str) -> None:
    st.markdown(f"**{number}. :material/{icon}: {title}**")


def render_audit_trail(record: dict) -> None:
    """Human-readable, step-by-step reconstruction of how this result was
    reached (Section 9 of the spec) -- every number/label shown here comes
    straight from the backend's AuditRecord, nothing is computed here."""
    cr = record.get("checkability_result")
    rr = record.get("retrieval_result")
    vr = record.get("verification_result")
    rs = record.get("risk_score_result")

    st.caption(
        "Full step-by-step trace of how this result was produced. Nothing below is invented by the dashboard - it is the exact backend output for this claim."
    )

    with st.container(border=True):
        _audit_step(1, "Source document", "description")
        st.write(f"Company: {record['company']}")

    with st.container(border=True):
        _audit_step(2, "Extracted claim", "format_quote")
        st.write(record["claim_text"])

    with st.container(border=True):
        _audit_step(3, "Checkability decision", "checklist")
        if cr:
            st.write(f"**{cr['checkability']}** - {cr['reason']}")
        else:
            st.write("Not evaluated.")

    with st.container(border=True):
        _audit_step(4, "Search queries generated", "search")
        if rr and rr.get("query_plan", {}).get("queries"):
            for q in rr["query_plan"]["queries"]:
                st.write(f"- {q}")
        else:
            st.write("No queries generated (claim not checkable).")

    with st.container(border=True):
        _audit_step(5, "Evidence retrieved", "fact_check")
        if rr and rr.get("evidence"):
            st.write(f"{len(rr['evidence'])} item(s) retrieved from the synthetic evidence corpus.")
        else:
            st.write("No evidence retrieved.")

    with st.container(border=True):
        _audit_step(6, "Evidence ranking", "sort")
        if rr and rr.get("evidence"):
            rows = [
                {
                    "Rank": ev["rank"],
                    "Evidence ID": ev["evidence_id"],
                    "BM25": round(ev["bm25_score"], 3),
                    "Semantic": round(ev["semantic_score"], 3),
                    "Combined": round(ev["combined_score"], 3),
                }
                for ev in rr["evidence"]
            ]
            st.dataframe(rows, hide_index=True)
        else:
            st.write("No ranking to show.")

    with st.container(border=True):
        _audit_step(7, "Numerical checks", "calculate")
        if vr and vr.get("numerical_checks"):
            for nc in vr["numerical_checks"]:
                status = "PASS" if nc["passed"] else ("SKIPPED" if nc["skipped"] else "MISMATCH")
                st.write(f"[{status}] {nc['check_type']}: {nc['detail']}")
        else:
            st.write("No numerical checks were applicable.")

    with st.container(border=True):
        _audit_step(8, "Verification", "gavel")
        if vr:
            st.write(f"**{vr['verdict']}** - {vr['reason']}")
        else:
            st.write("Not applicable.")

    with st.container(border=True):
        _audit_step(9, "Risk factors", "warning")
        if rs and rs.get("factors"):
            for f in sorted(rs["factors"], key=lambda x: x["points"], reverse=True):
                st.write(f"+{f['points']:.0f} pts - {f['factor']}: {f['reason']}")
        else:
            st.write("No risk factors (claim not checkable).")

    with st.container(border=True):
        _audit_step(10, "Final score", "speed")
        if rs:
            st.write(f"**{rs['risk_score']:.0f} / 100 - {rs['risk_band']} risk**")
        else:
            st.write("No score computed.")

    with st.expander("Raw audit record (JSON)"):
        st.json(record)


def render_claim_detail(record: dict) -> None:
    st.subheader(f"Claim Detail - {record['claim_id']}")

    st.markdown("**Original Claim Text**")
    st.write(record["claim_text"])
    st.caption(f"Company: {record['company']}")

    cr = record.get("checkability_result")
    rr = record.get("retrieval_result")
    vr = record.get("verification_result")
    rs = record.get("risk_score_result")

    tabs = st.tabs(
        [
            "Checkability",
            "Evidence",
            "Verification",
            "Numerical Checks",
            "Risk Score",
            "Audit Trail",
            "Full Report",
        ]
    )

    with tabs[0]:
        if cr:
            st.write(f"**Claim type:** {cr['claim_type']}")
            st.write(f"**Checkability:** {cr['checkability']}")
            st.write(f"**Completeness score:** {cr['checkability_completeness']:.0f}/100")
            st.write(f"**Reason:** {cr['reason']}")
            if cr["satisfied_fields"]:
                st.markdown("**Satisfied:** " + ", ".join(f"✓ {f}" for f in cr["satisfied_fields"]))
            if cr["missing_fields"]:
                st.markdown("**Missing:** " + ", ".join(cr["missing_fields"]))
            with st.expander("All rule results"):
                for rule in cr["rule_results"]:
                    status = (
                        "PASS" if rule["passed"] else ("N/A" if not rule["applicable"] else "FAIL")
                    )
                    st.write(f"[{status}] **{rule['rule_name']}** - {rule['detail']}")
        else:
            st.write("No checkability result available.")

    with tabs[1]:
        if rr and rr.get("evidence"):
            st.caption("Development / synthetic evidence corpus - not real regulatory records.")
            with st.expander("Search queries generated"):
                for q in rr["query_plan"]["queries"]:
                    st.write(f"- {q}")
            for ev in rr["evidence"]:
                tier_label = SOURCE_TIER_LABELS.get(ev["source_tier"], f"Tier {ev['source_tier']}")
                st.markdown(f"**[{ev['rank']}] {ev['source']}** - {tier_label}")
                st.write(ev["retrieved_text"])
                st.caption(
                    f"Publication date: {ev.get('publication_date', 'N/A')} | "
                    f"BM25: {ev['bm25_score']:.3f} | Semantic: {ev['semantic_score']:.3f} | "
                    f"Combined: {ev['combined_score']:.3f}"
                )
                st.divider()
        elif rr:
            st.write("No evidence retrieved for this claim.")
        else:
            st.write("This claim was not checkable, so no evidence retrieval was run.")

    with tabs[2]:
        if vr:
            color = VERDICT_COLORS.get(vr["verdict"], "#374151")
            st.markdown(
                f"### <span style='color:{color}'>{vr['verdict']}</span>", unsafe_allow_html=True
            )
            st.write(f"**Why:** {vr['reason']}")
            st.write(f"Supporting evidence: {', '.join(vr['supporting_evidence_ids']) or 'none'}")
            st.write(
                f"Contradicting evidence: {', '.join(vr['contradicting_evidence_ids']) or 'none'}"
            )
            st.write(
                f"Insufficient/inconclusive evidence: {', '.join(vr['insufficient_evidence_ids']) or 'none'}"
            )
            if vr.get("highest_authority_tier"):
                st.write(f"Highest-authority source tier used: {vr['highest_authority_tier']}")
        else:
            st.write("No verification result (claim not checkable).")

    with tabs[3]:
        if vr and vr.get("numerical_checks"):
            for nc in vr["numerical_checks"]:
                status = "PASS" if nc["passed"] else ("SKIPPED" if nc["skipped"] else "MISMATCH")
                st.markdown(f"**[{status}] {nc['check_type']}**")
                cols = st.columns(3)
                cols[0].write(f"Claimed value: {nc.get('claim_value')}")
                cols[1].write(f"Evidence value: {nc.get('evidence_value')}")
                cols[2].write(f"Tolerance: {nc['tolerance_pct']}%")
                st.write(nc["detail"])
                st.divider()
        else:
            st.write("No deterministic numerical checks were applicable to this claim.")

    with tabs[4]:
        if rs:
            st.markdown(f"### {rs['risk_score']:.0f} / 100 - {rs['risk_band']} Risk")
            st.write(rs["summary"])
            for f in sorted(rs["factors"], key=lambda x: x["points"], reverse=True):
                st.write(f"+{f['points']:.0f} pts - **{f['factor']}**: {f['reason']}")
            st.caption(rs["disclaimer"])
        else:
            st.write("No risk score computed (claim not checkable).")

    with tabs[5]:
        render_audit_trail(record)

    with tabs[6]:
        st.markdown("**Original claim**")
        st.write(record["claim_text"])
        st.caption(f"Company: {record['company']}")

        st.markdown("**Checkability**")
        if cr:
            st.write(f"{cr['checkability']} - {cr['reason']}")
        else:
            st.write("No checkability result available.")

        st.markdown("**Verdict and reasoning**")
        if vr:
            color = VERDICT_COLORS.get(vr["verdict"], "#374151")
            st.markdown(
                f"<span style='color:{color}'>**{vr['verdict']}**</span> - {vr['reason']}",
                unsafe_allow_html=True,
            )
        else:
            st.write("No verification result available for this claim.")

        st.markdown("**Risk score**")
        if rs:
            st.write(f"{rs['risk_score']:.0f} / 100 - {rs['risk_band']} risk")
            top_factors = sorted(rs["factors"], key=lambda x: x["points"], reverse=True)[:3]
            for f in top_factors:
                st.write(f"+{f['points']:.0f} pts - {f['factor']}: {f['reason']}")
        else:
            st.write("No risk score computed for this claim.")

        st.markdown("**External evidence used**")
        if rr and rr.get("evidence"):
            for ev in rr["evidence"]:
                tier_label = SOURCE_TIER_LABELS.get(ev["source_tier"], f"Tier {ev['source_tier']}")
                st.write(f"{ev['source']} ({tier_label})")
                st.caption(ev["retrieved_text"])
        else:
            st.write("No external evidence was used for this claim.")

        st.caption(
            rs["disclaimer"]
            if rs
            else "This is a triage indicator for human review, not a legal determination of greenwashing."
        )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def page_upload_and_analyze() -> None:
    st.title("ESG Claim Verification & Greenwashing Risk Analyzer")
    st.caption("Evidence-based ESG claim analysis for human review")
    st.warning(
        "This tool provides evidence-based triage and decision support. "
        "It does not constitute a legal determination of greenwashing."
    )

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload ESG PDF", type=["pdf"])
    with col2:
        use_demo = st.checkbox("Use Demo ESG Report (bundled synthetic sample, works offline)")

    company = st.text_input("Company name (optional)")

    if uploaded is not None:
        st.write(f"**File:** {uploaded.name}")
        st.write(f"**Size:** {len(uploaded.getvalue()) / 1024:.1f} KB")

    if st.button("Analyze Report", type="primary", disabled=(uploaded is None and not use_demo)):
        with st.spinner(
            "Running pipeline: parsing, extraction, checkability, retrieval, verification, risk scoring..."
        ):
            try:
                result = call_analyze(
                    file_bytes=uploaded.getvalue() if uploaded else None,
                    filename=uploaded.name if uploaded else None,
                    use_demo=use_demo,
                    company=company,
                    mode=st.session_state.get("mode", "mock"),
                    top_k=st.session_state.get("top_k", 5),
                    use_semantic=st.session_state.get("use_semantic", False),
                )
                st.session_state["last_result"] = result
                st.session_state["last_mode"] = st.session_state.get("mode", "mock")
            except RuntimeError as e:
                st.error(f"Analysis failed: {e}")
            except requests.RequestException as e:
                st.error(
                    f"Could not reach the backend API at {backend_url()}. Is it running? ({e})"
                )

    result = st.session_state.get("last_result")
    if result:
        st.divider()
        render_analysis_context(result, st.session_state.get("last_mode", "mock"))
        render_disclaimer_banner(result)
        if result["status"] == "no_claims":
            st.error(result["message"])
            if result.get("extraction_errors"):
                with st.expander("Extraction details"):
                    for e in result["extraction_errors"]:
                        st.write(e)
        else:
            render_executive_summary(result["summary"])
            render_claims_table(result["audit_records"])


def page_dataset_demo() -> None:
    st.title("Full Dataset Demo")
    st.caption(
        "Runs the curated synthetic dataset (legacy/v1_data/claims/claims.json) so ALIGN, "
        "CONTRADICT, and INSUFFICIENT_EVIDENCE examples are all reliably shown, "
        "independent of PDF extraction."
    )
    if st.button("Run Dataset Demo"):
        with st.spinner("Running pipeline over the curated dataset..."):
            try:
                result = call_demo_dataset(
                    top_k=st.session_state.get("top_k", 5),
                    use_semantic=st.session_state.get("use_semantic", False),
                )
                st.session_state["dataset_result"] = result
            except RuntimeError as e:
                st.error(f"Dataset demo failed: {e}")
            except requests.RequestException as e:
                st.error(
                    f"Could not reach the backend API at {backend_url()}. Is it running? ({e})"
                )

    result = st.session_state.get("dataset_result")
    if result:
        st.divider()
        render_analysis_context(result, "n/a (curated dataset, no extraction)")
        render_disclaimer_banner(result)
        render_executive_summary(result["summary"])
        render_claims_table(result["audit_records"])


# ---------------------------------------------------------------------------
# Sidebar + navigation
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Configuration")
    st.session_state["backend_url"] = st.text_input(
        "Backend API URL", value=st.session_state.get("backend_url", DEFAULT_BACKEND)
    )
    healthy = check_health()
    st.markdown(f"Backend status: {'**online**' if healthy else '**unreachable**'}")

    st.session_state["mode"] = st.selectbox("Extraction mode", ["mock", "groq", "ollama"], index=0)
    st.caption(
        "Use 'mock' for offline demo. Groq/Ollama require credentials configured on the backend."
    )
    st.session_state["top_k"] = st.slider("Evidence items per claim (top-k)", 1, 10, 5)
    st.session_state["use_semantic"] = st.checkbox(
        "Enable semantic (ChromaDB) retrieval", value=False
    )
    st.caption("Semantic retrieval requires downloading a local embedding model on first use.")

    st.divider()
    page = st.radio("Page", ["Upload & Analyze", "Full Dataset Demo"])

if page == "Upload & Analyze":
    page_upload_and_analyze()
else:
    page_dataset_demo()
