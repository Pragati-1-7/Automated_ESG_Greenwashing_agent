"""Small shared helpers for the world generator (geo, dates, money formatting)."""

from __future__ import annotations

import math
from datetime import date, timedelta

from . import spec

R_EARTH_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R_EARTH_KM * math.asin(math.sqrt(a))


def offset_point(lat: float, lon: float, dist_km: float, bearing_deg: float) -> tuple[float, float]:
    """Point at distance/bearing from (lat, lon) (spherical earth)."""
    d = dist_km / R_EARTH_KM
    b = math.radians(bearing_deg)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), math.degrees(l2)


def fy_range(fy: str) -> tuple[date, date]:
    a, b = spec.FY_DATE_RANGE[fy]
    return date.fromisoformat(a), date.fromisoformat(b)


def fy_of(iso: str) -> str | None:
    d = date.fromisoformat(iso)
    y = d.year + 1 if d.month >= 4 else d.year
    fy = f"FY{y}"
    return fy if fy in spec.FISCAL_YEARS else None


def rand_date(rng, start: date, end: date) -> date:
    span = (end - start).days
    return start + timedelta(days=rng.randint(0, max(span, 0)))


def fy_long(fy: str) -> str:
    y = int(fy[2:])
    return f"FY{y - 1}-{str(y)[2:]}"


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def fmt_month(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.year}"


def inr(amount: float) -> str:
    """Indian-press style money: 'Rs 4.2 crore', 'Rs 85 lakh'."""
    if amount >= 1e7:
        v = amount / 1e7
        s = f"{v:.2f}".rstrip("0").rstrip(".") if v < 100 else f"{v:,.0f}"
        return f"Rs {s} crore"
    v = amount / 1e5
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return f"Rs {s} lakh"


def num(x: float, dp: int = 0) -> str:
    return f"{x:,.{dp}f}"


def mt(tonnes: float) -> str:
    """Tonnes -> '10.86 Mt' or '71,760 t' style."""
    if tonnes >= 1e6:
        return f"{tonnes / 1e6:.2f} million tonnes"
    return f"{tonnes:,.0f} tonnes"


def add_days(iso: str, n: int) -> str:
    return (date.fromisoformat(iso) + timedelta(days=n)).isoformat()


def wc(text: str) -> int:
    return len(text.split())
