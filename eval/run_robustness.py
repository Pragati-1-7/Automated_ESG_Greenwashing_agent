"""
eval/run_robustness.py

Honest stress testing beyond the main benchmark. Five checks:

  A. HELD-OUT benchmark: 200 fresh cases generated with a different seed (777),
     never looked at while building the system; cases whose text also appears
     in the main benchmark are dropped.
  B. HAND-WRITTEN stress set: 24 claims written by hand in phrasings the
     generator never uses (paraphrase, word numbers, lakh units, negation,
     typos in company names, look-alike company, wrong-company figures,
     compound claims, unit traps). Labels computed from the DB.
  C. Bad inputs: blank/scanned, corrupted and non-ESG PDFs through the v2 pipeline.
  D. Decision-engine consistency: the same Jev questions asked 3 times
     WITHOUT the cassette, to measure how stable its answers are.
  E. Cold-run cost: one report analysed with an empty cassette (latency + calls).

    python -m eval.run_robustness          # needs TYPESAFE_API_KEY (records answers)
Writes data/benchmark/robustness_latest.json
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from collections import Counter
from pathlib import Path

from app.core.config import ROOT
from app.core.events import EventSink
from app.decision.jev import JevEngine, choice, engine, noul
from app.graph.claims import verify_claim
from app.graph.runner import new_analysis, run_analysis
from app.llm.providers import MockLLM
from eval.run_benchmark import metrics

OUT = ROOT / "data" / "benchmark" / "robustness_latest.json"

# (company name as written, claim, expected label, what it stresses)
STRESS = [
    ("Surasena Steel & Alloys Ltd", "Over five years our emissions per crore of revenue have come down by roughly 14%.",
     "ALIGN", "paraphrase, implicit baseline (intensity 342.1 -> 294.8 = -13.8%)"),
    ("Surasena Steel and Alloys Limited", "Scope 1 emissions stood at 11.18 lakh tCO2e in FY2024-25.",
     "ALIGN", "name variant + lakh unit (1,117,901 t)"),
    ("Loktak Sponge & Steel Ltd", "Not a single life was lost at work across our sites in the year ended 31 March 2025.",
     "CONTRADICT", "negated phrasing, date phrasing (FY2025 fatalities = 1)"),
    ("Dibang Mining & Minerals Ltd", "None of our units was asked by any regulator to shut operations during FY2024-25.",
     "CONTRADICT", "paraphrased closure direction (CPCB closure 2024-07-19)"),
    ("Surasena Steel & Alloys Ltd", "We received no notices or penalties from environmental regulators in FY2024-25.",
     "ALIGN", "true negative (0 actions in FY2025)"),
    ("Subansiri Agrochem Ltd", "We have cut purchased-electricity emissions by a third since FY2020.",
     "CONTRADICT", "word number 'a third' (Scope 2 -3.4%)"),
    ("Subansiri Agrochem Ltd", "Purchased-electricity (Scope 2) emissions were 3% lower in FY2025 than in FY2020.",
     "ALIGN", "paraphrased metric name (Scope 2 -3.4%)"),
    ("Pandya Tyres Ltd", "Close to 31 per cent of the power we used in FY2025 came from renewable sources.",
     "ALIGN", "'per cent', hedged rounding (30.6%)"),
    ("Pandya Tyres Ltd", "Nearly half of our electricity in FY2025 was renewable.",
     "CONTRADICT", "word number 'half' (30.6%)"),
    ("Kim Fertilisers Ltd", "Kim Fertilisers maintained a spotless compliance record throughout FY2024-25.",
     "CONTRADICT", "figurative wording (3 actions in FY2025)"),
    ("Pandya Tyres Ltd", "Pandya Tyres' Scope 1 emissions were 2,272,700 tCO2e in FY2025.",
     "CONTRADICT", "another company's figure (actual 15,856)"),
    ("Kim Fertilisers Ltd",
     "Our Scope 1 emissions were 22.7 lakh tCO2e in FY2025.", "ALIGN", "lakh unit (2,272,700 t)"),
    ("CMP-0011",
     "We sourced 58.6% of our electricity from renewables in FY2025 and recorded zero fatalities.",
     "ALIGN", "compound, both parts true"),
    ("Dibang Mining & Minerals Ltd",
     "Renewables met 16.4% of our electricity needs in FY2025, and we recorded zero fatalities.",
     "CONTRADICT", "compound, one part false (1 fatality)"),
    ("Jaintia Weaves Ltd", "Our employee engagement score rose to 82% in FY2025.",
     "INSUFFICIENT_EVIDENCE", "metric no source carries"),
    ("CMP-0013", "Scope 3 emissions from purchased goods fell 12% in FY2025.",
     "INSUFFICIENT_EVIDENCE", "Scope 3 not in any source"),
    ("CMP-0014", "We strive to minimise our environmental footprint wherever practicable.",
     "NOT_CHECKABLE", "hedged cheap talk"),
    ("CMP-0015", "By FY2030 we will halve our freshwater withdrawal.", "NOT_CHECKABLE", "future target"),
    ("Surasena Power Ltd", "We recorded zero fatalities in FY2025.", "INSUFFICIENT_EVIDENCE",
     "look-alike name: shares the distinctive token of a DB company but is a different firm"),
    ("Dibang Mining & Minerals Ltd", "No closure directions were issued to us in FY2023-24.", "ALIGN",
     "period trap (closure exists, but in FY2025)"),
    ("CMP-0015", "Water withdrawal was limited to 1.72 lakh kL in FY2025.", "ALIGN", "lakh kL (171,848 kL)"),
    ("Jaintia Weaves Ltd", "Water withdrawal was 435,929 litres in FY2025.", "CONTRADICT",
     "unit trap: number right, unit 1000x wrong (435,929 kL)"),
    ("Dibang Mining & Minerals Ltd", "Emission intensity fell 22% between FY2020 and FY2025.", "ALIGN",
     "intensity true (-21.8%)"),
    ("Dibang Mining & Minerals Ltd", "Absolute Scope 1 emissions fell 22% between FY2020 and FY2025.", "CONTRADICT",
     "absolute vs intensity (absolute +3.8%)"),
]


def _company_names() -> dict[str, str]:
    import sqlite3
    c = sqlite3.connect(ROOT / "data/world/world.db")
    return dict(c.execute("select company_id, name from companies").fetchall())


async def part_a() -> dict:
    main = {json.loads(l)["claim_text"] for l in (ROOT / "data/benchmark/cases.jsonl").read_text().splitlines() if l}
    cases = [json.loads(l) for l in (ROOT / "data/benchmark_heldout/cases.jsonl").read_text().splitlines() if l]
    fresh = [c for c in cases if c["claim_text"] not in main]
    from eval.run_benchmark import CONFIGS, predict
    preds = await predict(fresh, CONFIGS["full_system"])
    for p in preds:
        p["split"] = "heldout"
    (ROOT / "data/benchmark_heldout/predictions.jsonl").write_text("\n".join(json.dumps(p) for p in preds))
    m = metrics(preds)
    wrong = [{"case_id": p["case_id"], "label": p["label"], "pred": p["pred"], "gw_type": p["gw_type"]}
             for p in preds if p["pred"] != p["label"]]
    return {"n": len(preds), "dropped_overlap": len(cases) - len(fresh), **m, "errors": wrong}


async def part_b() -> dict:
    names = _company_names()
    jev, llm = engine(), MockLLM()
    rows = []
    for i, (co, text, exp, what) in enumerate(STRESS, 1):
        co = names.get(co, co)
        claim, match = await verify_claim(text, co, jev, llm, claim_id=f"ST-{i:02d}")
        rows.append({"id": f"ST-{i:02d}", "company": co, "claim": text, "expected": exp,
                     "predicted": claim.verdict.label, "confidence": round(claim.verdict.confidence, 3),
                     "resolved": match.resolved, "stresses": what, "correct": claim.verdict.label == exp})
    return {"n": len(rows), "correct": sum(r["correct"] for r in rows),
            "accuracy": round(sum(r["correct"] for r in rows) / len(rows), 3), "rows": rows}


async def part_c() -> list[dict]:
    out = []
    for f in sorted((ROOT / "legacy/v1_data/sample_pdfs/edge_cases").glob("*.pdf")):
        a, _ = await run_analysis(f, new_analysis(f.name), EventSink())
        out.append({"file": f.name, "status": a.status, "error": a.error,
                    "claims": a.summary.total_claims if a.summary else 0,
                    "verdicts": a.summary.verdict_counts if a.summary else None,
                    "company_resolved": a.company.resolved if a.company else None})
    return out


async def part_d() -> dict:
    """Ask identical questions 3x straight to the API (no cassette) and measure agreement."""
    eng = engine()
    stance = choice("Compare the company's claim with the external evidence. What is the evidence's stance?",
                    {"support": None, "contradict": None, "insufficient": None})
    states = [f"CLAIM: {s[1]}\nEVIDENCE: {e}" for s, e in [
        (STRESS[2], "BRSR FY2025 fatalities: 1."), (STRESS[7], "BRSR FY2025 renewable share: 30.6%."),
        (STRESS[8], "BRSR FY2025 renewable share: 30.6%."), (STRESS[5], "Scope 2 FY2020 88,576; FY2025 85,556 (-3.4%)."),
        (STRESS[19], "Only action: CPCB closure direction dated 2024-07-19 (FY2025)."),
        (STRESS[0], "Intensity FY2020 342.1, FY2025 294.8 (-13.8%)."),
        (STRESS[3], "CPCB closure direction 2024-07-19."), (STRESS[9], "3 regulator actions in FY2025."),
    ]]
    answers = []
    for s in states:
        runs = [await eng._call(s, {"stance": stance, "vague": noul("Is the claim vague?")}) for _ in range(3)]
        labels = [r["answers"]["stance"]["choice"] for r in runs]
        probs = [r["answers"]["stance"]["probabilities"][labels[0]] for r in runs]
        answers.append({"labels": labels, "p_spread": round(max(probs) - min(probs), 4)})
    agree = sum(len(set(a["labels"])) == 1 for a in answers)
    return {"questions": len(answers), "identical_label_all_3_runs": agree,
            "max_probability_spread": max(a["p_spread"] for a in answers), "detail": answers}


async def part_e() -> dict:
    with tempfile.TemporaryDirectory() as d:
        cold = JevEngine(cassette_dir=Path(d))
        t0 = time.time()
        a, _ = await run_analysis(ROOT / "data/reports/kaveri_threads_brsr_fy2025.pdf",
                                  new_analysis("kaveri (cold)"), EventSink(), jev=cold)
        return {"report": "kaveri_threads_brsr_fy2025.pdf (28 pages)", "seconds": round(time.time() - t0, 1),
                "jev_calls": cold.stats.calls, "jev_input_tokens": cold.stats.input_tokens,
                "approx_cost_usd_at_0.05_per_M_input": round(cold.stats.input_tokens / 1e6 * 0.05, 4),
                "status": a.status}


async def main() -> None:
    res = {}
    for name, fn in [("A_heldout_benchmark", part_a), ("B_handwritten_stress", part_b), ("C_bad_inputs", part_c),
                     ("D_engine_consistency", part_d), ("E_cold_run_cost", part_e)]:
        t = time.time()
        res[name] = await fn()
        print(f"== {name} ({time.time() - t:.0f}s)")
        r = res[name]
        if name.startswith("A"):
            print("  ", r["n"], r["overall"], "errors:", Counter((e["label"], e["pred"]) for e in r["errors"]))
        elif name.startswith("B"):
            print("  ", r["correct"], "/", r["n"])
            for row in r["rows"]:
                if not row["correct"]:
                    print("     MISS", row["id"], row["expected"], "->", row["predicted"], "|", row["stresses"])
        else:
            print("  ", json.dumps(r)[:600])
    OUT.write_text(json.dumps(res, indent=2))
    print("wrote", OUT)


if __name__ == "__main__":
    asyncio.run(main())
