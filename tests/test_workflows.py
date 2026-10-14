"""BatchWatch on Temporal's time-skipping test server: 90 days pass in seconds."""
import os
import uuid
from datetime import date, timedelta

import pytest
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

os.environ["SHELFMITRA_RISK"] = "rule"  # keep tests independent of TabPFN access

from shelfmitra import store  # noqa: E402
from shelfmitra.workflows import (  # noqa: E402
    TASK_QUEUE, BatchWatch, WatchInput, close_window, record_decision, remind_owner, score_batch,
)

ACTIVITIES = [score_batch, remind_owner, close_window, record_decision]


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB", str(tmp_path / "shop.db"))


def seed_batch(qty: int, daily_units: float, days_to_cutoff: int) -> int:
    expiry = date.today() + timedelta(days=days_to_cutoff + 90)
    with store.db() as con:
        bid = store.add_batch(con, product="ALLEGRA 120MG TAB", batch="AL6B19", expiry=expiry.isoformat(),
                              qty=qty, rate=171.5, category="R06", distributor="Sri Murugan Pharma")
        for i in range(120):
            d = (date.today() - timedelta(days=i)).isoformat()
            con.execute("INSERT INTO sales VALUES (?, ?, ?)", ("ALLEGRA 120MG TAB", d, daily_units))
    return bid


def events(kind: str) -> list:
    with store.db() as con:
        return [dict(r) for r in con.execute("SELECT * FROM events WHERE kind = ?", (kind,))]


async def test_slow_batch_gets_reminders_then_window_closes():
    bid = seed_batch(qty=200, daily_units=0.3, days_to_cutoff=90)  # 0.3/day will never clear 200
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=TASK_QUEUE, workflows=[BatchWatch], activities=ACTIVITIES):
            result = await env.client.execute_workflow(
                BatchWatch.run, WatchInput(bid, 90), id=f"t-{uuid.uuid4()}", task_queue=TASK_QUEUE)
    assert result == "window_closed"
    assert [e for e in events("checkpoint")] and len(events("checkpoint")) == 5   # 60, 30, 14, 7, 2
    assert len(events("reminder")) == 5
    assert len(events("window_closed")) == 1


async def test_fast_batch_is_checked_but_never_nags():
    bid = seed_batch(qty=20, daily_units=3.0, days_to_cutoff=90)  # sells out in about a week
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=TASK_QUEUE, workflows=[BatchWatch], activities=ACTIVITIES):
            await env.client.execute_workflow(
                BatchWatch.run, WatchInput(bid, 90), id=f"t-{uuid.uuid4()}", task_queue=TASK_QUEUE)
    assert len(events("checkpoint")) == 5
    assert events("reminder") == []


async def test_owner_decision_ends_the_watch_early():
    bid = seed_batch(qty=200, daily_units=0.3, days_to_cutoff=90)
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(env.client, task_queue=TASK_QUEUE, workflows=[BatchWatch], activities=ACTIVITIES):
            h = await env.client.start_workflow(
                BatchWatch.run, WatchInput(bid, 90), id=f"t-{uuid.uuid4()}", task_queue=TASK_QUEUE)
            await env.sleep(timedelta(days=45))          # past the 60-days-left checkpoint (day 30) only
            await h.signal(BatchWatch.decide, "returned")
            assert await h.result() == "returned"
    assert len(events("reminder")) == 1                  # no reminders after the owner acted
    with store.db() as con:
        assert con.execute("SELECT status FROM batches WHERE id = ?", (bid,)).fetchone()[0] == "returned"

# Crash recovery is shown live against a real Temporal server: see scripts/crash_demo.sh.
