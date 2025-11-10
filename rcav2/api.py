# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the FastAPI handlers.
"""

from fastapi import FastAPI, Request, APIRouter
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import asyncio
import json

import rcav2.tools.logjuicer
from rcav2.env import Env
import rcav2.model
import rcav2.auth
import rcav2.tools.zuul
import rcav2.workflows
from rcav2.worker import APIWorker, Watcher


async def run(worker: APIWorker, env: Env, workflow: str, url: str) -> None:
    try:
        await rcav2.workflows.run_workflow(env, workflow, url, worker)
    except Exception as e:
        env.log.exception("Job failed")
        await worker.emit(f"Analysis failed: {e}", event="status")


router = APIRouter()


class RcaState:
    def __init__(self, debug):
        self.env = Env(debug=True, cookie_path=None)
        rcav2.model.init_dspy()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup the fastapi app.state"""
    # setup
    app.state.rca = RcaState(True)
    yield
    # teardown
    pass


async def do_watch(watcher):
    """The watch handler, to follow the progress of a job."""
    while True:
        event = await watcher.recv()
        yield f"data: {json.dumps(event)}\n\n"
        if event == "status":
            break


@router.get("/get")
async def get(request: Request, build: str, workflow: str = "react"):
    """Perform RCA on a given build."""
    state = request.app.state.rca
    await rcav2.auth.ensure_cookie(state.env)
    watcher = Watcher()
    worker = APIWorker(watcher)
    asyncio.create_task(run(worker, state.env, workflow, build))
    return StreamingResponse(do_watch(watcher), media_type="text/event-stream")
