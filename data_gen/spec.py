"""
data_gen/spec.py

SINGLE SOURCE OF TRUTH for the synthetic "mock world".

Everything in this repository that is data -- the world database served by
mock_sources/, the demo ESG report PDFs, the 200-case benchmark -- is
generated from this file. That is what keeps the PDFs, the databases and
the ground truth consistent with each other.

ALL COMPANIES, FACILITIES, FIGURES AND EVENTS ARE FICTIONAL.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Global constants
# ---------------------------------------------------------------------------

SEED = 20261004
FISCAL_YEARS = ["FY2020", "FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
# Indian fiscal year: FY2025 = 1 Apr 2024 .. 31 Mar 2025
FY_DATE_RANGE = {fy: (f"{int(fy[2:]) - 1}-04-01", f"{fy[2:]}-03-31") for fy in FISCAL_YEARS}

N_COMPANIES = 150  # including the demo companies below that live in the DB

SECTORS = [
    "Steel", "Cement", "Power", "Textiles", "FMCG",
    "Chemicals", "Automotive", "Pharmaceuticals", "Mining", "IT Services",
]

# ---------------------------------------------------------------------------
# Metric catalogue: canonical metric keys used by EVERY component.
# key -> (label, unit, where it lives in the world DB)
# ---------------------------------------------------------------------------

METRICS: dict[str, dict] = {
    "scope1_tco2e":         {"label": "Scope 1 GHG emissions", "unit": "tCO2e", "table": "brsr_filings"},
    "scope2_tco2e":         {"label": "Scope 2 GHG emissions", "unit": "tCO2e", "table": "brsr_filings"},
    "ghg_intensity":        {"label": "GHG emission intensity (Scope 1+2 per Rs crore turnover)", "unit": "tCO2e/Rs cr", "table": "brsr_filings"},
    "energy_gj":            {"label": "Total energy consumed", "unit": "GJ", "table": "brsr_filings"},
    "re_pct":               {"label": "Renewable share of electricity", "unit": "%", "table": "brsr_filings"},
    "water_withdrawal_kl":  {"label": "Total water withdrawal", "unit": "kL", "table": "brsr_filings"},
    "water_discharge_kl":   {"label": "Total water discharged", "unit": "kL", "table": "brsr_filings"},
    "waste_generated_t":    {"label": "Total waste generated", "unit": "t", "table": "brsr_filings"},
    "waste_recovered_t":    {"label": "Waste recovered / recycled / co-processed", "unit": "t", "table": "brsr_filings"},
    "ltifr":                {"label": "Lost Time Injury Frequency Rate (per million hours)", "unit": "rate", "table": "brsr_filings"},
    "fatalities":           {"label": "Work-related fatalities", "unit": "count", "table": "brsr_filings"},
    "women_wage_pct":       {"label": "Gross wages paid to females as % of total wages", "unit": "%", "table": "brsr_filings"},
    "msme_sourcing_pct":    {"label": "Input material sourced from MSMEs", "unit": "%", "table": "brsr_filings"},
    "assurance_type":       {"label": "Type of external assurance on BRSR Core", "unit": "category", "table": "brsr_filings"},
    "regulatory_actions":   {"label": "Environmental regulatory actions / penalties", "unit": "count / INR", "table": "regulatory_actions"},
    "ocems_exceedances":    {"label": "Continuous emission monitoring exceedances", "unit": "count", "table": "ocems_exceedances"},
    "deforestation_ha":     {"label": "Forest-loss alerts near operations", "unit": "ha", "table": "land_alerts"},
    "rec_retirement":       {"label": "Renewable energy certificates retired", "unit": "MWh", "table": "re_certificates"},
    "scope3_tco2e":         {"label": "Scope 3 GHG emissions", "unit": "tCO2e", "table": None},   # deliberately NOT in any source
    "clinker_factor":       {"label": "Clinker-to-cement ratio", "unit": "ratio", "table": None},  # deliberately NOT in any source
}

# Source reliability tiers (1 = most authoritative)
SOURCE_TIERS = {
    "brsr_filings": 1, "facility_ghg": 1,
    "regulatory_actions": 2, "ocems_exceedances": 2,
    "land_alerts": 3, "re_certificates": 3, "audited_reports": 3,
    "news_pr": 4, "news": 5,
}

# Labels used by the benchmark and the system
LABELS = ["ALIGN", "CONTRADICT", "INSUFFICIENT_EVIDENCE", "NOT_CHECKABLE"]

GREENWASHING_TYPES = [
    "none",                     # honest claim
    "vague_claim",              # cheap talk, non-falsifiable
    "inflated_reduction",       # % reduction overstated vs filed numbers
    "cherry_picked_year",       # compares favourable year, not baseline
    "baseline_shift",           # silently moved baseline
    "scope_swap",               # claims scope 1 figure using scope 2, etc.
    "absolute_vs_intensity",    # intensity fell, claims absolute fell (or reverse)
    "unit_error",               # wrong unit / order of magnitude
    "future_target_as_achievement",
    "unretired_certificates",   # RE claim relies on unretired RECs
    "geo_contradiction",        # land clearing near a "zero deforestation" site
    "hidden_regulatory_penalty",
    "overstated_safety",
    "overstated_assurance",
    "data_not_disclosed",       # no external data can check it
]

# ---------------------------------------------------------------------------
# Demo companies (appear in the demo PDFs). The first three live in the DB.
# "true" = what the world DB holds. "claims" = what the PDF says.
# expected = the label the system SHOULD output.
# ---------------------------------------------------------------------------

DEMO_COMPANIES: list[dict] = [
    # ------------------------------------------------------------------ A
    {
        "company_id": "CMP-0001",
        "in_db": True,
        "cin": "L27100OR1998PLC005512",
        "name": "Vajra Steel & Power Ltd",
        "short_name": "Vajra Steel",
        "aliases": ["Vajra Steel", "Vajra Steel and Power", "VSPL"],
        "sector": "Steel",
        "hq_city": "Bhubaneswar", "hq_state": "Odisha",
        "listing": "NSE: VAJRASTL",
        "report_title": "Sustainability Report FY2024-25: Forging a Greener Future",
        "profile": "greenwasher",
        "brand_colour": "#0B3D91",
        "facilities": [
            {"facility_id": "FAC-0001", "name": "Jharsuguda Integrated Steel Plant", "type": "Integrated steel plant",
             "district": "Jharsuguda", "state": "Odisha", "lat": 21.8554, "lon": 84.0062,
             "capacity_value": 5.0, "capacity_unit": "MTPA crude steel", "forest_adjacent": False},
            {"facility_id": "FAC-0002", "name": "Angul Captive Power Plant", "type": "Coal-fired captive power plant",
             "district": "Angul", "state": "Odisha", "lat": 20.8400, "lon": 85.1010,
             "capacity_value": 1200, "capacity_unit": "MW", "forest_adjacent": False},
            {"facility_id": "FAC-0003", "name": "Keonjhar Iron Ore Mine", "type": "Open-cast iron ore mine",
             "district": "Keonjhar", "state": "Odisha", "lat": 21.6290, "lon": 85.5810,
             "capacity_value": 12.0, "capacity_unit": "MTPA ore", "forest_adjacent": True},
            {"facility_id": "FAC-0004", "name": "Barbil Pellet Plant", "type": "Pellet plant",
             "district": "Keonjhar", "state": "Odisha", "lat": 22.1010, "lon": 85.3820,
             "capacity_value": 6.0, "capacity_unit": "MTPA pellets", "forest_adjacent": False},
        ],
        # BRSR truth, FY2020..FY2025 (index aligned with FISCAL_YEARS)
        "true": {
            "revenue_cr":          [28000, 26500, 33800, 37200, 39900, 41500],
            "scope1_tco2e":        [11_800_000, 11_650_000, 11_900_000, 11_400_000, 11_050_000, 10_856_000],
            "scope2_tco2e":        [1_450_000, 1_430_000, 1_440_000, 1_410_000, 1_395_000, 1_380_000],
            "energy_gj":           [158_000_000, 155_500_000, 160_200_000, 157_900_000, 156_100_000, 155_300_000],
            "re_pct":              [6.0, 7.5, 9.0, 12.0, 15.5, 18.0],
            "water_withdrawal_kl": [68_000_000, 67_200_000, 69_500_000, 70_100_000, 71_300_000, 72_080_000],
            "water_discharge_kl":  [9_800_000, 9_600_000, 9_900_000, 10_100_000, 10_050_000, 10_200_000],
            "waste_generated_t":   [6_900_000, 6_700_000, 7_050_000, 7_200_000, 7_300_000, 7_400_000],
            "waste_recovered_t":   [5_800_000, 5_750_000, 6_150_000, 6_480_000, 6_640_000, 6_838_000],  # 92.4% in FY25
            "ltifr":               [0.62, 0.58, 0.55, 0.49, 0.44, 0.41],
            "fatalities":          [5, 4, 4, 3, 4, 3],
            "women_wage_pct":      [3.2, 3.4, 3.6, 3.8, 3.9, 4.1],
            "msme_sourcing_pct":   [11.0, 11.5, 12.0, 12.8, 13.1, 13.5],
            "assurance_type":      ["none", "none", "limited", "limited", "limited", "limited"],
            "assurance_provider":  [None, None, "Rao & Iyer Assurance LLP", "Rao & Iyer Assurance LLP",
                                    "Rao & Iyer Assurance LLP", "Rao & Iyer Assurance LLP"],
        },
        "events": {
            # planted external evidence the generator MUST create
            "regulatory_actions": [
                {"facility_id": "FAC-0002", "authority": "NGT", "order_type": "environmental_compensation",
                 "date": "2024-08-14", "penalty_inr": 42_000_000, "status": "paid_under_protest",
                 "case_no": "O.A. No. 311/2024 (EZ)",
                 "summary": "National Green Tribunal (Eastern Zone) directed Vajra Steel & Power Ltd to pay "
                            "environmental compensation of Rs 4.2 crore for fly-ash dyke breach and repeated "
                            "stack emission exceedances at the Angul captive power plant."},
                {"facility_id": "FAC-0002", "authority": "OSPCB", "order_type": "show_cause",
                 "date": "2024-11-02", "penalty_inr": 0, "status": "reply_filed",
                 "case_no": "OSPCB/ANG/SCN/2024/118",
                 "summary": "Odisha State Pollution Control Board show-cause notice for particulate matter "
                            "exceedances recorded by the online continuous emission monitoring system."},
            ],
            "ocems_exceedances": {"facility_id": "FAC-0002", "fy": "FY2025", "count": 37,
                                  "parameters": ["PM", "SO2"]},
            "land_alerts": {"facility_id": "FAC-0003", "radius_km": 5, "count": 14, "total_ha": 126.4,
                            "from": "2024-04-10", "to": "2025-03-05"},
            "re_certificates": {"retired_mwh": 310_000, "active_mwh": 2_100_000, "vintage": 2024},
        },
        "claims": [
            {"id": "VAJ-01", "section": "CEO letter", "metric": "scope1_tco2e", "fy": "FY2025",
             "text": "We have reduced our absolute Scope 1 emissions by 40% against our FY2020 baseline.",
             "expected": "CONTRADICT", "gw_type": "inflated_reduction",
             "truth_note": "Filed Scope 1 fell from 11.80 Mt to 10.86 Mt, an 8.0% reduction."},
            {"id": "VAJ-02", "section": "Climate", "metric": "ghg_intensity", "fy": "FY2025",
             "text": "Our GHG emission intensity fell by 38% between FY2020 and FY2025, reaching 295 tCO2e per Rs crore of turnover.",
             "expected": "ALIGN", "gw_type": "none",
             "truth_note": "(S1+S2)/revenue: 473.2 -> 294.9, a 37.7% fall."},
            {"id": "VAJ-03", "section": "Energy", "metric": "re_pct", "fy": "FY2025",
             "text": "In FY2025, 50% of the electricity consumed across our operations came from renewable sources.",
             "expected": "CONTRADICT", "gw_type": "unretired_certificates",
             "truth_note": "BRSR filing shows 18.0% renewable electricity."},
            {"id": "VAJ-04", "section": "Energy", "metric": "rec_retirement", "fy": "FY2025",
             "text": "All renewable energy certificates counted towards our renewable energy claims have been retired in our name.",
             "expected": "CONTRADICT", "gw_type": "unretired_certificates",
             "truth_note": "Registry: 2.1 million MWh of 2024-vintage certificates remain active, only 0.31 million MWh retired."},
            {"id": "VAJ-05", "section": "Water", "metric": "water_withdrawal_kl", "fy": "FY2025",
             "text": "We cut freshwater withdrawal by 25% compared with FY2020.",
             "expected": "CONTRADICT", "gw_type": "inflated_reduction",
             "truth_note": "Withdrawal rose from 68.0 to 72.08 million kL (+6.0%)."},
            {"id": "VAJ-06", "section": "Biodiversity", "metric": "deforestation_ha", "fy": "FY2025",
             "text": "Our Keonjhar mining operations caused zero deforestation during FY2024-25.",
             "expected": "CONTRADICT", "gw_type": "geo_contradiction",
             "truth_note": "14 forest-loss alerts totalling 126.4 ha within 5 km of the Keonjhar mine in FY2025."},
            {"id": "VAJ-07", "section": "Compliance", "metric": "regulatory_actions", "fy": "FY2025",
             "text": "There were no environmental violations or penalties at any of our sites during FY2024-25.",
             "expected": "CONTRADICT", "gw_type": "hidden_regulatory_penalty",
             "truth_note": "NGT environmental compensation of Rs 4.2 crore (Aug 2024) and OSPCB show-cause (Nov 2024)."},
            {"id": "VAJ-08", "section": "Air quality", "metric": "ocems_exceedances", "fy": "FY2025",
             "text": "Stack emissions at all our plants remained within prescribed limits throughout the year.",
             "expected": "CONTRADICT", "gw_type": "hidden_regulatory_penalty",
             "truth_note": "37 OCEMS exceedances (PM, SO2) at the Angul plant in FY2025."},
            {"id": "VAJ-09", "section": "Safety", "metric": "ltifr", "fy": "FY2025",
             "text": "Our Lost Time Injury Frequency Rate improved to 0.12 in FY2025.",
             "expected": "CONTRADICT", "gw_type": "overstated_safety",
             "truth_note": "Filed LTIFR for FY2025 is 0.41."},
            {"id": "VAJ-10", "section": "Safety", "metric": "fatalities", "fy": "FY2025",
             "text": "We recorded zero work-related fatalities across our operations in FY2025.",
             "expected": "CONTRADICT", "gw_type": "overstated_safety",
             "truth_note": "Filed fatalities for FY2025: 3."},
            {"id": "VAJ-11", "section": "Circularity", "metric": "waste_recovered_t", "fy": "FY2025",
             "text": "We recovered or recycled 92% of the waste generated at our sites in FY2025.",
             "expected": "ALIGN", "gw_type": "none",
             "truth_note": "6.838 Mt recovered of 7.40 Mt generated = 92.4%."},
            {"id": "VAJ-12", "section": "People", "metric": "women_wage_pct", "fy": "FY2025",
             "text": "Women employees received 4.1% of total gross wages paid in FY2025.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Filed: 4.1%."},
            {"id": "VAJ-13", "section": "Assurance", "metric": "assurance_type", "fy": "FY2025",
             "text": "Our BRSR Core disclosures for FY2025 received reasonable assurance from an independent provider.",
             "expected": "CONTRADICT", "gw_type": "overstated_assurance",
             "truth_note": "Filing records limited assurance."},
            {"id": "VAJ-14", "section": "Value chain", "metric": "scope3_tco2e", "fy": "FY2025",
             "text": "Our Scope 3 emissions declined by 15% year on year in FY2025.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed",
             "truth_note": "No external source carries Scope 3 data."},
            {"id": "VAJ-15", "section": "CEO letter", "metric": None, "fy": None,
             "text": "We remain deeply committed to a greener, cleaner tomorrow for all our stakeholders.",
             "expected": "NOT_CHECKABLE", "gw_type": "vague_claim", "truth_note": "Cheap talk."},
            {"id": "VAJ-16", "section": "Targets", "metric": "scope1_tco2e", "fy": None,
             "text": "We will achieve net zero emissions across our operations by 2050.",
             "expected": "NOT_CHECKABLE", "gw_type": "none", "truth_note": "Future target; planning, not verifiable today."},
        ],
        "news": [
            {"outlet": "The Eastern Ledger", "tier": 5, "date": "2024-08-16",
             "headline": "NGT orders Vajra Steel to pay Rs 4.2 crore over Angul fly-ash breach",
             "facts": ["Rs 4.2 crore environmental compensation", "Angul captive power plant", "fly-ash dyke breach",
                       "repeated stack emission exceedances"]},
            {"outlet": "Odisha Field Report", "tier": 5, "date": "2025-01-22",
             "headline": "Villagers near Keonjhar allege fresh forest clearing around iron ore lease",
             "facts": ["satellite alerts show about 126 hectares of forest loss", "within 5 km of Vajra's Keonjhar mine",
                       "between April 2024 and March 2025"]},
            {"outlet": "Vajra Steel & Power Ltd (press release)", "tier": 4, "date": "2025-06-05",
             "headline": "Vajra Steel powers half its operations with green energy",
             "facts": ["company says 50% of electricity is renewable", "based on renewable energy certificates purchased"]},
            {"outlet": "Business Mint India", "tier": 5, "date": "2025-07-10",
             "headline": "Analysts question Vajra's green power math as most RECs remain unretired",
             "facts": ["registry shows 2.1 million MWh of certificates still active", "only 0.31 million MWh retired",
                       "BRSR filing shows 18% renewable electricity"]},
        ],
    },
    # ------------------------------------------------------------------ B
    {
        "company_id": "CMP-0002",
        "in_db": True,
        "cin": "L26942MH2001PLC131870",
        "name": "Sahyadri Cement Industries Ltd",
        "short_name": "Sahyadri Cement",
        "aliases": ["Sahyadri Cement", "SCIL", "Sahyadri Cements"],
        "sector": "Cement",
        "hq_city": "Pune", "hq_state": "Maharashtra",
        "listing": "NSE: SAHYCEM",
        "report_title": "Integrated Annual Report FY2024-25: Building Responsibly",
        "profile": "mixed",
        "brand_colour": "#7A4B12",
        "facilities": [
            {"facility_id": "FAC-0005", "name": "Chandrapur Integrated Cement Plant", "type": "Integrated cement plant",
             "district": "Chandrapur", "state": "Maharashtra", "lat": 19.9615, "lon": 79.2961,
             "capacity_value": 6.5, "capacity_unit": "MTPA cement", "forest_adjacent": False},
            {"facility_id": "FAC-0006", "name": "Gulbarga Cement Works", "type": "Integrated cement plant",
             "district": "Kalaburagi", "state": "Karnataka", "lat": 17.3297, "lon": 76.8343,
             "capacity_value": 4.0, "capacity_unit": "MTPA cement", "forest_adjacent": False},
            {"facility_id": "FAC-0007", "name": "Raigad Grinding Unit", "type": "Grinding unit",
             "district": "Raigad", "state": "Maharashtra", "lat": 18.5158, "lon": 73.1822,
             "capacity_value": 2.0, "capacity_unit": "MTPA cement", "forest_adjacent": False},
            {"facility_id": "FAC-0008", "name": "Rajura Limestone Mine", "type": "Limestone mine",
             "district": "Chandrapur", "state": "Maharashtra", "lat": 19.7790, "lon": 79.3650,
             "capacity_value": 8.0, "capacity_unit": "MTPA limestone", "forest_adjacent": False},
        ],
        "true": {
            "revenue_cr":          [9800, 9100, 11200, 12600, 13400, 14100],
            "scope1_tco2e":        [6_200_000, 5_980_000, 6_150_000, 5_900_000, 5_720_000, 5_580_000],  # -10.0%
            "scope2_tco2e":        [410_000, 395_000, 400_000, 380_000, 362_000, 350_000],
            "energy_gj":           [41_000_000, 39_800_000, 41_600_000, 40_900_000, 40_100_000, 39_600_000],
            "re_pct":              [9.0, 11.0, 14.0, 18.0, 22.0, 26.0],
            "water_withdrawal_kl": [3_900_000, 3_820_000, 3_870_000, 3_750_000, 3_640_000, 3_580_000],
            "water_discharge_kl":  [120_000, 118_000, 115_000, 101_000, 96_000, 90_000],
            "waste_generated_t":   [210_000, 205_000, 214_000, 220_000, 226_000, 231_000],
            "waste_recovered_t":   [120_000, 128_000, 141_000, 156_000, 170_500, 181_200],
            "ltifr":               [0.52, 0.50, 0.47, 0.44, 0.41, 0.38],
            "fatalities":          [2, 1, 2, 1, 1, 0],
            "women_wage_pct":      [1.8, 1.9, 2.0, 2.4, 2.8, 3.1],
            "msme_sourcing_pct":   [18.0, 18.5, 19.2, 20.1, 21.0, 21.6],
            "assurance_type":      ["none", "limited", "limited", "limited", "reasonable", "reasonable"],
            "assurance_provider":  [None, "Mehta Kulkarni & Co", "Mehta Kulkarni & Co", "Mehta Kulkarni & Co",
                                    "Mehta Kulkarni & Co", "Mehta Kulkarni & Co"],
        },
        "events": {
            "regulatory_actions": [
                {"facility_id": "FAC-0006", "authority": "CPCB", "order_type": "closure_direction",
                 "date": "2023-02-09", "penalty_inr": 0, "status": "revoked_2023-04-18",
                 "case_no": "CPCB/IPC-II/KA/2023/017",
                 "summary": "Central Pollution Control Board direction under Section 5 of the Environment "
                            "(Protection) Act for fugitive dust emissions at the Gulbarga Cement Works; "
                            "revoked after compliance verification in April 2023."},
            ],
            "ocems_exceedances": {"facility_id": "FAC-0005", "fy": "FY2025", "count": 6, "parameters": ["PM"]},
            "land_alerts": {"facility_id": "FAC-0008", "radius_km": 5, "count": 0, "total_ha": 0.0,
                            "from": "2024-04-01", "to": "2025-03-31"},
            "re_certificates": {"retired_mwh": 240_000, "active_mwh": 0, "vintage": 2024},
        },
        "claims": [
            {"id": "SAH-01", "section": "Chairman's message", "metric": "scope1_tco2e", "fy": "FY2025",
             "text": "Since FY2020 we have reduced our absolute Scope 1 emissions by 10%.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "6.20 -> 5.58 Mt = -10.0%."},
            {"id": "SAH-02", "section": "Energy", "metric": "re_pct", "fy": "FY2025",
             "text": "Renewable power, including waste heat recovery, met 26% of our electricity needs in FY2025.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Filed 26.0%."},
            {"id": "SAH-03", "section": "Circularity", "metric": "waste_recovered_t", "fy": "FY2025",
             "text": "We co-processed and recovered 1.8 lakh tonnes of waste in FY2025.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Filed 181,200 t."},
            {"id": "SAH-04", "section": "Compliance", "metric": "regulatory_actions", "fy": "FY2025",
             "text": "No regulatory penalties or closure directions were issued against any of our plants in FY2024-25.",
             "expected": "ALIGN", "gw_type": "none",
             "truth_note": "Only action is a CPCB direction from Feb 2023 (FY2023), outside the claim period. Period trap."},
            {"id": "SAH-05", "section": "Biodiversity", "metric": "deforestation_ha", "fy": "FY2025",
             "text": "Our Rajura limestone mine recorded no forest loss within its 5 km buffer zone during FY2025.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Zero land alerts within 5 km."},
            {"id": "SAH-06", "section": "Safety", "metric": "ltifr", "fy": "FY2025",
             "text": "Our LTIFR improved from 0.52 in FY2020 to 0.30 in FY2025.",
             "expected": "CONTRADICT", "gw_type": "overstated_safety", "truth_note": "Filed FY2025 LTIFR = 0.38."},
            {"id": "SAH-07", "section": "Air quality", "metric": "ocems_exceedances", "fy": "FY2025",
             "text": "Our continuous emission monitoring systems recorded zero exceedances in FY2025.",
             "expected": "CONTRADICT", "gw_type": "hidden_regulatory_penalty",
             "truth_note": "6 PM exceedances at Chandrapur in FY2025."},
            {"id": "SAH-08", "section": "People", "metric": "women_wage_pct", "fy": "FY2025",
             "text": "The share of gross wages paid to women has doubled since FY2022.",
             "expected": "CONTRADICT", "gw_type": "inflated_reduction",
             "truth_note": "2.0% (FY2022) -> 3.1% (FY2025) = 1.55x, not 2x."},
            {"id": "SAH-09", "section": "Assurance", "metric": "assurance_type", "fy": "FY2025",
             "text": "Our BRSR Core indicators for FY2025 were subject to reasonable assurance.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Filed: reasonable."},
            {"id": "SAH-10", "section": "Climate", "metric": "clinker_factor", "fy": "FY2025",
             "text": "We lowered our clinker factor to 0.68 in FY2025, among the lowest in the industry.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed",
             "truth_note": "No source carries clinker factor."},
            {"id": "SAH-11", "section": "Water", "metric": None, "fy": "FY2025",
             "text": "Through rainwater harvesting we replenished 2.1 times the water we consumed, making us water positive.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed",
             "truth_note": "No harvesting / replenishment data in any source."},
            {"id": "SAH-12", "section": "Targets", "metric": None, "fy": None,
             "text": "We aim to deliver net zero concrete by 2050, in line with the GCCA roadmap.",
             "expected": "NOT_CHECKABLE", "gw_type": "none", "truth_note": "Future target."},
        ],
        "news": [
            {"outlet": "Deccan Industry Times", "tier": 5, "date": "2023-02-11",
             "headline": "CPCB orders Sahyadri's Gulbarga plant to curb dust or face closure",
             "facts": ["closure direction issued 9 February 2023", "fugitive dust emissions", "revoked in April 2023 after compliance"]},
            {"outlet": "Sahyadri Cement Industries Ltd (press release)", "tier": 4, "date": "2025-05-20",
             "headline": "Sahyadri crosses 26% renewable power with new waste heat recovery unit",
             "facts": ["26% renewable electricity in FY2025", "new 18 MW waste heat recovery system at Chandrapur"]},
            {"outlet": "Western Markets Daily", "tier": 5, "date": "2025-08-02",
             "headline": "Sahyadri Cement posts steady safety gains, LTIFR at 0.38",
             "facts": ["LTIFR of 0.38 in FY2025", "zero fatalities in FY2025"]},
        ],
    },
    # ------------------------------------------------------------------ C
    {
        "company_id": "CMP-0003",
        "in_db": True,
        "cin": "L17111TZ1985PLC001647",
        "name": "Kaveri Threads & Textiles Ltd",
        "short_name": "Kaveri Threads",
        "aliases": ["Kaveri Threads", "Kaveri Textiles", "KTTL"],
        "sector": "Textiles",
        "hq_city": "Coimbatore", "hq_state": "Tamil Nadu",
        "listing": "NSE: KAVERITEX",
        "report_title": "BRSR and Impact Report FY2024-25: Woven with Care",
        "profile": "honest",
        "brand_colour": "#1F6F50",
        "facilities": [
            {"facility_id": "FAC-0009", "name": "Coimbatore Spinning Mill", "type": "Spinning mill",
             "district": "Coimbatore", "state": "Tamil Nadu", "lat": 11.0168, "lon": 76.9558,
             "capacity_value": 220000, "capacity_unit": "spindles", "forest_adjacent": False},
            {"facility_id": "FAC-0010", "name": "Tiruppur Processing Unit (ZLD)", "type": "Dyeing and processing unit",
             "district": "Tiruppur", "state": "Tamil Nadu", "lat": 11.1085, "lon": 77.3411,
             "capacity_value": 60, "capacity_unit": "tonnes fabric/day", "forest_adjacent": False},
            {"facility_id": "FAC-0011", "name": "Tirunelveli Captive Wind Farm", "type": "Captive wind farm",
             "district": "Tirunelveli", "state": "Tamil Nadu", "lat": 8.7139, "lon": 77.7567,
             "capacity_value": 40, "capacity_unit": "MW", "forest_adjacent": False},
        ],
        "true": {
            "revenue_cr":          [2650, 2380, 3120, 3290, 3410, 3580],
            "scope1_tco2e":        [92_000, 88_400, 86_900, 81_200, 76_300, 71_760],   # -22.0%
            "scope2_tco2e":        [118_000, 104_000, 96_500, 84_000, 71_200, 60_400],
            "energy_gj":           [2_150_000, 2_050_000, 2_190_000, 2_160_000, 2_120_000, 2_090_000],
            "re_pct":              [31.0, 38.0, 44.0, 52.0, 59.0, 64.0],
            "water_withdrawal_kl": [1_480_000, 1_420_000, 1_390_000, 1_300_000, 1_240_000, 1_180_000],
            "water_discharge_kl":  [210_000, 160_000, 95_000, 30_000, 0, 0],
            "waste_generated_t":   [6_800, 6_500, 6_900, 6_700, 6_600, 6_400],
            "waste_recovered_t":   [5_100, 5_050, 5_500, 5_560, 5_610, 5_570],
            "ltifr":               [0.21, 0.18, 0.15, 0.12, 0.10, 0.08],
            "fatalities":          [0, 0, 0, 0, 0, 0],
            "women_wage_pct":      [33.0, 34.1, 35.6, 36.8, 37.7, 38.5],
            "msme_sourcing_pct":   [41.0, 42.5, 44.0, 45.2, 46.8, 48.0],
            "assurance_type":      ["limited", "limited", "reasonable", "reasonable", "reasonable", "reasonable"],
            "assurance_provider":  ["Natarajan Assurance Services", "Natarajan Assurance Services",
                                    "Natarajan Assurance Services", "Natarajan Assurance Services",
                                    "Natarajan Assurance Services", "Natarajan Assurance Services"],
        },
        "events": {
            "regulatory_actions": [],
            "ocems_exceedances": {"facility_id": "FAC-0010", "fy": "FY2025", "count": 0, "parameters": []},
            "land_alerts": {"facility_id": "FAC-0011", "radius_km": 5, "count": 0, "total_ha": 0.0,
                            "from": "2024-04-01", "to": "2025-03-31"},
            "re_certificates": {"retired_mwh": 95_000, "active_mwh": 0, "vintage": 2024},
        },
        "claims": [
            {"id": "KAV-01", "section": "Climate", "metric": "scope1_tco2e", "fy": "FY2025",
             "text": "Our Scope 1 emissions fell 22% between FY2020 and FY2025, to 71,760 tCO2e.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "92,000 -> 71,760 = -22.0%."},
            {"id": "KAV-02", "section": "Energy", "metric": "re_pct", "fy": "FY2025",
             "text": "Renewable sources, chiefly our captive wind farm, supplied 64% of our electricity in FY2025.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Filed 64.0%."},
            {"id": "KAV-03", "section": "Water", "metric": "water_discharge_kl", "fy": "FY2025",
             "text": "Our Tiruppur processing unit has operated at zero liquid discharge since FY2024.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Discharge 0 kL in FY2024 and FY2025."},
            {"id": "KAV-04", "section": "Water", "metric": "water_withdrawal_kl", "fy": "FY2025",
             "text": "Total water withdrawal decreased by about 20% compared with FY2020.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "1.48 -> 1.18 million kL = -20.3%."},
            {"id": "KAV-05", "section": "People", "metric": "women_wage_pct", "fy": "FY2025",
             "text": "Women received 38.5% of the gross wages we paid in FY2025.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Filed 38.5%."},
            {"id": "KAV-06", "section": "Safety", "metric": "ltifr", "fy": "FY2025",
             "text": "We achieved an LTIFR of 0.08 in FY2025, with zero fatalities for the sixth consecutive year.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "LTIFR 0.08; fatalities 0 for FY2020-FY2025."},
            {"id": "KAV-07", "section": "Compliance", "metric": "regulatory_actions", "fy": "FY2025",
             "text": "No environmental notices, penalties or closure directions were received during the year.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "No regulatory actions."},
            {"id": "KAV-08", "section": "Energy", "metric": "rec_retirement", "fy": "FY2025",
             "text": "Every renewable energy certificate we purchased in 2024 has been retired in our name.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "95,000 MWh retired, 0 active."},
            {"id": "KAV-09", "section": "Assurance", "metric": "assurance_type", "fy": "FY2025",
             "text": "Our BRSR Core disclosures received reasonable assurance for the fourth year running.",
             "expected": "ALIGN", "gw_type": "none", "truth_note": "Reasonable FY2022-FY2025."},
            {"id": "KAV-10", "section": "Supply chain", "metric": None, "fy": "FY2025",
             "text": "All workers across our tier-2 cotton supply chain are paid a living wage.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed",
             "truth_note": "No supply-chain wage data in any source."},
            {"id": "KAV-11", "section": "Targets", "metric": "re_pct", "fy": None,
             "text": "We aim to source 100% of our electricity from renewables by 2030.",
             "expected": "NOT_CHECKABLE", "gw_type": "none", "truth_note": "Future target."},
            {"id": "KAV-12", "section": "Message from the MD", "metric": None, "fy": None,
             "text": "Sustainability is woven into everything we do.",
             "expected": "NOT_CHECKABLE", "gw_type": "vague_claim", "truth_note": "Cheap talk."},
        ],
        "news": [
            {"outlet": "Kongu Business Review", "tier": 5, "date": "2024-09-12",
             "headline": "Kaveri Threads' Tiruppur unit hits zero liquid discharge milestone",
             "facts": ["zero liquid discharge since FY2024", "TNPCB inspection confirmed compliance"]},
            {"outlet": "Kaveri Threads & Textiles Ltd (press release)", "tier": 4, "date": "2025-06-18",
             "headline": "Kaveri Threads reports 64% renewable power, sixth straight year without fatalities",
             "facts": ["64% renewable electricity", "zero fatalities FY2020-FY2025"]},
        ],
    },
    # ------------------------------------------------------------------ D (NOT IN DB)
    {
        "company_id": None,
        "in_db": False,
        "cin": "U40106GJ2016PTC093215",
        "name": "Aurelia Renewables Pvt Ltd",
        "short_name": "Aurelia Renewables",
        "aliases": [],
        "sector": "Power",
        "hq_city": "Ahmedabad", "hq_state": "Gujarat",
        "listing": "Unlisted",
        "report_title": "Sustainability Report 2024-25: Powering Tomorrow",
        "profile": "unknown_company",
        "brand_colour": "#C2410C",
        "facilities": [
            {"facility_id": None, "name": "Kutch Solar Park", "type": "Solar park", "district": "Kutch",
             "state": "Gujarat", "lat": 23.7337, "lon": 69.8597, "capacity_value": 750, "capacity_unit": "MWp",
             "forest_adjacent": False},
        ],
        "true": None,
        "events": {},
        "claims": [
            {"id": "AUR-01", "section": "Climate", "metric": "scope1_tco2e", "fy": "FY2025",
             "text": "Our Scope 1 emissions fell by 30% in FY2025 compared with FY2023.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed", "truth_note": "Company not in any source."},
            {"id": "AUR-02", "section": "Energy", "metric": "re_pct", "fy": "FY2025",
             "text": "100% of the electricity used at our offices and plants in FY2025 was renewable.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed", "truth_note": "Company not in any source."},
            {"id": "AUR-03", "section": "Safety", "metric": "ltifr", "fy": "FY2025",
             "text": "Our LTIFR stood at 0.05 in FY2025.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed", "truth_note": "Company not in any source."},
            {"id": "AUR-04", "section": "Water", "metric": "water_withdrawal_kl", "fy": "FY2025",
             "text": "Robotic dry cleaning of panels cut our water withdrawal by 85% versus FY2022.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed", "truth_note": "Company not in any source."},
            {"id": "AUR-05", "section": "Biodiversity", "metric": "deforestation_ha", "fy": "FY2025",
             "text": "Our Kutch Solar Park caused zero forest loss during FY2025.",
             "expected": "INSUFFICIENT_EVIDENCE", "gw_type": "data_not_disclosed",
             "truth_note": "Not in DB; geo agent may still query alerts by coordinates. Zero alerts near Kutch: may lean ALIGN; accept ALIGN or INSUFFICIENT."},
            {"id": "AUR-06", "section": "Vision", "metric": None, "fy": None,
             "text": "We are passionate about building a cleaner world for future generations.",
             "expected": "NOT_CHECKABLE", "gw_type": "vague_claim", "truth_note": "Cheap talk."},
        ],
        "news": [],
    },
]


def demo_by_id(company_id: str) -> dict:
    for c in DEMO_COMPANIES:
        if c["company_id"] == company_id:
            return c
    raise KeyError(company_id)
