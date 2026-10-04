"""Aurelia Renewables Pvt Ltd: unlisted, not in any database. Self-reported tables only, consistent with claims."""
from __future__ import annotations
from . import layout as L, charts, common_text as C, data

ORDER = ["about", "message", "glance", "materiality", "strategy", "climate", "water", "bio", "people", "community",
         "governance", "supply", "data", "assurance", "gri", "glossary", "disclaimer"]
TOC_GROUPS = [{"at": "01", "label": "Introduction"}, {"at": "06", "label": "Environment"}, {"at": "09", "label": "Social"},
              {"at": "11", "label": "Governance and value chain"}, {"at": "13", "label": "Disclosures and reference"}]
YRS = ["FY21", "FY22", "FY23", "FY24", "FY25"]
CAP = [150, 300, 450, 600, 750]
GEN = [190, 420, 690, 960, 1320]
REV = [160, 330, 560, 840, 1180]


def make_charts(ctx):
    pal = ctx.pal
    charts.bar_chart(ctx.path("capacity.png"), YRS, CAP, pal, ylabel="MWp installed", h=2.3)
    charts.bar_chart(ctx.path("gen.png"), YRS, GEN, pal, ylabel="GWh generated", h=2.3)
    charts.bar_chart(ctx.path("revenue.png"), YRS, REV, pal, ylabel="Rs crore", h=2.2)
    charts.materiality(ctx.path("materiality.png"), [
        ("Climate and clean energy", 9.0, 8.6, 4), ("Land use and biodiversity", 7.8, 8.4, 3), ("Water use in arid regions", 7.6, 8.0, 3),
        ("Health and safety", 8.5, 9.0, 4), ("End-of-life of panels", 6.8, 7.4, 3), ("Local communities and jobs", 7.0, 7.9, 3),
        ("Supply chain labour standards", 7.4, 7.0, 3), ("Grid reliability", 8.2, 6.0, 2), ("Governance and ethics", 7.2, 6.4, 2), ("Innovation", 5.8, 5.2, 1)], pal)
    charts.timeline(ctx.path("timeline.png"), [
        ("FY2021 to FY2023", "Build", ["First 450 MWp online", "Safety systems in place", "Community office opened"]),
        ("FY2024 to FY2026", "Optimise", ["Robotic cleaning fleet", "Battery storage pilot", "Panel recycling partner"]),
        ("FY2027 and beyond", "Expand", ["Hybrid solar and storage", "New sites in Rajasthan", "Green hydrogen readiness"]),
    ], pal)
    charts.hbar_chart(ctx.path("csr.png"), ["Education", "Water access", "Livelihoods", "Health", "Environment"], [3.2, 2.4, 1.8, 1.0, 0.6], pal, xlabel="Rs crore, FY2025", fmt="{:.1f}", h=2.1)


def chapters(ctx):
    sec = {k: f"{i + 1:02d}" for i, k in enumerate(ORDER)}
    ctx.back_text = ("<p>Sustainability Office<br>Aurelia Tower, Sindhu Bhavan Road, Ahmedabad 380 054, Gujarat</p>"
                     "<p>esg@aureliarenewables.example | www.aureliarenewables.example</p><p>CIN U40106GJ2016PTC093215 | Unlisted private limited company</p>")
    return [globals()[f"ch_{k}"](ctx, sec) for k in ORDER]


def ch(title, subtitle, body, **kw):
    return {"title": title, "subtitle": subtitle, "body": body, **kw}


def ch_about(ctx, sec):
    b = (
        L.p(f"This is the first full sustainability report of {ctx.name}, an Ahmedabad-based developer and operator of utility-scale solar power. It covers the financial year from 1 April 2024 to 31 March 2025 and describes our one operating asset, the Kutch Solar Park, together with our corporate and project development offices.")
        + L.h3("Boundary and approach")
        + L.p("We are an unlisted company and are not required to file a BRSR, but we have chosen to report voluntarily using the BRSR Core structure, GRI Standards 2021 and the TCFD recommendations, because our lenders and offtakers increasingly expect it. All data is self-reported and has been compiled by our own teams. We have not obtained external assurance for this report, and the assurance section explains how we have reviewed the data internally.")
        + C.about_frameworks_callout()
        + L.p("Information on the project covers the construction and operation of solar generation, the substation and the transmission line to the grid interconnection point. Land lease arrangements, panel manufacturers and transport providers are outside the boundary, though we describe how we manage them.")
        + L.pull("A young company can still hold itself to an old-fashioned standard of clear accounts.", "Chief Financial Officer")
        + L.p("The Board approved this report on 12 June 2025. We welcome feedback to the address on the back cover.")
        + L.notes(["MWp denotes megawatt peak, the DC nameplate capacity of the solar modules.", "Figures are rounded and may not sum exactly."])
    )
    return ch("About this report", "Voluntary reporting by a young company", b)


def ch_message(ctx, sec):
    b = (
        L.p("Dear partners,")
        + '<p class="dropcap">' + "Eight years ago, a handful of engineers and I stood on a salt-white plain in Kutch with a survey map and a shared conviction that the desert's most abundant resource could power the cities in the east. Today, the plain carries three quarters of a gigawatt of solar modules, and the grid in Gujarat is a little cleaner for it." + '</p>'
        + L.p("The year to March 2025 was one of consolidation. We completed the last phase of the Kutch Solar Park, stabilised operations and improved availability. We also began to think harder about how a solar developer should measure itself, because clean electricity is only the beginning of a responsible project.")
        + L.p("Land, water, workers and waste matter as much as megawatts. A desert is not empty, and our neighbours there include pastoralists, salt workers, birds and a fragile ecology. We have tried to design, build and operate with that in mind.")
        + L.pull("Clean power should come from clean practice.", "Founder and Chief Executive Officer")
        + L.p("In this report we describe our approach to emissions, water, nature and people, and provide the data we have. We are a young company with young systems, and we say plainly where data is self-reported and not yet independently verified.")
        + L.stmt(f"As we grow, our motivation stays simple. {ctx.claim('AUR-06')} We hope this report helps you hold us to it.")
        + L.p("I would like to thank our lenders, our offtakers, the Gujarat state authorities and, above all, the hundreds of people who built and operate the park.")
        + '<div class="sign">Sincerely,<b>Kiran Desai</b><span>Founder and Chief Executive Officer<br>Ahmedabad, 12 June 2025</span></div>'
        + L.callout("Year in brief", items=["Final phase of Kutch Solar Park commissioned", "Robotic dry cleaning fleet deployed across the park", "Community water access programme extended", "First voluntary sustainability report published"])
    )
    return ch("Message from the Founder and CEO", "Powering tomorrow, responsibly", b)


def ch_glance(ctx, sec):
    b = (
        L.kpis([("750 MWp", "Installed capacity"), ("Rs 1,180 crore", "Revenue, FY2025"), ("1", "Operating solar park"), ("About 640", "Employees and long-term contractors")])
        + L.p(f"{ctx.name} was incorporated in 2016 in Ahmedabad. We develop, build, own and operate solar power plants and sell electricity to state distribution companies and corporate buyers under long-term power purchase agreements.")
        + L.p("Our operating asset is the Kutch Solar Park in Gujarat, built in phases between 2019 and 2025 on leased land in a region of high solar irradiance and low population density. The park uses bifacial modules on single-axis trackers, feeds a dedicated pooling substation and evacuates power over a transmission line to the state grid.")
        + C.facilities_table(ctx)
        + L.figure(ctx.img("map.png"), "<b>Figure 3.1</b> Location of the Kutch Solar Park in Gujarat.")
        + L.figure(ctx.img("capacity.png"), "<b>Figure 3.2</b> Installed capacity at year end, FY2021 to FY2025 (MWp).")
        + L.table("Business profile", ["Indicator", "Unit"] + YRS, [["Installed capacity", "MWp"] + [str(x) for x in CAP], ["Electricity generated", "GWh"] + [data.inr(x) for x in GEN], ["Revenue", "Rs crore"] + [data.inr(x) for x in REV]],
                  aligns=["l", "l"] + ["r"] * 5, src="Self-reported, unaudited management information for generation. Revenue is from management accounts.")
        + L.figure(ctx.img("gen.png"), "<b>Figure 3.3</b> Electricity generated, FY2021 to FY2025 (GWh).")
        + L.p("Our offtake portfolio is a mix of state utilities and commercial and industrial customers. We employ people directly in operations, maintenance and corporate roles, and engage contractors for security, module cleaning and civil work.")
    )
    return ch("Company at a glance", "A single large solar park in Kutch", b)


def ch_materiality(ctx, sec):
    b = (
        L.p("For this first report we carried out a streamlined materiality assessment. Management and Board members listed topics relevant to utility-scale solar based on sector standards, lender questionnaires and peer reports. We then consulted lenders, offtakers, panel suppliers, employee representatives and village leaders near the park, and asked them to rank the topics.")
        + L.figure(ctx.img("materiality.png"), "<b>Figure 4.1</b> Materiality matrix. Highlighted bubbles are priority topics.")
        + L.h3("Reading the results")
        + L.p("Lenders and offtakers rated grid reliability and climate impact highest. Village leaders emphasised land access, water and local employment. Employees spoke about safety in extreme heat. Together, they pointed to a set of priority topics that shape the structure of this report.")
        + L.callout("Who we engaged", items=["Project lenders and development finance institutions", "Offtakers and grid operators", "Panchayats and pastoral community groups", "Employees and contractors on site"])
        + L.p("We will broaden the process in future years and add structured engagement with non-governmental organisations and academic institutions working on arid-zone ecology.")
    )
    return ch("Materiality and stakeholders", "Choosing what to report on", b)


def ch_strategy(ctx, sec):
    b = (
        L.p("Our strategy has three parts. First, to build and operate solar capacity that delivers reliable power at competitive cost. Second, to do this with low impact on land, water and communities. Third, to prepare for the next stage of the energy transition, in which solar will be paired with storage and, eventually, with new demand such as green hydrogen.")
        + L.h3("Operate well")
        + L.p("Availability, performance ratio and safe operations are the foundation. We invest in monitoring, predictive maintenance and workforce training to keep plant performance high.")
        + L.figure(ctx.img("timeline.png"), "<b>Figure 5.1</b> Roadmap by phase. Phases indicate themes of work.")
        + L.h3("Minimise impact")
        + L.p("We avoid sensitive habitats in site selection, use waterless cleaning, and recycle materials where possible. Impact assessments precede each phase of construction.")
        + L.h3("Prepare for what comes next")
        + L.p("Battery storage pilots, hybrid designs and potential new sites in Rajasthan are being evaluated, subject to regulatory approvals and financing.")
        + L.callout("Investment discipline", "Every project is assessed for environmental and social risk before financial close, and lenders' standards, including the IFC Performance Standards, guide our design.")
    )
    return ch("Strategy and roadmap", "Building, operating and preparing for the next phase", b)


def ch_climate(ctx, sec):
    b = (
        L.p("Solar plants avoid the combustion emissions of fossil-fuel generation, but they are not free of a carbon footprint. Our direct emissions arise mainly from diesel used in generator sets and vehicles at the park, and from small amounts of refrigerants and sulphur hexafluoride in switchgear. Embedded emissions in modules and steel sit in our Scope 3.")
        + L.h3("Emissions")
        + L.stmt(f"We have worked to reduce our fuel use by electrifying site vehicles and improving grid reliability for auxiliary loads. {ctx.claim('AUR-01')}")
        + L.h3("Electricity use")
        + L.stmt(f"Our own consumption is a small fraction of what we generate, and we ensure that it comes from clean sources. {ctx.claim('AUR-02')}")
        + L.callout("Climate governance", items=["Board reviews climate risk twice a year", "Physical risk screening of extreme heat, dust storms and flooding", "Transition risk focus on tariffs, curtailment and policy", "Scenario analysis planned for the next cycle"])
        + L.p("Climate risk is real for a solar park. Extreme heat reduces module efficiency and can stress equipment. Dust storms soil modules, and rare but intense rainfall can flood access roads. We have designed drainage and elevated critical equipment, and review insurance cover annually.")
        + L.p("We have started building a Scope 3 inventory, starting with purchased goods, such as modules and steel, and transport. We will report on it once the data are robust.")
        + L.notes(["Scope 1 emissions comprise diesel combustion and fugitive gases.", "Reported figures are self-reported by the company and have not been externally assured."])
    )
    return ch("Climate and energy", "Low-carbon power, honestly accounted", b)


def ch_water(ctx, sec):
    b = (
        L.p("Kutch is a semi-arid region where water is scarce and precious. Conventional solar plants rely on water washing to remove dust from modules, and a park of our size could use large volumes. We decided early to find an alternative.")
        + L.stmt(f"We now use a fleet of battery-powered robots that brush the modules without water. {ctx.claim('AUR-04')} The robots work at night and in the early morning, when generation is low, so there is no loss of output.")
        + L.callout("Water practices", items=["Waterless cleaning with brushing robots", "Drinking water for staff supplied by treated sources and packaged water", "Rainwater capture at the operations building", "No process discharge to land or water"])
        + L.p("Water for construction, dust suppression and the staff colony has been supplied under permits from state authorities. We monitor the quantities and keep records for audit by lenders.")
        + L.h3("Sharing water with neighbours")
        + L.p("In partnership with local panchayats we have built storage tanks and pipelines to improve drinking water access for several hamlets, and we help maintain traditional ponds that serve livestock.")
        + L.p("Water risk is part of our enterprise risk process, and we will continue to report how we use and share this scarce resource.")
    )
    return ch("Water", "Dry cleaning in a dry land", b)


def ch_bio(ctx, sec):
    b = (
        L.p("The Rann of Kutch and the grasslands around it support remarkable wildlife, from flamingos and houbara bustards to wild asses and desert foxes. The Kutch Solar Park is located on land classified as revenue wasteland, outside notified protected areas, and sited after an ecological screening.")
        + L.stmt(f"Our land use has been planned to limit habitat disturbance. {ctx.claim('AUR-05')} We use satellite images and field surveys to keep track.")
        + L.h3("Design for wildlife")
        + L.p("We left corridors between array blocks, raised the lower edge of fences to allow small animals to pass, and avoided lighting that attracts insects and birds. Vegetation under the panels is allowed to regrow with native grasses and is managed with grazing by local shepherds rather than herbicides.")
        + L.callout("Biodiversity programme", items=["Ecological baseline survey before each phase", "Avian monitoring during winter migration", "Native grass restoration under arrays", "Grazing arrangements with local pastoralists"])
        + L.p("Birds are sometimes confused by reflective surfaces. Our monitoring has not found evidence of significant collisions, and we continue to look for evidence and share results with experts from conservation institutes.")
    )
    return ch("Biodiversity and land", "A solar park on arid grassland", b)


def ch_people(ctx, sec):
    b = (
        L.p("Working outdoors in a desert brings risks: extreme heat, high voltage, vehicle movement and working at height. Our safety approach emphasises hazard identification, controls and a culture of speaking up.")
        + L.stmt(f"We track incidents and report openly on them. {ctx.claim('AUR-03')} The figure is self-reported and calculated per million person-hours worked, including contractors.")
        + L.callout("Safety measures", items=["Heat stress protocol with work-rest schedules, shaded rest areas and hydration points", "Electrical safety training and lock-out tag-out", "Permit to work for high-risk jobs", "Emergency response drills with the local fire service"])
        + L.h3("Our people")
        + L.p("We are a young team with an average age in the early thirties. Engineering, operations and project roles are filled through campus hiring, lateral recruitment and a technician training programme developed with local industrial training institutes.")
        + L.h3("Inclusion")
        + L.p("We aim to build a diverse team. Recruitment panels include women where possible, the on-site colony has family accommodation and a crèche, and an Internal Committee handles complaints of harassment. Local hiring is a priority for semi-skilled positions.")
        + L.p("We offer health insurance, accident cover, and a provident fund to employees, and ensure that contractors comply with minimum wage and working hour laws.")
    )
    return ch("People and safety", "Working safely in the desert", b)


def ch_community(ctx, sec):
    b = (
        L.p("The villages near the Kutch Solar Park, home mostly to pastoral and salt-working families, have lived with this landscape for generations. We have tried to approach them as neighbours who deserve consultation, not merely as stakeholders.")
        + L.kpis([("Rs 9 crore", "Community investment, FY2025"), ("12", "Villages and hamlets in programme areas"), ("5", "Themes")])
        + L.figure(ctx.img("csr.png"), "<b>Figure 10.1</b> Community investment by theme, FY2025 (Rs crore).")
        + L.h3("Water, education and livelihoods")
        + L.p("Priorities were set through village meetings. Water access came first, followed by education and livelihoods. We supported school buildings and teachers, skills training for solar technicians, and market links for local crafts such as embroidery.")
        + L.h3("Land and grazing")
        + L.p("Our lease agreements were negotiated with the revenue department and, where relevant, with village committees. Access paths for herders and their animals have been maintained across the park, and we agreed seasonal grazing arrangements.")
        + L.callout("Grievance mechanism", "Villagers can approach the community liaison office, call a toll-free number or leave a note at the park gate. Complaints are logged and answered within set timelines.")
    )
    return ch("Community", "Neighbours in a shared landscape", b)


def ch_governance(ctx, sec):
    b = (
        L.p("Aurelia is a private limited company, governed by a Board with seven directors, including representatives of our institutional investors and two independent directors. We have voluntarily set up Audit and Risk, and Nomination and Remuneration committees, even though the law does not require them for a company of our kind.")
        + L.h3("Policies")
        + L.p("The Board has approved policies on code of conduct, anti-bribery, whistle-blowing, human rights, health and safety, environment and procurement. Employees and contractors receive training on these policies, and a hotline operated by an external provider allows anonymous reporting of concerns.")
        + L.callout("Lender standards", "Our debt facilities incorporate environmental and social covenants based on the IFC Performance Standards and Equator Principles, and we report to lenders twice a year.")
        + L.h3("Risk")
        + L.p("Our risk register covers regulatory change, curtailment, counterparty risk, supply of modules, extreme weather, cyber security and safety. Owners review risks monthly, and the Audit and Risk Committee reviews the top risks each quarter.")
        + L.p("We do not make political donations. We are members of industry associations for solar developers and participate in policy consultations with transparency.")
    )
    return ch("Governance and ethics", "Board, policies and risk", b)


def ch_supply(ctx, sec):
    b = (
        L.p("Solar modules, trackers, inverters and steel make up most of the material footprint of our projects. These come from manufacturers in India, China and elsewhere, and we take care to understand who they are and how they operate.")
        + L.h3("Procurement standards")
        + L.p("Our procurement policy requires suppliers to comply with labour, health and safety and environmental laws, and to confirm that they do not use forced labour. Module suppliers must provide traceability declarations for polysilicon and wafers, and we favour manufacturers that have undergone third-party social audits.")
        + L.callout("Supplier due diligence", items=["Questionnaire and desktop screening", "Audit reports reviewed by our team", "Contractual right to inspect", "Escalation and exit processes for serious breaches"])
        + L.h3("End of life")
        + L.p("Solar modules last around thirty years, so the volume of end-of-life panels is still small. However, we are planning ahead. We have signed a memorandum with an authorised e-waste recycler to explore recovery of glass, aluminium, silicon and silver from modules, and we keep records of damaged panels removed during operations.")
        + L.p("Packaging from deliveries, mostly wood and cardboard, is returned to suppliers or sent for recycling. Hazardous materials such as used oil and batteries are handled by authorised recyclers.")
    )
    return ch("Supply chain and end of life", "Responsible sourcing and recycling", b)


def ch_data(ctx, sec):
    b = (
        L.p("The table below summarises the key sustainability indicators we report, in the same terms as the claims made elsewhere in this report. All values are self-reported by Aurelia, and are not externally assured.")
        + L.table("Self-reported sustainability indicators", ["Indicator", "Unit", "FY2023", "FY2024", "FY2025"],
                  [["Scope 1 emissions (index, FY2023 = 100)", "Index", "100", "84", "70"],
                   ["Renewable share of electricity used at offices and plants", "%", "n.r.", "n.r.", "100"],
                   ["Water withdrawal (index, FY2022 = 100)", "Index", "n.r.", "n.r.", "15"],
                   ["Lost Time Injury Frequency Rate (per million hours)", "Rate", "n.r.", "n.r.", "0.05"],
                   ["Forest loss attributable to park", "ha", "n.r.", "n.r.", "0"]],
                  src="n.r. means not reported in this edition. Values are self-reported and unaudited.", aligns=["l", "l", "r", "r", "r"])
        + L.p("Indices are used rather than absolute values for Scope 1 and water because the baseline years are before the park reached full capacity, and absolute comparison would not be meaningful. Absolute volumes will be disclosed in future reports as measurement systems mature.")
        + L.callout("Basis of preparation", items=["Operational control boundary covering the Kutch Solar Park and offices", "Safety rates include contractors", "Water measured through flow meters at the intake and tanker logs", "Scope 1 per GHG Protocol Corporate Standard"])
        + L.p("Generation, capacity and revenue figures are presented in the section on the company at a glance.")
    )
    return ch("Performance data", "Self-reported indicators", b)


def ch_assurance(ctx, sec):
    b = (
        L.p("This report has not been externally assured. We have, however, subjected the data to an internal review that is described here, so that readers can judge how much weight to place on it.")
        + L.h3("Internal review")
        + L.p("Data owners at the park submit monthly figures for fuel, electricity, safety and water through a shared platform. The sustainability manager checks them against invoices, meter reads and incident logs. Our finance team reconciles revenue and generation figures to billing records, and the head of internal audit samples selected indicators each year.")
        + L.callout("Our plan for assurance", items=["Select an external assurance provider for FY2026", "Begin with limited assurance on a core set of indicators", "Extend to absolute emissions and water volumes", "Publish the assurance report with the next edition"])
        + L.p("Lenders also review our data through technical and environmental advisers who visit the site during operations. Their reports are confidential, but findings are shared with the Board.")
        + L.p("We invite readers to challenge our data, and we will correct errors in future editions.")
    )
    return ch("Assurance and data quality", "How we reviewed the data", b)


def ch_gri(ctx, sec):
    m = {"about": "about", "message": "message", "glance": "glance", "materiality": "materiality", "strategy": "strategy", "climate": "climate", "water": "water",
         "waste": "supply", "bio": "bio", "air": "climate", "people": "people", "di": "people", "community": "community", "governance": "governance",
         "supply": "supply", "assurance": "assurance"}
    topic = {k: sec[v] for k, v in m.items()}
    body = C.gri_index(topic, f"<b>Statement of use.</b> {ctx.name} has reported the information cited in this GRI content index for the period 1 April 2024 to 31 March 2025 with reference to the GRI Standards. Information is self-reported and not externally assured.",
                       partial=("302-1", "302-3", "302-4", "303-3", "303-4", "303-5", "305-3", "306-3", "306-4", "306-5", "405-1", "405-2", "2-5"))
    return ch("GRI content index", "Where to find each disclosure", body, raw=True, cls="gri")


def ch_glossary(ctx, sec):
    extra = {"Bifacial module": "A solar module that generates power from both its front and rear faces.", "Curtailment": "Reduction of generation ordered by the grid operator.",
             "MWp": "Megawatt peak, the DC nameplate capacity of solar modules.", "Performance ratio": "The ratio of actual to theoretical energy output of a solar plant.",
             "PPA": "Power purchase agreement.", "Tracker": "A mount that rotates solar modules to follow the sun.", "Pooling substation": "A substation where power from many inverters is combined for transmission.",
             "IFC Performance Standards": "Environmental and social standards of the International Finance Corporation used by project lenders.",
             "GWh": "Gigawatt hour, one million kilowatt hours."}
    return ch("Glossary", "Terms and abbreviations", C.glossary({**C.BASE_TERMS, **extra}), cls="glossary")


def ch_disclaimer(ctx, sec):
    return ch("Forward-looking statements", "Important notice to readers", C.forward_looking(ctx))
