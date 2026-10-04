import { useState } from "react";
import type { Config } from "./ConfigPanel";
import { analyze, ApiError } from "../lib/api";
import type { AnalyzeResult } from "../lib/types";
import { DisclaimerBanner, AnalysisContext } from "./DisclaimerBanner";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { ClaimsTable } from "./ClaimsTable";

export function UploadAnalyzePage({ config }: { config: Config }) {
  const [file, setFile] = useState<File | null>(null);
  const [useDemo, setUseDemo] = useState(false);
  const [company, setCompany] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [lastMode, setLastMode] = useState("mock");

  const canAnalyze = file !== null || useDemo;

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await analyze(config.backendUrl, {
        file,
        useDemo,
        company,
        mode: config.mode,
        topK: config.topK,
        useSemantic: config.useSemantic,
      });
      setResult(r);
      setLastMode(config.mode);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`Analysis failed: ${e.message}`);
      } else {
        setError(`Could not reach the backend API at ${config.backendUrl}. Is it running?`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>ESG Claim Verification &amp; Greenwashing Risk Analyzer</h1>
      <p className="subtitle">Evidence-based ESG claim analysis for human review</p>
      <div className="banner banner-warning">
        This tool provides evidence-based triage and decision support. It does not constitute a
        legal determination of greenwashing.
      </div>

      <div className="upload-row">
        <div className="upload-col">
          <label>Upload ESG PDF</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>
        <div className="upload-col">
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={useDemo}
              onChange={(e) => setUseDemo(e.target.checked)}
            />
            Use demo ESG report (bundled synthetic sample, works offline)
          </label>
        </div>
      </div>

      <label>Company name (optional)</label>
      <input
        type="text"
        value={company}
        onChange={(e) => setCompany(e.target.value)}
        placeholder="Company name"
      />

      {file && (
        <p className="hint">
          File: {file.name} &middot; Size: {(file.size / 1024).toFixed(1)} KB
        </p>
      )}

      <button className="primary-button" disabled={!canAnalyze || loading} onClick={handleAnalyze}>
        {loading ? "Analyzing..." : "Analyze report"}
      </button>
      {loading && (
        <p className="hint">
          Running pipeline: parsing, extraction, checkability, retrieval, verification, risk
          scoring...
        </p>
      )}
      {error && <div className="banner banner-error">{error}</div>}

      {result && (
        <>
          <hr />
          <AnalysisContext result={result} mode={lastMode} />
          <DisclaimerBanner result={result} />
          {result.status === "no_claims" ? (
            <div className="banner banner-error">
              {result.message}
              {result.extraction_errors.length > 0 && (
                <details>
                  <summary>Extraction details</summary>
                  <ul>
                    {result.extraction_errors.map((e, i) => (
                      <li key={i}>{e}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ) : (
            <>
              <ExecutiveSummary summary={result.summary} />
              <ClaimsTable records={result.audit_records} />
            </>
          )}
        </>
      )}
    </div>
  );
}
