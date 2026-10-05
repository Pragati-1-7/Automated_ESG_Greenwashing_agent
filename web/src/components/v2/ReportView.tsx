import { useRef } from "react";
import type { Analysis, ClaimResult, Evidence } from "../../lib/v2types";
import { VerdictPill, riskClass } from "./ui";

// Formatted verification report built from the analysis JSON, plus export:
// PDF (print-ready window), Markdown (server report) and JSON (raw analysis).

const TIER_SHORT: Record<number, string> = {
  1: "Tier 1 · Regulatory filing",
  2: "Tier 2 · Regulator record",
  3: "Tier 3 · Third-party data",
  4: "Tier 4 · Company PR",
  5: "Tier 5 · News",
};

const ACTION_TEXT: Record<string, string> = {
  planning: "Future target or commitment",
  indeterminate: "Vague statement, nothing measurable",
  implemented: "No measurable figure to check",
};

const cleanSnippet = (t: string) => t.replace(/\s*Turnover \(Rs crore\) as filed:[^.]*(\.\d[^.]*)*\./g, "").trim();
const clip = (t: string, n: number) => (t.length <= n ? t : t.slice(0, n - 1).trimEnd() + "...");

function keyEvidence(c: ClaimResult): Evidence | null {
  const want = c.verdict.label === "CONTRADICT" ? "contradict" : c.verdict.label === "ALIGN" ? "support" : null;
  if (!want) return null;
  const hits = c.sub_claims.flatMap((s) => s.evidence).filter((e) => e.stance?.label === want);
  return hits.sort((a, b) => a.tier - b.tier)[0] ?? null;
}

const calcOf = (c: ClaimResult) => c.sub_claims.flatMap((s) => s.computations)[0]?.expression ?? null;

function llmName(l: string | undefined) {
  if (!l) return "the text model";
  if (l.startsWith("groq:")) return `${l.slice(5).replace("openai/", "").toUpperCase()} (via Groq)`;
  return "a built-in template writer that only restates the facts";
}

function slug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function download(name: string, body: string, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function EvidenceBox({ c }: { c: ClaimResult }) {
  const e = keyEvidence(c);
  const calc = calcOf(c);
  if (!e && !calc) return null;
  return (
    <div className="rp-evidence">
      {e && (
        <>
          <span className={`tier tier-${e.tier}`}>{TIER_SHORT[e.tier] ?? `Tier ${e.tier}`}</span>
          <span className="rp-ev-text">{clip(cleanSnippet(e.snippet), 340)}</span>
        </>
      )}
      {calc && (
        <div className="rp-calc">
          Calculation: <code>{calc}</code>
        </div>
      )}
    </div>
  );
}

function ClaimMeta({ c }: { c: ClaimResult }) {
  return (
    <div className="rp-meta">
      <span>Page {c.page}</span>
      <VerdictPill label={c.verdict.label} />
      <span>Confidence {(c.verdict.confidence * 100).toFixed(0)}%</span>
      {c.risk && (
        <span>
          Risk <span className={`riskdot ${riskClass(c.risk.score)}`}>{c.risk.score.toFixed(0)}</span>
        </span>
      )}
    </div>
  );
}

export default function ReportView({ a, markdown }: { a: Analysis; markdown: string | null }) {
  const docRef = useRef<HTMLDivElement>(null);
  const s = a.summary;
  const vc = s?.verdict_counts ?? ({} as Record<string, number>);
  const name = a.company?.name ?? "Unknown company";
  const byId = new Map(a.claims.map((c) => [c.claim_id, c]));
  const flagged = (s?.top_red_flags ?? []).map((id) => byId.get(id)).filter(Boolean).slice(0, 5) as ClaimResult[];
  const flaggedIds = new Set(flagged.map((c) => c.claim_id));
  const sorted = [...a.claims].sort((x, y) => (y.risk?.score ?? 0) - (x.risk?.score ?? 0));
  const group = (l: string) => sorted.filter((c) => c.verdict.label === l);
  const score = s?.company_risk_score ?? null;
  const fileBase = `${slug(name)}_greenwashing_report`;

  const exportPdf = () => {
    const node = docRef.current;
    if (!node) return;
    const styles = Array.from(document.querySelectorAll('style, link[rel="stylesheet"]'))
      .map((el) => el.outerHTML)
      .join("\n");
    const w = window.open("", "_blank");
    if (!w) {
      window.print();
      return;
    }
    w.document.write(
      `<!doctype html><html><head><meta charset="utf-8"><title>${fileBase}</title>${styles}</head>` +
        `<body class="rp-print-body">${node.outerHTML}</body></html>`,
    );
    w.document.close();
    setTimeout(() => {
      w.focus();
      w.print();
    }, 500);
  };

  return (
    <div className="rp-wrap">
      <div className="rp-toolbar">
        <span className="hint tight">Export this report</span>
        <button className="primary-button small" onClick={exportPdf}>
          Export PDF
        </button>
        <button
          className="ghost-button"
          disabled={!markdown}
          onClick={() => markdown && download(`${fileBase}.md`, markdown, "text/markdown")}
        >
          Download Markdown
        </button>
        <button
          className="ghost-button"
          onClick={() => download(`${fileBase}.json`, JSON.stringify(a, null, 2), "application/json")}
        >
          Download JSON
        </button>
      </div>

      <div className="rp-doc" ref={docRef}>
        <header className="rp-head">
          <div className="rp-eyebrow">Greenwashing verification report</div>
          <h1>{name}</h1>
          <div className="rp-sub">
            {a.source_document}
            {a.page_count ? ` · ${a.page_count} pages` : ""} · analysed {a.created_at.slice(0, 16).replace("T", " ")} UTC ·
            ID {a.analysis_id}
          </div>
        </header>

        {s && (
          <section className="rp-glance">
            <div className={`rp-score ${riskClass(score)}`}>
              <div className="rp-score-label">Greenwashing risk score</div>
              <div className="rp-score-num">
                {score !== null ? score.toFixed(0) : "-"}
                <span>/100</span>
              </div>
              <div className="rp-band">{s.risk_band ?? "n/a"} risk</div>
              <div className="rp-bar">
                <div className="rp-bar-fill" style={{ width: `${Math.max(2, Math.min(100, score ?? 0))}%` }} />
                <i style={{ left: "25%" }} />
                <i style={{ left: "50%" }} />
                <i style={{ left: "75%" }} />
              </div>
              <div className="rp-bar-scale">
                <span>Low</span>
                <span>Moderate</span>
                <span>High</span>
                <span>Very high</span>
              </div>
            </div>
            <div className="rp-tiles">
              <div className="rp-tile v-contra">
                <b>{vc.CONTRADICT ?? 0}</b>Contradicted
              </div>
              <div className="rp-tile v-align">
                <b>{vc.ALIGN ?? 0}</b>Confirmed
              </div>
              <div className="rp-tile v-insuf">
                <b>{vc.INSUFFICIENT_EVIDENCE ?? 0}</b>Not enough evidence
              </div>
              <div className="rp-tile v-nc">
                <b>{vc.NOT_CHECKABLE ?? 0}</b>Not checkable
              </div>
              <div className="rp-tiles-note">
                {s.total_claims} claims found in {s.total_candidates} sentences · {s.checkable_claims} checkable
              </div>
            </div>
          </section>
        )}

        {s && (
          <section>
            <h2>Summary</h2>
            <p>
              {name}'s report makes {s.total_claims} ESG claims. {s.checkable_claims} could be checked against external
              records: <b>{vc.CONTRADICT ?? 0} are contradicted</b>, {vc.ALIGN ?? 0} are confirmed and{" "}
              {vc.INSUFFICIENT_EVIDENCE ?? 0} have no reliable record either way. The other {vc.NOT_CHECKABLE ?? 0} are
              future targets or vague statements.
              {score !== null && (
                <>
                  {" "}
                  Overall greenwashing risk is{" "}
                  <b>
                    {score.toFixed(0)}/100 ({s.risk_band})
                  </b>
                  .
                </>
              )}
            </p>
            {a.company && (
              <p className="rp-small">
                Company matched to registry record <b>{a.company.name}</b> ({(a.company.match_score * 100).toFixed(0)}%
                confidence).
              </p>
            )}
          </section>
        )}

        {flagged.length > 0 && (
          <section>
            <h2>Key findings</h2>
            <p className="rp-small">The claims most likely to be greenwashing, worst first.</p>
            {flagged.map((c, i) => (
              <div key={c.claim_id} className={`rp-finding rp-${c.verdict.label.toLowerCase()}`}>
                <div className="rp-num">{i + 1}</div>
                <div className="rp-body">
                  <blockquote>"{c.text}"</blockquote>
                  <ClaimMeta c={c} />
                  <EvidenceBox c={c} />
                </div>
              </div>
            ))}
          </section>
        )}

        <section>
          <h2>All checked claims</h2>
          {(
            [
              ["CONTRADICT", "Contradicted by external records"],
              ["ALIGN", "Confirmed by external records"],
            ] as const
          ).map(([lab, title]) => {
            const cs = group(lab);
            if (!cs.length) return null;
            return (
              <div key={lab}>
                <h3>
                  {title} ({cs.length})
                </h3>
                {cs.map((c) => (
                  <div key={c.claim_id} className="rp-claim">
                    <div className="rp-claim-text">"{c.text}"</div>
                    <ClaimMeta c={c} />
                    {flaggedIds.has(c.claim_id) ? (
                      <div className="rp-small dim">Evidence shown in Key findings.</div>
                    ) : (
                      <EvidenceBox c={c} />
                    )}
                  </div>
                ))}
              </div>
            );
          })}

          {group("INSUFFICIENT_EVIDENCE").length > 0 && (
            <>
              <h3>Not enough evidence to decide ({group("INSUFFICIENT_EVIDENCE").length})</h3>
              <p className="rp-small">No reliable record covers these claims for the stated period, so the system does not guess.</p>
              <ul className="rp-list">
                {group("INSUFFICIENT_EVIDENCE").map((c) => (
                  <li key={c.claim_id}>
                    "{c.text}" <span className="dim">(page {c.page})</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {group("NOT_CHECKABLE").length > 0 && (
            <>
              <h3>Not checkable ({group("NOT_CHECKABLE").length})</h3>
              <p className="rp-small">
                Future targets and vague statements cannot be verified yet. Vague wording still adds to the risk score.
              </p>
              <ul className="rp-list">
                {group("NOT_CHECKABLE").map((c) => (
                  <li key={c.claim_id}>
                    "{c.text}" <span className="dim">(page {c.page})</span>{" "}
                    <span className="chip">{ACTION_TEXT[c.triage.action] ?? c.triage.action}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="rp-method">
          <h2>How this report was produced</h2>
          <ul>
            <li>
              Every judgement is a typed question to the decision engine ({a.engines.decision ?? "Jev"}), answered with a
              probability. Explanations are written by {llmName(a.engines.llm)}.
            </li>
            <li>
              Evidence trust levels: Tier 1 regulatory filing, Tier 2 regulator record, Tier 3 third-party data, Tier 4
              company PR, Tier 5 news. Official records outweigh company PR.
            </li>
            <li>All arithmetic is done by a calculator tool and is shown next to each finding.</li>
            <li>The full step-by-step audit trail is in the Live trace tab and in the Markdown export.</li>
          </ul>
          <p className="rp-small dim">
            {a.synthetic_notice} {a.disclaimer}
          </p>
        </section>
      </div>
    </div>
  );
}
