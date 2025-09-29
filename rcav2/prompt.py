# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import rcav2.errors


def keep_context(source: str) -> bool:
    """Decide if the before/after lines should be kept"""
    return source == "job-output" or "ansible" in source


def report_to_prompt(report: rcav2.errors.Report) -> str:
    """Convert a report to a LLM prompt

    >>> report_to_prompt(rcav2.errors.json_to_report(TEST_REPORT))
    'The following errors are from a Zuul job named tox:\\n\\n## zuul/overcloud.log\\noops'
    """
    lines = [f"The following errors are from a {report.target}:"]
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
