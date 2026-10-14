"""Accounts: sign-up, login, sessions and shop isolation."""
import importlib
import os

import pytest
from fastapi.testclient import TestClient

os.environ["SHELFMITRA_RISK"] = "rule"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SHELFMITRA_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("TEMPORAL_ADDRESS", raising=False)
    from shelfmitra import store, auth, app as app_mod
    monkeypatch.setattr(store, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(store, "DB", None)
    importlib.reload(app_mod)
    with TestClient(app_mod.app) as c:
        yield c


def signup(c, email, shop="Sri Balaji Medicals"):
    return c.post("/api/auth/signup", json={"email": email, "password": "strongpass1", "shop_name": shop, "area": "T Nagar, Chennai"})


def test_visitor_sees_demo_shop(client):
    me = client.get("/api/me").json()
    assert me["demo"] is True
    assert client.get("/api/dashboard").json()["totals"]["batches"] == 12


def test_signup_gives_an_empty_private_shop(client):
    assert signup(client, "owner@shop.in").status_code == 200
    me = client.get("/api/me").json()
    assert me["demo"] is False and me["name"] == "Sri Balaji Medicals"
    assert client.get("/api/dashboard").json()["totals"]["batches"] == 0


def test_shops_cannot_see_each_other(client):
    signup(client, "a@shop.in", "Shop A")
    r = client.post("/api/invoice/confirm", json={"distributor": "X", "lines": [
        {"product": "DOLO 650 TAB", "batch": "D1", "expiry": "2027-03-31", "qty": 10}]})
    assert r.json()["saved"] == 1
    client.post("/api/auth/logout")
    client.cookies.clear()
    signup(client, "b@shop.in", "Shop B")
    assert client.get("/api/dashboard").json()["totals"]["batches"] == 0


def test_wrong_password_and_duplicate_email(client):
    signup(client, "dup@shop.in")
    assert signup(client, "dup@shop.in").status_code == 400
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"email": "dup@shop.in", "password": "nope-nope"})
    assert r.status_code == 401
    assert client.post("/api/auth/login", json={"email": "dup@shop.in", "password": "strongpass1"}).status_code == 200


def test_forged_cookie_is_ignored(client):
    client.cookies.set("sm_session", "sdeadbeef.9999999999.forgedsig")
    assert client.get("/api/me").json()["demo"] is True


def test_only_demo_can_be_reset(client):
    signup(client, "r@shop.in")
    assert client.post("/api/demo/reset").status_code == 403
