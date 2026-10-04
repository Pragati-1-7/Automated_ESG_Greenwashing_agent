"""Resolver agent: which company is this report about, and does it exist in the
external sources? Fuzzy registry lookup (tool) + Jev same-entity decision."""

from __future__ import annotations

import re
from collections import Counter

from app.agents import prompts as P
from app.core.events import emit
from app.core.models import CompanyMatch
from app.decision.jev import JevEngine, noul
from app.tools import sources

_NAME = re.compile(r"\b([A-Z][A-Za-z&.'\-]+(?:\s+(?:&|and|[A-Z][A-Za-z&.'\-]+)){0,5}\s+"
                   r"(?:Ltd|Limited|Pvt\.?\s+Ltd|Private\s+Limited))\b")


def candidate_names(front_text: str) -> list[str]:
    names = [re.sub(r"\s+", " ", m.group(1)).strip() for m in _NAME.finditer(front_text)]
    return [n for n, _ in Counter(names).most_common(3)]


async def resolve(front_text: str, jev: JevEngine) -> tuple[CompanyMatch, dict | None, list[dict]]:
    emit("resolver", "start", "Identifying the reporting company")
    names = candidate_names(front_text)
    if not names:
        emit("resolver", "decision", "No company name found in the report front matter")
        return CompanyMatch(resolved=False, name="Unknown", match_score=0, reason="No legal entity name found"), None, []
    return await resolve_name(names[0], front_text, jev)


async def resolve_name(report_name: str, context: str, jev: JevEngine) -> tuple[CompanyMatch, dict | None, list[dict]]:
    front_text = context
    _, data = await sources.resolve_company(report_name)
    cands = data.get("candidates", [])
    if not cands:
        return CompanyMatch(resolved=False, name=report_name, match_score=0, reason="Registry returned no candidates"), None, []
    top = cands[0]
    state = (f"Company named in the report: {report_name}\nReport front matter: {front_text[:600]}\n\n"
             f"Registry record: {top['name']} (CIN {top['cin']}), sector {top['sector']}, HQ {top['hq_city']}, "
             f"{top['hq_state']}; aliases {', '.join(top['aliases'])}")
    ans = await jev.ask(state, {"same": noul(P.SAME_ENTITY_Q)})
    p = ans["same"].p
    resolved = p >= 0.5 and top["match_score"] >= 0.3
    reason = (f"Registry candidate '{top['name']}' (string similarity {top['match_score']:.2f}); "
              f"Jev same-entity probability {p:.2f}")
    emit("resolver", "decision", ("Resolved to " if resolved else "Not resolved; closest was ") + top["name"],
         data={"report_name": report_name, "candidate": top["name"], "similarity": top["match_score"], "p_same": p})
    match = CompanyMatch(resolved=resolved, company_id=top["company_id"] if resolved else None,
                         name=top["name"] if resolved else report_name,
                         match_score=round(p if resolved else top["match_score"], 3), reason=reason)
    if not resolved:
        return match, None, []
    _, fac = await sources.facilities(top["company_id"])
    return match, top, fac.get("rows", [])
