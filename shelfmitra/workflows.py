"""Temporal: one durable workflow per batch, from the day it arrives to its return cutoff.

A batch can sit on a shelf for months, and the shop's laptop will restart many
times before its return window closes. The workflow sleeps on Temporal's
durable timers, wakes at fixed checkpoints before the cutoff, re-scores the
batch with the latest sales, and reminds the owner only when it is at risk.
It ends as soon as the owner records what they did with the batch.

DAY_SECONDS shrinks a day for demos (for example 2 means one day passes every
two seconds); in production it is 86400.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from datetime import date

CHECKPOINTS = [60, 30, 14, 7, 2]  # days before the return cutoff
TASK_QUEUE = "shelfmitra"


@dataclass
class WatchInput:
    batch_id: int
    days_to_cutoff: int
    day_seconds: float = 86400.0
    shop: str = "demo"


@dataclass
class Checkpoint:
    batch_id: int
    days_left: int
    shop: str = "demo"


@dataclass
class BatchRef:
    batch_id: int
    shop: str = "demo"
    decision: str = ""


# ---------------------------------------------------------------- activities
@activity.defn
async def score_batch(cp: Checkpoint) -> dict:
    from . import risk, store
    with store.db(cp.shop) as con:
        b = con.execute("SELECT * FROM batches WHERE id = ?", (cp.batch_id,)).fetchone()
        if b is None or b["status"] != "active":
            return {"action": "closed", "risk": 0.0}
        b = dict(b)
        hist = store.sales_history(con, b["product"], date.today().isoformat())
        scored = risk.score([b], {b["product"]: hist})[0]
        store.log(con, "checkpoint", cp.batch_id, days_left=cp.days_left, risk=scored["risk"], action=scored["action"])
        return {"action": scored["action"], "risk": scored["risk"], "expected_left": scored["expected_left"]}


@activity.defn
async def remind_owner(cp: Checkpoint) -> None:
    from . import notify, store
    with store.db(cp.shop) as con:
        b = dict(con.execute("SELECT * FROM batches WHERE id = ?", (cp.batch_id,)).fetchone())
        store.log(con, "reminder", cp.batch_id, days_left=cp.days_left)
    notify.send(f"{b['product']} batch {b['batch']}: {b['qty_on_hand']} on hand, "
                f"{cp.days_left} days left to return it to {b['distributor'] or 'the distributor'}.")


@activity.defn
async def close_window(ref: BatchRef) -> None:
    from . import store
    with store.db(ref.shop) as con:
        left = con.execute("SELECT qty_on_hand FROM batches WHERE id = ?", (ref.batch_id,)).fetchone()
        store.log(con, "window_closed", ref.batch_id, still_on_hand=left[0] if left else 0)


@activity.defn
async def record_decision(ref: BatchRef) -> None:
    from . import store
    with store.db(ref.shop) as con:
        con.execute("UPDATE batches SET status = ? WHERE id = ?", (ref.decision, ref.batch_id))
        store.log(con, "decision", ref.batch_id, decision=ref.decision)


# ---------------------------------------------------------------- workflow
@workflow.defn
class BatchWatch:
    def __init__(self) -> None:
        self.decision: str | None = None
        self.stage = "sleeping"
        self.last_risk: float | None = None

    @workflow.signal
    def decide(self, decision: str) -> None:
        """'returned', 'sold' or 'keep': the owner's call ends the watch."""
        self.decision = decision

    @workflow.query
    def status(self) -> dict:
        return {"stage": self.stage, "decision": self.decision, "last_risk": self.last_risk}

    async def _wait(self, span: timedelta) -> None:
        """Sleep for span, or less if the owner records a decision meanwhile."""
        try:
            await workflow.wait_condition(lambda: self.decision is not None, timeout=span)
        except asyncio.TimeoutError:
            pass

    @workflow.run
    async def run(self, inp: WatchInput) -> str:
        day = timedelta(seconds=inp.day_seconds)
        # A step cut off by a crash (or a flaky model or TabPFN API call) is retried with backoff,
        # forever, until some worker finishes it: the watch itself must never fail.
        opts = {"start_to_close_timeout": timedelta(minutes=2),
                "retry_policy": RetryPolicy(initial_interval=timedelta(seconds=5), backoff_coefficient=2.0,
                                            maximum_interval=timedelta(minutes=10), maximum_attempts=0)}
        elapsed = 0
        for cp in [c for c in CHECKPOINTS if c < inp.days_to_cutoff]:
            wait_days = inp.days_to_cutoff - cp - elapsed
            self.stage = f"sleeping until {cp} days before cutoff"
            # Durable timer: survives worker crashes and laptop restarts; wakes early on a decision.
            await self._wait(day * wait_days)
            if self.decision:
                break
            elapsed += wait_days
            self.stage = f"checking at {cp} days left"
            result = await workflow.execute_activity(score_batch, Checkpoint(inp.batch_id, cp, inp.shop), **opts)
            self.last_risk = result["risk"]
            if result["action"] == "closed":
                return "closed"
            if result["action"] in ("return_now", "stop_reorder"):
                self.stage = f"reminded at {cp} days left"
                await workflow.execute_activity(remind_owner, Checkpoint(inp.batch_id, cp, inp.shop), **opts)
        if self.decision:
            await workflow.execute_activity(record_decision, BatchRef(inp.batch_id, inp.shop, self.decision), **opts)
            self.stage = f"done: {self.decision}"
            return self.decision
        remaining = inp.days_to_cutoff - elapsed
        if remaining > 0:
            self.stage = "waiting for the cutoff"
            await self._wait(day * remaining)
        if self.decision:
            await workflow.execute_activity(record_decision, BatchRef(inp.batch_id, inp.shop, self.decision), **opts)
            self.stage = f"done: {self.decision}"
            return self.decision
        await workflow.execute_activity(close_window, BatchRef(inp.batch_id, inp.shop), **opts)
        self.stage = "return window closed"
        return "window_closed"
