import { useEffect, useState } from "react";
import { getJson, startAnalysis, url, useBackend } from "../../lib/v2api";
import { navigate } from "../../lib/route";
import type { DemoReport } from "../../lib/v2types";
import { Empty, ErrorBox, Loading } from "./ui";

export function AnalyzePage() {
  const base = useBackend();
  const [reports, setReports] = useState<DemoReport[] | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [maxClaims, setMaxClaims] = useState(40);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setReports(null);
    setLoadErr(null);
    getJson<DemoReport[]>(base, "/v2/demo-reports", ctl.signal)
      .then(setReports)
      .catch((e) => e.name !== "AbortError" && setLoadErr(e.message));
    return () => ctl.abort();
  }, [base, tick]);

  const run = async () => {
    setBusy(true);
    setErr(null);
    try {
      const r = await startAnalysis(base, {
        file,
        demoReport: file ? undefined : (selected ?? undefined),
        maxClaims,
      });
      navigate(`/analyses/${r.analysis_id}`);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const canRun = !busy && (file || selected);

  return (
    <div>
      <h1>Analyze a sustainability report</h1>
      <p className="subtitle">
        Pick a demo report or upload your own PDF. Agents extract claims, plan evidence checks against regulatory
        sources and return a verdict per claim.
      </p>

      <h2>Demo reports</h2>
      {loadErr && <ErrorBox message={loadErr} onRetry={() => setTick(tick + 1)} />}
      {!reports && !loadErr && <Loading text="Loading demo reports..." />}
      {reports && reports.length === 0 && <Empty>No demo reports available on the backend.</Empty>}
      {reports && (
        <div className="cards">
          {reports.map((r) => (
            <div
              key={r.key}
              className={`card demo-card ${selected === r.key && !file ? "selected" : ""}`}
              onClick={() => {
                setSelected(r.key);
                setFile(null);
              }}
            >
              <div className="card-title">{r.title}</div>
              <div className="card-sub">{r.company}</div>
              <div className="card-meta">
                <span>{r.pages} pages</span>
                <span className="chip">{r.profile}</span>
              </div>
              <a
                className="link-button"
                href={url(base, `/v2/demo-reports/${encodeURIComponent(r.key)}/pdf`)}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
              >
                Open PDF
              </a>
            </div>
          ))}
        </div>
      )}

      <h2>Or upload a PDF</h2>
      <div className="panel upload-panel">
        <input
          type="file"
          accept="application/pdf,.pdf"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            if (e.target.files?.[0]) setSelected(null);
          }}
        />
        {file && <p className="hint">Selected: {file.name}</p>}
        <label>Max claims to analyze: {maxClaims}</label>
        <input type="range" min={5} max={100} step={5} value={maxClaims} onChange={(e) => setMaxClaims(Number(e.target.value))} />
      </div>

      {err && <ErrorBox message={err} />}
      <button className="primary-button" disabled={!canRun} onClick={run}>
        {busy ? "Starting..." : "Run analysis"}
      </button>
      {!canRun && !busy && <span className="hint"> Select a demo report or choose a file.</span>}
    </div>
  );
}
