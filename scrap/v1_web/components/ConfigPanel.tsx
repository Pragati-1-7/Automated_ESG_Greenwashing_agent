import { useEffect, useState } from "react";
import { checkHealth } from "../lib/api";

export interface Config {
  backendUrl: string;
  mode: string;
  topK: number;
  useSemantic: boolean;
}

export function ConfigPanel({
  config,
  onChange,
  page,
  onPageChange,
}: {
  config: Config;
  onChange: (c: Config) => void;
  page: "analyze" | "dataset";
  onPageChange: (p: "analyze" | "dataset") => void;
}) {
  const [healthy, setHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      const ok = await checkHealth(config.backendUrl);
      if (!cancelled) setHealthy(ok);
    };
    poll();
    const id = setInterval(poll, 8000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [config.backendUrl]);

  return (
    <aside className="sidebar">
      <h3>Configuration</h3>

      <label>Backend API URL</label>
      <input
        type="text"
        value={config.backendUrl}
        onChange={(e) => onChange({ ...config, backendUrl: e.target.value })}
      />
      <p className="hint">
        Backend status:{" "}
        <strong className={healthy ? "status-ok" : "status-bad"}>
          {healthy === null ? "checking..." : healthy ? "online" : "unreachable"}
        </strong>
      </p>

      <label>Extraction mode</label>
      <select
        value={config.mode}
        onChange={(e) => onChange({ ...config, mode: e.target.value })}
      >
        <option value="mock">mock (offline)</option>
        <option value="groq">groq</option>
        <option value="ollama">ollama</option>
      </select>
      <p className="hint">
        Use 'mock' for offline demo. Groq/Ollama require credentials configured on the backend.
      </p>

      <label>Evidence items per claim (top-k): {config.topK}</label>
      <input
        type="range"
        min={1}
        max={10}
        value={config.topK}
        onChange={(e) => onChange({ ...config, topK: Number(e.target.value) })}
      />

      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={config.useSemantic}
          onChange={(e) => onChange({ ...config, useSemantic: e.target.checked })}
        />
        Enable semantic (ChromaDB) retrieval
      </label>
      <p className="hint">
        Semantic retrieval requires downloading a local embedding model on first use.
      </p>

      <hr />

      <h4>Page</h4>
      <label className="radio-row">
        <input
          type="radio"
          name="page"
          checked={page === "analyze"}
          onChange={() => onPageChange("analyze")}
        />
        Upload &amp; analyze
      </label>
      <label className="radio-row">
        <input
          type="radio"
          name="page"
          checked={page === "dataset"}
          onChange={() => onPageChange("dataset")}
        />
        Full dataset demo
      </label>
    </aside>
  );
}
