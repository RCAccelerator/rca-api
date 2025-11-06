# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the FastAPI handlers.
"""

from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import (
    StreamingResponse,
)
from contextlib import asynccontextmanager
import json

import rcav2.tools.logjuicer
from rcav2.env import Env
import rcav2.model
import rcav2.database
import rcav2.auth
import rcav2.tools.zuul
import rcav2.workflows
from rcav2.worker import Pool, Worker, Job
from rcav2.config import DATABASE_FILE


class RCAJob(Job):
    """Perform RCA on the given build URL"""

    def __init__(self, env: Env, db: rcav2.database.Engine, workflow: str, url: str):
        self.url = url
        self.workflow = workflow
        self.env = env
        self.db = db

    async def prepare(self):
        await rcav2.auth.ensure_cookie(self.env)

    @property
    def job_key(self) -> str:
        return f"{self.workflow}-{self.url}"

    async def run(self, worker: Worker) -> None:
        try:
            await rcav2.workflows.run_workflow(
                self.env, self.db, self.workflow, self.url, worker
            )
            rcav2.database.set(
                self.db,
                self.workflow,
                self.url,
                json.dumps(
                    list(filter(lambda msg: msg[0] != "progress", worker.history))
                ),
            )
            await worker.emit("completed", event="status")

        except Exception as e:
            self.env.log.exception("Job failed")
            await worker.emit(f"Analysis failed: {e}", event="status")


router = APIRouter()


async def do_watch(pool: Pool, key: str):
    """The watch handler, to follow the progress of a job."""
    watcher = await pool.watch(key)
    if not watcher:
        # The report is now completed, redirect the client to the static page
        yield f"data: {json.dumps(['redirect', True])}\n\n"
        return
    while True:
        event = await watcher.recv()
        yield f"data: {json.dumps(event)}\n\n"
        if event == "status":
            break


class RcaState:
    def __init__(self, max_worker, debug, db_file):
        self.env = Env(debug=True, cookie_path=None)
        self.pool = Pool(max_worker)
        self.db = rcav2.database.create(db_file)
        rcav2.model.init_dspy()

    async def stop(self):
        await self.pool.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup the fastapi app.state"""
    # setup
    app.state.rca = RcaState(2, True, DATABASE_FILE)
    yield
    # teardown
    await app.state.rca.stop()


@router.put("/get")
async def get(request: Request, build: str, workflow: str = "react"):
    """Get or submit the build."""
    state = request.app.state.rca
    if state.pool.pending.get(f"{workflow}-{build}"):
        return dict(status="PENDING")
    if events := rcav2.database.get(state.db, workflow, build):
        return json.loads(events)
    await state.pool.submit(RCAJob(state.env, state.db, workflow, build))
    return dict(status="PENDING")


@router.get("/watch")
async def watch(request: Request, build: str, workflow: str = "react"):
    """Watch a pending build."""
    resp = do_watch(request.app.state.rca.pool, f"{workflow}-{build}")
    return StreamingResponse(resp, media_type="text/event-stream")
