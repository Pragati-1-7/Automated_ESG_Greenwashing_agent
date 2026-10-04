"""Triage agent (A3CG-style): implemented / planning / indeterminate, vagueness,
checkability and materiality. Decides which claims go to investigation."""

from __future__ import annotations

from app.agents import prompts as P
from app.core.events import emit
from app.core.models import Triage
from app.decision.jev import JevEngine, choice, noul, score


async def triage(claim_id: str, text: str, section: str | None, is_claim_prob: float, metric: str | None,
                 metric_conf: float, jev: JevEngine) -> Triage:
    ans = await jev.ask(
        f"Section: {section or 'n/a'}\nStatement: {text}",
        {"action": choice(P.ACTION_Q, P.ACTION_OPTIONS), "vague": noul(P.VAGUE_Q), "checkable": noul(P.CHECKABLE_Q),
         "materiality": score(P.MATERIALITY_Q, P.MATERIALITY_LEVELS)},
    )
    action = ans["action"]
    vague, chk, mat = ans["vague"].p, ans["checkable"].p, ans["materiality"]
    checkable = action.choice == "implemented" and vague < 0.6
    if action.choice == "planning":
        reason = "Future target or commitment: cannot be verified against past records yet"
    elif action.choice == "indeterminate" or vague >= 0.6:
        reason = "Vague or non-attributable statement with no measurable outcome (cheap talk)"
    elif chk < 0.5:
        reason = "Concrete past-performance claim, but few external record types cover it; investigating anyway"
    else:
        reason = f"Concrete past-performance claim; checkable against external records (p={chk:.2f})"
    t = Triage(is_claim_prob=is_claim_prob, action=action.choice, action_probs=action.probabilities,
               checkable=checkable, materiality=mat.normalised, vagueness=vague, metric=metric,
               metric_confidence=metric_conf, reason=reason)
    emit("triage", "decision", f"{action.choice}, {'checkable' if checkable else 'not checkable'}: {reason}",
         claim_id, {"action": action.choice, "p_vague": vague, "p_checkable": chk, "materiality": mat.level})
    return t
