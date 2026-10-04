import { useState } from "react";
import { postJson, useBackend } from "../../lib/v2api";
import type { VerifyResponse } from "../../lib/v2types";
import { ClaimDetail } from "./ClaimDrawer";
import { Timeline } from "./Timeline";
import { ErrorBox, Loading } from "./ui";

export function VerifyPage() {
  const base = useBackend();
  const [company, setCompany] = useState("Vajra Steel & Power Ltd");
  const [claim, setClaim] = useState("We cut our Scope 1 emissions by 40% since FY2020.");
  const [fy, setFy] = useState("FY2023");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [res, setRes] = useState<VerifyResponse | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    setRes(null);
    try {
      const body: Record<string, string> = { claim: claim.trim(), company: company.trim() };
      if (fy.trim()) body.fy = fy.trim();
      setRes(await postJson<VerifyResponse>(base, "/v2/verify-claim", body));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1>Verify a claim</h1>
      <p className="subtitle">Check a single sentence against the evidence sources, using the same agents as a full report.</p>
      <div className="panel verify-form">
        <label>
          Company
          <input type="text" value={company} onChange={(e) => setCompany(e.target.value)} />
        </label>
        <label>
          Claim
          <textarea rows={3} value={claim} onChange={(e) => setClaim(e.target.value)} />
        </label>
        <label className="fy">
          Financial year (optional)
          <input type="text" value={fy} onChange={(e) => setFy(e.target.value)} placeholder="FY2023" />
        </label>
        <div>
          <button className="primary-button" disabled={busy || !claim.trim() || !company.trim()} onClick={run}>
            {busy ? "Verifying..." : "Verify claim"}
          </button>
        </div>
      </div>
      {busy && <Loading text="Agents are checking the claim..." />}
      {err && <ErrorBox message={err} onRetry={run} />}
      {res && (
        <>
          {res.company && (
            <p className="res-badges">
              <b>{res.company.name}</b>{" "}
              <span className={`chip ${res.company.resolved ? "chip-ok" : "chip-warn"}`}>
                {res.company.resolved ? `Resolved${res.company.company_id ? ` ${res.company.company_id}` : ""}` : "Not resolved"}
              </span>{" "}
              <span className="hint">match {res.company.match_score.toFixed(2)}</span>
            </p>
          )}
          <ClaimDetail claim={res.claim} />
          <Timeline events={res.events} running={false} onClaim={() => undefined} />
        </>
      )}
    </div>
  );
}
