"""Investigator agent: executes the router's plan through the source tools,
then asks Jev whether the evidence is sufficient. If not, it widens the search
(sources it skipped, broader news window) for one more round. This is the
FIRE / DEFAME retrieve-until-confident loop, capped by a round budget."""

from __future__ import annotations

import asyncio

from app.agents import prompts as P
from app.agents.evidence import BUILDERS, TIER_NAME, Ctx, Gathered
from app.core.ablation import flags
from app.core.config import settings
from app.core.events import emit
from app.core.models import SubClaim
from app.decision.jev import JevEngine, noul


def evidence_block(sc: SubClaim, items=None) -> str:
    items = sc.evidence if items is None else items
    lines = [f"[{e.evidence_id} | {TIER_NAME.get(e.tier, e.tier)} | {e.endpoint}] {e.title}: {e.snippet}"
             for e in items]
    calc = [f"- {c.op}: {c.expression}" for c in sc.computations]
    out = "EXTERNAL EVIDENCE:\n" + ("\n".join(lines) if lines else "(none found)")
    if calc:
        out += "\nCALCULATOR RESULTS:\n" + "\n".join(calc)
    return out


def _merge(sc: SubClaim, g: Gathered) -> None:
    seen = {e.evidence_id for e in sc.evidence}
    sc.tool_calls.extend(g.tool_calls)
    sc.evidence.extend(e for e in g.evidence if e.evidence_id not in seen)
    have = {c.expression for c in sc.computations}
    sc.computations.extend(c for c in g.computations if c.expression not in have)


async def investigate(sc: SubClaim, ctx: Ctx, nums: list[tuple[float, str | None]], jev: JevEngine) -> SubClaim:
    chosen = [p["source"] for p in sc.sources_planned if p.get("selected")]
    emit("investigator", "start", f"{sc.sub_id}: round 1 over {', '.join(chosen) or 'no sources'}", ctx.claim_id)
    for g in await asyncio.gather(*(BUILDERS[s](sc, ctx, nums) for s in chosen)):
        _merge(sc, g)
    rounds = 1
    f = flags()
    max_rounds = f.max_rounds or settings().max_investigation_rounds
    while rounds < max_rounds and f.retrieval and not f.only_sources:
        state = f"Company: {ctx.company['name'] if ctx.company else 'unknown'}\nClaim: {sc.text}\nPeriod: {sc.period}\n\n" \
                + evidence_block(sc)
        p = (await jev.ask(state, {"sufficient": noul(P.SUFFICIENT_Q)}))["sufficient"].p
        emit("investigator", "decision", f"{sc.sub_id}: evidence sufficient? p={p:.2f}", ctx.claim_id,
             {"p_sufficient": p, "round": rounds})
        if p >= 0.5:
            break
        extra = [x["source"] for x in sc.sources_planned
                 if not x.get("selected") and x["probability"] >= 0.2 and (ctx.company or x["source"] == "news")]
        tasks = [BUILDERS[s](sc, ctx, nums) for s in extra if s != "news"]
        tasks.append(BUILDERS["news"](sc, ctx, nums, broaden=True))
        emit("investigator", "start", f"{sc.sub_id}: round {rounds + 1}, widening to "
             + ", ".join([*(s for s in extra if s != 'news'), "news (wider window)"]), ctx.claim_id)
        for g in await asyncio.gather(*tasks):
            _merge(sc, g)
        for x in sc.sources_planned:
            if x["source"] in extra:
                x["selected"] = True
        rounds += 1
    emit("investigator", "info", f"{sc.sub_id}: {len(sc.evidence)} evidence item(s), {len(sc.computations)} "
         f"calculation(s) after {rounds} round(s)", ctx.claim_id)
    return sc
