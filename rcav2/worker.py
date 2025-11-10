# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines a Pool object to manage job pub/sub
"""

import asyncio
from abc import abstractmethod

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

    @abstractmethod
    async def emit(self, body: Body, event: str) -> None: ...


class APIWorker(Worker):
    def __init__(self, watcher: Watcher):
        self.watcher = watcher

    async def emit(self, body: Body, event: str) -> None:
        await self.watcher.send((event, body))


class CLIWorker(Worker):
    async def emit(self, body: Body, event: str) -> None:
        if event == "report" and isinstance(body, dict):
            if "possible_root_causes" in body:
                # New format with possible_root_causes
                print("Report\n~~~~~~\n")
                if body.get("summary"):
                    print(f"Summary:\n{body['summary']}\n")
                for i, root_cause in enumerate(body["possible_root_causes"], 1):
                    print(f"Possible Root Cause {i}:")
                    print(f"{root_cause['cause']}\n")
                    print("Evidences:")
                    for evidence in root_cause["evidences"]:
                        print(f"- {evidence['error']}")
                        print(f"  source: {evidence['source']}")
                    print()

                if body.get("jira_tickets"):
                    print("Related JIRA Tickets:\n")
                    for ticket in body["jira_tickets"]:
                        print(f"- {ticket['key']}: {ticket['summary']}")
                        print(f"  {ticket['url']}")
            else:
                # Legacy format with description/evidences
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
