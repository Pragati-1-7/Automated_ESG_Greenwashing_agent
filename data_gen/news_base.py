"""
data_gen/news_base.py

Shared infrastructure for the news generator: the data context (indexes over the
generated tables), text helpers, filler paragraphs and the article finaliser.
ALL FICTIONAL.
"""

from __future__ import annotations

import re
from collections import defaultdict

from .world_refs import STATES
from .world_utils import fmt_date, fy_long, inr, wc

BOARD_NAME = {
    "OSPCB": "Odisha State Pollution Control Board", "MPCB": "Maharashtra Pollution Control Board",
    "KSPCB": "Karnataka State Pollution Control Board", "TNPCB": "Tamil Nadu Pollution Control Board",
    "GPCB": "Gujarat Pollution Control Board", "UPPCB": "Uttar Pradesh Pollution Control Board",
    "JSPCB": "Jharkhand State Pollution Control Board", "CECB": "Chhattisgarh Environment Conservation Board",
    "MPPCB": "Madhya Pradesh Pollution Control Board", "RSPCB": "Rajasthan State Pollution Control Board",
    "WBPCB": "West Bengal Pollution Control Board", "TSPCB": "Telangana State Pollution Control Board",
    "APPCB": "Andhra Pradesh Pollution Control Board", "HSPCB": "Haryana State Pollution Control Board",
    "PPCB": "Punjab Pollution Control Board", "DPCC": "Delhi Pollution Control Committee",
    "UKPCB": "Uttarakhand Pollution Control Board", "HPSPCB": "Himachal Pradesh State Pollution Control Board",
    "GSPCB": "Goa State Pollution Control Board",
}
ZONE_CITY = {"EZ": "Kolkata", "WZ": "Pune", "SZ": "Chennai", "CZ": "Bhopal", "PB": "New Delhi"}
ZONE_NAME = {"EZ": "Eastern Zone", "WZ": "Western Zone", "SZ": "Southern Zone", "CZ": "Central Zone", "PB": "Principal Bench"}

SECTOR_PHRASE = {"Steel": "steel and metals", "Cement": "cement", "Power": "power generation", "Textiles": "textiles and apparel",
                 "FMCG": "fast-moving consumer goods", "Chemicals": "chemicals", "Automotive": "automotive components",
                 "Pharmaceuticals": "pharmaceuticals", "Mining": "mining and minerals", "IT Services": "information technology services"}

SECTOR_CTX = {
    "Steel": ["India is the world's second-largest producer of crude steel, and the sector is among the biggest industrial sources of greenhouse gases in the country, with blast furnace and coal-based direct reduced iron routes accounting for most of its footprint.",
              "Steelmakers are investing in scrap-based electric arc furnaces, waste heat recovery and renewable power contracts to bring down emission intensity, though capital-intensive options such as green hydrogen remain at the pilot stage.",
              "Analysts say that the sector's margins are sensitive to coking coal prices, which makes the economics of decarbonisation projects harder to pin down."],
    "Cement": ["Cement is a hard-to-abate sector because roughly half of its emissions come from the calcination of limestone, which cannot be eliminated by switching fuels alone.",
               "Producers have been raising the share of blended cements, using alternative fuels and installing waste heat recovery systems to bring down their carbon footprint.",
               "Capacity additions in the sector are concentrated in central and southern India, where limestone reserves and growing demand sit close together."],
    "Power": ["India's power sector is undergoing a slow shift as renewable capacity additions outpace coal, but thermal plants still supply the bulk of electricity and remain the largest single source of the country's emissions.",
              "Operators of coal-fired plants face tighter norms on particulate matter, sulphur dioxide and fly ash utilisation, while developers of solar and wind parks face land, transmission and offtake challenges.",
              "Investors increasingly look at plant-level emission data and ash utilisation records alongside regulated returns."],
    "Textiles": ["Textile and apparel makers face pressure from global buyers to cut water use, effluent and emissions, and many have moved towards zero liquid discharge systems in processing clusters.",
                 "The sector is labour-intensive and has one of the highest shares of women in the workforce among Indian industries.",
                 "Captive wind and solar power have become a common route for mills to lower electricity costs and the carbon footprint of their operations."],
    "FMCG": ["Packaged goods companies are under scrutiny for plastic packaging, water use and the emissions embedded in their agricultural supply chains.",
             "Most large players have set renewable electricity and packaging targets, and investors are asking for third-party assurance on the underlying numbers.",
             "Distribution networks and contract manufacturers make the sector's emissions harder to measure than those of a single-site industrial producer."],
    "Chemicals": ["The chemicals sector combines high energy use with the handling of hazardous inputs, which makes effluent treatment and air emission control central to its regulatory risk.",
                  "Clusters in Gujarat, Maharashtra and Andhra Pradesh have seen repeated action by pollution control boards over effluent discharge.",
                  "Specialty chemicals makers argue that stricter compliance is a cost of doing business with global customers who audit their sites."],
    "Automotive": ["Automotive suppliers are being asked by global carmakers to report emissions and shift to renewable electricity, since most of their footprint is purchased power.",
                   "Foundry and forging units remain the most emission-intensive parts of the supply chain, with particulate matter a recurring compliance concern.",
                   "The shift to electric vehicles is pushing component makers to rebuild their product portfolios while keeping an eye on costs."],
    "Pharmaceuticals": ["Drugmakers are being pushed to disclose effluent and solvent management practices, particularly at active pharmaceutical ingredient plants.",
                        "Regulators abroad and in India have tightened scrutiny of effluent from bulk drug clusters, and large buyers audit suppliers on environmental grounds.",
                        "Renewable power purchases have become the easiest lever for formulation plants to reduce their Scope 2 emissions."],
    "Mining": ["Mining companies operate under some of the strictest environmental and forest clearance conditions in the country, and their lease areas often sit close to protected or reserved forests.",
               "Satellite-based alert systems have given communities and researchers new tools to track vegetation loss near mining leases in near real time.",
               "Rehabilitation, overburden management and dust suppression remain the main compliance flashpoints."],
    "IT Services": ["Technology services companies have among the lowest direct emissions per rupee of revenue, so their climate disclosures centre on purchased electricity and business travel.",
                    "Most large players have committed to renewable electricity targets and rely on certificates and power purchase agreements to meet them.",
                    "Investors treat governance, diversity and data security disclosures as the more material parts of the sector's BRSR filings."],
}

REG_CTX = [
    "Environmental enforcement in India rests on the Water and Air Acts, the Environment (Protection) Act and the polluter pays principle, which the National Green Tribunal has applied to order compensation even where no prosecution has been filed.",
    "State pollution control boards have been stepping up the use of online continuous emission and effluent monitoring systems, whose data is now visible to the Central Pollution Control Board in near real time.",
    "Lawyers who track environmental cases say that compensation orders are increasingly based on a formula linked to the scale of the unit and the duration of the violation, which makes penalties more predictable than in the past.",
]
ESG_CTX_GENERIC = [
    "SEBI's Business Responsibility and Sustainability Report framework requires the top listed companies to disclose a core set of indicators and, in phases, to obtain external assurance on them, which has made company-level numbers easier to compare.",
    "Investors and rating agencies have begun to cross-check company disclosures against regulatory orders, satellite data and certificate registries, rather than relying on sustainability reports alone.",
    "Analysts caution that headline sustainability claims are best read alongside the filed numbers, since the choice of baseline year and the use of intensity rather than absolute figures can change the picture considerably.",
]
SPOKES = ["a company spokesperson", "the company's head of environment, health and safety", "the company's chief sustainability officer",
          "a senior company executive", "the company's corporate communications team"]


def poss(name: str) -> str:
    return name + ("'" if name.endswith("s") else "'s")


def a_an(phrase: str) -> str:
    return "an" if phrase[0].lower() in "aeiou" else "a"


def join_and(items: list[str]) -> str:
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def short_issue(issue: str) -> str:
    keys = [("Business Responsibility Report", "business responsibility disclosure lapses"), ("flue gas", "FGD delays"), ("ash", "fly ash lapses"), ("dust", "fugitive dust"), ("emission", "stack emissions"),
            ("particulate", "stack emissions"), ("air pollution control", "air pollution lapses"),
            ("zero liquid", "effluent norms"), ("effluent", "effluent discharge"), ("lease boundary", "mining violations"),
            ("trees", "tree felling"), ("overburden", "overburden dumping"), ("environmental clearance limit", "excess extraction"),
            ("groundwater", "groundwater extraction"), ("hazardous", "hazardous waste handling"), ("clearance", "clearance violations"),
            ("consent", "consent violations"), ("BRSR", "BRSR disclosure lapses"), ("Regulation", "disclosure lapses")]
    for k, v in keys:
        if k in issue:
            return v
    return "pollution norms"


def issue_of(summary: str) -> str:
    m = re.search(r" for (.+?) at ", summary) or re.search(r" for (.+?)[.;]", summary) or re.search(r" over (.+?)[.;]", summary)
    return m.group(1) if m else "alleged violations of environmental norms"


class Ctx:
    """Indexes over the generated tables used by the article templates."""

    def __init__(self, tables: dict):
        self.t = tables
        self.co = {c["company_id"]: c for c in tables["companies"]}
        self.fac = {f["facility_id"]: f for f in tables["facilities"]}
        self.fac_by_c = defaultdict(list)
        for f in tables["facilities"]:
            self.fac_by_c[f["company_id"]].append(f)
        self.brsr = {(b["company_id"], b["fy"]): b for b in tables["brsr_filings"]}
        self.regs = {r["action_id"]: r for r in tables["regulatory_actions"]}
        self.regs_by_c = defaultdict(list)
        for r in tables["regulatory_actions"]:
            self.regs_by_c[r["company_id"]].append(r)
        self.oce_by_fac = defaultdict(list)
        for e in tables["ocems_exceedances"]:
            self.oce_by_fac[e["facility_id"]].append(e)
        self.certs_by_c = defaultdict(list)
        for r in tables["re_certificates"]:
            self.certs_by_c[r["company_id"]].append(r)
        self.audit = {(a["company_id"], a["fy"]): a for a in tables["audited_reports"]}
        self.alerts_by_fac = defaultdict(list)
        for a in tables["land_alerts"]:
            if a["nearest_facility_id"]:
                self.alerts_by_fac[a["nearest_facility_id"]].append(a)

    def latest(self, cid):
        return self.brsr[(cid, "FY2025")]

    def asof(self, cid, iso):
        """Most recent BRSR filing already filed on or before `iso` (None if none)."""
        rows = [self.brsr[(cid, fy)] for fy in ("FY2020", "FY2021", "FY2022", "FY2023", "FY2024", "FY2025")
                if self.brsr[(cid, fy)]["filed_on"] <= iso]
        return rows[-1] if rows else None

    def b(self, cid, fy):
        return self.brsr[(cid, fy)]

    def states(self, cid):
        return sorted({f["state"] for f in self.fac_by_c[cid]})


def dateline(c, fac=None) -> str:
    city = (fac["district"] if fac and fac.get("district") else c["hq_city"]).upper()
    return f"{city}: "


def background_para(ctx: Ctx, c, b) -> str:
    facs = ctx.fac_by_c[c["company_id"]]
    lst = ("Its shares trade under the listing " + c["listing"] + ".") if c["listing"] != "Unlisted" else \
        "The company is unlisted but publishes a voluntary BRSR."
    return (f"{c['name']} is {a_an(SECTOR_PHRASE[c['sector']])} {SECTOR_PHRASE[c['sector']]} company headquartered in {c['hq_city']}, {c['hq_state']}. "
            f"It reported turnover of Rs {b['revenue_cr']:,.0f} crore in {fy_long(b['fy'])} and operates {len(facs)} facilities "
            f"across {join_and(ctx.states(c['company_id']))}. {lst}")


def esg_ctx_para(ctx: Ctx, c, b) -> str:
    ass = {"none": "The disclosure was not externally assured.", "limited": f"The disclosure carried limited assurance from {b['assurance_provider']}.",
           "reasonable": f"The disclosure carried reasonable assurance from {b['assurance_provider']}."}[b["assurance_type"]]
    return (f"In its BRSR for {fy_long(b['fy'])}, {c['short_name']} reported Scope 1 emissions of {b['scope1_tco2e']:,.0f} tCO2e, "
            f"Scope 2 emissions of {b['scope2_tco2e']:,.0f} tCO2e and a GHG intensity of {b['ghg_intensity']} tCO2e per Rs crore of turnover, "
            f"with {b['re_pct']}% of its electricity from renewable sources. {ass}")


def finalize(ctx: Ctx | None, rng, a: dict, extra_fill: list[str] | None = None, min_w: int | None = None, max_w: int = 585) -> dict:
    """Pad with context paragraphs until the body reaches min_w words; trim if above max_w."""
    min_w = min_w if min_w is not None else rng.randint(300, 400)
    paras = list(a["paras"])
    fills: list[str] = []
    c = ctx.co.get(a.get("company_id")) if (ctx and a.get("company_id")) else None
    if extra_fill:
        fills.extend(extra_fill)
    if c is not None:
        sec = list(SECTOR_CTX[c["sector"]])
        rng.shuffle(sec)
        fills.append(sec[0])
        b = ctx.asof(c["company_id"], a["date"])
        if b is not None:
            body_so_far = " ".join(paras)
            if f"{b['scope1_tco2e']:,.0f}" not in body_so_far:
                fills.append(esg_ctx_para(ctx, c, b))
            if f"{b['revenue_cr']:,.0f}" not in body_so_far:
                fills.append(background_para(ctx, c, b))
        fills.append(rng.choice(REG_CTX))
        fills.extend(sec[1:])
    fills.extend(ESG_CTX_GENERIC)
    i = 0
    while sum(wc(p) for p in paras) < min_w and i < len(fills):
        if fills[i] not in paras:
            paras.append(fills[i])
        i += 1
    while sum(wc(p) for p in paras) > max_w and len(paras) > 3:
        paras.pop()
    out = dict(company_id=a.get("company_id"), outlet=a["outlet"], outlet_tier=a.get("tier", 5), published_on=a["date"],
               headline=a["headline"], body="\n\n".join(paras), topics=a["topics"])
    return out


def amount_text(x: float) -> str:
    return inr(x)
