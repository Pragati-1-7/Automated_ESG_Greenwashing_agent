import type { ClaimResult, Evidence, SubClaim } from "../../lib/v2types";
import { Json, ProbBars, TIER_LABELS, VerdictPill, fmtNum, pct, riskClass } from "./ui";

function Bar({ v, label }: { v: number; label: string }) {
  return (
    <div className="probrow">
      <span className="probname">{label}</span>
      <span className="probtrack">
        <span className="probfill accent" style={{ width: `${Math.max(0, Math.min(1, v)) * 100}%` }} />
      </span>
      <span className="probval">{pct(v, 0)}</span>
    </div>
  );
}

function EvidenceCard({ e }: { e: Evidence }) {
  const rel = typeof e.data?.relevance === "number" ? (e.data.relevance as number) : null;
  const off = rel !== null && rel < 0.5;
  return (
    <div className={`evcard ${off ? "evcard-muted" : ""}`}>
      <div className="ev-head">
        <span className={`tier tier-${e.tier}`}>{TIER_LABELS[e.tier] ?? `Tier ${e.tier}`}</span>
        <span className="chip">{e.source}</span>
        {rel !== null && <span className={`chip relevance ${off ? "rel-low" : "rel-ok"}`}>relevance {rel.toFixed(2)}</span>}
        {e.stance && <VerdictPill label={e.stance.label} />}
      </div>
      {off && <div className="offtopic">off-topic: excluded from verdict</div>}
      <div className="ev-title">{e.title}</div>
      <p className="ev-snip">{e.snippet}</p>
      <div className="ev-end mono">{e.endpoint}</div>
      {e.stance && <ProbBars probs={e.stance.probabilities} highlight={e.stance.label} />}
      <Json data={e.data} label="raw data" />
    </div>
  );
}

function SubClaimView({ s }: { s: SubClaim }) {
  return (
    <div className="subclaim">
      <div className="sub-head">
        <span className="chip">{s.sub_id}</span>
        <span className="chip chip-type">{s.check_type}</span>
        {s.metric && <span className="chip mono">{s.metric}</span>}
        {s.stance && <VerdictPill label={s.stance.label} />}
        {s.stance && <span className="hint">conf {pct(s.stance.confidence)}</span>}
      </div>
      <p className="sub-text">{s.text}</p>
      <dl className="kv inline">
        <dt>Period</dt>
        <dd>{s.period ?? "-"}</dd>
        <dt>Baseline</dt>
        <dd>{s.baseline_period ?? "-"}</dd>
        <dt>Claimed value</dt>
        <dd>{s.claimed_value === null ? "-" : fmtNum(s.claimed_value)}</dd>
      </dl>

      {s.sources_planned.length > 0 && (
        <>
          <h5>Sources planned</h5>
          <div className="probbars">
            {s.sources_planned.map((p) => (
              <Bar key={p.source} v={p.probability} label={`${p.source}${p.selected === false ? " (skipped)" : ""}`} />
            ))}
          </div>
        </>
      )}

      {s.tool_calls.length > 0 && (
        <>
          <h5>Tool calls</h5>
          <div className="v2-table-wrap">
            <table className="dense">
              <thead>
                <tr>
                  <th>Tool</th>
                  <th>Args</th>
                  <th>Status</th>
                  <th>Latency</th>
                  <th>Results</th>
                </tr>
              </thead>
              <tbody>
                {s.tool_calls.map((t, i) => (
                  <tr key={i}>
                    <td className="mono">{t.tool}</td>
                    <td className="mono small" title={JSON.stringify(t.args)}>
                      {JSON.stringify(t.args)}
                    </td>
                    <td>
                      <span className={`chip call-${t.status}`}>{t.status}</span>
                    </td>
                    <td>{t.latency_ms} ms</td>
                    <td>{t.result_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {s.computations.length > 0 && (
        <>
          <h5>Computations</h5>
          <ul className="comps">
            {s.computations.map((c, i) => (
              <li key={i}>
                <span className="chip">{c.op}</span> <code>{c.expression}</code> = <b>{fmtNum(c.result)}</b>
              </li>
            ))}
          </ul>
        </>
      )}

      {s.evidence.length > 0 && (
        <>
          <h5>Evidence ({s.evidence.length})</h5>
          {s.evidence.map((e) => (
            <EvidenceCard key={e.evidence_id} e={e} />
          ))}
        </>
      )}
    </div>
  );
}

export function ClaimDetail({ claim }: { claim: ClaimResult }) {
  const t = claim.triage;
  const v = claim.verdict;
  return (
    <div className="claim-detail">
          <blockquote className="claim-quote">{claim.text}</blockquote>
          <p className="hint">
            {claim.page > 0 ? `Page ${claim.page}` : "Single claim"}
            {claim.section ? ` · ${claim.section}` : ""}
            {claim.parsed.period ? ` · period ${claim.parsed.period}` : ""}
            {claim.parsed.baseline_period ? ` · baseline ${claim.parsed.baseline_period}` : ""}
            {claim.parsed.facility_hint ? ` · facility ${claim.parsed.facility_hint}` : ""}
          </p>
          {claim.parsed.numbers.length > 0 && (
            <p>
              {claim.parsed.numbers.map((n, i) => (
                <span className="chip" key={i}>
                  {n.raw}
                </span>
              ))}
            </p>
          )}

          <h4>Triage</h4>
          <div className="panel flat">
            <dl className="kv inline">
              <dt>Is a claim</dt>
              <dd>{pct(t.is_claim_prob)}</dd>
              <dt>Action</dt>
              <dd>
                <span className={`chip act-${t.action}`}>{t.action}</span>
              </dd>
              <dt>Checkable</dt>
              <dd>{t.checkable ? "yes" : "no"}</dd>
              <dt>Metric</dt>
              <dd className="mono">
                {t.metric ?? "-"} <span className="hint">({pct(t.metric_confidence)})</span>
              </dd>
            </dl>
            <div className="probbars">
              <Bar v={t.materiality} label="materiality" />
              <Bar v={t.vagueness} label="vagueness" />
            </div>
            <h5>Action probabilities</h5>
            <div className="probbars">
              {Object.entries(t.action_probs).map(([k, p]) => (
                <Bar key={k} v={p} label={k} />
              ))}
            </div>
            <p className="small">{t.reason}</p>
          </div>

          <h4>Sub-claims ({claim.sub_claims.length})</h4>
          {claim.sub_claims.length === 0 && <p className="hint">No sub-claims (claim was not decomposed).</p>}
          <div className="tree">
            {claim.sub_claims.map((s) => (
              <SubClaimView key={s.sub_id} s={s} />
            ))}
          </div>

          <h4>Final verdict</h4>
          <div className={`verdict-box vb-${v.label}`}>
            <div className="row-gap between">
              <VerdictPill label={v.label} />
              <span>Confidence {pct(v.confidence, 1)}</span>
            </div>
            <ProbBars probs={v.probabilities} highlight={v.label} />
            <p className="reasoning">{v.reasoning}</p>
          </div>

          <h4>Risk</h4>
          {claim.risk ? (
            <>
              <p>
                Score <span className={`riskdot ${riskClass(claim.risk.score)}`}>{claim.risk.score.toFixed(0)}</span> · {claim.risk.band}
              </p>
              <div className="v2-table-wrap">
                <table className="dense">
                  <thead>
                    <tr>
                      <th>Component</th>
                      <th>Value</th>
                      <th>Weight</th>
                      <th>Contribution</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {claim.risk.components.map((c) => (
                      <tr key={c.name}>
                        <td>{c.name}</td>
                        <td>{c.value.toFixed(2)}</td>
                        <td>{c.weight.toFixed(2)}</td>
                        <td>{c.contribution.toFixed(2)}</td>
                        <td className="small">{c.note}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="hint">No risk score (claim not scored).</p>
          )}
    </div>
  );
}

export function ClaimDrawer({ claim, onClose }: { claim: ClaimResult; onClose: () => void }) {
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" aria-label="Claim detail">
        <div className="drawer-head">
          <div>
            <span className="chip">{claim.claim_id}</span> <VerdictPill label={claim.verdict.label} />
          </div>
          <button className="ghost-button" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="drawer-body">
          <ClaimDetail claim={claim} />
        </div>
      </aside>
    </>
  );
}
