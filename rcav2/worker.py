# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines a Pool object to manage job pub/sub
"""

import asyncio
from abc import ABCMeta, abstractmethod

type Body = str | bool | int | list | dict
type Event = tuple[str, Body]


class Watcher:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def send(self, event: Event):
        await self.queue.put(event)

    async def recv(self) -> Event:
        event = await self.queue.get()
        self.queue.task_done()
        return event


class Worker:
    """A worker process that can be watched"""

    def __init__(self) -> None:
        self.watchers: list[Watcher] = []
        self.history: list[Event] = []

    async def emit(self, body: Body, event: str) -> None:
        item = (event, body)
        self.history.append(item)
        for watcher in self.watchers:
            await watcher.send(item)

    async def add_watcher(self, watcher: Watcher):
        # Send past message...
        for item in self.history:
            await watcher.send(item)
        self.watchers.append(watcher)


class CLIWorker(Worker):
    async def emit(self, body: Body, event: str) -> None:
        if event == "report" and isinstance(body, dict):
            print(f"Report\n~~~~~~\n\n{body['description']}\n\nEvidences:\n")
            for evidence in body["evidences"]:
                print(f"- {evidence['error']}\n  source: {evidence['source']}")

            if body.get("jira_tickets"):
                print("\nRelated JIRA Tickets:\n")
                for ticket in body["jira_tickets"]:
                    print(f"- {ticket['key']}: {ticket['summary']}")
                    print(f"  {ticket['url']}")
        else:
            print(f"{event} - {body}")


class Job(metaclass=ABCMeta):
    @abstractmethod
    async def run(self, worker: Worker): ...

    @property
    @abstractmethod
    def job_key(self) -> str: ...

    @property
    @abstractmethod
    async def prepare(self): ...


class Pool:
    """Pool of workers to manage pub/sub."""

    # https://docs.python.org/3/library/asyncio-queue.html#examples
    def __init__(self, max_worker: int):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.pending: dict[str, tuple[Worker, Job]] = dict()
        self.workers = []
        for i in range(max_worker):
            task = asyncio.create_task(self.worker())
            self.workers.append(task)

    async def stop(self):
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

    async def submit(self, job: Job) -> None:
        key = job.job_key
        if not self.pending.get(key):
            worker_job = (Worker(), job)
            self.pending[key] = worker_job
            await job.prepare()
            await self.queue.put(worker_job)

    async def watch(self, key: str) -> Watcher | None:
        if self.pending.get(key):
            watcher = Watcher()
            await self.pending[key][0].add_watcher(watcher)
            return watcher
        else:
            return None

    async def worker(self):
        while True:
            (worker, job) = await self.queue.get()
            key = job.job_key
            await job.run(worker)
            self.queue.task_done()
            del self.pending[key]
