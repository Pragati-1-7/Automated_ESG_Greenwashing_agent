import { useState } from "react";
import { ConfigPanel } from "./components/ConfigPanel";
import type { Config } from "./components/ConfigPanel";
import { UploadAnalyzePage } from "./components/UploadAnalyzePage";
import { DatasetDemoPage } from "./components/DatasetDemoPage";
import { DEFAULT_BACKEND } from "./lib/constants";
import "./App.css";

export default function App() {
  const [config, setConfig] = useState<Config>({
    backendUrl: DEFAULT_BACKEND,
    mode: "mock",
    topK: 5,
    useSemantic: false,
  });
  const [page, setPage] = useState<"analyze" | "dataset">("analyze");

  return (
    <div className="app-shell">
      <ConfigPanel config={config} onChange={setConfig} page={page} onPageChange={setPage} />
      <main className="main-content">
        {page === "analyze" ? (
          <UploadAnalyzePage config={config} />
        ) : (
          <DatasetDemoPage config={config} />
        )}
      </main>
    </div>
  );
}
