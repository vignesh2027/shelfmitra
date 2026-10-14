"""ShelfMitra web app: FastAPI backend plus the dashboard in web/.

Visitors without an account see the public demo shop. Signed-in owners see
only their own shop: every request sets the active shop from a signed cookie,
and each shop's data lives in its own database file.
"""
from __future__ import annotations

import csv
import io
import os
import re
import time
import urllib.parse
from collections import defaultdict, deque
from datetime import date

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, invoice, messages, risk, store

WEB = os.path.join(os.path.dirname(__file__), "..", "web")
TEMPORAL = os.environ.get("TEMPORAL_ADDRESS")  # unset = run without Temporal
DAY_SECONDS = float(os.environ.get("SHELFMITRA_DAY_SECONDS", "86400"))
DEMO_NAME = os.environ.get("SHELFMITRA_SHOP", "Lakshmi Medicals")
PUBLIC_DEMO = os.environ.get("SHELFMITRA_PUBLIC_DEMO") == "1"
SECURE_COOKIE = os.environ.get("SHELFMITRA_SECURE_COOKIE", "1" if PUBLIC_DEMO else "0") == "1"
# "none" lets the session work inside the Hugging Face Spaces iframe (needs a secure cookie).
SAMESITE = os.environ.get("SHELFMITRA_COOKIE_SAMESITE", "lax")

app = FastAPI(title="ShelfMitra", docs_url=None, redoc_url=None)
_temporal = None

# Per-visitor limits on the endpoints that spend model or API credits.
LIMITS = {"ask": (15, 3600), "invoice": (8, 3600), "message": (15, 3600), "reset": (3, 3600),
          "auth": (12, 900), "sales": (10, 3600)}
_hits: dict = defaultdict(deque)


def limit(request: Request, kind: str):
    if not PUBLIC_DEMO and kind != "auth":
        return
    n, window = LIMITS[kind]
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "?")).split(",")[0].strip()
    q, now = _hits[(kind, ip)], time.time()
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= n:
        raise HTTPException(429, f"Too many requests ({n} per {window // 60} minutes). Please wait a little.")
    q.append(now)


@app.middleware("http")
async def shop_context(request: Request, call_next):
    shop_id = auth.read_token(request.cookies.get(auth.COOKIE)) or "demo"
    request.state.shop = shop_id
    token = store.current_shop.set(shop_id)
    try:
        resp = await call_next(request)
    finally:
        store.current_shop.reset(token)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "same-origin"
    return resp


@app.on_event("startup")
async def seed_if_empty():
    with store.db("demo") as con:
        empty = con.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0
    if empty:
        await demo_reset_impl()


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------- accounts
class SignUp(BaseModel):
    email: str
    password: str
    shop_name: str
    area: str | None = None


class LogIn(BaseModel):
    email: str
    password: str


def _set_session(resp: Response, shop_id: str):
    resp.set_cookie(auth.COOKIE, auth.make_token(shop_id), max_age=auth.MAX_AGE, httponly=True,
                    samesite=SAMESITE, secure=SECURE_COOKIE or SAMESITE == "none")


@app.post("/api/auth/signup")
def signup(s: SignUp, request: Request, response: Response):
    limit(request, "auth")
    try:
        shop = auth.signup(s.email, s.password, s.shop_name, s.area)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _set_session(response, shop["id"])
    return {"shop": shop}


@app.post("/api/auth/login")
def login(l: LogIn, request: Request, response: Response):
    limit(request, "auth")
    try:
        shop = auth.login(l.email, l.password)
    except ValueError as e:
        raise HTTPException(401, str(e))
    _set_session(response, shop["id"])
    return {"shop": shop}


@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(auth.COOKIE, samesite=SAMESITE, secure=SECURE_COOKIE or SAMESITE == "none", httponly=True)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    if request.state.shop == "demo":
        return {"demo": True, "name": DEMO_NAME, "area": "Mylapore, Chennai"}
    s = auth.shop(request.state.shop) or {}
    return {"demo": False, "name": s.get("name"), "email": s.get("email"), "area": s.get("area")}


def shop_name(request: Request) -> str:
    return DEMO_NAME if request.state.shop == "demo" else (auth.shop(request.state.shop) or {}).get("name", "My shop")


# ---------------------------------------------------------------- temporal
async def temporal():
    global _temporal
    if not TEMPORAL:
        return None
    if _temporal is None:
        from temporalio.client import Client
        _temporal = await Client.connect(TEMPORAL)
    return _temporal


def wf_id(shop: str, batch_id: int) -> str:
    return f"{shop}-batch-{batch_id}"


async def start_watch(shop: str, batch: dict, days_to_cutoff: int):
    client = await temporal()
    if client is None or days_to_cutoff <= 0:
        return
    from temporalio.common import WorkflowIDReusePolicy
    from .workflows import TASK_QUEUE, BatchWatch, WatchInput
    try:
        await client.start_workflow(BatchWatch.run, WatchInput(batch["id"], days_to_cutoff, DAY_SECONDS, shop),
                                    id=wf_id(shop, batch["id"]), task_queue=TASK_QUEUE,
                                    id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE_FAILED_ONLY)
    except Exception as e:  # already running is fine
        if "already" not in str(e).lower():
            raise


# ---------------------------------------------------------------- dashboard
def scored(con):
    bs = store.batches(con)
    hist = {b["product"]: store.sales_history(con, b["product"], date.today().isoformat()) for b in bs}
    return risk.score(bs, hist)


@app.get("/api/dashboard")
def dashboard(request: Request):
    with store.db() as con:
        rows = scored(con)
        ev = [dict(r) for r in con.execute("SELECT * FROM events ORDER BY id DESC LIMIT 25")]
    at_risk = [b for b in rows if b["action"] in ("return_now", "stop_reorder")]
    return {
        "shop": shop_name(request),
        "demo": request.state.shop == "demo",
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


# ---------------------------------------------------------------- invoices
@app.post("/api/invoice")
async def read_invoice(request: Request, file: UploadFile = File(...)):
    limit(request, "invoice")
    data = await file.read()
    if len(data) > 8_000_000:
        raise HTTPException(413, "Photo too large (max 8 MB)")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(415, "Please upload a photo (JPEG or PNG)")
    import anyio
    return await anyio.to_thread.run_sync(lambda: invoice.read_invoice(data, mime=file.content_type))


class ConfirmLine(BaseModel):
    product: str
    pack: str | None = None
    batch: str
    expiry: str
    qty: int
    rate: float | None = None
    mrp: float | None = None
    category: str | None = None
    composition: str | None = None


class Confirm(BaseModel):
    distributor: str | None = None
    invoice_no: str | None = None
    return_policy: str | None = None
    lines: list[ConfirmLine]


def window_from_policy(text: str | None) -> int:
    m = re.search(r"(\d{2,3})\s*days?", text or "", re.I)
    return int(m.group(1)) if m else 90


@app.post("/api/invoice/confirm")
async def confirm_invoice(c: Confirm, request: Request):
    from . import catalog
    window = window_from_policy(c.return_policy)
    saved = []
    with store.db() as con:
        for l in c.lines[:200]:
            info = catalog.lookup(l.product)
            bid = store.add_batch(con, product=l.product, pack=l.pack, batch=l.batch, expiry=l.expiry, qty=l.qty,
                                  rate=l.rate, mrp=l.mrp, category=l.category or info.get("category"),
                                  composition=l.composition or info.get("composition"), distributor=c.distributor,
                                  invoice_no=c.invoice_no, return_window_days=window)
            store.log(con, "received", bid, invoice=c.invoice_no, qty=l.qty)
            saved.append(dict(con.execute("SELECT * FROM batches WHERE id = ?", (bid,)).fetchone()))
    for b in saved:
        await start_watch(request.state.shop, b, (risk.return_cutoff(b["expiry"], window) - date.today()).days)
    return {"saved": len(saved), "return_window_days": window}


# ---------------------------------------------------------------- sales import
@app.post("/api/sales")
async def import_sales(request: Request, file: UploadFile = File(...)):
    """CSV from any billing software: columns date, product, units (header names are matched loosely)."""
    limit(request, "sales")
    raw = (await file.read())[:3_000_000].decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    cols = {k.lower().strip(): k for k in (reader.fieldnames or [])}
    pick = lambda *names: next((cols[n] for n in names if n in cols), None)  # noqa: E731
    dcol, pcol, ucol = pick("date", "day", "bill date"), pick("product", "item", "medicine", "name"), pick("units", "qty", "quantity", "strips")
    if not (dcol and pcol and ucol):
        raise HTTPException(400, "CSV needs columns for date, product and units.")
    n = 0
    with store.db() as con:
        for row in reader:
            try:
                d = row[dcol].strip()
                d = date.fromisoformat(d) if "-" in d else date(*map(int, reversed(d.split("/"))))
                con.execute("INSERT INTO sales VALUES (?, ?, ?) ON CONFLICT(product, day) DO UPDATE SET units = units + excluded.units",
                            (row[pcol].strip().upper(), d.isoformat(), float(row[ucol])))
                n += 1
            except (ValueError, TypeError, KeyError):
                continue
    return {"rows": n}


# ---------------------------------------------------------------- messages, decisions, agent
class MessageReq(BaseModel):
    batch_ids: list[int]
    lang: str = "en"
    phone: str | None = None


@app.post("/api/message")
def message(m: MessageReq, request: Request):
    limit(request, "message")
    if m.lang not in messages.LANGS:
        raise HTTPException(400, "lang must be en, ta or hi")
    with store.db() as con:
        rows = [b for b in scored(con) if b["id"] in m.batch_ids]
    if not rows:
        raise HTTPException(404, "no such batches")
    text = messages.return_request(m.lang, rows[0]["distributor"] or "Sir", shop_name(request), rows)
    phone = re.sub(r"\D", "", m.phone or "")
    return {"text": text, "whatsapp": f"https://wa.me/{phone}?text={urllib.parse.quote(text)}"}


class Decision(BaseModel):
    batch_id: int
    decision: str  # returned, sold, keep


@app.post("/api/decision")
async def decision(d: Decision, request: Request):
    if d.decision not in ("returned", "sold", "keep"):
        raise HTTPException(400, "decision must be returned, sold or keep")
    client = await temporal()
    if client:
        from .workflows import BatchWatch
        try:
            await client.get_workflow_handle(wf_id(request.state.shop, d.batch_id)).signal(BatchWatch.decide, d.decision)
            return {"via": "temporal"}
        except Exception:
            pass
    with store.db() as con:
        con.execute("UPDATE batches SET status = ? WHERE id = ?", (d.decision, d.batch_id))
        store.log(con, "decision", d.batch_id, decision=d.decision)
    return {"via": "direct"}


@app.get("/api/workflows")
async def workflows(request: Request):
    client = await temporal()
    if client is None:
        return {"temporal": False, "workflows": []}
    from .workflows import BatchWatch
    out = []
    with store.db() as con:
        ids = [r[0] for r in con.execute("SELECT id FROM batches")]
    for bid in ids:
        try:
            h = client.get_workflow_handle(wf_id(request.state.shop, bid))
            desc = await h.describe()
            st = await h.query(BatchWatch.status) if desc.status.name == "RUNNING" else {"stage": desc.status.name.lower()}
            out.append({"batch_id": bid, "status": desc.status.name, **st})
        except Exception:
            continue
    return {"temporal": True, "workflows": out}


class Ask(BaseModel):
    question: str


@app.post("/api/ask")
async def ask(a: Ask, request: Request):
    limit(request, "ask")
    q = a.question.strip()[:500]
    if not q:
        raise HTTPException(400, "empty question")
    from . import agent
    import anyio
    shop, name = request.state.shop, shop_name(request)
    return await anyio.to_thread.run_sync(lambda: agent.ask(q, shop=shop, shop_name=name))


@app.post("/api/demo/reset")
async def demo_reset(request: Request):
    if request.state.shop != "demo":
        raise HTTPException(403, "Only the demo shop can be reset.")
    limit(request, "reset")
    return await demo_reset_impl()


async def demo_reset_impl():
    from .demo import seed
    client = await temporal()
    if client:  # stop the old watches so new batch ids never inherit an old workflow
        with store.db("demo") as con:
            old = [r[0] for r in con.execute("SELECT id FROM batches")]
        for bid in old:
            try:
                await client.get_workflow_handle(wf_id("demo", bid)).terminate("demo reset")
            except Exception:
                pass
    batches = seed("demo")
    for b in batches:
        await start_watch("demo", b, (risk.return_cutoff(b["expiry"], b["return_window_days"]) - date.today()).days)
    return {"seeded": len(batches)}


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB, "index.html"))


app.mount("/static", StaticFiles(directory=WEB), name="static")
