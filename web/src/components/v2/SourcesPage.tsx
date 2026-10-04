import { useEffect, useState } from "react";
import { getJson, useBackend } from "../../lib/v2api";
import type { SourceRows, SourcesOverview } from "../../lib/v2types";
import { Empty, ErrorBox, Loading, TIER_LABELS, fmtNum } from "./ui";

const LIMIT = 50;

function Cell({ v }: { v: unknown }) {
  if (v === null || v === undefined) return <span className="dim">null</span>;
  if (typeof v === "object") {
    const s = JSON.stringify(v);
    return <span title={s}>{s.length > 60 ? s.slice(0, 57) + "..." : s}</span>;
  }
  const s = fmtNum(v);
  return <span title={String(v)}>{s.length > 80 ? s.slice(0, 77) + "..." : s}</span>;
}

function TableBrowser({ name }: { name: string }) {
  const base = useBackend();
  const [offset, setOffset] = useState(0);
  const [cid, setCid] = useState("");
  const [applied, setApplied] = useState("");
  const [data, setData] = useState<SourceRows | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    setOffset(0);
    setCid("");
    setApplied("");
  }, [name]);

  useEffect(() => {
    const ctl = new AbortController();
    setData(null);
    setErr(null);
    const q = new URLSearchParams({ limit: String(LIMIT), offset: String(offset) });
    if (applied) q.set("company_id", applied);
    getJson<SourceRows>(base, `/v2/sources/${encodeURIComponent(name)}?${q}`, ctl.signal)
      .then(setData)
      .catch((e) => e.name !== "AbortError" && setErr(e.message));
    return () => ctl.abort();
  }, [base, name, offset, applied]);

  const cols = data ? Array.from(new Set(data.rows.flatMap((r) => Object.keys(r)))) : [];
  return (
    <div className="panel">
      <div className="row-gap between">
        <h3 className="tight">{name}</h3>
        <form
          className="row-gap"
          onSubmit={(e) => {
            e.preventDefault();
            setOffset(0);
            setApplied(cid.trim());
          }}
        >
          <input type="text" placeholder="filter by company_id" value={cid} onChange={(e) => setCid(e.target.value)} />
          <button className="primary-button small">Filter</button>
        </form>
      </div>
      {err && <ErrorBox message={err} />}
      {!data && !err && <Loading />}
      {data && data.rows.length === 0 && <Empty>No rows.</Empty>}
      {data && data.rows.length > 0 && (
        <>
          <div className="v2-table-wrap scroll-x">
            <table className="dense">
              <thead>
                <tr>
                  {cols.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r, i) => (
                  <tr key={i}>
                    {cols.map((c) => (
                      <td key={c}>
                        <Cell v={r[c]} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row-gap between">
            <span className="hint">
              Rows {data.total === 0 ? 0 : offset + 1}-{offset + data.rows.length} of {data.total.toLocaleString()}
            </span>
            <span className="row-gap">
              <button className="ghost-button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>
                Previous
              </button>
              <button className="ghost-button" disabled={offset + LIMIT >= data.total} onClick={() => setOffset(offset + LIMIT)}>
                Next
              </button>
            </span>
          </div>
        </>
      )}
    </div>
  );
}

export function SourcesPage() {
  const base = useBackend();
  const [ov, setOv] = useState<SourcesOverview | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setOv(null);
    setErr(null);
    getJson<SourcesOverview>(base, "/v2/sources/overview", ctl.signal)
      .then(setOv)
      .catch((e) => e.name !== "AbortError" && setErr(e.message));
    return () => ctl.abort();
  }, [base, tick]);

  return (
    <div>
      <h1>Data sources</h1>
      <p className="subtitle">Evidence tables the investigator agents query. All data is synthetic.</p>
      {err && <ErrorBox message={err} onRetry={() => setTick(tick + 1)} />}
      {!ov && !err && <Loading />}
      {ov && ov.tables.length === 0 && <Empty>No tables reported by the backend.</Empty>}
      {ov && ov.tables.length > 0 && (
        <div className="v2-table-wrap">
          <table className="clickable">
            <thead>
              <tr>
                <th>Table</th>
                <th>Rows</th>
                <th>Tier</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {ov.tables.map((t) => (
                <tr key={t.name} className={sel === t.name ? "row-selected" : ""} onClick={() => setSel(t.name)}>
                  <td>
                    <b>{t.name}</b>
                  </td>
                  <td>{t.rows.toLocaleString()}</td>
                  <td>
                    <span className={`tier tier-${t.tier}`}>{t.tier === null || t.tier === undefined ? "n/a" : (TIER_LABELS[t.tier] ?? `Tier ${t.tier}`)}</span>
                  </td>
                  <td>{t.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {ov && !sel && ov.tables.length > 0 && <p className="hint">Click a table to browse its rows.</p>}
      {sel && <TableBrowser name={sel} />}
    </div>
  );
}
