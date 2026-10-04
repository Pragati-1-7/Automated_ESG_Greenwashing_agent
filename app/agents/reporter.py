"""Report writer: technical summary + per-claim reasoning + audit trail, as
Markdown. Text comes from the LLM slot (MockLLM writes only from facts it is
given); every number is copied from the analysis, never generated."""

from __future__ import annotations

from app.agents.evidence import TIER_NAME
from app.core.models import AgentEvent, Analysis


def _esc(t: str) -> str:
    return t.replace("|", "/").replace("\n", " ")


def render(a: Analysis, events: list[AgentEvent], llm) -> str:
    s = a.summary
    vc = s.verdict_counts if s else {}
    by_id = {c.claim_id: c for c in a.claims}
    flags = [f"{cid} ({_esc(by_id[cid].text[:80])})" for cid in (s.top_red_flags[:3] if s else [])]
    summary = llm.summarise({
        "company": a.company.name if a.company else "Unknown company", "document": a.source_document,
        "claims": s.total_claims if s else 0, "candidates": s.total_candidates if s else 0,
        "checkable": s.checkable_claims if s else 0, "align": vc.get("ALIGN", 0), "contradict": vc.get("CONTRADICT", 0),
        "insufficient": vc.get("INSUFFICIENT_EVIDENCE", 0), "not_checkable": vc.get("NOT_CHECKABLE", 0),
        "risk": s.company_risk_score if s else None, "band": s.risk_band if s else None, "flags": flags})
    L = [f"# Greenwashing verification report: {a.company.name if a.company else 'Unknown company'}", "",
         f"Document: **{a.source_document}** ({a.page_count} pages). Analysis `{a.analysis_id}`, {a.created_at}.",
         f"Engines: decision = {a.engines.get('decision')}, text = {a.engines.get('llm')}.", "",
         "## Executive summary", "", summary, ""]
    if a.company:
        L += [f"Company resolution: {'resolved' if a.company.resolved else 'NOT resolved'}. {a.company.reason}.", ""]
    L += ["## Claims", "", "| ID | Page | Claim | Verdict | Confidence | Risk |", "|---|---|---|---|---|---|"]
    for c in sorted(a.claims, key=lambda c: -(c.risk.score if c.risk else 0)):
        L.append(f"| {c.claim_id} | {c.page} | {_esc(c.text[:110])} | {c.verdict.label} | "
                 f"{c.verdict.confidence:.2f} | {c.risk.score:.0f} ({c.risk.band}) |")
    L += ["", "## Reasoning and evidence per investigated claim", ""]
    for c in a.claims:
        if c.verdict.label == "NOT_CHECKABLE":
            continue
        L += [f"### {c.claim_id} (p.{c.page}): {c.verdict.label}", "", f"> {c.text}", "", c.verdict.reasoning, ""]
        for sc in c.sub_claims:
            L.append(f"- **{sc.sub_id}** [{sc.check_type}, {sc.metric or 'no metric'}, {sc.period}] stance: "
                     f"{sc.stance.label if sc.stance else 'n/a'}")
            for e in sc.evidence:
                L.append(f"    - {e.evidence_id} ({TIER_NAME.get(e.tier, e.tier)}, `{e.endpoint}`): "
                         f"{_esc(e.snippet[:240])} -> **{e.stance.label if e.stance else 'n/a'}**")
            for comp in sc.computations:
                L.append(f"    - calc: {comp.expression}")
        L.append("")
    L += ["## Audit trail", "", "| # | Time (UTC) | Agent | Type | Claim | Event |", "|---|---|---|---|---|---|"]
    for ev in events:
        L.append(f"| {ev.seq} | {ev.ts[11:23]} | {ev.agent} | {ev.type} | {ev.claim_id or ''} | {_esc(ev.message[:160])} |")
    L += ["", "## Limitations", "",
          "- Evidence comes from a synthetic mock-sources service; verdicts demonstrate the method, not facts about real firms.",
          "- Claims stated only inside chart images are not read (text and tables only).",
          "- A verdict is a triage signal for a human reviewer, not a legal finding.", "",
          f"_{a.disclaimer}_"]
    return "\n".join(L)
