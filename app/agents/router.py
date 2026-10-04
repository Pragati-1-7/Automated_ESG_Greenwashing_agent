"""Router agent: Jev decides, per sub-claim, which external sources could hold
evidence. Each source is a separate yes/no question so the plan comes with a
probability per source (shown in the UI)."""

from __future__ import annotations

from app.agents import prompts as P
from app.core.ablation import flags
from app.core.events import emit
from app.core.models import SubClaim
from app.decision.jev import JevEngine, noul
from data_gen.spec import METRICS


async def plan_sources(claim_id: str, sc: SubClaim, company_known: bool, jev: JevEngine) -> list[dict]:
    metric = METRICS.get(sc.metric or "", {}).get("label", "unspecified")
    state = (f"Claim to verify: {sc.text}\nMetric: {metric}\nCheck type: {sc.check_type}\n"
             f"Period: {sc.period}" + (f" (baseline {sc.baseline_period})" if sc.baseline_period else ""))
    ans = await jev.ask(state, {k: noul(q) for k, q in P.SOURCE_QUESTIONS.items()})
    plan = sorted(({"source": k, "probability": round(a.p, 3)} for k, a in ans.items()),
                  key=lambda r: r["probability"], reverse=True)
    chosen = [p for p in plan if p["probability"] >= P.SOURCE_THRESHOLD]
    if not chosen:
        chosen = plan[:1]
    f = flags()
    if not f.retrieval:
        chosen = []
    elif f.only_sources:
        chosen = [p for p in plan if p["source"] in f.only_sources]
    if not company_known:
        # Without a registry match only open sources (news) can be searched by name.
        chosen = [p for p in plan if p["source"] == "news" and f.retrieval]
    for p in plan:
        p["selected"] = p in chosen
    emit("router", "decision", f"{sc.sub_id}: query " + ", ".join(f"{p['source']} ({p['probability']:.2f})" for p in chosen),
         claim_id, {"plan": plan})
    return plan
