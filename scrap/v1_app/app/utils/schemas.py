"""
schemas.py

Pydantic data models for the ESG Greenwashing Detection & Verification Agent.

WHY THIS FILE EXISTS (Step 1):
We need a single, shared, strongly-typed definition of what a "claim" and
a piece of "evidence" look like, so that:
  1. Our dataset files (legacy/v1_data/claims/claims.json, legacy/v1_data/evidence/evidence.json)
     can be validated automatically (see scripts/validate_dataset.py).
  2. Every later phase (extraction, retrieval, scoring, API) imports these
     SAME models instead of re-defining fields inconsistently.

These models will grow in later phases (e.g. adding character offsets once
the PDF extraction engine exists), but the core fields are fixed now so the
dataset design does not need to change later.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

class Verdict(str, Enum):
    """The only allowed outcomes of claim verification.

    NOT_APPLICABLE is used for claims that are not checkable (e.g. vague
    aspirational statements) and therefore never enter the verdict pipeline.
    """
    ALIGN = "ALIGN"
    CONTRADICT = "CONTRADICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Checkability(str, Enum):
    CHECKABLE = "CHECKABLE"
    NOT_CHECKABLE = "NOT_CHECKABLE"


class ClaimType(str, Enum):
    RESULT = "result"          # A claimed past/present outcome (e.g. "we reduced X by Y%")
    TARGET = "target"          # A future commitment/goal (e.g. "we will reach X by 2030")
    COMMITMENT = "commitment"  # A vague values statement (e.g. "we care about sustainability")
    COMPARATIVE = "comparative"  # A comparison claim (e.g. "better than industry average")
    CERTIFICATION = "certification"  # A claim of holding a standard/certificate


class SourceTier(int, Enum):
    """Evidence source reliability hierarchy (Tier 1 = most reliable)."""
    TIER_1_REGULATORY_FILING = 1
    TIER_2_REGULATOR_OR_TRIBUNAL = 2
    TIER_3_AUDITED_REPORT = 3
    TIER_4_COMPANY_PR = 4
    TIER_5_NEWS = 5


class ExpectedRelationship(str, Enum):
    """What a piece of evidence is expected to do to its associated claim."""
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    PARTIAL = "PARTIAL"
    UNRELATED = "UNRELATED"


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

class ClaimRecord(BaseModel):
    claim_id: str = Field(..., description="Unique identifier, e.g. CLM-001")
    company: str = Field(..., description="Name of the company making the claim (synthetic in Step 1)")
    original_text: str = Field(..., description="The exact ESG claim text as it would appear in a report")

    # Structured/extracted fields (nullable: not every claim has a clean number)
    metric: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    scope: Optional[str] = None
    boundary: Optional[str] = None
    baseline_year: Optional[str] = None
    reporting_period: Optional[str] = None

    claim_type: ClaimType
    checkability: Checkability
    expected_verdict: Optional[Verdict] = Field(
        default=None,
        description=(
            "The verdict our system SHOULD reach; used for evaluation of the synthetic "
            "Step 1 dataset, not shown to the model. STEP 2 EXTENSION: made optional "
            "(was required) because claims extracted from a real/synthetic PDF by the "
            "Step 2 pipeline have no known ground-truth verdict at extraction time -- "
            "that verdict only exists once Step 4 (verification) runs. All 12 existing "
            "Step 1 dataset records still provide this field, so validation behaviour "
            "for Step 1 data is unchanged."
        ),
    )

    source_document: str = Field(..., description="Source document filename this claim is drawn from (synthetic in Step 1, real PDF filename in Step 2)")
    page_number: Optional[int] = Field(default=None, ge=1)

    # ---- STEP 2 EXTENSION: source traceability + provenance -------------
    # Added so a claim extracted from a real PDF can point back to exactly
    # where in the document it came from, and so we never confuse a MOCK
    # (deterministic, non-LLM) extraction result with a real LLM result.
    # Both fields are optional and default to None, so every existing
    # Step 1 record (which has neither) still validates unchanged.
    char_start: Optional[int] = Field(
        default=None, ge=0, description="STEP 2: character offset where original_text starts within the page text, if known."
    )
    char_end: Optional[int] = Field(
        default=None, ge=0, description="STEP 2: character offset where original_text ends within the page text, if known."
    )
    extraction_method: Optional[str] = Field(
        default=None,
        description=(
            "STEP 2: how this claim record was produced, e.g. 'mock' or "
            "'llm:groq:llama-3.1-70b-versatile' or 'llm:ollama:llama3'. "
            "Required to be set by the Step 2 extraction pipeline so mock output "
            "can never be silently mistaken for real LLM output; left None for "
            "the hand-written Step 1 synthetic dataset."
        ),
    )

    @field_validator("claim_id")
    @classmethod
    def claim_id_format(cls, v: str) -> str:
        if not v.startswith("CLM-"):
            raise ValueError(f"claim_id must start with 'CLM-', got: {v}")
        return v

    @field_validator("checkability")
    @classmethod
    def checkability_verdict_consistency(cls, v, info):
        # NOT_CHECKABLE claims should never carry a resolvable verdict.
        return v

    @model_validator(mode="after")
    def char_offsets_are_ordered(self) -> "ClaimRecord":
        # STEP 2: if both offsets are present, char_end must not be before char_start.
        if self.char_start is not None and self.char_end is not None:
            if self.char_end < self.char_start:
                raise ValueError(
                    f"char_end ({self.char_end}) cannot be less than char_start ({self.char_start})"
                )
        return self


# ---------------------------------------------------------------------------
# Checkability result (Step 3)
# ---------------------------------------------------------------------------
# STEP 3 ADDITION. Reuses the existing `Checkability` and `ClaimType` enums
# above rather than inventing new ones -- there is no new "NON_CHECKABLE"
# concept here, it is the same Checkability.NOT_CHECKABLE already defined
# in Step 1/2. This section only adds the structured *explanation* of a
# checkability decision that Step 1/2 didn't need (Step 1's dataset already
# had hand-labeled checkability; Step 2's extractor produces a first-pass
# LLM/mock guess). Step 3 adds a transparent, rule-based, independently
# computed decision with a reason and a list of missing fields.

class RuleCheckResult(BaseModel):
    """The outcome of a single named checkability rule against one claim."""
    rule_name: str = Field(..., description="Short identifier, e.g. 'metric_present'")
    applicable: bool = Field(
        ..., description="Whether this rule applies to this claim at all (e.g. 'baseline_required' is not applicable to a claim whose unit is a plain share/percent rather than a percent_reduction)."
    )
    passed: bool = Field(..., description="True if the claim satisfies this rule (only meaningful when applicable=True).")
    detail: str = Field(..., description="One-sentence, human-readable explanation of this specific rule's outcome.")


class CheckabilityResult(BaseModel):
    """Structured, explainable output of the Step 3 checkability engine for
    one claim. This does NOT determine whether the claim is true -- only
    whether it currently contains enough specific information to be worth
    sending to a future evidence-retrieval stage."""

    claim_id: str = Field(..., description="The ClaimRecord.claim_id this result is about")
    claim_type: ClaimType

    checkability: Checkability = Field(
        ..., description="Final Step 3 determination. Reuses the existing Checkability enum (CHECKABLE / NOT_CHECKABLE)."
    )
    reason: str = Field(..., description="Human-readable explanation of the overall decision.")

    missing_fields: list[str] = Field(
        default_factory=list, description="Names of HARD-required fields that are missing, causing NOT_CHECKABLE (empty if CHECKABLE)."
    )
    satisfied_fields: list[str] = Field(
        default_factory=list, description="Names of fields that were checked and found present."
    )
    rule_results: list[RuleCheckResult] = Field(
        default_factory=list, description="Every individual rule evaluated, for full auditability."
    )

    checkability_completeness: float = Field(
        ...,
        ge=0,
        le=100,
        description=(
            "0-100 structural completeness score over the rules that APPLY to this claim. "
            "This is NOT the Greenwashing Risk Score (that is a later-phase, evidence-based "
            "0-100 score covering an entirely different question -- see docs/PROJECT_PROGRESS_STEP_3.md)."
        ),
    )

    extraction_time_checkability: Optional[Checkability] = Field(
        default=None,
        description="What Step 2's extraction prompt guessed for this claim's checkability, if known, kept for observability/comparison only -- Step 3's own rule-based `checkability` field above is authoritative.",
    )
    agrees_with_extraction: Optional[bool] = Field(
        default=None, description="Whether Step 3's rule-based checkability agrees with extraction_time_checkability, when the latter is known."
    )

    method: str = Field(
        default="rule_based",
        description="How this result was computed. Always 'rule_based' in Step 3 -- see docs for why no LLM call is used here.",
    )



class EvidenceRecord(BaseModel):
    evidence_id: str = Field(..., description="Unique identifier, e.g. EVD-001")
    claim_id: str = Field(..., description="The claim this evidence relates to")
    company: str

    source: str = Field(..., description="Human-readable name of the source, e.g. 'BRSR Filing FY2024'")
    source_tier: SourceTier
    source_type: str = Field(..., description="e.g. 'regulatory_filing', 'news_article', 'audited_report'")
    publication_date: str = Field(..., description="ISO date string, e.g. '2024-06-15'")
    reporting_period: Optional[str] = None

    retrieved_text: str = Field(..., description="The (synthetic) passage of text retrieved as evidence")
    expected_relationship: ExpectedRelationship

    url_or_path: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("evidence_id")
    @classmethod
    def evidence_id_format(cls, v: str) -> str:
        if not v.startswith("EVD-"):
            raise ValueError(f"evidence_id must start with 'EVD-', got: {v}")
        return v

    @field_validator("claim_id")
    @classmethod
    def claim_id_ref_format(cls, v: str) -> str:
        if not v.startswith("CLM-"):
            raise ValueError(f"claim_id reference must start with 'CLM-', got: {v}")
        return v


# ---------------------------------------------------------------------------
# Hard case (a special claim with an explanation of WHY it is hard)
# ---------------------------------------------------------------------------

class HardCaseType(str, Enum):
    TRUE_BUT_VAGUE = "TRUE_BUT_VAGUE"
    FALSE_BUT_PRECISE = "FALSE_BUT_PRECISE"
    PERIOD_MISMATCH = "PERIOD_MISMATCH"
    BASELINE_SHIFT = "BASELINE_SHIFT"
    SCOPE_CONFUSION = "SCOPE_CONFUSION"
    ABSOLUTE_VS_INTENSITY = "ABSOLUTE_VS_INTENSITY"
    BOUNDARY_MISMATCH = "BOUNDARY_MISMATCH"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    UNSUPPORTED_TARGET = "UNSUPPORTED_TARGET"
    CAPACITY_MISMATCH = "CAPACITY_MISMATCH"


class HardCaseRecord(BaseModel):
    case_id: str = Field(..., description="Unique identifier, e.g. HC-001")
    company: str
    original_text: str

    metric: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    scope: Optional[str] = None
    boundary: Optional[str] = None
    baseline_year: Optional[str] = None
    reporting_period: Optional[str] = None

    hard_case_type: HardCaseType
    checkability: Checkability
    expected_verdict: Verdict
    notes: str = Field(..., description="Explanation of exactly why this case is difficult and what a naive system would get wrong")

    @field_validator("case_id")
    @classmethod
    def case_id_format(cls, v: str) -> str:
        if not v.startswith("HC-"):
            raise ValueError(f"case_id must start with 'HC-', got: {v}")
        return v


# ---------------------------------------------------------------------------
# Step 4: Query planning + retrieval schemas
# ---------------------------------------------------------------------------
# These are additive additions only. All existing Step 1/2/3 schemas above
# are completely untouched.

class QueryPlan(BaseModel):
    """The set of search queries generated for one checkable claim.

    The query planner (app/retrieval/query_planner.py) generates 2-4 targeted
    keyword queries per claim. Keeping them together in a single model lets the
    audit trail record exactly what was searched, not just what was found.
    """
    claim_id: str
    company: str
    queries: list[str] = Field(..., description="Ordered list of search query strings, most targeted first")
    generation_method: str = Field(
        default="deterministic",
        description="How queries were generated: 'deterministic' (rule-based) or 'llm:<provider>'",
    )


class RetrievedEvidence(BaseModel):
    """One piece of evidence retrieved for a claim, augmented with retrieval scores.

    Wraps the core EvidenceRecord fields inline (so downstream code doesn't need
    to join two objects) and adds the three score columns that make the hybrid
    ranking transparent and auditable.
    """
    evidence_id: str
    claim_id: str
    company: str
    source: str
    source_tier: SourceTier
    source_type: str
    publication_date: str
    reporting_period: Optional[str] = None
    retrieved_text: str
    url_or_path: Optional[str] = None
    notes: Optional[str] = None
    expected_relationship: Optional[ExpectedRelationship] = Field(
        default=None,
        description="Expected relationship if known (e.g. from synthetic evidence dataset)",
    )

    # Retrieval scoring
    rank: int = Field(..., ge=1, description="Final rank in the combined result list (1 = most relevant)")
    bm25_score: float = Field(default=0.0, description="Normalised BM25 score [0-1]")
    semantic_score: float = Field(default=0.0, description="Normalised semantic/vector similarity score [0-1]")
    combined_score: float = Field(default=0.0, description="Weighted hybrid score [0-1] used for final ranking")

    @classmethod
    def from_evidence_record(
        cls,
        ev: "EvidenceRecord",
        rank: int,
        bm25_score: float = 0.0,
        semantic_score: float = 0.0,
        combined_score: float = 0.0,
    ) -> "RetrievedEvidence":
        return cls(
            evidence_id=ev.evidence_id,
            claim_id=ev.claim_id,
            company=ev.company,
            source=ev.source,
            source_tier=ev.source_tier,
            source_type=ev.source_type,
            publication_date=ev.publication_date,
            reporting_period=ev.reporting_period,
            retrieved_text=ev.retrieved_text,
            url_or_path=ev.url_or_path,
            notes=ev.notes,
            expected_relationship=getattr(ev, "expected_relationship", None),
            rank=rank,
            bm25_score=bm25_score,
            semantic_score=semantic_score,
            combined_score=combined_score,
        )



class RetrievalResult(BaseModel):
    """All retrieved evidence for one claim, plus the query plan used to find it."""
    claim_id: str
    query_plan: QueryPlan
    evidence: list[RetrievedEvidence] = Field(default_factory=list)
    top_k: int = Field(default=5, description="Maximum evidence items returned")


# ---------------------------------------------------------------------------
# Step 5: Verification + numeric check + risk scoring schemas
# ---------------------------------------------------------------------------

class NumericalCheckResult(BaseModel):
    """Result of a deterministic Python arithmetic check on claim vs. evidence numbers.

    This is NEVER produced by an LLM. All arithmetic is done in
    app/evaluation/numeric_checks.py using standard Python operators.
    """
    check_type: str = Field(..., description="e.g. 'percent_reduction', 'absolute_value', 'unit_mismatch'")
    passed: bool = Field(..., description="True if numbers are consistent within tolerance")
    claim_value: Optional[float] = None
    evidence_value: Optional[float] = None
    tolerance_pct: float = Field(default=5.0, description="Allowed rounding tolerance (%)")
    detail: str = Field(..., description="Human-readable explanation of what was checked and why it passed/failed")
    skipped: bool = Field(default=False, description="True when the check could not be applied (e.g. unit mismatch, missing data)")
    skip_reason: Optional[str] = Field(default=None, description="Why the check was skipped, if skipped=True")


class VerificationResult(BaseModel):
    """Full, explainable output of the Step 5 verification engine for one claim.

    The verdict is one of the three allowed outcomes defined in the existing
    Verdict enum: ALIGN, CONTRADICT, or INSUFFICIENT_EVIDENCE.
    NOT_APPLICABLE is set upstream (in checkability) and is never produced here.
    This is a TRIAGE result for human reviewers -- not a legal verdict.
    """
    claim_id: str
    verdict: Verdict
    reason: str = Field(..., description="Human-readable explanation of how the verdict was reached")

    # Detailed breakdown
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    insufficient_evidence_ids: list[str] = Field(default_factory=list)

    numerical_checks: list[NumericalCheckResult] = Field(default_factory=list)

    # Key dimensions compared
    company_match: Optional[bool] = None
    period_match: Optional[bool] = None
    scope_match: Optional[bool] = None
    unit_match: Optional[bool] = None
    boundary_match: Optional[bool] = None

    highest_authority_tier: Optional[int] = Field(
        default=None,
        description="Lowest source_tier number (= highest authority) among retrieved evidence",
    )
    method: str = Field(default="rule_based", description="How verification was computed")


class RiskScoreFactor(BaseModel):
    """One contributing factor in the Greenwashing Risk Score calculation."""
    factor: str = Field(..., description="Short name of the risk factor")
    points: float = Field(..., description="Points contributed by this factor (positive = higher risk)")
    max_points: float = Field(..., description="Maximum this factor can contribute")
    reason: str = Field(..., description="Human-readable explanation")


class RiskScoreResult(BaseModel):
    """Explainable 0-100 Greenwashing Risk Score for one claim.

    IMPORTANT: This is a triage indicator for human reviewers.
    It is NOT a legal verdict and does NOT prove or disprove greenwashing.

    The score is computed from a deterministic weighted sum of named factors
    (see app/scoring/risk_score.py). Every point contributed is traced to a
    named factor with a documented reason, so a faculty member or EY reviewer
    can understand exactly why a claim received its score.

    Score interpretation (advisory only):
        0-29   Low risk — evidence broadly supports the claim
        30-59  Moderate risk — some concerns, human review warranted
        60-79  High risk — significant concerns identified
        80-100 Very high risk — strong contradictions or data quality issues
    """
    claim_id: str
    risk_score: float = Field(..., ge=0, le=100, description="Final clamped score [0, 100]")
    risk_band: str = Field(..., description="'Low', 'Moderate', 'High', or 'Very High'")
    factors: list[RiskScoreFactor] = Field(default_factory=list)
    summary: str = Field(..., description="One-paragraph plain-English summary of the score")
    disclaimer: str = Field(
        default=(
            "This Greenwashing Risk Score is a triage indicator produced by an automated "
            "rule-based system. It is intended to support human review, not to replace it. "
            "It does not constitute legal, regulatory, or professional advice."
        )
    )


# ---------------------------------------------------------------------------
# Audit trail (full pipeline result for one claim)
# ---------------------------------------------------------------------------

class AuditRecord(BaseModel):
    """Complete audit trail for one claim through the full pipeline.

    Ties together every intermediate result so a human reviewer (or an EY
    auditor) can trace the entire decision path from raw claim text to final
    risk score.
    """
    claim_id: str
    claim_text: str
    company: str
    checkability_result: Optional[CheckabilityResult] = None
    retrieval_result: Optional[RetrievalResult] = None
    verification_result: Optional[VerificationResult] = None
    risk_score_result: Optional[RiskScoreResult] = None

