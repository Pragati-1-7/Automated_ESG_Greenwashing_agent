"""
app/graph/pipeline.py

LangGraph orchestration. Wiring only: every node calls one agent.

    ingest -> resolve -> extract -> triage --Send(per checkable claim)--> claim_pipeline -> aggregate -> report
                                          \\-----------(no checkable claims)--------------/

claim_pipeline is a compiled sub-graph run once per claim, in parallel:

    decompose -> route -> investigate -> judge -> verdict

The investigate node contains the FIRE-style loop (retrieve, ask Jev if the
evidence suffices, widen and retry within a round budget).
"""

from __future__ import annotations

import asyncio
import operator
import re
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents import decomposer, extractor, investigator, judge, reporter, resolver, risk, router, triage
from app.agents.evidence import Ctx
from app.core.config import settings
from app.core.events import emit
from app.core.models import (Analysis, ClaimResult, Summary, VerdictResult)
from app.ingest.pdf import parse_pdf
from app.tools.claim_parser import fy_from, parse


# ----------------------------------------------------------------------------- state
class PipelineState(TypedDict, total=False):
    pdf_path: str
    analysis: Analysis
    env: dict[str, Any]                 # jev, llm, sink, company, facilities, doc_fy
    doc: Any
    extracted: list[dict]
    to_investigate: list[ClaimResult]
    claim_results: Annotated[list[ClaimResult], operator.add]
    severities: Annotated[dict[str, float], operator.or_]
    report_md: str


class ClaimState(TypedDict, total=False):
    claim: ClaimResult
    cenv: dict[str, Any]
    claim_results: Annotated[list[ClaimResult], operator.add]
    severities: Annotated[dict[str, float], operator.or_]


def _company_name(env: dict) -> str:
    return env["company"]["name"] if env.get("company") else env.get("report_company", "unknown company")


# ----------------------------------------------------------------------------- top-level nodes
async def node_ingest(s: PipelineState) -> dict:
    emit("ingest", "start", f"Parsing {s['analysis'].source_document}")
    doc = await asyncio.to_thread(parse_pdf, s["pdf_path"])
    m = re.search(r"FY\s?20\d{2}\s?[-–]\s?\d{2}|FY\s?20\d{2}|20\d{2}[-–]\d{2}", doc.front_text)
    doc_fy = (fy_from(m.group(0)) if m else None) or "FY2025"
    a = s["analysis"]
    a.page_count = doc.page_count
    emit("ingest", "info", f"{doc.page_count} pages, {len(doc.sentences)} sentences, reporting year {doc_fy}",
         data={"pages": doc.page_count, "sentences": len(doc.sentences), "doc_fy": doc_fy})
    return {"doc": doc, "env": {**s["env"], "doc_fy": doc_fy}}


async def node_resolve(s: PipelineState) -> dict:
    env = s["env"]
    match, company, facilities = await resolver.resolve(s["doc"].front_text, env["jev"])
    s["analysis"].company = match
    return {"env": {**env, "company": company, "facilities": facilities, "report_company": match.name}}


async def node_extract(s: PipelineState) -> dict:
    found = await extractor.extract(s["doc"].sentences, s["env"]["jev"])
    return {"extracted": found}


async def node_triage(s: PipelineState) -> dict:
    env = s["env"]
    jev = env["jev"]
    found = s["extracted"]

    async def one(i: int, r: dict) -> ClaimResult:
        sent = r["sentence"]
        cid = f"C{i + 1:03d}"
        t = await triage.triage(cid, sent.text, sent.section, r["is_claim_prob"], r["metric"],
                                r["metric_confidence"], jev)
        return ClaimResult(claim_id=cid, text=sent.text, page=sent.page, section=sent.section, triage=t,
                           parsed=parse(sent.text))

    claims = await asyncio.gather(*(one(i, r) for i, r in enumerate(found)))
    checkable = [c for c in claims if c.triage.checkable]
    # Budget: investigate the most material checkable claims first.
    checkable.sort(key=lambda c: c.triage.materiality, reverse=True)
    limit = env.get("max_claims") or settings().max_claims
    investigate, deferred = checkable[:limit], checkable[limit:]
    done = []
    for c in claims:
        if not c.triage.checkable or c in deferred:
            label = "NOT_CHECKABLE"
            reason = c.triage.reason if not c.triage.checkable else "Not investigated (claim budget reached)"
            c.verdict = VerdictResult(label=label, probabilities={"NOT_CHECKABLE": 1.0}, confidence=max(
                c.triage.action_probs.get(c.triage.action, 0.0), c.triage.vagueness), reasoning=env["llm"].explain(
                c.text, label, c.triage.action_probs.get(c.triage.action, 0.0), [reason]))
            done.append(c)
    emit("triage", "info", f"{len(investigate)} claims sent to investigation, {len(done)} not checkable",
         data={"investigate": len(investigate), "not_checkable": len(done)})
    return {"to_investigate": investigate, "claim_results": done}


def fan_out(s: PipelineState):
    env = s["env"]
    sends = [Send("claim_pipeline", {"claim": c, "cenv": env}) for c in s.get("to_investigate", [])]
    return sends or "aggregate"


async def node_aggregate(s: PipelineState) -> dict:
    claims = sorted(s.get("claim_results", []), key=lambda c: c.claim_id)
    sev = s.get("severities", {})
    for c in claims:
        c.risk = risk.claim_risk(c, sev.get(c.claim_id, 0.0))
    company_score = risk.company_risk(claims)
    counts = {k: 0 for k in ("ALIGN", "CONTRADICT", "INSUFFICIENT_EVIDENCE", "NOT_CHECKABLE")}
    for c in claims:
        counts[c.verdict.label] += 1
    flags = [c.claim_id for c in sorted(claims, key=lambda c: c.risk.score, reverse=True)
             if c.verdict.label == "CONTRADICT"][:5]
    a = s["analysis"]
    a.claims = claims
    a.summary = Summary(total_candidates=len(extractor.screen(s["doc"].sentences)), total_claims=len(claims),
                        checkable_claims=sum(c.triage.checkable for c in claims), verdict_counts=counts,
                        company_risk_score=company_score,
                        risk_band=risk.band(company_score) if company_score is not None else None, top_red_flags=flags)
    emit("risk", "info", f"Company greenwashing risk score {company_score}/100 ({a.summary.risk_band})"
         if company_score is not None else "No claims to score", data={"verdict_counts": counts})
    return {}


async def node_report(s: PipelineState) -> dict:
    emit("reporter", "info", "Writing technical summary and audit trail")
    s["analysis"].engines["decision"] = f"TypeSafe {s['env']['jev'].model_version}"
    md = reporter.render(s["analysis"], s["env"]["sink"].events, s["env"]["llm"])
    return {"report_md": md}


# ----------------------------------------------------------------------------- per-claim sub-graph nodes
def _ctx(cs: ClaimState) -> Ctx:
    e = cs["cenv"]
    c = cs["claim"]
    return Ctx(company=e.get("company"), facilities=e.get("facilities", []), doc_fy=e["doc_fy"], claim_id=c.claim_id,
               claim_text=c.text, llm=e["llm"])


async def node_decompose(cs: ClaimState) -> dict:
    c, e = cs["claim"], cs["cenv"]
    emit("decomposer", "start", f"Decomposing: {c.text[:100]}", c.claim_id)
    c.sub_claims = await decomposer.decompose(c.claim_id, c.text, c.parsed, c.triage.metric, e["doc_fy"],
                                              e["llm"], e["jev"])
    return {"claim": c}


async def node_route(cs: ClaimState) -> dict:
    c, e = cs["claim"], cs["cenv"]
    plans = await asyncio.gather(*(router.plan_sources(c.claim_id, sc, bool(e.get("company")), e["jev"])
                                   for sc in c.sub_claims))
    for sc, plan in zip(c.sub_claims, plans):
        sc.sources_planned = plan
    return {"claim": c}


async def node_investigate(cs: ClaimState) -> dict:
    c, e = cs["claim"], cs["cenv"]
    ctx = _ctx(cs)

    async def run(sc):
        nums = [(n.value, n.unit) for n in (parse(sc.text).numbers or c.parsed.numbers)]
        return await investigator.investigate(sc, ctx, nums, e["jev"])

    c.sub_claims = list(await asyncio.gather(*(run(sc) for sc in c.sub_claims)))
    return {"claim": c}


async def node_judge(cs: ClaimState) -> dict:
    c, e = cs["claim"], cs["cenv"]
    name = _company_name(e)
    c.sub_claims = list(await asyncio.gather(*(judge.judge_subclaim(c.claim_id, name, sc, e["jev"])
                                               for sc in c.sub_claims)))
    return {"claim": c}


async def node_verdict(cs: ClaimState) -> dict:
    c, e = cs["claim"], cs["cenv"]
    c.verdict, severity = await judge.decide(c, _company_name(e), e["jev"], e["llm"])
    return {"claim_results": [c], "severities": {c.claim_id: severity}}


# ----------------------------------------------------------------------------- build
def build_claim_graph():
    g = StateGraph(ClaimState)
    for name, fn in [("decompose", node_decompose), ("route", node_route), ("investigate", node_investigate),
                     ("judge", node_judge), ("verdict", node_verdict)]:
        g.add_node(name, fn)
    g.add_edge(START, "decompose")
    g.add_edge("decompose", "route")
    g.add_edge("route", "investigate")
    g.add_edge("investigate", "judge")
    g.add_edge("judge", "verdict")
    g.add_edge("verdict", END)
    return g.compile()


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("ingest", node_ingest)
    g.add_node("resolve", node_resolve)
    g.add_node("extract", node_extract)
    g.add_node("triage", node_triage)
    g.add_node("claim_pipeline", CLAIM_GRAPH)
    g.add_node("aggregate", node_aggregate)
    g.add_node("report", node_report)
    g.add_edge(START, "ingest")
    g.add_edge("ingest", "resolve")
    g.add_edge("resolve", "extract")
    g.add_edge("extract", "triage")
    g.add_conditional_edges("triage", fan_out, ["claim_pipeline", "aggregate"])
    g.add_edge("claim_pipeline", "aggregate")
    g.add_edge("aggregate", "report")
    g.add_edge("report", END)
    return g.compile()


CLAIM_GRAPH = build_claim_graph()
GRAPH = build_graph()
