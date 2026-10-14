"""Builds expiry-risk scenarios from real pharmacy sales.

Source: daily sales of 8 ATC drug categories from one pharmacy, 2014-2019
(Kaggle "pharma-sales-data", CC BY-NC 4.0). Each scenario is a batch that
arrives on a real day with a known number of days until the distributor's
return cutoff. The label comes from what actually sold afterwards, so no
outcome is invented: the only simulated parts are the batch size and the
brand's share of its category.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIES = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]
CATEGORY_NAMES = {
    "M01AB": "Anti-inflammatory (diclofenac type)",
    "M01AE": "Anti-inflammatory (ibuprofen type)",
    "N02BA": "Aspirin-type pain relief",
    "N02BE": "Paracetamol-type pain relief",
    "N05B": "Anxiolytics",
    "N05C": "Sleep medicines",
    "R03": "Asthma and COPD",
    "R06": "Antihistamines (allergy)",
}

FEATURES = [
    "qty", "days_to_cutoff", "vel7", "vel30", "vel90", "cv30", "trend",
    "cover_days", "zero_days30", "month", "category_idx", "rule_left_frac",
]


def load_sales(path: str = "data/raw/salesdaily.csv") -> pd.DataFrame:
    d = pd.read_csv(path)
    d["date"] = pd.to_datetime(d["datum"], format="%m/%d/%Y")
    d = d.set_index("date")[CATEGORIES].clip(lower=0)
    # Reindex to a full calendar so missing days count as zero sales.
    return d.reindex(pd.date_range(d.index.min(), d.index.max(), freq="D"), fill_value=0.0)


def item_features(history: np.ndarray, qty: float, days_to_cutoff: int, month: int, category_idx: int) -> dict:
    """Features a pharmacist's own records give them on the day a batch arrives."""
    last7, last30, last90 = history[-7:], history[-30:], history[-90:]
    vel7, vel30, vel90 = last7.mean(), last30.mean(), last90.mean()
    eps = 1e-6
    return {
        "qty": qty,
        "days_to_cutoff": days_to_cutoff,
        "vel7": vel7,
        "vel30": vel30,
        "vel90": vel90,
        "cv30": last30.std() / (vel30 + eps),
        "trend": (vel30 + eps) / (vel90 + eps),
        "cover_days": qty / (vel30 + eps),
        "zero_days30": float((last30 == 0).sum()),
        "month": month,
        "category_idx": category_idx,
        # The pharmacist's straight-line estimate, given to the model so it learns corrections.
        "rule_left_frac": max(qty - vel30 * days_to_cutoff, 0.0) / max(qty, eps),
    }


def make_scenarios(sales: pd.DataFrame, n: int, start: str, end: str, seed: int = 0) -> pd.DataFrame:
    """n batch scenarios whose arrival day falls in [start, end)."""
    rng = np.random.default_rng(seed)
    days = sales.index
    lo, hi = days.get_loc(pd.Timestamp(start)), days.get_loc(pd.Timestamp(end))
    rows = []
    while len(rows) < n:
        t0 = int(rng.integers(max(lo, 90), hi))
        horizon = int(rng.choice([30, 45, 60, 90, 120, 180]))
        if t0 + horizon >= len(days):
            continue
        ci = int(rng.integers(len(CATEGORIES)))
        share = float(rng.uniform(0.15, 0.7))  # this brand's share of the category
        item = sales.iloc[:, ci].to_numpy() * share
        past, future = item[t0 - 90:t0], item[t0:t0 + horizon]
        vel30 = past[-30:].mean()
        if vel30 <= 0.05:
            continue
        # Batch sizes around what straight-line demand would need, from half to double.
        qty = float(np.round(vel30 * horizon * rng.uniform(0.5, 2.0)))
        if qty < 1:
            continue
        sold = float(future.sum())
        f = item_features(past, qty, horizon, days[t0].month, ci)
        f.update({
            "date": days[t0].date().isoformat(),
            "category": CATEGORIES[ci],
            "sold_by_cutoff": round(sold, 2),
            "left_at_cutoff": round(max(qty - sold, 0.0), 2),
            # At risk: more than 10% of the batch is still on the shelf at the cutoff.
            "at_risk": int(qty - sold > 0.10 * qty),
        })
        rows.append(f)
    return pd.DataFrame(rows)
