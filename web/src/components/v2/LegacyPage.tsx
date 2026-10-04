import { useState } from "react";
import { ConfigPanel } from "../ConfigPanel";
import type { Config } from "../ConfigPanel";
import { UploadAnalyzePage } from "../UploadAnalyzePage";
import { DatasetDemoPage } from "../DatasetDemoPage";
import { useBackend } from "../../lib/v2api";

export function LegacyPage() {
  const base = useBackend();
  const [config, setConfig] = useState<Config>({ backendUrl: base, mode: "mock", topK: 5, useSemantic: false });
  const [page, setPage] = useState<"analyze" | "dataset">("analyze");
  return (
    <div className="app-shell legacy-shell">
      <ConfigPanel config={config} onChange={setConfig} page={page} onPageChange={setPage} />
      <div className="main-content">
        {page === "analyze" ? <UploadAnalyzePage config={config} /> : <DatasetDemoPage config={config} />}
      </div>
    </div>
  );
}
