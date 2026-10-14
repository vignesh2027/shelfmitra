"""Return-request messages to the distributor, in Tamil, Hindi or English.

The open model writes only the wording, as a template with placeholders.
Code then fills in every product, batch, quantity and date, and refuses any
template that drops a placeholder, so the model can never change a number.
Templates are cached per language, so a shop pays for one model call per
language, not one per message.
"""
from __future__ import annotations

import json
import pathlib

from .llm import TruncatedOutput, chat

LANGS = {"en": "English", "ta": "Tamil", "hi": "Hindi"}
REQUIRED = ["{distributor}", "{shop}", "{items}", "{count}", "{cutoff}"]
CACHE = pathlib.Path("data/templates.json")

PROMPT = """Write a short, polite WhatsApp message from a small medical shop owner in India to their
medicine distributor, asking them to collect some medicines for expiry return before the return deadline.
Write it in {lang}, in the natural, respectful tone a shop owner uses with a distributor they work with often.
Use these placeholders exactly as written, each one once, and nothing else in curly braces:
{distributor} = distributor name, {shop} = shop name, {count} = number of items,
{items} = the list of items (it will be inserted as separate lines), {cutoff} = the deadline date.
Keep it under 70 words. Return only the message text."""

FALLBACK = {
    "en": "Hello {distributor}, this is {shop}. Please collect these {count} items for expiry return before {cutoff}:\n{items}\nThank you.",
}


def template(lang: str) -> str:
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    if lang in cache:
        return cache[lang]
    for _ in range(3):
        try:
            t = chat(PROMPT.format(lang=LANGS[lang], distributor="{distributor}", shop="{shop}",
                                   count="{count}", items="{items}", cutoff="{cutoff}"), max_tokens=3000).strip()
        except TruncatedOutput:
            continue
        if all(t.count(p) == 1 for p in REQUIRED):
            cache[lang] = t
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))
            return t
    return FALLBACK["en"]  # never send a message whose placeholders were mangled


def return_request(lang: str, distributor: str, shop: str, batches: list[dict]) -> str:
    items = "\n".join(f"{i}. {b['product']} | Batch {b['batch']} | Exp {b['expiry'][5:7]}/{b['expiry'][2:4]} | Qty {b['qty_on_hand']}"
                      for i, b in enumerate(batches, 1))
    cutoff = min(b["return_cutoff"] for b in batches)
    d = cutoff.split("-")
    return template(lang).format(distributor=distributor, shop=shop, items=items,
                                 count=len(batches), cutoff=f"{d[2]}/{d[1]}/{d[0]}")
