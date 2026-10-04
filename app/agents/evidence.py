"""
app/agents/evidence.py

Evidence builders, one per external source. Each builder:
  1. calls the source tool(s) with parameters taken from the structured
     sub-claim (company, metric, period, facility),
  2. turns the payload into citeable Evidence items (snippet + endpoint),
  3. runs the calculator tool for every comparison the judge will need.

Builders never decide whether a claim is true. They only fetch, format and
compute; the Jev judge decides.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.models import Computation, Evidence, SubClaim, ToolCall
from app.tools import calculator as calc
from app.tools import sources
from data_gen.spec import FISCAL_YEARS, METRICS

BRSR_NUMERIC = {"scope1_tco2e", "scope2_tco2e", "ghg_intensity", "energy_gj", "re_pct", "water_withdrawal_kl",
                "water_discharge_kl", "waste_generated_t", "waste_recovered_t", "ltifr", "fatalities",
                "women_wage_pct", "msme_sourcing_pct"}
TIER_NAME = {1: "Tier 1 regulatory filing", 2: "Tier 2 regulator record", 3: "Tier 3 third-party dataset",
             4: "Tier 4 company press release", 5: "Tier 5 news report"}


@dataclass
class Ctx:
    company: dict | None
    facilities: list[dict]
    doc_fy: str
    claim_id: str
    claim_text: str
    llm: object


@dataclass
class Gathered:
    tool_calls: list[ToolCall] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    computations: list[Computation] = field(default_factory=list)


def fy_window(fy: str) -> tuple[str, str]:
    y = int(fy[2:])
    return f"{y - 1}-04-01", f"{y}-03-31"


def _fmt(v) -> str:
    if isinstance(v, (int, float)):
        return f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 100 else f"{v:,.0f}"
    return str(v)


def _period(sc: SubClaim, ctx: Ctx) -> str:
    return sc.period or ctx.doc_fy


def _pct_numbers(sc: SubClaim) -> list[float]:
    return [n for n in (sc.claimed_value,) if n is not None]


def _ev_id(ctx: Ctx, sc: SubClaim, n: int) -> str:
    return f"{sc.sub_id}-E{n}"


# --------------------------------------------------------------------------- BRSR
async def brsr(sc: SubClaim, ctx: Ctx, nums: list[tuple[float, str | None]]) -> Gathered:
    g = Gathered()
    if not ctx.company:
        return g
    tc, data = await sources.brsr(ctx.company["company_id"], claim_id=ctx.claim_id)
    g.tool_calls.append(tc)
    rows = {r["fy"]: r for r in data.get("rows", [])}
    if not rows:
        return g
    period = _period(sc, ctx)
    metric = sc.metric
    cur = rows.get(period)
    base = rows.get(sc.baseline_period) if sc.baseline_period else None
    lines = []
    if metric in BRSR_NUMERIC:
        unit = METRICS[metric]["unit"]
        series = "; ".join(f"{fy} {_fmt(rows[fy][metric])}" for fy in FISCAL_YEARS if fy in rows)
        lines.append(f"{METRICS[metric]['label']} ({unit}) as filed: {series}.")
        lines.append("Turnover (Rs crore) as filed: " + "; ".join(f"{fy} {_fmt(rows[fy]['revenue_cr'])}"
                                                                 for fy in FISCAL_YEARS if fy in rows) + ".")
        if metric == "waste_recovered_t" and cur:
            lines.append(f"Waste generated {period}: {_fmt(cur['waste_generated_t'])} t.")
        if metric == "ghg_intensity" and cur:
            lines.append(f"Scope 1 {period}: {_fmt(cur['scope1_tco2e'])} tCO2e; Scope 2 {_fmt(cur['scope2_tco2e'])} "
                         f"tCO2e; turnover Rs {_fmt(cur['revenue_cr'])} crore.")
        _computations(g, sc, metric, cur, base, nums, period)
    elif metric == "assurance_type" and cur:
        lines.append(f"Assurance on BRSR Core {period}: {cur['assurance_type']} assurance"
                     + (f" by {cur['assurance_provider']}" if cur["assurance_provider"] else "") + ".")
        lines.append("Assurance history: " + "; ".join(f"{fy} {rows[fy]['assurance_type']}" for fy in FISCAL_YEARS if fy in rows) + ".")
    else:
        return g
    filed = cur["filed_on"] if cur else "n/a"
    g.evidence.append(Evidence(
        evidence_id=_ev_id(ctx, sc, 1), source="brsr_filings", tier=1,
        title=f"SEBI BRSR Core filing, {ctx.company['name']} ({period}, filed {filed})",
        snippet=" ".join(lines), endpoint=data.get("endpoint", "/sebi/brsr"),
        data={"metric": metric, "period": period, "current": cur.get(metric) if cur and metric in cur else None,
              "baseline": base.get(metric) if base and metric in base else None}))
    return g


_UNIT_FACTORS = {
    "tCO2e": {"mtco2e": 1e6, "ktco2e": 1e3, "mt": 1e6, "kt": 1e3, "t": 1.0, "tonnes": 1.0, "tonne": 1.0, "tco2e": 1.0},
    "kL": {"ml": 1e3, "megalitres": 1e3, "megalitre": 1e3, "litres": 1e-3, "litre": 1e-3, "kl": 1.0},
    "GJ": {"tj": 1e3, "pj": 1e6, "mwh": 3.6, "gwh": 3600.0, "kwh": 0.0036, "gj": 1.0},
    "t": {"mt": 1e6, "kt": 1e3, "t": 1.0, "tonnes": 1.0, "tonne": 1.0},
}


def _to_metric_unit(metric: str, unit: str | None) -> float:
    """Factor that converts a claimed unit into the unit the filing uses (1.0 if unknown/same)."""
    if not unit:
        return 1.0
    return _UNIT_FACTORS.get(METRICS[metric]["unit"], {}).get(unit.lower(), 1.0)


def _computations(g: Gathered, sc: SubClaim, metric: str, cur: dict | None, base: dict | None,
                  nums: list[tuple[float, str | None]], period: str) -> None:
    if not cur:
        return
    actual = cur[metric]
    pcts = [v for v, u in nums if u == "%"]
    mults = [v for v, u in nums if u in ("x", "times")]
    plain = [v for v, u in nums if u not in ("%", "x", "times", "km")]
    try:
        if base is not None and metric in base:
            ch = calc.pct_change(base[metric], actual, metric)
            g.computations.append(ch)
            if mults:
                g.computations.append(calc.multiple(base[metric], actual))
            if pcts and sc.check_type == "pct_change":
                claimed = -abs(pcts[0]) if re.search(r"reduc|cut|fell|lower|declin|decreas|down|improv", sc.text, re.I) \
                    and metric not in ("re_pct", "women_wage_pct", "msme_sourcing_pct", "waste_recovered_t") else pcts[0]
                g.computations.append(calc.relative_gap(claimed, ch.result))
        if metric == "waste_recovered_t" and pcts:
            sh = calc.share_pct(cur["waste_recovered_t"], cur["waste_generated_t"], "waste_recovered")
            g.computations.append(sh)
            g.computations.append(calc.relative_gap(pcts[-1], sh.result))
        elif metric in ("re_pct", "women_wage_pct", "msme_sourcing_pct") and pcts and sc.check_type != "pct_change":
            g.computations.append(calc.relative_gap(pcts[-1], actual))
        elif plain and sc.check_type in ("point_value", "pct_change", "share"):
            value, unit = [(v, u) for v, u in nums if u not in ("%", "x", "times", "km")][-1]
            factor = _to_metric_unit(metric, unit)
            if factor != 1.0:
                g.computations.append(Computation(
                    op="unit_conversion", expression=f"{_fmt(value)} {unit} x {factor:g} = {_fmt(value * factor)} "
                    f"{METRICS[metric]['unit']}", inputs={"value": value, "factor": factor}, result=value * factor))
            g.computations.append(calc.relative_gap(value * factor, actual))
        if metric == "ghg_intensity" and plain:
            pass
    except ZeroDivisionError:
        pass


# --------------------------------------------------------------------------- facility GHG
async def facility_ghg(sc: SubClaim, ctx: Ctx, nums) -> Gathered:
    g = Gathered()
    if not ctx.company:
        return g
    period = _period(sc, ctx)
    tc, data = await sources.facility_ghg(ctx.company["company_id"], claim_id=ctx.claim_id)
    g.tool_calls.append(tc)
    by_fy: dict[str, float] = {}
    for r in data.get("rows", []):
        by_fy[r["fy"]] = by_fy.get(r["fy"], 0) + r["total_tco2e"]
    if not by_fy:
        return g
    series = "; ".join(f"{fy} {_fmt(v)}" for fy, v in sorted(by_fy.items()))
    g.evidence.append(Evidence(
        evidence_id=_ev_id(ctx, sc, 2), source="facility_ghg", tier=1,
        title=f"Facility GHG registry, sum over {len({r['facility_id'] for r in data['rows']})} facilities",
        snippet=f"Sum of facility-level direct (Scope 1) emissions, tCO2e: {series}.",
        endpoint=data.get("endpoint", "/ghg/facility"), data={"by_fy": by_fy, "period": period}))
    if sc.baseline_period in by_fy and period in by_fy:
        g.computations.append(calc.pct_change(by_fy[sc.baseline_period], by_fy[period], "facility_scope1"))
    return g


# --------------------------------------------------------------------------- OCEMS
async def ocems(sc: SubClaim, ctx: Ctx, nums) -> Gathered:
    g = Gathered()
    if not ctx.company:
        return g
    period = _period(sc, ctx)
    tc, data = await sources.ocems(ctx.company["company_id"], fy=period, claim_id=ctx.claim_id)
    g.tool_calls.append(tc)
    rows = data.get("rows", [])
    lo, hi = fy_window(period)
    if rows:
        by_param: dict[str, int] = {}
        by_fac: dict[str, int] = {}
        for r in rows:
            by_param[r["parameter"]] = by_param.get(r["parameter"], 0) + 1
            by_fac[r["facility_name"]] = by_fac.get(r["facility_name"], 0) + 1
        worst = max(rows, key=lambda r: r["reading"] / r["limit_value"])
        snippet = (f"{len(rows)} emission-limit exceedance events recorded by online continuous monitoring between "
                   f"{lo} and {hi}: " + ", ".join(f"{k} {v}" for k, v in by_param.items()) + ". Facilities: "
                   + ", ".join(f"{k} ({v})" for k, v in by_fac.items()) + f". Worst: {worst['parameter']} "
                   f"{worst['reading']} {worst['unit']} against a limit of {worst['limit_value']} on {worst['date']}.")
    else:
        snippet = f"No emission-limit exceedances recorded for any {ctx.company['name']} facility between {lo} and {hi}."
    g.computations.append(calc.total([1.0] * len(rows), "exceedances"))
    g.evidence.append(Evidence(evidence_id=_ev_id(ctx, sc, 3), source="ocems_exceedances", tier=2,
                               title=f"CPCB OCEMS exceedance log, {period}", snippet=snippet,
                               endpoint=data.get("endpoint", "/cpcb/ocems/exceedances"),
                               data={"count": len(rows), "period": period}))
    return g


# --------------------------------------------------------------------------- regulatory
async def regulatory(sc: SubClaim, ctx: Ctx, nums) -> Gathered:
    g = Gathered()
    if not ctx.company:
        return g
    period = _period(sc, ctx)
    lo, hi = fy_window(period)
    tc, data = await sources.regulatory(ctx.company["company_id"], claim_id=ctx.claim_id)
    g.tool_calls.append(tc)
    rows = data.get("rows", [])
    inside = [r for r in rows if lo <= r["date"] <= hi]
    outside = [r for r in rows if not (lo <= r["date"] <= hi)]
    n = 10
    for r in inside:
        n += 1
        pen = f" Penalty/compensation: Rs {r['penalty_inr'] / 1e7:,.2f} crore." if r["penalty_inr"] else ""
        g.evidence.append(Evidence(
            evidence_id=_ev_id(ctx, sc, n), source="regulatory_actions", tier=2,
            title=f"{r['authority']} {r['order_type'].replace('_', ' ')} ({r['date']}, {r['case_no']})",
            snippet=f"Dated {r['date']}, inside the claim period {period} ({lo} to {hi}). {r['summary']}{pen} "
                    f"Status: {r['status']}.",
            endpoint=data.get("endpoint", "/regulatory/actions"), data=r))
    if not inside:
        note = ""
        if outside:
            o = sorted(outside, key=lambda r: r["date"])[-1]
            note = (f" The only recorded actions fall OUTSIDE this period: {len(outside)} action(s), latest "
                    f"{o['authority']} {o['order_type'].replace('_', ' ')} dated {o['date']}.")
        g.evidence.append(Evidence(
            evidence_id=_ev_id(ctx, sc, n + 1), source="regulatory_actions", tier=2,
            title=f"Regulator and tribunal records search, {period}",
            snippet=f"No regulatory notices, penalties or closure directions against {ctx.company['name']} dated "
                    f"between {lo} and {hi}.{note}",
            endpoint=data.get("endpoint", "/regulatory/actions"),
            data={"count_in_period": 0, "count_outside_period": len(outside)}))
    g.computations.append(calc.total([r["penalty_inr"] for r in inside], "penalties_inr"))
    return g


# --------------------------------------------------------------------------- land alerts
def _match_facility(hint: str | None, facilities: list[dict]) -> dict | None:
    if not hint:
        return None
    h = hint.lower()
    for f in facilities:
        if h in f["name"].lower() or h in f["district"].lower():
            return f
    return None


async def land_alerts(sc: SubClaim, ctx: Ctx, nums) -> Gathered:
    g = Gathered()
    if not ctx.company:
        return g
    period = _period(sc, ctx)
    radius = next((v for v, u in nums if u == "km"), 5.0)
    fac = _match_facility(sc_facility(sc), ctx.facilities)
    if fac:
        tc, data = await sources.alerts_near(fac["lat"], fac["lon"], fy=period, radius_km=radius, claim_id=ctx.claim_id)
        where = f"{radius:g} km of {fac['name']} ({fac['lat']:.3f}, {fac['lon']:.3f})"
    else:
        tc, data = await sources.alerts_company(ctx.company["company_id"], fy=period, radius_km=radius,
                                                claim_id=ctx.claim_id)
        where = f"{radius:g} km of any of the company's {len(ctx.facilities)} facilities"
    g.tool_calls.append(tc)
    rows = data.get("rows", [])
    lo, hi = fy_window(period)
    area = data.get("total_area_ha", 0.0)
    if rows:
        conf = {}
        for r in rows:
            conf[r["confidence"]] = conf.get(r["confidence"], 0) + 1
        snippet = (f"{len(rows)} satellite forest-loss alerts within {where} between {lo} and {hi}, totalling "
                   f"{area:,.1f} hectares (confidence: " + ", ".join(f"{k} {v}" for k, v in conf.items()) + ").")
    else:
        snippet = f"No satellite forest-loss alerts within {where} between {lo} and {hi}."
    g.computations.append(calc.total([r["area_ha"] for r in rows], "forest_loss_ha"))
    g.evidence.append(Evidence(evidence_id=_ev_id(ctx, sc, 30), source="land_alerts", tier=3,
                               title=f"GFW-style integrated forest-loss alerts, {period}", snippet=snippet,
                               endpoint=data.get("endpoint", "/gfw/alerts"),
                               data={"count": len(rows), "area_ha": area, "radius_km": radius,
                                     "facility": fac["name"] if fac else None}))
    return g


def sc_facility(sc: SubClaim) -> str | None:
    from app.tools.claim_parser import facility_hint
    return facility_hint(sc.text)


# --------------------------------------------------------------------------- REC registry
async def rec_registry(sc: SubClaim, ctx: Ctx, nums) -> Gathered:
    g = Gathered()
    if not ctx.company:
        return g
    period = _period(sc, ctx)
    m = re.search(r"\b(20\d{2})\b(?![-–])", sc.text)
    vintage = int(m.group(1)) if m else int(period[2:]) - 1
    tc, data = await sources.rec_registry(ctx.company["company_id"], vintage=vintage, claim_id=ctx.claim_id)
    g.tool_calls.append(tc)
    totals = data.get("totals_mwh", {})
    if not data.get("rows"):
        g.evidence.append(Evidence(evidence_id=_ev_id(ctx, sc, 40), source="re_certificates", tier=3,
                                   title=f"REC registry, vintage {vintage}",
                                   snippet=f"No renewable energy certificates of vintage {vintage} registered to "
                                           f"{ctx.company['name']}.", endpoint=data.get("endpoint", "/registry/rec"),
                                   data={"vintage": vintage}))
        return g
    tot = sum(totals.values())
    retired = totals.get("retired", 0.0)
    g.computations.append(calc.share_pct(retired, tot, "certificates_retired"))
    g.evidence.append(Evidence(
        evidence_id=_ev_id(ctx, sc, 40), source="re_certificates", tier=3,
        title=f"Renewable energy certificate registry, vintage {vintage}",
        snippet=f"Certificates of vintage {vintage} held by {ctx.company['name']}: "
                + ", ".join(f"{k} {v:,.0f} MWh" for k, v in totals.items())
                + f". Only retired certificates can be counted towards renewable electricity claims; "
                  f"{retired / tot * 100:.1f}% of the volume is retired.",
        endpoint=data.get("endpoint", "/registry/rec"), data={"vintage": vintage, "totals_mwh": totals}))
    return g


# --------------------------------------------------------------------------- assurance
async def assurance(sc: SubClaim, ctx: Ctx, nums) -> Gathered:
    g = Gathered()
    if not ctx.company:
        return g
    period = _period(sc, ctx)
    tc, data = await sources.assurance(ctx.company["company_id"], claim_id=ctx.claim_id)
    g.tool_calls.append(tc)
    rows = data.get("rows", [])
    hist = "; ".join(f"{r['fy']} {r['assurance_type']} ({r['auditor']})" for r in rows) or "none on record"
    cur = next((r for r in rows if r["fy"] == period), None)
    text = (f"{period}: {cur['assurance_type']} assurance by {cur['auditor']}, opinion {cur['opinion']}. "
            f"Excerpt: {cur['text'][:260]}" if cur else f"No assurance statement on record for {period}.")
    g.evidence.append(Evidence(evidence_id=_ev_id(ctx, sc, 50), source="audited_reports", tier=3,
                               title=f"Independent assurance statements on BRSR Core", snippet=f"{text} History: {hist}.",
                               endpoint=data.get("endpoint", "/assurance/statements"),
                               data={"period": period, "assurance_type": cur["assurance_type"] if cur else None}))
    return g


# --------------------------------------------------------------------------- news
def _best_sentences(body: str, query: str, k: int = 2) -> str:
    q = set(re.findall(r"[a-z0-9]{3,}", query.lower()))
    sents = re.split(r"(?<=[.!?])\s+", body)
    ranked = sorted(sents, key=lambda s: len(q & set(re.findall(r"[a-z0-9]{3,}", s.lower()))), reverse=True)
    keep = set(ranked[:k])
    return " ".join(s for s in sents if s in keep)


async def news(sc: SubClaim, ctx: Ctx, nums, broaden: bool = False) -> Gathered:
    g = Gathered()
    company_name = ctx.company["name"] if ctx.company else None
    metric_label = METRICS[sc.metric]["label"] if sc.metric in METRICS else None
    q = ctx.llm.search_query(ctx.company["short_name"] if ctx.company else None, sc.text, metric_label)
    period = _period(sc, ctx)
    lo, hi = fy_window(period)
    date_to = f"{int(hi[:4]) + (1 if broaden else 0)}-12-31"
    tc, data = await sources.news(q, company_id=ctx.company["company_id"] if ctx.company else None, k=3,
                                  date_from=None if broaden else f"{int(lo[:4])}-01-01", date_to=date_to,
                                  claim_id=ctx.claim_id)
    g.tool_calls.append(tc)
    for i, r in enumerate(data.get("rows", [])):
        if r["score"] < 0.25:
            continue
        g.evidence.append(Evidence(
            evidence_id=_ev_id(ctx, sc, 60 + i + (10 if broaden else 0)), source="news_articles",
            tier=int(r["tier"]), title=f"{r['outlet']}, {r['date']}: {r['title']}",
            snippet=_best_sentences(r["text"], q + " " + sc.text), endpoint=data.get("endpoint", "/news/search"),
            data={"article_id": r["id"], "outlet": r["outlet"], "date": r["date"], "retrieval_score": r["score"]}))
    return g


BUILDERS = {
    "brsr": brsr, "facility_ghg": facility_ghg, "ocems": ocems, "regulatory": regulatory,
    "land_alerts": land_alerts, "rec_registry": rec_registry, "assurance": assurance, "news": news,
}
