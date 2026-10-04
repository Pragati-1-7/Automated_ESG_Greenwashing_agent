"""
checkability.py

STEP 3: the Checkability / Claim Triage Engine.

WHAT THIS ANSWERS
-------------------
Given an already-extracted, structured ClaimRecord (produced by the Step 2
pipeline), this module answers exactly ONE question:

    "Does this claim currently contain enough specific information that a
    future evidence-retrieval stage could meaningfully search for and
    evaluate evidence about it?"

It does NOT answer "is this claim true?" -- that is a later-phase question
(verification, Step 4+) that requires external evidence. A claim can be
perfectly CHECKABLE and still turn out to be FALSE once evidence is
retrieved (see hard case HC-002, "false but precise"). Equally, a claim
being NOT_CHECKABLE says nothing about whether it is true or false -- it
just means there is nothing concrete enough to search for.

WHY THIS IS RULE-BASED, NOT LLM-BASED
----------------------------------------
By the time a claim reaches this module, Step 2's extraction has already
turned free-form report text into structured fields (metric, value, unit,
scope, boundary, baseline_year, reporting_period, claim_type). Checkability
therefore reduces to a STRUCTURAL question over fields that are already
typed and already null when genuinely absent (Step 2's prompt explicitly
forbids inventing values -- see prompts/claim_extraction_prompt.md rule
13). That means the interesting cases ("is this claim vague?") already
show up as literal missing fields (metric=None, value=None, unit=None),
not as something that requires re-reading the original sentence with an
LLM. A deterministic rule engine over these fields is:
  - fully explainable (every decision traces to a named rule),
  - deterministic and reproducible (same claim -> same result, every time),
  - free to run with zero API keys, zero network access, zero latency.
An LLM call here would add cost and non-determinism without resolving any
question the structured fields don't already answer. (If a future need
arises to detect vagueness in text that nonetheless produced non-null
fields, that would be a narrow, well-scoped addition -- not a reason to
route every claim through an LLM by default.)

WHAT COUNTS AS "ENOUGH INFORMATION" (THE RULES)
--------------------------------------------------
Applied uniformly regardless of the LLM-assigned claim_type label (a
"commitment" with a real metric/value/unit is just as checkable as a
"result" with the same fields -- see PART 5 of the Step 3 spec):

  HARD-REQUIRED, always:
    1. metric is present (non-empty).
    2. unit is present (non-empty).
    3. reporting_period is present (non-empty) -- without SOME period or
       target year, there is no timeframe to search evidence within.
    4. value is present -- UNLESS unit == "boolean", in which case the
       claim is a status/compliance-style claim (e.g. "published its
       BRSR report") that is checkable without a numeric value.

  HARD-REQUIRED, conditionally:
    5. baseline_year is present, but ONLY when unit is an explicitly
       relative/comparison unit ("percent_reduction" or "percent_increase").
       A claim like "reduced emissions by 40%" is meaningless without a
       reference point; a claim like "sourced 92% renewable electricity"
       is a snapshot and does not need one.
    6. scope is present, but ONLY when the metric is emissions-related
       (contains "emission", "scope", "carbon", or "ghg"). A governance or
       workforce-diversity claim does not need a Scope 1/2/3 designation.

  SOFT (recorded for the completeness score and explanation, but never
  by themselves force NOT_CHECKABLE):
    7. boundary is present.
    8. the wording does not match common vague/promotional filler phrases
       with no accompanying metric (a redundant safety net -- see below).

WHAT THIS DELIBERATELY DOES NOT CHECK
----------------------------------------
This engine does not check whether a unit is the DIMENSIONALLY CORRECT
unit for the stated period (e.g. "500 MW generated in FY2024" -- MW is a
capacity unit, not a generation-over-time unit; see hard case HC-008,
UNIT_MISMATCH). It also does not check whether a stated quantity is
PHYSICALLY PLAUSIBLE (e.g. HC-010, CAPACITY_MISMATCH) or whether a stated
scope is genuinely UNAMBIGUOUS (e.g. HC-005, SCOPE_CONFUSION -- the scope
field is non-null ("unspecified (ambiguous)") so it structurally passes
rule 6, even though a human would flag the ambiguity). Those are all
VERIFICATION-stage problems: they require comparing the claim's fields
against external evidence or domain knowledge, not just checking whether
the fields exist. Forcing Step 3 to resolve them would blur checkability
into truth-checking, which Part 2/Part "IMPORTANT DISTINCTIONS" of the
Step 3 spec explicitly warns against.
"""

from __future__ import annotations

from app.utils.schemas import CheckabilityResult, Checkability, ClaimRecord, ClaimType, RuleCheckResult

# Relative/comparison units that require a baseline_year to be interpretable.
_RELATIVE_CHANGE_UNITS = {"percent_reduction", "percent_increase"}

# A unit value of "boolean" marks a status/compliance-style claim (no numeric magnitude).
_BOOLEAN_UNIT = "boolean"

# Keyword fragments that mark a metric as emissions-related (case-insensitive substring match).
_EMISSIONS_METRIC_KEYWORDS = ("emission", "scope", "carbon", "ghg")

# Common vague/promotional filler phrases used only as a redundant, explanatory
# secondary signal -- see module docstring. Never overrides the hard field checks.
_VAGUE_PHRASES = (
    "committed to",
    "greener future",
    "sustainability journey",
    "leader in",
    "proud to",
    "proud leader",
    "we believe",
    "striving",
    "dedicated to",
    "passionate about",
    "meaningful progress",
)


def _is_present(value) -> bool:
    """True if `value` is meaningfully present: not None, and not an
    empty/whitespace-only string. Numeric 0 counts as present (e.g. "zero
    fatal workplace accidents" is a perfectly checkable claim)."""
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _is_emissions_metric(metric: str | None) -> bool:
    if not metric:
        return False
    lowered = metric.lower()
    return any(kw in lowered for kw in _EMISSIONS_METRIC_KEYWORDS)


def _looks_vague(original_text: str) -> bool:
    lowered = original_text.lower()
    return any(phrase in lowered for phrase in _VAGUE_PHRASES)


def assess_checkability(claim: ClaimRecord) -> CheckabilityResult:
    """Run the full Step 3 rule set against a single ClaimRecord and return
    a structured, explainable CheckabilityResult."""

    rules: list[RuleCheckResult] = []
    missing: list[str] = []
    satisfied: list[str] = []

    # --- Rule 1: metric present (hard, always) ---------------------------
    metric_ok = _is_present(claim.metric)
    rules.append(RuleCheckResult(
        rule_name="metric_present",
        applicable=True,
        passed=metric_ok,
        detail=(
            f"A specific metric is identified ('{claim.metric}')."
            if metric_ok else
            "No specific ESG metric was identified for this claim."
        ),
    ))
    (satisfied if metric_ok else missing).append("metric")

    # --- Rule 2: unit present (hard, always) ------------------------------
    unit_ok = _is_present(claim.unit)
    rules.append(RuleCheckResult(
        rule_name="unit_present",
        applicable=True,
        passed=unit_ok,
        detail=(
            f"A unit is specified ('{claim.unit}')."
            if unit_ok else
            "No unit is specified, so any number present cannot be interpreted."
        ),
    ))
    (satisfied if unit_ok else missing).append("unit")

    # --- Rule 3: reporting_period present (hard, always) ------------------
    period_ok = _is_present(claim.reporting_period)
    rules.append(RuleCheckResult(
        rule_name="reporting_period_present",
        applicable=True,
        passed=period_ok,
        detail=(
            f"A reporting period / target year is specified ('{claim.reporting_period}')."
            if period_ok else
            "No reporting period or target year is specified, so there is no timeframe to search evidence within."
        ),
    ))
    (satisfied if period_ok else missing).append("reporting_period")

    # --- Rule 4: value present, unless unit == "boolean" (hard, conditional on unit) ---
    is_boolean_claim = (claim.unit or "").strip().lower() == _BOOLEAN_UNIT
    value_ok = True if is_boolean_claim else _is_present(claim.value)
    rules.append(RuleCheckResult(
        rule_name="value_present_or_boolean",
        applicable=True,
        passed=value_ok,
        detail=(
            "This is a status/compliance-style claim (unit='boolean'), so no numeric value is required."
            if is_boolean_claim else
            (f"A numeric value is specified ({claim.value})." if value_ok else
             "No numeric value is specified for a claim that is not a boolean/status claim.")
        ),
    ))
    if not is_boolean_claim:
        (satisfied if value_ok else missing).append("value")

    # --- Rule 5: baseline_year present, only if unit implies a relative change (hard, conditional) ---
    baseline_required = (claim.unit or "").strip().lower() in _RELATIVE_CHANGE_UNITS
    baseline_ok = _is_present(claim.baseline_year) if baseline_required else True
    rules.append(RuleCheckResult(
        rule_name="baseline_present_if_relative_change",
        applicable=baseline_required,
        passed=baseline_ok,
        detail=(
            (f"A baseline year is specified ('{claim.baseline_year}'), needed to interpret a "
             f"relative-change unit ('{claim.unit}').")
            if baseline_required and baseline_ok else
            (f"Unit '{claim.unit}' expresses a relative change, but no baseline year is given, "
             f"so the change has no reference point.")
            if baseline_required and not baseline_ok else
            f"Not applicable: unit '{claim.unit}' is a snapshot/share, not a relative change, so no baseline is needed."
        ),
    ))
    if baseline_required:
        (satisfied if baseline_ok else missing).append("baseline_year")

    # --- Rule 6: scope present, only if metric is emissions-related (hard, conditional) ---
    scope_required = _is_emissions_metric(claim.metric)
    scope_ok = _is_present(claim.scope) if scope_required else True
    rules.append(RuleCheckResult(
        rule_name="scope_present_if_emissions_metric",
        applicable=scope_required,
        passed=scope_ok,
        detail=(
            (f"Scope is specified ('{claim.scope}') for this emissions-related metric.")
            if scope_required and scope_ok else
            "This is an emissions-related metric, but no Scope 1/2/3 or equivalent boundary is given."
            if scope_required and not scope_ok else
            "Not applicable: this metric is not emissions-related, so no Scope 1/2/3 designation is needed."
        ),
    ))
    if scope_required:
        (satisfied if scope_ok else missing).append("scope")

    # --- Rule 7 (soft): boundary present -----------------------------------
    boundary_ok = _is_present(claim.boundary)
    rules.append(RuleCheckResult(
        rule_name="boundary_present",
        applicable=True,
        passed=boundary_ok,
        detail=(
            f"An organizational boundary is specified ('{claim.boundary}')."
            if boundary_ok else
            "No organizational boundary (e.g. company-wide vs. a specific facility) is stated; "
            "retrieval will default to a company-wide search."
        ),
    ))
    if boundary_ok:
        satisfied.append("boundary")
    # NOTE: boundary is intentionally NOT added to `missing` even when absent -- it is a
    # soft/advisory field only (see module docstring), so its absence never forces NOT_CHECKABLE.

    # --- Rule 8 (soft): wording is not generic vague/promotional filler ----
    vague_wording = _looks_vague(claim.original_text) and not metric_ok
    rules.append(RuleCheckResult(
        rule_name="specific_wording",
        applicable=True,
        passed=not vague_wording,
        detail=(
            "Wording matches common vague/promotional phrasing (e.g. 'committed to', "
            "'greener future') with no accompanying metric."
            if vague_wording else
            "Wording is not flagged as generic vague/promotional filler."
        ),
    ))
    # Soft rule: contributes to the completeness score below but never appears in `missing`,
    # since rules 1-6 already capture the structural reason a vague claim is NOT_CHECKABLE.

    # --- Final decision: CHECKABLE iff every HARD-required, applicable rule passed ---
    hard_rule_names = {
        "metric_present", "unit_present", "reporting_period_present",
        "value_present_or_boolean", "baseline_present_if_relative_change",
        "scope_present_if_emissions_metric",
    }
    hard_failures = [r for r in rules if r.rule_name in hard_rule_names and r.applicable and not r.passed]
    is_checkable = len(hard_failures) == 0

    checkability = Checkability.CHECKABLE if is_checkable else Checkability.NOT_CHECKABLE

    if is_checkable:
        reason = (
            f"CHECKABLE: all required structural fields for a claim of this shape are present "
            f"({', '.join(satisfied)}). This claim has enough specific information to be handed "
            f"to a future evidence-retrieval stage. (This does NOT mean the claim is true -- only "
            f"that it can be meaningfully checked.)"
        )
    else:
        reason = (
            f"NOT_CHECKABLE: missing required field(s) [{', '.join(missing)}]. Without these, "
            f"there is not enough specific information to search for or evaluate evidence about "
            f"this claim."
        )

    # --- Completeness score: percentage of APPLICABLE rules (hard + soft) that passed ---
    applicable_rules = [r for r in rules if r.applicable]
    completeness = (
        round(100 * sum(1 for r in applicable_rules if r.passed) / len(applicable_rules), 1)
        if applicable_rules else 0.0
    )

    extraction_time = claim.checkability  # what Step 2's extraction/mock provider guessed
    agrees = (extraction_time == checkability) if extraction_time is not None else None

    return CheckabilityResult(
        claim_id=claim.claim_id,
        claim_type=claim.claim_type,
        checkability=checkability,
        reason=reason,
        missing_fields=missing,
        satisfied_fields=satisfied,
        rule_results=rules,
        checkability_completeness=completeness,
        extraction_time_checkability=extraction_time,
        agrees_with_extraction=agrees,
        method="rule_based",
    )


def assess_checkability_batch(claims: list[ClaimRecord]) -> list[CheckabilityResult]:
    """Convenience helper: run assess_checkability over a list of claims."""
    return [assess_checkability(c) for c in claims]


def filter_checkable(claims: list[ClaimRecord]) -> tuple[list[ClaimRecord], list[ClaimRecord]]:
    """Split claims into (checkable, not_checkable) using this module's own
    rule-based determination (NOT the extraction-time guess). This is the
    function a future retrieval stage (Step 4+) should call: only the first
    list should ever be sent on to evidence retrieval."""
    checkable: list[ClaimRecord] = []
    not_checkable: list[ClaimRecord] = []
    for claim in claims:
        result = assess_checkability(claim)
        (checkable if result.checkability == Checkability.CHECKABLE else not_checkable).append(claim)
    return checkable, not_checkable
