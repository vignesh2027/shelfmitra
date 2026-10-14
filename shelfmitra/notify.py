"""Gets a reminder to the owner's phone.

Uses ntfy.sh, a free, open-source push service: the owner installs the ntfy
app and subscribes to their shop's topic. With no topic set, reminders only
appear in the ShelfMitra inbox.
"""
from __future__ import annotations

import os

import httpx

from .llm import http

TOPIC = os.environ.get("SHELFMITRA_NTFY_TOPIC")


def send(text: str) -> bool:
    if not TOPIC:
        return False
    try:
        http().post(f"https://ntfy.sh/{TOPIC}", content=text.encode(), timeout=10,
                   headers={"Title": "ShelfMitra reminder", "Tags": "pill,alarm_clock"})
        return True
    except httpx.HTTPError:
        return False
