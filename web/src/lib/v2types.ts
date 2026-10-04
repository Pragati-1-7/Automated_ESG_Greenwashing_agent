// Copied from docs/API_V2_CONTRACT.md (only `export` added). Do not edit by hand.

export type Label = "ALIGN" | "CONTRADICT" | "INSUFFICIENT_EVIDENCE" | "NOT_CHECKABLE";

export interface DemoReport { key: string; title: string; company: string; filename: string; pages: number; profile: string; }

export interface AnalysisListItem { analysis_id: string; status: string; source_document: string; company_name: string | null;
  created_at: string; company_risk_score: number | null; }

export interface Analysis {
  analysis_id: string;
  status: "queued" | "running" | "done" | "error";
  error: string | null;
  source_document: string;
  page_count: number | null;
  created_at: string; finished_at: string | null;
  engines: Record<string, string>;          // decision, decision_mode, llm, orchestrator
  company: { resolved: boolean; company_id: string | null; name: string; match_score: number; reason: string } | null;
  summary: {
    total_candidates: number;       // sentences screened
    total_claims: number;
    checkable_claims: number;
    verdict_counts: Record<Label, number>;
    company_risk_score: number | null;   // 0-100
    risk_band: "Low" | "Moderate" | "High" | "Very High" | null;
    top_red_flags: string[];              // claim_ids, worst first
  } | null;
  claims: ClaimResult[];
  disclaimer: string;
  synthetic_notice: string;
}

export interface ClaimResult {
  claim_id: string; text: string; page: number; section: string | null;
  triage: {
    is_claim_prob: number;
    action: "implemented" | "planning" | "indeterminate";   // A3CG
    action_probs: Record<string, number>;
    checkable: boolean;
    materiality: number;      // 0-1
    vagueness: number;        // 0-1
    metric: string | null;    // canonical metric key, see data_gen/spec.py METRICS
    metric_confidence: number;
    reason: string;
  };
  parsed: { numbers: {value: number; unit: string | null; raw: string}[]; period: string | null;
            baseline_period: string | null; facility_hint: string | null };
  sub_claims: SubClaim[];
  verdict: { label: Label; probabilities: Record<string, number>; confidence: number; reasoning: string };
  risk: { score: number; band: string; components: {name: string; value: number; weight: number; contribution: number; note: string}[] } | null;
}

export interface SubClaim {
  sub_id: string; text: string; metric: string | null;
  check_type: "point_value" | "pct_change" | "share" | "zero_events" | "compliance" | "geo" | "certificate" | "assurance" | "other";
  period: string | null; baseline_period: string | null; claimed_value: number | null;
  sources_planned: { source: string; probability: number; selected?: boolean }[];
  tool_calls: { tool: string; args: Record<string, unknown>; status: "ok" | "empty" | "error"; latency_ms: number; result_count: number }[];
  evidence: Evidence[];
  computations: { op: string; expression: string; inputs: Record<string, number>; result: number }[];
  stance: { label: "support" | "contradict" | "insufficient"; probabilities: Record<string, number>; confidence: number } | null;
}

export interface Evidence {
  evidence_id: string; source: string; tier: number; title: string; snippet: string;
  endpoint: string;            // mock_sources path that returned it
  data: Record<string, unknown>;
  stance: { label: "support" | "contradict" | "insufficient"; probabilities: Record<string, number> } | null;
}

export interface AgentEvent {
  seq: number; ts: string;
  agent: "ingest" | "resolver" | "extractor" | "triage" | "decomposer" | "router" | "investigator" | "calculator" | "judge" | "verdict" | "risk" | "reporter" | "system";
  type: "start" | "tool_call" | "tool_result" | "decision" | "verdict" | "info" | "error" | "done";
  claim_id: string | null;
  message: string;
  data: Record<string, unknown> | null;
}

export interface BenchmarkReport {
  created_at: string; split: string; n_cases: number;
  overall: { accuracy: number; macro_f1: number; coverage: number; citation_precision: number };
  per_label: Record<Label, { precision: number; recall: number; f1: number; support: number }>;
  per_gw_type: Record<string, { n: number; accuracy: number }>;
  confusion: { labels: Label[]; matrix: number[][] };
  ablations: { name: string; accuracy: number; macro_f1: number; coverage?: number }[];
  all_cases?: { n: number; accuracy: number; macro_f1: number; coverage: number; citation_precision: number };
  engine?: { decision: string; jev_calls?: number; cache_hits?: number; seconds?: number };
  pdf_eval?: Record<string, PdfEvalRow[]>;
}

export interface PdfEvalRow {
  report: string; planted_claims: number; extracted: number; correct: number;
  company_risk_score: number | null; risk_band: string | null;
  other_claims_verdicts: Record<string, number>;
}

export interface VerifyResponse { company: Analysis["company"]; claim: ClaimResult; events: AgentEvent[]; }

export interface Health { status: string; decision_engine: string; llm: string; sources: string; }
export interface SourcesOverview { tables: { name: string; rows: number; tier: number | null; description: string }[]; }
export interface SourceRows { table: string; total: number; rows: Record<string, unknown>[]; }
