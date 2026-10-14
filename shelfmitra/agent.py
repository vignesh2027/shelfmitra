"""The ShelfMitra agent: an open-weight model that answers the owner with TabPFN as its prediction tool.

The model decides which tool to call and writes the answer in the owner's
language. Every number in the answer comes from a tool: the model never
estimates stock, risk or dates on its own.
"""
from __future__ import annotations

import json
import os
from datetime import date

from . import messages, risk, store
from .llm import http

MODEL = os.environ.get("SHELFMITRA_AGENT_MODEL", "openai/gpt-oss-120b")
MAX_STEPS = 6
_SHOP_NAME = "Lakshmi Medicals"

SYSTEM = """You are ShelfMitra, an assistant for a small medical shop in India. You help the owner
avoid losses from medicines that expire on the shelf. Today is {today}.
Rules:
- Answer in the same language the owner used (Tamil, Hindi or English). Keep it short and practical.
- Every number you mention (quantities, rupees, risk, dates) must come from a tool result. Never estimate.
- Use expiry_risk to judge stock already on the shelf. Its what_to_do field is the shop's decision; repeat it, do not
  invent your own thresholds.
- Whenever the owner asks whether to order, buy or restock a quantity, you MUST call what_if_order with that
  product and quantity, and base the advice on its risk. If its risk is 30% or more, suggest a smaller quantity
  and check that smaller quantity with what_if_order too.
  Then give both: the risk for the quantity they asked about, and the smaller quantity with its risk.
- Use return_message when the owner wants to ask the distributor to collect stock.
- Risk is a probability that more than 10% of the batch is still unsold at the distributor's return cutoff.
- Never suggest discounting prescription medicines or selling them without a prescription.
- Write plain text for a phone screen: short sentences, a numbered line per medicine if there are several,
  no markdown, no tables, no asterisks. Show risk as a percent and dates exactly as the tools give them.
  Never show field names or codes from the tools."""

TOOLS = [
    {"type": "function", "function": {
        "name": "stock", "description": "List batches on the shelf with expiry, return cutoff and quantity on hand.",
        "parameters": {"type": "object", "properties": {"product": {"type": ["string", "null"], "description": "optional product name filter"}}}}},
    {"type": "function", "function": {
        "name": "expiry_risk", "description": "TabPFN-predicted risk for every batch (or one product), sorted by rupees at risk, with the recommended action.",
        "parameters": {"type": "object", "properties": {"product": {"type": ["string", "null"]}}}}},
    {"type": "function", "function": {
        "name": "what_if_order", "description": "Predict with TabPFN whether a new purchase of qty units of a product would still be unsold at its return cutoff.",
        "parameters": {"type": "object", "required": ["product", "qty"], "properties": {
            "product": {"type": "string"}, "qty": {"type": "integer"},
            "months_to_expiry": {"type": ["integer", "null"], "description": "shelf life of the new batch in months, default 18"}}}}},
    {"type": "function", "function": {
        "name": "return_message", "description": "Draft the WhatsApp message asking the distributor to collect at-risk batches for expiry return.",
        "parameters": {"type": "object", "properties": {"lang": {"type": ["string", "null"], "enum": ["en", "ta", "hi", None]}}}}},
]


def _scored(product: str | None = None):
    with store.db() as con:
        bs = [b for b in store.batches(con) if not product or product.lower() in b["product"].lower()]
        hist = {b["product"]: store.sales_history(con, b["product"], date.today().isoformat()) for b in bs}
    return risk.score(bs, hist)


ACTIONS = {
    "en": {"return_now": "return it now", "stop_reorder": "stop reordering it", "watch": "watch it",
           "ok": "fine, nothing to do", "need_sales": "not enough sales data yet", "window_closed": "return window already closed"},
    "ta": {"return_now": "இப்போதே திருப்பி அனுப்புங்கள்", "stop_reorder": "மீண்டும் ஆர்டர் செய்ய வேண்டாம்", "watch": "கவனித்து வாருங்கள்",
           "ok": "சரியாக உள்ளது", "need_sales": "விற்பனை தரவு போதவில்லை", "window_closed": "திருப்பும் காலம் முடிந்தது"},
    "hi": {"return_now": "अभी लौटाइए", "stop_reorder": "दोबारा ऑर्डर मत कीजिए", "watch": "नज़र रखिए",
           "ok": "ठीक है, कुछ नहीं करना", "need_sales": "बिक्री का डेटा अभी कम है", "window_closed": "वापसी की अवधि खत्म हो गई"},
}
_LANG = "en"


def _dmy(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}/{m}/{y}"


def _human(b: dict) -> dict:
    """Tool output in the words and units the owner uses, so the model has nothing to convert."""
    return {"product": b["product"], "batch": b["batch"], "on_hand": b["qty_on_hand"], "return_by": _dmy(b["return_cutoff"]),
            "days_left_to_return": b["days_to_cutoff"], "risk_percent": round(b["risk"] * 100),
            "units_likely_unsold": round(float(b["expected_left"]), 1), "rupees_at_risk": round(b["rupees_at_risk"]),
            "what_to_do": ACTIONS[_LANG].get(b["action"], b["action"])}


def run_tool(name: str, args: dict) -> dict:
    if name == "stock":
        rows = _scored(args.get("product"))
        return {"batches": [{"product": b["product"], "batch": b["batch"], "expiry": _dmy(b["expiry"]), "return_by": _dmy(b["return_cutoff"]),
                             "on_hand": b["qty_on_hand"], "distributor": b["distributor"]} for b in rows]}
    if name == "expiry_risk":
        rows = _scored(args.get("product"))
        return {"batches": [_human(b) for b in rows]}
    if name == "what_if_order":
        with store.db() as con:
            ref = next((b for b in store.batches(con, status=None) if args["product"].lower() in b["product"].lower()), None)
            if ref is None:
                return {"error": f"no sales history for {args['product']}"}
            hist = store.sales_history(con, ref["product"], date.today().isoformat())
            # Older stock of the same product sells first, so the new batch only clears after it does.
            on_shelf = sum(b["qty_on_hand"] for b in store.batches(con) if b["product"] == ref["product"])
        from datetime import timedelta
        months = int(args.get("months_to_expiry") or 18)
        hypo = {**ref, "id": 0, "qty_on_hand": int(args["qty"]) + on_shelf,
                "expiry": (date.today() + timedelta(days=30 * months)).isoformat()}
        s = risk.score([hypo], {ref["product"]: hist})[0]
        return {"product": ref["product"], "qty": int(args["qty"]), "already_on_shelf": on_shelf, "risk_percent": round(s["risk"] * 100),
                "units_likely_unsold": round(float(s["expected_left"]), 1), "sales_per_day_last_30": round(float(s["vel30"]), 2), "return_by": _dmy(s["return_cutoff"])}
    if name == "return_message":
        rows = [b for b in _scored() if b["action"] == "return_now"]
        if not rows:
            return {"message": None, "note": "no batch needs returning right now"}
        return {"message": messages.return_request(args.get("lang") or "en", rows[0]["distributor"] or "Sir",
                                                   _SHOP_NAME, rows)}
    return {"error": f"unknown tool {name}"}


def llm_step(history: list[dict]) -> dict:
    """One model call. Returns the assistant message (with tool_calls or final content)."""
    r = http().post("https://api.groq.com/openai/v1/chat/completions",
                   headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
                   json={"model": MODEL, "messages": history, "tools": TOOLS, "temperature": 0.2, "max_tokens": 4000,
                         "reasoning_effort": "low"})
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


HINGLISH = {"kya", "karun", "karu", "hai", "hain", "kitna", "kitne", "aur", "ke", "ki", "mein", "nahi", "chahiye", "kaun", "lautana", "bhejna", "dawa"}
TANGLISH = {"enna", "venum", "vendum", "evlo", "evvalavu", "irukku", "pannanum", "panna", "edhu", "ethai", "anuppanum", "sollu"}


def reply_language(q: str) -> str:
    """Code, not the model, decides the reply language from the script and words used."""
    if any("\u0b80" <= c <= "\u0bff" for c in q):
        return "Tamil (Tamil script)"
    if any("\u0900" <= c <= "\u097f" for c in q):
        return "Hindi (Devanagari script)"
    words = {w.strip("?.,!").lower() for w in q.split()}
    if len(words & HINGLISH) >= 2:
        return "Hindi written in English letters (Hinglish), the way the owner wrote"
    if len(words & TANGLISH) >= 1:
        return "Tamil written in English letters (Tanglish), the way the owner wrote"
    return "English"


def start(question: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM.format(today=date.today().isoformat())},
            {"role": "user", "content": f"{question}\n\n(Reply in {reply_language(question)}.)"}]


def ask(question: str, shop: str = "demo", shop_name: str = "Lakshmi Medicals") -> dict:
    """Run the agent loop for one shop. Tools only ever see that shop's database."""
    token = store.current_shop.set(shop)
    try:
        return _ask(question, shop_name)
    finally:
        store.current_shop.reset(token)


def _ask(question: str, shop_name: str) -> dict:
    global _SHOP_NAME, _LANG
    _SHOP_NAME = shop_name
    rl = reply_language(question)
    _LANG = "ta" if rl.startswith("Tamil (") else "hi" if rl.startswith("Hindi (") else "en"
    history, trace = start(question), []
    for _ in range(MAX_STEPS):
        msg = llm_step(history)
        history.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        if not msg.get("tool_calls"):
            return {"answer": msg.get("content", ""), "trace": trace}
        for call in msg["tool_calls"]:
            args = json.loads(call["function"].get("arguments") or "{}")
            result = run_tool(call["function"]["name"], args)
            trace.append({"tool": call["function"]["name"], "args": args})
            history.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result, ensure_ascii=False, default=str)})
    return {"answer": "I could not finish that in time. Please ask again more simply.", "trace": trace}
