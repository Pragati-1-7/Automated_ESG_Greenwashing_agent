import type { Summary } from "../lib/types";

function KpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="kpi-card">
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  );
}

export function ExecutiveSummary({ summary }: { summary: Summary }) {
  return (
    <section>
      <h2>Executive summary</h2>
      <div className="kpi-row">
        <KpiCard label="Total claims" value={summary.total_claims} />
        <KpiCard label="Checkable" value={summary.checkable_claims} />
        <KpiCard label="Not checkable" value={summary.not_checkable_claims} />
        <KpiCard label="Aligned" value={summary.align_count} />
        <KpiCard label="Contradicted" value={summary.contradict_count} />
        <KpiCard label="Insufficient evidence" value={summary.insufficient_evidence_count} />
      </div>
      {summary.average_risk_score !== null && (
        <div className="kpi-card kpi-wide">
          <div className="kpi-value">{summary.average_risk_score.toFixed(1)} / 100</div>
          <div className="kpi-label">Average greenwashing risk score (checkable claims)</div>
          <p className="hint">
            The risk score is a rule-based triage indicator used to prioritize claims for human
            review. It is not a probability of greenwashing.
          </p>
        </div>
      )}
    </section>
  );
}
