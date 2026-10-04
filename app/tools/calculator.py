"""Calculator tool. Agents never do arithmetic in a language model: every
number they compare comes from one of these pure functions, and each returns
a Computation record that is shown in the audit trail."""

from __future__ import annotations

from app.core.models import Computation


def _fmt(x: float) -> str:
    return f"{x:,.4g}" if abs(x) < 1000 else f"{x:,.0f}"


def pct_change(old: float, new: float, label: str = "value") -> Computation:
    if old == 0:
        raise ZeroDivisionError("baseline is zero")
    r = (new - old) / old * 100
    return Computation(op="pct_change", expression=f"({_fmt(new)} - {_fmt(old)}) / {_fmt(old)} x 100 = {r:+.1f}%",
                       inputs={f"{label}_baseline": old, f"{label}_current": new}, result=round(r, 2))


def share_pct(part: float, total: float, label: str = "share") -> Computation:
    if total == 0:
        raise ZeroDivisionError("total is zero")
    r = part / total * 100
    return Computation(op="share_pct", expression=f"{_fmt(part)} / {_fmt(total)} x 100 = {r:.1f}%",
                       inputs={f"{label}_part": part, f"{label}_total": total}, result=round(r, 2))


def multiple(old: float, new: float) -> Computation:
    if old == 0:
        raise ZeroDivisionError("baseline is zero")
    r = new / old
    return Computation(op="multiple", expression=f"{_fmt(new)} / {_fmt(old)} = {r:.2f}x",
                       inputs={"baseline": old, "current": new}, result=round(r, 3))


def relative_gap(claimed: float, actual: float) -> Computation:
    """How far the claimed figure is from the filed one, relative to the filed one."""
    base = abs(actual) if actual else 1.0
    r = (claimed - actual) / base * 100
    return Computation(op="relative_gap",
                       expression=f"(claimed {_fmt(claimed)} - filed {_fmt(actual)}) / {_fmt(base)} x 100 = {r:+.1f}%",
                       inputs={"claimed": claimed, "filed": actual}, result=round(r, 2))


def total(values: list[float], label: str = "total") -> Computation:
    r = float(sum(values))
    return Computation(op="sum", expression=f"sum of {len(values)} records = {_fmt(r)}",
                       inputs={f"{label}_n": float(len(values))}, result=round(r, 3))
