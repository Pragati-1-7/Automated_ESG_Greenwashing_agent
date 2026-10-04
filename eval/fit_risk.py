"""
eval/fit_risk.py

Fits the risk-score weights (app/agents/risk.py) by logistic regression on the
benchmark TRAIN split, so the 0-100 score is learned, not hand-tuned.

Target: 1 if the case is greenwashing (label CONTRADICT, or vague cheap talk),
else 0. Features: the decision-engine outputs recorded in
data/benchmark/predictions_full_system.jsonl. Reports test-split AUC.

    python -m eval.fit_risk
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from app.agents.risk import FEATURES, WEIGHTS_PATH
from app.core.config import ROOT

PRED = ROOT / "data" / "benchmark" / "predictions_full_system.jsonl"


def target(p: dict) -> int:
    return int(p["label"] == "CONTRADICT" or p["gw_type"] == "vague_claim")


def main() -> None:
    preds = [json.loads(l) for l in PRED.read_text().splitlines() if l.strip()]
    tr = [p for p in preds if p["split"] == "train"]
    te = [p for p in preds if p["split"] == "test"]
    X = lambda ps: np.array([[p["features"][f] for f in FEATURES] for p in ps])  # noqa: E731
    y = lambda ps: np.array([target(p) for p in ps])  # noqa: E731
    model = LogisticRegression(C=1.0, max_iter=2000).fit(X(tr), y(tr))
    auc_tr = roc_auc_score(y(tr), model.predict_proba(X(tr))[:, 1])
    auc_te = roc_auc_score(y(te), model.predict_proba(X(te))[:, 1])
    weights = {"bias": float(model.intercept_[0]), **{f: float(w) for f, w in zip(FEATURES, model.coef_[0])}}
    WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    WEIGHTS_PATH.write_text(json.dumps({
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "method": "logistic regression (L2, C=1)",
        "train_n": len(tr), "test_n": len(te), "auc_train": round(auc_tr, 3), "auc_test": round(auc_te, 3),
        "target": "label == CONTRADICT or gw_type == vague_claim", "weights": weights}, indent=2))
    print(json.dumps(weights, indent=2))
    print(f"AUC train {auc_tr:.3f}  test {auc_te:.3f} -> {WEIGHTS_PATH}")


if __name__ == "__main__":
    main()
