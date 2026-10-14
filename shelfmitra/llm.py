"""One door to the open-weight models.

Two backends with the same call:
  local  - Ollama on the shop's own machine (nothing leaves the laptop)
  hosted - an open-weight model served by Groq (for the public demo)
Set SHELFMITRA_LLM=local or hosted. The models are open weights either way,
so a shop can move from hosted to local without changing anything else.
"""
from __future__ import annotations

import base64
import json
import os
import re

import certifi
import httpx

BACKEND = os.environ.get("SHELFMITRA_LLM", "hosted")
HOSTED_TEXT = os.environ.get("SHELFMITRA_HOSTED_TEXT", "openai/gpt-oss-120b")
HOSTED_VISION = os.environ.get("SHELFMITRA_HOSTED_VISION", "qwen/qwen3.8-27b")
LOCAL_TEXT = os.environ.get("SHELFMITRA_LOCAL_TEXT", "qwen3:4b")
LOCAL_VISION = os.environ.get("SHELFMITRA_LOCAL_VISION", "qwen2.5vl:3b")
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
LOCAL_TIMEOUT = float(os.environ.get("SHELFMITRA_LOCAL_TIMEOUT", "600"))  # small CPUs, cold model loads

class TruncatedOutput(RuntimeError):
    """The model stopped mid-answer; never use a cut-off reply."""


# Force IPv4: on networks with broken IPv6 every call first stalls ~75 s before falling back.
_client = httpx.Client(timeout=120, transport=httpx.HTTPTransport(local_address="0.0.0.0", verify=certifi.where(), retries=2))


def http() -> httpx.Client:
    return _client


def _image_part(image_bytes: bytes, mime: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(image_bytes).decode()}"}}


def chat(prompt: str, *, image: bytes | None = None, mime: str = "image/jpeg", system: str = "",
         json_mode: bool = False, max_tokens: int = 1500, backend: str | None = None) -> str:
    backend = backend or BACKEND
    if backend == "local":
        model = LOCAL_VISION if image else LOCAL_TEXT
        msg = {"role": "user", "content": prompt}
        if image:
            msg["images"] = [base64.b64encode(image).decode()]
        body = {"model": model, "messages": ([{"role": "system", "content": system}] if system else []) + [msg],
                "stream": False, "options": {"temperature": 0.2}}
        if json_mode:
            body["format"] = "json"
        r = _client.post(f"{OLLAMA}/api/chat", json=body, timeout=LOCAL_TIMEOUT)
        r.raise_for_status()
        return r.json()["message"]["content"]

    model = HOSTED_VISION if image else HOSTED_TEXT
    content = [{"type": "text", "text": prompt}] + ([_image_part(image, mime)] if image else [])
    body = {"model": model, "max_tokens": max_tokens, "temperature": 0.2,
            "messages": ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": content}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = _client.post("https://api.groq.com/openai/v1/chat/completions", json=body,
                     headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"})
    r.raise_for_status()
    choice = r.json()["choices"][0]
    if choice.get("finish_reason") == "length":
        raise TruncatedOutput(f"{model} hit max_tokens={max_tokens} before finishing")
    return choice["message"]["content"]


def parse_json(text: str) -> dict:
    """Models sometimes wrap JSON in prose or code fences; take the outermost object."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in model output")
    return json.loads(m.group(0))
