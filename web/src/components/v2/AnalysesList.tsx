import { useEffect, useState } from "react";
import { getJson, useBackend } from "../../lib/v2api";
import { navigate } from "../../lib/route";
import type { AnalysisListItem } from "../../lib/v2types";
import { Empty, ErrorBox, Loading, fmtTime, riskClass } from "./ui";

export function AnalysesList() {
  const base = useBackend();
  const [items, setItems] = useState<AnalysisListItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setItems(null);
    setErr(null);
    getJson<AnalysisListItem[]>(base, "/v2/analyses", ctl.signal)
      .then(setItems)
      .catch((e) => e.name !== "AbortError" && setErr(e.message));
    return () => ctl.abort();
  }, [base, tick]);

  return (
    <div>
      <h1>Analyses</h1>
      <p className="subtitle">Previous and running analyses, newest first.</p>
      {err && <ErrorBox message={err} onRetry={() => setTick(tick + 1)} />}
      {!items && !err && <Loading />}
      {items && items.length === 0 && (
        <Empty>
          No analyses yet. <a href="#/analyze">Run your first analysis</a>.
        </Empty>
      )}
      {items && items.length > 0 && (
        <div className="v2-table-wrap">
          <table className="clickable">
            <thead>
              <tr>
                <th>Document</th>
                <th>Company</th>
                <th>Status</th>
                <th>Risk</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.analysis_id} onClick={() => navigate(`/analyses/${a.analysis_id}`)}>
                  <td>{a.source_document}</td>
                  <td>{a.company_name ?? "-"}</td>
                  <td>
                    <span className={`chip status-${a.status}`}>{a.status}</span>
                  </td>
                  <td>
                    {a.company_risk_score === null ? "-" : <span className={`riskdot ${riskClass(a.company_risk_score)}`}>{a.company_risk_score.toFixed(0)}</span>}
                  </td>
                  <td>{fmtTime(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
