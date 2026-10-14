"""Runs the Temporal worker: BatchWatch workflows and their activities."""
import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from .workflows import TASK_QUEUE, BatchWatch, close_window, record_decision, remind_owner, score_batch


async def main():
    client = await Client.connect(os.environ.get("TEMPORAL_ADDRESS", "localhost:7233"))
    worker = Worker(client, task_queue=TASK_QUEUE, workflows=[BatchWatch],
                    activities=[score_batch, remind_owner, close_window, record_decision])
    print("ShelfMitra worker running on task queue", TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
