"""Storage: one SQLite database per shop, plus an accounts database.

Each shop's stock lives in its own file (data/shops/<shop_id>.db), so one
shop's data can never leak into another's query. The active shop is held in a
context variable that the web request (or Temporal activity) sets.
"""
from __future__ import annotations

import contextvars
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta

DATA_DIR = os.environ.get("SHELFMITRA_DATA_DIR", "data")
DB = os.environ.get("SHELFMITRA_DB")  # tests may pin a single file
current_shop: contextvars.ContextVar[str] = contextvars.ContextVar("current_shop", default="demo")

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product TEXT NOT NULL, pack TEXT, batch TEXT NOT NULL, expiry TEXT NOT NULL,
  qty_received INTEGER NOT NULL, qty_on_hand INTEGER NOT NULL,
  rate REAL, mrp REAL, category TEXT, composition TEXT,
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


def shop_db_path(shop: str | None = None) -> str:
    if DB:
        return DB
    shop = shop or current_shop.get()
    if not re.fullmatch(r"[a-z0-9_-]{1,40}", shop):
        raise ValueError("bad shop id")
    return os.path.join(DATA_DIR, "shops", f"{shop}.db")


@contextmanager
def db(shop: str | None = None):
    path = shop_db_path(shop)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def add_batch(con, **b) -> int:
    cur = con.execute(
        """INSERT INTO batches (product, pack, batch, expiry, qty_received, qty_on_hand, rate, mrp, category, composition,
                                distributor, invoice_no, received, return_window_days)
           VALUES (:product, :pack, :batch, :expiry, :qty, :qty, :rate, :mrp, :category, :composition,
                   :distributor, :invoice_no, :received, :return_window_days)
           ON CONFLICT(product, batch) DO UPDATE SET qty_on_hand = qty_on_hand + excluded.qty_on_hand,
                                                     qty_received = qty_received + excluded.qty_received
           RETURNING id""",
        {"pack": None, "rate": None, "mrp": None, "category": None, "composition": None, "distributor": None,
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
    end = date.fromisoformat(until)
    return [float(by_day.get((end - timedelta(days=days - 1 - i)).isoformat(), 0.0)) for i in range(days)]
