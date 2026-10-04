"""Kaveri Threads & Textiles Ltd: honest profile. BRSR-style tables use TRUE values for the metrics whose
claims align (Scope 1, renewable share, water discharge/withdrawal, women wage share, LTIFR, fatalities,
assurance) plus revenue."""
from __future__ import annotations
from . import layout as L, charts, common_text as C, data

ORDER = ["about", "message", "glance", "materiality", "strategy", "climate", "water", "waste", "bio", "air",
         "people", "di", "community", "governance", "supply", "brsr", "assurance", "letter", "gri", "glossary", "disclaimer"]
TOC_GROUPS = [{"at": "01", "label": "Introduction"}, {"at": "06", "label": "Environment"}, {"at": "11", "label": "Social"},
              {"at": "14", "label": "Governance and value chain"}, {"at": "16", "label": "Disclosures, assurance and reference"}]


def make_charts(ctx):
    pal, t = ctx.pal, ctx.co["true"]
    charts.bar_chart(ctx.path("revenue.png"), ctx.fy, t["revenue_cr"], pal, ylabel="Rs crore", h=2.2)
    charts.bar_chart(ctx.path("scope1.png"), ctx.fy, [round(x / 1000, 1) for x in t["scope1_tco2e"]], pal, ylabel="thousand tCO2e", fmt="{:.1f}", h=2.3)
    charts.line_chart(ctx.path("re.png"), ctx.fy, {"Renewable share of electricity (%)": t["re_pct"]}, pal, ylabel="% of electricity", fmt="{:.0f}", h=2.3)
    charts.bar_chart(ctx.path("withdrawal.png"), ctx.fy, [round(x / 1e6, 2) for x in t["water_withdrawal_kl"]], pal, ylabel="million kL", fmt="{:.2f}", h=1.8)
    charts.line_chart(ctx.path("discharge.png"), ctx.fy, {"Liquid discharge (thousand kL)": [round(x / 1000) for x in t["water_discharge_kl"]]}, pal, ylabel="thousand kL", fmt="{:.0f}", h=1.8)
    charts.line_chart(ctx.path("ltifr.png"), ctx.fy, {"LTIFR (per million person-hours)": t["ltifr"]}, pal, ylabel="rate", fmt="{:.2f}", h=2.2)
    charts.line_chart(ctx.path("women.png"), ctx.fy, {"Women's share of gross wages (%)": t["women_wage_pct"]}, pal, ylabel="% of gross wages", fmt="{:.1f}", h=2.2)
    charts.materiality(ctx.path("materiality.png"), [
        ("Renewable energy and climate", 8.8, 8.5, 4), ("Water and effluent", 8.4, 9.0, 4), ("Chemicals management", 7.2, 8.0, 3),
        ("Worker safety and wellbeing", 8.6, 9.2, 4), ("Fair wages and conditions", 7.6, 8.8, 3), ("Women's participation", 6.8, 7.8, 3),
        ("Cotton sourcing and traceability", 7.9, 7.0, 3), ("Waste and circular fibres", 6.4, 6.6, 2), ("Product safety", 6.0, 6.0, 2),
        ("Community livelihoods", 5.4, 7.2, 2), ("Ethics and transparency", 7.5, 6.5, 2), ("Innovation and digital", 5.8, 4.8, 1)], pal)
    charts.timeline(ctx.path("timeline.png"), [
        ("FY2021 to FY2024", "Foundation", ["Captive wind capacity", "Zero liquid discharge at Tiruppur", "Safety systems overhaul"]),
        ("FY2025 to FY2027", "Deepen", ["Efficiency in spinning", "Solar rooftops", "Cotton traceability"]),
        ("FY2028 to FY2030", "Complete", ["Full renewable supply", "Circular fibre scale-up", "Supplier wage programme"]),
        ("Beyond FY2030", "Regenerate", ["Regenerative cotton", "Closed-loop textiles"]),
    ], pal)
    charts.hbar_chart(ctx.path("csr.png"), ["Education and skilling", "Women's livelihoods", "Healthcare", "Water and sanitation", "Environment", "Culture and sport"],
                      [5.5, 4.0, 3.5, 2.5, 1.5, 0.8], pal, xlabel="Rs crore, FY2025", fmt="{:.1f}", h=2.3)


def chapters(ctx):
    sec = {k: f"{i + 1:02d}" for i, k in enumerate(ORDER)}
    ctx.back_text = ("<p>Sustainability Office<br>Kaveri Mills Campus, Avinashi Road, Coimbatore 641 018, Tamil Nadu</p>"
                     "<p>impact@kaverithreads.example | www.kaverithreads.example</p><p>CIN L17111TZ1985PLC001647 | NSE: KAVERITEX</p>")
    return [globals()[f"ch_{k}"](ctx, sec) for k in ORDER]


def ch(title, subtitle, body, **kw):
    return {"title": title, "subtitle": subtitle, "body": body, **kw}


def ch_about(ctx, sec):
    b = (
        L.p(f"This BRSR and Impact Report presents the environmental, social and governance performance of {ctx.name} for the financial year from 1 April 2024 to 31 March 2025. We have written it for the people who weigh our yarn and fabric on a scale of trust: brand buyers, investors, lenders, our own colleagues and the communities of western Tamil Nadu.")
        + L.h3("Boundary")
        + L.p("The report covers our Coimbatore Spinning Mill, the Tiruppur Processing Unit, the Tirunelveli Captive Wind Farm and the corporate office in Coimbatore. We report on the basis of operational control. Cotton farmers, ginners, garmenting customers and other value chain partners are outside the boundary, though we describe our engagement with them in the supply chain section.")
        + L.p("Financial data is taken from our audited financial statements. Environmental and social data comes from plant records, utility meters, payroll and incident systems. Where we use estimates, we say so. Earlier-year figures are unchanged unless noted.")
        + C.about_frameworks_callout()
        + L.h3("A note on how we write")
        + L.p("We have tried to keep language plain and to show both progress and unfinished business. Where a topic is important but we do not yet measure it well, we say so rather than leave it out.")
        + L.pull("If a number matters, it should be possible to trace it back to a meter, a payslip or a register.", "Head of Sustainability")
        + L.p("The Board approved this report on 26 May 2025. A glossary and a GRI content index at the end help readers find their way, and the contact details on the back cover are open to questions at any time.")
        + L.notes(["BRSR Core indicators for FY2025 were reviewed by the Audit Committee before filing.", "Rs 1 crore equals 10 million rupees."])
    )
    return ch("About this report", "Boundary, period and frameworks", b)


def ch_message(ctx, sec):
    b = (
        L.p("Dear friends,")
        + '<p class="dropcap">' + "A cotton boll is picked in a field in Maharashtra or Telangana, spun into yarn in Coimbatore, dyed and finished in Tiruppur, cut and stitched somewhere else, and finally worn by someone we shall never meet. Across that long journey, there are thousands of chances to do right by people and by nature, and equally many to look away." + '</p>'
        + L.p("Kaveri Threads was founded forty years ago by a small group of mill engineers and weavers who believed that good cloth and good conduct belonged together. Our founders would find the machines and the markets unrecognisable today, but I hope they would recognise the values.")
        + L.stmt(f"{ctx.claim('KAV-12')} It shows in how we plan our energy, treat our water, protect our workers and share our results, and the pages that follow try to give evidence for that statement rather than simply repeat it.")
        + L.p("This year, our wind farm continued to be the backbone of our power supply, our Tiruppur unit completed another full year operating without releasing treated effluent, and our teams across all three sites kept up a steady focus on safety. We also took a hard look at the parts of our value chain where we have less visibility, including farm-level practices and wages in our supplier base.")
        + L.pull("The honest report is the useful one. We would rather be corrected than admired.", "Managing Director")
        + L.p("There is more to do. Cotton remains a thirsty crop, dyeing remains a chemical process, and fashion remains a fast business. We shall keep investing in cleaner technology, in the skills of our people, and in partnerships with farmers and customers who share our long view.")
        + L.p("My thanks to our employees, our customers, our bankers and shareholders, and to the communities of Coimbatore, Tiruppur and Tirunelveli for their support.")
        + '<div class="sign">With regards,<b>Lakshmi Narayanan</b><span>Managing Director<br>Coimbatore, 26 May 2025</span></div>'
        + L.callout("Year in brief", items=["Captive wind farm supported the bulk of our electricity needs", "Another full year of zero liquid discharge at Tiruppur", "Safety performance maintained with no fatalities", "Cotton traceability pilot extended to more farmer groups"])
    )
    return ch("Message from the Managing Director", "Woven with care", b)


def ch_glance(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.kpis([("Rs 3,580 crore", "Revenue, FY2025"), ("220,000", "Spindles installed"), ("60 tonnes/day", "Fabric processing capacity"), ("40 MW", "Captive wind capacity")])
        + L.p(f"{ctx.name} is a vertically integrated textile company headquartered in Coimbatore and listed on the National Stock Exchange. We spin cotton and blended yarns, process knitted fabric and supply brands that sell in India, Europe and North America.")
        + L.p("Our Coimbatore mill makes combed and carded cotton yarn. The Tiruppur unit dyes and finishes knit fabric for garment makers in the cluster, and the 40 MW wind farm in the southern district of Tirunelveli supplies a large part of the electricity needed by our mills through the grid under open access arrangements.")
        + C.facilities_table(ctx)
        + L.figure(ctx.img("map.png"), "<b>Figure 3.1</b> Kaveri's facilities in Tamil Nadu. Marker positions in the enlarged panel are nudged to avoid overlap.")
        + L.p("About 6,500 people work with us. Textile work has long been among the largest sources of formal employment for women in the state, and our workforce reflects that tradition. We also work with several hundred contract workers, mainly in packing, transport and housekeeping.")
        + L.table("Revenue from operations", ["Financial year"] + ctx.fy, [["Rs crore"] + [data.inr(v) for v in t["revenue_cr"]]], src="Source: audited financial statements.")
        + L.figure(ctx.img("revenue.png"), "<b>Figure 3.2</b> Revenue from operations, FY2020 to FY2025 (Rs crore).")
        + L.callout("Our values", "Care for people, respect for resources, honesty in dealing and craft in everything we make.")
    )
    return ch("Company at a glance", "Mills, wind farm and markets", b)


def ch_materiality(ctx, sec):
    b = (
        L.p("Textiles touch many parts of society. We therefore try to listen widely. In 2024 we asked around 300 stakeholders what matters most to them: customers and brand sustainability teams, investors, lenders, employee committees, trade unions, cotton farmer groups, suppliers and local community representatives. Sessions were held in Tamil, English and Hindi.")
        + L.p("Topics were scored on importance to stakeholders and to the business, then reviewed by a panel of senior managers and two independent advisers. The matrix below shows the outcome.")
        + L.figure(ctx.img("materiality.png"), "<b>Figure 4.1</b> Materiality matrix. Priority topics are in the upper right quadrant.")
        + L.h3("What stood out")
        + L.p("Water and effluent, worker safety and fair wages topped the concerns of nearly every group. Brand customers emphasised chemicals management and traceability of cotton. Investors added questions on renewable energy dependence and exposure to climate-related disruptions, such as erratic monsoons that affect cotton.")
        + L.callout("How we engage", items=["Quarterly brand customer reviews", "Worker committees at every unit", "Farmer producer group meetings in cotton belts", "Annual open day for neighbouring villages"])
    )
    return ch("Materiality and stakeholders", "Listening before deciding", b)


def ch_strategy(ctx, sec):
    b = (
        L.p("Our strategy is called Woven with Care, and it has three strands: care for the planet, care for people, and care for the craft. It is meant to be simple enough to be understood in a spinning department and rigorous enough to be examined by an analyst.")
        + L.h3("Care for the planet")
        + L.p("We aim to decouple growth from resource use. Renewable power, efficient machines, water recovery and chemical stewardship are the main tools, with circular fibres a growing area of interest.")
        + L.h3("Care for people")
        + L.p("Safe, fairly paid and respected workers are the core of a textile company. We invest in safety, skills, housing, childcare and women's career progression, and in transparency with unions and worker committees.")
        + L.figure(ctx.img("timeline.png"), "<b>Figure 5.1</b> Strategy roadmap by phase. Phases describe themes of work.")
        + L.h3("Care for the craft")
        + L.p("Quality and innovation, from finer yarn counts to digital printing and recycled fibres, keep us relevant to demanding brands. Better technology usually means less waste.")
        + L.stmt(f"For energy, our principal long-term ambition is straightforward. {ctx.claim('KAV-11')} This builds on the captive wind farm and will require additional generation, storage and open access contracts, subject to regulation and economics.")
        + L.callout("How we track strategy", "A scorecard of environmental, social and governance indicators is reviewed by the Board's Sustainability Committee every quarter, and a subset of the indicators is linked to management incentives.")
        + L.p("The roadmap above describes phases of work. Milestones for each phase are reviewed annually and published in this report, and we are open about delays.")
    )
    return ch("Strategy and targets", "Woven with Care: three strands, one plan", b)


def ch_climate(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.p("Textile production is energy-intensive, mostly because of spinning, which uses electricity, and wet processing, which uses steam and hot water. Our greenhouse gas footprint therefore reflects boilers, thermal oil heaters and purchased power. Our approach to climate follows the TCFD structure, and the Managing Director chairs our Climate Committee.")
        + L.h3("Governance and strategy")
        + L.p("The Board's Sustainability Committee reviews climate risks twice a year. We examine transition risks, such as buyer requirements and a future carbon market, and physical risks, including erratic monsoons that affect cotton supply and heat stress in mills. Scenario analysis shows that dependence on a single wind regime is a risk we need to manage by diversifying sources.")
        + L.h3("Emissions")
        + L.stmt(f"{ctx.claim('KAV-01')} The reduction came from boiler efficiency, switching part of the fuel to biomass, heat recovery in processing and better steam management.")
        + L.figure(ctx.img("scope1.png"), "<b>Figure 6.1</b> Scope 1 GHG emissions, FY2020 to FY2025 (thousand tCO2e).")
        + L.h3("Energy")
        + L.p("The 40 MW captive wind farm in Tirunelveli was commissioned in stages and now plays a central role in our energy mix. We complement it with solar rooftops at the Coimbatore mill and purchase of renewable electricity through open access.")
        + L.stmt(f"{ctx.claim('KAV-02')} {ctx.claim('KAV-08')}")
        + L.figure(ctx.img("re.png"), "<b>Figure 6.2</b> Renewable share of electricity, FY2020 to FY2025 (per cent).")
        + L.callout("Efficiency measures in spinning", items=["High-efficiency motors and fans", "Variable frequency drives on humidification plants", "LED lighting and automated controls", "Compressed air leak management"])
        + L.notes(["Scope 1 covers boiler and thermal oil heater fuel, diesel generator sets and company vehicles.", "Certificates are tracked in our name on the national registry and retired at the end of each calendar year."])
    )
    return ch("Climate and energy", "Wind power, efficiency and certificates", b)


def ch_water(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.p("Water is the lifeblood of textile wet processing. Dyeing and finishing in the Tiruppur cluster once left the Noyyal river in poor condition, and the cluster has since invested in effluent treatment. We want to be among the companies that finish that job.")
        + L.stmt(f"{ctx.claim('KAV-03')} Treated effluent is passed through ultrafiltration, reverse osmosis and multiple effect evaporation, and the recovered water and salts are reused in dyeing.")
        + L.figure(ctx.img("discharge.png"), "<b>Figure 7.1</b> Treated liquid discharge from our operations, FY2020 to FY2025 (thousand kL).")
        + L.stmt(f"Reducing what we draw in the first place is equally important. {ctx.claim('KAV-04')}")
        + L.figure(ctx.img("withdrawal.png"), "<b>Figure 7.2</b> Total water withdrawal, FY2020 to FY2025 (million kL).")
        + L.table("Water indicators", ["Indicator", "Unit"] + ctx.fy, [["Total water withdrawal", "million kL"] + [f"{x / 1e6:.2f}" for x in t["water_withdrawal_kl"]],
                                                              ["Total water discharged", "kL"] + [data.inr(x) for x in t["water_discharge_kl"]]],
                  aligns=["l", "l"] + ["r"] * 6, src="Withdrawal is metered at borewells and municipal connections. Discharge is metered at final outfalls.")
    )
    return ch("Water and zero liquid discharge", "Reuse, recovery and stewardship", b)


def ch_waste(ctx, sec):
    b = (
        L.p("Textile waste comes in many forms: cotton waste from carding and combing, yarn and fabric offcuts, packaging, chemical containers, effluent treatment sludge and salts. The most valuable of these is cotton waste, which is spun again into coarser yarns or sold to the nonwoven and recycled fibre industries.")
        + L.h3("Cotton and fabric waste")
        + L.p("Comber noil, fly and sweepings are sold to open-end spinners and to producers of nonwoven products. Cutting waste from fabric is collected, sorted by fibre and colour and sent for mechanical recycling. We are testing chemical recycling partnerships for blended fabrics, which are harder to recycle.")
        + L.h3("Hazardous waste")
        + L.p("Used dye containers, oil, and laboratory chemicals are collected under authorisation and handed to registered recyclers or treatment facilities. Effluent treatment plant sludge is stored in covered bays and disposed of at authorised secure landfills.")
        + L.callout("Circular programmes", items=["Recycled cotton yarn range with brand partners", "Returnable cones and pallets", "Sorting and baling of fabric offcuts for recycling", "Pilot on dye bath reuse"])
        + L.p("Waste reduction begins with design. We work with merchandising teams and customers on marker efficiency, standard sizes and minimum order quantities that reduce the offcuts and leftover stock.")
        + L.p("Our waste data is compiled by weight at each unit and reviewed in monthly plant meetings. Because waste sold to third parties leaves our control, we track end use through buyer declarations wherever possible.")
    )
    return ch("Waste and circular fibres", "From offcuts to opportunity", b)


def ch_bio(ctx, sec):
    b = (
        L.p("Our own sites are in industrial and agricultural areas, and we do not operate in or next to protected forests. Our biodiversity footprint lies mostly upstream, in cotton fields, and downstream in the rivers that receive textile effluent. The wind farm sits on dry upland in Tirunelveli, with some of the turbines near migratory bird routes.")
        + L.h3("Wind farm and wildlife")
        + L.p("Before construction, bird and bat surveys were conducted and turbine layouts were adjusted to leave corridors. Post-construction monitoring continues with a local ornithological society. We share results with the Forest Department and use them to adjust operation during peak migration if needed.")
        + L.h3("Cotton and soil")
        + L.p("Cotton farming draws heavily on soil and water and, if poorly managed, on pesticides. Our farmer outreach programme supports integrated pest management, drip irrigation, soil health testing and intercropping. We favour regenerative practices and are building a base of farmers in Maharashtra and Telangana.")
        + L.callout("Nature-positive steps", items=["Native tree plantations around mills and wind farm", "Support for pond restoration in neighbouring villages", "Bird monitoring at the wind farm", "Pesticide reduction training for farmers"])
        + L.p("We are beginning to map our nature-related dependencies using the TNFD framework, starting with cotton sourcing regions. As this work progresses, we will report more on our upstream footprint.")
    )
    return ch("Biodiversity and nature", "Cotton fields, rivers and wind", b)


def ch_air(ctx, sec):
    b = (
        L.p("Compliance is the floor of our environmental work, not its ceiling. Each of our three sites operates under consents issued by the Tamil Nadu Pollution Control Board, and the Tiruppur unit is subject to additional conditions on effluent and zero liquid discharge, with online monitoring linked to the Board.")
        + L.h3("How we manage compliance")
        + L.p("We maintain a register of legal requirements for each site, with owners and due dates. Responsible managers confirm status monthly, and the Head of Sustainability reviews a consolidated report. External auditors conduct an environmental compliance audit at each site every year, and their findings are tracked to closure.")
        + L.stmt(f"We pay close attention to what regulators tell us, and to what they do not. {ctx.claim('KAV-07')}")
        + L.callout("Air emissions control", items=["Bag filters and cyclones on boilers", "Biomass and cleaner fuel preferred over coal", "Regular stack monitoring by accredited laboratories", "Cotton dust extraction in blow room and carding"])
        + L.p("Spinning produces cotton dust, which is a respiratory hazard for workers. Humidification, extraction and filtration systems keep dust levels within limits, and workers receive periodic lung function tests.")
        + L.p("In the dyeing house, volatile solvents are minimised through the choice of chemicals, and boilers are tuned for complete combustion. Odour and noise are monitored at the boundary of the Tiruppur unit.")
    )
    return ch("Air quality and compliance", "Meeting standards and keeping regulators informed", b)


def ch_people(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.p("Textile mills run around the clock. People work close to rotating machinery, hot water and steam, and in humid, noisy environments. We manage these risks through engineering controls, training and a culture in which anyone can stop work.")
        + L.stmt(f"We treat safety as a shared responsibility and report on it openly. {ctx.claim('KAV-06')}")
        + L.figure(ctx.img("ltifr.png"), "<b>Figure 11.1</b> Lost Time Injury Frequency Rate per million person-hours, FY2020 to FY2025.")
        + L.h3("Safety system")
        + L.p("Our management system is certified to ISO 45001. Hazard identification covers each machine and process, and every near-miss is investigated for root cause. Contractors follow the same standards, and no work begins without a permit where the task is high risk.")
        + L.callout("Safety practices", items=["Machine guarding and lock-out procedures in spinning and processing", "Chemical handling training and personal protective equipment in the dye house", "Fire safety drills and sprinklers", "Joint worker-management safety committees at each unit"])
        + L.h3("Health and wellbeing")
        + L.p("Occupational health centres at Coimbatore and Tiruppur provide periodic check-ups, audiometry, lung function tests and first aid. Counsellors support workers who live away from their families in company hostels.")
        + L.h3("Skills")
        + L.p("The Kaveri Skills Academy trains operators, mechanics and supervisors, and provides a pathway for school leavers to join as apprentices. Many of our supervisors began as trainees on the shop floor.")
        + L.p("Collective bargaining covers most workmen in our mills, and wage agreements are reached by negotiation. Grievance committees meet monthly.")
    )
    return ch("People and safety", "Looking after those who make our cloth", b)


def ch_di(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.p("Women have always been central to the textile industry in Tamil Nadu. Our task is to ensure that this participation comes with fair pay, safe working conditions, opportunities to advance and freedom from harassment. We do not regard high employment of women as an achievement by itself unless those conditions are met.")
        + L.stmt(f"We monitor how earnings are shared as a simple indicator of fairness. {ctx.claim('KAV-05')}")
        + L.figure(ctx.img("women.png"), "<b>Figure 12.1</b> Gross wages paid to women as a percentage of total gross wages, FY2020 to FY2025.")
        + L.table("Women's share of gross wages", ["Indicator"] + ctx.fy, [["% of total gross wages"] + [f"{x:.1f}" for x in t["women_wage_pct"]]],
                  src="Gross wages include basic pay, allowances, overtime and bonus for permanent employees and workers.")
        + L.h3("Beyond participation")
        + L.p("We are working to increase the share of women in supervisory and technical roles through training and mentoring. Hostels for migrant workers have security, medical care and recreation, and each unit operates a crèche for children of employees.")
        + L.callout("Inclusion measures", items=["Internal Committee under the POSH Act, with worker representation", "Leadership programme for women supervisors", "Equal pay for equal work audits", "Recruitment of persons with disabilities in suitable roles"])
        + L.p("We recognise that inclusion extends to migrant workers from other states, who face language and housing barriers. Our welfare officers speak several languages, and orientation is provided in the worker's own language.")
    )
    return ch("Diversity and inclusion", "Fair opportunity at every level", b)


def ch_community(ctx, sec):
    b = (
        L.p("Kaveri's mills are woven into the neighbourhoods around them. Many of our employees live nearby, and the success of the company is closely linked to the health of these places. Our CSR activities focus on women's livelihoods, education, health and the environment.")
        + L.kpis([("Rs 18 crore", "CSR and community spend, FY2025"), ("45", "Villages in programme areas"), ("6", "Themes")])
        + L.figure(ctx.img("csr.png"), "<b>Figure 13.1</b> CSR spend by theme, FY2025 (Rs crore).")
        + L.h3("Women's livelihoods")
        + L.p("Self-help groups receive training in tailoring, handloom, food processing and digital skills, together with linkages to banks and markets. Several groups now supply us with packing materials and uniforms.")
        + L.h3("Education and health")
        + L.p("We have supported science laboratories and sanitation facilities in government schools, scholarships for girls, and evening study centres for children of migrant workers. A mobile clinic visits villages near Tirunelveli and Tiruppur twice a week.")
        + L.h3("Environment")
        + L.p("Pond de-silting, tree planting and school eco-clubs engage children and adults in caring for local ecosystems.")
        + L.callout("Participatory planning", "Each village programme is chosen with panchayat members and reviewed in an annual social audit.")
    )
    return ch("Community and social investment", "Growing together with our neighbours", b)


def ch_governance(ctx, sec):
    b = (
        L.p("The Board has nine directors, five of them independent, with two women directors. The Chairman is a non-executive director, and the Managing Director leads the executive team. Board skills include textiles, finance, law, technology and sustainability.")
        + L.h3("Oversight")
        + L.p("The Audit Committee oversees financial and non-financial reporting and the system of internal controls. The Sustainability Committee, chaired by an independent director, meets quarterly to review plans, performance, risks and disclosures. The Risk Management Committee reviews the enterprise risk register.")
        + L.callout("Conduct and ethics", items=["Code of Conduct and annual declaration", "Anti-bribery and anti-corruption policy", "Independent whistle-blower hotline reporting to the Audit Committee chair", "Human rights policy covering employees and suppliers"])
        + L.h3("Risk management")
        + L.p("Strategic, operational, financial and ESG risks are scored by owners and reviewed regularly. Cotton price volatility, wind variability, regulatory change on effluent standards, labour availability and climate-related disruptions are among the principal risks, each with a mitigation plan.")
        + L.p("The company does not make political contributions. We belong to industry associations such as the Southern India Mills Association and the Tiruppur Exporters' Association, and we disclose our policy positions where they affect our stakeholders.")
        + L.p("Executive remuneration includes a component linked to safety, resource efficiency and customer sustainability audits, as determined by the Nomination and Remuneration Committee.")
    )
    return ch("Governance and ethics", "A board that asks questions", b)


def ch_supply(ctx, sec):
    b = (
        L.p("The biggest part of a textile company's footprint lies outside its gates: on cotton farms, in ginning mills and in the factories that cut and sew our fabric. We cannot control these places but we can influence them, and we increasingly try to.")
        + L.h3("Cotton sourcing")
        + L.p("We buy cotton from farmer producer groups, traders and the Cotton Corporation of India. A traceability pilot uses digital records to link bales to farmer groups, and a growing proportion of our cotton comes with documentation of origin. We prefer Better Cotton and organic sources where customers ask for them.")
        + L.stmt(f"Fair pay for supply chain workers is an important issue for brands and for us. {ctx.claim('KAV-10')}")
        + L.callout("Supplier standards", items=["Supplier Code of Conduct covering labour, safety and environment", "Risk-based audits, including by customers and third parties", "Chemical management in line with ZDHC guidelines", "Worker voice channels for key suppliers"])
        + L.h3("Customers")
        + L.p("Brands increasingly ask for environmental data, product-level footprints and chemical compliance. We maintain test reports and certifications such as OEKO-TEX and GOTS for relevant product lines, and share information through industry platforms.")
        + L.p("Value chain emissions are a growing topic of conversation with customers. We are building a Scope 3 inventory starting with purchased goods and transport, and will report on it when data quality allows.")
    )
    return ch("Supply chain and customers", "Cotton, suppliers and brand partners", b)


def ch_brsr(ctx, sec):
    t = ctx.co["true"]
    sel = [3, 4, 5]
    f = lambda k, fmt="{:.1f}": [fmt.format(t[k][i]) for i in sel]
    b = (
        L.p("The table below shows selected BRSR Core indicators for the last three years. The full BRSR is available on the stock exchange websites.")
        + L.table("BRSR Core summary: selected indicators", ["Attribute", "Indicator", "Unit"] + [ctx.fy[i] for i in sel],
                  [["Economic", "Revenue from operations", "Rs crore"] + [data.inr(t["revenue_cr"][i]) for i in sel],
                   ["GHG footprint", "Total Scope 1 emissions", "tCO2e"] + [data.inr(t["scope1_tco2e"][i]) for i in sel],
                   ["Energy footprint", "Share of electricity from renewable sources", "%"] + f("re_pct"),
                   ["Water footprint", "Total water withdrawal", "kL"] + [data.inr(t["water_withdrawal_kl"][i]) for i in sel],
                   ["Water footprint", "Total water discharged", "kL"] + [data.inr(t["water_discharge_kl"][i]) for i in sel],
                   ["Employee wellbeing and safety", "Lost Time Injury Frequency Rate (per million hours)", "Rate"] + f("ltifr", "{:.2f}"),
                   ["Employee wellbeing and safety", "Work-related fatalities", "Count"] + f("fatalities", "{:.0f}"),
                   ["Gender diversity", "Gross wages paid to females as % of total wages", "%"] + f("women_wage_pct"),
                   ["Openness", "Type of assurance on BRSR Core", "Category"] + [t["assurance_type"][i].capitalize() for i in sel]],
                  src="Definitions follow SEBI's BRSR Core framework. Assurance provider: Natarajan Assurance Services.", aligns=["l", "l", "l", "r", "r", "r"])
        + L.p("BRSR Core also asks for indicators on circularity, inclusive development and fairness to customers and suppliers. These appear in the statutory BRSR and are discussed in the narrative sections of this report.")
        + L.callout("Basis of preparation", items=["Operational control boundary", "Water discharge covers treated effluent leaving the site", "Fatalities include employees and contract workers", "Wages cover permanent employees and workers"])
        + L.p("Our renewable electricity share counts generation from the captive wind farm consumed at our mills together with certified renewable purchases.")
    )
    return ch("BRSR Core summary", "Selected indicators, FY2023 to FY2025", b)


def ch_assurance(ctx, sec):
    b = (
        L.p("Assurance gives readers confidence that what we report is complete and accurate. We began with limited assurance on our BRSR Core indicators and have progressively moved to a higher standard as our systems improved.")
        + L.stmt(f"{ctx.claim('KAV-09')} The independent report from Natarajan Assurance Services follows this section.")
        + L.h3("Engagement")
        + L.p("The assurance team visited all three sites, tested a sample of data points from meter to report, interviewed process owners and reviewed our calculation workbooks. They raised a small number of observations on documentation, which we have since addressed.")
        + L.callout("Internal controls on reporting", items=["Plant-level data owners sign off monthly", "Sustainability team reconciles to utility bills and payroll", "Internal audit tests selected indicators", "Audit Committee review before publication"])
        + L.p("We will continue to extend assurance to indicators beyond BRSR Core as methods mature, and to supply chain data in particular.")
    )
    return ch("Assurance and reporting integrity", "Independent review of our data", b)


def ch_letter(ctx, sec):
    body = C.assurance_letter(ctx, "Natarajan Assurance Services", "CA Sundaram Natarajan", "004517S", "Coimbatore", "29 May 2025",
                              "The engagement covered the BRSR Core indicators for the year ended 31 March 2025 as presented in the Company's filing.")
    return ch("Independent assurance report", "Reasonable assurance on selected BRSR Core indicators", body, raw=True)


def ch_gri(ctx, sec):
    topic = {k: sec[k] for k in ["about", "message", "glance", "materiality", "strategy", "climate", "water", "waste", "bio", "air", "people", "di", "community", "governance", "supply", "assurance"]}
    body = C.gri_index(topic, f"<b>Statement of use.</b> {ctx.name} has reported the information cited in this GRI content index for the period 1 April 2024 to 31 March 2025 with reference to the GRI Standards.",
                       partial=("305-3", "301-1", "301-2", "304-3", "304-4", "403-10"))
    return ch("GRI content index", "Where to find each disclosure", body, raw=True, cls="gri")


def ch_glossary(ctx, sec):
    extra = {"Comber noil": "Short fibres removed during combing, sold for coarser yarns and nonwovens.", "GOTS": "Global Organic Textile Standard.",
             "OEKO-TEX": "A family of tests and labels for textile safety.", "Open access": "A framework allowing consumers to buy power directly from generators using the grid.",
             "Spindle": "The spinning unit that twists fibre into yarn; mills quote capacity in spindles.", "ZDHC": "Zero Discharge of Hazardous Chemicals programme.",
             "Ultrafiltration": "A membrane process that removes suspended solids and large molecules from effluent.", "Reverse osmosis": "A membrane process that removes dissolved salts from water.",
             "Wet processing": "Dyeing, printing and finishing of textiles using water and chemicals."}
    return ch("Glossary", "Terms and abbreviations", C.glossary({**C.BASE_TERMS, **extra}), cls="glossary")


def ch_disclaimer(ctx, sec):
    return ch("Forward-looking statements", "Important notice to readers", C.forward_looking(ctx))
