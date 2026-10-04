"""
Versioned question texts for the Jev decision engine. Kept in one module so
prompt changes are reviewable in one diff. PROMPT_VERSION is recorded in
every analysis.

Design sources (see docs/TECHNICAL_SUMMARY.md):
  - claim definition: Stammbach et al., "Environmental Claim Detection" (ACL 2023)
  - action labels: Ong et al., A3CG aspect-action (implemented / planning / indeterminate)
  - decomposition into typed checks: ProgramFC (ACL 2023), AFEV (2025)
  - stance + verdict with abstention: MiniCheck (EMNLP 2024), EmeraldMind (2025)
  - iterative retrieve-until-sufficient: FIRE (NAACL Findings 2025), DEFAME (ICML 2025)
"""

from __future__ import annotations

from data_gen.spec import METRICS

PROMPT_VERSION = "v2.0"

# ---------------------------------------------------------------- extractor
IS_CLAIM = (
    "The text is one sentence from a company's sustainability or annual report. Does it make a claim about "
    "THIS company's own environmental, social or governance performance, record, compliance, certification "
    "or commitment (for example an emissions figure, a percentage reduction, a safety record, 'no penalties', "
    "'zero deforestation', an assurance level, a target year, or a broad sustainability pledge)? Answer no for "
    "definitions, methodology notes, descriptions of frameworks, general industry context, table-of-contents "
    "lines, figure or table captions, raw table rows, incomplete sentence fragments, and descriptions of products or business activities without a sustainability performance element."
)

METRIC_OPTIONS: dict[str, str | None] = {k: v["label"] for k, v in METRICS.items()}
METRIC_OPTIONS["none"] = "No specific measurable ESG metric (vague statement, policy, or something else)"
METRIC_Q = "Which single ESG metric is this sentence's claim primarily about?"

# ---------------------------------------------------------------- triage (A3CG)
ACTION_Q = "Classify the company action described in this sustainability statement."
ACTION_OPTIONS = {
    "implemented": "Reports something already done or a measured result for a past period (a concrete, "
                   "attributable outcome, figure, record or certification).",
    "planning": "States a future target, goal, aim, ambition or commitment that has not yet been achieved.",
    "indeterminate": "Vague, evasive or non-attributable rhetoric with no concrete action or measurable outcome "
                     "(cheap talk).",
}
VAGUE_Q = ("Is this statement vague or non-falsifiable, meaning no external data could ever show it to be true or "
           "false?")
CHECKABLE_Q = ("Could this claim, in principle, be checked against external records such as regulatory filings, "
               "emissions monitoring data, regulator orders, satellite forest-loss alerts, certificate registries, "
               "assurance statements or news reports?")
MATERIALITY_Q = ("How material would this claim be to an investor or regulator assessing the company's "
                 "sustainability performance?")
MATERIALITY_LEVELS = ["minor", "moderate", "significant", "critical"]

# ---------------------------------------------------------------- decomposer
CHECK_TYPE_Q = "What kind of check is needed to verify this claim fragment?"
CHECK_TYPE_OPTIONS = {
    "pct_change": "A percentage or multiple change of a metric between two periods (reduced by X%, doubled since).",
    "point_value": "A specific value of a metric in one period (e.g. LTIFR of 0.08, 71,760 tCO2e, 1.8 lakh tonnes).",
    "share": "A percentage share in one period (e.g. 64% renewable electricity, 4.1% of wages, 92% recycled).",
    "zero_events": "A claim that something did not happen or happened zero times (no exceedances, zero fatalities, "
                   "within limits).",
    "compliance": "A claim about regulatory compliance, violations, notices, penalties or closure directions.",
    "geo": "A claim about deforestation, forest loss or land use at or around a site.",
    "certificate": "A claim about renewable energy certificates being purchased, retired or counted.",
    "assurance": "A claim about the type or level of external assurance or audit of the disclosures.",
    "other": "Anything else.",
}

# ---------------------------------------------------------------- router
SOURCE_QUESTIONS = {
    "brsr": "Would the company's annual SEBI BRSR Core filing (Scope 1 and 2 emissions, emission intensity, energy, "
            "renewable electricity share, water withdrawal and discharge, waste generated and recovered, LTIFR, "
            "fatalities, women's share of wages, MSME sourcing, assurance type) contain data to check this claim?",
    "facility_ghg": "Would facility-level greenhouse gas registry data (CO2, CH4, N2O per plant per year) help "
                    "check this claim?",
    "ocems": "Would continuous emission monitoring (OCEMS) exceedance records for the company's plants help "
             "check this claim?",
    "regulatory": "Would regulator and tribunal records (NGT orders, pollution control board notices, penalties, "
                  "closure directions) help check this claim?",
    "land_alerts": "Would satellite forest-loss alerts near the company's sites help check this claim?",
    "rec_registry": "Would the renewable energy certificate registry (certificates retired or still active) help "
                    "check this claim?",
    "assurance": "Would independent assurance statements on the company's BRSR disclosures help check this claim?",
    "news": "Would news coverage or press releases about the company help check this claim?",
}
SOURCE_THRESHOLD = 0.45

# ---------------------------------------------------------------- investigator (FIRE stop rule)
SUFFICIENT_Q = ("Taken together, is the evidence above sufficient to decide whether the claim is accurate or "
                "inaccurate for the stated period?")

# ---------------------------------------------------------------- judge / verdict
RELEVANT_Q = ("Is this evidence about the same specific topic as the claim (the same metric, event type, site or "
              "certification), so that it could confirm or refute it? Evidence about a different topic, even if "
              "negative about the company, is NOT relevant. A different quantity is also NOT relevant: water withdrawn is not "
              "water replenished, the company's own wages are not its suppliers' wages, Scope 1 is not Scope 3, and an "
              "emission-limit exceedance is not a regulator's action.")
STANCE_Q = "Compare the company's claim with the external evidence. What is the evidence's stance on the claim?"
STANCE_OPTIONS = {
    "support": "The evidence confirms the claim for the claimed period. Small rounding differences (within about "
               "3% relative) still count as confirmation.",
    "contradict": "The evidence shows the claim is false, overstated or misleading for the claimed period.",
    "insufficient": "The evidence does not address this claim, covers a different period or entity, or is too weak "
                    "to judge.",
}
VERDICT_Q = ("You are an ESG assurance analyst. Considering all the evidence and its reliability, what is the "
             "verdict on the company's claim?")
VERDICT_OPTIONS = {
    "ALIGN": "Reliable external evidence confirms the claim.",
    "CONTRADICT": "Reliable external evidence shows the claim is false, overstated or misleading. Regulatory filings "
                  "and regulator records (tiers 1-2) outweigh company press releases (tier 4).",
    "INSUFFICIENT_EVIDENCE": "No reliable external evidence addresses the claim, so it can be neither confirmed nor "
                             "refuted.",
}
SEVERITY_Q = "If this claim is inaccurate, how severe is the discrepancy for investors and regulators?"
SEVERITY_LEVELS = ["none", "minor", "moderate", "severe"]

# ---------------------------------------------------------------- resolver
SAME_ENTITY_Q = ("Do the company named in the report and the registry record refer to the same legal entity? "
                 "Generic shared words such as 'Renewable', 'Power' or 'Steel' are not enough.")
