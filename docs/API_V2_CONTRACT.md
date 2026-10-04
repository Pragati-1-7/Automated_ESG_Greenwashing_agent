# API v2 contract (backend <-> React)

Base URL: `http://127.0.0.1:8000`. All JSON. The frontend computes nothing; it renders these shapes.

## Endpoints

| Method | Path | Returns |
|---|---|---|
| GET | `/health` | `{status:"ok", decision_engine:"jev"|"offline", llm:"mock"|"groq:<model>", sources:"up"|"down"}` |
| GET | `/v2/demo-reports` | `DemoReport[]` |
| GET | `/v2/demo-reports/{key}/pdf` | the PDF file (application/pdf) |
| POST | `/v2/analyses` | multipart: `file` (PDF) **or** form field `demo_report=<key>`; optional `max_claims` (int, default 40). Returns `{analysis_id, status:"queued"}` (HTTP 202) |
| GET | `/v2/analyses` | `AnalysisListItem[]` newest first |
| GET | `/v2/analyses/{id}` | `Analysis` (partial while running, complete when `status=="done"`) |
| GET | `/v2/analyses/{id}/events` | **Server-Sent Events**. Each `event: agent_event` has `data: AgentEvent` JSON. Replays all past events first, then live ones. Ends with `event: done` (`data: {"status":"done"|"error"}`) |
| GET | `/v2/analyses/{id}/report` | `{markdown: string}` technical summary + audit trail |
| GET | `/v2/sources/overview` | `{tables: [{name, rows, tier, description}]}` |
| GET | `/v2/sources/{table}?limit=50&offset=0&company_id=` | `{table, total, rows: object[]}` |
| GET | `/v2/benchmark/latest` | `BenchmarkReport` or 404 |
| POST | `/v2/verify-claim` | JSON `{claim, company, fy?}` -> `{company: CompanyMatch, claim: ClaimResult, events: AgentEvent[]}` (one sentence, same agents) |

## Types (TypeScript)

```ts
type Label = "ALIGN" | "CONTRADICT" | "INSUFFICIENT_EVIDENCE" | "NOT_CHECKABLE";

interface DemoReport { key: string; title: string; company: string; filename: string; pages: number; profile: string; }

interface AnalysisListItem { analysis_id: string; status: string; source_document: string; company_name: string | null;
  created_at: string; company_risk_score: number | null; }

interface Analysis {
  analysis_id: string;
  status: "queued" | "running" | "done" | "error";
  error: string | null;
  source_document: string;
  page_count: number | null;
  created_at: string; finished_at: string | null;
  engines: Record<string, string>;   // {decision:"TypeSafe jev-1.13.0", decision_mode:"live", llm:"mock-deterministic", orchestrator:"LangGraph"}
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

interface ClaimResult {
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

interface SubClaim {
  sub_id: string; text: string; metric: string | null;
  check_type: "point_value" | "pct_change" | "share" | "zero_events" | "compliance" | "geo" | "certificate" | "assurance" | "other";
  period: string | null; baseline_period: string | null; claimed_value: number | null;
  sources_planned: { source: string; probability: number }[];
  tool_calls: { tool: string; args: Record<string, unknown>; status: "ok" | "empty" | "error"; latency_ms: number; result_count: number }[];
  evidence: Evidence[];
  computations: { op: string; expression: string; inputs: Record<string, number>; result: number }[];
  stance: { label: "support" | "contradict" | "insufficient"; probabilities: Record<string, number>; confidence: number } | null;
}

interface Evidence {
  evidence_id: string; source: string; tier: number; title: string; snippet: string;
  endpoint: string;            // mock_sources path that returned it
  data: Record<string, unknown>;
  stance: { label: "support" | "contradict" | "insufficient"; probabilities: Record<string, number> } | null;
}

interface AgentEvent {
  seq: number; ts: string;
  agent: "ingest" | "resolver" | "extractor" | "triage" | "decomposer" | "router" | "investigator" | "calculator" | "judge" | "verdict" | "risk" | "reporter" | "system";
  type: "start" | "tool_call" | "tool_result" | "decision" | "verdict" | "info" | "error" | "done";
  claim_id: string | null;
  message: string;
  data: Record<string, unknown> | null;
}

interface BenchmarkReport {
  created_at: string; split: string; n_cases: number;
  overall: { accuracy: number; macro_f1: number; coverage: number; citation_precision: number };
  per_label: Record<Label, { precision: number; recall: number; f1: number; support: number }>;
  per_gw_type: Record<string, { n: number; accuracy: number }>;
  confusion: { labels: Label[]; matrix: number[][] };
  ablations: { name: string; accuracy: number; macro_f1: number }[];
}
```
