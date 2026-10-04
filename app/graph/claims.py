"""Verify individual claim sentences (no PDF): used by POST /v2/verify-claim
and by the benchmark harness. Runs the SAME agents and the SAME per-claim
LangGraph sub-graph as a full report analysis."""

from __future__ import annotations

from app.agents import prompts as P
from app.agents import resolver, risk, triage
from app.core.models import ClaimResult, CompanyMatch, VerdictResult
from app.decision.jev import JevEngine, choice, noul
from app.tools.claim_parser import parse


async def verify_claim(text: str, company_name: str, jev: JevEngine, llm, doc_fy: str = "FY2025",
                       claim_id: str = "C001", company_cache: dict | None = None) -> tuple[ClaimResult, CompanyMatch]:
    from app.graph.pipeline import CLAIM_GRAPH

    cache = company_cache if company_cache is not None else {}
    if company_name not in cache:
        cache[company_name] = await resolver.resolve_name(company_name, f"Report published by {company_name}.", jev)
    match, company, facilities = cache[company_name]

    ans = await jev.ask(f"Section: n/a\nSentence: {text}",
                        {"is_claim": noul(P.IS_CLAIM), "metric": choice(P.METRIC_Q, P.METRIC_OPTIONS)})
    metric = None if ans["metric"].choice == "none" else ans["metric"].choice
    t = await triage.triage(claim_id, text, None, ans["is_claim"].p, metric, ans["metric"].confidence, jev)
    claim = ClaimResult(claim_id=claim_id, text=text, page=0, triage=t, parsed=parse(text))
    severity = 0.0
    if not t.checkable:
        conf = max(t.action_probs.get(t.action, 0.0), t.vagueness)
        claim.verdict = VerdictResult(label="NOT_CHECKABLE", probabilities={"NOT_CHECKABLE": 1.0}, confidence=conf,
                                      reasoning=llm.explain(text, "NOT_CHECKABLE", conf, [t.reason]))
    else:
        env = {"jev": jev, "llm": llm, "company": company, "facilities": facilities, "doc_fy": doc_fy,
               "report_company": match.name}
        out = await CLAIM_GRAPH.ainvoke({"claim": claim, "cenv": env})
        claim = out["claim_results"][0]
        severity = out.get("severities", {}).get(claim_id, 0.0)
    claim.risk = risk.claim_risk(claim, severity)
    return claim, match
