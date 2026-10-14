"""The shop's stock ledger in SQLite: batches, daily sales and decisions."""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date

DB = os.environ.get("SHELFMITRA_DB", "data/shop.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product TEXT NOT NULL, pack TEXT, batch TEXT NOT NULL, expiry TEXT NOT NULL,
  qty_received INTEGER NOT NULL, qty_on_hand INTEGER NOT NULL,
  rate REAL, mrp REAL, category TEXT,
  distributor TEXT, invoice_no TEXT, received TEXT NOT NULL,
  return_window_days INTEGER NOT NULL DEFAULT 90,
  status TEXT NOT NULL DEFAULT 'active',
  UNIQUE(product, batch)
);
CREATE TABLE IF NOT EXISTS sales (
  product TEXT NOT NULL, day TEXT NOT NULL, units REAL NOT NULL,
  PRIMARY KEY (product, day)
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, batch_id INTEGER,
  kind TEXT NOT NULL, detail TEXT
);
"""


@contextmanager
def db():
    os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def add_batch(con, **b) -> int:
    cur = con.execute(
        """INSERT INTO batches (product, pack, batch, expiry, qty_received, qty_on_hand, rate, mrp, category,
                                distributor, invoice_no, received, return_window_days)
           VALUES (:product, :pack, :batch, :expiry, :qty, :qty, :rate, :mrp, :category,
                   :distributor, :invoice_no, :received, :return_window_days)
           ON CONFLICT(product, batch) DO UPDATE SET qty_on_hand = qty_on_hand + excluded.qty_on_hand,
                                                     qty_received = qty_received + excluded.qty_received
           RETURNING id""",
        {"pack": None, "rate": None, "mrp": None, "category": None, "distributor": None,
         "invoice_no": None, "received": date.today().isoformat(), "return_window_days": 90} | b,
    )
    return cur.fetchone()[0]


def log(con, kind: str, batch_id: int | None = None, **detail):
    con.execute("INSERT INTO events (at, batch_id, kind, detail) VALUES (datetime('now'), ?, ?, ?)",
                (batch_id, kind, json.dumps(detail, ensure_ascii=False)))


def batches(con, status: str | None = "active"):
    q = "SELECT * FROM batches" + (" WHERE status = ?" if status else "") + " ORDER BY expiry"
    return [dict(r) for r in con.execute(q, (status,) if status else ())]


def sales_history(con, product: str, until: str, days: int = 120) -> list[float]:
    rows = con.execute(
        "SELECT day, units FROM sales WHERE product = ? AND day <= ? AND day > date(?, ?) ORDER BY day",
        (product, until, until, f"-{days} days")).fetchall()
    by_day = {r["day"]: r["units"] for r in rows}
    from datetime import timedelta
    end = date.fromisoformat(until)
    return [float(by_day.get((end - timedelta(days=days - 1 - i)).isoformat(), 0.0)) for i in range(days)]
