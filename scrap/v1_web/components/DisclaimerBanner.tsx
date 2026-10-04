import type { AnalyzeResult } from "../lib/types";

export function DisclaimerBanner({ result }: { result: AnalyzeResult }) {
  return (
    <div className="banner banner-warning">
      <strong>Synthetic evidence corpus:</strong> {result.synthetic_evidence_notice}
      <br />
      {result.disclaimer}
    </div>
  );
}

export function AnalysisContext({ result, mode }: { result: AnalyzeResult; mode: string }) {
  return (
    <div className="context-strip">
      <span>
        <strong>Analyzing:</strong> {result.source_document}
      </span>
      <span>
        <strong>Company:</strong> {result.company}
      </span>
      <span>
        <strong>Extraction mode:</strong> {mode}
      </span>
    </div>
  );
}
