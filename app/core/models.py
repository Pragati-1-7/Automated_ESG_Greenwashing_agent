"""v2 data models. Mirrors docs/API_V2_CONTRACT.md exactly."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Label = Literal["ALIGN", "CONTRADICT", "INSUFFICIENT_EVIDENCE", "NOT_CHECKABLE"]
StanceLabel = Literal["support", "contradict", "insufficient"]
CheckType = Literal["point_value", "pct_change", "share", "zero_events", "compliance", "geo",
                    "certificate", "assurance", "other"]

DISCLAIMER = ("This tool provides evidence-based triage and decision support. It does not constitute a "
              "legal determination of greenwashing. Every verdict should be reviewed by a human analyst.")
SYNTHETIC_NOTICE = ("Evidence comes from the mock_sources service, a synthetic stand-in for SEBI BRSR filings, "
                    "CPCB OCEMS data, NGT/SPCB orders, GFW forest alerts, REC registries, assurance statements and "
                    "news. All companies and figures are fictional.")


class Sentence(BaseModel):
    sid: str
    text: str
    page: int
    section: Optional[str] = None


class ParsedNumber(BaseModel):
    value: float
    unit: Optional[str] = None
    raw: str


class Parsed(BaseModel):
    numbers: list[ParsedNumber] = Field(default_factory=list)
    period: Optional[str] = None
    baseline_period: Optional[str] = None
    facility_hint: Optional[str] = None


class Triage(BaseModel):
    is_claim_prob: float
    action: Literal["implemented", "planning", "indeterminate"] = "implemented"
    action_probs: dict[str, float] = Field(default_factory=dict)
    checkable: bool = True
    materiality: float = 0.5
    vagueness: float = 0.0
    metric: Optional[str] = None
    metric_confidence: float = 0.0
    reason: str = ""


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any]
    status: Literal["ok", "empty", "error"]
    latency_ms: int
    result_count: int


class Computation(BaseModel):
    op: str
    expression: str
    inputs: dict[str, float]
    result: float


class Stance(BaseModel):
    label: StanceLabel
    probabilities: dict[str, float]
    confidence: float = 0.0


class Evidence(BaseModel):
    evidence_id: str
    source: str
    tier: int
    title: str
    snippet: str
    endpoint: str
    data: dict[str, Any] = Field(default_factory=dict)
    stance: Optional[Stance] = None


class SubClaim(BaseModel):
    sub_id: str
    text: str
    metric: Optional[str] = None
    check_type: CheckType = "other"
    period: Optional[str] = None
    baseline_period: Optional[str] = None
    claimed_value: Optional[float] = None
    sources_planned: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    computations: list[Computation] = Field(default_factory=list)
    stance: Optional[Stance] = None


class VerdictResult(BaseModel):
    label: Label
    probabilities: dict[str, float]
    confidence: float
    reasoning: str


class RiskComponent(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float
    note: str


class Risk(BaseModel):
    score: float
    band: str
    components: list[RiskComponent]


class ClaimResult(BaseModel):
    claim_id: str
    text: str
    page: int
    section: Optional[str] = None
    triage: Triage
    parsed: Parsed = Field(default_factory=Parsed)
    sub_claims: list[SubClaim] = Field(default_factory=list)
    verdict: Optional[VerdictResult] = None
    risk: Optional[Risk] = None


class CompanyMatch(BaseModel):
    resolved: bool
    company_id: Optional[str] = None
    name: str
    match_score: float
    reason: str


class Summary(BaseModel):
    total_candidates: int
    total_claims: int
    checkable_claims: int
    verdict_counts: dict[str, int]
    company_risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    top_red_flags: list[str] = Field(default_factory=list)


class AgentEvent(BaseModel):
    seq: int
    ts: str
    agent: str
    type: str
    claim_id: Optional[str] = None
    message: str
    data: Optional[dict[str, Any]] = None


class Analysis(BaseModel):
    analysis_id: str
    status: Literal["queued", "running", "done", "error"] = "queued"
    error: Optional[str] = None
    source_document: str
    page_count: Optional[int] = None
    created_at: str
    finished_at: Optional[str] = None
    engines: dict[str, str] = Field(default_factory=dict)
    company: Optional[CompanyMatch] = None
    summary: Optional[Summary] = None
    claims: list[ClaimResult] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    synthetic_notice: str = SYNTHETIC_NOTICE
