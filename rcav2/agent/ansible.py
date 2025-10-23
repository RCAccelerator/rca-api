# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import dspy  # type: ignore[import-untyped]
from pydantic import BaseModel
import glob

import rcav2.tools.git
from rcav2.worker import Worker


class Job(BaseModel):
    description: str
    actions: list[str]


class DSPyAnsibleOracle(dspy.Signature):
    """You are a Ansible Playbooks knowledge service agent that helps user understand the purpose of a Zuul job.

    You are given a playbook path, and you should use tool in order to discover the role and tasks content."""

    playbooks: list[str] = dspy.InputField()
    job: Job = dspy.OutputField()


root = rcav2.tools.git.workspace_root.expanduser()


def make_agent(worker: Worker) -> dspy.ReAct:
    async def read_file(path: str) -> str | None:
        """Read a file content, return None when there is an error"""
        await worker.emit(f"Reading {path}", "progress")
        try:
            return (root / path).read_text()
        except Exception as e:
            await worker.emit(f"{path}: read error {e}", "error")
            print(f"{path}: read error {e}")
            return None

    async def find_file(path_glob: str) -> list[str]:
        """Return paths matching a glob pattern."""
        await worker.emit(f"Searching {path_glob}", "progress")
        return glob.glob(path_glob, root_dir=root)

    return dspy.ReAct(DSPyAnsibleOracle, tools=[read_file, find_file])


async def call_agent(agent: dspy.ReAct, plays: list[str], worker: Worker) -> Job:
    # Make the path relative to the workspace
    playbooks = list(map(lambda p: str(p)[len(str(root)) + 1 :], plays))

    await worker.emit("Calling AnsibleOracle", "progress")
    await worker.emit(playbooks, "playbooks")
    result = await agent.acall(playbooks=playbooks)
    await rcav2.model.emit_dspy_usage(result, worker)
    return result.job


async def main() -> None:
    """A test experiment"""
    import sys
    import json
    import rcav2.tools.zuul
    import rcav2.model
    from rcav2.worker import CLIWorker

    job = sys.argv[1]
    export = json.load(open(".zuul-export.json"))
    info = rcav2.tools.zuul.read_weeder_export(export)
    plays = await rcav2.tools.zuul.get_job_playbooks(info, job)
    if not plays:
        print("Couldn't find job playbook")
        return

    rcav2.model.init_dspy()
    worker = CLIWorker()
    agent = make_agent(worker)
    job_info = await call_agent(agent, plays, worker)
    print(job_info)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
