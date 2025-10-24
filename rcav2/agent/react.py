# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
A next-gen rca agent that reads the errors as needed
"""

import dspy  # type: ignore[import-untyped]
import re

import rcav2.errors
import rcav2.prompt
import rcav2.model
import rcav2.agent.zuul
from rcav2.worker import Worker
from rcav2.report import Report


class RCAAccelerator(dspy.Signature):
    """You are a CI engineer, your goal is to find the RCA of this build failure.

    Your investigation strategy should be as follows:
    1.  **Start with `job-output.txt`:** Use the `read_errors` tool on this file first to identify the final error or symptom of the failure.
    2.  **Trace back to the root cause:** The errors in `job-output.txt` are often just symptoms. The actual root cause likely occurred earlier. The earlier logs are critical for finding the initial point of failure.
    3.  **Follow the error trail:** Within each file you inspect, follow the sequence of errors to understand the full context of how the problem developed. The ultimate root cause is somewhere in the available logs. Use the `search_errors` tool to find all the evidences. Don't stop reading errors until the root cause is fully diagnosed.
    4.  **Synthesize your findings:** Connect the events from the early logs with the final failure shown in `job-output.txt` to build a complete and accurate root cause analysis.
    """

    job: rcav2.agent.zuul.Job = dspy.InputField()

    errors: dict[str, int] = dspy.InputField(
        desc="list of source and their error count"
    )

    report: Report = dspy.OutputField()


def make_agent(errors: rcav2.errors.Report, worker: Worker) -> dspy.Predict:
    async def read_errors(source: str) -> list[rcav2.errors.Error]:
        """Read the errors contained in a source log, including the before after context"""
        await worker.emit(f"Checking {source}", "progress")
        for logfile in errors.logfiles:
            if logfile.source == source:
                return logfile.errors
        return []

    async def search_errors(regex: str) -> list[rcav2.errors.LogFile]:
        """Search in the logs using a regular expression"""
        await worker.emit(f"Search {regex}", "progress")
        reg = re.compile(regex, re.I)
        logfiles: list[rcav2.errors.LogFile] = []
        for logfile in errors.logfiles:
            for error in logfile.errors:
                if reg.search(error.line):
                    logfiles.append(logfile)
                    break
        return logfiles

    return dspy.ReAct(RCAAccelerator, tools=[read_errors, search_errors])


async def call_agent(
    agent: dspy.Predict,
    job: rcav2.agent.zuul.Job | None,
    errors: rcav2.errors.Report,
    worker: Worker,
) -> Report:
    if not job:
        job = rcav2.agent.zuul.Job(description="", actions=[])
    await worker.emit("Calling RCAAccelerator", "progress")
    errors_count = dict()
    for logfile in errors.logfiles:
        errors_count[logfile.source] = len(logfile.errors)
    agent.set_lm(rcav2.model.get_lm("gemini-2.5-pro", max_tokens=1024 * 1024))
    result = await agent.acall(job=job, errors=errors_count)
    await rcav2.model.emit_dspy_usage(result, worker)
    return result.report
