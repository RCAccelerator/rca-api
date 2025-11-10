# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import re

import rcav2.models.errors
import rcav2.agent.ansible
from rcav2.models.report import PossibleRootCause
from rcav2.worker import Worker
from rcav2.model import dspy


class RCAAccelerator(dspy.Signature):
    """
    You are a CI engineer, your goal is to find the RCA of this build failure.

    ============================================================================
    INVESTIGATION STRATEGY
    ============================================================================

    1. **Start with `job-output.txt`:**
       - Use the `read_errors` tool on this file first
       - This identifies the final error or symptom of the failure

    2. **Trace back to the root cause:**
       - The errors in `job-output.txt` are often just symptoms
       - The actual root cause likely occurred earlier
       - The earlier logs are critical for finding the initial point of failure

    3. **Follow the error trail:**
       - Within each file you inspect, follow the sequence of errors
       - Understand the full context of how the problem developed
       - The ultimate root cause is somewhere in the available logs
       - Use the `search_errors` tool to find all the evidences
       - Don't stop reading errors until the root cause is fully diagnosed

    4. **Synthesize your findings:**
       - Connect the events from the early logs with the final failure shown in `job-output.txt`
       - Build a complete and accurate root cause analysis

    5. **Identify all possible root causes:**
       - After a full analysis, identify all possible root causes (usually 1-3 possibilities)

    ============================================================================
    ROOT CAUSE REPORTING
    ============================================================================

    Provide a Summary:
    - Provide a concise summary of the root cause analysis
    - The summary should be a brief overview that helps someone quickly understand what went wrong
    - The summary should include the stage at which the root cause occurred
    - The summary should also include a small table showing the timeline
      for the errors that you have identified

    You should identify all possible root causes of the failure.

    For each root cause, provide:
    - cause: The root cause of the failure
    - evidences: The evidence that supports the root cause

    You should order the root causes by the likelihood of the root cause being the actual
    root cause, starting with the most likely root cause.
    """

    job: rcav2.agent.ansible.Job = dspy.InputField()

    # TODO: provide tools instead to access the raw reports. Then remove the errors input
    errors: str = dspy.InputField()

    possible_root_causes: list[PossibleRootCause] = dspy.OutputField()


def make_agent(errors: rcav2.models.errors.Report, worker: Worker) -> dspy.ReAct:
    async def read_errors(source: str) -> list[rcav2.models.errors.Error]:
        """Read the errors contained in a source log, including the before after context"""
        await worker.emit(f"Checking {source}", "progress")
        for logfile in errors.logfiles:
            if logfile.source == source:
                return logfile.errors
        return []

    async def search_errors(regex: str) -> list[rcav2.models.errors.LogFile]:
        """Search in the logs using a regular expression"""
        await worker.emit(f"Search {regex}", "progress")
        reg = re.compile(regex, re.I)
        logfiles: list[rcav2.models.errors.LogFile] = []
        for logfile in errors.logfiles:
            for error in logfile.errors:
                if reg.search(error.line):
                    logfiles.append(logfile)
                    break
        return logfiles

    return dspy.ReAct(RCAAccelerator, tools=[read_errors, search_errors])


async def call_agent(
    agent: dspy.ReAct,
    job: rcav2.agent.ansible.Job | None,
    errors: rcav2.models.errors.Report,
    worker: Worker,
) -> list[PossibleRootCause]:
    if not job:
        job = rcav2.agent.ansible.Job(description="", actions=[])

    # Add log URL to job description if available
    if log_url := errors.log_url:
        job.description += f"\n\nBuild Log URL: {log_url}"

    await worker.emit("Calling RCAAccelerator", "progress")
    errors_count = dict()
    for logfile in errors.logfiles:
        errors_count[logfile.source] = len(logfile.errors)
    result = await agent.acall(job=job, errors=errors_count)
    await rcav2.model.emit_dspy_usage(result, worker)
    return result.possible_root_causes
