import { useState } from "react";
import type { ReactNode } from "react";

export const TIER_LABELS: Record<number, string> = {
  1: "Tier 1 Regulatory filing",
  2: "Tier 2 Regulator record",
  3: "Tier 3 Third-party dataset / audit",
  4: "Tier 4 Company PR",
  5: "Tier 5 News",
};

export const VERDICT_LABEL: Record<string, string> = {
  ALIGN: "Align",
  CONTRADICT: "Contradict",
  INSUFFICIENT_EVIDENCE: "Insufficient",
  NOT_CHECKABLE: "Not checkable",
  support: "Support",
  contradict: "Contradict",
  insufficient: "Insufficient",
};

const VCLASS: Record<string, string> = {
  ALIGN: "v-align",
  support: "v-align",
  CONTRADICT: "v-contra",
  contradict: "v-contra",
  INSUFFICIENT_EVIDENCE: "v-insuf",
  insufficient: "v-insuf",
  NOT_CHECKABLE: "v-nc",
};

export function VerdictPill({ label, count }: { label: string; count?: number }) {
  return (
    <span className={`pill ${VCLASS[label] ?? "v-nc"}`}>
      {VERDICT_LABEL[label] ?? label}
      {count !== undefined && <b>{count}</b>}
    </span>
  );
}

export const pct = (x: number | null | undefined, d = 0) =>
  x === null || x === undefined ? "-" : `${(x * 100).toFixed(d)}%`;

export function ProbBars({ probs, highlight }: { probs: Record<string, number>; highlight?: string }) {
  const entries = Object.entries(probs).sort((a, b) => b[1] - a[1]);
  return (
    <div className="probbars">
      {entries.map(([k, v], i) => (
        <div className="probrow" key={k}>
          <span className="probname">{VERDICT_LABEL[k] ?? k.replace(/_/g, " ")}</span>
          <span className="probtrack">
            <span
              className={`probfill ${VCLASS[k] ?? ""} ${k === highlight || (!highlight && i === 0) ? "top" : ""}`}
              style={{ width: `${Math.max(0, Math.min(1, v)) * 100}%` }}
            />
          </span>
          <span className="probval">{pct(v, 1)}</span>
        </div>
      ))}
    </div>
  );
}

export function Json({ data, label = "data" }: { data: unknown; label?: string }) {
  const [open, setOpen] = useState(false);
  if (data === null || data === undefined) return null;
  return (
    <div className="jsonbox">
      <button className="link-button" onClick={() => setOpen(!open)}>
        {open ? "Hide" : "Show"} {label}
      </button>
      {open && <pre>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
}

export function Loading({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="state state-loading">
      <span className="spinner" /> {text}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="banner banner-error">
      {message}{" "}
      {onRetry && (
        <button className="link-button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="state state-empty">{children}</div>;
}

export function fmtTime(s: string | null | undefined): string {
  if (!s) return "-";
  const d = new Date(s);
  return isNaN(d.getTime()) ? s : d.toLocaleString();
}

export function fmtNum(x: unknown): string {
  if (typeof x === "number") return Number.isInteger(x) ? x.toLocaleString() : x.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return String(x);
}

export function riskClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "r-na";
  if (score >= 75) return "r-vh";
  if (score >= 50) return "r-h";
  if (score >= 25) return "r-m";
  return "r-l";
}
