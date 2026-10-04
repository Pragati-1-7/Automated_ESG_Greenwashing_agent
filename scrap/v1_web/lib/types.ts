// Mirrors the JSON shapes returned by app/api/main.py. Kept loose (not a
// 1:1 generated client) since the backend is the single source of truth --
// this file exists for editor autocomplete, not for validation. The
// frontend never computes a verdict, score, or explanation itself; it only
// renders exactly what these types describe.

export interface RuleCheckResult {
  rule_name: string;
  applicable: boolean;
  passed: boolean;
  detail: string;
}

export interface CheckabilityResult {
  claim_id: string;
  claim_type: string;
  checkability: "CHECKABLE" | "NOT_CHECKABLE";
  reason: string;
  missing_fields: string[];
  satisfied_fields: string[];
  rule_results: RuleCheckResult[];
  checkability_completeness: number;
  method: string;
}

export interface RetrievedEvidence {
  evidence_id: string;
  source: string;
  source_tier: number;
  source_type: string;
  publication_date: string;
  reporting_period: string | null;
  retrieved_text: string;
  rank: number;
  bm25_score: number;
  semantic_score: number;
  combined_score: number;
}

export interface QueryPlan {
  queries: string[];
}

export interface RetrievalResult {
  query_plan: QueryPlan;
  evidence: RetrievedEvidence[];
}

export interface NumericalCheckResult {
  check_type: string;
  passed: boolean;
  claim_value: number | null;
  evidence_value: number | null;
  tolerance_pct: number;
  detail: string;
  skipped: boolean;
  skip_reason: string | null;
}

export type Verdict = "ALIGN" | "CONTRADICT" | "INSUFFICIENT_EVIDENCE" | "NOT_APPLICABLE";

export interface VerificationResult {
  verdict: Verdict;
  reason: string;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  insufficient_evidence_ids: string[];
  numerical_checks: NumericalCheckResult[];
  highest_authority_tier: number | null;
}

export interface RiskScoreFactor {
  factor: string;
  points: number;
  max_points: number;
  reason: string;
}

export interface RiskScoreResult {
  risk_score: number;
  risk_band: string;
  factors: RiskScoreFactor[];
  summary: string;
  disclaimer: string;
}

export interface AuditRecord {
  claim_id: string;
  claim_text: string;
  company: string;
  checkability_result: CheckabilityResult | null;
  retrieval_result: RetrievalResult | null;
  verification_result: VerificationResult | null;
  risk_score_result: RiskScoreResult | null;
}

export interface Summary {
  total_claims: number;
  checkable_claims: number;
  not_checkable_claims: number;
  align_count: number;
  contradict_count: number;
  insufficient_evidence_count: number;
  average_risk_score: number | null;
  claims_scored: number;
}

export interface AnalyzeResult {
  status: "ok" | "no_claims";
  source_document: string;
  company: string;
  page_count: number | null;
  message?: string;
  extraction_errors: string[];
  summary: Summary;
  audit_records: AuditRecord[];
  synthetic_evidence_notice: string;
  disclaimer: string;
}
