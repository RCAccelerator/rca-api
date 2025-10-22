# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel


class Evidence(BaseModel):
    error: str
    source: str


class JiraTicket(BaseModel):
    key: str
    url: str
    summary: str


class Report(BaseModel):
    description: str
    evidences: list[Evidence]
    jira_tickets: list[JiraTicket] = []
