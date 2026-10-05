"""Report writer: a readable verification report in Markdown.

Layout (same as the UI's Report tab):
  header + score -> summary -> key findings -> claims by verdict -> method -> audit trail (appendix)

Text comes from the LLM slot (MockLLM writes only from facts it is given);
every number is copied from the analysis, never generated."""

from __future__ import annotations

import re

from app.agents.evidence import TIER_NAME
from app.core.models import AgentEvent, Analysis, ClaimResult

VERDICT_NAME = {"ALIGN": "Align", "CONTRADICT": "Contradict", "INSUFFICIENT_EVIDENCE": "Insufficient evidence",
                "NOT_CHECKABLE": "Not checkable"}
ACTION_NAME = {"planning": "future target or commitment", "indeterminate": "vague statement, nothing measurable",
               "implemented": "no measurable figure to check"}


def _esc(t: str) -> str:
    return t.replace("|", "/").replace("\n", " ").strip()


def clean_snippet(t: str) -> str:
    """Drop the turnover line the evidence builder appends for intensity checks; it is noise in a report."""
    return re.sub(r"\s*Turnover \(Rs crore\) as filed:[^.]*(\.\d[^.]*)*\.", "", t).strip()


def _clip(t: str, n: int) -> str:
    t = _esc(t)
    return t if len(t) <= n else t[: n - 1].rstrip() + "..."


def key_evidence(c: ClaimResult):
    """The evidence item that best explains the verdict: matching stance, most reliable tier first."""
    want = {"CONTRADICT": "contradict", "ALIGN": "support"}.get(c.verdict.label)
    items = [e for sc in c.sub_claims for e in sc.evidence]
    if want:
        hits = [e for e in items if e.stance and e.stance.label == want]
        if hits:
            return sorted(hits, key=lambda e: e.tier)[0]
    return None


def _calc(c: ClaimResult) -> str | None:
    for sc in c.sub_claims:
        for comp in sc.computations:
            return comp.expression
    return None


def _finding(c: ClaimResult, n: int | None = None, brief: bool = False) -> list[str]:
    head = f"{n}. " if n else "- "
    L = [f"{head}**\"{_esc(c.text)}\"** (page {c.page})",
         f"    - Verdict: **{VERDICT_NAME[c.verdict.label]}**, confidence {c.verdict.confidence:.0%}"
         + (f", risk {c.risk.score:.0f}/100 ({c.risk.band})" if c.risk else "")]
    if brief:
        return L
    e = key_evidence(c)
    if e:
        L.append(f"    - What the records show ({TIER_NAME.get(e.tier, e.tier)}): {_clip(clean_snippet(e.snippet), 320)}")
    calc = _calc(c)
    if calc:
        L.append(f"    - Calculation: `{calc}`")
    return L


def _llm_name(l: str | None) -> str:
    if l and l.startswith("groq:"):
        return l[5:].replace("openai/", "").upper() + " (via Groq)"
    return "a built-in template writer that only restates the facts"


def render(a: Analysis, events: list[AgentEvent], llm) -> str:
    s = a.summary
    vc = s.verdict_counts if s else {}
    name = a.company.name if a.company else "Unknown company"
    by_id = {c.claim_id: c for c in a.claims}
    flags = [f"{cid} ({_esc(by_id[cid].text[:80])})" for cid in (s.top_red_flags[:3] if s else [])]
    summary = llm.summarise({
        "company": name, "document": a.source_document,
        "claims": s.total_claims if s else 0, "candidates": s.total_candidates if s else 0,
        "checkable": s.checkable_claims if s else 0, "align": vc.get("ALIGN", 0), "contradict": vc.get("CONTRADICT", 0),
        "insufficient": vc.get("INSUFFICIENT_EVIDENCE", 0), "not_checkable": vc.get("NOT_CHECKABLE", 0),
        "risk": s.company_risk_score if s else None, "band": s.risk_band if s else None, "flags": flags})

    L = [f"# Greenwashing verification report: {name}", "",
         f"**Document:** {a.source_document} ({a.page_count} pages)  ",
         f"**Analysed:** {a.created_at[:16].replace('T', ' ')} UTC  ",
         f"**Analysis ID:** {a.analysis_id}", ""]

    if s:
        score = f"{s.company_risk_score:.0f}/100 ({s.risk_band})" if s.company_risk_score is not None else "n/a"
        L += ["## Result at a glance", "",
              "| Greenwashing risk score | Contradicted | Aligned | Insufficient evidence | Not checkable |",
              "|---|---|---|---|---|",
              f"| **{score}** | {vc.get('CONTRADICT', 0)} | {vc.get('ALIGN', 0)} | "
              f"{vc.get('INSUFFICIENT_EVIDENCE', 0)} | {vc.get('NOT_CHECKABLE', 0)} |", "",
              f"{s.total_claims} claims were found in {s.total_candidates} screened sentences; "
              f"{s.checkable_claims} could be checked against external records.", ""]

    if s:
        summary = (f"{name}'s report makes {s.total_claims} ESG claims. {s.checkable_claims} could be checked against "
                   f"external records: {vc.get('CONTRADICT', 0)} are contradicted, {vc.get('ALIGN', 0)} are confirmed and "
                   f"{vc.get('INSUFFICIENT_EVIDENCE', 0)} have no reliable record either way. The other "
                   f"{vc.get('NOT_CHECKABLE', 0)} are future targets or vague statements.")
        if s.company_risk_score is not None:
            summary += f" Overall greenwashing risk: **{s.company_risk_score:.0f}/100 ({s.risk_band})**."
    L += ["## Summary", "", summary, ""]
    if a.company:
        L += [f"Company matched to registry record **{a.company.name}** "
              f"({a.company.match_score:.0%} confidence).", ""]

    flagged = [by_id[cid] for cid in (s.top_red_flags if s else []) if cid in by_id]
    if flagged:
        L += ["## Key findings", ""]
        for i, c in enumerate(flagged[:5], 1):
            L += _finding(c, i)
        L.append("")

    order = sorted(a.claims, key=lambda c: -(c.risk.score if c.risk else 0))
    groups = [("CONTRADICT", "Contradicted by external records"), ("ALIGN", "Confirmed by external records"),
              ("INSUFFICIENT_EVIDENCE", "Not enough evidence to decide")]
    L += ["## All checked claims", ""]
    for lab, title in groups:
        cs = [c for c in order if c.verdict.label == lab]
        if not cs:
            continue
        L += [f"### {title} ({len(cs)})", ""]
        for c in cs:
            if lab == "INSUFFICIENT_EVIDENCE":
                L.append(f"- \"{_esc(c.text)}\" (page {c.page}): no reliable record covers this claim for the stated period.")
            else:
                L += _finding(c, brief=c in flagged[:5])
                if c in flagged[:5]:
                    L.append("    - Evidence: see Key findings above.")
        L.append("")

    nc = [c for c in order if c.verdict.label == "NOT_CHECKABLE"]
    if nc:
        L += [f"### Not checkable ({len(nc)})", "",
              "Future targets and vague statements cannot be verified yet. Vague wording still adds to the risk score.", ""]
        for c in nc:
            L.append(f"- \"{_esc(c.text)}\" (page {c.page}): {ACTION_NAME.get(c.triage.action, c.triage.action)}")
        L.append("")

    L += ["## How this report was produced", "",
          f"- Decision engine: {a.engines.get('decision')} (every judgement is a typed question answered with a probability).",
          f"- Orchestration: {a.engines.get('orchestrator', 'LangGraph')}; explanations written by {_llm_name(a.engines.get('llm'))}.",
          "- Evidence trust levels: Tier 1 regulatory filing, Tier 2 regulator record, Tier 3 third-party dataset, "
          "Tier 4 company press release, Tier 5 news. Tiers 1-2 outweigh company PR.",
          "- All arithmetic is done by a calculator tool and shown above.",
          f"- {a.synthetic_notice}", "", f"_{a.disclaimer}_", ""]

    L += ["## Audit trail", "", "Every step the agents took, in order.", "",
          "| # | Time (UTC) | Agent | Claim | Step |", "|---|---|---|---|---|"]
    for ev in events:
        L.append(f"| {ev.seq} | {ev.ts[11:19]} | {ev.agent} | {ev.claim_id or ''} | {_clip(ev.message, 140)} |")
    return "\n".join(L)
