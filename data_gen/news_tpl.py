"""
data_gen/news_tpl.py

The article template library (34 distinct templates). Each template is a function
    t_xxx(ctx, rng, **params) -> dict(company_id, outlet, tier, date, headline, paras, topics[, fill])
whose facts come from real rows of the generated tables, so that articles stay
consistent with the database. ALL FICTIONAL.
"""

from __future__ import annotations

from datetime import date, timedelta

from .news_base import (SECTOR_PHRASE, poss, BOARD_NAME, SPOKES, ZONE_CITY, ZONE_NAME, Ctx, dateline, issue_of, join_and, short_issue)
from .world_refs import FOREST_BOXES, OUTLETS, STATES
from .world_utils import add_days, fmt_date, fmt_month, fy_long, fy_range, inr, haversine_km

CAP = date(2026, 9, 30)

REGIONAL_OUTLETS = {
    "Odisha": ["The Eastern Ledger", "The Mahanadi Post", "Odisha Field Report"],
    "Jharkhand": ["The Eastern Ledger", "The Gangetic Business Chronicle"], "West Bengal": ["The Eastern Ledger", "The Gangetic Business Chronicle"],
    "Tamil Nadu": ["Kongu Business Review", "Southern Industrial Gazette"], "Karnataka": ["Southern Industrial Gazette", "Capital Pulse India"],
    "Maharashtra": ["Western Markets Daily", "Konkan Trade Journal", "Deccan Industry Times"], "Gujarat": ["Western Markets Daily", "Bharat Commerce Weekly"],
    "Telangana": ["Telangana Economic Bulletin", "Deccan Industry Times"], "Andhra Pradesh": ["Telangana Economic Bulletin", "Deccan Industry Times"],
    "Delhi": ["Rajdhani Financial Standard", "Northern Industry Observer"], "Haryana": ["Rajdhani Financial Standard", "Northern Industry Observer"],
    "Uttar Pradesh": ["Northern Industry Observer", "Rajdhani Financial Standard"], "Punjab": ["Northern Industry Observer"],
    "Chhattisgarh": ["The Gangetic Business Chronicle", "Bharat Commerce Weekly"], "Madhya Pradesh": ["Bharat Commerce Weekly", "Capital Pulse India"],
    "Rajasthan": ["Rajdhani Financial Standard", "Bharat Commerce Weekly"],
}
NATIONAL = ["Business Mint India", "Bharat Commerce Weekly", "Capital Pulse India", "Green Ledger India", "ESG Watch India"]


def pick_outlet(rng, state: str | None = None, national_bias: float = 0.4) -> str:
    reg = REGIONAL_OUTLETS.get(state or "", [])
    if reg and rng.random() > national_bias:
        return rng.choice(reg)
    return rng.choice(NATIONAL + OUTLETS[:6] if not reg else NATIONAL)


def cap(f) -> str:
    v = f["capacity_value"]
    return f"{v:,.0f} {f['capacity_unit']}" if float(v).is_integer() else f"{v} {f['capacity_unit']}"


def pub(rng, iso: str, lo: int, hi: int) -> str:
    d = date.fromisoformat(add_days(iso, rng.randint(lo, hi)))
    return min(d, CAP).isoformat()


def spokes(rng) -> str:
    return rng.choice(SPOKES)


def pct_change(a, b):
    return (b - a) / a * 100.0


def art(c, d, headline, paras, topics, tier=5, outlet=None, fill=None, rng=None):
    return dict(company_id=c["company_id"] if c else None, outlet=outlet, tier=tier, date=d, headline=headline,
                paras=paras, topics=topics, fill=fill)


def company_outlet(c):
    return f"{c['name']} (press release)"


def status_sentence(r, short, pub_iso):
    s = r["status"]
    if s.startswith("revoked_") or s.startswith("restored_"):
        d = s.split("_", 1)[1]
        verb = "revoked the direction" if s.startswith("revoked") else "restored the consent"
        return f"Update ({fmt_date(d)}): the authority {verb} after compliance was verified."
    return {
        "paid": f"Company filings indicate that {short} has since paid the amount.",
        "paid_under_protest": f"{short} has paid the amount under protest while it considers its legal options.",
        "appealed": f"{short} has challenged the order in appeal, and the matter is pending.",
        "pending_payment": f"Payment of the amount was still pending when the order was published.",
        "stayed_by_court": f"A court has since stayed the operation of the order, pending a hearing.",
        "reply_filed": f"{short} has filed its reply to the authority.",
        "closed": "The matter has since been closed after compliance reports were accepted.",
        "complied": "The matter has since been closed after the company reported compliance.",
        "pending": "The matter is pending before the authority.",
        "settled": f"{short} has settled the matter with the regulator.",
        "appealed_SAT": f"{short} has appealed to the Securities Appellate Tribunal.",
        "in_force": "The order remains in force at the time of writing.",
    }.get(s, "The matter is pending.")


# =====================================================================
# Regulatory coverage (6 templates)
# =====================================================================

def t_ngt(ctx: Ctx, rng, row):
    c, fac = ctx.co[row["company_id"]], ctx.fac[row["facility_id"]]
    zone = STATES[fac["state"]]["zone"]
    issue, amt = issue_of(row["summary"]), inr(row["penalty_inr"])
    kind = "environmental compensation" if row["order_type"] == "environmental_compensation" else "a penalty"
    d = pub(rng, row["date"], 1, 9)
    head = rng.choice([f"NGT orders {c['short_name']} to pay {amt} over {short_issue(issue)}",
                       f"Green tribunal imposes {amt} on {c['short_name']} for {short_issue(issue)}",
                       f"{c['short_name']} faces {amt} NGT bill after {short_issue(issue)} complaint"])
    n_ev = len([e for e in ctx.oce_by_fac[fac["facility_id"]] if add_days(row["date"], -365) <= e["date"] <= row["date"]])
    paras = [
        f"{dateline(c, fac)}The National Green Tribunal's {ZONE_NAME[zone]} bench at {ZONE_CITY[zone]} has directed {c['name']} to pay {kind} of {amt} "
        f"for {issue} at its {fac['name']} in {fac['district']}, {fac['state']}, according to an order dated {fmt_date(row['date'])}. "
        f"The matter was registered as {row['case_no']}.",
        f"In its order, the bench applied the polluter pays principle and asked the {BOARD_NAME[STATES[fac['state']]['board']]} to monitor "
        f"compliance and report back to the tribunal. The tribunal said that the amount is meant to restore the environment and is not a substitute "
        f"for any prosecution that the board may initiate under the Water and Air Acts.",
        (f"Online monitoring data on the public portal show {n_ev} recorded exceedances at the facility in the twelve months before the order. " if n_ev
         else "The tribunal relied on a joint committee report that inspected the site and examined consent conditions. ") +
        status_sentence(row, c["short_name"], d),
        f"{spokes(rng).capitalize()} said that the company is studying the order and remains committed to compliance with all applicable norms. "
        f"The {fac['name']} has a capacity of {cap(fac)} and operates under consent number {fac['consent_no']}.",
    ]
    return art(c, d, head, paras, ["regulatory", "emissions" if "emission" in issue or "dust" in issue else "waste"],
               outlet=pick_outlet(rng, fac["state"]))


def t_notice(ctx: Ctx, rng, row):
    c, fac = ctx.co[row["company_id"]], ctx.fac[row["facility_id"]]
    board = row["authority"]
    bname = "Central Pollution Control Board" if board == "CPCB" else BOARD_NAME.get(board, board)
    issue = issue_of(row["summary"])
    kind = "show-cause notice" if row["order_type"] == "show_cause" else "warning"
    d = pub(rng, row["date"], 1, 12)
    head = rng.choice([f"{board} issues {kind} to {c['short_name']} over {short_issue(issue)}",
                       f"{c['short_name']} gets {kind} for {short_issue(issue)} at {fac['district']} unit",
                       f"Pollution board serves {kind} on {c['short_name']}, seeks reply"])
    n_ev = len([e for e in ctx.oce_by_fac[fac["facility_id"]] if add_days(row["date"], -365) <= e["date"] <= row["date"]])
    paras = [
        f"{dateline(c, fac)}The {bname} has issued a {kind} to {c['name']} over {issue} at its {fac['name']} in {fac['district']}, "
        f"{fac['state']}. The notice, dated {fmt_date(row['date'])} and filed under {row['case_no']}, follows an inspection of the site.",
        (f"The authority asked the company to explain within 15 days why further action, including closure directions or environmental "
         f"compensation, should not be taken. " if row["order_type"] == "show_cause" else
         "The authority directed the company to take corrective measures and submit an action plan, and warned that continued non-compliance could attract "
         "closure directions or environmental compensation. ") +
        (f"Data from the plant's online monitoring system show {n_ev} exceedances of prescribed limits in the preceding twelve months." if n_ev else
         "Officials said that the notice is based on the findings of the inspection team."),
        f"{spokes(rng).capitalize()} said that the company has received the notice and will respond within the stipulated time. "
        + status_sentence(row, c["short_name"], d),
        f"The {fac['name']} has a capacity of {cap(fac)}. Notices of this kind are the first formal step in the enforcement ladder of pollution boards, "
        f"and most are closed after a satisfactory reply and a compliance verification visit.",
    ]
    return art(c, d, head, paras, ["regulatory", "emissions" if "emission" in issue or "dust" in issue else "water"],
               outlet=pick_outlet(rng, fac["state"]))


def t_closure(ctx: Ctx, rng, row):
    c, fac = ctx.co[row["company_id"]], ctx.fac[row["facility_id"]]
    auth = row["authority"]
    bname = {"CPCB": "Central Pollution Control Board", "NGT": "National Green Tribunal"}.get(auth, BOARD_NAME.get(auth, auth))
    issue = issue_of(row["summary"])
    revoke = row["order_type"] == "consent_revoked"
    d = pub(rng, row["date"], 1, 6)
    head = rng.choice([f"{auth} {'revokes consent of' if revoke else 'orders closure of'} {poss(c['short_name'])} {fac['district']} unit",
                       f"{c['short_name']} told to {'stop operations' if not revoke else 'halt production'} at {fac['district']} over {short_issue(issue)}",
                       f"Closure order for {c['short_name']} {fac['district']} plant on {short_issue(issue)}"])
    paras = [
        f"{dateline(c, fac)}The {bname} has {'revoked the consent to operate of' if revoke else 'issued a closure direction for'} the {fac['name']} "
        f"in {fac['district']}, {fac['state']}, operated by {c['name']}, citing {issue}. The order is dated {fmt_date(row['date'])} ({row['case_no']}).",
        f"The direction asks the company to {'suspend activity under the revoked consent' if revoke else 'shut down the affected units'} and to submit a compliance plan; "
        f"power and water connections to the site can be disconnected if the order is not followed. Officials said the order was issued after repeated inspections.",
        status_sentence(row, c["short_name"], d) + f" {spokes(rng).capitalize()} said that the company is working with the authority on corrective measures.",
        f"The facility, with a capacity of {cap(fac)}, is one of {len(ctx.fac_by_c[c['company_id']])} operated by the company. Closure directions are used sparingly "
        f"by regulators and are typically withdrawn once the authority is satisfied that the violations have been remedied.",
    ]
    return art(c, d, head, paras, ["regulatory", "emissions" if "emission" in issue or "dust" in issue else "water"],
               outlet=pick_outlet(rng, fac["state"]))


def t_penalty_board(ctx: Ctx, rng, row):
    c, fac = ctx.co[row["company_id"]], ctx.fac[row["facility_id"]]
    auth = row["authority"]
    bname = "Central Pollution Control Board" if auth == "CPCB" else BOARD_NAME.get(auth, auth)
    issue, amt = issue_of(row["summary"]), inr(row["penalty_inr"])
    kind = "environmental compensation" if row["order_type"] == "environmental_compensation" else "a penalty"
    d = pub(rng, row["date"], 1, 10)
    head = rng.choice([f"{auth} levies {amt} on {c['short_name']} for {short_issue(issue)}",
                       f"{c['short_name']} hit with {amt} pollution penalty at {fac['district']}",
                       f"{amt} compensation for {c['short_name']} as {auth} acts on {short_issue(issue)}"])
    paras = [
        f"{dateline(c, fac)}The {bname} has directed {c['name']} to pay {kind} of {amt} for {issue} at its {fac['name']} in {fac['district']}, "
        f"{fac['state']}. The order is dated {fmt_date(row['date'])} and carries the reference {row['case_no']}.",
        f"An official familiar with the matter said that the amount was calculated on the basis of the unit's scale and the period of the violation, "
        f"in line with the compensation formula adopted by the regulator. The company has been given a fixed period to deposit the sum and to file a compliance report.",
        status_sentence(row, c["short_name"], d) + f" {spokes(rng).capitalize()} said that the company has taken corrective steps at the site.",
        f"Located in {fac['district']}, the {fac['name']} has a capacity of {cap(fac)}. The company's other facilities are in {join_and(ctx.states(c['company_id']))}.",
    ]
    return art(c, d, head, paras, ["regulatory", "water" if "effluent" in issue else "emissions"], outlet=pick_outlet(rng, fac["state"]))


def t_moefcc(ctx: Ctx, rng, row):
    c, fac = ctx.co[row["company_id"]], ctx.fac[row["facility_id"]]
    issue = issue_of(row["summary"])
    kind = row["order_type"].replace("_", " ")
    d = pub(rng, row["date"], 2, 14)
    head = rng.choice([f"Environment ministry issues {kind} to {c['short_name']} over {short_issue(issue)}",
                       f"MoEFCC action on {c['short_name']}: {kind} for {fac['district']} project"])
    pen = f" A penalty of {inr(row['penalty_inr'])} was levied." if row["penalty_inr"] else ""
    paras = [
        f"{dateline(c, fac)}The Ministry of Environment, Forest and Climate Change has issued a {kind} to {c['name']} over {issue} at its {fac['name']} "
        f"in {fac['district']}, {fac['state']}, according to a communication dated {fmt_date(row['date'])} ({row['case_no']}).{pen}",
        f"The ministry's regional office said that an inspection found non-compliance with conditions attached to the environmental or forest clearance. "
        f"The company has been asked to submit an action-taken report and to ensure that conditions on green belt, tree plantation and monitoring are met.",
        status_sentence(row, c["short_name"], d) + f" {spokes(rng).capitalize()} said that the company has initiated a review of all clearance conditions.",
        f"The {fac['name']} has a capacity of {cap(fac)}. Clearance conditions are enforced through periodic site visits by the ministry's regional offices, "
        f"and violations can lead to suspension of the clearance.",
    ]
    return art(c, d, head, paras, ["regulatory", "biodiversity"], outlet=pick_outlet(rng, fac["state"]))


def t_sebi(ctx: Ctx, rng, row):
    c = ctx.co[row["company_id"]]
    issue = issue_of(row["summary"])
    d = pub(rng, row["date"], 1, 10)
    pen = row["order_type"] == "penalty"
    head = (f"SEBI penalises {c['short_name']} {inr(row['penalty_inr'])} over {short_issue(issue)}" if pen
            else f"SEBI warns {c['short_name']} on {short_issue(issue)}")
    paras = [
        f"{dateline(c)}The Securities and Exchange Board of India has {'imposed a penalty of ' + inr(row['penalty_inr']) + ' on' if pen else 'issued an administrative warning to'} "
        f"{c['name']} for {issue}, according to an order dated {fmt_date(row['date'])} ({row['case_no']}).",
        "The regulator said that listed entities among the top by market capitalisation are required to file their business responsibility and sustainability "
        "disclosures with their annual reports and that these disclosures must be complete and timely. It noted that investors rely on these filings.",
        status_sentence(row, c["short_name"], d) + f" {spokes(rng).capitalize()} said that the company has strengthened its internal reporting calendar.",
        f"{c['short_name']}, which is listed as {c['listing']}, operates {len(ctx.fac_by_c[c['company_id']])} facilities across {join_and(ctx.states(c['company_id']))}. "
        f"Market observers said that disclosure-related actions are usually modest in size but are watched by ESG rating agencies.",
    ]
    return art(c, d, head, paras, ["regulatory", "governance"], outlet=pick_outlet(rng, c["hq_state"], 0.6))


# =====================================================================
# Evidence-driven coverage
# =====================================================================

def t_ocems(ctx: Ctx, rng, fac, fy):
    c = ctx.co[fac["company_id"]]
    a, b = fy_range(fy)
    ev = [e for e in ctx.oce_by_fac[fac["facility_id"]] if a.isoformat() <= e["date"] <= b.isoformat()]
    byp = {}
    for e in ev:
        byp.setdefault(e["parameter"], []).append(e)
    worst = max(ev, key=lambda e: e["reading"] / e["limit_value"])
    last = max(e["date"] for e in ev)
    d = pub(rng, last, 12, 45)
    head = rng.choice([f"{len(ev)} emission exceedances logged at {poss(c['short_name'])} {fac['district']} unit in {fy_long(fy)}",
                       f"Online data flag {len(ev)} limit breaches at {c['short_name']} {fac['district']} facility",
                       f"{poss(c['short_name'])} {fac['district']} plant breached monitoring limits {len(ev)} times in {fy_long(fy)}"])
    parts = join_and([f"{len(v)} for {k}" for k, v in sorted(byp.items())])
    paras = [
        f"{dateline(c, fac)}Online continuous monitoring data show that the {fac['name']} of {c['name']} recorded {len(ev)} exceedances of prescribed limits "
        f"during {fy_long(fy)}, an analysis of the monitoring portal shows. The events comprise {parts}.",
        f"The worst reading was {worst['reading']} {worst['unit']} for {worst['parameter']} on {fmt_date(worst['date'])}, against a limit of "
        f"{worst['limit_value']:g} {worst['unit']}. Individual events lasted between {min(e['duration_h'] for e in ev)} and {max(e['duration_h'] for e in ev)} hours, "
        f"and were reported to {join_and(sorted({e['reported_to'] for e in ev}))}.",
        f"{spokes(rng).capitalize()} said that exceedances are investigated as they occur and that the plant's pollution control equipment is maintained "
        f"under the conditions of its consent ({fac['consent_no']}). Environmentalists argued that sustained breaches should trigger faster regulatory action.",
        f"The facility has a capacity of {cap(fac)} and is located in {fac['district']}, {fac['state']}. Under national norms, plants in designated categories "
        f"must transmit emission and effluent data to the regulators continuously, and exceedances are visible on the public dashboard.",
    ]
    return art(c, d, head, paras, ["emissions" if byp.keys() & {"PM", "SO2", "NOx"} else "water", "regulatory"], outlet=pick_outlet(rng, fac["state"]))


def t_forest(ctx: Ctx, rng, fac, fy, alerts):
    c = ctx.co[fac["company_id"]]
    n, ha = len(alerts), sum(x["area_ha"] for x in alerts)
    last = max(x["alert_date"] for x in alerts)
    d = pub(rng, last, 20, 70)
    head = rng.choice([f"Satellite alerts show {ha:.0f} ha of forest loss near {poss(c['short_name'])} {fac['district']} operations",
                       f"Locals flag forest clearing near {c['short_name']} {fac['district']} lease",
                       f"{n} forest-loss alerts recorded near {c['short_name']} site in {fy_long(fy)}"])
    paras = [
        f"{dateline(c, fac)}Satellite-based forest-loss alerts recorded {n} separate events totalling {ha:.1f} hectares within 5 km of the {fac['name']} operated by "
        f"{c['name']} in {fac['district']}, {fac['state']}, during {fy_long(fy)}, according to an analysis of an open global forest-watch dataset.",
        f"A local forest-rights collective said that residents had seen fresh clearing and road building around the lease area and asked the forest department to "
        f"inspect the site. The alerts do not by themselves show who was responsible for the clearing, and some may relate to community activity or roads.",
        f"{spokes(rng).capitalize()} said that all operations at the {fac['name']} remain within the approved lease and clearance conditions, and that the company "
        f"would cooperate with any verification by the authorities. The district forest office said it would examine the alerts during its next site inspection.",
        f"The facility has a capacity of {cap(fac)}. Researchers note that alert data are most reliable for clearing larger than a fraction of a hectare, and that field "
        f"verification is needed before drawing conclusions about individual operators.",
    ]
    return art(c, d, head, paras, ["biodiversity", "regulatory"], outlet=pick_outlet(rng, fac["state"]))


def t_positive_re(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    cur = ctx.b(cid, fy)
    prev = ctx.b(cid, f"FY{int(fy[2:]) - 1}")
    d = pub(rng, cur["filed_on"], 5, 45)
    head = rng.choice([f"{c['short_name']} lifts renewable share to {cur['re_pct']}% of electricity",
                       f"{poss(c['short_name'])} green power share jumps {cur['re_pct'] - prev['re_pct']:.1f} points to {cur['re_pct']}%",
                       f"Renewables now meet {cur['re_pct']}% of {poss(c['short_name'])} power needs"])
    paras = [
        f"{dateline(c)}{c['name']} reported that renewable sources supplied {cur['re_pct']}% of the electricity it consumed in {fy_long(fy)}, up from "
        f"{prev['re_pct']}% a year earlier, according to its BRSR filed on {fmt_date(cur['filed_on'])}.",
        f"The company said that the increase came from a mix of captive solar, open-access power purchase agreements and renewable energy certificates. "
        f"Over the same period its Scope 2 emissions moved from {prev['scope2_tco2e']:,.0f} tCO2e to {cur['scope2_tco2e']:,.0f} tCO2e.",
        f"{spokes(rng).capitalize()} said that further capacity is being contracted and that the company will continue to retire certificates in its own name. "
        f"Analysts noted that the filed renewable share is the figure that investors should compare across peers.",
        f"The firm's overall GHG intensity was {cur['ghg_intensity']} tCO2e per Rs crore of turnover in {fy_long(fy)}, compared with {prev['ghg_intensity']} the previous year.",
    ]
    return art(c, d, head, paras, ["energy", "emissions"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_intensity(ctx: Ctx, rng, cid):
    c = ctx.co[cid]
    a, z = ctx.b(cid, "FY2020"), ctx.b(cid, "FY2025")
    drop = pct_change(a["ghg_intensity"], z["ghg_intensity"])
    d = pub(rng, z["filed_on"], 7, 60)
    head = rng.choice([f"{c['short_name']} cuts emission intensity by {abs(drop):.0f}% since FY2020" if drop < 0 else f"{c['short_name']} emission intensity rises {drop:.0f}% since FY2020",
                       f"{c['short_name']}: GHG intensity at {z['ghg_intensity']} tCO2e per Rs crore in {fy_long('FY2025')}"])
    paras = [
        f"{dateline(c)}{c['name']}'s greenhouse gas emission intensity stood at {z['ghg_intensity']} tCO2e per Rs crore of turnover in {fy_long('FY2025')}, "
        f"compared with {a['ghg_intensity']} in {fy_long('FY2020')}, a change of {drop:+.1f}%, its BRSR filings show.",
        f"In absolute terms, Scope 1 emissions went from {a['scope1_tco2e']:,.0f} tCO2e to {z['scope1_tco2e']:,.0f} tCO2e ({pct_change(a['scope1_tco2e'], z['scope1_tco2e']):+.1f}%), "
        f"while Scope 2 emissions went from {a['scope2_tco2e']:,.0f} tCO2e to {z['scope2_tco2e']:,.0f} tCO2e ({pct_change(a['scope2_tco2e'], z['scope2_tco2e']):+.1f}%). "
        f"Turnover grew from Rs {a['revenue_cr']:,.0f} crore to Rs {z['revenue_cr']:,.0f} crore over the period.",
        f"Analysts point out that intensity metrics can improve even when absolute emissions rise, since they are measured against revenue. "
        f"{spokes(rng).capitalize()} said that the company reports both measures and has set internal targets for each.",
        f"The renewable share of its electricity rose from {a['re_pct']}% to {z['re_pct']}% across the same years.",
    ]
    return art(c, d, head, paras, ["emissions", "results"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_assurance(ctx: Ctx, rng, cid, fy, frm, to):
    c = ctx.co[cid]
    b = ctx.b(cid, fy)
    d = pub(rng, b["filed_on"], 5, 40)
    word = {"none": "no external assurance", "limited": "limited assurance", "reasonable": "reasonable assurance"}
    head = rng.choice([f"{c['short_name']} moves to {to} assurance on BRSR Core", f"{c['short_name']} gets {to} assurance for sustainability data from {b['assurance_provider']}"])
    paras = [
        f"{dateline(c)}{c['name']} has had its BRSR Core disclosures for {fy_long(fy)} assured at the {to} level by {b['assurance_provider']}, "
        f"up from {word[frm]} the previous year, according to its filing dated {fmt_date(b['filed_on'])}.",
        f"{'Reasonable assurance involves more extensive testing, including of internal controls, than a limited engagement.' if to == 'reasonable' else 'A limited assurance engagement relies mainly on inquiries, analytical procedures and sample testing of records.'} "
        f"The assurance statement covers indicators such as Scope 1 emissions of {b['scope1_tco2e']:,.0f} tCO2e and Scope 2 emissions of {b['scope2_tco2e']:,.0f} tCO2e.",
        f"{spokes(rng).capitalize()} said that the move reflects the company's effort to give investors more confidence in its numbers. "
        f"Governance experts said that the type of assurance should be read together with the scope covered and any qualifications.",
        f"The company's wage data show that women received {b['women_wage_pct']}% of gross wages in the year, and that MSMEs supplied {b['msme_sourcing_pct']}% of inputs.",
    ]
    return art(c, d, head, paras, ["assurance", "governance"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_zld(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    cur, prev = ctx.b(cid, fy), ctx.b(cid, f"FY{int(fy[2:]) - 1}")
    d = pub(rng, cur["filed_on"], 5, 50)
    ch = pct_change(prev["water_discharge_kl"], cur["water_discharge_kl"])
    head = rng.choice([f"{c['short_name']} cuts water discharge {abs(ch):.0f}% in {fy_long(fy)}", f"{c['short_name']} trims effluent discharge to {cur['water_discharge_kl'] / 1e3:,.0f} thousand kL"])
    paras = [
        f"{dateline(c)}{c['name']} reduced the water it discharged to {cur['water_discharge_kl']:,.0f} kL in {fy_long(fy)} from {prev['water_discharge_kl']:,.0f} kL a year earlier, "
        f"a fall of {abs(ch):.1f}%, its BRSR shows. Total withdrawal was {cur['water_withdrawal_kl']:,.0f} kL, compared with {prev['water_withdrawal_kl']:,.0f} kL.",
        f"The company attributed the fall to expanded recycling and tertiary treatment at its effluent plants. {spokes(rng).capitalize()} said that treated water is now reused in "
        f"cooling, gardening and process applications at several units.",
        f"Industry experts said that effluent reduction has become a priority for processing-heavy sectors because of tighter norms and customer audits, and that independent "
        f"verification of water numbers remains important.",
        f"Waste generated by the company was {cur['waste_generated_t']:,.0f} tonnes in the year, of which {cur['waste_recovered_t']:,.0f} tonnes were recovered or recycled.",
    ]
    return art(c, d, head, paras, ["water", "results"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_safety(ctx: Ctx, rng, cid):
    c = ctx.co[cid]
    a, z = ctx.b(cid, "FY2020"), ctx.b(cid, "FY2025")
    d = pub(rng, z["filed_on"], 5, 50)
    head = rng.choice([f"{c['short_name']} LTIFR falls to {z['ltifr']:.2f} from {a['ltifr']:.2f} since FY2020", f"Safety record: {c['short_name']} reports LTIFR of {z['ltifr']:.2f}"])
    fat = sum(ctx.b(cid, fy)["fatalities"] for fy in ["FY2020", "FY2021", "FY2022", "FY2023", "FY2024", "FY2025"])
    paras = [
        f"{dateline(c)}{c['name']} reported a lost-time injury frequency rate of {z['ltifr']:.2f} per million hours worked in {fy_long('FY2025')}, compared with {a['ltifr']:.2f} in "
        f"{fy_long('FY2020')}, its BRSR filings show.",
        f"Over the six years from FY2020 to FY2025 the company's filings record a total of {fat} work-related fatalities, with {z['fatalities']} in the latest year. "
        f"{spokes(rng).capitalize()} said that behavioural safety programmes, contractor induction and near-miss reporting had helped to reduce injuries.",
        "Safety experts noted that frequency rates depend on how consistently contractor injuries are counted, and urged companies to publish both employee and contract-worker data.",
    ]
    return art(c, d, head, paras, ["safety", "results"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_fatality(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b = ctx.b(cid, fy)
    d = pub(rng, b["filed_on"], 3, 40)
    n = b["fatalities"]
    head = rng.choice([f"{c['short_name']} reports {n} work-related fatalit{'y' if n == 1 else 'ies'} in {fy_long(fy)}", f"Worker deaths at {c['short_name']}: BRSR records {n} in {fy_long(fy)}"])
    fac = max(ctx.fac_by_c[cid], key=lambda f: f["capacity_value"] if f["capacity_unit"].startswith("M") else 0)
    paras = [
        f"{dateline(c)}{c['name']} recorded {n} work-related fatalit{'y' if n == 1 else 'ies'} in {fy_long(fy)}, according to its BRSR filed on {fmt_date(b['filed_on'])}. "
        f"The company's lost-time injury frequency rate for the year was {b['ltifr']:.2f}.",
        f"Trade union representatives said that contract workers at heavy-industry sites remain the most exposed and called for independent safety audits. "
        f"{spokes(rng).capitalize()} said that every incident is investigated and that corrective actions are tracked by the board's risk committee.",
        f"The company operates {len(ctx.fac_by_c[cid])} facilities, including the {fac['name']} in {fac['district']}, {fac['state']}. "
        f"In the previous year its filing had recorded {ctx.b(cid, 'FY' + str(int(fy[2:]) - 1))['fatalities']} fatalities."
        if fy != "FY2020" else f"The company operates {len(ctx.fac_by_c[cid])} facilities across {join_and(ctx.states(cid))}.",
    ]
    return art(c, d, head, paras, ["safety", "results"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_results(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b, p = ctx.b(cid, fy), ctx.b(cid, f"FY{int(fy[2:]) - 1}")
    g = pct_change(p["revenue_cr"], b["revenue_cr"])
    d = pub(rng, b["filed_on"], 3, 28)
    head = rng.choice([f"{c['short_name']} FY{fy[2:]} turnover at Rs {b['revenue_cr']:,.0f} crore; ESG disclosures filed",
                       f"{c['short_name']} annual results: turnover {'up' if g >= 0 else 'down'} {abs(g):.1f}%, intensity at {b['ghg_intensity']}"])
    paras = [
        f"{dateline(c)}{c['name']} reported turnover of Rs {b['revenue_cr']:,.0f} crore for {fy_long(fy)}, {'up' if g >= 0 else 'down'} {abs(g):.1f}% from "
        f"Rs {p['revenue_cr']:,.0f} crore in the previous year, as it published its annual report and sustainability disclosures.",
        f"The ESG section of the report put Scope 1 emissions at {b['scope1_tco2e']:,.0f} tCO2e and Scope 2 at {b['scope2_tco2e']:,.0f} tCO2e, giving an intensity of "
        f"{b['ghg_intensity']} tCO2e per Rs crore of turnover ({p['ghg_intensity']} a year earlier). Renewable sources supplied {b['re_pct']}% of electricity "
        f"and the LTIFR was {b['ltifr']:.2f}.",
        f"The company recovered {b['waste_recovered_t']:,.0f} tonnes of the {b['waste_generated_t']:,.0f} tonnes of waste it generated. Women received {b['women_wage_pct']}% of gross wages.",
        f"{spokes(rng).capitalize()} said that the board had reviewed the sustainability metrics, which were {'externally assured at the ' + b['assurance_type'] + ' level' if b['assurance_type'] != 'none' else 'not externally assured this year'}.",
    ]
    return art(c, d, head, paras, ["results", "emissions", "governance"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


# =====================================================================
# Company press releases (tier 4)
# =====================================================================

def _about(c) -> str:
    status = f"listed ({c['listing']})" if c["listing"] != "Unlisted" else "privately held"
    return (f"About {c['name']}: {c['name']} is a {status} {SECTOR_PHRASE[c['sector']]} company "
            f"headquartered in {c['hq_city']}, {c['hq_state']}.")


def t_pr_green(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b = ctx.b(cid, fy)
    d = pub(rng, fy_range(fy)[1].isoformat(), 40, 100)
    head = rng.choice([f"{c['short_name']} meets {b['re_pct']}% of electricity from renewables in {fy_long(fy)}", f"{c['short_name']} announces {b['re_pct']}% renewable electricity share"])
    paras = [
        f"{dateline(c)}{c['name']} today announced that renewable sources met {b['re_pct']}% of the electricity consumed across its operations during {fy_long(fy)}.",
        f"\"This reflects our sustained investment in clean power,\" {spokes(rng)} said in a statement. The company said it will continue to expand captive and "
        f"open-access renewable capacity and will report progress in its annual BRSR.",
        f"The company reported turnover of Rs {b['revenue_cr']:,.0f} crore for the year and operates {len(ctx.fac_by_c[cid])} facilities across {join_and(ctx.states(cid))}.",
        _about(c),
    ]
    return art(c, d, head, paras, ["energy"], tier=4, outlet=company_outlet(c))


def t_pr_assurance(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b = ctx.b(cid, fy)
    d = pub(rng, b["filed_on"], 1, 15)
    head = f"{c['short_name']} publishes {fy_long(fy)} BRSR with {b['assurance_type']} assurance"
    paras = [
        f"{dateline(c)}{c['name']} has published its Business Responsibility and Sustainability Report for {fy_long(fy)}. The BRSR Core indicators carry "
        f"{b['assurance_type']} assurance from {b['assurance_provider']}.",
        f"Key indicators include Scope 1 emissions of {b['scope1_tco2e']:,.0f} tCO2e, Scope 2 emissions of {b['scope2_tco2e']:,.0f} tCO2e, a GHG intensity of {b['ghg_intensity']} "
        f"tCO2e per Rs crore and renewable electricity of {b['re_pct']}%. The report is available on the company's investor relations page.",
        f"\"Transparent, assured reporting is central to how we work with investors,\" {spokes(rng)} said.",
        _about(c),
    ]
    return art(c, d, head, paras, ["assurance", "results"], tier=4, outlet=company_outlet(c))


def t_pr_capacity(ctx: Ctx, rng, cid, fac):
    c = ctx.co[cid]
    b = ctx.latest(cid)
    d = pub(rng, ctx.latest(cid)["filed_on"], 5, 200)
    head = rng.choice([f"{c['short_name']} to expand {fac['name']} in {fac['district']}", f"{c['short_name']} board approves capex for {fac['district']} facility"])
    paras = [
        f"{dateline(c, fac)}{c['name']} said its board has approved an investment programme for the {fac['name']} in {fac['district']}, {fac['state']}, "
        f"which currently has a capacity of {cap(fac)}. The company said that the project will include energy-efficiency measures and upgraded pollution control equipment.",
        f"\"The expansion is aligned with our plan to reduce emission intensity, which stood at {b['ghg_intensity']} tCO2e per Rs crore of turnover in {fy_long('FY2025')},\" "
        f"{spokes(rng)} said. The project will require all statutory approvals, including consent from the {BOARD_NAME[STATES[fac['state']]['board']]}.",
        f"The company reported turnover of Rs {b['revenue_cr']:,.0f} crore in {fy_long('FY2025')}.",
        _about(c),
    ]
    return art(c, d, head, paras, ["energy", "governance"], tier=4, outlet=company_outlet(c))


def t_pr_safety(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b, p = ctx.b(cid, fy), ctx.b(cid, f"FY{int(fy[2:]) - 1}")
    d = pub(rng, b["filed_on"], 1, 30)
    head = f"{c['short_name']} improves lost-time injury rate to {b['ltifr']:.2f} in {fy_long(fy)}"
    paras = [
        f"{dateline(c)}{c['name']} announced that its lost-time injury frequency rate improved to {b['ltifr']:.2f} per million hours worked in {fy_long(fy)}, from {p['ltifr']:.2f} a year earlier.",
        f"The company said that the improvement followed investments in safety training, machine guarding and contractor onboarding. "
        f"\"Every incident is a call to do better,\" {spokes(rng)} said. The company recorded {b['fatalities']} work-related fatalit{'y' if b['fatalities'] == 1 else 'ies'} during the year and said that it continues to work towards zero harm.",
        f"The company's safety performance is disclosed in its BRSR for the year, which was filed on {fmt_date(b['filed_on'])}.",
        _about(c),
    ]
    return art(c, d, head, paras, ["safety"], tier=4, outlet=company_outlet(c))


# =====================================================================
# Features and commentary
# =====================================================================

def t_analyst(ctx: Ctx, rng, cid):
    c = ctx.co[cid]
    a, z = ctx.b(cid, "FY2023"), ctx.b(cid, "FY2025")
    d = pub(rng, z["filed_on"], 20, 90)
    head = rng.choice([f"Analysts see ESG disclosures as swing factor for {c['short_name']}", f"What {poss(c['short_name'])} BRSR numbers say about the next two years"])
    paras = [
        f"{dateline(c)}Brokerages tracking {c['name']} said that the company's sustainability disclosures have become a larger part of their assessment, "
        f"with Scope 1 and Scope 2 emissions of {z['scope1_tco2e'] + z['scope2_tco2e']:,.0f} tCO2e in {fy_long('FY2025')} against {a['scope1_tco2e'] + a['scope2_tco2e']:,.0f} tCO2e two years earlier.",
        f"One analyst said that intensity, at {z['ghg_intensity']} tCO2e per Rs crore of turnover, is the metric to watch because it ties emissions to the scale of the business, "
        f"while another cautioned that absolute emissions matter for carbon pricing exposure. Renewable power was {z['re_pct']}% of electricity in the year.",
        f"The firms also flagged the assurance level ({z['assurance_type']}) and the lack of Scope 3 data as areas where disclosure could improve. "
        f"{spokes(rng).capitalize()} said that the company is working with its advisers on value-chain reporting.",
        f"Turnover was Rs {z['revenue_cr']:,.0f} crore in {fy_long('FY2025')}, against Rs {a['revenue_cr']:,.0f} crore in {fy_long('FY2023')}.",
    ]
    return art(c, d, head, paras, ["results", "governance", "emissions"], outlet=pick_outlet(rng, None, 0.0) if False else rng.choice(NATIONAL))


def t_rec(ctx: Ctx, rng, cid):
    c = ctx.co[cid]
    certs = [r for r in ctx.certs_by_c[cid] if r["vintage_year"] == 2024]
    ret = sum(r["mwh"] for r in certs if r["status"] == "retired")
    act = sum(r["mwh"] for r in certs if r["status"] == "active")
    b = ctx.latest(cid)
    d = pub(rng, b["filed_on"], 10, 90)
    head = rng.choice([f"Registry data: {c['short_name']} retired {ret:,.0f} MWh of 2024-vintage certificates", f"What the certificate registry shows about {poss(c['short_name'])} renewable claims"])
    paras = [
        f"{dateline(c)}Registry records show that {c['name']} held renewable energy certificates of 2024 vintage totalling {ret + act:,.0f} MWh, of which {ret:,.0f} MWh "
        f"have been retired and {act:,.0f} MWh remain active, as of the latest registry extract.",
        f"Retirement is the step that allows a buyer to claim the renewable attribute of a certificate; certificates that remain active can still be sold or transferred, "
        f"and so should not be counted towards a renewable energy claim. The company's BRSR for {fy_long('FY2025')} reports that {b['re_pct']}% of its electricity was renewable.",
        f"{spokes(rng).capitalize()} said that the company manages its certificate portfolio in line with registry rules. Analysts said that readers of sustainability reports should "
        f"compare claims with the retired volume rather than with purchases.",
        "Certificates are issued through registries such as the REC Registry of India and the international I-REC standard, each of which publishes issuance and redemption data.",
    ]
    return art(c, d, head, paras, ["energy", "assurance"], outlet=rng.choice(["Green Ledger India", "ESG Watch India", "Business Mint India"]))


def t_waste(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b = ctx.b(cid, fy)
    share = b["waste_recovered_t"] / b["waste_generated_t"] * 100
    d = pub(rng, b["filed_on"], 10, 80)
    head = rng.choice([f"{c['short_name']} recovers {share:.0f}% of waste in {fy_long(fy)}", f"Circularity push: {c['short_name']} recycles {b['waste_recovered_t']:,.0f} tonnes of waste"])
    paras = [
        f"{dateline(c)}{c['name']} generated {b['waste_generated_t']:,.0f} tonnes of waste in {fy_long(fy)} and recovered, recycled or co-processed {b['waste_recovered_t']:,.0f} tonnes, "
        f"or {share:.1f}%, according to its BRSR.",
        f"The company said that by-products are sold to downstream users or fed back into its own processes, and that hazardous waste is sent to authorised facilities. "
        f"{spokes(rng).capitalize()} said that the aim is to raise the recovery share each year.",
        f"Water withdrawal for the year was {b['water_withdrawal_kl']:,.0f} kL and discharge was {b['water_discharge_kl']:,.0f} kL.",
        "Circularity indicators are among the BRSR Core attributes that are now subject to assurance for the largest listed companies.",
    ]
    return art(c, d, head, paras, ["waste", "results"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_women(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b, a = ctx.b(cid, fy), ctx.b(cid, "FY2020")
    d = pub(rng, b["filed_on"], 10, 80)
    head = rng.choice([f"Women get {b['women_wage_pct']}% of wages at {c['short_name']} in {fy_long(fy)}", f"{c['short_name']} reports rise in women's share of wages to {b['women_wage_pct']}%"])
    paras = [
        f"{dateline(c)}Women received {b['women_wage_pct']}% of the gross wages paid by {c['name']} in {fy_long(fy)}, up from {a['women_wage_pct']}% in {fy_long('FY2020')}, "
        f"its BRSR filings show.",
        f"The company said that it has widened recruitment, introduced flexible shifts and expanded training for women at plant level. "
        f"{spokes(rng).capitalize()} said that the share is likely to rise as more women move into supervisory roles.",
        f"Gender diversity is one of the nine BRSR Core attributes, and gender-wise wage data are among the indicators subject to assurance. "
        f"{poss(c['short_name'])} indicators for the year were {'externally assured' if b['assurance_type'] != 'none' else 'not externally assured'}.",
        f"The company's MSME sourcing was {b['msme_sourcing_pct']}% of inputs in the year.",
    ]
    return art(c, d, head, paras, ["diversity", "results"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_msme(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b, a = ctx.b(cid, fy), ctx.b(cid, "FY2020")
    d = pub(rng, b["filed_on"], 10, 80)
    head = rng.choice([f"{c['short_name']} sources {b['msme_sourcing_pct']}% of inputs from MSMEs", f"MSME sourcing at {c['short_name']} rises to {b['msme_sourcing_pct']}%"])
    paras = [
        f"{dateline(c)}{c['name']} sourced {b['msme_sourcing_pct']}% of its input material from micro, small and medium enterprises in {fy_long(fy)}, compared with "
        f"{a['msme_sourcing_pct']}% in {fy_long('FY2020')}, its BRSR shows.",
        f"The company said that it runs vendor development programmes, offers faster payment cycles to small suppliers and helps them to meet environmental norms. "
        f"{spokes(rng).capitalize()} said that local sourcing also lowers logistics emissions.",
        "Inclusive development is one of the BRSR Core attributes, and MSME sourcing is reported both as a share of inputs and as a share of purchases.",
        f"Turnover for the year was Rs {b['revenue_cr']:,.0f} crore.",
    ]
    return art(c, d, head, paras, ["governance", "results"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_digest(ctx: Ctx, rng, cid, fy):
    c = ctx.co[cid]
    b = ctx.b(cid, fy)
    d = pub(rng, b["filed_on"], 3, 20)
    head = rng.choice([f"{c['short_name']} BRSR at a glance: {fy_long(fy)}", f"Inside {poss(c['short_name'])} {fy_long(fy)} BRSR filing"])
    paras = [
        f"{dateline(c)}{c['name']} filed its Business Responsibility and Sustainability Report for {fy_long(fy)} on {fmt_date(b['filed_on'])}. "
        f"Turnover was Rs {b['revenue_cr']:,.0f} crore.",
        f"Emissions: Scope 1 of {b['scope1_tco2e']:,.0f} tCO2e, Scope 2 of {b['scope2_tco2e']:,.0f} tCO2e, intensity of {b['ghg_intensity']} tCO2e per Rs crore. "
        f"Energy: {b['energy_gj']:,.0f} GJ consumed, with {b['re_pct']}% of electricity from renewables. Water: {b['water_withdrawal_kl']:,.0f} kL withdrawn and {b['water_discharge_kl']:,.0f} kL discharged.",
        f"Waste: {b['waste_generated_t']:,.0f} tonnes generated, {b['waste_recovered_t']:,.0f} tonnes recovered. People: LTIFR of {b['ltifr']:.2f}, {b['fatalities']} fatalities, "
        f"{b['women_wage_pct']}% of wages paid to women and {b['msme_sourcing_pct']}% of inputs from MSMEs.",
        f"Assurance: {'none' if b['assurance_type'] == 'none' else b['assurance_type'] + ' assurance by ' + b['assurance_provider']}. {spokes(rng).capitalize()} said that the company "
        f"will continue to expand the scope of its reporting.",
    ]
    return art(c, d, head, paras, ["results", "emissions", "assurance"], outlet=pick_outlet(rng, c["hq_state"], 0.5))


def t_facility(ctx: Ctx, rng, cid, fac):
    c = ctx.co[cid]
    d = pub(rng, ctx.latest(cid)["filed_on"], 5, 200)
    head = rng.choice([f"Inside {poss(c['short_name'])} {fac['name']}", f"{fac['district']} unit anchors {poss(c['short_name'])} {fac['state']} operations"])
    b = ctx.latest(cid)
    paras = [
        f"{dateline(c, fac)}The {fac['name']} of {c['name']} in {fac['district']}, {fac['state']}, has a capacity of {cap(fac)} and operates under consent "
        f"{fac['consent_no']} from the {BOARD_NAME[STATES[fac['state']]['board']]}. It is one of {len(ctx.fac_by_c[cid])} facilities that the company runs.",
        f"The site is located at roughly {fac['lat']:.2f} degrees north and {fac['lon']:.2f} degrees east. "
        + ("It sits close to forest land, which makes dust control, green belt maintenance and compliance with clearance conditions a daily concern for the plant team. "
           if fac["forest_adjacent"] else "Local officials said that the plant is a significant employer in the district. ")
        + f"{spokes(rng).capitalize()} said that the facility is a priority for energy-efficiency investments.",
        f"Across the company, Scope 1 emissions were {b['scope1_tco2e']:,.0f} tCO2e in {fy_long('FY2025')}, and a share of that is attributed to this facility in its facility-level disclosures.",
    ]
    return art(c, d, head, paras, ["energy", "emissions"], outlet=pick_outlet(rng, fac["state"]))


# =====================================================================
# General industry articles (company_id NULL)
# =====================================================================

def _gd(rng, fy, lo=30, hi=200):
    y = int(fy[2:])
    return min(date(y, 8, 1) + timedelta(days=rng.randint(lo, hi)), CAP).isoformat()


def _prev(fy):
    return f"FY{int(fy[2:]) - 1}"


def _fy_rows(ctx, a, b, key="date", table="regulatory_actions"):
    return [r for r in ctx.t[table] if a.isoformat() <= r[key] <= b.isoformat()]


def g_roundup(ctx: Ctx, rng, sector, fy):
    a, b = fy_range(fy)
    allr = [r for r in ctx.t["regulatory_actions"] if a.isoformat() <= r["date"] <= b.isoformat() and ctx.co[r["company_id"]]["sector"] == sector]
    rows = sorted(allr, key=lambda r: -r["penalty_inr"])[:4]
    if len(rows) < 3:
        return None
    total = sum(r["penalty_inr"] for r in allr)
    by_auth = {}
    for r in allr:
        k = "state boards" if r["authority"] not in ("NGT", "CPCB", "SEBI", "MoEFCC") else r["authority"]
        by_auth[k] = by_auth.get(k, 0) + 1
    by_type = {}
    for r in allr:
        by_type[r["order_type"].replace("_", " ")] = by_type.get(r["order_type"].replace("_", " "), 0) + 1
    d = _gd(rng, fy, 20, 120)
    head = rng.choice([f"{sector} sector: regulators' orders in {fy_long(fy)} add up to {inr(total)}", f"{sector} makers faced {len(allr)} environmental orders in {fy_long(fy)}"])
    items = []
    for r in rows:
        c = ctx.co[r["company_id"]]
        items.append(f"{c['name']} ({r['authority']}, {fmt_date(r['date'])}, {r['order_type'].replace('_', ' ')}{', ' + inr(r['penalty_inr']) if r['penalty_inr'] else ''})")
    paras = [
        f"A review of regulatory records for {fy_long(fy)} shows that companies in the {sector.lower()} sector were subject to {len(allr)} environmental orders, "
        f"with total monetary penalties and compensation of {inr(total)}.",
        "The most significant orders were against " + join_and(items) + ".",
        "By authority, the orders were split as follows: " + join_and([f"{v} from {k}" for k, v in sorted(by_auth.items(), key=lambda x: -x[1])]) + ". "
        "By type: " + join_and([f"{v} {k}" for k, v in sorted(by_type.items(), key=lambda x: -x[1])]) + ".",
        "Lawyers said that the mix of orders has shifted from simple show-cause notices towards compensation, in line with the polluter pays principle that the tribunal applies. "
        "They added that many orders are appealed and that the final amounts can differ from those initially directed.",
        "Industry bodies said that the sector has been investing in pollution control and online monitoring, and that continuous data now makes violations easier to detect and verify. "
        "Several companies named above said that they had filed replies or paid under protest, and that they were reviewing their compliance systems.",
        f"Analysts said that the financial impact of individual orders is usually small relative to the turnover of the companies involved, but that repeated orders at the same site can "
        f"lead to consent conditions that constrain production, which is the larger risk to earnings.",
    ]
    return art(None, d, head, paras, ["regulatory"], outlet=rng.choice(OUTLETS))


POLICY = [
    ("Carbon market rules: what India's trading scheme means for heavy industry",
     ["India's compliance carbon market is set to place emission intensity targets on large industrial units in energy-intensive sectors such as steel, cement, power and chemicals, with units that outperform their targets earning tradable credits and those that miss them having to buy.",
      "Industry executives said that the design of baselines will decide who gains. Plants that have already invested in efficiency may find that the easy reductions have been made, while those with older equipment may have more headroom.",
      "Analysts said that credible plant-level emission data will become a prerequisite, which strengthens the case for third-party verification and for matching company disclosures against facility-level reporting.",
      "Companies are building internal carbon prices to prepare, and several have asked for clarity on how renewable energy certificates and captive generation will be treated under the scheme.",
      "Finance teams said that the first compliance cycle will be a learning exercise, with the real cost impact depending on the price at which credits trade and on how quickly targets tighten after the first period.",
      "Environmental groups welcomed the move but said that intensity targets alone do not guarantee that absolute emissions will fall, and asked for an absolute cap to be phased in for the largest emitters."], ["emissions", "regulatory"]),
    ("BRSR Core assurance: the glide path for India's listed companies",
     ["SEBI's glide path for assurance on BRSR Core indicators brings the largest listed companies into a regime where nine ESG attributes are verified by an independent provider, starting with limited assurance and moving towards reasonable assurance.",
      "Assurance providers say that demand has outstripped supply of qualified practitioners, particularly for greenhouse gas verification at industrial sites, and that fees have risen.",
      "Investors have welcomed the move but note that the scope and conclusion of each assurance statement differ, and that a qualified conclusion or a narrow scope tells a different story from an unmodified one.",
      "Companies that have moved early to reasonable assurance argue that it forces better controls on data, while others say that the cost and effort are material for mid-sized firms.",
      "Practitioners said that the most common qualifications relate to estimated water withdrawal, default emission factors for fugitive emissions and incomplete contractor safety data, which are areas where systems are still maturing.",
      "Regulators have indicated that they will review the first full cycle of assured filings before deciding on the next phase of the glide path."], ["assurance", "governance"]),
    ("Online emission monitoring: what the data shows and what regulators do with it",
     ["Industries in the highly polluting categories are required to transmit stack emission and effluent data continuously to pollution control boards, and the data are now used by regulators to prioritise inspections.",
      "Environmental lawyers said that exceedance data have started to figure in tribunal proceedings, where petitioners submit extracts from the monitoring portals as evidence.",
      "Industry groups say that sensor drift and downtime can cause spurious readings, and they have asked boards to publish calibration records alongside the data.",
      "Several states have started to link repeated exceedances to automatic show-cause notices, which is expected to speed up enforcement.",
      "Typical limits for particulate matter range from 30 to 50 mg per normal cubic metre depending on the age and category of the plant, while sulphur dioxide and nitrogen oxide limits vary by technology and unit size.",
      "Effluent norms for treated discharge commonly specify limits of 30 mg per litre for biochemical oxygen demand, 250 mg per litre for chemical oxygen demand and 100 mg per litre for suspended solids."], ["emissions", "regulatory"]),
    ("Fly ash utilisation and the power sector's compliance challenge",
     ["Coal-fired power plants are required to utilise nearly all of the fly ash they generate, and non-compliance can attract environmental compensation.",
      "Operators say that demand from cement makers and brick manufacturers is uneven across regions, leaving some plants with ash stockpiles and dykes that need careful management.",
      "Regulators have been inspecting ash ponds after several breaches, and the tribunal has directed compensation in cases where dyke failures damaged farmland.",
      "Industry bodies have asked for transport subsidies to move ash to distant buyers and for faster clearances for ash-based construction projects.",
      "Cement producers said that they are willing to take more ash as a blending material, but that quality variations between plants and the distance to the plant gate affect economics.",
      "Investors tracking the sector said that ash utilisation, dyke integrity and flue gas desulphurisation timelines are now routine questions in meetings with management."], ["waste", "regulatory"]),
    ("Forest clearances and the new role of satellite alerts",
     ["Mining and industrial lease holders are finding that satellite-based forest-loss alerts are being used by communities, researchers and regulators to question activity near their sites.",
      "Alert systems detect loss of tree cover at a fine resolution and publish it within days, but they do not attribute responsibility, and field verification remains essential.",
      "Forest officials said that they have begun to cross-check alerts against clearance maps, while companies say that they need clear protocols on how alerts will be treated.",
      "Researchers cautioned against reading too much into single alerts, but said that clusters near a lease over a year deserve scrutiny.",
      "Companies with zero-deforestation commitments said that they are adding satellite monitoring to their own reporting, so that they can respond before a third party raises a question.",
      "Legal experts said that a satellite alert is not proof of a violation, but that a pattern of alerts within a lease buffer could shift the burden of explanation onto the operator."], ["biodiversity", "regulatory"]),
    ("Renewable certificates: what counts as a renewable energy claim",
     ["Renewable energy certificates let buyers claim the attributes of renewable generation, but the claim is only valid once the certificates are retired in the buyer's name.",
      "Registry data show that a significant volume of certificates are issued each year that are never retired, and that some buyers hold large active balances.",
      "Sustainability analysts said that corporate renewable claims should be reconciled against retirement records, and against the renewable share reported in filed disclosures.",
      "Registries have been asked to make retirement data easier to search, so that investors and civil society can verify claims.",
      "Buyers said that the choice between certificates and physical power contracts depends on the location of their plants and on grid constraints, and that many use a mix of both.",
      "Standard setters said that any claim of renewable electricity should be accompanied by the period, the volume retired and the registry in which the retirement was recorded."], ["energy", "assurance"]),
]


def g_policy(ctx: Ctx, rng, topic: int, year: int):
    h, ps, topics = POLICY[topic % len(POLICY)]
    d = min(date(year, rng.randint(1, 12), rng.randint(1, 28)), CAP).isoformat()
    ps = list(ps) + [rng.choice(ESG_G)]
    return art(None, d, h, ps, topics, outlet=rng.choice(OUTLETS))


ESG_G = [
    "Market participants said that the next phase of disclosure rules will test how well companies can reconcile their reported numbers with external records.",
    "Rating agencies said that they now routinely compare company filings with regulatory orders and satellite data before assigning ESG scores.",
    "The ministry is expected to consult industry before notifying the final rules, and stakeholders have been asked to submit comments.",
]


def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def g_league(ctx: Ctx, rng, sector, fy):
    rows = [(b["ghg_intensity"], b) for b in ctx.t["brsr_filings"] if b["fy"] == fy and ctx.co[b["company_id"]]["sector"] == sector]
    if len(rows) < 8:
        return None
    rows.sort(key=lambda x: x[0])
    low, high = rows[:3], rows[-3:]
    d = _gd(rng, fy, 40, 220)
    fmt = lambda xs: join_and([f"{ctx.co[b['company_id']]['name']} ({gi} tCO2e per Rs crore)" for gi, b in xs])
    med = _median([x[0] for x in rows])
    prev = [b["ghg_intensity"] for b in ctx.t["brsr_filings"] if b["fy"] == _prev(fy) and ctx.co[b["company_id"]]["sector"] == sector]
    pmed = _median(prev) if prev else None
    assured = sum(1 for _, b in rows if b["assurance_type"] != "none")
    head = rng.choice([f"{sector} emission league table, {fy_long(fy)}: who is cleanest per rupee", f"Emission intensity across {sector.lower()} companies varies widely in {fy_long(fy)}"])
    paras = [
        f"An analysis of BRSR filings for {fy_long(fy)} across {len(rows)} {sector.lower()} companies shows a wide spread in greenhouse gas intensity, measured as Scope 1 plus Scope 2 emissions "
        f"per Rs crore of turnover. The median was {med} tCO2e per Rs crore.",
        f"The lowest intensities were reported by {fmt(low)}.",
        f"At the other end, the highest intensities were reported by {fmt(list(reversed(high)))}. The top of the range is {high[-1][0] / max(low[0][0], 0.1):.1f} times the bottom.",
        (f"The median in the previous year was {pmed} tCO2e per Rs crore, so the sector median moved by {pct_change(pmed, med):+.1f}% year on year. " if pmed else "")
        + f"Of the {len(rows)} filings, {assured} carried some form of external assurance.",
        "Analysts cautioned that product mix, fuel mix and the share of captive power explain much of the difference, and that intensity comparisons are most meaningful within narrow sub-segments.",
        "They added that intensity can improve while absolute emissions rise, and that investors should read both figures together with the assurance level of each filing.",
    ]
    return art(None, d, head, paras, ["emissions", "results"], outlet=rng.choice(OUTLETS))


def g_crackdown(ctx: Ctx, rng, state, fy):
    a, b = fy_range(fy)
    fids = {f["facility_id"] for f in ctx.t["facilities"] if f["state"] == state}
    regs = [r for r in ctx.t["regulatory_actions"] if r["facility_id"] in fids and a.isoformat() <= r["date"] <= b.isoformat()]
    ev = [e for e in ctx.t["ocems_exceedances"] if e["facility_id"] in fids and a.isoformat() <= e["date"] <= b.isoformat()]
    total = sum(r["penalty_inr"] for r in regs)
    if len(regs) < 4 or total <= 0:
        return None
    board = BOARD_NAME[STATES[state]["board"]]
    top = sorted(regs, key=lambda r: -r["penalty_inr"])[:3]
    bytype = {}
    for r in regs:
        k = r["order_type"].replace("_", " ")
        bytype[k] = bytype.get(k, 0) + 1
    byparam = {}
    for e in ev:
        byparam[e["parameter"]] = byparam.get(e["parameter"], 0) + 1
    d = _gd(rng, fy, 20, 150)
    head = rng.choice([f"{state}: {len(regs)} environmental orders against tracked industrial units in {fy_long(fy)}", f"{board} and the tribunal: {state}'s enforcement record for {fy_long(fy)}"])
    paras = [
        f"Regulatory records for {fy_long(fy)} show {len(regs)} environmental orders against industrial facilities of tracked listed companies in {state}, with penalties and compensation "
        f"totalling {inr(total)}. The {board} accounted for {len([r for r in regs if r['authority'] == STATES[state]['board']])} of them.",
        "The largest orders were against " + join_and([f"{ctx.co[r['company_id']]['name']} ({r['authority']}, {fmt_date(r['date'])}{', ' + inr(r['penalty_inr']) if r['penalty_inr'] else ''})" for r in top]) + ".",
        "By type, the orders comprised " + join_and([f"{v} {k}" for k, v in sorted(bytype.items(), key=lambda x: -x[1])]) + ".",
        f"Online monitoring data from the same facilities recorded {len(ev)} exceedances of prescribed limits during the year"
        + (", comprising " + join_and([f"{v} for {k}" for k, v in sorted(byparam.items(), key=lambda x: -x[1])]) + ". " if byparam else ". ")
        + "Officials said that the data help the board to target inspections.",
        "Industry representatives said that compliance spending has risen and that they would like clearer timelines for the closure of show-cause matters.",
        f"Environmental groups in {state} said that enforcement is improving but that follow-up verification after an order is inconsistent, and asked boards to publish compliance status alongside the original order.",
    ]
    return art(None, d, head, paras, ["regulatory", "emissions"], outlet=pick_outlet(rng, state, 0.2))


def g_forest_report(ctx: Ctx, rng, fy):
    a, b = fy_range(fy)
    al = [x for x in ctx.t["land_alerts"] if a.isoformat() <= x["alert_date"] <= b.isoformat()]
    rows = []
    for nm, lat0, lat1, lon0, lon1, w in FOREST_BOXES[:4]:
        sub = [x for x in al if lat0 <= x["lat"] <= lat1 and lon0 <= x["lon"] <= lon1]
        rows.append((nm, len(sub), sum(x["area_ha"] for x in sub)))
    near = [x for x in al if x["nearest_facility_id"] and x["distance_km"] is not None and x["distance_km"] <= 5]
    byfac = {}
    for x in near:
        byfac.setdefault(x["nearest_facility_id"], []).append(x)
    topf = sorted(byfac.items(), key=lambda kv: -sum(y["area_ha"] for y in kv[1]))[:3]
    d = _gd(rng, fy, 30, 200)
    head = rng.choice([f"Forest-loss alerts in central and eastern India, {fy_long(fy)}: what the data shows", f"Satellite alerts flag clearing in {rows[0][0]} and neighbouring states in {fy_long(fy)}"])
    paras = [
        f"Satellite-based alerts in {fy_long(fy)} recorded {len(al)} forest-loss events in the tracked dataset, totalling {sum(x['area_ha'] for x in al):,.0f} hectares. "
        f"Of these, {len(near)} fell within 5 km of an industrial or mining facility in the database of listed companies.",
        "By state: " + join_and([f"{nm} {n} alerts ({ha:,.0f} ha)" for nm, n, ha in rows]) + ".",
        ("The facilities with the largest alert areas within 5 km were " + join_and([
            f"the {ctx.fac[fid]['name']} of {ctx.co[ctx.fac[fid]['company_id']]['name']} ({len(v)} alerts, {sum(y['area_ha'] for y in v):.1f} ha)" for fid, v in topf]) + "."
         if topf else "No facility in the tracked set recorded alerts within 5 km during the year."),
        "Researchers said that most alerts are in areas with no industrial presence and relate to shifting cultivation, roads, fire and encroachment, so proximity to a facility is a prompt to check and not proof of responsibility.",
        "Forest departments said that they are integrating alerts into patrolling plans, while civil society groups want the data to be considered in clearance reviews.",
        "Analysts noted that confidence levels differ between alert products, and that alerts flagged as highest confidence are the ones most likely to be confirmed in the field.",
    ]
    return art(None, d, head, paras, ["biodiversity"], outlet=rng.choice(["Odisha Field Report", "Green Ledger India", "ESG Watch India", "The Gangetic Business Chronicle"]))


def g_rec_market(ctx: Ctx, rng, vintage):
    certs = [r for r in ctx.t["re_certificates"] if r["vintage_year"] == vintage]
    tot = {s: sum(r["mwh"] for r in certs if r["status"] == s) for s in ("retired", "active", "transferred")}
    allv = sum(tot.values())
    reg = {}
    for r in certs:
        reg[r["registry"]] = reg.get(r["registry"], 0) + r["mwh"]
    d = min(date(vintage + 1, rng.randint(7, 12), rng.randint(1, 28)), CAP).isoformat()
    head = rng.choice([f"{vintage}-vintage certificates: {tot['retired'] / allv * 100:.0f}% retired among tracked companies", f"Renewable certificate market, {vintage} vintage: what companies retired"])
    paras = [
        f"Registry data on {len(certs)} certificate lots of {vintage} vintage held by companies in the tracked set show {allv:,.0f} MWh in total, of which {tot['retired']:,.0f} MWh "
        f"({tot['retired'] / allv * 100:.0f}%) were retired, {tot['active']:,.0f} MWh remained active and {tot['transferred']:,.0f} MWh had been transferred.",
        "By registry, the volumes were " + join_and([f"{v:,.0f} MWh on {k}" for k, v in sorted(reg.items())]) + ".",
        "Market participants said that the gap between certificates bought and certificates retired is a reminder that purchases alone do not support a renewable energy claim.",
        "Buyers in information technology and consumer goods have been the most active, while heavy industry has leaned on captive and open-access renewable supply.",
        "Registries said that they are considering features that would make retirement records easier to verify for third parties, including public redemption statements that name the beneficiary and the period of the claim.",
        "Analysts said that investors should compare the retired volume with a company's reported renewable electricity, since a large unretired balance can indicate that purchases are being counted before they are claimable.",
    ]
    return art(None, d, head, paras, ["energy"], outlet=rng.choice(["Green Ledger India", "ESG Watch India", "Business Mint India", "Capital Pulse India"]))


def g_assurance_trend(ctx: Ctx, rng, fy):
    rows = [b for b in ctx.t["brsr_filings"] if b["fy"] == fy]
    prows = [b for b in ctx.t["brsr_filings"] if b["fy"] == _prev(fy)]
    n = len(rows)
    cnt = {k: sum(1 for b in rows if b["assurance_type"] == k) for k in ("none", "limited", "reasonable")}
    pcnt = {k: sum(1 for b in prows if b["assurance_type"] == k) for k in ("none", "limited", "reasonable")}
    provs = {}
    for b in rows:
        if b["assurance_provider"]:
            provs[b["assurance_provider"]] = provs.get(b["assurance_provider"], 0) + 1
    topp = sorted(provs.items(), key=lambda kv: -kv[1])[:3]
    d = _gd(rng, fy, 20, 160)
    head = rng.choice([f"Assurance on BRSR: {cnt['reasonable'] + cnt['limited']} of {n} tracked companies had it in {fy_long(fy)}", f"How many companies get their sustainability data assured? The {fy_long(fy)} numbers"])
    paras = [
        f"Of {n} companies in the tracked set, {cnt['limited']} reported limited assurance on their BRSR Core disclosures for {fy_long(fy)}, {cnt['reasonable']} reported reasonable assurance and "
        f"{cnt['none']} reported none.",
        f"A year earlier, {pcnt['limited']} reported limited assurance, {pcnt['reasonable']} reasonable assurance and {pcnt['none']} none, so the number of assured filings moved from "
        f"{pcnt['limited'] + pcnt['reasonable']} to {cnt['limited'] + cnt['reasonable']}.",
        ("The busiest assurance providers were " + join_and([f"{k} ({v} filings)" for k, v in topp]) + "." if topp else "No assurance providers were recorded."),
        "Assurance providers said that adoption is highest among the largest listed companies, where the regulatory glide path is binding, and lowest among smaller filers.",
        "Investors said that they look not only at whether assurance exists but at its scope, level and any qualifications recorded in the statement.",
        "Several companies have moved from limited to reasonable assurance in successive years, which providers said is a sign of maturing data systems.",
    ]
    return art(None, d, head, paras, ["assurance", "governance"], outlet=rng.choice(OUTLETS))


def g_re_league(ctx: Ctx, rng, sector, fy):
    rows = sorted([(b["re_pct"], b) for b in ctx.t["brsr_filings"] if b["fy"] == fy and ctx.co[b["company_id"]]["sector"] == sector], key=lambda x: -x[0])
    if len(rows) < 8:
        return None
    top, bot = rows[:3], rows[-3:]
    d = _gd(rng, fy, 40, 220)
    avg = sum(x[0] for x in rows) / len(rows)
    prow = [b["re_pct"] for b in ctx.t["brsr_filings"] if b["fy"] == _prev(fy) and ctx.co[b["company_id"]]["sector"] == sector]
    pavg = sum(prow) / len(prow) if prow else None
    head = rng.choice([f"Renewable electricity in {sector.lower()}: leaders and laggards, {fy_long(fy)}", f"{sector} companies' renewable share averages {avg:.0f}% in {fy_long(fy)}"])
    f = lambda xs: join_and([f"{ctx.co[b['company_id']]['name']} ({p}%)" for p, b in xs])
    paras = [
        f"BRSR filings for {fy_long(fy)} show that renewable sources supplied an average of {avg:.1f}% of electricity across {len(rows)} {sector.lower()} companies in the tracked set.",
        f"The highest shares were reported by {f(top)}.",
        f"The lowest were reported by {f(list(reversed(bot)))}.",
        (f"The average was {pavg:.1f}% in the previous year, a change of {avg - pavg:+.1f} percentage points. " if pavg is not None else "")
        + f"{sum(1 for p, _ in rows if p >= 50)} of the {len(rows)} companies reported a renewable share of 50% or more.",
        "Analysts said that open-access contracts and captive projects are the main routes to higher shares, and that certificate purchases should be disclosed separately from physical supply.",
        "They added that the filed renewable share is the figure to compare across companies, and that claims in press releases or sustainability reports should be reconciled against it.",
    ]
    return art(None, d, head, paras, ["energy", "results"], outlet=rng.choice(OUTLETS))


TEMPLATE_NAMES = [n for n in globals() if n.startswith(("t_", "g_"))]
