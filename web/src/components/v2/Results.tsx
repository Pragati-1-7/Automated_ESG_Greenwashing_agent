import { Fragment, useMemo, useState } from "react";
import type { Analysis, ClaimResult, Label } from "../../lib/v2types";
import { Empty, VerdictPill, pct, riskClass } from "./ui";

const LABELS: Label[] = ["ALIGN", "CONTRADICT", "INSUFFICIENT_EVIDENCE", "NOT_CHECKABLE"];

export function RiskGauge({ score, band }: { score: number | null; band: string | null }) {
  return (
    <div className="gauge">
      <div className="gauge-head">
        <span className={`gauge-score ${riskClass(score)}`}>{score === null ? "-" : score.toFixed(0)}</span>
        <span className="gauge-of">/ 100</span>
        <span className={`gauge-band ${riskClass(score)}`}>{band ?? "n/a"}</span>
      </div>
      <div className="gauge-track">
        <i className="seg r-l" />
        <i className="seg r-m" />
        <i className="seg r-h" />
        <i className="seg r-vh" />
        {score !== null && <span className="gauge-marker" style={{ left: `${Math.min(100, Math.max(0, score))}%` }} />}
      </div>
      <div className="gauge-scale">
        <span>0 Low</span>
        <span>25 Moderate</span>
        <span>50 High</span>
        <span>75 Very High</span>
      </div>
    </div>
  );
}

export function Summary({ a, onClaim }: { a: Analysis; onClaim: (id: string) => void }) {
  const s = a.summary;
  return (
    <div>
      <div className="grid-2">
        <div className="panel">
          <h4 className="tight">Company</h4>
          {a.company ? (
            <>
              <div className="big-name">{a.company.name}</div>
              <p>
                <span className={`chip ${a.company.resolved ? "chip-ok" : "chip-warn"}`}>
                  {a.company.resolved ? "Resolved" : "Not resolved"}
                </span>{" "}
                {a.company.company_id && <span className="chip">{a.company.company_id}</span>}
              </p>
              <p className="hint">Match score {a.company.match_score.toFixed(2)}</p>
              <p className="small">{a.company.reason}</p>
            </>
          ) : (
            <Empty>Company not resolved yet.</Empty>
          )}
        </div>
        <div className="panel">
          <h4 className="tight">Engines</h4>
          <dl className="kv">
            {Object.entries(a.engines ?? {}).map(([k, v]) => (
              <Fragment key={k}>
                <dt>{k.replace(/_/g, " ")}</dt>
                <dd>{String(v)}</dd>
              </Fragment>
            ))}
            <dt>Document</dt>
            <dd>{a.source_document}</dd>
            <dt>Pages</dt>
            <dd>{a.page_count ?? "-"}</dd>
          </dl>
        </div>
      </div>

      {s && (
        <>
          <div className="kpi-row">
            <div className="kpi-card">
              <div className="kpi-value">{s.total_candidates}</div>
              <div className="kpi-label">Sentences screened</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-value">{s.total_claims}</div>
              <div className="kpi-label">Claims</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-value">{s.checkable_claims}</div>
              <div className="kpi-label">Checkable</div>
            </div>
            <div className="kpi-card kpi-pills">
              {LABELS.map((l) => (
                <VerdictPill key={l} label={l} count={s.verdict_counts[l] ?? 0} />
              ))}
              <div className="kpi-label">Verdicts</div>
            </div>
          </div>

          <h3>Top red flags</h3>
          {s.top_red_flags.length === 0 ? (
            <Empty>No red flags raised.</Empty>
          ) : (
            <ol className="flags">
              {s.top_red_flags.map((id) => {
                const c = a.claims.find((x) => x.claim_id === id);
                return (
                  <li key={id} onClick={() => onClaim(id)}>
                    <span className="chip">{id}</span>{" "}
                    {c ? (
                      <>
                        <VerdictPill label={c.verdict.label} /> <span className="flag-text">{c.text}</span>
                        {c.risk && <span className={`riskdot ${riskClass(c.risk.score)}`}>{c.risk.score.toFixed(0)}</span>}
                      </>
                    ) : null}
                  </li>
                );
              })}
            </ol>
          )}
        </>
      )}
    </div>
  );
}

type SortKey = "risk" | "verdict" | "page";
const VORDER: Record<string, number> = { CONTRADICT: 0, INSUFFICIENT_EVIDENCE: 1, ALIGN: 2, NOT_CHECKABLE: 3 };

export function ClaimsTable({
  claims,
  selected,
  onSelect,
}: {
  claims: ClaimResult[];
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const [sort, setSort] = useState<SortKey>("risk");
  const [dir, setDir] = useState<1 | -1>(-1);
  const [filter, setFilter] = useState<string>("all");

  const rows = useMemo(() => {
    const f = filter === "all" ? claims : claims.filter((c) => c.verdict.label === filter);
    const val = (c: ClaimResult) =>
      sort === "risk" ? (c.risk?.score ?? -1) : sort === "page" ? c.page : (VORDER[c.verdict.label] ?? 9);
    return [...f].sort((a, b) => (val(a) - val(b)) * dir);
  }, [claims, sort, dir, filter]);

  const th = (k: SortKey, label: string) => (
    <th className="sortable" onClick={() => (sort === k ? setDir(dir === 1 ? -1 : 1) : (setSort(k), setDir(k === "risk" ? -1 : 1)))}>
      {label} {sort === k ? (dir === 1 ? "▲" : "▼") : ""}
    </th>
  );

  return (
    <div>
      <div className="row-gap between">
        <h3 className="tight">Claims ({rows.length}{rows.length !== claims.length ? ` of ${claims.length}` : ""})</h3>
        <div className="filter-pills">
          <button className={`fp ${filter === "all" ? "on" : ""}`} onClick={() => setFilter("all")}>
            All
          </button>
          {LABELS.map((l) => (
            <button key={l} className={`fp ${filter === l ? "on" : ""}`} onClick={() => setFilter(l)}>
              <VerdictPill label={l} />
            </button>
          ))}
        </div>
      </div>
      {claims.length === 0 ? (
        <Empty>No claims extracted yet.</Empty>
      ) : (
        <div className="v2-table-wrap">
          <table className="clickable claims">
            <thead>
              <tr>
                <th>ID</th>
                {th("page", "Page")}
                <th>Claim</th>
                <th>Triage</th>
                <th>Metric</th>
                {th("verdict", "Verdict")}
                <th>Conf.</th>
                {th("risk", "Risk")}
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.claim_id} className={selected === c.claim_id ? "row-selected" : ""} onClick={() => onSelect(c.claim_id)}>
                  <td>
                    <span className="chip">{c.claim_id}</span>
                  </td>
                  <td>{c.page}</td>
                  <td className="claim-cell" title={c.text}>
                    {c.text.length > 110 ? c.text.slice(0, 107) + "..." : c.text}
                  </td>
                  <td>
                    <span className={`chip act-${c.triage.action}`}>{c.triage.action}</span>
                  </td>
                  <td className="mono">{c.triage.metric ?? "-"}</td>
                  <td>
                    <VerdictPill label={c.verdict.label} />
                  </td>
                  <td>{pct(c.verdict.confidence)}</td>
                  <td>{c.risk ? <span className={`riskdot ${riskClass(c.risk.score)}`}>{c.risk.score.toFixed(0)}</span> : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function EngineChips({ engines }: { engines: Record<string, string> | undefined }) {
  const e = engines ?? {};
  const items: [string, string | undefined][] = [
    ["decision engine", e.decision],
    ["llm", e.llm],
    ["orchestrator", e.orchestrator],
  ];
  return (
    <span className="engine-chips">
      {items.map(([k, v]) =>
        v ? (
          <span className="chip engine-chip" key={k}>
            {k} <b>{v}</b>
          </span>
        ) : null,
      )}
    </span>
  );
}
