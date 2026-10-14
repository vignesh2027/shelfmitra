"""Reads a distributor invoice photo into stock batches.

The model reads; code decides. The open vision model only transcribes the
table. Every field is then checked in plain code, and any line that fails a
check is marked for the pharmacist to confirm instead of being guessed.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import asdict, dataclass, field
from datetime import date

from .llm import chat, parse_json

PROMPT = """You are reading a photo of an Indian pharmaceutical distributor's tax invoice.
Copy the item table exactly as printed. Do not guess or correct anything; if a cell is unreadable, use null.
Return JSON only, in this shape:
{"distributor": "...", "invoice_no": "...", "invoice_date": "DD/MM/YYYY",
 "return_policy": "any printed note about expiry returns, or null",
 "items": [{"product": "...", "pack": "...", "batch": "...", "expiry": "MM/YY as printed",
            "qty": number, "free": number, "mrp": number, "rate": number, "amount": number}]}"""

BATCH_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-/]{2,14}$")


@dataclass
class Line:
    product: str
    pack: str | None
    batch: str | None
    expiry: str | None          # ISO date: last day of the printed expiry month
    qty: int | None
    free: int
    mrp: float | None
    rate: float | None
    amount: float | None
    issues: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return bool(self.issues)


def parse_expiry(text: str | None) -> date | None:
    """'03/27', '3/2027', 'MAR-27' -> last day of that month (medicines expire at month end)."""
    if not text:
        return None
    t = str(text).strip().upper().replace("-", "/").replace(".", "/")
    months = {m.upper(): i for i, m in enumerate(calendar.month_abbr) if m}
    m = re.fullmatch(r"(\d{1,2})/(\d{2}|\d{4})", t) or re.fullmatch(r"([A-Z]{3})/?(\d{2}|\d{4})", t)
    if not m:
        return None
    mon = int(m.group(1)) if m.group(1).isdigit() else months.get(m.group(1))
    year = int(m.group(2))
    year = year + 2000 if year < 100 else year
    if not mon or not 1 <= mon <= 12 or not 2020 <= year <= 2040:
        return None
    return date(year, mon, calendar.monthrange(year, mon)[1])


def _num(v):
    try:
        return float(str(v).replace(",", "")) if v not in (None, "") else None
    except ValueError:
        return None


def validate(raw: dict) -> Line:
    issues = []
    product = (raw.get("product") or "").strip()
    if not product:
        issues.append("product name missing")
    batch = (raw.get("batch") or "").strip().upper() or None
    if not batch or not BATCH_RE.match(batch):
        issues.append(f"batch '{raw.get('batch')}' does not look like a batch number")
    exp = parse_expiry(raw.get("expiry"))
    if not exp:
        issues.append(f"expiry '{raw.get('expiry')}' is not a valid MM/YY date")
    qty, free = _num(raw.get("qty")), _num(raw.get("free")) or 0
    if qty is None or qty <= 0 or qty != int(qty):
        issues.append(f"quantity '{raw.get('qty')}' is not a whole number")
    mrp, rate, amount = _num(raw.get("mrp")), _num(raw.get("rate")), _num(raw.get("amount"))
    if rate and mrp and rate > mrp:
        issues.append("purchase rate is higher than MRP")
    if qty and rate and amount and abs(qty * rate - amount) > max(1.0, 0.01 * amount):
        issues.append(f"qty x rate = {qty * rate:.2f} but amount says {amount:.2f}")
    return Line(product=product, pack=raw.get("pack"), batch=batch, expiry=exp.isoformat() if exp else None,
                qty=int(qty) if qty else None, free=int(free), mrp=mrp, rate=rate, amount=amount, issues=issues)


def read_invoice(image: bytes, mime: str = "image/jpeg", backend: str | None = None) -> dict:
    data = parse_json(chat(PROMPT, image=image, mime=mime, json_mode=False, max_tokens=2500, backend=backend))
    lines = [validate(it) for it in data.get("items", [])]
    return {
        "distributor": data.get("distributor"),
        "invoice_no": data.get("invoice_no"),
        "invoice_date": data.get("invoice_date"),
        "return_policy": data.get("return_policy"),
        "lines": [asdict(l) | {"needs_review": l.needs_review} for l in lines],
        "ok": sum(not l.needs_review for l in lines),
        "review": sum(l.needs_review for l in lines),
    }
