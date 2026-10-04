"""Claim extractor agent. Screens every sentence of the report with Jev
(is it a company ESG claim? which metric?) and keeps the claims."""

from __future__ import annotations

import asyncio
import re

from app.agents import prompts as P
from app.core.events import emit
from app.core.models import Sentence
from app.decision.jev import JevEngine, choice, noul

# Pure document-structure filter (not a claim judgement): back-matter that by
# construction holds no company claims.
_SKIP_SECTIONS = re.compile(r"gri content index|glossary|contents|forward-looking|abbreviations", re.I)
_ESG_HINT = re.compile(r"\d|zero|\bno\b|net[- ]zero|renewable|emission|carbon|water|waste|safety|fatalit|injur|"
                       r"women|divers|forest|deforest|biodivers|penalt|violation|complian|assur|certif|sustainab|"
                       r"green|clean|climate|commit|target|aim|pledge|planet|wage|discharge|recycl|plastic", re.I)


def screen(sentences: list[Sentence]) -> list[Sentence]:
    out = []
    for s in sentences:
        if s.section and _SKIP_SECTIONS.search(s.section):
            continue
        if not (30 <= len(s.text) <= 400) or not _ESG_HINT.search(s.text):
            continue
        toks = s.text.split()
        if sum(bool(re.fullmatch(r"[\d.,%()\-]+", t)) for t in toks) >= 4 and not s.text.rstrip().endswith("."):
            continue   # a flattened table row, not prose
        out.append(s)
    return out


async def extract(sentences: list[Sentence], jev: JevEngine, threshold: float = 0.6) -> list[dict]:
    cands = screen(sentences)
    emit("extractor", "start", f"Screening {len(cands)} of {len(sentences)} sentences with the decision engine",
         data={"sentences": len(sentences), "candidates": len(cands)})

    async def judge(s: Sentence) -> dict | None:
        ans = await jev.ask(f"Section: {s.section or 'n/a'}\nSentence: {s.text}",
                            {"is_claim": noul(P.IS_CLAIM), "metric": choice(P.METRIC_Q, P.METRIC_OPTIONS)})
        p = ans["is_claim"].p
        if p < threshold:
            return None
        m = ans["metric"]
        return {"sentence": s, "is_claim_prob": p, "metric": None if m.choice == "none" else m.choice,
                "metric_confidence": m.confidence}

    found = [r for r in await asyncio.gather(*(judge(s) for s in cands)) if r]
    for r in found:
        emit("extractor", "decision", f"Claim on p.{r['sentence'].page}: {r['sentence'].text[:110]}",
             data={"p_claim": r["is_claim_prob"], "metric": r["metric"]})
    emit("extractor", "info", f"{len(found)} claims extracted", data={"claims": len(found), "screened": len(cands)})
    return found
