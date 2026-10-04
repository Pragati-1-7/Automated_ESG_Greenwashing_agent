"""Spec access helpers: company records, derived series, number formatting, palettes."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data_gen.spec import DEMO_COMPANIES, FISCAL_YEARS  # noqa: E402

KEYS = {"vajra": "CMP-0001", "sahyadri": "CMP-0002", "kaveri": "CMP-0003", "aurelia": None}
YLAB = [f"FY{y[4:]}" for y in FISCAL_YEARS]  # FY20..FY25

SECONDARY = {"vajra": "#D99A00", "sahyadri": "#3F7D6B", "kaveri": "#C77D2E", "aurelia": "#1F4E79"}


def company(key: str) -> dict:
    cid = KEYS[key]
    for c in DEMO_COMPANIES:
        if c["company_id"] == cid and (cid is not None or c["in_db"] is False):
            return c
    raise KeyError(key)


def claim_text(co: dict, cid: str) -> str:
    for c in co["claims"]:
        if c["id"] == cid:
            return c["text"]
    raise KeyError(cid)


def intensity(co: dict) -> list[float]:
    t = co["true"]
    return [(a + b) / r for a, b, r in zip(t["scope1_tco2e"], t["scope2_tco2e"], t["revenue_cr"])]


def recovery_pct(co: dict) -> list[float]:
    t = co["true"]
    return [100 * r / g for r, g in zip(t["waste_recovered_t"], t["waste_generated_t"])]


def mix(hex_a: str, hex_b: str, w: float) -> str:
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * (1 - w) + y * w):02x}" for x, y in zip(a, b))


def palette(key: str, brand: str) -> dict:
    return {
        "brand": brand,
        "dark": mix(brand, "#000000", 0.35),
        "mid": mix(brand, "#ffffff", 0.35),
        "tint": mix(brand, "#ffffff", 0.90),
        "tint2": mix(brand, "#ffffff", 0.75),
        "sec": SECONDARY[key],
        "ink": "#1f2328",
        "grey": "#7d838c",
        "rule": "#d5d9df",
    }


def inr(n: float) -> str:
    """Indian digit grouping."""
    s = f"{int(round(n))}"
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])
