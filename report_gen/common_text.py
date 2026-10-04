"""Shared building blocks: GRI index, glossary, disclaimer, assurance letter, fact tables."""
from __future__ import annotations
from . import layout as L

# (code, title, topic key). Topic keys are resolved to section numbers by each report.
GRI = [
    ("2-1", "Organizational details", "glance"), ("2-2", "Entities included in sustainability reporting", "about"),
    ("2-3", "Reporting period, frequency and contact point", "about"), ("2-4", "Restatements of information", "about"),
    ("2-5", "External assurance", "assurance"), ("2-6", "Activities, value chain and other business relationships", "glance"),
    ("2-7", "Employees", "people"), ("2-8", "Workers who are not employees", "people"),
    ("2-9", "Governance structure and composition", "governance"), ("2-10", "Nomination and selection of the highest governance body", "governance"),
    ("2-11", "Chair of the highest governance body", "governance"), ("2-12", "Role of the highest governance body in overseeing impacts", "governance"),
    ("2-13", "Delegation of responsibility for managing impacts", "governance"), ("2-14", "Role of the highest governance body in sustainability reporting", "governance"),
    ("2-15", "Conflicts of interest", "governance"), ("2-16", "Communication of critical concerns", "governance"),
    ("2-17", "Collective knowledge of the highest governance body", "governance"), ("2-18", "Evaluation of the performance of the highest governance body", "governance"),
    ("2-19", "Remuneration policies", "governance"), ("2-20", "Process to determine remuneration", "governance"),
    ("2-22", "Statement on sustainable development strategy", "message"), ("2-23", "Policy commitments", "governance"),
    ("2-24", "Embedding policy commitments", "governance"), ("2-25", "Processes to remediate negative impacts", "governance"),
    ("2-26", "Mechanisms for seeking advice and raising concerns", "governance"), ("2-27", "Compliance with laws and regulations", "air"),
    ("2-28", "Membership associations", "governance"), ("2-29", "Approach to stakeholder engagement", "materiality"),
    ("2-30", "Collective bargaining agreements", "people"), ("3-1", "Process to determine material topics", "materiality"),
    ("3-2", "List of material topics", "materiality"), ("3-3", "Management of material topics", "strategy"),
    ("201-1", "Direct economic value generated and distributed", "glance"), ("201-2", "Financial implications and other risks and opportunities due to climate change", "climate"),
    ("203-1", "Infrastructure investments and services supported", "community"), ("203-2", "Significant indirect economic impacts", "community"),
    ("204-1", "Proportion of spending on local suppliers", "supply"), ("205-1", "Operations assessed for risks related to corruption", "governance"),
    ("205-2", "Communication and training about anti-corruption policies", "governance"), ("205-3", "Confirmed incidents of corruption and actions taken", "governance"),
    ("206-1", "Legal actions for anti-competitive behaviour", "governance"), ("301-1", "Materials used by weight or volume", "waste"),
    ("301-2", "Recycled input materials used", "waste"), ("302-1", "Energy consumption within the organization", "climate"),
    ("302-3", "Energy intensity", "climate"), ("302-4", "Reduction of energy consumption", "climate"),
    ("303-1", "Interactions with water as a shared resource", "water"), ("303-2", "Management of water discharge-related impacts", "water"),
    ("303-3", "Water withdrawal", "water"), ("303-4", "Water discharge", "water"), ("303-5", "Water consumption", "water"),
    ("304-1", "Operational sites in or adjacent to protected areas", "bio"), ("304-2", "Significant impacts of activities on biodiversity", "bio"),
    ("304-3", "Habitats protected or restored", "bio"), ("304-4", "IUCN Red List species in areas affected by operations", "bio"),
    ("305-1", "Direct (Scope 1) GHG emissions", "climate"), ("305-2", "Energy indirect (Scope 2) GHG emissions", "climate"),
    ("305-3", "Other indirect (Scope 3) GHG emissions", "supply"), ("305-4", "GHG emissions intensity", "climate"),
    ("305-5", "Reduction of GHG emissions", "climate"), ("305-7", "Nitrogen oxides, sulfur oxides and other significant air emissions", "air"),
    ("306-1", "Waste generation and significant waste-related impacts", "waste"), ("306-2", "Management of significant waste-related impacts", "waste"),
    ("306-3", "Waste generated", "waste"), ("306-4", "Waste diverted from disposal", "waste"), ("306-5", "Waste directed to disposal", "waste"),
    ("308-1", "New suppliers screened using environmental criteria", "supply"), ("401-1", "New employee hires and employee turnover", "people"),
    ("401-2", "Benefits provided to full-time employees", "people"), ("401-3", "Parental leave", "di"),
    ("403-1", "Occupational health and safety management system", "people"), ("403-2", "Hazard identification, risk assessment and incident investigation", "people"),
    ("403-3", "Occupational health services", "people"), ("403-4", "Worker participation, consultation and communication on OHS", "people"),
    ("403-5", "Worker training on occupational health and safety", "people"), ("403-6", "Promotion of worker health", "people"),
    ("403-7", "Prevention and mitigation of OHS impacts linked by business relationships", "people"), ("403-8", "Workers covered by an OHS management system", "people"),
    ("403-9", "Work-related injuries", "people"), ("403-10", "Work-related ill health", "people"),
    ("404-1", "Average hours of training per year per employee", "people"), ("404-2", "Programs for upgrading employee skills", "people"),
    ("405-1", "Diversity of governance bodies and employees", "di"), ("405-2", "Ratio of basic salary and remuneration of women to men", "di"),
    ("406-1", "Incidents of discrimination and corrective actions taken", "di"), ("407-1", "Operations and suppliers at risk for freedom of association", "supply"),
    ("408-1", "Operations and suppliers at risk for child labour", "supply"), ("409-1", "Operations and suppliers at risk for forced labour", "supply"),
    ("413-1", "Operations with local community engagement", "community"), ("413-2", "Operations with significant negative impacts on local communities", "community"),
    ("414-1", "New suppliers screened using social criteria", "supply"), ("415-1", "Political contributions", "governance"),
    ("416-1", "Assessment of health and safety impacts of product and service categories", "glance"),
    ("417-1", "Requirements for product and service information and labelling", "glance"),
    ("418-1", "Substantiated complaints concerning breaches of customer privacy", "governance"),
]


def gri_index(sec: dict, intro: str, partial=(), withheld=(), withheld_text="Refer statutory BRSR filing") -> str:
    """sec: topic key -> section number string. withheld: GRI codes pointed to the BRSR filing instead."""
    rows = []
    for code, title, topic in GRI:
        if code in withheld:
            loc, stat = withheld_text, '<span class="tag">Cross-reference</span>'
        elif topic not in sec:
            loc, stat = "Not applicable to our operations", '<span class="tag">Omitted</span>'
        elif code in partial:
            loc, stat = f"Section {sec[topic]}", '<span class="tag">Partial</span>'
        else:
            loc, stat = f"Section {sec[topic]}", '<span class="tag">Reported</span>'
        rows.append((code, title, loc, stat))
    tbl = L.table("GRI content index", ["Disclosure", "Title", "Location in this report", "Status"], rows,
                  src="GRI 1: Foundation 2021, GRI 2: General Disclosures 2021 and GRI 3: Material Topics 2021 apply to all rows. "
                      "Sector-specific standards are not yet available for our sector.", aligns=["l", "l", "l", "l"])
    tbl = tbl.replace('class="span tbl"', 'class="span tbl gri-t"')
    return f'<p style="text-align:left">{intro}</p>' + tbl


def glossary(terms: dict) -> str:
    items = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in sorted(terms.items(), key=lambda kv: kv[0].lower()))
    return f'<dl class="glos">{items}</dl>'


BASE_TERMS = {
    "BRSR": "Business Responsibility and Sustainability Report, the disclosure format prescribed by SEBI for listed entities in India.",
    "BRSR Core": "The subset of BRSR indicators, across nine ESG attributes, that is subject to assurance and value chain disclosure.",
    "CPCB": "Central Pollution Control Board, the statutory body under the Ministry of Environment, Forest and Climate Change.",
    "CSR": "Corporate social responsibility, spending governed by Section 135 of the Companies Act, 2013.",
    "ESG": "Environmental, social and governance.",
    "FY2025": "The financial year from 1 April 2024 to 31 March 2025.",
    "GHG": "Greenhouse gases, expressed as carbon dioxide equivalent (tCO2e) using IPCC AR6 warming potentials unless noted.",
    "GRI": "Global Reporting Initiative; this report is prepared with reference to the GRI Standards 2021.",
    "Lakh": "A unit of 100,000. One crore equals 100 lakh, or 10 million.",
    "LTIFR": "Lost Time Injury Frequency Rate, the number of lost-time injuries per million person-hours worked.",
    "MSME": "Micro, small and medium enterprise, as classified under the MSMED Act, 2006.",
    "MTPA": "Million tonnes per annum.",
    "REC": "Renewable energy certificate, a tradable instrument representing one megawatt-hour of renewable generation.",
    "SEBI": "Securities and Exchange Board of India.",
    "Scope 1": "Direct GHG emissions from sources owned or controlled by the company.",
    "Scope 2": "Indirect GHG emissions from the generation of purchased electricity, steam, heating or cooling.",
    "Scope 3": "All other indirect GHG emissions in the value chain, upstream and downstream.",
    "TCFD": "Task Force on Climate-related Financial Disclosures, whose recommendations structure our climate reporting.",
    "tCO2e": "Tonnes of carbon dioxide equivalent.",
    "ZLD": "Zero liquid discharge, a design in which treated effluent is fully recovered and reused.",
    "Value chain": "The activities, actors and flows upstream and downstream of a company's own operations.",
    "Reasonable assurance": "A higher level of assurance, expressed as a positive-form opinion, with more extensive testing than limited assurance.",
    "Limited assurance": "A lower level of assurance, expressed as a negative-form conclusion, based on less extensive procedures.",
}


def forward_looking(ctx) -> str:
    n = ctx.name
    return (
        L.p(f"This report contains statements about {n}'s plans, objectives, strategies, expectations and aspirations that are forward-looking in nature. "
            "Such statements are not guarantees of future performance. They reflect management's current views and assumptions as of the date of publication and are "
            "subject to risks, uncertainties and changes in circumstances that are difficult to predict. Words such as aim, expect, intend, plan, will, "
            "target and ambition identify many of these statements.")
        + L.p("Actual outcomes may differ materially from those expressed or implied, because of factors that include changes in government policy and regulation, "
              "movements in commodity, power and fuel prices, availability of capital and technology, climatic and weather events, "
              "project approvals and construction timelines, counterparty performance, litigation, and general economic conditions in India and the markets we serve.")
        + L.p("Data in this report has been compiled from internal systems, plant records and third-party sources. Where estimates or methodologies have been used, we have tried to say so in the notes to the relevant tables. "
              "Figures may not add up because of rounding. Past performance is not a guide to future results. Nothing in this report constitutes an offer, "
              "invitation or recommendation to buy or sell securities, and readers should not rely on it as investment, legal or tax advice.")
        + L.p(f"{n} undertakes no obligation to update any forward-looking statement, except as required by applicable law or by the Securities and Exchange Board of India (Listing Obligations and Disclosure Requirements) Regulations, 2015, as amended. "
              "This publication, the company, its facilities, people, events and data are entirely fictional and have been created for an academic demonstration of ESG claim verification.")
    )


def assurance_letter(ctx, provider: str, partner: str, firm_reg: str, city: str, date: str, scope_note: str) -> str:
    n = ctx.name
    return f'''<div class="assur"><h2>Independent Assurer's Reasonable Assurance Report</h2>
<p><b>To the Board of Directors of {n}</b></p>
<p>We, {provider}, were engaged by the management of {n} (the "Company") to perform a reasonable assurance engagement on the selected BRSR Core indicators set out in the Company's report for the year ended 31 March 2025 (the "Subject Matter Information").</p>
<p><b>Management's responsibility.</b> The Company's management is responsible for the preparation of the Subject Matter Information in accordance with the SEBI BRSR Core framework and the criteria described in the reporting boundary, and for the design and maintenance of internal controls relevant to that preparation.</p>
<p><b>Our responsibility.</b> Our responsibility is to express a reasonable assurance opinion on the Subject Matter Information based on our work, which we performed in accordance with the Standard on Assurance Engagements (SAE) 3000 (Revised) and, for greenhouse gas indicators, SAE 3410, issued by the Institute of Chartered Accountants of India. {scope_note}</p>
<p><b>Procedures.</b> Our procedures included inquiries of personnel responsible for data collection, site visits to selected facilities, inspection of source records and calculation workbooks, re-performance of calculations on a sample basis, and evaluation of the appropriateness of the reporting criteria and the disclosures in this report.</p>
<p><b>Opinion.</b> In our opinion, the Subject Matter Information for the year ended 31 March 2025 has been prepared, in all material respects, in accordance with the applicable criteria.</p>
<p><b>Independence and quality control.</b> We have complied with the independence and other ethical requirements of the Code of Ethics issued by the Institute of Chartered Accountants of India and apply a system of quality management that includes documented policies on ethical requirements and professional standards.</p>
<p style="margin-top:6mm"><b>{provider}</b><br>Chartered Accountants, Firm Registration No. {firm_reg}<br>{partner}, Partner<br>{city}, {date}</p></div>'''


def about_frameworks_callout() -> str:
    return L.callout("Frameworks and standards applied", items=[
        "<b>SEBI BRSR and BRSR Core</b>, as per the circulars applicable to the top 1,000 listed entities by market capitalisation.",
        "<b>GRI Standards 2021</b>, in reference to GRI 1, GRI 2 and GRI 3 and the topic standards listed in the content index.",
        "<b>TCFD</b> recommendations on governance, strategy, risk management, and metrics and targets.",
        "National Guidelines on Responsible Business Conduct (NGRBC) and the nine principles they set out.",
        "Greenhouse Gas Protocol Corporate Standard and Scope 2 Guidance.",
    ])


def facilities_table(ctx) -> str:
    rows = []
    for i, f in enumerate(ctx.co["facilities"], 1):
        cap = f"{f['capacity_value']:,} {f['capacity_unit']}" if isinstance(f["capacity_value"], int) else f"{f['capacity_value']} {f['capacity_unit']}"
        rows.append((str(i), f["name"], f["type"], f"{f['district']}, {f['state']}", f"{f['lat']:.2f} N, {f['lon']:.2f} E", cap))
    return L.table("Operating facilities", ["#", "Facility", "Type", "Location", "Coordinates", "Rated capacity"], rows,
                   src="Coordinates are approximate and rounded to two decimals. Capacities are nameplate figures as at 31 March 2025.",
                   aligns=["l", "l", "l", "l", "l", "l"])
