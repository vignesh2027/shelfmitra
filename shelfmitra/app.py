"""ShelfMitra web app: FastAPI backend plus the dashboard in web/."""
from __future__ import annotations

import os
import re
import urllib.parse
from datetime import date

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import invoice, messages, risk, store

WEB = os.path.join(os.path.dirname(__file__), "..", "web")
TEMPORAL = os.environ.get("TEMPORAL_ADDRESS")  # unset = run without Temporal
DAY_SECONDS = float(os.environ.get("SHELFMITRA_DAY_SECONDS", "86400"))
SHOP = os.environ.get("SHELFMITRA_SHOP", "Lakshmi Medicals")

app = FastAPI(title="ShelfMitra")
_temporal = None


async def temporal():
    global _temporal
    if not TEMPORAL:
        return None
    if _temporal is None:
        from temporalio.client import Client
        _temporal = await Client.connect(TEMPORAL)
    return _temporal


async def start_watch(batch: dict, days_to_cutoff: int):
    client = await temporal()
    if client is None or days_to_cutoff <= 0:
        return
    from temporalio.common import WorkflowIDReusePolicy
    from .workflows import TASK_QUEUE, BatchWatch, WatchInput
    try:
        await client.start_workflow(BatchWatch.run, WatchInput(batch["id"], days_to_cutoff, DAY_SECONDS),
                                    id=f"batch-{batch['id']}", task_queue=TASK_QUEUE,
                                    id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY)
    except Exception as e:  # already running is fine
        if "already started" not in str(e).lower():
            raise


def scored(con):
    bs = store.batches(con)
    hist = {b["product"]: store.sales_history(con, b["product"], date.today().isoformat()) for b in bs}
    return risk.score(bs, hist)


@app.get("/api/dashboard")
def dashboard():
    with store.db() as con:
        rows = scored(con)
        ev = [dict(r) for r in con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 25")]
    at_risk = [b for b in rows if b["action"] in ("return_now", "stop_reorder")]
    return {
        "shop": SHOP,
        "engine": risk.engine(),
        "temporal": bool(TEMPORAL),
        "batches": rows,
        "totals": {
            "batches": len(rows),
            "at_risk": len(at_risk),
            "rupees_at_risk": round(sum(b["rupees_at_risk"] for b in at_risk), 2),
            "return_now": sum(b["action"] == "return_now" for b in rows),
        },
        "events": ev,
    }


@app.post("/api/invoice")
async def read_invoice(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 8_000_000:
        raise HTTPException(413, "Photo too large (max 8 MB)")
    return invoice.read_invoice(data, mime=file.content_type or "image/jpeg")


class ConfirmLine(BaseModel):
    product: str
    pack: str | None = None
    batch: str
    expiry: str
    qty: int
    rate: float | None = None
    mrp: float | None = None
    category: str | None = None


class Confirm(BaseModel):
    distributor: str | None = None
    invoice_no: str | None = None
    return_policy: str | None = None
    lines: list[ConfirmLine]


def window_from_policy(text: str | None) -> int:
    m = re.search(r"(\d{2,3})\s*days?", text or "", re.I)
    return int(m.group(1)) if m else 90


@app.post("/api/invoice/confirm")
async def confirm_invoice(c: Confirm):
    window = window_from_policy(c.return_policy)
    saved = []
    with store.db() as con:
        for l in c.lines:
            bid = store.add_batch(con, product=l.product, pack=l.pack, batch=l.batch, expiry=l.expiry, qty=l.qty,
                                  rate=l.rate, mrp=l.mrp, category=l.category, distributor=c.distributor,
                                  invoice_no=c.invoice_no, return_window_days=window)
            store.log(con, "received", bid, invoice=c.invoice_no, qty=l.qty)
            saved.append(dict(con.execute("SELECT * FROM batches WHERE id = ?", (bid,)).fetchone()))
    for b in saved:
        await start_watch(b, (risk.return_cutoff(b["expiry"], window) - date.today()).days)
    return {"saved": len(saved), "return_window_days": window}


class MessageReq(BaseModel):
    batch_ids: list[int]
    lang: str = "en"
    phone: str | None = None


@app.post("/api/message")
def message(m: MessageReq):
    if m.lang not in messages.LANGS:
        raise HTTPException(400, "lang must be en, ta or hi")
    with store.db() as con:
        rows = [b for b in scored(con) if b["id"] in m.batch_ids]
    if not rows:
        raise HTTPException(404, "no such batches")
    distributor = rows[0]["distributor"] or "Sir"
    text = messages.return_request(m.lang, distributor, SHOP, rows)
    phone = re.sub(r"\D", "", m.phone or "")
    wa = f"https://wa.me/{phone}?text={urllib.parse.quote(text)}" if phone else f"https://wa.me/?text={urllib.parse.quote(text)}"
    return {"text": text, "whatsapp": wa}


class Decision(BaseModel):
    batch_id: int
    decision: str  # returned, sold, keep


@app.post("/api/decision")
async def decision(d: Decision):
    if d.decision not in ("returned", "sold", "keep"):
        raise HTTPException(400, "decision must be returned, sold or keep")
    client = await temporal()
    if client:
        from .workflows import BatchWatch
        try:
            await client.get_workflow_handle(f"batch-{d.batch_id}").signal(BatchWatch.decide, d.decision)
            return {"via": "temporal"}
        except Exception:
            pass
    with store.db() as con:
        con.execute("UPDATE batches SET status = ? WHERE id = ?", (d.decision, d.batch_id))
        store.log(con, "decision", d.batch_id, decision=d.decision)
    return {"via": "direct"}


@app.get("/api/workflows")
async def workflows():
    client = await temporal()
    if client is None:
        return {"temporal": False, "workflows": []}
    from .workflows import BatchWatch
    out = []
    with store.db() as con:
        ids = [r[0] for r in con.execute("SELECT id FROM batches")]
    for bid in ids:
        try:
            h = client.get_workflow_handle(f"batch-{bid}")
            desc = await h.describe()
            st = await h.query(BatchWatch.status) if desc.status.name == "RUNNING" else {"stage": desc.status.name.lower()}
            out.append({"batch_id": bid, "status": desc.status.name, **st})
        except Exception:
            continue
    return {"temporal": True, "workflows": out}


@app.post("/api/demo/reset")
async def demo_reset():
    from .demo import seed
    batches = seed()
    for b in batches:
        await start_watch(b, (risk.return_cutoff(b["expiry"], b["return_window_days"]) - date.today()).days)
    return {"seeded": len(batches)}


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


app.mount("/static", StaticFiles(directory=WEB), name="static")


class Ask(BaseModel):
    question: str


@app.post("/api/ask")
async def ask(a: Ask):
    q = a.question.strip()[:500]
    if not q:
        raise HTTPException(400, "empty question")
    from . import agent
    import anyio
    return await anyio.to_thread.run_sync(agent.ask, q)
