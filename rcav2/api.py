# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

from fastapi import FastAPI, Request
from fastapi.responses import (
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import json

import rcav2.logjuicer
import rcav2.env
import rcav2.model
import rcav2.prompt
import rcav2.database
from rcav2.worker import Pool, Worker, Job
from rcav2.config import DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT, DATABASE_FILE


class RCAJob(Job):
    """Perform RCA on the given build URL"""

    def __init__(self, env: rcav2.env.Env, db: rcav2.database.Engine, url: str):
        self.url = url
        self.env = env
        self.db = db

    @property
    def job_key(self) -> str:
        return self.url

    async def run(self, worker: Worker):
        try:
            await worker.emit("Fetching build report...", event="progress")
            report = await rcav2.logjuicer.get_remote_report(self.env, self.url, worker)

            await worker.emit("Generating prompt...", event="progress")
            prompt = rcav2.prompt.report_to_prompt(report)

            await worker.emit("Analyzing build with LLM...", event="progress")

            async for message, event in rcav2.model.query(
                self.env, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT, prompt
            ):
                await worker.emit(message, event)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup
    app.state.env = rcav2.env.Env(debug=True, cookie_path=None)
    app.state.worker_pool = Pool(2)
    app.state.db = rcav2.database.create(DATABASE_FILE)
    yield
    # teardown
    await app.state.worker_pool.stop()


app = FastAPI(lifespan=lifespan)


def get_pool(request: Request) -> Pool:
    return request.app.state.worker_pool


@app.get("/report")
def report(request: Request, build: str):
    """Return completed report"""
    if events := rcav2.database.get(request.app.state.db, build):
        return json.loads(events)
    return dict(status="Report not found")


@app.put("/submit")
async def submit(request: Request, build: str):
    """Submit the build"""
    pool = get_pool(request)
    if pool.pending.get(build):
        return dict(status="PENDING")
    db = request.app.state.db
    if rcav2.database.get(db, build):
        return dict(status="COMPLETED")
    await pool.submit(RCAJob(request.app.state.env, db, build))
    return dict(status="PENDING")


@app.get("/watch")
async def watch(request: Request, build: str):
    """Watch a pending build."""

    async def watch_build():
        watcher = await get_pool(request).watch(build)
        if not watcher:
            # The report is now completed, redirect the client to the static page
            yield f"data: {json.dumps(['redirect', True])}\n\n"
            return
        while True:
            event = await watcher.recv()
            yield f"data: {json.dumps(event)}\n\n"
            if event == "status":
                break

    return StreamingResponse(watch_build(), media_type="text/event-stream")


app.mount("/", StaticFiles(directory="dist", html=True), name="static")
