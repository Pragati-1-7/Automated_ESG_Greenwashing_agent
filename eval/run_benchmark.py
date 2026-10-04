"""
eval/run_benchmark.py

Runs the 200-case benchmark (data/benchmark/cases.jsonl) through the SAME
agents used for PDF analysis, plus ablations that switch one component off.

    python -m eval.run_benchmark                 # full system on all 200, ablations on the 60-case test split
    python -m eval.run_benchmark --quick         # full system on the test split only

Writes data/benchmark/results_latest.json (API: GET /v2/benchmark/latest) and
data/benchmark/predictions_<config>.jsonl. With JEV_MODE=replay it runs
offline from recorded decision-engine answers.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

from app.core.ablation import Flags, use_flags
from app.core.config import ROOT
from app.decision.jev import engine
from app.graph.claims import verify_claim
from app.llm.providers import MockLLM

BENCH = ROOT / "data" / "benchmark"
LABELS = ["ALIGN", "CONTRADICT", "INSUFFICIENT_EVIDENCE", "NOT_CHECKABLE"]

CONFIGS = {
    "full_system": Flags(),
    "no_retrieval": Flags(retrieval=False),
    "news_rag_only": Flags(only_sources=("news",)),
    "single_round": Flags(max_rounds=1),
    "no_relevance_gate": Flags(relevance_gate=False),
}


def load_cases() -> list[dict]:
    return [json.loads(l) for l in (BENCH / "cases.jsonl").read_text().splitlines() if l.strip()]


async def predict(cases: list[dict], flags: Flags, concurrency: int = 8) -> list[dict]:
    jev, llm = engine(), MockLLM()
    sem = asyncio.Semaphore(concurrency)
    cache: dict = {}

    async def one(c: dict) -> dict:
        async with sem:
            token = use_flags(flags)
            try:
                claim, match = await verify_claim(c["claim_text"], c["company_name"], jev, llm,
                                                  doc_fy=c["fy"] or "FY2025", claim_id=c["case_id"], company_cache=cache)
            finally:
                from app.core.ablation import _flags
                _flags.reset(token)
            cited_sources = sorted({e.source for s in claim.sub_claims for e in s.evidence
                                    if e.stance and e.stance.label in ("support", "contradict")})
            feats = {comp.name: comp.value for comp in claim.risk.components}
            return {"case_id": c["case_id"], "label": c["label"], "pred": claim.verdict.label,
                    "confidence": claim.verdict.confidence, "gw_type": c["gw_type"], "difficulty": c["difficulty"],
                    "split": c["split"], "resolved": match.resolved, "cited_sources": cited_sources,
                    "truth_tables": sorted({r.split(":")[0] for r in c["evidence_refs"]}), "features": feats,
                    "risk": claim.risk.score}

    return list(await asyncio.gather(*(one(c) for c in cases)))


def metrics(preds: list[dict]) -> dict:
    n = len(preds)
    acc = sum(p["pred"] == p["label"] for p in preds) / n if n else 0
    per = {}
    for lab in LABELS:
        tp = sum(p["pred"] == lab and p["label"] == lab for p in preds)
        fp = sum(p["pred"] == lab and p["label"] != lab for p in preds)
        fn = sum(p["pred"] != lab and p["label"] == lab for p in preds)
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        per[lab] = {"precision": round(pr, 3), "recall": round(rc, 3),
                    "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0,
                    "support": sum(p["label"] == lab for p in preds)}
    decisive_truth = [p for p in preds if p["label"] in ("ALIGN", "CONTRADICT")]
    coverage = (sum(p["pred"] in ("ALIGN", "CONTRADICT") for p in decisive_truth) / len(decisive_truth)
                if decisive_truth else 0.0)
    decisive = [p for p in preds if p["pred"] in ("ALIGN", "CONTRADICT") and p["truth_tables"]]
    cite = (sum(bool(set(p["cited_sources"]) & set(p["truth_tables"])) for p in decisive) / len(decisive)
            if decisive else 0.0)
    by_type = defaultdict(list)
    for p in preds:
        by_type[p["gw_type"]].append(p["pred"] == p["label"])
    conf = [[sum(p["label"] == a and p["pred"] == b for p in preds) for b in LABELS] for a in LABELS]
    return {"overall": {"accuracy": round(acc, 3),
                        "macro_f1": round(sum(v["f1"] for v in per.values()) / len(per), 3),
                        "coverage": round(coverage, 3), "citation_precision": round(cite, 3)},
            "per_label": per,
            "per_gw_type": {k: {"n": len(v), "accuracy": round(sum(v) / len(v), 3)} for k, v in sorted(by_type.items())},
            "confusion": {"labels": LABELS, "matrix": conf}}


async def main(quick: bool) -> None:
    cases = load_cases()
    test = [c for c in cases if c["split"] == "test"]
    t0 = time.time()
    full = await predict(test if quick else cases, CONFIGS["full_system"])
    (BENCH / "predictions_full_system.jsonl").write_text("\n".join(json.dumps(p) for p in full))
    full_test = [p for p in full if p["split"] == "test"]
    report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "split": "test",
              "n_cases": len(full_test), **metrics(full_test),
              "all_cases": {"n": len(full), **metrics(full)["overall"]}, "ablations": []}
    print(f"full_system test: {report['overall']}  (all {len(full)}: {report['all_cases']})")
    for name, f in CONFIGS.items():
        preds = full_test if name == "full_system" else await predict(test, f)
        m = metrics(preds)["overall"]
        report["ablations"].append({"name": name, "accuracy": m["accuracy"], "macro_f1": metrics(preds)["overall"]["macro_f1"],
                                    "coverage": m["coverage"]})
        print(f"{name:18s} acc={m['accuracy']:.3f} macroF1={m['macro_f1']:.3f} coverage={m['coverage']:.3f}")
        if name != "full_system":
            (BENCH / f"predictions_{name}.jsonl").write_text("\n".join(json.dumps(p) for p in preds))
    jev = engine()
    report["engine"] = {"decision": jev.model_version, "jev_calls": jev.stats.calls, "cache_hits": jev.stats.cache_hits,
                        "seconds": round(time.time() - t0, 1)}
    (BENCH / "results_latest.json").write_text(json.dumps(report, indent=2))
    print("wrote", BENCH / "results_latest.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    asyncio.run(main(ap.parse_args().quick))
