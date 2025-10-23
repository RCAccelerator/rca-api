# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import dspy  # type: ignore[import-untyped]

import rcav2.errors
import rcav2.agent.zuul
from rcav2.report import Report
from rcav2.worker import Worker


class RCAAccelerator(dspy.Signature):
    """You are a CI engineer, your goal is to find the RCA of this build failure.

    You are given a description of the job and the errors found in the logs.

    Your investigation strategy should be as follows:
    1.  **Recognize Symptoms:** The errors in `job-output.txt` are often just symptoms. The actual root cause likely occurred earlier.
    2.  **Trace Back to the Root Cause:** Use the log file list to examine logs that came before `job-output.txt`. These earlier logs are critical for finding the initial point of failure.
    3.  **Analyze All Evidence:** It is crucial that you analyze all the provided errors before drawing a conclusion. Do not stop at the first error you find.
    4.  **Identify the Root Cause:** After a full analysis, identify the definitive root cause.
    """

    job: rcav2.agent.zuul.Job = dspy.InputField()

    # TODO: provide tools instead to access the raw reports. Then remove the errors input
    errors: str = dspy.InputField()

    report: Report = dspy.OutputField()


def make_agent() -> dspy.Predict:
    return dspy.ChainOfThought(RCAAccelerator, max_tokens=1024 * 1024)


async def call_agent(
    agent: dspy.Predict,
    job: rcav2.agent.zuul.Job | None,
    errors: rcav2.errors.Report,
    worker: Worker,
) -> Report:
    if not job:
        job = rcav2.agent.zuul.Job(description="", actions=[])
    await worker.emit("Calling RCAAccelerator", "progress")
    agent.set_lm(rcav2.model.get_lm("gemini-2.5-pro", max_tokens=1024 * 1024))
    errors_report = rcav2.prompt.report_to_prompt(errors)
    result = await agent.acall(job=job, errors=errors_report)
    await rcav2.model.emit_dspy_usage(result, worker)
    return result.report


def keep_context(source: str) -> bool:
    """Decide if the before/after lines should be kept"""
    return source == "job-output" or "ansible" in source


def report_to_prompt(report: rcav2.errors.Report) -> str:
    """Convert a report to a LLM prompt

    >>> report_to_prompt(rcav2.errors.json_to_report(TEST_REPORT))
    '\\n## zuul/overcloud.log\\noops'
    """
    lines = []
    for logfile in report.logfiles:
        lines.append(f"\n## {logfile.source}")
        context = keep_context(logfile.source)
        for error in logfile.errors:
            if context:
                for line in error.before:
                    lines.append(line)
            lines.append(error.line)
            if context:
                for line in error.after:
                    lines.append(line)
    return "\n".join(lines)


TEST_REPORT = dict(
    target={"Zuul": {"job_name": "tox"}},
    log_reports=[
        dict(
            source={"RawFile": {"Remote": [12, "example.com/zuul/overcloud.log"]}},
            anomalies=[
                {"before": [], "anomaly": {"line": "oops", "pos": 42}, "after": []}
            ],
        )
    ],
)
