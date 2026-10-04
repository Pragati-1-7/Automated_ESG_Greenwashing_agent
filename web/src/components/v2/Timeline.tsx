import { useEffect, useRef, useState } from "react";
import type { AgentEvent } from "../../lib/v2types";
import { Json } from "./ui";

export function Timeline({
  events,
  running,
  onClaim,
}: {
  events: AgentEvent[];
  running: boolean;
  onClaim: (id: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const stick = useRef(true);
  const [filter, setFilter] = useState("all");
  const agents = Array.from(new Set(events.map((e) => e.agent)));
  const shown = filter === "all" ? events : events.filter((e) => e.agent === filter);

  useEffect(() => {
    const el = ref.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [shown.length]);

  return (
    <div className="panel timeline-panel">
      <div className="row-gap between">
        <h3 className="tight">
          Agent timeline {running && <span className="live"><i className="dot dot-live" />live</span>}
        </h3>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} className="inline-select">
          <option value="all">All agents</option>
          {agents.map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </div>
      <div
        className="timeline"
        ref={ref}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
        }}
      >
        {shown.length === 0 && <div className="state state-empty">{running ? "Waiting for first event..." : "No events."}</div>}
        {shown.map((e) => (
          <div className={`tl-row type-${e.type}`} key={e.seq}>
            <span className="tl-seq">{e.seq}</span>
            <span className={`tl-ic ic-${e.type}`} title={e.type} />
            <span className={`agent a-${e.agent}`}>{e.agent}</span>
            <div className="tl-body">
              <span className="tl-msg">{e.message}</span>
              {e.claim_id && (
                <button className="chip chip-btn" onClick={() => onClaim(e.claim_id!)}>
                  {e.claim_id}
                </button>
              )}
              {e.data && Object.keys(e.data).length > 0 && <Json data={e.data} />}
            </div>
            <span className="tl-time">{new Date(e.ts).toLocaleTimeString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
