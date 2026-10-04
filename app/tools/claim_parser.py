"""Deterministic claim parser tool: pulls numbers (with Indian units), fiscal
periods, baselines and facility hints out of one claim sentence. It only
reads the text; deciding what the numbers MEAN is left to the agents."""

from __future__ import annotations

import re

from app.core.models import Parsed, ParsedNumber

_MULT = {"lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "crores": 1e7, "million": 1e6, "mn": 1e6, "billion": 1e9,
         "thousand": 1e3}
_UNIT = (r"%|per cent|percent|tco2e|mtco2e|ktco2e|tonnes?|t\b|mt\b|kt\b|kl\b|kilolitres?|ml\b|megalitres?|"
         r"litres?|mwh|gwh|kwh|gj|tj|pj|ha\b|hectares?|km\b|mw\b|x\b|times")
_NUM = re.compile(
    r"(?P<raw>(?:rs\.?\s*)?(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
    r"(?P<mult>lakh|lakhs|crore|crores|million|mn|billion|thousand)?\s*(?P<unit>" + _UNIT + r")?)",
    re.I)
_WORD_NUM = {"zero": 0, "no": 0, "half": 50, "doubled": 2, "double": 2, "tripled": 3, "twice": 2}


def fy_from(text: str) -> str | None:
    """'FY2025', 'FY25', 'FY2024-25', '2024-25' -> 'FY2025'."""
    m = re.search(r"\bFY\s?(\d{4})\s?[-–/]\s?(\d{2,4})\b", text, re.I) or re.search(r"\b(\d{4})[-–](\d{2})\b", text)
    if m:
        end = m.group(2)
        return f"FY{m.group(1)[:2] + end[-2:]}" if len(end) <= 2 else f"FY{end}"
    m = re.search(r"\bFY\s?'?(\d{4}|\d{2})\b", text, re.I)
    if m:
        y = m.group(1)
        return f"FY{'20' + y if len(y) == 2 else y}"
    return None


def periods(text: str) -> tuple[str | None, str | None]:
    """Return (period, baseline_period)."""
    fys = []
    for m in re.finditer(r"\bFY\s?\d{4}(?:\s?[-–]\s?\d{2,4})?|\b\d{4}[-–]\d{2}\b|\bFY\s?\d{2}\b", text, re.I):
        fy = fy_from(m.group(0))
        if fy:
            fys.append((m.start(), fy))
    baseline = None
    bm = re.search(r"(since|against|compared with|compared to|versus|vs\.?|from|relative to|over|than(?: in)?|than that of)\s+(our\s+|the\s+)?"
                   r"(FY\s?\d{4}(?:\s?[-–]\s?\d{2,4})?|\d{4}[-–]\d{2}|FY\s?\d{2})", text, re.I)
    if bm:
        baseline = fy_from(bm.group(3))
    fm = re.search(r"from\s+[\d.,]+\s*\S*\s+in\s+(FY\s?\d{4}(?:\s?[-\u2013]\s?\d{2,4})?)", text, re.I)
    if fm and not baseline:
        baseline = fy_from(fm.group(1))
    m = re.search(r"between\s+(FY\s?\d{4})\s+and\s+(FY\s?\d{4})", text, re.I)
    if m:
        return fy_from(m.group(2)), fy_from(m.group(1))
    others = [fy for _, fy in fys if fy != baseline]
    period = others[-1] if others else (None if baseline else (fys[-1][1] if fys else None))
    return period, baseline


def numbers(text: str) -> list[ParsedNumber]:
    out: list[ParsedNumber] = []
    clean = re.sub(r"\bFY\s?\d{2,4}(?:\s?[-–]\s?\d{2,4})?|\b(19|20)\d{2}[-–]\d{2}\b", " ", text, flags=re.I)
    clean = re.sub(r"\b(scope|tier|phase|level|category|section|class)[\s-]?\d+\b", " ", clean, flags=re.I)
    clean = re.sub(r"\b(figure|fig\.|table|chart|exhibit|note)\s*\d+(\.\d+)*", " ", clean, flags=re.I)
    for m in _NUM.finditer(clean):
        num = float(m.group("num").replace(",", ""))
        unit = (m.group("unit") or "").lower() or None
        mult = m.group("mult")
        if unit is None and mult is None and 1990 <= num <= 2100 and "." not in m.group("num"):
            continue  # a year, not a quantity
        if mult:
            num *= _MULT[mult.lower()]
        if unit in ("per cent", "percent"):
            unit = "%"
        out.append(ParsedNumber(value=num, unit=unit, raw=m.group("raw").strip()))
    for w, v in _WORD_NUM.items():
        if re.search(rf"\b{w}\b", text, re.I) and not out:
            out.append(ParsedNumber(value=float(v), unit="x" if v in (2, 3) else None, raw=w))
    return out


def facility_hint(text: str) -> str | None:
    m = re.search(r"\b((?:[A-Z][a-z]+\s){0,3}(?:[A-Z][a-z]+))\s+(?i:iron ore |limestone |coal |solar |wind |captive |"
                  r"processing |integrated |cement |steel |spinning |grinding |pellet |power |mining |bauxite |copper |"
                  r"zinc |gas |thermal |hydro )*"
                  r"(?i:(mine|mines|plant|plants|unit|park|farm|works|mill|operations|campus|refinery|smelter))\b", text)
    if not m:
        return None
    words = [w for w in m.group(1).split() if w.lower() not in {"our", "all", "the", "every", "each", "we", "at", "in"}]
    return " ".join(words) or None


def parse(text: str) -> Parsed:
    period, baseline = periods(text)
    return Parsed(numbers=numbers(text), period=period, baseline_period=baseline, facility_hint=facility_hint(text))
