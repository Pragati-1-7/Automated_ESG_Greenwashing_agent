import { useEffect, useState } from "react";
import { getJson, saveBackendUrl } from "../../lib/v2api";
import type { Health } from "../../lib/v2types";

export const NAV: { path: string; label: string }[] = [
  { path: "/analyze", label: "Analyze (v2)" },
  { path: "/analyses", label: "Analyses" },
  { path: "/verify", label: "Verify a claim" },
  { path: "/sources", label: "Data sources" },
  { path: "/benchmark", label: "Benchmark" },
  { path: "/legacy", label: "Legacy v1" },
];

function HealthIndicator({ base }: { base: string }) {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    let dead = false;
    const ctl = new AbortController();
    const poll = () =>
      getJson<Health>(base, "/health", ctl.signal)
        .then((r) => !dead && (setH(r), setErr(false)))
        .catch((e) => !dead && e.name !== "AbortError" && (setErr(true), setH(null)));
    poll();
    const id = setInterval(poll, 10000);
    return () => {
      dead = true;
      ctl.abort();
      clearInterval(id);
    };
  }, [base]);

  if (err) return <span className="health health-bad"><i className="dot" />Backend unreachable</span>;
  if (!h) return <span className="health"><i className="dot dot-wait" />Checking...</span>;
  const ok = h.status === "ok" && h.sources === "up";
  return (
    <span className={`health ${ok ? "health-ok" : "health-warn"}`} title="decision engine / llm / sources">
      <i className="dot" />
      engine <b>{h.decision_engine}</b> · llm <b>{h.llm}</b> · sources <b>{h.sources}</b>
    </span>
  );
}

export function Shell({
  route,
  base,
  onBase,
  children,
}: {
  route: string;
  base: string;
  onBase: (u: string) => void;
  children: React.ReactNode;
}) {
  const [draft, setDraft] = useState(base);
  const [open, setOpen] = useState(false);
  const active = (p: string) =>
    p === "/analyze" ? route === "/analyze" || route === "/" : route === p || route.startsWith(p + "/");

  return (
    <div className="v2-shell">
      <header className="topbar">
        <div className="topbar-in">
          <div className="brand">
            <span className="brand-mark" />
            ESG Greenwashing Detector
          </div>
          <nav className="topnav">
            {NAV.map((n) => (
              <a key={n.path} href={`#${n.path}`} className={active(n.path) ? "on" : ""}>
                {n.label}
              </a>
            ))}
          </nav>
          <div className="topbar-right">
            <HealthIndicator base={base} />
            <button className="gear" onClick={() => setOpen(!open)} aria-label="Backend settings">
              API
            </button>
            {open && (
              <div className="popover">
                <label>Backend URL</label>
                <input type="text" value={draft} onChange={(e) => setDraft(e.target.value)} />
                <div className="row-gap">
                  <button
                    className="primary-button small"
                    onClick={() => {
                      const u = draft.trim() || base;
                      saveBackendUrl(u);
                      onBase(u);
                      setOpen(false);
                    }}
                  >
                    Save
                  </button>
                  <button className="link-button" onClick={() => setOpen(false)}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
      <main className="v2-main">{children}</main>
    </div>
  );
}
