"""
schemas.py

Pydantic data models for the ESG Greenwashing Detection & Verification Agent.

WHY THIS FILE EXISTS (Step 1):
We need a single, shared, strongly-typed definition of what a "claim" and
a piece of "evidence" look like, so that:
  1. Our dataset files (data/claims/claims.json, data/evidence/evidence.json)
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

from pydantic import BaseModel, Field, field_validator


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
    expected_verdict: Verdict = Field(
        ..., description="The verdict our system SHOULD reach; used for evaluation, not shown to the model."
    )

    source_document: str = Field(..., description="Synthetic source document filename this claim is drawn from")
    page_number: Optional[int] = Field(default=None, ge=1)

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


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

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
