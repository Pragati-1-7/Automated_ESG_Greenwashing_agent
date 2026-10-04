"""Decomposer agent (AFEV / ProgramFC style): split a claim into atomic
sub-claims, then let Jev type each one (metric + kind of check). The typed
check is the 'program' the investigators execute."""

from __future__ import annotations

import asyncio

from app.agents import prompts as P
from app.core.events import emit
from app.core.models import Parsed, SubClaim
from app.decision.jev import JevEngine, choice
from app.tools.claim_parser import parse


async def decompose(claim_id: str, text: str, parsed: Parsed, claim_metric: str | None, doc_fy: str,
                    llm, jev: JevEngine) -> list[SubClaim]:
    clauses = llm.split_clauses(text)

    async def type_clause(i: int, clause: str) -> SubClaim:
        ans = await jev.ask(f"Full claim: {text}\nFragment to verify: {clause}",
                            {"metric": choice(P.METRIC_Q, P.METRIC_OPTIONS),
                             "check": choice(P.CHECK_TYPE_Q, P.CHECK_TYPE_OPTIONS)})
        cp = parse(clause)
        metric = ans["metric"].choice
        metric = None if metric == "none" else metric
        if len(clauses) == 1 and claim_metric and ans["metric"].confidence < 0.6:
            metric = claim_metric
        nums = cp.numbers or parsed.numbers
        claimed = next((n.value for n in reversed(nums) if n.unit not in ("km",)), None)
        return SubClaim(sub_id=f"{claim_id}.{i + 1}", text=clause, metric=metric, check_type=ans["check"].choice,
                        period=cp.period or parsed.period or doc_fy,
                        baseline_period=cp.baseline_period or parsed.baseline_period, claimed_value=claimed)

    subs = list(await asyncio.gather(*(type_clause(i, c) for i, c in enumerate(clauses))))
    emit("decomposer", "decision", f"{len(subs)} atomic sub-claim(s): "
         + "; ".join(f"[{s.check_type} | {s.metric or 'no metric'} | {s.period}] {s.text[:60]}" for s in subs),
         claim_id, {"sub_claims": [s.model_dump(include={'sub_id', 'metric', 'check_type', 'period', 'baseline_period',
                                                         'claimed_value'}) for s in subs]})
    return subs
