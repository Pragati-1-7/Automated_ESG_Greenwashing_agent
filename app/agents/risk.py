"""
Risk aggregator. The PS asks for "an algorithmic mechanism to aggregate the
contradictions into a single Greenwashing Risk Score (0-100)".

Claim score = 100 * sigmoid(b + sum_i w_i * x_i) over decision-engine outputs:

  x = [P(contradict), P(insufficient), severity, materiality, vagueness,
       P(indeterminate action), contradicted-by-tier-1/2 evidence]

The weights are NOT hand-picked points: `eval/fit_risk.py` fits them by
logistic regression on the benchmark train split (target = greenwashing
case: CONTRADICT label or vague cheap talk) and writes
data/models/risk_weights.json. Until fitted, documented priors are used.

Company score = 0.6 * materiality-weighted mean + 0.4 * mean of the worst
three claims, so one severe contradiction is not averaged away.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache

from app.core.config import ROOT
from app.core.models import ClaimResult, Risk, RiskComponent

WEIGHTS_PATH = ROOT / "data" / "models" / "risk_weights.json"

FEATURES = ["p_contradict", "p_insufficient", "severity", "materiality", "vagueness", "p_indeterminate",
            "high_tier_contradiction"]
PRIOR = {"bias": -3.0, "p_contradict": 4.5, "p_insufficient": 1.0, "severity": 1.5, "materiality": 0.8,
         "vagueness": 1.2, "p_indeterminate": 1.0, "high_tier_contradiction": 1.0}
NOTES = {
    "p_contradict": "Decision-engine probability that external evidence contradicts the claim",
    "p_insufficient": "Probability that nothing external can confirm the claim (unverifiable)",
    "severity": "Decision-engine rating of how serious the discrepancy is",
    "materiality": "How much the claim matters to investors and regulators",
    "vagueness": "Probability the statement is vague, non-falsifiable cheap talk",
    "p_indeterminate": "A3CG: probability the action is indeterminate rhetoric",
    "high_tier_contradiction": "A regulatory filing or regulator record contradicts the claim",
}


@lru_cache(maxsize=1)
def weights() -> dict[str, float]:
    if WEIGHTS_PATH.exists():
        return json.loads(WEIGHTS_PATH.read_text())["weights"]
    return dict(PRIOR)


def band(score: float) -> str:
    return "Low" if score < 25 else "Moderate" if score < 50 else "High" if score < 75 else "Very High"


def features(c: ClaimResult, severity: float) -> dict[str, float]:
    probs = c.verdict.probabilities if c.verdict else {}
    hi = any(e.stance and e.stance.label == "contradict" and e.tier <= 2 for s in c.sub_claims for e in s.evidence)
    if c.verdict and c.verdict.label == "NOT_CHECKABLE":
        pc, pi = 0.0, 0.0
    else:
        pc, pi = probs.get("CONTRADICT", 0.0), probs.get("INSUFFICIENT_EVIDENCE", 0.0)
    return {"p_contradict": pc, "p_insufficient": pi, "severity": severity if pc >= 0.5 else 0.0,
            "materiality": c.triage.materiality, "vagueness": c.triage.vagueness,
            "p_indeterminate": c.triage.action_probs.get("indeterminate", 0.0), "high_tier_contradiction": float(hi)}


def claim_risk(c: ClaimResult, severity: float) -> Risk:
    w = weights()
    x = features(c, severity)
    z = w["bias"] + sum(w[k] * x[k] for k in FEATURES)
    s = round(100 / (1 + math.exp(-z)), 1)
    comps = [RiskComponent(name=k, value=round(x[k], 3), weight=round(w[k], 3), contribution=round(w[k] * x[k], 3),
                           note=NOTES[k]) for k in FEATURES]
    comps.append(RiskComponent(name="bias", value=1.0, weight=round(w["bias"], 3), contribution=round(w["bias"], 3),
                               note="Intercept (fitted)"))
    return Risk(score=s, band=band(s), components=comps)


def company_risk(claims: list[ClaimResult]) -> float | None:
    scored = [c for c in claims if c.risk]
    if not scored:
        return None
    wsum = sum(c.triage.materiality + 0.1 for c in scored)
    mean = sum((c.triage.materiality + 0.1) * c.risk.score for c in scored) / wsum
    worst = sorted((c.risk.score for c in scored), reverse=True)[:3]
    return round(0.6 * mean + 0.4 * sum(worst) / len(worst), 1)
