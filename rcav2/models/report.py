# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel


class Evidence(BaseModel):
    error: str
    source: str


class PossibleRootCause(BaseModel):
    cause: str
    evidences: list[Evidence]


class JiraTicket(BaseModel):
    key: str
    url: str
    summary: str


class Report(BaseModel):
    summary: str = ""
    possible_root_causes: list[PossibleRootCause] = []
    jira_tickets: list[JiraTicket] = []
