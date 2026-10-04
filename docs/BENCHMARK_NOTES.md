# Benchmark notes (honest record)

## First full run (before fixes): 187/200 correct (0.935), test split 58/60 (0.967)

| Case | Split | Label | Predicted | Cause | Fix applied |
|---|---|---|---|---|---|
| BM-022, BM-066, BM-082 | train, train, test | ALIGN | CONTRADICT | Facility name "Sundargarh Bauxite Mine" not parsed (capital "Mine", unknown "bauxite"), so alerts near a different facility were used | Case-insensitive facility suffixes, more facility types |
| BM-108 | train | CONTRADICT | INSUFFICIENT | "lower than in FY2019-20" not recognised as a baseline, so the claim period became FY2020 | Baseline patterns "than (in)" |
| BM-103, BM-151 | train | CONTRADICT | ALIGN | Unit errors (ML vs kL, TJ vs GJ): numbers matched, units ignored | Unit-conversion step in the calculator before comparison |
| BM-112 | train | ALIGN | CONTRADICT | Claim referenced revenue growth that the evidence did not show | Turnover series added to every BRSR evidence item |
| BM-113 | train | ALIGN | INSUFFICIENT | "While X rose, Y fell" not split into two sub-claims | Clause splitter handles while/whereas/although |
| BM-062, BM-073 | train | INSUFFICIENT | CONTRADICT | Evidence about a different quantity (water withdrawn vs replenished; own wages vs supplier wages) judged relevant | Relevance question names quantity mismatches explicitly |
| BM-069, BM-140, BM-158 | train, test, train | ALIGN | CONTRADICT | Regulator show-cause "for stack exceedances" or an OCEMS event read as contradicting "clean record" or "zero exceedances" claims. Partly label noise in the generated world | Same relevance clarification ("an exceedance is not a regulator's action") |

## After fixes: 196/200 (0.98), test split 60/60

Still wrong (all in the train split):

| Case | Label | Predicted | Why |
|---|---|---|---|
| BM-069 | ALIGN | CONTRADICT | The world has a CPCB show-cause "for stack emission exceedances" in the same year as an empty OCEMS log; the engine sides with the regulator. Arguably label noise |
| BM-158 | ALIGN | CONTRADICT | An OCEMS exceedance counted against "no environmental action initiated". Debatable |
| BM-073 | INSUFFICIENT_EVIDENCE | CONTRADICT | The company's own wage share still treated as relevant to a claim about supplier units |
| BM-113 | ALIGN | CONTRADICT | Two-part claim (absolute up, intensity down) now split, but one part is still judged against the other's figures |

Because these fixes were made after looking at errors that include test cases, the test-split score is optimistic. A truly held-out evaluation would need a fresh benchmark generated with a different seed and not inspected before scoring.

Remaining errors on all 200 cases: see `data/benchmark/predictions_full_system.jsonl` (rows where `pred != label`).
