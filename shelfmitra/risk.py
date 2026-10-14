"""Expiry risk for each batch on the shelf.

TabPFN is an in-context model: it is never trained here. On start-up it is
given a reference set of batch outcomes built from real pharmacy sales, and
it predicts each live batch against that context in one forward pass. The
straight-line rule a careful pharmacist would use is computed alongside and
passed in as a feature, so the model learns where the rule goes wrong.
If TabPFN is unavailable the rule is used on its own, and the UI says so.
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np

from .scenarios import CATEGORIES, FEATURES, item_features, load_sales, make_scenarios

_model = None
_engine = "rule"


def _load():
    global _model, _engine
    if _model is not None or os.environ.get("SHELFMITRA_RISK") == "rule":
        return
    try:
        from tabpfn import TabPFNClassifier
        ref = make_scenarios(load_sales(), int(os.environ.get("SHELFMITRA_CONTEXT", 400)), "2014-04-01", "2019-06-30", seed=7)
        m = TabPFNClassifier(device="cpu", n_estimators=4)
        m.fit(ref[FEATURES].to_numpy(), ref["at_risk"].to_numpy())
        _model, _engine = m, "tabpfn"
    except Exception as e:  # no token, no weights or no network: fall back honestly
        print("TabPFN unavailable, using the straight-line rule:", type(e).__name__, str(e)[:120])
        _model, _engine = None, "rule"


def engine() -> str:
    _load()
    return _engine


def return_cutoff(expiry: str, window_days: int) -> date:
    from datetime import timedelta
    return date.fromisoformat(expiry) - timedelta(days=window_days)


def score(batches: list[dict], histories: dict[str, list[float]], today: date | None = None) -> list[dict]:
    """Adds risk, expected leftover units, rupees at risk and an action to each batch."""
    _load()
    today = today or date.today()
    rows, out = [], []
    for b in batches:
        cutoff = return_cutoff(b["expiry"], b["return_window_days"])
        days = (cutoff - today).days
        hist = np.asarray(histories.get(b["product"], [0.0] * 120), dtype=float)
        # Classes outside the reference data are treated as steady sellers (the paracetamol group);
        # their own sales history still drives the prediction.
        cat = CATEGORIES.index(b["category"]) if b.get("category") in CATEGORIES else CATEGORIES.index("N02BE")
        f = item_features(hist[-90:], float(b["qty_on_hand"]), max(days, 1), today.month, cat)
        rows.append([f[k] for k in FEATURES])
        out.append({**b, "no_sales": float(hist.sum()) == 0.0, "return_cutoff": cutoff.isoformat(), "days_to_cutoff": days,
                    "vel30": round(f["vel30"], 2), "rule_left_frac": round(f["rule_left_frac"], 3)})
    if not out:
        return out
    X = np.asarray(rows)
    rule = np.clip(X[:, FEATURES.index("rule_left_frac")] + 0.1, 0, 1)
    p = _model.predict_proba(X)[:, 1] if _model is not None else rule
    for b, risk, r in zip(out, p, rule):
        expected_left = max(b["qty_on_hand"] - b["vel30"] * max(b["days_to_cutoff"], 0), 0.0)
        b["risk"] = round(float(risk), 3)
        b["rule_risk"] = round(float(r), 3)
        b["expected_left"] = round(expected_left, 1)
        b["rupees_at_risk"] = round(expected_left * (b.get("rate") or 0), 2)
        b["action"] = decide(b)
        b["engine"] = _engine
    return sorted(out, key=lambda b: (-b["rupees_at_risk"], -b["risk"]))


def decide(b: dict) -> str:
    """Code, not the model, picks the action from the numbers."""
    if b["days_to_cutoff"] < 0:
        return "window_closed"
    if b.get("no_sales"):
        return "need_sales"   # no history yet: say so instead of guessing
    if b["risk"] >= 0.6 and b["days_to_cutoff"] <= 45:
        return "return_now"
    if b["risk"] >= 0.6:
        return "stop_reorder"
    if b["risk"] >= 0.3:
        return "watch"
    return "ok"
