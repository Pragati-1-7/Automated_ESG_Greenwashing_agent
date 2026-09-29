import { useState } from "react";
import type { AuditRecord } from "../lib/types";
import { VERDICT_COLORS, VERDICT_BG } from "../lib/constants";
import { ClaimDetail } from "./ClaimDetail";

function VerdictBadge({ verdict }: { verdict: string }) {
  const color = VERDICT_COLORS[verdict] ?? "#6b7280";
  const bg = VERDICT_BG[verdict] ?? "#eef0f2";
  return (
    <span className="badge" style={{ color, backgroundColor: bg }}>
      {verdict}
    </span>
  );
}

export function ClaimsTable({ records }: { records: AuditRecord[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(records[0]?.claim_id ?? null);

  if (records.length === 0) {
    return <p className="hint">No claims to display.</p>;
  }

  const selected = records.find((r) => r.claim_id === selectedId) ?? records[0];

  return (
    <section>
      <h2>Claim analysis</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Claim ID</th>
              <th>Claim</th>
              <th>Checkability</th>
              <th>Verification</th>
              <th>Risk score</th>
              <th>Risk band</th>
            </tr>
          </thead>
          <tbody>
            {records.map((r) => {
              const cr = r.checkability_result;
              const vr = r.verification_result;
              const rs = r.risk_score_result;
              const truncated =
                r.claim_text.length > 90 ? r.claim_text.slice(0, 90) + "..." : r.claim_text;
              return (
                <tr
                  key={r.claim_id}
                  className={r.claim_id === selected.claim_id ? "row-selected" : ""}
                  onClick={() => setSelectedId(r.claim_id)}
                >
                  <td>{r.claim_id}</td>
                  <td>{truncated}</td>
                  <td>{cr?.checkability ?? "-"}</td>
                  <td>{vr ? <VerdictBadge verdict={vr.verdict} /> : "-"}</td>
                  <td>{rs?.risk_score ?? "-"}</td>
                  <td>{rs?.risk_band ?? "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="claim-select">
        <label htmlFor="claim-picker">Select a claim to inspect in detail</label>
        <select
          id="claim-picker"
          value={selected.claim_id}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {records.map((r) => (
            <option key={r.claim_id} value={r.claim_id}>
              {r.claim_id}
            </option>
          ))}
        </select>
      </div>

      <ClaimDetail record={selected} />
    </section>
  );
}
