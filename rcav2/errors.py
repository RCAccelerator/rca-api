# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module contains helpers to pre-process a LogJuicer report.
"""

from pydantic import BaseModel


class Error(BaseModel):
    before: list[str]
    line: str
    pos: int
    after: list[str]


class LogFile(BaseModel):
    source: str
    errors: list[Error]


class Report(BaseModel):
    target: str
    logfiles: list[LogFile]


def read_source(source) -> str:
    """Convert absolute source url into a relative path.

    >>> read_source({'RawFile': {'Remote': [12, 'example.com/zuul/overcloud.log']}})
    'zuul/overcloud.log'
    """
    match source:
        case {"RawFile": {"Remote": [pos, path]}}:
            return path[pos:]
        case {"TarFile": [{"Remote": [pos, _]}, _, path]}:
            return path[pos:]
        case _:
            return f"Unknown source: {source}"


def read_target(target) -> str:
    """Convert a target description.

    >>> read_target({'Zuul': {'job_name': 'tox'}})
    'tox'
    """
    match target:
        case {"Zuul": build}:
            return build["job_name"]
        case _:
            return f"Unknown target: {target}"


def read_error(anomaly) -> Error:
    return Error(
        before=anomaly["before"],
        line=anomaly["anomaly"]["line"],
        pos=anomaly["anomaly"]["pos"],
        after=anomaly["after"],
    )


def read_logfile(log_report) -> LogFile:
    return LogFile(
        source=read_source(log_report["source"]),
        errors=list(map(read_error, log_report["anomalies"])),
    )


def json_to_report(report) -> Report:
    return Report(
        target=read_target(report["target"]),
        logfiles=list(map(read_logfile, report["log_reports"])),
    )


def report_to_json(report: Report) -> dict:
    return report.model_dump()
