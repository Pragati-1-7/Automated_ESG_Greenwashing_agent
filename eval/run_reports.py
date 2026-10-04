"""
eval/run_reports.py

End-to-end evaluation on the demo report PDFs: extraction recall of the
planted claims, verdict accuracy on them, company risk score, and what the
system said about everything else it extracted. Also runs the PDFs with the
relevance gate switched off, where its effect is visible (off-topic negative
news no longer drags unrelated claims to CONTRADICT).

    python -m eval.run_reports
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter

from app.core.ablation import Flags, _flags, use_flags
from app.core.config import ROOT
from app.core.events import EventSink
from app.graph.runner import new_analysis, run_analysis
from data_gen.spec import DEMO_COMPANIES

REPORTS = ROOT / "data" / "reports"
OUT = ROOT / "data" / "benchmark" / "reports_eval.json"
KEYS = {"vajra": 0, "sahyadri": 1, "kaveri": 2, "aurelia": 3}


async def evaluate(key: str, flags: Flags) -> dict:
    man = {m["key"]: m for m in json.loads((REPORTS / "manifest.json").read_text())}
    m = man[key]
    token = use_flags(flags)
    try:
        a, _ = await run_analysis(REPORTS / m["filename"], new_analysis(m["filename"]), EventSink())
    finally:
        _flags.reset(token)
    spec = DEMO_COMPANIES[KEYS[key]]["claims"]
    by_text = {c.text: c for c in a.claims}
    rows = []
    for c in spec:
        got = by_text.get(c["text"])
        pred = got.verdict.label if got else "NOT_EXTRACTED"
        ok = pred == c["expected"] or (c["id"] == "AUR-05" and pred in ("ALIGN", "INSUFFICIENT_EVIDENCE"))
        rows.append({"id": c["id"], "expected": c["expected"], "predicted": pred, "correct": ok,
                     "confidence": round(got.verdict.confidence, 3) if got else None})
    extra = [c for c in a.claims if c.text not in {s["text"] for s in spec}]
    return {"report": key, "status": a.status, "company_resolved": a.company.resolved if a.company else False,
            "planted_claims": len(spec), "extracted": sum(r["predicted"] != "NOT_EXTRACTED" for r in rows),
            "correct": sum(r["correct"] for r in rows), "company_risk_score": a.summary.company_risk_score,
            "risk_band": a.summary.risk_band, "other_claims": len(extra),
            "other_claims_verdicts": dict(Counter(c.verdict.label for c in extra)), "claims": rows}


async def main() -> None:
    out = {}
    for name, f in [("full_system", Flags()), ("no_relevance_gate", Flags(relevance_gate=False))]:
        out[name] = [await evaluate(k, f) for k in KEYS]
        tot = sum(r["planted_claims"] for r in out[name])
        cor = sum(r["correct"] for r in out[name])
        ext = sum(r["extracted"] for r in out[name])
        print(f"{name}: extraction recall {ext}/{tot}, verdict accuracy {cor}/{tot}")
        for r in out[name]:
            print(f"   {r['report']:9s} {r['correct']}/{r['planted_claims']} risk={r['company_risk_score']} "
                  f"({r['risk_band']}) other={r['other_claims_verdicts']}")
    OUT.write_text(json.dumps(out, indent=2))
    res = ROOT / "data" / "benchmark" / "results_latest.json"
    if res.exists():
        d = json.loads(res.read_text())
        d["pdf_eval"] = {k: [{x: r[x] for x in ("report", "planted_claims", "extracted", "correct", "company_risk_score",
                                                "risk_band", "other_claims_verdicts")} for r in v] for k, v in out.items()}
        res.write_text(json.dumps(d, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    asyncio.run(main())
