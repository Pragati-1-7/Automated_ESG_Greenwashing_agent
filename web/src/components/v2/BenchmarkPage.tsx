import { useEffect, useState } from "react";
import { HttpError, getJson, useBackend } from "../../lib/v2api";
import type { BenchmarkReport, Label } from "../../lib/v2types";
import type { PdfEvalRow } from "../../lib/v2types";
import { Empty, ErrorBox, Loading, VerdictPill, fmtTime, pct } from "./ui";

export function BenchmarkPage() {
  const base = useBackend();
  const [r, setR] = useState<BenchmarkReport | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setR(null);
    setErr(null);
    setMissing(false);
    getJson<BenchmarkReport>(base, "/v2/benchmark/latest", ctl.signal)
      .then(setR)
      .catch((e) => {
        if (e.name === "AbortError") return;
        if (e instanceof HttpError && e.status === 404) setMissing(true);
        else setErr(e.message);
      });
    return () => ctl.abort();
  }, [base, tick]);

  return (
    <div>
      <h1>Benchmark</h1>
      {err && <ErrorBox message={err} onRetry={() => setTick(tick + 1)} />}
      {!r && !err && !missing && <Loading />}
      {missing && (
        <Empty>
          The benchmark has not been run yet. Run the benchmark script on the backend, then{" "}
          <button className="link-button" onClick={() => setTick(tick + 1)}>
            reload
          </button>
          .
        </Empty>
      )}
      {r && <BenchmarkView r={r} />}
    </div>
  );
}

function BenchmarkView({ r }: { r: BenchmarkReport }) {
  const tiles: [string, number][] = [
    ["Accuracy", r.overall.accuracy],
    ["Macro F1", r.overall.macro_f1],
    ["Coverage", r.overall.coverage],
    ["Citation precision", r.overall.citation_precision],
  ];
  const labels = r.confusion.labels;
  const rowMax = r.confusion.matrix.map((row) => Math.max(1, ...row));
  return (
    <>
      <p className="subtitle">
        Split <b>{r.split}</b> · {r.n_cases} cases · run {fmtTime(r.created_at)}
        {r.engine && (
          <>
            {" "}· engine <b>{r.engine.decision}</b>
            {r.engine.seconds !== undefined && <> · {r.engine.seconds}s</>}
            {r.engine.cache_hits !== undefined && <> · {r.engine.cache_hits} cache hits</>}
          </>
        )}
      </p>
      {r.all_cases && (
        <p className="hint">
          All {r.all_cases.n} cases: accuracy {pct(r.all_cases.accuracy, 1)}, macro F1 {pct(r.all_cases.macro_f1, 1)}, coverage{" "}
          {pct(r.all_cases.coverage, 1)}, citation precision {pct(r.all_cases.citation_precision, 1)}.
        </p>
      )}
      <div className="kpi-row">
        {tiles.map(([k, v]) => (
          <div className="kpi-card" key={k}>
            <div className="kpi-value">{pct(v, 1)}</div>
            <div className="kpi-label">{k}</div>
          </div>
        ))}
      </div>

      <h2>Per-label metrics</h2>
      <div className="v2-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Label</th>
              <th>Precision</th>
              <th>Recall</th>
              <th>F1</th>
              <th>Support</th>
            </tr>
          </thead>
          <tbody>
            {(Object.keys(r.per_label) as Label[]).map((l) => (
              <tr key={l}>
                <td>
                  <VerdictPill label={l} />
                </td>
                <td>{r.per_label[l].precision.toFixed(3)}</td>
                <td>{r.per_label[l].recall.toFixed(3)}</td>
                <td>{r.per_label[l].f1.toFixed(3)}</td>
                <td>{r.per_label[l].support}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="two-col">
        <div>
          <h2>Confusion matrix</h2>
          <p className="hint">Rows are true labels, columns are predicted. Shading is relative to row maximum.</p>
          <div className="confusion" style={{ gridTemplateColumns: `110px repeat(${labels.length}, 1fr)` }}>
            <div />
            {labels.map((l) => (
              <div className="cm-head" key={l}>
                {(l.replace(/_/g, " ").toLowerCase())}
              </div>
            ))}
            {r.confusion.matrix.map((row, i) => (
              <div className="cm-row" key={i} style={{ display: "contents" }}>
                <div className="cm-head left">{labels[i].replace(/_/g, " ").toLowerCase()}</div>
                {row.map((v, j) => {
                  const a = v / rowMax[i];
                  const diag = i === j;
                  return (
                    <div
                      key={j}
                      className="cm-cell"
                      style={{
                        background: diag ? `rgba(26,127,55,${0.08 + a * 0.6})` : `rgba(180,35,24,${v ? 0.06 + a * 0.5 : 0})`,
                        color: a > 0.7 ? "#fff" : undefined,
                      }}
                    >
                      {v}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
        <div>
          <h2>Accuracy by greenwashing type</h2>
          <div className="probbars">
            {Object.entries(r.per_gw_type).map(([k, v]) => (
              <div className="probrow wide" key={k}>
                <span className="probname">{k.replace(/_/g, " ")} <span className="dim">n={v.n}</span></span>
                <span className="probtrack">
                  <span className="probfill accent" style={{ width: `${v.accuracy * 100}%` }} />
                </span>
                <span className="probval">{pct(v.accuracy, 1)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <h2>Ablations</h2>
      <div className="v2-table-wrap">
        <table>
          <thead>
            <tr>
              <th>Configuration</th>
              <th>Accuracy</th>
              <th>Macro F1</th>
              <th>Coverage</th>
            </tr>
          </thead>
          <tbody>
            {r.ablations.map((a) => (
              <tr key={a.name}>
                <td>{a.name}</td>
                <td>{pct(a.accuracy, 1)}</td>
                <td>{pct(a.macro_f1, 1)}</td>
                <td>{pct(a.coverage, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {r.pdf_eval && <PdfEval data={r.pdf_eval} />}
    </>
  );
}

const VSHORT: Record<string, string> = { ALIGN: "align", CONTRADICT: "contradict", INSUFFICIENT_EVIDENCE: "insuff.", NOT_CHECKABLE: "not checkable" };

function PdfEval({ data }: { data: Record<string, PdfEvalRow[]> }) {
  return (
    <>
      <h2>End-to-end PDF evaluation</h2>
      <p className="hint">Demo PDFs with planted claims, run through extraction and the full pipeline.</p>
      {Object.entries(data).map(([cfg, rows]) => (
        <div key={cfg}>
          <h4>{cfg.replace(/_/g, " ")}</h4>
          <div className="v2-table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Report</th>
                  <th>Planted</th>
                  <th>Extracted</th>
                  <th>Correct</th>
                  <th>Risk score</th>
                  <th>Band</th>
                  <th>Other claims</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((x) => (
                  <tr key={x.report}>
                    <td>{x.report}</td>
                    <td>{x.planted_claims}</td>
                    <td>{x.extracted}</td>
                    <td>
                      {x.correct}/{x.planted_claims}
                    </td>
                    <td>{x.company_risk_score === null ? "-" : x.company_risk_score.toFixed(1)}</td>
                    <td>{x.risk_band ?? "-"}</td>
                    <td className="small">
                      {Object.entries(x.other_claims_verdicts)
                        .map(([k, n]) => `${VSHORT[k] ?? k} ${n}`)
                        .join(" · ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </>
  );
}
