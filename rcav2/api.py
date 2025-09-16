# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

from fastapi import FastAPI, Request
from fastapi.responses import (
    StreamingResponse,
    HTMLResponse,
    PlainTextResponse,
    FileResponse,
)
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import cast

import rcav2.logjuicer
import rcav2.env
import rcav2.model
import rcav2.prompt
from rcav2.worker import Pool, Worker, Job
from rcav2.config import DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT


class RCAJob(Job):
    """Perform RCA on the given build URL"""

    def __init__(self, env: rcav2.env.Env, url: str):
        self.url = url
        self.env = env
        self.result: None | str = None

    @property
    def job_key(self) -> str:
        return self.url

    async def run(self, worker: Worker):
        try:
            await worker.emit("Fetching build report...", event="status")
            report = await rcav2.logjuicer.get_remote_report(self.env, self.url)

            await worker.emit("Generating prompt...", event="status")
            prompt = rcav2.prompt.report_to_prompt(report)

            await worker.emit("Analyzing build with LLM...", event="status")
            result = []
            async for message, event in rcav2.model.stream(
                self.env, DEFAULT_MODEL, DEFAULT_SYSTEM_PROMPT, prompt
            ):
                if event == "chunk":
                    result.append(message)
                await worker.emit(message, event)
            self.result = "".join(result)
            await worker.emit("done!", event="done")

        except Exception as e:
            self.env.log.exception("Job failed")
            self.result = f"Analysis failed: {e}"
            await worker.emit(self.result, event="error")
            await worker.emit("done!", event="done")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # setup
    app.state.env = rcav2.env.Env(debug=True)
    app.state.worker_pool = Pool(2)
    yield
    # teardown
    await app.state.worker_pool.stop()


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="rcav2/static"), name="static")


def get_pool(request: Request) -> Pool:
    return request.app.state.worker_pool


@app.get("/report", response_class=PlainTextResponse)
def report(request: Request, build: str):
    """Return completed report"""
    if report := get_pool(request).completed.get(build):
        return cast(RCAJob, report).result
    return "Report not found"


@app.put("/submit")
async def submit(request: Request, build: str):
    """Submit the build"""
    status = await get_pool(request).submit(RCAJob(request.app.state.env, build))
    return dict(status=status)


@app.get("/watch")
async def watch(request: Request, build: str):
    """Watch a pending build."""

    async def watch_build():
        watcher = await get_pool(request).watch(build)
        if not watcher:
            # The report is now completed, redirect the client to the static page
            yield "event: done\ntrue\n\n"
            return
        while True:
            event, msg = await watcher.recv()
            if event == "done":
                yield f"event: done\ndata: {msg}\n\n"
                break

            data_payload = "\n".join(f"data: {line}" for line in msg.split("\n"))
            yield f"event: {event}\n{data_payload}\n\n"

    return StreamingResponse(watch_build(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse("rcav2/static/index.html")
