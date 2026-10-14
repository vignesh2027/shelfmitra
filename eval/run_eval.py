"""Backtest: which method spots expiring stock best when a shop has little history?

Train on scenarios from 2014-2017, test on 2018-2019 (no time leakage).
Each method is trained on only n = 50, 100, 200 or 500 batches, repeated
over 5 seeds. Writes eval/results.json and eval/results.md.
Usage: python eval/run_eval.py [--no-tabpfn]
"""
import json
import pathlib
import sys
import time

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from shelfmitra.scenarios import FEATURES, load_sales, make_scenarios  # noqa: E402

OUT = pathlib.Path(__file__).parent
SIZES = [50, 100, 200, 500]
SEEDS = [0, 1, 2, 3, 4]
USE_TABPFN = "--no-tabpfn" not in sys.argv


def straight_line_rule(X):
    """What a careful pharmacist does: will last month's pace clear the batch in time?"""
    qty, days, vel30 = X[:, FEATURES.index("qty")], X[:, FEATURES.index("days_to_cutoff")], X[:, FEATURES.index("vel30")]
    expected = vel30 * days
    # Score = share of the batch expected to be left over (higher = riskier).
    return np.clip((qty - expected) / np.maximum(qty, 1e-6) + 0.1, 0, 1)


def units_rescued(score, left, qty, top_frac=0.2):
    """Share of all leftover units found if the owner acts on the top 20% of batches,
    ranked by expected units at risk (risk score x batch size), the same for every method."""
    k = max(1, int(len(score) * top_frac))
    top = np.argsort(-(score * qty))[:k]
    return float(left[top].sum() / max(left.sum(), 1e-6))


def models():
    out = {
        "Logistic regression": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
        "Gradient boosting": lambda: HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06),
    }
    if USE_TABPFN:
        from tabpfn import TabPFNClassifier
        out["TabPFN"] = lambda: TabPFNClassifier(device="cpu", n_estimators=4)
    return out


def main():
    sales = load_sales()
    pool = make_scenarios(sales, 3000, "2014-04-01", "2017-12-31", seed=11)
    test = make_scenarios(sales, 1200, "2018-01-01", "2019-06-30", seed=99)
    Xte, yte, left = test[FEATURES].to_numpy(), test["at_risk"].to_numpy(), test["left_at_cutoff"].to_numpy()
    qty = test["qty"].to_numpy()
    print(f"pool {len(pool)} (at risk {pool.at_risk.mean():.0%}), test {len(test)} (at risk {yte.mean():.0%})")

    results = {"test_size": len(test), "test_at_risk_rate": round(float(yte.mean()), 3), "rows": []}
    s = straight_line_rule(Xte)
    results["rows"].append({"method": "Straight-line rule", "n": 0,
                            "auc": round(roc_auc_score(yte, s), 3), "f1": round(f1_score(yte, s > 0.1), 3),
                            "rescued": round(units_rescued(s, left, qty), 3), "fit_s": 0.0})
    for name, make in models().items():
        for n in SIZES:
            aucs, f1s, res, secs = [], [], [], []
            for seed in SEEDS:
                tr = pool.sample(n, random_state=seed)
                if tr.at_risk.nunique() < 2:
                    continue
                m = make()
                t = time.time()
                m.fit(tr[FEATURES].to_numpy(), tr["at_risk"].to_numpy())
                p = m.predict_proba(Xte)[:, 1]
                secs.append(time.time() - t)
                aucs.append(roc_auc_score(yte, p)); f1s.append(f1_score(yte, p > 0.5)); res.append(units_rescued(p, left, qty))
            row = {"method": name, "n": n, "auc": round(float(np.mean(aucs)), 3), "auc_sd": round(float(np.std(aucs)), 3),
                   "f1": round(float(np.mean(f1s)), 3), "rescued": round(float(np.mean(res)), 3), "fit_s": round(float(np.mean(secs)), 2)}
            results["rows"].append(row)
            print(row)

    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    lines = ["| Method | Training batches | ROC-AUC | F1 | Leftover units found in top 20% |", "| --- | ---: | ---: | ---: | ---: |"]
    for r in results["rows"]:
        lines.append(f"| {r['method']} | {r['n'] or 'none (rule)'} | {r['auc']:.3f} | {r['f1']:.3f} | {r['rescued']:.0%} |")
    (OUT / "results.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
