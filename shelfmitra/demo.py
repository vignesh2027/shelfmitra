"""Demo shop: Lakshmi Medicals, with sales histories taken from real pharmacy data.

Each demo product is mapped to the drug category it belongs to in the public
pharmacy sales dataset, and its daily sales are that category's real sales
(scaled to one brand's share), shifted to end today. Stock and expiry dates
are set so the shop has a realistic mix of safe and at-risk batches.
"""
from __future__ import annotations

import os
from datetime import date, timedelta

from . import store
from .scenarios import load_sales

# product, pack, batch, months to expiry, qty on hand, rate, mrp, category, share of category, distributor
PRODUCTS = [
    ("DOLO 650 TAB", "15'S", "D2241", 17, 40, 23.10, 33.60, "N02BE", 0.30, "Sri Murugan Pharma"),
    ("CROCIN ADVANCE TAB", "15'S", "CR8812", 6, 60, 19.80, 27.50, "N02BE", 0.08, "Sri Murugan Pharma"),
    ("ALLEGRA 120MG TAB", "10'S", "AL6B19", 5, 20, 171.50, 231.00, "R06", 0.25, "Sri Murugan Pharma"),
    ("CETIRIZINE 10MG TAB", "10'S", "CTZ7712", 4, 50, 13.60, 18.90, "R06", 0.30, "Sri Murugan Pharma"),
    ("MONTAIR LC TAB", "10'S", "MLC5527", 7, 15, 168.40, 226.90, "R03", 0.20, "Balaji Medical Agencies"),
    ("ASTHALIN INHALER", "200MD", "AS3390", 4, 12, 118.00, 158.00, "R03", 0.06, "Balaji Medical Agencies"),
    ("COMBIFLAM TAB", "20'S", "CF2208", 9, 25, 35.30, 48.00, "M01AE", 0.35, "Sri Murugan Pharma"),
    ("BRUFEN 400 TAB", "15'S", "BR4471", 5, 45, 12.40, 17.20, "M01AE", 0.10, "Sri Murugan Pharma"),
    ("VOVERAN 50 TAB", "10'S", "VV5020", 8, 30, 27.90, 38.50, "M01AB", 0.30, "Balaji Medical Agencies"),
    ("ECOSPRIN 75 TAB", "14'S", "EC7519", 11, 35, 4.10, 5.60, "N02BA", 0.40, "Balaji Medical Agencies"),
    ("ALPRAX 0.25 TAB", "15'S", "AX2508", 6, 20, 32.60, 44.80, "N05B", 0.15, "Balaji Medical Agencies"),
    ("ZOLFRESH 5 TAB", "10'S", "ZF5106", 5, 18, 96.20, 132.00, "N05C", 0.50, "Sri Murugan Pharma"),
]


def seed() -> list[dict]:
    if os.path.exists(store.DB):
        os.remove(store.DB)
    sales = load_sales()
    tail = sales.iloc[-120:]          # the last 120 real days, shifted to end today
    today = date.today()
    out = []
    with store.db() as con:
        for name, pack, batch, months, qty, rate, mrp, cat, share, dist in PRODUCTS:
            expiry = (today.replace(day=1) + timedelta(days=32 * months)).replace(day=1) - timedelta(days=1)
            bid = store.add_batch(con, product=name, pack=pack, batch=batch, expiry=expiry.isoformat(), qty=qty,
                                  rate=rate, mrp=mrp, category=cat, distributor=dist, invoice_no="DEMO",
                                  received=(today - timedelta(days=60)).isoformat(), return_window_days=90)
            for i, units in enumerate(tail[cat].to_numpy()):
                d = today - timedelta(days=len(tail) - 1 - i)
                con.execute("INSERT OR REPLACE INTO sales VALUES (?, ?, ?)", (name, d.isoformat(), round(float(units) * share, 2)))
            store.log(con, "received", bid, invoice="DEMO", qty=qty)
            out.append(dict(con.execute("SELECT * FROM batches WHERE id = ?", (bid,)).fetchone()))
    return out
