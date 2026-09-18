"""
query_planner.py

STEP 4: Deterministic query generator for evidence retrieval.

WHAT THIS DOES
--------------
Given a CHECKABLE ClaimRecord, this module generates 2-4 targeted keyword
search queries. The queries are used by the BM25 and semantic retrievers to
find relevant evidence from the evidence corpus.

WHY DETERMINISTIC?
------------------
The query planner is intentionally rule-based, not LLM-based, for three
reasons that matter in an academic EY project:

  1. Reproducibility: the same claim always produces the same queries, which
     makes tests easy to write and results easy to explain.
  2. Cost: no API calls needed, works fully offline.
  3. Interpretability: a human reviewer can see exactly why those queries were
     chosen and verify that they are appropriate.

HOW QUERIES ARE BUILT
----------------------
Each claim already has structured fields extracted in Step 2:
  - company, metric, scope, reporting_period, baseline_year, value, unit.

The planner uses these fields to build queries from most-specific to
most-general:
  1. Query 1 (most specific): company + metric + reporting_period [+ scope]
  2. Query 2: company + metric + baseline_year (if present)
  3. Query 3: company + reporting_period + sustainability/emissions/ESG
  4. Query 4 (most general): company + sustainability report

OPTIONAL LLM EXTENSION
-----------------------
An LLM-augmented version is sketched at the bottom of this file (commented
out). It is NOT used by default: the deterministic path is always available
and is what the tests rely on.
"""

from __future__ import annotations

from app.utils.schemas import ClaimRecord, QueryPlan


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_query_plan(claim: ClaimRecord) -> QueryPlan:
    """Generate a deterministic QueryPlan for one CHECKABLE claim.

    Args:
        claim: A ClaimRecord that has already been confirmed CHECKABLE by the
               Step 3 checkability engine. The planner does not re-check
               checkability -- call filter_checkable() before calling this.

    Returns:
        A QueryPlan containing 2-4 search queries, most targeted first.
    """
    queries: list[str] = []

    company = claim.company.strip()
    metric = (claim.metric or "").replace("_", " ").strip()
    period = (claim.reporting_period or "").strip()
    baseline = (claim.baseline_year or "").strip()
    scope = (claim.scope or "").strip()
    unit = (claim.unit or "").strip()

    # --- Query 1: most specific -------------------------------------------
    # company + metric + period (+ scope if present)
    parts_q1 = [company, metric, period]
    if scope and scope.lower() not in ("", "none"):
        parts_q1.append(scope)
    queries.append(_clean_query(parts_q1))

    # --- Query 2: add baseline year if it adds information ----------------
    if baseline and baseline != period:
        parts_q2 = [company, metric, baseline, period]
        q2 = _clean_query(parts_q2)
        if q2 not in queries:
            queries.append(q2)

    # --- Query 3: general metric + sustainability context -----------------
    # Derive a readable domain hint from the metric name
    domain_hint = _metric_to_domain_hint(claim.metric or "")
    parts_q3 = [company, period, domain_hint] if domain_hint else [company, period, "sustainability"]
    q3 = _clean_query(parts_q3)
    if q3 not in queries:
        queries.append(q3)

    # --- Query 4: broad fallback ------------------------------------------
    parts_q4 = [company, "sustainability report", period if period else ""]
    q4 = _clean_query(parts_q4)
    if q4 not in queries and len(queries) < 4:
        queries.append(q4)

    return QueryPlan(
        claim_id=claim.claim_id,
        company=company,
        queries=queries,
        generation_method="deterministic",
    )


def generate_query_plans(claims: list[ClaimRecord]) -> list[QueryPlan]:
    """Convenience: generate QueryPlans for a list of claims."""
    return [generate_query_plan(c) for c in claims]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean_query(parts: list[str]) -> str:
    """Join non-empty parts with a space, strip extra whitespace."""
    return " ".join(p.strip() for p in parts if p and p.strip())


# Map common metric name fragments to a human-readable domain hint for query 3.
_METRIC_DOMAIN_HINTS: list[tuple[tuple[str, ...], str]] = [
    (("emission", "scope", "carbon", "ghg", "co2"), "emissions reduction"),
    (("energy", "renewable", "electricity", "solar", "wind"), "renewable energy"),
    (("water", "withdrawal", "liquid", "discharge"), "water management"),
    (("waste", "recycl", "plastic", "ewaste", "e-waste"), "waste recycling"),
    (("women", "gender", "diversity", "inclusion"), "gender diversity"),
    (("safety", "accident", "fatality", "fatal", "injury"), "workplace safety"),
    (("disclosure", "brsr", "report", "compliance"), "sustainability disclosure"),
    (("deforestation", "forest", "cotton", "sourcing"), "sustainable sourcing"),
    (("neutrality", "net.zero", "carbon neutral"), "carbon neutrality"),
]


def _metric_to_domain_hint(metric: str) -> str:
    """Return a short domain hint string for the metric, or empty string if unknown."""
    lowered = metric.lower()
    for keywords, hint in _METRIC_DOMAIN_HINTS:
        if any(kw in lowered for kw in keywords):
            return hint
    return ""
