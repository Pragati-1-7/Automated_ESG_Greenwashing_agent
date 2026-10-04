"""
app/llm/providers.py

The GENERATIVE slot of the system (writing text, never deciding). Decisions are
made by the Jev decision engine; this slot only

  * splits a compound claim into candidate clauses,
  * writes a search query,
  * turns structured verdict facts into readable reasoning / summaries.

`MockLLM` is the default: deterministic, offline, rate-limit free. It writes
ONLY from the structured facts it is handed, so it cannot hallucinate evidence.
`GroqLLM` is an optional drop-in (LLM_PROVIDER=groq) for nicer prose.
"""

from __future__ import annotations

import re
from typing import Protocol

from app.core.config import settings

_STOP = {"the", "a", "an", "our", "we", "of", "in", "to", "and", "by", "for", "at", "on", "with", "from", "has", "have",
         "been", "was", "were", "is", "are", "all", "any", "its", "their", "this", "that", "during", "year", "fy"}


class LLMProvider(Protocol):
    name: str

    def split_clauses(self, text: str) -> list[str]: ...
    def search_query(self, company: str | None, claim: str, metric_label: str | None) -> str: ...
    def explain(self, claim: str, label: str, confidence: float, facts: list[str]) -> str: ...
    def summarise(self, facts: dict) -> str: ...


class MockLLM:
    name = "mock-deterministic"

    def split_clauses(self, text: str) -> list[str]:
        """Split on clause boundaries that usually join two independent claims
        ('..., with zero fatalities ...', '... and recorded ...')."""
        t = text.strip().rstrip(".")
        m = re.match(r"(?i)(?:while|whereas|although)\s+(.+?),\s+(.+)$", t)
        if m:
            return [m.group(1).strip(), m.group(2).strip()]
        parts = re.split(r",\s+with\s+|;\s+|\s+and\s+(?=(?:we|our|recorded|achieved|reduced|cut|zero|no)\b)", t)
        parts = [p.strip(" ,") for p in parts if len(p.strip()) > 12]
        return parts if len(parts) > 1 else [text.strip()]

    def search_query(self, company: str | None, claim: str, metric_label: str | None) -> str:
        words = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", claim) if w.lower() not in _STOP]
        terms = ([company] if company else []) + ([metric_label] if metric_label else []) + words[:8]
        return " ".join(dict.fromkeys(terms))

    def explain(self, claim: str, label: str, confidence: float, facts: list[str]) -> str:
        lead = {
            "ALIGN": "The retrieved evidence supports this claim",
            "CONTRADICT": "The retrieved evidence contradicts this claim",
            "INSUFFICIENT_EVIDENCE": "No retrieved source can confirm or refute this claim",
            "NOT_CHECKABLE": "This statement is not a verifiable performance claim",
        }[label]
        body = " ".join(f"{f.rstrip('.')}." for f in facts[:6])
        return f"{lead} (decision confidence {confidence:.0%}). {body}".strip()

    def summarise(self, facts: dict) -> str:
        c = facts
        lines = [
            f"{c['company']} ({c['document']}): {c['claims']} claims extracted from {c['candidates']} screened sentences; "
            f"{c['checkable']} were checkable.",
            f"Verdicts: {c['align']} align, {c['contradict']} contradict, {c['insufficient']} insufficient evidence, "
            f"{c['not_checkable']} not checkable.",
        ]
        if c.get("risk") is not None:
            lines.append(f"Company greenwashing risk score: {c['risk']:.0f}/100 ({c['band']}).")
        if c.get("flags"):
            lines.append("Most serious flags: " + "; ".join(c["flags"]) + ".")
        return " ".join(lines)


class GroqLLM(MockLLM):
    """Optional. Uses Groq for prose only; falls back to MockLLM on any error so
    rate limits can never break an analysis."""

    def __init__(self) -> None:
        from langchain_groq import ChatGroq
        self.name = f"groq:{settings().groq_model}"
        self._chat = ChatGroq(model=settings().groq_model, api_key=settings().groq_api_key, temperature=0)

    def explain(self, claim: str, label: str, confidence: float, facts: list[str]) -> str:
        try:
            msg = ("Write 2-3 plain sentences explaining this verdict to an ESG analyst. Use ONLY these facts; "
                   f"do not add numbers.\nClaim: {claim}\nVerdict: {label} ({confidence:.0%})\nFacts:\n- "
                   + "\n- ".join(facts[:8]))
            return self._chat.invoke(msg).content.strip()
        except Exception:  # noqa: BLE001
            return super().explain(claim, label, confidence, facts)


def get_llm() -> LLMProvider:
    if settings().llm_provider == "groq" and settings().groq_api_key:
        try:
            return GroqLLM()
        except Exception:  # noqa: BLE001
            return MockLLM()
    return MockLLM()
