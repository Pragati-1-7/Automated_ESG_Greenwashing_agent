"""Sahyadri Cement Industries Ltd: integrated annual report, mixed profile. Tables use TRUE values only for
metrics whose claims align (Scope 1, renewable share, waste recovered, assurance) plus revenue."""
from __future__ import annotations
from . import layout as L, charts, common_text as C, data

ORDER = ["about", "message", "glance", "materiality", "strategy", "climate", "water", "waste", "bio", "air",
         "people", "di", "community", "governance", "supply", "brsr", "assurance", "letter", "gri", "glossary", "disclaimer"]
TOC_GROUPS = [{"at": "01", "label": "Introduction"}, {"at": "06", "label": "Environment"}, {"at": "11", "label": "Social"},
              {"at": "14", "label": "Governance and value chain"}, {"at": "16", "label": "Disclosures, assurance and reference"}]


def make_charts(ctx):
    pal, t = ctx.pal, ctx.co["true"]
    charts.bar_chart(ctx.path("revenue.png"), ctx.fy, t["revenue_cr"], pal, ylabel="Rs crore", h=2.2)
    charts.bar_chart(ctx.path("scope1.png"), ctx.fy, [round(x / 1e6, 2) for x in t["scope1_tco2e"]], pal, ylabel="million tCO2e", fmt="{:.2f}", h=2.3, ylim=(0, 7.2))
    charts.line_chart(ctx.path("re.png"), ctx.fy, {"Renewable share of electricity (%)": t["re_pct"]}, pal, ylabel="% of electricity", fmt="{:.0f}", h=2.3)
    charts.bar_chart(ctx.path("waste.png"), ctx.fy, [round(x / 1e5, 2) for x in t["waste_recovered_t"]], pal, ylabel="lakh tonnes", fmt="{:.2f}", h=2.2)
    charts.materiality(ctx.path("materiality.png"), [
        ("Climate and decarbonisation", 9.0, 8.8, 4), ("Alternative fuels and raw materials", 8.2, 7.2, 3), ("Dust and air emissions", 7.8, 8.7, 3),
        ("Water security", 7.0, 8.0, 3), ("Health and safety", 8.7, 9.2, 4), ("Quarry rehabilitation and biodiversity", 6.2, 7.6, 2),
        ("Low-carbon products", 8.5, 6.4, 3), ("Local employment", 6.0, 7.0, 2), ("Responsible sourcing", 6.6, 5.8, 2),
        ("Ethics and governance", 7.9, 7.3, 3), ("Inclusion and diversity", 5.0, 6.2, 1), ("Community development", 5.5, 7.4, 2)], pal)
    charts.timeline(ctx.path("timeline.png"), [
        ("FY2021 to FY2024", "Build the base", ["Heat and power audits", "Waste heat recovery projects", "Alternative fuel feeding systems"]),
        ("FY2025 to FY2028", "Scale the levers", ["Blended cement mix", "More renewable power", "Calcined clay trials"]),
        ("FY2029 to FY2035", "Break through", ["Kiln fuel switching", "Carbon capture pilots", "Low-carbon concrete range"]),
        ("Beyond FY2035", "Net zero path", ["Industry roadmap alignment", "Supplier partnerships"]),
    ], pal)
    charts.hbar_chart(ctx.path("csr.png"), ["Education and skilling", "Health and sanitation", "Water and watershed", "Livelihoods", "Environment", "Rural infrastructure"],
                      [11, 9, 8, 6, 4, 3], pal, xlabel="Rs crore, FY2025", h=2.3)


def chapters(ctx):
    sec = {k: f"{i + 1:02d}" for i, k in enumerate(ORDER)}
    ctx.back_text = ("<p>Investor Relations and Sustainability<br>Sahyadri House, Senapati Bapat Road, Pune 411 016, Maharashtra</p>"
                     "<p>sustainability@sahyadricement.example | www.sahyadricement.example</p><p>CIN L26942MH2001PLC131870 | NSE: SAHYCEM</p>")
    return [globals()[f"ch_{k}"](ctx, sec) for k in ORDER]


def ch(title, subtitle, body, **kw):
    return {"title": title, "subtitle": subtitle, "body": body, **kw}


def ch_about(ctx, sec):
    b = (
        L.p(f"This Integrated Annual Report of {ctx.name} brings together our financial and non-financial performance for the year from 1 April 2024 to 31 March 2025. It follows the integrated reporting approach, and tries to show how our strategy, governance, operations and the context in which we work create value over time for shareholders, employees, customers and the communities near our plants.")
        + L.h3("Scope and boundary")
        + L.p("The report covers our four facilities: the Chandrapur Integrated Cement Plant and the Rajura Limestone Mine in Maharashtra, the Gulbarga Cement Works in Karnataka and the Raigad Grinding Unit in Maharashtra, along with our registered office in Pune. Environmental data is consolidated on an operational control basis, and social data covers permanent employees and, where stated, contract workers.")
        + L.p("Financial data is drawn from our audited financial statements prepared under Ind AS. Non-financial data has been compiled by plant teams, reviewed by the corporate sustainability cell and, for selected BRSR Core indicators, subjected to independent assurance, as set out in the assurance section.")
        + C.about_frameworks_callout()
        + L.h3("Navigating the report")
        + L.p("Sections 2 to 5 describe who we are and how we choose what to focus on. Sections 6 to 15 cover the environmental, social and governance topics in turn. The BRSR Core summary, the independent assurance report, the GRI content index and the glossary follow. Cross-references in the margin notes point to related material.")
        + L.pull("An integrated report should read like one story told by one company.", "Chief Financial Officer")
        + L.p("The Board of Directors approved this report on 28 May 2025 on the recommendation of the Audit Committee. Comments and questions are welcome at the address on the back cover.")
        + L.notes(["Operational control: we account for 100 per cent of emissions and resource use at facilities we operate.", "Rounding differences may arise in some tables."])
    )
    return ch("About this report", "Boundary, period, frameworks and approach", b)


def ch_message(ctx, sec):
    b = (
        L.p("Dear shareholders,")
        + '<p class="dropcap">' + "India is building at a pace the country has not seen in a generation. Roads, ports, metros, housing and data centres are rising everywhere, and each of them is made with cement. That gives our industry an extraordinary opportunity, and an equally large responsibility, because cement is also one of the hardest sectors in which to cut carbon." + '</p>'
        + L.p("Against that backdrop, Sahyadri Cement delivered another year of steady growth. Volumes rose, margins held up despite volatile fuel prices, and our balance sheet remained strong. Beyond the numbers, I am proud of the way our people took care of one another and of our neighbours throughout the year.")
        + L.stmt(f"Our climate work is gradual but measurable. {ctx.claim('SAH-01')} We achieved this while growing output, through better kiln efficiency, higher use of alternative fuels and a shift to cleaner power.")
        + L.p("We also made headway on the nature of our energy mix. A new waste heat recovery system at Chandrapur began contributing to our power needs, and our open access renewable contracts matured. Further capacity is being planned for the coming years, subject to regulatory approvals.")
        + L.pull("Cement will be needed for decades. Our task is to make each tonne lighter on the planet.", "Chairman")
        + L.p("Our governance of sustainability has also matured. The Board's Sustainability Committee now reviews a dashboard of environmental and social indicators each quarter, and senior management incentives include goals tied to safety, energy efficiency and alternative fuel use.")
        + L.p("I thank my colleagues on the Board, our employees, our dealers and customers, and the communities of Chandrapur, Kalaburagi and Raigad for their trust. I invite you to read this report and to tell us how we can do better.")
        + '<div class="sign">Yours sincerely,<b>Ashok Deshmukh</b><span>Chairman<br>Pune, 28 May 2025</span></div>'
        + L.callout("Highlights of the year", items=["Higher volumes with stable profitability", "Waste heat recovery unit commissioned at Chandrapur", "Expanded use of alternative fuels and raw materials", "Further strengthening of safety governance at quarry and plant"])
    )
    return ch("Chairman's message", "Building responsibly for a growing India", b)


def ch_glance(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.kpis([("Rs 14,100 crore", "Revenue, FY2025"), ("12.5 MTPA", "Cement capacity"), ("8.0 MTPA", "Limestone mining capacity"), ("4", "Operating facilities")])
        + L.p(f"{ctx.name} is a mid-sized cement producer headquartered in Pune. We make ordinary Portland, Portland pozzolana and Portland slag cements, sold under the Sahyadri brand through a dealer network that covers Maharashtra, Karnataka, Telangana, Goa and parts of Madhya Pradesh.")
        + L.p("Our integrated plants at Chandrapur and Gulbarga combine limestone crushing, raw grinding, pyroprocessing, cement grinding and packing. The grinding unit at Raigad serves the Konkan and Mumbai markets, drawing clinker by rail and sea from our integrated plants, and supplying a growing share of blended cements.")
        + C.facilities_table(ctx)
        + L.figure(ctx.img("map.png"), "<b>Figure 3.1</b> Our facilities in Maharashtra and Karnataka. Marker positions in the enlarged panel are nudged to avoid overlap.")
        + L.p("Roughly 3,900 people work at our facilities and offices, supported by contractors in mining, packing and logistics. The company is listed on the National Stock Exchange, and promoters hold a majority stake alongside a base of institutional and retail shareholders.")
        + L.table("Revenue from operations", ["Financial year"] + ctx.fy, [["Rs crore"] + [data.inr(v) for v in t["revenue_cr"]]],
                  src="Source: audited financial statements. Rs crore at current prices.")
        + L.figure(ctx.img("revenue.png"), "<b>Figure 3.2</b> Revenue from operations, FY2020 to FY2025 (Rs crore).")
        + L.callout("What we stand for", "Strength, stewardship and service. These three words appear on every plant gate, and we ask ourselves each quarter whether our decisions would pass that test.")
    )
    return ch("Company at a glance", "Plants, products and markets", b)


def ch_materiality(ctx, sec):
    b = (
        L.p("We identify material topics through a structured process, repeated every two years. In FY2025 we reviewed topics through desk research on peer disclosures and regulatory trends, workshops with functional heads, interviews with major institutional investors and large customers, and consultation with village representatives around our quarries and plants.")
        + L.p("Each topic was rated on its potential effect on the company's financial performance and on the significance of its impacts on the economy, environment and people. The scores were moderated by the Sustainability Committee, which also decided where the line between priority and monitored topics should fall.")
        + L.figure(ctx.img("materiality.png"), "<b>Figure 4.1</b> Materiality matrix. Highlighted bubbles are priority topics for management attention and disclosure.")
        + L.h3("Key takeaways")
        + L.p("Climate and decarbonisation, health and safety, and dust and air emissions occupy the top right of the matrix. Investors added questions about low-carbon product strategy and capital allocation, while community members emphasised water access, quarry blasting and local employment.")
        + L.callout("Engagement calendar", items=["Quarterly results calls with analysts", "Annual dealer and contractor meets", "Monthly village liaison meetings at each plant", "Annual dialogue with regulators and industry bodies"])
    )
    return ch("Materiality and stakeholders", "Where we focus and why", b)


def ch_strategy(ctx, sec):
    b = (
        L.p("Our strategy rests on a simple idea: grow the business by making better, lower-carbon cement, and make the business stronger by managing the resources it depends on with care. Four strategic themes organise our work, and each is supported by a roadmap, an owner and a set of internal indicators.")
        + L.h3("Efficient operations")
        + L.p("Kiln stability, heat recovery, optimised grinding and predictive maintenance cut energy use and reduce variability. We use advanced process control on all kilns and are rolling out digital twins at Chandrapur.")
        + L.h3("Cleaner inputs")
        + L.p("We replace conventional fuels and raw materials with alternatives, including biomass, refuse-derived fuel, fly ash and slag, in partnership with municipal bodies and industrial generators.")
        + L.figure(ctx.img("timeline.png"), "<b>Figure 5.1</b> Roadmap by phase. Phases describe themes of work rather than quantified commitments.")
        + L.h3("Lower-carbon products")
        + L.p("The largest lever in cement is the clinker content of the product. We are increasing the share of blended cements, testing calcined clay and limestone blends, and working with customers on mix design.")
        + L.h3("Responsible neighbours")
        + L.p("Our quarries and plants sit among farms and villages. We aim to be considerate, from dust control and blast management to local hiring and water sharing.")
        + L.stmt(f"We have also aligned our long-term ambition with that of our industry. {ctx.claim('SAH-12')} The roadmap above shows the stages through which we plan to progress, and we will report on how technology, policy and costs evolve.")
        + L.callout("Capital allocation", "Sustainability projects compete for capital on the same footing as other investments, with an internal shadow price for carbon applied in project appraisal.")
    )
    return ch("Strategy and targets", "Four themes and a phased roadmap", b)


def ch_climate(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.p("Cement manufacture releases carbon dioxide in two ways: from the burning of fuel in the kiln and from the chemical decomposition of limestone into lime. The second source, process emissions, cannot be avoided by switching fuels, which is why the industry's climate challenge is unusually hard.")
        + L.h3("Governance and risk")
        + L.p("Climate matters are overseen by the Board's Sustainability Committee. Management has mapped transition risks such as carbon pricing, policy on blended cements and demand shifts, and physical risks, including heat and monsoon variability, to each plant. Scenario analysis informs capital plans.")
        + L.h3("Emissions")
        + L.stmt(f"Our direct emissions have declined while volumes have grown. The chart below shows the trend in our Scope 1 emissions, which come mainly from clinker production and kiln fuel.")
        + L.figure(ctx.img("scope1.png"), "<b>Figure 6.1</b> Scope 1 GHG emissions, FY2020 to FY2025 (million tCO2e).")
        + L.stmt(f"Clinker content is the most important determinant of cement's carbon footprint. {ctx.claim('SAH-10')} We continue to raise the share of blended cements in our mix.")
        + L.h3("Energy")
        + L.p("Thermal energy for the kiln and electrical energy for grinding together define our energy footprint. Waste heat recovery, high-efficiency fans and mills, and variable speed drives have reduced the electricity we draw per tonne of cement.")
        + L.stmt(f"{ctx.claim('SAH-02')} The waste heat recovery system at Chandrapur was a significant contributor, supplemented by open access wind and solar power.")
        + L.figure(ctx.img("re.png"), "<b>Figure 6.2</b> Renewable share of electricity consumed, FY2020 to FY2025 (per cent).")
        + L.callout("Decarbonisation levers", items=["Alternative fuels and raw materials", "Blended cement and calcined clay", "Waste heat recovery and efficient equipment", "Renewable power and storage", "Carbon capture, utilisation and storage pilots"])
        + L.notes(["Scope 1 includes process and fuel emissions of the integrated plants, calculated using the GCCA Cement CO2 and Energy Protocol.", "Renewable share includes waste heat recovery as per the company's reporting policy, which is disclosed in the basis of preparation."])
    )
    return ch("Climate and energy", "Cutting carbon in a hard-to-abate industry", b)


def ch_water(ctx, sec):
    b = (
        L.p("Cement is not a water-intensive industry compared with many others, but our plants operate in regions that are vulnerable to drought, notably in Vidarbha and north Karnataka. Water is central to our social licence, and we pursue a policy of reducing freshwater use, recycling and harvesting rainwater at every site.")
        + L.h3("Efficiency and reuse")
        + L.p("Process water is recirculated through cooling towers and settling ponds. Treated sewage from our colonies is used for dust suppression and horticulture, and plants operate with minimal liquid discharge. Dry process kilns and air-cooled equipment reduce water needs from the outset.")
        + L.stmt(f"We also invest in harvesting and recharge beyond our boundaries. {ctx.claim('SAH-11')} The programme includes mine pit storage, check dams, farm ponds and roof-top harvesting in plant colonies.")
        + L.callout("Water programmes", items=["Quarry pit rainwater storage for plant and community use", "Check dams and farm ponds in partnership with village committees", "Groundwater level monitoring around Chandrapur and Gulbarga", "Water literacy sessions in schools"])
        + L.p("Our quarry at Rajura collects significant rainfall in worked-out pits, and the water is used for dust suppression and offered to neighbouring farmers during the lean season. Independent hydrogeologists review the impact of dewatering on nearby wells each year.")
        + L.p("We are building a basin-level view of water risk using public datasets and our own measurements, and intend to disclose more about site-level water balances in coming reports.")
    )
    return ch("Water", "Using less and giving back to the catchment", b)


def ch_waste(ctx, sec):
    t = ctx.co["true"]
    b = (
        L.p("Cement kilns are well suited to recover value from waste. Operating at very high temperatures with long residence times, they can destroy organic compounds and incorporate mineral residues in clinker without generating additional ash. This is called co-processing, and it is an important part of our strategy.")
        + L.stmt(f"We source alternative fuels and raw materials from industry, agriculture and municipal systems. {ctx.claim('SAH-03')} The tonnage reflects both agricultural biomass and industrial residues such as fly ash and slag.")
        + L.figure(ctx.img("waste.png"), "<b>Figure 8.1</b> Waste co-processed and recovered, FY2020 to FY2025 (lakh tonnes).")
        + L.table("Waste co-processed and recovered", ["Indicator"] + ctx.fy, [["Lakh tonnes"] + [f"{x / 1e5:.2f}" for x in t["waste_recovered_t"]]],
                  src="Quantities are weighed at the receiving point. One lakh equals 100,000.")
        + L.h3("How co-processing works")
        + L.p("Wastes arrive after pre-processing and testing against acceptance criteria. Combustible wastes are fed into the kiln burner or calciner, and mineral wastes into the raw mill or cement mill. Continuous monitoring ensures that stack emissions stay within norms and that clinker quality is unaffected.")
        + L.callout("Waste partners", "We work with municipal corporations, industrial parks, power plants and biomass aggregators. A dedicated team vets each source for composition, hazard and consistency before approval.")
        + L.p("Our own waste is also managed through reduction and reuse. Kiln dust is recycled into the process, packaging residues are returned to authorised recyclers, and used oil is sent to registered re-refiners.")
    )
    return ch("Waste and circularity", "Co-processing as a service to society", b)


def ch_bio(ctx, sec):
    b = (
        L.p("Limestone quarrying changes landscapes. Our task is to limit that change, rehabilitate land as we go and protect the plants and animals that share it. Rajura is our principal quarry, in a mixed landscape of farms and scrub near the Wardha valley.")
        + L.stmt(f"We watch the land around our mine closely. {ctx.claim('SAH-05')} We use satellite alerts alongside field visits to confirm this and to detect any changes early.")
        + L.h3("Rehabilitation")
        + L.p("Quarry rehabilitation follows a plan approved with the mine closure plan. Overburden is used to backfill worked-out areas where feasible, topsoil is stored for reuse, and benches are planted with native species in consultation with the Forest Department.")
        + L.callout("Nature initiatives", items=["Native species nursery near Rajura", "Green belt around plants", "Pond and wetland restoration", "Bird and butterfly monitoring with local naturalists"])
        + L.p("Around the plants, we maintain green belts, protect natural drainage lines and avoid works during nesting seasons wherever practical. Blasting is carefully controlled to limit vibration and noise.")
        + L.p("We are beginning to assess our nature-related dependencies and impacts using the TNFD LEAP approach, starting with the Chandrapur cluster, and will share findings as the work advances.")
    )
    return ch("Biodiversity and land", "Responsible quarrying and rehabilitation", b)


def ch_air(ctx, sec):
    b = (
        L.p("Dust is the most visible environmental impact of cement making, and the one our neighbours care about most. Our plants are equipped with bag filters, electrostatic precipitators and enclosed conveyors, and we monitor stack and ambient air quality continuously and report the data to the regulators.")
        + L.h3("Monitoring")
        + L.p("Continuous emission monitoring systems at kilns, coolers and mills measure particulate matter, sulphur dioxide and nitrogen oxides, and the data stream is accessible to the Central and State Pollution Control Boards. Ambient stations in and around the plant and in nearby villages give an independent view.")
        + L.stmt(f"We report on our emission performance in plain terms. {ctx.claim('SAH-07')}")
        + L.h3("Regulatory compliance")
        + L.stmt(f"Compliance with the conditions of our consents and clearances is central to our licence to operate. {ctx.claim('SAH-04')}")
        + L.callout("Dust control measures", items=["Covered raw material storage and enclosed transfer points", "Paved haul roads with sprinkling and sweeping", "Wheel washing at plant exits", "Bag filter replacement planned ahead of failure"])
        + L.p("Our legal compliance system tracks obligations by plant and quarry, assigns owners and escalates overdue items. Regular third-party audits test the system. We share learnings from near-misses across plants so that fixes are made once and applied everywhere.")
        + L.p("In recent years we have invested in upgrading dust collection at older units and in more reliable instrumentation, because accurate measurement is the basis for good control.")
    )
    return ch("Air quality and compliance", "Controlling dust and meeting our obligations", b)


def ch_people(ctx, sec):
    b = (
        L.p("Cement plants and quarries combine heavy machinery, high temperatures and vehicle movements. The safety of employees and contractors is our first priority, and we expect every leader to be visible, curious and consistent on safety.")
        + L.h3("Safety management")
        + L.p("Our management system is aligned to ISO 45001. Contractors are inducted and assessed before work starts, permit-to-work procedures cover high-risk jobs, and each plant has a safety committee with worker representation. We use leading indicators such as near-miss reports, safety observations and closure of audit actions to detect problems before they cause injuries.")
        + L.stmt(f"We communicate openly about outcomes. {ctx.claim('SAH-06')}")
        + L.callout("Safety initiatives", items=["Vehicle movement control and speed management in quarries", "Machine guarding and lock-out tag-out audits", "Safety leadership programme for plant heads and supervisors", "Driver training for bulk cement transporters"])
        + L.h3("Health and wellbeing")
        + L.p("Occupational health centres provide periodic medical examinations, noise and dust exposure screening, and emergency care. Wellness programmes address nutrition, fitness and stress, and employees can access confidential counselling.")
        + L.h3("Learning and development")
        + L.p("We invest in technical training on kiln operation, grinding, maintenance and electrical systems. A trainee engineers programme, an apprenticeship scheme with industrial training institutes and online learning modules support career growth. Job rotation across plants builds versatility.")
        + L.p("Industrial relations at our plants are cooperative. We recognise union representation where applicable, hold regular consultations and settle wages through negotiation.")
    )
    return ch("People and safety", "Looking after the people behind every bag of cement", b)


def ch_di(ctx, sec):
    b = (
        L.p("Our policy on equal opportunity commits us to hiring, paying and promoting people on merit, to a workplace free from harassment and to reasonable accommodation for people with disabilities. Cement has traditionally had few women in its workforce, and we are working to change that, starting with the pipeline.")
        + L.stmt(f"We track how earnings are shared across our workforce as one indicator of progress. {ctx.claim('SAH-08')}")
        + L.h3("Hiring and development")
        + L.p("Campus recruitment now includes engineering and management institutes with strong women enrolment. Shop floor opportunities in control rooms, laboratories, and packing and dispatch are being opened up with suitable training and infrastructure changes such as rest rooms and safe transport.")
        + L.callout("Inclusion at work", items=["Mentoring for women engineers in their first three years", "Flexible working and return-to-work support", "Internal Committee under the POSH Act, with annual awareness sessions", "Accessible infrastructure at offices and plants"])
        + L.p("We also take care to include local communities in our workforce. Pre-employment training for youth from villages near our plants has helped hundreds of them find work with us and our contractors.")
        + L.p("Inclusion is also a matter of respect in everyday behaviour, and our code of conduct training deals with it directly. Managers are expected to listen, to challenge bias and to make sure that every voice is heard.")
    )
    return ch("Diversity and inclusion", "A workplace open to more people", b)


def ch_community(ctx, sec):
    b = (
        L.p("The villages around our plants have lived with limestone quarries and cement for decades. Our relationship with them is long and, we hope, mutually beneficial. We support communities through a CSR programme designed with village representatives, and by providing employment and business opportunities close to our sites.")
        + L.kpis([("Rs 41 crore", "CSR and community spend, FY2025"), ("60+", "Villages in programme areas"), ("6", "Themes")])
        + L.figure(ctx.img("csr.png"), "<b>Figure 13.1</b> CSR spend by theme, FY2025 (Rs crore).")
        + L.h3("Education")
        + L.p("We support government schools with classrooms, science laboratories and teachers' training, and run a scholarship programme for girls from nearby villages. Vocational courses train youth in welding, electrical work and heavy vehicle driving.")
        + L.h3("Water and livelihoods")
        + L.p("Check dams, farm ponds and drip irrigation help farmers near the Rajura quarry to take a second crop. Self-help groups of women receive training and seed capital for small enterprises such as dairy, tailoring and food processing.")
        + L.h3("Health")
        + L.p("Mobile medical vans and health camps provide check-ups, eye care and referral support. We run awareness campaigns on hygiene and nutrition with local health workers.")
        + L.callout("Community voice", "Each plant holds monthly meetings with sarpanchs and village committees. Grievances are logged, assigned and reported back at the next meeting.")
        + L.notes(["CSR spend figures are as reported by the CSR Committee.", "Village counts are approximate."])
    )
    return ch("Community development", "Working with our neighbours", b)


def ch_governance(ctx, sec):
    b = (
        L.p("Our Board has eleven directors, of whom six are independent, and includes two women. The Chairman is a non-executive director, and the roles of Chairman and Managing Director are held by different people. Directors are chosen for their experience in industry, finance, engineering, law and public policy.")
        + L.h3("Committees")
        + L.p("The Audit Committee, the Nomination and Remuneration Committee, the Stakeholders Relationship Committee, the Corporate Social Responsibility Committee, the Risk Management Committee and the Sustainability Committee assist the Board. The Sustainability Committee, chaired by an independent director, reviews our ESG strategy, risks and disclosures.")
        + L.callout("Ethics at Sahyadri", items=["Code of Conduct signed annually by employees", "Anti-bribery and anti-corruption policy covering third parties", "Whistle-blower mechanism with independent ethics hotline", "Related party transaction policy reviewed by the Audit Committee"])
        + L.h3("Risk management")
        + L.p("The enterprise risk framework covers strategic, operational, financial, regulatory and ESG risks. Risk owners assess likelihood and impact, and top risks are reviewed by the Risk Management Committee each quarter. Climate, safety, water and community risks are included in the register alongside fuel prices, regulatory changes and counterparty exposure.")
        + L.p("The company has policies on human rights, data privacy, responsible advocacy, tax and conflict of interest. We do not make political contributions. We participate in the work of industry bodies, including the Cement Manufacturers' Association, and disclose our positions on public policy.")
        + L.p("Executive remuneration includes a variable component linked to financial and non-financial goals, including safety, energy and environmental measures, as approved by the Nomination and Remuneration Committee.")
    )
    return ch("Governance and ethics", "Board oversight, conduct and risk", b)


def ch_supply(ctx, sec):
    b = (
        L.p("Cement is a local business. Limestone comes from our own quarry, gypsum and coal from regional sources, fly ash and slag from nearby power and steel plants, and our products travel mostly by road and rail to markets within a few hundred kilometres. That gives us the chance to work closely with suppliers and to support small enterprises near our plants.")
        + L.h3("Sourcing standards")
        + L.p("Our Supplier Code of Conduct sets expectations on legal compliance, labour practices, health and safety, environmental management and ethics. Key suppliers and transporters are assessed on these criteria before onboarding and periodically thereafter.")
        + L.callout("Supplier engagement", items=["Transporter safety training and vehicle audits", "Digital tracking of deliveries to reduce idling and waiting", "Prompt payments for small suppliers", "Preference to local contractors for services"])
        + L.h3("Customers and product responsibility")
        + L.p("We are working with architects, builders and ready-mix producers on mix designs that deliver the same strength with less cement, and on durability, which extends the life of structures. Technical support teams visit sites to advise on curing, storage and handling. Product quality is controlled through accredited laboratories and national standards.")
        + L.h3("Logistics")
        + L.p("Rail dispatches from Chandrapur and Gulbarga reduce road traffic and associated emissions. Bulk cement tankers and rakes are increasingly used, cutting packaging waste. We continue to explore coastal shipping for the Konkan markets.")
        + L.p("Value chain emissions are an area where we are still building capability, and we intend to expand data collection from suppliers in coming years.")
    )
    return ch("Supply chain and customers", "Local sourcing and responsible products", b)


def ch_brsr(ctx, sec):
    t = ctx.co["true"]
    sel = [3, 4, 5]
    b = (
        L.p("This summary presents selected BRSR Core indicators for the last three financial years. The statutory BRSR filed with the stock exchanges contains the full set of indicators in the prescribed format.")
        + L.table("BRSR Core summary: selected indicators", ["Attribute", "Indicator", "Unit"] + [ctx.fy[i] for i in sel],
                  [["Economic", "Revenue from operations", "Rs crore"] + [data.inr(t["revenue_cr"][i]) for i in sel],
                   ["GHG footprint", "Total Scope 1 emissions", "tCO2e"] + [data.inr(t["scope1_tco2e"][i]) for i in sel],
                   ["Energy footprint", "Share of electricity from renewable sources", "%"] + [f"{t['re_pct'][i]:.1f}" for i in sel],
                   ["Circularity", "Waste co-processed and recovered", "tonnes"] + [data.inr(t["waste_recovered_t"][i]) for i in sel],
                   ["Openness", "Type of assurance on BRSR Core", "Category"] + [t["assurance_type"][i].capitalize() for i in sel]],
                  src="Definitions follow SEBI's BRSR Core framework. Assurance provider for FY2023 to FY2025: Mehta Kulkarni & Co, Chartered Accountants.",
                  aligns=["l", "l", "l", "r", "r", "r"])
        + L.p("The nine BRSR Core attributes cover greenhouse gas, water and energy footprints, circularity, employee wellbeing and safety, gender diversity, inclusive development, fairness to customers and suppliers, and openness of business. The indicators above are those for which we present comparable multi-year series in this report.")
        + L.callout("Basis of preparation", items=["Boundary as per the section on scope", "Renewable share includes waste heat recovery under company policy", "Waste co-processed covers alternative fuels and raw materials received from third parties", "Figures rounded where indicated"])
        + L.p("Further indicators, including water, safety and workforce measures, are provided in the statutory BRSR filing and discussed in the relevant sections of this report.")
        + L.notes(["See SEBI circular dated 12 July 2023 on BRSR Core.", "Prior-year values have not been restated."])
    )
    return ch("BRSR Core summary", "Selected indicators, FY2023 to FY2025", b)


def ch_assurance(ctx, sec):
    b = (
        L.p("Our reporting process is led by the Chief Financial Officer, with the corporate sustainability cell consolidating data submitted by plant teams. Each plant head certifies submissions quarterly. Internal audit tests controls over a sample of indicators each year.")
        + L.stmt(f"We have progressively extended the level of external assurance on our non-financial reporting. {ctx.claim('SAH-09')} The independent assurer's report follows this section.")
        + L.h3("Scope of assurance")
        + L.p("Assurance covers the BRSR Core indicators for FY2025 as filed. Mehta Kulkarni & Co, Chartered Accountants, performed the engagement, visiting the Chandrapur and Gulbarga plants and the Rajura mine, reviewing source records and re-performing selected calculations.")
        + L.callout("Our reporting controls", items=["Plant data certification each quarter", "Reconciliation with commercial records", "Annual internal audit of selected indicators", "Audit Committee review before publication"])
        + L.p("The observations of the assurer, including suggestions to improve data capture for alternative fuels and to document estimation methods, have been shared with management and an action plan has been agreed.")
    )
    return ch("Assurance and reporting integrity", "Controls and independent review", b)


def ch_letter(ctx, sec):
    body = C.assurance_letter(ctx, "Mehta Kulkarni & Co", "CA Prakash Mehta", "112233W", "Pune", "30 May 2025",
                              "The engagement covered the BRSR Core indicators for the year ended 31 March 2025 as presented in the Company's filing.")
    return ch("Independent assurance report", "Reasonable assurance on selected BRSR Core indicators", body, raw=True)


def ch_gri(ctx, sec):
    topic = {k: sec[k] for k in ["about", "message", "glance", "materiality", "strategy", "climate", "water", "waste", "bio", "air", "people", "di", "community", "governance", "supply", "assurance"]}
    body = C.gri_index(topic, f"<b>Statement of use.</b> {ctx.name} has reported the information cited in this GRI content index for the period 1 April 2024 to 31 March 2025 with reference to the GRI Standards.",
                       partial=("303-3", "303-4", "303-5", "305-3", "302-4", "304-3", "304-4"))
    return ch("GRI content index", "Where to find each disclosure", body, raw=True, cls="gri")


def ch_glossary(ctx, sec):
    extra = {"Clinker": "The intermediate product of the kiln, ground with gypsum and other materials to make cement.",
             "Co-processing": "Use of waste materials as fuel or raw material in cement kilns.", "GCCA": "Global Cement and Concrete Association.",
             "Kiln": "A rotary furnace in which raw meal is heated to form clinker.", "Pozzolana": "A siliceous material, such as fly ash, that reacts with lime to form cementitious compounds.",
             "WHR": "Waste heat recovery, the capture of heat in kiln exhaust gases to generate electricity.", "Calcined clay": "Clay heated to make it reactive, used as a partial substitute for clinker."}
    return ch("Glossary", "Terms and abbreviations", C.glossary({**C.BASE_TERMS, **extra}), cls="glossary")


def ch_disclaimer(ctx, sec):
    return ch("Forward-looking statements", "Important notice to readers", C.forward_looking(ctx))
