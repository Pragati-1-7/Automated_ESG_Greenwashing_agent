import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getJson, url, useBackend } from "../../lib/v2api";
import { isFixtureMode } from "../../lib/route";
import { Markdown } from "../../lib/markdown";
import type { AgentEvent, Analysis } from "../../lib/v2types";
import sample from "../../fixtures/sampleAnalysis.json";
import { Timeline } from "./Timeline";
import { ClaimsTable, EngineChips, RiskGauge, Summary } from "./Results";
import { ClaimDrawer } from "./ClaimDrawer";
import { Empty, ErrorBox, Loading } from "./ui";

type Tab = "trace" | "results" | "report";
const fixture = sample as unknown as { analysis: Analysis; events: AgentEvent[]; report: string };

function Counters({ a, events }: { a: Analysis | null; events: AgentEvent[] }) {
  const claims = a?.claims.length ?? 0;
  const subs = a?.claims.reduce((n, c) => n + c.sub_claims.length, 0) ?? 0;
  const calls = events.filter((e) => e.type === "tool_call").length;
  const verdicts = events.filter((e) => e.type === "verdict").length;
  const items: [string, number][] = [
    ["Claims found", claims],
    ["Sub-claims", subs],
    ["Tool calls", calls],
    ["Verdicts", verdicts],
  ];
  return (
    <div className="counters">
      {items.map(([k, v]) => (
        <div className="counter" key={k}>
          <b>{v}</b>
          <span>{k}</span>
        </div>
      ))}
    </div>
  );
}

export function AnalysisPage({ id }: { id: string }) {
  const base = useBackend();
  const useFixture = isFixtureMode();
  const [a, setA] = useState<Analysis | null>(useFixture ? fixture.analysis : null);
  const [events, setEvents] = useState<AgentEvent[]>(useFixture ? fixture.events : []);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>(useFixture ? "results" : "trace");
  const [sel, setSel] = useState<string | null>(null);
  const [report, setReport] = useState<string | null>(useFixture ? fixture.report : null);
  const [reportErr, setReportErr] = useState<string | null>(null);
  const finished = useRef(useFixture);
  const [streamDone, setStreamDone] = useState(useFixture);

  const fetchAnalysis = useCallback(
    async (signal?: AbortSignal) => {
      try {
        const r = await getJson<Analysis>(base, `/v2/analyses/${id}`, signal);
        setA(r);
        setErr(null);
        if (r.status === "done" || r.status === "error") {
          if (!finished.current) {
            finished.current = true;
            if (r.status === "done") setTab("results");
          }
        }
        return r;
      } catch (e) {
        if ((e as Error).name !== "AbortError") setErr((e as Error).message);
        return null;
      }
    },
    [base, id],
  );

  // SSE + polling (skipped in fixture mode)
  useEffect(() => {
    if (useFixture) return;
    finished.current = false;
    setA(null);
    setEvents([]);
    setReport(null);
    setStreamDone(false);
    setErr(null);
    const ctl = new AbortController();
    fetchAnalysis(ctl.signal);

    const es = new EventSource(url(base, `/v2/analyses/${id}/events`));
    const seen = new Set<number>();
    es.addEventListener("agent_event", (m) => {
      try {
        const ev = JSON.parse((m as MessageEvent).data) as AgentEvent;
        if (seen.has(ev.seq)) return;
        seen.add(ev.seq);
        setEvents((prev) => [...prev, ev]);
      } catch {
        /* ignore malformed event */
      }
    });
    es.addEventListener("done", () => {
      es.close();
      setStreamDone(true);
      fetchAnalysis();
    });
    es.onerror = () => {
      // EventSource auto-retries; if the run already finished, stop.
      if (finished.current) es.close();
    };
    const poll = setInterval(() => {
      if (!finished.current) fetchAnalysis(ctl.signal);
    }, 2000);
    return () => {
      ctl.abort();
      es.close();
      clearInterval(poll);
    };
  }, [base, id, useFixture, fetchAnalysis]);

  const running = !streamDone && (!a || a.status === "queued" || a.status === "running");

  useEffect(() => {
    if (tab !== "report" || report !== null || a?.status !== "done" || useFixture) return;
    getJson<{ markdown: string }>(base, `/v2/analyses/${id}/report`)
      .then((r) => setReport(r.markdown))
      .catch((e) => setReportErr(e.message));
  }, [tab, report, a?.status, base, id, useFixture]);

  const claim = useMemo(() => a?.claims.find((c) => c.claim_id === sel) ?? null, [a, sel]);

  if (!a && err) return <ErrorBox message={err} onRetry={() => fetchAnalysis()} />;
  if (!a && events.length === 0) return <Loading text="Opening analysis..." />;

  return (
    <div>
      {useFixture && <div className="banner banner-warning">Fixture mode: showing bundled sample data, no backend calls.</div>}
      <div className="res-header">
        <div className="res-main">
          <h1>{a?.company?.name ?? a?.source_document ?? "Analysis"}</h1>
          <p className="subtitle">
            {a?.source_document} · <span className={`chip status-${a?.status ?? "running"}`}>{a?.status ?? "running"}</span>
            {a?.page_count ? ` · ${a.page_count} pages` : ""} · <span className="mono">{id}</span>
          </p>
          <p className="res-badges">
            {a?.company && (
              <span className={`chip ${a.company.resolved ? "chip-ok" : "chip-warn"}`}>
                {a.company.resolved ? `Resolved${a.company.company_id ? ` ${a.company.company_id}` : ""}` : "Not resolved"}
              </span>
            )}
            <EngineChips engines={a?.engines} />
          </p>
        </div>
        {a?.summary && (
          <div className="res-gauge">
            <RiskGauge score={a.summary.company_risk_score} band={a.summary.risk_band} />
          </div>
        )}
      </div>
      {a?.status === "error" && <ErrorBox message={a.error ?? "Analysis failed."} />}
      {err && a && <p className="hint">Refresh issue: {err}</p>}
      {a && (a.disclaimer || a.synthetic_notice) && (
        <div className="banner banner-warning">
          {a.synthetic_notice && (
            <>
              <strong>Synthetic evidence:</strong> {a.synthetic_notice}
              <br />
            </>
          )}
          {a.disclaimer}
        </div>
      )}

      <Counters a={a} events={events} />

      <div className="tabs">
        {(
          [
            ["trace", "Live trace"],
            ["results", "Results"],
            ["report", "Report"],
          ] as [Tab, string][]
        ).map(([k, l]) => (
          <button key={k} className={`tab ${tab === k ? "tab-active" : ""}`} onClick={() => setTab(k)}>
            {l}
          </button>
        ))}
      </div>

      {tab === "trace" && <Timeline events={events} running={running} onClaim={(c) => (setSel(c), setTab("results"))} />}

      {tab === "results" &&
        (a && (a.summary || a.claims.length > 0) ? (
          <>
            {running && <p className="hint">Partial results, updating every 2 seconds.</p>}
            <Summary a={a} onClaim={setSel} />
            <ClaimsTable claims={a.claims} selected={sel} onSelect={setSel} />
          </>
        ) : (
          <Empty>{running ? "Analysis is running. Results will appear here as claims are verified." : "No results."}</Empty>
        ))}

      {tab === "report" &&
        (report !== null ? (
          <div className="panel">
            <Markdown source={report} />
          </div>
        ) : reportErr ? (
          <ErrorBox message={reportErr} />
        ) : a?.status === "done" ? (
          <Loading text="Loading report..." />
        ) : (
          <Empty>The report is available once the analysis finishes.</Empty>
        ))}

      {claim && <ClaimDrawer claim={claim} onClose={() => setSel(null)} />}
    </div>
  );
}
