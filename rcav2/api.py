# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the FastAPI handlers.
"""

from fastapi import FastAPI, Request
from fastapi.responses import (
    StreamingResponse,
)
from contextlib import asynccontextmanager
import json

import rcav2.tools.logjuicer
import rcav2.env
import rcav2.model
import rcav2.database
import rcav2.auth
import rcav2.tools.zuul
import rcav2.workflows
from rcav2.worker import Pool, Worker, Job
from rcav2.config import DATABASE_FILE


class RCAJob(Job):
    """Perform RCA on the given build URL"""

    def __init__(self, env: rcav2.env.Env, db: rcav2.database.Engine, url: str):
        self.url = url
        self.env = env
        self.db = db

    async def prepare(self):
        await rcav2.auth.ensure_cookie(self.env)

    @property
    def job_key(self) -> str:
        return self.url

    async def run(self, worker: Worker) -> None:
        try:
            await rcav2.workflows.rca_react(self.env, self.db, self.url, worker)
            await worker.emit("completed", event="status")
        except Exception as e:
            self.env.log.exception("Job failed")
            await worker.emit(f"Analysis failed: {e}", event="status")

        # TODO: maybe compact the chunk in a single 'llm_response' event?
        rcav2.database.set(
            self.db,
            self.url,
            json.dumps(list(filter(lambda msg: msg[0] != "progress", worker.history))),
        )


class ZuulJob(Job):
    """Discover Job definition"""

    def __init__(self, env: rcav2.env.Env, db: rcav2.database.Engine, name: str):
        self.name = name
        self.env = env
        self.db = db

    async def prepare(self):
        await rcav2.tools.zuul.ensure_zuul_info(self.env)

    @property
    def job_key(self) -> str:
        return self.name

    async def run(self, worker: Worker):
        try:
            if job := await rcav2.workflows.job_from_model(self.env, self.name, worker):
                await worker.emit(job.model_dump(), event="job")
        except Exception as e:
            self.env.log.exception("Job failed")
            await worker.emit(f"Analysis failed: {e}", event="status")
        rcav2.database.set_job(
            self.db,
            self.name,
            json.dumps(list(filter(lambda msg: msg[0] != "progress", worker.history))),
        )


async def job_get(request: Request, name: str):
    """Describe a job"""
    pool = get_pool(request)
    if pool.pending.get(name):
        return dict(status="PENDING")
    db = request.app.state.db
    if events := rcav2.database.get_job(db, name):
        return json.loads(events)
    await pool.submit(ZuulJob(request.app.state.env, db, name))
    return dict(status="PENDING")


async def job_watch(request: Request, name: str):
    """Watch a pending job."""
    return StreamingResponse(do_watch(request, name), media_type="text/event-stream")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup the fastapi app.state"""
    # setup
    app.state.env = rcav2.env.Env(debug=True, cookie_path=None)
    app.state.worker_pool = Pool(2)
    app.state.db = rcav2.database.create(DATABASE_FILE)
    rcav2.model.init_dspy()
    yield
    # teardown
    await app.state.worker_pool.stop()


def get_pool(request: Request) -> Pool:
    """Return the worker pool."""
    return request.app.state.worker_pool


async def get(request: Request, build: str):
    """Get or submit the build."""
    pool = get_pool(request)
    if pool.pending.get(build):
        return dict(status="PENDING")
    db = request.app.state.db
    if events := rcav2.database.get(db, build):
        return json.loads(events)
    await pool.submit(RCAJob(request.app.state.env, db, build))
    return dict(status="PENDING")


async def do_watch(request, job):
    """The watch handler, to follow the progress of a job."""
    watcher = await get_pool(request).watch(job)
    if not watcher:
        # The report is now completed, redirect the client to the static page
        yield f"data: {json.dumps(['redirect', True])}\n\n"
        return
    while True:
        event = await watcher.recv()
        yield f"data: {json.dumps(event)}\n\n"
        if event == "status":
            break


async def watch(request: Request, build: str):
    """Watch a pending build."""
    return StreamingResponse(do_watch(request, build), media_type="text/event-stream")


def setup_handlers(app: FastAPI):
    app.add_api_route("/get", endpoint=get, methods=["PUT"])
    app.add_api_route("/watch", endpoint=watch, methods=["GET"])
    app.add_api_route("/get_job", endpoint=job_get, methods=["PUT"])
    app.add_api_route("/watch_job", endpoint=job_watch, methods=["GET"])
