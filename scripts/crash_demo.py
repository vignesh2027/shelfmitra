"""Kills the Temporal worker in the middle of a batch watch and shows that nothing is lost.

Runs its own Temporal dev server (UI on http://localhost:8244) and its own shop
database, so it does not touch the app you have running. One shop "day" lasts
one second here, so a 70-day return window plays out in about a minute:

  1. start a worker and a BatchWatch for one batch, 70 days before its cutoff
  2. wait for the first checkpoint (60 days left), then kill -9 the worker
  3. stay down while the 30-day checkpoint falls due
  4. start a fresh worker: the overdue checkpoint runs, and the watch carries on to the cutoff

Usage: .venv/bin/python scripts/crash_demo.py
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PORT, UI_PORT = 7244, 8244
DAYS, DAY_SECONDS = 70, 1.0


def say(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def wait_port(port: int) -> None:
    while True:
        try:
            socket.create_connection(("localhost", port), timeout=0.5).close()
            return
        except OSError:
            time.sleep(0.3)


def events(data_dir: str) -> list[tuple]:
    import sqlite3
    path = os.path.join(data_dir, "shops", "demo.db")
    with sqlite3.connect(path) as con:
        return con.execute("SELECT at, kind, detail FROM events WHERE batch_id IS NOT NULL ORDER BY id").fetchall()


def start_worker(env: dict, log) -> subprocess.Popen:
    return subprocess.Popen([sys.executable, "-m", "shelfmitra.worker"], cwd=ROOT, env=env, stdout=log, stderr=log)


async def main() -> None:
    work = tempfile.mkdtemp(prefix="shelfmitra-crash-")
    env = os.environ | {"TEMPORAL_ADDRESS": f"localhost:{PORT}", "SHELFMITRA_DATA_DIR": work}
    env.pop("SHELFMITRA_DB", None)
    os.environ.update(env)

    from shelfmitra import demo, store
    store.DATA_DIR = work
    demo.seed("demo")
    with store.db("demo") as con:
        con.execute("DELETE FROM events")
        b = dict(store.batches(con)[0])
    say(f"Watching {b['product']} batch {b['batch']} ({b['qty_on_hand']} on hand), {DAYS} days before its return cutoff")

    temporal = subprocess.Popen(["temporal", "server", "start-dev", "--port", str(PORT), "--ui-port", str(UI_PORT),
                                 "--db-filename", os.path.join(work, "temporal.db"), "--log-level", "error"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    wait_port(PORT)
    log = open(os.path.join(work, "worker.log"), "w")
    worker = start_worker(env, log)
    try:
        from temporalio.client import Client
        from shelfmitra.workflows import TASK_QUEUE, BatchWatch, WatchInput
        client = await Client.connect(f"localhost:{PORT}")
        wf_id = f"crash-demo-batch-{b['id']}"
        handle = await client.start_workflow(BatchWatch.run, WatchInput(b["id"], DAYS, DAY_SECONDS, "demo"),
                                             id=wf_id, task_queue=TASK_QUEUE)
        say(f"Started workflow {wf_id}  (Temporal UI: http://localhost:{UI_PORT})")

        while not any(k == "checkpoint" for _, k, _ in events(work)):
            await asyncio.sleep(0.5)
        say("Checkpoint at 60 days left is done.")
        worker.send_signal(signal.SIGKILL)
        worker.wait()
        say("Worker killed with SIGKILL. Nothing is running the watch now.")

        down = (60 - 30) * DAY_SECONDS + 8
        say(f"Staying down for {down:.0f}s, past the moment the 30-day checkpoint falls due ...")
        await asyncio.sleep(down)
        before = sum(k == "checkpoint" for _, k, _ in events(work))
        say(f"Checkpoints recorded while the worker was dead: {before - 1}")

        worker = start_worker(env, log)
        say("Fresh worker started.")
        result = await handle.result()
        say(f"Workflow finished: {result}")

        print("\nWhat the shop's event log recorded:")
        for at, kind, detail in events(work):
            d = json.loads(detail or "{}")
            print(f"  {at}  {kind:<14} {', '.join(f'{k}={v}' for k, v in d.items())}")
        ran = [json.loads(d)["days_left"] for _, k, d in events(work) if k == "checkpoint"]
        hist = [e async for e in handle.fetch_history_events()]
        print(f"\nCheckpoints run, by days left: {ran}  (expected [60, 30, 14, 7, 2])")
        print(f"Temporal history: {len(hist)} events for this one batch.")
        print(f"Workflow and history stay browsable at http://localhost:{UI_PORT} until you press Enter.")
        hold = float(os.environ.get("CRASH_DEMO_HOLD", "0"))
        if hold:
            await asyncio.sleep(hold)
        elif sys.stdin.isatty():
            input()
    finally:
        worker.kill()
        temporal.send_signal(signal.SIGINT)
        temporal.wait(timeout=10)
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
