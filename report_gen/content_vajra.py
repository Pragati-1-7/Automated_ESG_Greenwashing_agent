"""Vajra Steel & Power Ltd: glossy, PR-heavy report. Only ALIGN metrics (intensity, waste recovery,
women wage share) plus revenue appear in tables and charts. Scope 1/2, water, LTIFR, fatalities and
renewable-share figures are deliberately NOT printed anywhere."""
from __future__ import annotations
from . import layout as L, charts, common_text as C, data

ORDER = ["about", "message", "glance", "materiality", "strategy", "climate", "water", "waste", "bio", "air",
         "people", "di", "community", "governance", "supply", "brsr", "assurance", "gri", "glossary", "disclaimer"]
TOC_GROUPS = [{"at": "01", "label": "Introduction"}, {"at": "06", "label": "Environment"}, {"at": "11", "label": "Social"},
              {"at": "14", "label": "Governance and value chain"}, {"at": "16", "label": "Disclosures and reference"}]


def make_charts(ctx):
    pal, co = ctx.pal, ctx.co
    t = co["true"]
    charts.bar_chart(ctx.path("revenue.png"), ctx.fy, t["revenue_cr"], pal, ylabel="Rs crore", h=2.3)
    charts.line_chart(ctx.path("intensity.png"), ctx.fy, {"Scope 1+2 intensity (tCO2e per Rs crore of turnover)": [round(x) for x in data.intensity(co)]}, pal, ylabel="tCO2e / Rs crore", h=2.5)
    charts.bar_chart(ctx.path("recovery.png"), ctx.fy, [round(x, 1) for x in data.recovery_pct(co)], pal, ylabel="% of waste generated", fmt="{:.1f}", h=2.3, ylim=(0, 105))
    charts.line_chart(ctx.path("women.png"), ctx.fy, {"Women's share of gross wages (%)": t["women_wage_pct"]}, pal, ylabel="% of gross wages", fmt="{:.1f}", h=2.3)
    charts.materiality(ctx.path("materiality.png"), [
        ("Climate change and decarbonisation", 9.2, 9.0, 4), ("Air quality and emissions", 8.1, 8.6, 3), ("Water stewardship", 7.2, 7.8, 3),
        ("Occupational health and safety", 8.8, 9.3, 4), ("Circular economy and by-products", 7.6, 6.9, 3), ("Biodiversity and land use", 6.1, 7.7, 2),
        ("Workforce capability", 7.0, 6.2, 2), ("Community relations", 5.6, 7.1, 2), ("Responsible supply chain", 6.8, 6.0, 2),
        ("Ethics and governance", 8.3, 7.4, 3), ("Green steel products", 7.9, 5.8, 2), ("Diversity and inclusion", 4.8, 6.6, 1)], pal)
    charts.timeline(ctx.path("timeline.png"), [
        ("FY2021 to FY2024", "Foundation", ["Baseline inventory", "Energy management system", "Water and waste mapping"]),
        ("FY2025 to FY2028", "Acceleration", ["Renewable power sourcing", "Process efficiency upgrades", "Pellet and DRI optimisation"]),
        ("FY2029 to FY2035", "Transformation", ["Scrap and electric routes", "Hydrogen readiness", "Carbon capture studies"]),
        ("Beyond FY2035", "Deep transition", ["Low-carbon steel portfolio", "Value chain partnerships"]),
    ], pal)
    charts.hbar_chart(ctx.path("csr.png"), ["Education and skilling", "Healthcare and nutrition", "Livelihoods and enterprise", "Drinking water and sanitation", "Environment and plantation", "Sports and culture"],
                      [38, 27, 24, 14, 9, 6], pal, xlabel="Rs crore, FY2025", h=2.4)


def chapters(ctx):
    sec = {k: f"{i + 1:02d}" for i, k in enumerate(ORDER)}
    ctx.back_text = ("<p>Corporate Sustainability Office<br>Vajra Bhawan, Janpath, Bhubaneswar 751 001, Odisha</p>"
                     "<p>sustainability@vajrasteel.example | www.vajrasteel.example</p>"
                     "<p>CIN L27100OR1998PLC005512 | NSE: VAJRASTL</p>")
    B = {k: globals()[f"ch_{k}"] for k in ORDER}
    return [B[k](ctx, sec) for k in ORDER]


def ch(title, subtitle, body, **kw):
    return {"title": title, "subtitle": subtitle, "body": body, **kw}


def ch_about(ctx, sec):
    n = ctx.name
    b = (
        L.p(f"Welcome to the sustainability report of {n}, covering the financial year from 1 April 2024 to 31 March 2025. This is our fifth consecutive annual report on environmental, social and governance performance and the first in which we describe our work as a single, connected programme rather than a set of separate initiatives. "
            "We hope that customers, investors, regulators, employees and the communities around our plants will find it a clear account of where we stand and where we are heading.")
        + L.h3("Reporting boundary")
        + L.p("The report covers our four operating facilities in Odisha: the Jharsuguda Integrated Steel Plant, the Angul Captive Power Plant, the Keonjhar Iron Ore Mine and the Barbil Pellet Plant, together with our corporate office in Bhubaneswar. Joint ventures and associate companies in which we do not hold operational control are outside the boundary. Contractor personnel working at our sites are included wherever a disclosure refers to workers.")
        + L.p("Financial information is consistent with our audited consolidated financial statements. Environmental and social information follows an operational control approach. Where a methodology changed during the year we say so in the notes to the relevant section, and any restatement of earlier figures is marked as such.")
        + C.about_frameworks_callout()
        + L.h3("How to read this report")
        + L.p("Each section opens with a short statement of why the topic matters to a business of our kind, followed by our approach, the programmes under way and the year's progress. Tables carry units in the column headings. Defined terms are explained in the glossary near the end, and a GRI content index shows where each disclosure can be found.")
        + L.p("The report was reviewed by our Sustainability Steering Committee and approved by the Board of Directors on 22 May 2025. We welcome feedback through the contact details on the back cover.")
        + L.pull("Steel is the backbone of a modern economy. Making it responsibly is the job in front of us.", "Sustainability Steering Committee")
        + L.p("Comparative figures for earlier years are provided where they help the reader see direction of travel. We have tried to be plain about definitions, boundaries and limitations, because a report is only useful if it can be read without a specialist at hand.")
        + L.notes(["Operational control means we report 100 per cent of the data of facilities over which we have authority to introduce and implement operating policies.",
                   "The statutory BRSR for FY2025 was filed with the stock exchanges separately and remains the reference for detailed filed values."])
    )
    return ch("About this report", "Scope, boundary, period and frameworks", b)


def ch_message(ctx, sec):
    b = (
        L.p("Dear stakeholders,")
        + '<p class="dropcap">' + ("Every tonne of steel we make carries a promise. It is a promise to the engineer who builds a bridge, to the family that moves into a new home, and to the villages that live in the shadow of our furnaces. Over the last year we worked to keep that promise with greater discipline, greater transparency and, I believe, greater imagination than before.") + '</p>'
        + L.p("The year was demanding. Input costs moved sharply, global trade flows shifted, and our customers asked more of us on provenance and carbon. Yet our teams delivered record output and healthy margins, while continuing to invest in cleaner processes and in the people who run them.")
        + L.stmt(f"On climate, the direction of our business is clear. {ctx.claim('VAJ-01')} That progress came from process optimisation, better utilisation of by-product gases and sustained investment in efficiency, and it gives us the confidence to commit to the harder work that lies ahead.")
        + L.p("Our Odisha operations sit in a landscape of great natural beauty and great social expectation. I regard the trust of our neighbours as a licence that is renewed daily, not a right we hold by virtue of a mining lease. This is why we expanded engagement with panchayats, with tribal councils and with district administrations during the year, and why we have opened our plants to more visitors, students and civil society groups than ever before.")
        + L.pull("Trust is built in the quiet hours between announcements.", "Chairman and Managing Director")
        + L.p("I would like to thank our 14,000-strong team, our customers, our lenders and shareholders, and the Government of Odisha for their partnership. I also thank the Board for its guidance as we sharpened our governance of sustainability and strengthened the oversight role of our Risk and Sustainability Committee.")
        + L.stmt(f"As we look ahead, our purpose is unchanged. {ctx.claim('VAJ-15')} We will keep working, measuring and reporting, and we invite you to hold us to account.")
        + '<div class="sign">With best wishes,<b>Rajiv Mohapatra</b><span>Chairman and Managing Director<br>Bhubaneswar, 22 May 2025</span></div>'
        + L.callout("Year in brief", items=["Record production and sales volumes across the integrated plant", "New renewable power sourcing arrangements signed", "Expanded community health and skilling programmes in Jharsuguda and Keonjhar", "Governance of sustainability moved to a dedicated Board committee"])
    )
    return ch("Message from the Chairman and Managing Director", "A letter on progress, purpose and the road ahead", b)


def ch_glance(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.kpis([("Rs 41,500 crore", "Revenue, FY2025"), ("5.0 MTPA", "Crude steel capacity"), ("1,200 MW", "Captive power capacity"), ("12.0 MTPA", "Iron ore mining capacity")])
        + L.p(f"{ctx.name} is an integrated steel and power company headquartered in Bhubaneswar and listed on the National Stock Exchange of India. We convert Odisha's iron ore into long and flat steel products for infrastructure, construction, automotive and capital goods customers across India and in export markets.")
        + L.p("Our value chain runs from mine to market. Iron ore from our Keonjhar mine is beneficiated and pelletised at Barbil, then charged with coking coal and fluxes at the Jharsuguda works. A captive power plant at Angul supplies the integrated complex with electricity and process steam, and we sell surplus power to the grid when conditions allow.")
        + L.h3("Our facilities")
        + C.facilities_table(ctx)
        + L.figure(ctx.img("map.png"), "<b>Figure 3.1</b> Location of our four operating facilities in Odisha, with an enlarged view of the cluster. Source: company records.", wide=True)
        + L.p("About 14,000 people work with us directly, supported by a larger community of contractors, transporters and service partners. Our products are supplied through a network of regional stockyards, and a growing share of volume is sold under long-term contracts with infrastructure developers and original equipment makers.")
        + L.table("Revenue from operations", ["Financial year"] + ctx.fy, [["Rs crore"] + [data.inr(v) for v in t["revenue_cr"]]],
                  src="Source: audited consolidated financial statements. Figures in Rs crore; one crore equals 10 million.")
        + L.figure(ctx.img("revenue.png"), "<b>Figure 3.2</b> Revenue from operations, FY2020 to FY2025 (Rs crore).")
        + L.callout("Our purpose and values", "We exist to make the steel that builds India, responsibly. Four values guide how we work: safety first, integrity always, customers at the centre and respect for people and place.")
    )
    return ch("Company at a glance", "Who we are, where we operate and what we make", b)


def ch_materiality(ctx, sec):
    b = (
        L.p("Materiality tells us where to focus. In the autumn of 2024 we refreshed our materiality assessment, drawing on structured interviews with investors, lenders, customers, regulators, employee representatives, community leaders and non-governmental organisations. Around 400 stakeholders took part through interviews, surveys and workshops conducted in English, Hindi and Odia.")
        + L.p("The assessment followed the double materiality logic of GRI 3: we asked how each topic affects the value of our business, and how our business affects people and the environment. Topics were scored on both dimensions by a cross-functional panel, challenged by external advisers and then validated by the Sustainability Steering Committee.")
        + L.figure(ctx.img("materiality.png"), "<b>Figure 4.1</b> Materiality matrix. Topics in the upper right quadrant are those we regard as highest priority for management and disclosure.")
        + L.h3("What we heard")
        + L.p("Investors and lenders pressed hardest on decarbonisation pathways and the cost of transition. Customers in the automotive and construction sectors asked for product-level carbon information. Community representatives raised air quality, water availability and employment for local youth, while employee voices emphasised safety, skills and fairness in promotion.")
    )
    return ch("Materiality and stakeholder engagement", "What matters most to our stakeholders and to our business", b)


def ch_strategy(ctx, sec):
    b = (
        L.p("Our sustainability strategy is organised around four pillars that mirror how a steelmaker actually creates and destroys value: the process we run, the power we use, the materials we recover and the places we belong to. Each pillar has a named executive owner, a roadmap of initiatives and a set of internal key performance indicators that feed into management scorecards.")
        + L.h3("Pillar 1: Cleaner process")
        + L.p("We are improving the efficiency of every stage of the steel route, from raw material preparation to rolling. Priorities include burden optimisation in the blast furnace, injection technology, recovery of waste heat, and digital controls that reduce variability in energy use.")
        + L.h3("Pillar 2: Responsible power")
        + L.p("Our captive power fleet supports reliability, but our direction is toward a cleaner electricity mix. We are expanding procurement of renewable power and are evaluating storage and hybrid arrangements to firm up supply to the integrated complex.")
        + L.figure(ctx.img("timeline.png"), "<b>Figure 5.1</b> Strategic roadmap by phase. Phases describe themes of work and are not commitments to specific quantities.")
        + L.h3("Pillar 3: Circular materials")
        + L.p("By-products such as slag, dust and sludge are resources in the wrong place. We work with cement makers, brick manufacturers and road builders to find productive uses for them and continue to invest in processing capability on site.")
        + L.h3("Pillar 4: Thriving communities")
        + L.p("Our licence to operate rests on shared prosperity. We invest in health, education and livelihoods around our sites, and we seek to hire locally wherever skills allow.")
        + L.stmt(f"Looking to the long term, we have set our direction in line with national ambition. {ctx.claim('VAJ-16')} Our roadmap sets out the phases of work through which we intend to get there, and we will report on progress as technologies and policy mature.")
    )
    return ch("ESG strategy and targets", "Four pillars, a phased roadmap and a long-term direction", b)


def ch_climate(ctx, sec):
    t = ctx.co["true"]
    inten = data.intensity(ctx.co)
    b = (
        L.p("Steelmaking is among the most carbon-intensive of industrial activities, and we do not pretend otherwise. Our approach to climate is organised along the four pillars of the TCFD framework, and is led by the Managing Director with oversight from the Board's Risk and Sustainability Committee.")
        + L.h3("Governance and strategy")
        + L.p("Climate-related risks and opportunities are reviewed quarterly by the executive committee and twice a year by the Board committee. We use two scenario families, an orderly transition aligned with national policy and a disorderly scenario with delayed action and higher carbon prices, to test the resilience of capital plans. Transition risks include carbon pricing under the proposed Indian carbon market, shifts in customer demand and technology cost; physical risks include heat stress, intense rainfall and water scarcity at our sites.")
        + L.h3("Metrics")
        + L.stmt(f"{ctx.claim('VAJ-02')} The improvement reflects a combination of process efficiency, a richer product mix and growth in turnover over the period, and we continue to track it every quarter.")
        + L.figure(ctx.img("intensity.png"), "<b>Figure 6.1</b> GHG emission intensity (Scope 1 and 2 combined, per Rs crore of turnover), FY2020 to FY2025.")
        + L.table("GHG emission intensity", ["Indicator"] + ctx.fy, [["tCO2e per Rs crore of turnover"] + [f"{x:,.0f}" for x in inten]],
                  src="Intensity is calculated as combined Scope 1 and Scope 2 emissions divided by revenue from operations. Revenue is in Rs crore at current prices.")
        + L.h3("Energy")
        + L.p("Our energy strategy rests on three legs: using every gigajoule better, switching to cleaner sources where we can, and building the grid connections and storage that make that switch reliable. Within the plant, waste heat and process gases are recovered and used in power generation and in heating applications.")
        + L.stmt(f"Our renewable power programme combines open access procurement with the purchase of certificates. {ctx.claim('VAJ-03')} {ctx.claim('VAJ-04')}")
        + L.callout("Technology levers under evaluation", items=["Higher scrap charge and electric arc capacity", "Direct reduced iron with natural gas and, later, hydrogen", "Top gas recycling and waste heat recovery upgrades", "Biochar and other carbon-lean reductants", "Carbon capture, utilisation and storage feasibility studies"])
        + L.notes(["Emission factors follow the GHG Protocol and the latest CEA grid emission factors for purchased electricity.", "Targets and ambitions are described in the strategy section and are forward-looking statements."])
    )
    return ch("Climate and energy", "Our TCFD-aligned approach to decarbonisation", b)


def ch_water(ctx, sec):
    b = (
        L.p("Water is both an operational necessity and a shared resource. Steel and power generation use water for cooling, descaling, dust suppression, slurry transport and steam, and our sites in Odisha draw on rivers, reservoirs and groundwater that also serve local households and farms.")
        + L.h3("Our approach")
        + L.p("Our water policy commits us to understanding our interaction with catchments, to reducing freshwater use through efficiency and reuse, and to engaging communities and authorities in transparent water stewardship. Each site maintains a water balance, reviewed monthly, that tracks withdrawal, consumption, recycling and discharge.")
        + L.stmt(f"Water efficiency has been a priority for several years. {ctx.claim('VAJ-05')} The programme combined recirculation upgrades, loss detection, treated effluent reuse and a focus on high-use departments.")
        + L.callout("Where we focus", items=["Closed-circuit cooling and blowdown recovery", "Sewage and effluent treatment with reuse in dust suppression and gardening", "Rainwater harvesting structures at plant and township", "Ultrasonic flow metering and leak detection", "Village water access projects with local panchayats"])
        + L.p("We have extended our attention beyond the fence. In partnership with district authorities, we supported watershed treatment, check dams and pond rejuvenation around our mining lease and plant villages. These projects aim to improve groundwater recharge and to lower competition between industrial and domestic use in the dry season.")
        + L.p("Water risk screening is part of every major capital project. Our tools consider catchment stress, regulatory limits on abstraction, climate projections and community dependence. The results influence site selection, technology choices and the design of cooling systems.")
        + L.pull("The measure of a good neighbour is what is left in the river after you have drawn from it.", "Head of Environment")
        + L.p("Looking ahead, we plan to deepen our work on basin-level targets, tighten water accounting at the mine, and publish more detail on stewardship partnerships in future reports.")
    )
    return ch("Water stewardship", "Using less, reusing more and sharing the catchment", b)


def ch_waste(ctx, sec):
    rec = data.recovery_pct(ctx.co)
    b = (
        L.p("Steelmaking generates large volumes of by-products, chiefly blast furnace and steel melt shop slag, dust, sludge, mill scale and fly ash from our power plant. Managed well, these streams are valuable inputs for the construction, road and cement industries; managed poorly, they become a burden on land and communities.")
        + L.p("We follow a waste hierarchy that puts prevention first, followed by reuse, recycling, recovery and, only as a last resort, safe disposal in engineered facilities. Hazardous wastes are handled under authorisations from the State Pollution Control Board and are transported and treated by licensed operators.")
        + L.stmt(f"Our circularity efforts have scaled steadily over the years. {ctx.claim('VAJ-11')} The balance is directed to engineered storage and disposal under regulatory authorisation.")
        + L.figure(ctx.img("recovery.png"), "<b>Figure 8.1</b> Share of waste generated that was recovered, recycled or co-processed, FY2020 to FY2025 (per cent).")
        + L.table("Waste recovery rate", ["Indicator"] + ctx.fy, [["% of waste generated recovered or recycled"] + [f"{x:.1f}" for x in rec]],
                  src="Waste generated and waste recovered are measured in tonnes at the weighbridge or by calibrated estimation. Recovery includes recycling within our processes and supply to third-party users.")
        + L.h3("Slag, dust and sludge")
        + L.p("Granulated blast furnace slag is a prized input for cement manufacturers and a replacement for natural aggregates. We have long-term arrangements with cement partners in eastern India and supported the setting up of slag processing capacity near our plant. Steel melt shop slag is processed to recover metallics and then used in road sub-bases.")
        + L.p("Dust and sludge from gas cleaning systems, rich in iron and carbon, are recycled through sinter and pellet processes after suitable conditioning. Mill scale is sold to powder metallurgy and ferro-alloy users. Fly ash from the captive plant is supplied to brick makers and cement producers, and ash ponds are managed under a dyke safety programme overseen by the plant head.")
        + L.callout("Circularity partnerships", "We work with research institutes on use of steel slag in road construction, with state agencies on fly ash brick clusters, and with start-ups on recovery of zinc and other metals from dust.")
    )
    return ch("Waste and circularity", "Turning by-products into resources", b)


def ch_bio(ctx, sec):
    b = (
        L.p("Our Keonjhar iron ore mine is located in a region of mixed forest, agriculture and tribal habitation. Mining here carries a special responsibility to protect ecosystems and the services they provide to local communities, from fuelwood and minor forest produce to water regulation.")
        + L.h3("Our biodiversity approach")
        + L.p("Our biodiversity policy follows the mitigation hierarchy: avoid, minimise, restore and, as a last resort, offset. Mine plans are reviewed against ecological baseline studies before each phase of expansion, and statutory conditions attached to forest and environmental clearances are tracked on an internal compliance system.")
        + L.stmt(f"We apply the same discipline to day-to-day mining practice, and we are clear about the standard we hold ourselves to. {ctx.claim('VAJ-06')} We continue to monitor satellite imagery of the lease area and its surroundings, and to engage with the Forest Department and local committees on land use.")
        + L.callout("Restoration and nature programmes", items=["Progressive reclamation of mined-out benches with native species", "Green belt development around the plant, township and haul roads", "Nursery of local species supporting village plantations", "Wildlife corridor awareness work with the Forest Department", "Pollinator and bird surveys with university partners"])
        + L.p("Reclamation is planned from the start of a mine. Overburden is stacked in engineered dumps, topsoil is conserved for later use, and benches are re-vegetated using species selected with the help of botanists from the state forest research institute. Biological indicators such as bird counts and soil health are monitored at selected plots.")
        + L.p("At our plant sites, we work to enhance green cover and to protect water bodies within the fence. Our township has a biodiversity register, and employees and their families take part in annual bird counts and tree planting days.")
        + L.h3("Looking ahead")
        + L.p("We are building capability to report against the emerging TNFD recommendations, starting with a screening of nature-related dependencies and impacts across our sites. Findings will inform both operational practice and future disclosures.")
        + L.notes(["The Keonjhar lease operates under forest and environmental clearances issued by the competent authorities and renewed in accordance with law.", "TNFD refers to the Taskforce on Nature-related Financial Disclosures."])
    )
    return ch("Biodiversity and land", "Protecting ecosystems around our mine and plants", b)


def ch_air(ctx, sec):
    b = (
        L.p("Clean air is a basic expectation of every community near an industrial site. Our plants are subject to emission standards notified under the Environment (Protection) Act, 1986, and to conditions in the consent to operate granted by the State Pollution Control Board. We treat these standards as a floor and invest to stay ahead of them.")
        + L.h3("Controls and monitoring")
        + L.p("Stacks at our major units are fitted with online continuous emission monitoring systems that transmit data to the regulator's servers. Electrostatic precipitators, bag filters, flue gas desulphurisation provisions and low-NOx burners are used wherever process and fuel mix require them. Fugitive emissions are controlled through enclosed conveyors, water sprinklers, road sweeping, covered storage and truck washing.")
        + L.stmt(f"We take our environmental responsibilities seriously and report on them with care. {ctx.claim('VAJ-08')} {ctx.claim('VAJ-07')}")
        + L.callout("Environmental compliance system", items=["Legal register covering all applicable environmental laws and permits", "Monthly compliance reviews by plant heads and quarterly review by the executive committee", "Third-party environmental audits at selected sites each year", "Dedicated environmental control rooms operating around the clock"])
        + L.p("Ambient air quality is measured at stations inside and outside the plant boundary, and data is shared with the regulator. In the township and at the mine, we run public information boards showing air quality readings so that neighbours can see what we see.")
        + L.h3("Other emissions and noise")
        + L.p("Beyond particulates, sulphur oxides and nitrogen oxides, we manage volatile organic compounds, noise and vibration associated with blasting and heavy equipment. Blasting follows a protocol designed with technical advisers, and monitors record ground vibration at the nearest habitations.")
        + L.p("We invest in training of operators and maintenance staff on pollution control equipment, because even the best technology depends on the people who run it. Equipment availability is tracked as a key indicator, and preventive maintenance is scheduled so that shutdowns for pollution control repairs are planned and brief.")
    )
    return ch("Air quality and compliance", "Controls, monitoring and the way we manage compliance", b)


def ch_people(ctx, sec):
    b = (
        L.p("Making steel and power is inherently hazardous work. Hot metal, molten slag, heavy rotating equipment, gases, working at height and mine haul roads all demand vigilance. Our first value, safety first, is more than a slogan: it shapes how we plan work, design plants and reward behaviour.")
        + L.h3("Safety management")
        + L.p("Our occupational health and safety management system is certified to ISO 45001 and covers employees and contractors at all sites. Hazards are identified through job safety analyses, process hazard studies and field walkdowns. Contractors are inducted, trained and assessed before access, and permit-to-work systems control high-risk activities such as hot work, confined space entry and electrical isolation.")
        + L.stmt(f"We keep a close watch on safety performance and share it openly with the workforce. {ctx.claim('VAJ-09')} {ctx.claim('VAJ-10')}")
        + L.callout("Safety programmes", items=["Critical risk controls for ten activities with highest potential for harm", "Behavioural safety observations at every shift", "Virtual reality simulators for confined space and crane operations", "Safety committees with equal worker and management representation", "Annual safety week and recognition for near-miss reporting"])
        + L.h3("Health and wellbeing")
        + L.p("Occupational health centres at the integrated plant, the mine and the township provide periodic examinations, vaccination, ergonomic assessments and emergency response. Employee assistance programmes offer confidential counselling, and wellness camps address nutrition, hypertension and diabetes screening.")
        + L.h3("Learning and careers")
        + L.p("We run a graduate engineer trainee programme, a technician apprenticeship scheme with industrial training institutes, and leadership programmes in partnership with management institutes. Each employee has a development plan, and mobility between plants is encouraged to build broader experience.")
        + L.p("Industrial relations remain cordial. Recognised unions represent most workmen at the integrated plant, and long-term wage settlements are negotiated through bipartite discussions. Grievance forums operate at each site and escalate unresolved matters to a joint committee.")
    )
    return ch("People and safety", "Protecting and developing the people who make steel", b)


def ch_di(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.p("A steel company is often imagined as a male preserve. We want that to change. Our diversity and inclusion policy commits us to equal opportunity in hiring, pay, development and promotion, and to a workplace free of harassment and discrimination. The policy applies to all employees and, through contract terms, to contractors.")
        + L.stmt(f"We track a number of indicators of inclusion, among them how earnings are shared across the workforce. {ctx.claim('VAJ-12')} We recognise that the share is lower than we would like, in part because of the historical composition of the industry, and we are working to broaden the pipeline.")
        + L.figure(ctx.img("women.png"), "<b>Figure 12.1</b> Gross wages paid to women as a percentage of total gross wages paid, FY2020 to FY2025.")
        + L.table("Women's share of gross wages", ["Indicator"] + ctx.fy, [["% of total gross wages"] + [f"{x:.1f}" for x in t["women_wage_pct"]]],
                  src="Gross wages include basic pay, allowances, overtime and bonus, for permanent employees and workers, as defined in the BRSR Core.")
        + L.h3("Building the pipeline")
        + L.p("Our campus recruitment now targets engineering colleges with strong women enrolment, and we have introduced scholarships for women students at technical institutes near our sites. Shopfloor roles that were once closed to women, including control room operation, crane driving and laboratory work, are open and actively promoted.")
        + L.callout("Inclusion initiatives", items=["Women in manufacturing mentoring circles", "Crèche, flexible hours and return-to-work support after parental leave", "Accessible infrastructure and assistive technology for employees with disabilities", "Internal Committee under the POSH Act at each location, with annual training"])
    )
    return ch("Diversity and inclusion", "Widening who makes steel", b)


def ch_community(ctx, sec):
    b = (
        L.p("The communities around our plants and mine are our closest stakeholders. Their schools, clinics, roads and livelihoods are the best indicator of whether our presence is a force for good. Our corporate social responsibility programme, governed by Section 135 of the Companies Act, 2013, is designed in consultation with them.")
        + L.kpis([("Rs 118 crore", "CSR and community investment, FY2025"), ("Over 90", "Villages in programme areas"), ("6", "Focus themes")])
        + L.figure(ctx.img("csr.png"), "<b>Figure 13.1</b> CSR and community investment by theme, FY2025 (Rs crore).")
        + L.h3("Education and skilling")
        + L.p("We support government and community schools with infrastructure, teacher training and digital classrooms. Vocational training centres in Jharsuguda and Keonjhar prepare young people for jobs in welding, fitting, electrical work and heavy equipment operation, with placement support to local employers.")
        + L.h3("Health and nutrition")
        + L.p("Mobile health clinics visit remote villages on a fixed schedule, offering consultation, diagnostics and referral. Special programmes address maternal and child health, anaemia and tuberculosis screening, run with district health authorities.")
        + L.h3("Livelihoods and enterprise")
        + L.p("Women's self-help groups receive training and market linkages for agricultural, food processing and handicraft enterprises. Farmer producer organisations are supported with improved seed, irrigation and aggregation facilities.")
        + L.callout("How we involve communities", "Village development committees help set priorities, monitor delivery and review grievances. Annual social audits by an independent agency verify that projects reach intended beneficiaries.")
        + L.p("We also provide emergency relief. During the cyclone season we mobilised our township and plant resources for evacuation support, food distribution and restoration of power supply to neighbouring villages.")
        + L.notes(["CSR spend figures are drawn from the Board's CSR Committee report and are net of administrative overheads.", "Programme area village counts are approximate."])
    )
    return ch("Community and social investment", "Shared prosperity around our sites", b)


def ch_governance(ctx, sec):
    b = (
        L.p("Good governance is the foundation on which every other commitment in this report rests. Our Board of Directors comprises twelve members, including a majority of independent directors and two women directors. The roles of Chairman and Managing Director are combined, balanced by a lead independent director who chairs executive sessions of the independent members.")
        + L.h3("Board oversight of sustainability")
        + L.p("The Risk and Sustainability Committee, chaired by an independent director, meets at least four times a year. It reviews the sustainability strategy, enterprise risks including climate, major incidents, and the integrity of disclosures. An executive Sustainability Steering Committee chaired by the Managing Director coordinates delivery across functions.")
        + L.callout("Board committees", items=["Audit Committee", "Nomination and Remuneration Committee", "Stakeholders Relationship Committee", "Corporate Social Responsibility Committee", "Risk and Sustainability Committee"])
        + L.h3("Ethics and conduct")
        + L.p("Our Code of Conduct sets out expectations on integrity, conflicts of interest, gifts and hospitality, fair competition and protection of company assets. All employees certify annually that they have read and will follow the Code, and mandatory e-learning covers anti-corruption, insider trading and data privacy.")
        + L.p("A vigil mechanism administered by an independent ethics helpline allows employees, contractors and members of the public to raise concerns anonymously. Reports are investigated by a committee that reports to the Audit Committee, and the outcome of every substantiated case is tracked to closure.")
        + L.h3("Risk management")
        + L.p("Our enterprise risk management framework identifies, scores and mitigates risks across strategic, operational, financial, compliance and sustainability categories. Top risks are reviewed by the Board each quarter, and key risk owners present their mitigation plans. Climate, water, community and safety risks feature in the corporate risk register alongside commodity, regulatory and technology risks.")
        + L.p("We maintain policies on human rights, anti-bribery, responsible lobbying, tax transparency and data protection. We do not make political contributions. We are members of industry associations including those representing steel producers, mining companies and industrial power users, and we declare our positions on public policy openly.")
        + L.notes(["Board composition is as at 31 March 2025.", "Policies are available on the investor relations section of the company website."])
    )
    return ch("Governance and ethics", "Board oversight, conduct and risk management", b)


def ch_supply(ctx, sec):
    b = (
        L.p("Our value chain begins in mines and ends in buildings, vehicles and machines. The suppliers that provide coking coal, fluxes, alloys, refractories, consumables and logistics services influence our footprint as much as our own operations do. We therefore expect them to meet standards on safety, labour, environment and ethics, and we support them in doing so.")
        + L.h3("Responsible sourcing")
        + L.p("Our Supplier Code of Conduct, which forms part of every purchase order, covers legal compliance, prohibition of child and forced labour, freedom of association, health and safety, environmental management and anti-corruption. Critical suppliers undergo a risk screening and, where warranted, an on-site assessment by our procurement and EHS teams.")
        + L.p("Raw material sourcing is increasingly shaped by traceability. We require documentation of origin for imported coking coal, and we participate in industry initiatives on responsible steel and mining.")
        + L.stmt(f"Understanding our indirect emissions is the next frontier of our climate work. {ctx.claim('VAJ-14')} We are strengthening supplier data collection and refining our calculation methods so that future disclosure rests on a firmer foundation.")
        + L.callout("Supplier engagement", items=["Annual supplier meets on safety, quality and sustainability", "Training for contractors on working at height and confined space entry", "Prompt payment commitments for small enterprises", "Preference for local vendors for non-critical goods and services"])
        + L.h3("Customers and product stewardship")
        + L.p("Customers increasingly ask for environmental product declarations and information on the carbon content of steel. We are preparing product-level declarations for key grades and engaging with customers in the automotive and infrastructure segments on low-carbon steel offerings. Quality and safety of our products are governed by national standards and by customer specifications, and our laboratories are accredited to ISO/IEC 17025.")
        + L.p("Logistics matters too. Rail takes the largest share of our inbound and outbound freight, and we are investing in rail sidings, conveyors and covered wagons to reduce road dust and congestion around our plants. Our fleet contractors are encouraged to move to cleaner vehicles as supply becomes available.")
    )
    return ch("Supply chain and customers", "Working with partners to raise standards", b)


def ch_brsr(ctx, sec):
    t = ctx.co["true"]
    inten = data.intensity(ctx.co); rec = data.recovery_pct(ctx.co)
    sel = [3, 4, 5]
    b = (
        L.p("The table below presents selected indicators from our BRSR Core disclosures for the three most recent financial years. The full set of BRSR Core and other BRSR indicators is contained in our statutory filing with the stock exchanges for FY2025, which readers should consult for complete information.")
        + L.table("BRSR Core summary: selected indicators", ["Attribute", "Indicator", "Unit"] + [ctx.fy[i] for i in sel],
                  [["Economic", "Revenue from operations", "Rs crore"] + [data.inr(t["revenue_cr"][i]) for i in sel],
                   ["Environment", "GHG emission intensity (Scope 1 + 2 per Rs crore of turnover)", "tCO2e / Rs crore"] + [f"{inten[i]:,.0f}" for i in sel],
                   ["Environment", "Waste recovered, recycled or co-processed as a share of waste generated", "%"] + [f"{rec[i]:.1f}" for i in sel],
                   ["Social", "Gross wages paid to females as a percentage of total wages", "%"] + [f"{t['women_wage_pct'][i]:.1f}" for i in sel]],
                  src="Definitions follow the SEBI BRSR Core framework. Percentages are rounded to one decimal place; intensity is rounded to the nearest whole number.",
                  aligns=["l", "l", "l", "r", "r", "r"])
        + L.p("BRSR Core organises nine ESG attributes: greenhouse gas footprint, water footprint, energy footprint, embracing circularity, enhancing employee wellbeing and safety, enabling gender diversity in the workplace, enabling inclusive development, fairness in engaging with customers and suppliers, and openness of business. Our summary here follows the attributes in which we report comparable multi-year trends.")
        + L.callout("Basis of preparation", items=["Reporting boundary is as described in the section on this report", "Turnover is revenue from operations in the audited consolidated financial statements", "Wage data covers permanent employees and workers", "Waste recovery covers hazardous and non-hazardous waste"])
        + L.p("Readers who need additional indicators, including energy, water, safety and emissions by scope, should refer to the statutory BRSR filing, which contains the full set in the prescribed format.")
        + L.notes(["BRSR Core indicators are defined in SEBI circular SEBI/HO/CFD/CFD-SEC-2/P/CIR/2023/122.", "Previous year values are unchanged from the figures reported last year."])
    )
    return ch("BRSR Core summary", "Selected indicators for FY2023 to FY2025", b)


def ch_assurance(ctx, sec):
    b = (
        L.p("Credible reporting depends on controls over data and on challenge from independent parties. Our reporting process is overseen by the Chief Financial Officer and the Head of Sustainability, with data owners at each facility certifying their submissions each quarter. Data is consolidated on a central platform with validation rules, variance analysis and an audit trail of changes.")
        + L.h3("Three lines of defence")
        + L.p("The first line consists of plant data owners and function heads who are responsible for accuracy. The second line is the corporate sustainability and finance team, which reviews submissions, checks calculations and reconciles to source records. The third line is internal audit, which includes sustainability data controls in its annual plan and reports findings to the Audit Committee.")
        + L.stmt(f"Independent assurance adds a further layer of confidence. {ctx.claim('VAJ-13')} The engagement scope, the standards applied and the basis for the conclusions are documented in the assurance engagement file maintained by the company.")
        + L.callout("Reporting integrity measures", items=["Quarterly sign-off by facility heads on environmental and safety data", "Reconciliation of energy, fuel and production data to commercial records", "Internal audit of selected indicators each year", "Board Audit Committee review of the sustainability report before publication"])
        + L.p("We continue to enhance the maturity of our data systems. Planned improvements include automated meter integration, digital permit-to-work and incident capture, and a workflow tool for supplier data. We also participate in industry peer reviews that compare definitions and methods, with the aim of improving comparability across companies in the sector.")
        + L.p("Feedback from stakeholders, including investors and rating agencies, is considered through our reporting improvement log. Observations raised in the year related to data granularity and boundary clarity, and an action plan has been agreed for the coming reporting cycle.")
    )
    return ch("Assurance and reporting integrity", "How we govern our data", b)


def ch_gri(ctx, sec):
    topic = {"about": sec["about"], "message": sec["message"], "glance": sec["glance"], "materiality": sec["materiality"], "strategy": sec["strategy"],
             "climate": sec["climate"], "water": sec["water"], "waste": sec["waste"], "bio": sec["bio"], "air": sec["air"], "people": sec["people"],
             "di": sec["di"], "community": sec["community"], "governance": sec["governance"], "supply": sec["supply"], "assurance": sec["assurance"]}
    body = C.gri_index(topic, "<b>Statement of use.</b> " + ctx.name + " has reported the information cited in this GRI content index for the period 1 April 2024 to 31 March 2025 with reference to the GRI Standards. Where a disclosure is shown as a cross-reference, the information is available in the statutory BRSR filing for FY2025.",
                       partial=("305-3", "305-7", "403-9", "403-10", "2-27"),
                       withheld=("302-1", "302-4", "303-3", "303-4", "303-5", "305-1", "305-2", "305-5"))
    return ch("GRI content index", "Where to find each disclosure", body, raw=True, cls="gri")


def ch_glossary(ctx, sec):
    extra = {"Blast furnace": "A furnace in which iron ore is reduced to molten iron using coke and hot air.",
             "DRI": "Direct reduced iron, produced by reducing iron ore in solid state with gas or coal.",
             "Pellet": "Hardened balls of fine iron ore used as blast furnace or DRI feed.",
             "Slag": "A non-metallic by-product formed during smelting and steelmaking, used in cement and roads.",
             "Sinter": "Agglomerated fine ore and fluxes used as blast furnace charge.",
             "OCEMS": "Online continuous emission monitoring system.", "ESP": "Electrostatic precipitator, a particulate control device.",
             "Beneficiation": "Processing of ore to improve its grade before smelting."}
    base = {k: v for k, v in C.BASE_TERMS.items() if "assurance" not in k}
    body = C.glossary({**base, **extra})
    return ch("Glossary", "Terms and abbreviations", body, cls="glossary")


def ch_disclaimer(ctx, sec):
    return ch("Forward-looking statements", "Important notice to readers", C.forward_looking(ctx))
