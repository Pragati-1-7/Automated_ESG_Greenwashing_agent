import { useState } from "react";
import type { Config } from "./ConfigPanel";
import { demoDataset, ApiError } from "../lib/api";
import type { AnalyzeResult } from "../lib/types";
import { DisclaimerBanner, AnalysisContext } from "./DisclaimerBanner";
import { ExecutiveSummary } from "./ExecutiveSummary";
import { ClaimsTable } from "./ClaimsTable";

export function DatasetDemoPage({ config }: { config: Config }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await demoDataset(config.backendUrl, config.topK, config.useSemantic);
      setResult(r);
    } catch (e) {
      if (e instanceof ApiError) {
        setError(`Dataset demo failed: ${e.message}`);
      } else {
        setError(`Could not reach the backend API at ${config.backendUrl}. Is it running?`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Full dataset demo</h1>
      <p className="subtitle">
        Runs the curated synthetic dataset (data/claims/claims.json) so ALIGN, CONTRADICT, and
        INSUFFICIENT_EVIDENCE examples are all reliably shown, independent of PDF extraction.
      </p>

      <button className="primary-button" disabled={loading} onClick={handleRun}>
        {loading ? "Running..." : "Run dataset demo"}
      </button>
      {loading && <p className="hint">Running pipeline over the curated dataset...</p>}
      {error && <div className="banner banner-error">{error}</div>}

      {result && (
        <>
          <hr />
          <AnalysisContext result={result} mode="n/a (curated dataset, no extraction)" />
          <DisclaimerBanner result={result} />
          <ExecutiveSummary summary={result.summary} />
          <ClaimsTable records={result.audit_records} />
        </>
      )}
    </div>
  );
}
