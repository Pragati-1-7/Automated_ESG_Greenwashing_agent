"""Judge + verdict agents (MiniCheck-style grounded stance, EmeraldMind-style
abstention). Jev reads the claim next to the evidence and calculator output:

  1. stance of every evidence item  (support / contradict / insufficient)
  2. stance of every sub-claim       (all its evidence together)
  3. claim verdict                   (ALIGN / CONTRADICT / INSUFFICIENT_EVIDENCE)

Hallucination control: the verdict state contains ONLY retrieved evidence,
and `validate_citations` checks that every cited id exists in what was fetched.
"""

from __future__ import annotations

import asyncio

from app.agents import prompts as P
from app.agents.evidence import TIER_NAME
from app.agents.investigator import evidence_block
from app.core.ablation import flags
from app.core.events import emit
from app.core.models import ClaimResult, Stance, SubClaim, VerdictResult
from app.decision.jev import JevEngine, choice, noul, score

_STANCE = choice(P.STANCE_Q, P.STANCE_OPTIONS)


def _period_line(sc: SubClaim) -> str:
    return f"Claimed period: {sc.period}" + (f"; baseline {sc.baseline_period}" if sc.baseline_period else "")


async def judge_subclaim(claim_id: str, company: str, sc: SubClaim, jev: JevEngine) -> SubClaim:
    calc = "\n".join(f"- {c.expression}" for c in sc.computations)

    async def one(e):
        state = (f"Company: {company}\nCLAIM (from the company's own report): {sc.text}\n{_period_line(sc)}\n\n"
                 f"EVIDENCE [{TIER_NAME.get(e.tier, e.tier)}] {e.title}: {e.snippet}"
                 + (f"\nCALCULATOR RESULTS:\n{calc}" if calc and e.tier <= 3 else ""))
        ans = await jev.ask(state, {"relevant": noul(P.RELEVANT_Q), "stance": _STANCE})
        a, rel = ans["stance"], ans["relevant"].p
        e.data = {**e.data, "relevance": rel}
        if rel < 0.5 and flags().relevance_gate:
            # Evidence relevance validation: off-topic evidence may not move the verdict.
            e.stance = Stance(label="insufficient", probabilities={"support": 0.0, "contradict": 0.0, "insufficient": 1.0},
                              confidence=round(1 - rel, 3))
        else:
            e.stance = Stance(label=a.choice, probabilities=a.probabilities, confidence=a.confidence)

    await asyncio.gather(*(one(e) for e in sc.evidence))
    gate = flags().relevance_gate
    relevant = [e for e in sc.evidence if not gate or e.data.get("relevance", 1) >= 0.5]
    if relevant:
        state = (f"Company: {company}\nCLAIM (from the company's own report): {sc.text}\n{_period_line(sc)}\n\n"
                 + evidence_block(sc, relevant))
        a = (await jev.ask(state, {"stance": _STANCE}))["stance"]
        sc.stance = Stance(label=a.choice, probabilities=a.probabilities, confidence=a.confidence)
    else:
        sc.stance = Stance(label="insufficient", probabilities={"support": 0.0, "contradict": 0.0, "insufficient": 1.0},
                           confidence=1.0)
    emit("judge", "decision", f"{sc.sub_id}: stance {sc.stance.label} ({sc.stance.confidence:.2f}); per evidence: "
         + ", ".join(f"{e.evidence_id}={e.stance.label}" for e in sc.evidence if e.stance), claim_id,
         {"stance": sc.stance.model_dump()})
    return sc


def validate_citations(sub_claims: list[SubClaim], cited: list[str]) -> list[str]:
    """Return any cited evidence id that was NOT retrieved (must be empty)."""
    have = {e.evidence_id for s in sub_claims for e in s.evidence}
    return [c for c in cited if c not in have]


async def decide(claim: ClaimResult, company: str, jev: JevEngine, llm) -> tuple[VerdictResult, float]:
    """Returns (verdict, severity 0-1)."""
    subs = claim.sub_claims
    blocks = []
    for s in subs:
        blocks.append(f"SUB-CLAIM {s.sub_id}: {s.text} ({_period_line(s)})\n"
                      f"Sub-claim stance: {s.stance.label if s.stance else 'n/a'}\n"
                      f"{evidence_block(s, [e for e in s.evidence if not flags().relevance_gate or e.data.get('relevance', 1) >= 0.5])}")
    state = f"Company: {company}\nCLAIM: {claim.text}\n\n" + "\n\n".join(blocks)
    ans = await jev.ask(state, {"verdict": choice(P.VERDICT_Q, P.VERDICT_OPTIONS),
                                "severity": score(P.SEVERITY_Q, P.SEVERITY_LEVELS)})
    v = ans["verdict"]
    label = v.choice
    # Grounding guard: a verdict other than INSUFFICIENT needs at least one retrieved, non-neutral evidence item.
    decisive = [e for s in subs for e in s.evidence if e.stance and e.stance.label != "insufficient"]
    if label != "INSUFFICIENT_EVIDENCE" and not decisive:
        emit("verdict", "info", "Grounding guard: no decisive retrieved evidence, abstaining", claim.claim_id)
        label = "INSUFFICIENT_EVIDENCE"
    want = {"ALIGN": "support", "CONTRADICT": "contradict"}.get(label)
    cited = [e for s in subs for e in s.evidence if e.stance and e.stance.label == want] if want else []
    cited.sort(key=lambda e: (e.tier, -(e.stance.confidence if e.stance else 0)))
    bad = validate_citations(subs, [e.evidence_id for e in cited])
    assert not bad, f"citation validator: {bad}"
    facts = [f"{e.evidence_id} ({TIER_NAME.get(e.tier, e.tier)}): {e.snippet[:220]}" for e in cited[:3]]
    facts += [c.expression for s in subs for c in s.computations][:3]
    if not facts:
        facts = ["No source returned data about this company and metric for the claimed period"]
    result = VerdictResult(label=label, probabilities=v.probabilities, confidence=v.probabilities.get(label, v.confidence),
                           reasoning=llm.explain(claim.text, label, v.probabilities.get(label, v.confidence), facts))
    emit("verdict", "verdict", f"{label} ({result.confidence:.2f}) for: {claim.text[:90]}", claim.claim_id,
         {"probabilities": v.probabilities, "severity": ans["severity"].level, "cited": [e.evidence_id for e in cited]})
    return result, ans["severity"].normalised
