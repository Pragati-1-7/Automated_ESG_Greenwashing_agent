import { useState } from "react";
import type { AuditRecord } from "../lib/types";
import { SOURCE_TIER_LABELS, VERDICT_COLORS } from "../lib/constants";

const TABS = [
  "Checkability",
  "Evidence",
  "Verification",
  "Numerical checks",
  "Risk score",
  "Audit trail",
] as const;

type Tab = (typeof TABS)[number];

export function ClaimDetail({ record }: { record: AuditRecord }) {
  const [tab, setTab] = useState<Tab>("Checkability");
  const { checkability_result: cr, retrieval_result: rr, verification_result: vr, risk_score_result: rs } =
    record;

  return (
    <div className="claim-detail">
      <h3>Claim detail - {record.claim_id}</h3>
      <p className="claim-text">{record.claim_text}</p>
      <p className="hint">Company: {record.company}</p>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t}
            className={t === tab ? "tab tab-active" : "tab"}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="tab-panel">
        {tab === "Checkability" && (
          <>
            {cr ? (
              <>
                <p>
                  <strong>Claim type:</strong> {cr.claim_type}
                </p>
                <p>
                  <strong>Checkability:</strong> {cr.checkability}
                </p>
                <p>
                  <strong>Completeness score:</strong> {cr.checkability_completeness.toFixed(0)}/100
                </p>
                <p>
                  <strong>Reason:</strong> {cr.reason}
                </p>
                {cr.satisfied_fields.length > 0 && (
                  <p>
                    <strong>Satisfied:</strong>{" "}
                    {cr.satisfied_fields.map((f) => `✓ ${f}`).join(", ")}
                  </p>
                )}
                {cr.missing_fields.length > 0 && (
                  <p>
                    <strong>Missing:</strong> {cr.missing_fields.join(", ")}
                  </p>
                )}
                <details>
                  <summary>All rule results</summary>
                  <ul>
                    {cr.rule_results.map((rule, i) => {
                      const status = rule.passed ? "PASS" : !rule.applicable ? "N/A" : "FAIL";
                      return (
                        <li key={i}>
                          [{status}] <strong>{rule.rule_name}</strong> - {rule.detail}
                        </li>
                      );
                    })}
                  </ul>
                </details>
              </>
            ) : (
              <p>No checkability result available.</p>
            )}
          </>
        )}

        {tab === "Evidence" && (
          <>
            {rr && rr.evidence.length > 0 ? (
              <>
                <p className="hint">
                  Development / synthetic evidence corpus - not real regulatory records.
                </p>
                <details>
                  <summary>Search queries generated</summary>
                  <ul>
                    {rr.query_plan.queries.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </details>
                {rr.evidence.map((ev) => (
                  <div key={ev.evidence_id} className="evidence-item">
                    <p>
                      <strong>
                        [{ev.rank}] {ev.source}
                      </strong>{" "}
                      - {SOURCE_TIER_LABELS[ev.source_tier] ?? `Tier ${ev.source_tier}`}
                    </p>
                    <p>{ev.retrieved_text}</p>
                    <p className="hint">
                      Publication date: {ev.publication_date} | BM25: {ev.bm25_score.toFixed(3)} |
                      Semantic: {ev.semantic_score.toFixed(3)} | Combined:{" "}
                      {ev.combined_score.toFixed(3)}
                    </p>
                    <hr />
                  </div>
                ))}
              </>
            ) : rr ? (
              <p>No evidence retrieved for this claim.</p>
            ) : (
              <p>This claim was not checkable, so no evidence retrieval was run.</p>
            )}
          </>
        )}

        {tab === "Verification" && (
          <>
            {vr ? (
              <>
                <h4 style={{ color: VERDICT_COLORS[vr.verdict] ?? "#374151" }}>{vr.verdict}</h4>
                <p>
                  <strong>Why:</strong> {vr.reason}
                </p>
                <p>Supporting evidence: {vr.supporting_evidence_ids.join(", ") || "none"}</p>
                <p>Contradicting evidence: {vr.contradicting_evidence_ids.join(", ") || "none"}</p>
                <p>
                  Insufficient/inconclusive evidence:{" "}
                  {vr.insufficient_evidence_ids.join(", ") || "none"}
                </p>
                {vr.highest_authority_tier && (
                  <p>Highest-authority source tier used: {vr.highest_authority_tier}</p>
                )}
              </>
            ) : (
              <p>No verification result (claim not checkable).</p>
            )}
          </>
        )}

        {tab === "Numerical checks" && (
          <>
            {vr && vr.numerical_checks.length > 0 ? (
              vr.numerical_checks.map((nc, i) => {
                const status = nc.passed ? "PASS" : nc.skipped ? "SKIPPED" : "MISMATCH";
                return (
                  <div key={i} className="evidence-item">
                    <p>
                      <strong>
                        [{status}] {nc.check_type}
                      </strong>
                    </p>
                    <div className="numeric-grid">
                      <span>Claimed value: {nc.claim_value ?? "-"}</span>
                      <span>Evidence value: {nc.evidence_value ?? "-"}</span>
                      <span>Tolerance: {nc.tolerance_pct}%</span>
                    </div>
                    <p>{nc.detail}</p>
                    <hr />
                  </div>
                );
              })
            ) : (
              <p>No deterministic numerical checks were applicable to this claim.</p>
            )}
          </>
        )}

        {tab === "Risk score" && (
          <>
            {rs ? (
              <>
                <h4>
                  {rs.risk_score.toFixed(0)} / 100 - {rs.risk_band} risk
                </h4>
                <p>{rs.summary}</p>
                {[...rs.factors]
                  .sort((a, b) => b.points - a.points)
                  .map((f, i) => (
                    <p key={i}>
                      +{f.points.toFixed(0)} pts - <strong>{f.factor}</strong>: {f.reason}
                    </p>
                  ))}
                <p className="hint">{rs.disclaimer}</p>
              </>
            ) : (
              <p>No risk score computed (claim not checkable).</p>
            )}
          </>
        )}

        {tab === "Audit trail" && <AuditTrail record={record} />}
      </div>
    </div>
  );
}

function AuditTrail({ record }: { record: AuditRecord }) {
  const { checkability_result: cr, retrieval_result: rr, verification_result: vr, risk_score_result: rs } =
    record;
  const [showRaw, setShowRaw] = useState(false);

  const steps: { title: string; body: React.ReactNode }[] = [
    { title: "1. Source document", body: <span>Company: {record.company}</span> },
    { title: "2. Extracted claim", body: <span>{record.claim_text}</span> },
    {
      title: "3. Checkability decision",
      body: cr ? (
        <span>
          <strong>{cr.checkability}</strong> - {cr.reason}
        </span>
      ) : (
        "Not evaluated."
      ),
    },
    {
      title: "4. Search queries generated",
      body:
        rr && rr.query_plan.queries.length > 0 ? (
          <ul>
            {rr.query_plan.queries.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        ) : (
          "No queries generated (claim not checkable)."
        ),
    },
    {
      title: "5. Evidence retrieved",
      body:
        rr && rr.evidence.length > 0
          ? `${rr.evidence.length} item(s) retrieved from the synthetic evidence corpus.`
          : "No evidence retrieved.",
    },
    {
      title: "6. Evidence ranking",
      body:
        rr && rr.evidence.length > 0 ? (
          <table className="mini-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Evidence ID</th>
                <th>BM25</th>
                <th>Semantic</th>
                <th>Combined</th>
              </tr>
            </thead>
            <tbody>
              {rr.evidence.map((ev) => (
                <tr key={ev.evidence_id}>
                  <td>{ev.rank}</td>
                  <td>{ev.evidence_id}</td>
                  <td>{ev.bm25_score.toFixed(3)}</td>
                  <td>{ev.semantic_score.toFixed(3)}</td>
                  <td>{ev.combined_score.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          "No ranking to show."
        ),
    },
    {
      title: "7. Numerical checks",
      body:
        vr && vr.numerical_checks.length > 0 ? (
          <ul>
            {vr.numerical_checks.map((nc, i) => (
              <li key={i}>
                [{nc.passed ? "PASS" : nc.skipped ? "SKIPPED" : "MISMATCH"}] {nc.check_type}:{" "}
                {nc.detail}
              </li>
            ))}
          </ul>
        ) : (
          "No numerical checks were applicable."
        ),
    },
    {
      title: "8. Verification",
      body: vr ? (
        <span>
          <strong>{vr.verdict}</strong> - {vr.reason}
        </span>
      ) : (
        "Not applicable."
      ),
    },
    {
      title: "9. Risk factors",
      body:
        rs && rs.factors.length > 0 ? (
          <ul>
            {[...rs.factors]
              .sort((a, b) => b.points - a.points)
              .map((f, i) => (
                <li key={i}>
                  +{f.points.toFixed(0)} pts - {f.factor}: {f.reason}
                </li>
              ))}
          </ul>
        ) : (
          "No risk factors (claim not checkable)."
        ),
    },
    {
      title: "10. Final score",
      body: rs ? `${rs.risk_score.toFixed(0)} / 100 - ${rs.risk_band} risk` : "No score computed.",
    },
  ];

  return (
    <div>
      <p className="hint">
        Full step-by-step trace of how this result was produced. Nothing below is invented by the
        frontend - it is the exact backend output for this claim.
      </p>
      {steps.map((s, i) => (
        <div key={i} className="audit-step">
          <strong>{s.title}</strong>
          <div>{s.body}</div>
        </div>
      ))}
      <button className="link-button" onClick={() => setShowRaw((v) => !v)}>
        {showRaw ? "Hide" : "Show"} raw audit record (JSON)
      </button>
      {showRaw && <pre className="raw-json">{JSON.stringify(record, null, 2)}</pre>}
    </div>
  );
}
