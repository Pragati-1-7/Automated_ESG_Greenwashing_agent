"""
data_gen/news_gen.py

gen_news_articles(): builds ~500 articles. Order of business:
  1. the spec "news" items for the demo companies (exact headline / outlet / date / tier)
  2. a few neutral, truth-consistent extra articles per demo company
  3. evidence-driven coverage of generated companies (regulatory actions, OCEMS, land alerts, filings...)
  4. general industry articles (company_id NULL) until the target is reached
"""

from __future__ import annotations

import json

from . import news_tpl as T
from .news_base import BOARD_NAME, Ctx, dateline, finalize, join_and
from .world_utils import fmt_date, fy_long, haversine_km, inr, wc

DEMO = {"CMP-0001", "CMP-0002", "CMP-0003"}
TARGET = 500
TOPICS_OK = {"emissions", "energy", "water", "waste", "biodiversity", "regulatory", "safety", "diversity", "governance", "assurance", "results"}

GEN_FILL = [
    "Companies in heavy industry have been asked by lenders and customers to disclose facility-level data, and many have started to publish site-wise emissions and water use alongside their annual reports.",
    "Environmental lawyers said that the quality of data is now a bigger issue than its availability, since regulators, investors and communities increasingly compare several sources before forming a view on a company.",
    "Industry associations said that compliance costs have risen across sectors, but argued that predictable rules and clear timelines are more important to investment decisions than the level of any single norm.",
    "Sustainability consultants said that the gap between voluntary targets and filed numbers is where most disputes arise, and recommended that companies reconcile their communications with their regulatory filings every year.",
]


def _spec_articles(ctx: Ctx, rng) -> list[dict]:
    out = []
    regs1 = ctx.regs_by_c["CMP-0001"]
    ngt = next(r for r in regs1 if r["authority"] == "NGT")
    ospcb = next(r for r in regs1 if r["authority"] == "OSPCB")
    b24, b25, b20 = ctx.b("CMP-0001", "FY2024"), ctx.b("CMP-0001", "FY2025"), ctx.b("CMP-0001", "FY2020")
    la = [a for a in ctx.alerts_by_fac["FAC-0003"] if a["distance_km"] <= 5]
    ha = sum(a["area_ha"] for a in la)
    V = "Vajra Steel & Power Ltd"

    # ---- Vajra 1: NGT order (2024-08-16)
    out.append(dict(company_id="CMP-0001", outlet="The Eastern Ledger", tier=5, date="2024-08-16",
                    headline="NGT orders Vajra Steel to pay Rs 4.2 crore over Angul fly-ash breach",
                    topics=["regulatory", "emissions", "waste"], paras=[
        f"BHUBANESWAR: The National Green Tribunal's Eastern Zone bench at Kolkata has directed {V} to pay environmental compensation of Rs 4.2 crore for a fly-ash dyke "
        f"breach and repeated stack emission exceedances at its 1,200 MW captive power plant in Angul, Odisha. The order is dated {fmt_date(ngt['date'])} and was passed in {ngt['case_no']}.",
        "The bench found that a breach in the ash dyke at the Angul plant had allowed slurry to flow beyond the plant boundary, and noted that the plant's online monitoring data showed "
        "stack emission exceedances on repeated occasions. Applying the polluter pays principle, it asked the Odisha State Pollution Control Board to monitor compliance and report back.",
        f"Company records indicate that {V} has paid the amount under protest while it considers its legal options. {T.spokes(rng).capitalize()} said that the company respects the tribunal, "
        f"is studying the order and remains committed to compliance at all its sites. The sum is small against turnover of Rs {b24['revenue_cr']:,.0f} crore in {fy_long('FY2024')}, but environmental "
        f"lawyers said that the finding on repeated exceedances could matter more than the amount.",
        f"The company operates four facilities in Odisha, including an integrated steel plant at Jharsuguda, an iron ore mine in Keonjhar and a pellet plant at Barbil. Its filing for "
        f"{fy_long('FY2024')} reported Scope 1 emissions of {b24['scope1_tco2e']:,.0f} tCO2e and Scope 2 emissions of {b24['scope2_tco2e']:,.0f} tCO2e, with {b24['re_pct']}% of electricity from renewable sources.",
        "Local residents have for years complained about ash and dust around the Angul industrial belt, and the tribunal said that its directions are meant to restore the environment and are not a substitute for any action that the board may take under the Water and Air Acts."]))

    # ---- Vajra 2: villagers allege clearing (2025-01-22)
    out.append(dict(company_id="CMP-0001", outlet="Odisha Field Report", tier=5, date="2025-01-22",
                    headline="Villagers near Keonjhar allege fresh forest clearing around iron ore lease",
                    topics=["biodiversity", "regulatory"], paras=[
        f"KEONJHAR: Residents of several villages near the iron ore lease of {V} in Keonjhar district have alleged fresh forest clearing around the mine, and say that roads and "
        f"dumps have crept into areas that used to be wooded. Satellite alerts compiled by a local forest-rights collective show about {ha:.0f} hectares of forest loss within 5 km of the company's "
        f"Keonjhar mine, across {len(la)} separate alerts, between April 2024 and March 2025.",
        "The collective, which tracks an open forest-watch dataset, said that the pattern of alerts, clustered along the lease boundary and along haul roads, suggests continuing activity rather than "
        "isolated events. It has written to the district collector and the divisional forest officer asking for a joint field verification.",
        "Researchers who reviewed the data said that satellite alerts do not by themselves attribute responsibility, and that some of the loss could relate to community roads or fire. They added, "
        "however, that clusters of this size within a few kilometres of an active mine warrant a ground check, particularly in an area where forest clearance conditions apply.",
        f"The company did not respond to queries sent before publication. The Keonjhar mine, which has a capacity of 12 million tonnes a year of ore, feeds the company's integrated steel plant "
        f"at Jharsuguda and its pellet plant at Barbil. District officials said that they had received the villagers' representation and would examine it.",
        "Mining companies in Odisha operate under strict forest clearance conditions, including compensatory afforestation and limits on the area that can be broken. "
        "Forest-rights groups say that community consent processes are often not followed when leases expand."]))

    # ---- Vajra 3: press release (2025-06-05)
    out.append(dict(company_id="CMP-0001", outlet="Vajra Steel & Power Ltd (press release)", tier=4, date="2025-06-05",
                    headline="Vajra Steel powers half its operations with green energy",
                    topics=["energy"], paras=[
        f"BHUBANESWAR: {V} today announced that 50% of the electricity consumed across its operations in {fy_long('FY2025')} came from renewable sources, a claim the company says is based on "
        f"renewable energy certificates purchased during the year, along with its growing share of green power contracts.",
        f"\"Our customers expect low-carbon steel and we are delivering,\" {T.spokes(rng)} said in a statement. The company said that it has contracted additional solar and wind capacity "
        "and will continue to buy renewable energy certificates to cover its remaining requirement.",
        "The company said that it will publish detailed numbers in its annual disclosures, and that it remains committed to reducing the emission intensity of its steel production.",
        f"The company operates an integrated steel plant at Jharsuguda, a captive power plant at Angul, a pellet plant at Barbil and an iron ore mine at Keonjhar, all in Odisha.",
        f"About {V}: {V} is a NSE-listed (NSE: VAJRASTL) steel and power company headquartered in Bhubaneswar, Odisha."]))

    # ---- Vajra 4: Business Mint analysis (2025-07-10)
    out.append(dict(company_id="CMP-0001", outlet="Business Mint India", tier=5, date="2025-07-10",
                    headline="Analysts question Vajra's green power math as most RECs remain unretired",
                    topics=["energy", "assurance", "emissions"], paras=[
        f"MUMBAI: Analysts are questioning the renewable energy claims of {V} after registry data showed that most of the certificates it holds for 2024 remain unretired. "
        f"The registry shows 2.1 million MWh of certificates still active, and only 0.31 million MWh retired.",
        f"The company said in a June press release that half of its electricity in {fy_long('FY2025')} came from renewable sources, based on renewable energy certificates purchased. "
        f"Its BRSR filing, however, shows renewable electricity at {b25['re_pct']}% of the total.",
        "Retirement is the step that lets a buyer claim the renewable attribute of a certificate; certificates that remain active can still be sold or transferred. "
        "Sustainability analysts said that a claim based on purchased but unretired certificates should not be counted as renewable electricity, and that the filed figure is the number to use.",
        f"{T.spokes(rng).capitalize()} said that the company manages its certificate portfolio in line with registry rules and that further retirements would follow. "
        f"The company's filed Scope 1 emissions were {b25['scope1_tco2e']:,.0f} tCO2e in {fy_long('FY2025')}, against {b20['scope1_tco2e']:,.0f} tCO2e in {fy_long('FY2020')}.",
        f"The BRSR carries limited assurance from {b25['assurance_provider']}, and analysts said that reasonable assurance would give investors more comfort on energy claims."]))

    # ---- Sahyadri 1: CPCB closure direction (2023-02-11)
    cp = next(r for r in ctx.regs_by_c["CMP-0002"] if r["authority"] == "CPCB")
    out.append(dict(company_id="CMP-0002", outlet="Deccan Industry Times", tier=5, date="2023-02-11",
                    headline="CPCB orders Sahyadri's Gulbarga plant to curb dust or face closure",
                    topics=["regulatory", "emissions"], paras=[
        "KALABURAGI: The Central Pollution Control Board has issued a closure direction to the Gulbarga Cement Works of Sahyadri Cement Industries Ltd over fugitive dust emissions, "
        f"under Section 5 of the Environment (Protection) Act. The direction was issued on {fmt_date(cp['date'])} ({cp['case_no']}).",
        "The board said that inspections found dust escaping from raw material handling and clinker storage areas, and directed the company to take corrective steps, including covered "
        "conveyors, water sprinkling and upgrades to bag filters. The direction carries no monetary penalty, but allows the authority to cut power and water to the unit if the company does not comply.",
        "A company spokesperson said that Sahyadri Cement has received the direction and is working with the board on corrective measures. The Gulbarga works has a capacity of 4 million tonnes of cement a year and is one of four facilities "
        "that the company operates in Maharashtra and Karnataka.",
        "Update (18 April 2023): the CPCB revoked the direction after verifying compliance, according to a communication seen by this publication. The board said that the corrective measures "
        "had been completed and that the unit's dust emissions were within limits at the time of the verification visit.",
        "Cement plants are among the sources of fine particulate emissions that regulators monitor most closely, and closure directions are typically withdrawn once a verification visit confirms compliance."]))

    # ---- Sahyadri 2: PR (2025-05-20)
    out.append(dict(company_id="CMP-0002", outlet="Sahyadri Cement Industries Ltd (press release)", tier=4, date="2025-05-20",
                    headline="Sahyadri crosses 26% renewable power with new waste heat recovery unit",
                    topics=["energy"], paras=[
        "CHANDRAPUR: Sahyadri Cement Industries Ltd today announced that renewable sources, including waste heat recovery, met 26% of its electricity requirement in FY2025, "
        "helped by the commissioning of a new 18 MW waste heat recovery system at its Chandrapur integrated cement plant.",
        f"\"Waste heat recovery turns heat that would otherwise be lost into clean power, and lowers our dependence on the grid,\" {T.spokes(rng)} said in a statement. "
        "The system captures heat from the kiln and cooler exhaust gases and drives a turbine that supplies the plant.",
        "The company said that it has retired all renewable energy certificates that it purchased for 2024 and will continue to report its renewable share in its annual BRSR.",
        "The Chandrapur plant has a capacity of 6.5 million tonnes of cement a year. The company also operates a cement works at Gulbarga in Karnataka, a grinding unit at Raigad and a limestone mine at Rajura.",
        "About Sahyadri Cement Industries Ltd: Sahyadri Cement is an NSE-listed (NSE: SAHYCEM) cement company headquartered in Pune, Maharashtra."]))

    # ---- Sahyadri 3: safety (2025-08-02)
    s25 = ctx.b("CMP-0002", "FY2025")
    out.append(dict(company_id="CMP-0002", outlet="Western Markets Daily", tier=5, date="2025-08-02",
                    headline="Sahyadri Cement posts steady safety gains, LTIFR at 0.38",
                    topics=["safety", "results"], paras=[
        f"PUNE: Sahyadri Cement Industries Ltd reported a lost-time injury frequency rate of {s25['ltifr']} in {fy_long('FY2025')} and zero fatalities, according to its BRSR filed on {fmt_date(s25['filed_on'])}. "
        "The rate has fallen every year since FY2020, when it stood at 0.52.",
        f"The company recorded {ctx.b('CMP-0002', 'FY2020')['fatalities']} fatalities in FY2020 and {ctx.b('CMP-0002', 'FY2024')['fatalities']} in FY2024. {T.spokes(rng).capitalize()} said that investments in "
        "mine safety, contractor onboarding and a behavioural safety programme had contributed to the improvement.",
        "Cement plants and limestone mines involve heavy mobile equipment, work at height and confined spaces, which makes contractor safety the main risk. Safety experts said "
        "that frequency rates depend on consistent counting of contractor injuries and that the company's rate should be read together with its severity data.",
        f"The company's BRSR also reported turnover of Rs {s25['revenue_cr']:,.0f} crore, a renewable share of {s25['re_pct']}% and reasonable assurance from {s25['assurance_provider']}. "
        f"Women received {s25['women_wage_pct']}% of gross wages in the year.",
        "Sahyadri Cement operates integrated cement plants at Chandrapur and Gulbarga, a grinding unit at Raigad and a limestone mine at Rajura."]))

    # ---- Kaveri 1: ZLD (2024-09-12)
    k24 = ctx.b("CMP-0003", "FY2024")
    out.append(dict(company_id="CMP-0003", outlet="Kongu Business Review", tier=5, date="2024-09-12",
                    headline="Kaveri Threads' Tiruppur unit hits zero liquid discharge milestone",
                    topics=["water", "regulatory"], paras=[
        "TIRUPPUR: Kaveri Threads & Textiles Ltd said that its dyeing and processing unit in Tiruppur has operated at zero liquid discharge since FY2024, and that the Tamil Nadu Pollution Control Board "
        "has confirmed compliance after an inspection of the effluent treatment and reverse osmosis systems.",
        f"The company's BRSR for {fy_long('FY2024')}, filed on {fmt_date(k24['filed_on'])}, reported water discharge of {k24['water_discharge_kl']:,.0f} kL, compared with 210,000 kL in {fy_long('FY2020')}. "
        f"Total withdrawal fell to {k24['water_withdrawal_kl']:,.0f} kL over the same period from 1.48 million kL.",
        "Tiruppur's textile cluster has a history of effluent problems, and zero liquid discharge systems, which recover water and salts from the effluent, have been mandated for dyeing units by the courts. "
        "Cluster operators said that the technology is capital-intensive and that running costs are significant.",
        f"{T.spokes(rng).capitalize()} said that recovered water is reused in dyeing and that salt recovery is sold to authorised users. The unit has a capacity of 60 tonnes of fabric a day.",
        "Kaveri Threads & Textiles, based in Coimbatore, also operates a 220,000-spindle spinning mill and a 40 MW captive wind farm in Tirunelveli district."]))

    # ---- Kaveri 2: PR (2025-06-18)
    out.append(dict(company_id="CMP-0003", outlet="Kaveri Threads & Textiles Ltd (press release)", tier=4, date="2025-06-18",
                    headline="Kaveri Threads reports 64% renewable power, sixth straight year without fatalities",
                    topics=["energy", "safety"], paras=[
        "COIMBATORE: Kaveri Threads & Textiles Ltd announced that renewable sources supplied 64% of its electricity in FY2025, chiefly from its captive wind farm in Tirunelveli, and that the company "
        "recorded zero fatalities in each of the six years from FY2020 to FY2025.",
        f"\"Safety and clean power are not trade-offs for us, they are how we run our mills,\" {T.spokes(rng)} said in a statement. The company said that it will publish detailed figures, with reasonable assurance, in its annual BRSR.",
        "The company said that all renewable energy certificates it purchased for 2024 have been retired in its name, and that it plans to raise its renewable share further through additional wind and solar contracts.",
        "Kaveri Threads operates a spinning mill in Coimbatore, a dyeing and processing unit with zero liquid discharge in Tiruppur and a captive wind farm in Tirunelveli.",
        "About Kaveri Threads & Textiles Ltd: Kaveri Threads is an NSE-listed (NSE: KAVERITEX) textile company headquartered in Coimbatore, Tamil Nadu."]))
    return out


def _tied_demo_extras(ctx: Ctx, rng) -> list[dict]:
    out = []
    add = out.append
    add(T.t_results(ctx, rng, "CMP-0001", "FY2025"))
    add(T.t_digest(ctx, rng, "CMP-0001", "FY2025"))
    add(T.t_facility(ctx, rng, "CMP-0001", ctx.fac["FAC-0004"]))
    add(T.t_msme(ctx, rng, "CMP-0001", "FY2025"))
    add(T.t_results(ctx, rng, "CMP-0002", "FY2025"))
    add(T.t_assurance(ctx, rng, "CMP-0002", "FY2024", "limited", "reasonable"))
    add(T.t_facility(ctx, rng, "CMP-0002", ctx.fac["FAC-0007"]))
    add(T.t_results(ctx, rng, "CMP-0003", "FY2025"))
    add(T.t_women(ctx, rng, "CMP-0003", "FY2025"))
    add(T.t_msme(ctx, rng, "CMP-0003", "FY2025"))
    return out


def _sample(rng, items, k):
    items = list(items)
    if len(items) <= k:
        return items
    return rng.sample(items, k)


def _tied_generated(ctx: Ctx, rng, plan) -> list[dict]:
    out: list[dict] = []
    ids = sorted(c for c in ctx.co if c not in DEMO)
    FYS = ["FY2020", "FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]

    # --- regulatory coverage
    planted_regs = set()
    for p in plan["regulatory_penalty"]:
        for r in ctx.regs_by_c[p["company_id"]]:
            if r["penalty_inr"] and r["facility_id"] == p["facility_id"]:
                planted_regs.add(r["action_id"])
    cand = [r for r in ctx.t["regulatory_actions"] if r["company_id"] not in DEMO and not (r["authority"] == "NGT" and r["order_type"] == "warning")]
    rest = [r for r in cand if r["action_id"] not in planted_regs]
    wts = sorted(rest, key=lambda r: (rng.random() - (0.6 if r["penalty_inr"] else 0) - (0.3 if r["order_type"] in ("closure_direction", "consent_revoked") else 0)))
    chosen = [ctx.regs[a] for a in sorted(planted_regs)] + wts[:max(0, 72 - len(planted_regs))]
    for r in chosen:
        o, a = r["order_type"], r["authority"]
        if a == "SEBI":
            out.append(T.t_sebi(ctx, rng, r))
        elif a == "MoEFCC":
            out.append(T.t_moefcc(ctx, rng, r))
        elif o in ("closure_direction", "consent_revoked"):
            out.append(T.t_closure(ctx, rng, r))
        elif a == "NGT":
            out.append(T.t_ngt(ctx, rng, r))
        elif o in ("show_cause", "warning"):
            out.append(T.t_notice(ctx, rng, r))
        else:
            out.append(T.t_penalty_board(ctx, rng, r))

    # --- OCEMS coverage
    planted = {(p["facility_id"], p["fy"]) for p in plan["ocems"]}
    clusters = []
    for fid, evs in ctx.oce_by_fac.items():
        if ctx.fac[fid]["company_id"] in DEMO:
            continue
        for fy in FYS:
            n = sum(1 for e in evs if T.fy_range(fy)[0].isoformat() <= e["date"] <= T.fy_range(fy)[1].isoformat())
            if n >= 7:
                clusters.append((n, fid, fy))
    clusters.sort(reverse=True)
    pl = [c for c in clusters if (c[1], c[2]) in planted]
    others = [c for c in clusters if (c[1], c[2]) not in planted]
    for n, fid, fy in pl + others[:max(0, 30 - len(pl))]:
        out.append(T.t_ocems(ctx, rng, ctx.fac[fid], fy))

    # --- forest clearing coverage
    fclusters = []
    for f in ctx.t["facilities"]:
        if not f["forest_adjacent"] or f["company_id"] in DEMO:
            continue
        for fy in FYS:
            a, b = T.fy_range(fy)
            al = [x for x in ctx.alerts_by_fac[f["facility_id"]] if x["distance_km"] <= 5 and a.isoformat() <= x["alert_date"] <= b.isoformat()]
            if len(al) >= 5:
                fclusters.append((len(al), f["facility_id"], fy, al))
    fclusters.sort(key=lambda x: -x[0])
    plf = {(p["facility_id"], p["fy"]) for p in plan["land_alerts"]}
    fsel = [x for x in fclusters if (x[1], x[2]) in plf] + [x for x in fclusters if (x[1], x[2]) not in plf][:8]
    for n, fid, fy, al in fsel[:24]:
        out.append(T.t_forest(ctx, rng, ctx.fac[fid], fy, al))

    # --- positive RE
    c1 = [(cid, fy) for cid in ids for fy in FYS[1:] if ctx.b(cid, fy)["re_pct"] - ctx.b(cid, FYS[FYS.index(fy) - 1])["re_pct"] >= 4.0]
    for cid, fy in _sample(rng, c1, 14):
        out.append(T.t_positive_re(ctx, rng, cid, fy))
    # --- intensity
    c2 = [cid for cid in ids if ctx.b(cid, "FY2025")["ghg_intensity"] <= 0.8 * ctx.b(cid, "FY2020")["ghg_intensity"]]
    for cid in _sample(rng, c2, 12):
        out.append(T.t_intensity(ctx, rng, cid))
    # --- assurance upgrades
    rank = {"none": 0, "limited": 1, "reasonable": 2}
    c3 = [(cid, fy, ctx.b(cid, FYS[FYS.index(fy) - 1])["assurance_type"], ctx.b(cid, fy)["assurance_type"]) for cid in ids for fy in FYS[1:]
          if rank[ctx.b(cid, fy)["assurance_type"]] > rank[ctx.b(cid, FYS[FYS.index(fy) - 1])["assurance_type"]] and ctx.b(cid, fy)["assurance_type"] != "none"]
    for x in _sample(rng, c3, 10):
        out.append(T.t_assurance(ctx, rng, *x))
    # --- water discharge
    c4 = [(cid, fy) for cid in ids for fy in FYS[1:] if ctx.b(cid, FYS[FYS.index(fy) - 1])["water_discharge_kl"] > 0
          and ctx.b(cid, fy)["water_discharge_kl"] <= 0.8 * ctx.b(cid, FYS[FYS.index(fy) - 1])["water_discharge_kl"]]
    for x in _sample(rng, c4, 8):
        out.append(T.t_zld(ctx, rng, *x))
    # --- safety
    c5 = [cid for cid in ids if ctx.b(cid, "FY2025")["ltifr"] <= 0.7 * ctx.b(cid, "FY2020")["ltifr"]]
    for cid in _sample(rng, c5, 8):
        out.append(T.t_safety(ctx, rng, cid))
    c6 = [(cid, fy) for cid in ids for fy in FYS[1:] if ctx.b(cid, fy)["fatalities"] >= 2]
    for x in _sample(rng, c6, 8):
        out.append(T.t_fatality(ctx, rng, *x))
    # --- results
    c7 = [(cid, fy) for cid in ids for fy in FYS[2:]]
    for x in _sample(rng, c7, 20):
        out.append(T.t_results(ctx, rng, *x))
    # --- press releases (tier 4)
    for cid, fy in _sample(rng, [(cid, fy) for cid in ids for fy in FYS[2:]], 10):
        out.append(T.t_pr_green(ctx, rng, cid, fy))
    for cid, fy in _sample(rng, [(cid, fy) for cid in ids for fy in FYS[2:] if ctx.b(cid, fy)["assurance_type"] != "none"], 8):
        out.append(T.t_pr_assurance(ctx, rng, cid, fy))
    for cid in _sample(rng, ids, 10):
        out.append(T.t_pr_capacity(ctx, rng, cid, rng.choice(ctx.fac_by_c[cid])))
    for cid, fy in _sample(rng, [(cid, fy) for cid in ids for fy in FYS[2:] if ctx.b(cid, fy)["ltifr"] < ctx.b(cid, FYS[FYS.index(fy) - 1])["ltifr"]], 8):
        out.append(T.t_pr_safety(ctx, rng, cid, fy))
    # --- commentary and features
    for cid in _sample(rng, ids, 12):
        out.append(T.t_analyst(ctx, rng, cid))
    rec_ids = [p["company_id"] for p in plan["rec_unretired"]]
    rec_other = [cid for cid in ids if cid not in rec_ids and any(r["vintage_year"] == 2024 for r in ctx.certs_by_c[cid])]
    for cid in rec_ids[:7] + _sample(rng, rec_other, 3):
        out.append(T.t_rec(ctx, rng, cid))
    for cid, fy in _sample(rng, [(cid, fy) for cid in ids for fy in FYS[2:]], 5):
        out.append(T.t_waste(ctx, rng, cid, fy))
    for cid, fy in _sample(rng, [(cid, fy) for cid in ids if ctx.co[cid]["sector"] in ("IT Services", "Textiles", "Pharmaceuticals", "FMCG") for fy in FYS[3:]], 5):
        out.append(T.t_women(ctx, rng, cid, fy))
    for cid, fy in _sample(rng, [(cid, fy) for cid in ids for fy in FYS[3:]], 5):
        out.append(T.t_msme(ctx, rng, cid, fy))
    for cid, fy in _sample(rng, [(cid, fy) for cid in ids for fy in FYS[2:]], 8):
        out.append(T.t_digest(ctx, rng, cid, fy))
    for cid in _sample(rng, ids, 8):
        out.append(T.t_facility(ctx, rng, cid, rng.choice(ctx.fac_by_c[cid])))
    return [a for a in out if a]


def _general(ctx: Ctx, rng, n_needed: int) -> list[dict]:
    out: list[dict] = []
    FYS = ["FY2020", "FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
    states = sorted({f["state"] for f in ctx.t["facilities"]})
    sectors = sorted({c["sector"] for c in ctx.t["companies"]})
    seen = set()
    makers = [
        lambda: ("roundup", (rng.choice(sectors), rng.choice(FYS[1:])), T.g_roundup),
        lambda: ("policy", (rng.randint(0, 5), rng.randint(2020, 2026)), T.g_policy),
        lambda: ("league", (rng.choice(sectors), rng.choice(FYS[2:])), T.g_league),
        lambda: ("crackdown", (rng.choice(states), rng.choice(FYS[1:])), T.g_crackdown),
        lambda: ("forest", (rng.choice(FYS[1:]),), T.g_forest_report),
        lambda: ("recmkt", (rng.choice([2021, 2022, 2023, 2024]),), T.g_rec_market),
        lambda: ("assur", (rng.choice(FYS[2:]),), T.g_assurance_trend),
        lambda: ("releague", (rng.choice(sectors), rng.choice(FYS[2:])), T.g_re_league),
    ]
    weights = [5, 3, 4, 4, 2, 2, 2, 3]
    tries = 0
    while len(out) < n_needed and tries < 20000:
        tries += 1
        name, args, fn = rng.choices(makers, weights=weights)[0]()
        if (name, args) in seen:
            continue
        a = fn(ctx, rng, *args)
        if a is None:
            continue
        seen.add((name, args))
        out.append(a)
    return out


def gen_news_articles(rng, tables: dict, plan: dict) -> list[dict]:
    ctx = Ctx(tables)
    final: list[dict] = []
    for a in _spec_articles(ctx, rng):
        final.append(finalize(ctx, rng, a, min_w=262, max_w=500))
    for a in _tied_demo_extras(ctx, rng):
        final.append(finalize(ctx, rng, a))
    for a in _tied_generated(ctx, rng, plan):
        final.append(finalize(ctx, rng, a))
    n_gen = TARGET - len(final)
    for a in _general(ctx, rng, n_gen):
        final.append(finalize(None, rng, a, extra_fill=GEN_FILL))
    final.sort(key=lambda r: (r["published_on"], r["headline"]))
    rows = []
    for i, r in enumerate(final, 1):
        assert set(r["topics"]) <= TOPICS_OK, r["topics"]
        assert 250 <= wc(r["body"]) <= 600, (r["headline"], wc(r["body"]))
        rows.append(dict(article_id=f"NWS-{i:05d}", company_id=r["company_id"], outlet=r["outlet"], outlet_tier=r["outlet_tier"],
                         published_on=r["published_on"], headline=r["headline"], body=r["body"], topics=json.dumps(r["topics"])))
    return rows
