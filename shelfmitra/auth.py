"""Shop accounts: email + password, PBKDF2 hashing, signed session cookies.

No third-party auth service: the shop's login never leaves the server it
runs on, which matters for a tool a pharmacy may run on its own machine.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time

from . import store

SECRET = os.environ.get("SHELFMITRA_SECRET") or secrets.token_hex(32)
COOKIE = "sm_session"
MAX_AGE = 30 * 24 * 3600
ITER = 200_000


def _con():
    path = os.path.join(store.DATA_DIR, "accounts.db")
    os.makedirs(store.DATA_DIR, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS shops (
        id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, area TEXT,
        pw_salt BLOB NOT NULL, pw_hash BLOB NOT NULL, created TEXT DEFAULT (datetime('now')))""")
    return con


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITER)


def signup(email: str, password: str, name: str, area: str | None) -> dict:
    email = email.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email):
        raise ValueError("Please enter a valid email.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    name = name.strip()[:60]
    if not name:
        raise ValueError("Please enter your shop's name.")
    shop_id = "s" + secrets.token_hex(6)
    salt = os.urandom(16)
    with _con() as con:
        try:
            con.execute("INSERT INTO shops (id, email, name, area, pw_salt, pw_hash) VALUES (?, ?, ?, ?, ?, ?)",
                        (shop_id, email, name, (area or "").strip()[:60], salt, _hash(password, salt)))
        except sqlite3.IntegrityError:
            raise ValueError("An account with this email already exists. Please log in.")
    return {"id": shop_id, "name": name, "email": email}


def login(email: str, password: str) -> dict:
    with _con() as con:
        row = con.execute("SELECT * FROM shops WHERE email = ?", (email.strip().lower(),)).fetchone()
    # Compare in constant time, and do the hashing work even for unknown emails.
    salt = row["pw_salt"] if row else os.urandom(16)
    ok = hmac.compare_digest(_hash(password, salt), row["pw_hash"] if row else b"x" * 32)
    if not (row and ok):
        raise ValueError("Wrong email or password.")
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def shop(shop_id: str) -> dict | None:
    with _con() as con:
        row = con.execute("SELECT id, name, email, area FROM shops WHERE id = ?", (shop_id,)).fetchone()
    return dict(row) if row else None


def make_token(shop_id: str) -> str:
    exp = str(int(time.time()) + MAX_AGE)
    sig = hmac.new(SECRET.encode(), f"{shop_id}.{exp}".encode(), hashlib.sha256).digest()
    return f"{shop_id}.{exp}.{base64.urlsafe_b64encode(sig).decode().rstrip('=')}"


def read_token(token: str | None) -> str | None:
    try:
        shop_id, exp, sig = (token or "").split(".")
        want = base64.urlsafe_b64encode(hmac.new(SECRET.encode(), f"{shop_id}.{exp}".encode(), hashlib.sha256).digest()).decode().rstrip("=")
        if hmac.compare_digest(sig, want) and int(exp) > time.time():
            return shop_id
    except ValueError:
        pass
    return None
