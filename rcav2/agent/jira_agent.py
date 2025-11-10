# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

from rcav2.worker import Worker
from rcav2.env import Env
from rcav2.models.report import JiraTicket, PossibleRootCause
from rcav2.model import dspy
import rcav2.model


class JiraAgent(dspy.Signature):
    """You are a CI engineer, your goal is to find relevant JIRA issue for the provided build report.

    Use search_jira_issues with proper JQL syntax. Examples:
    - search_jira_issues('text ~ "cert-manager secrets not found"')
    - search_jira_issues('summary ~ "timeout" AND text ~ "openstackcontrolplane"')
    Remember: Use ~ operator with quoted strings for text searches!

    IMPORTANT: Populate the jira_tickets field in your report with all relevant JIRA tickets you found.
    For each ticket, include:
    - key: The JIRA ticket key (e.g., "OSPCIX-1234")
    - url: The full URL to the ticket
    - summary: The ticket summary/title
    Use the results from search_jira_issues to populate this field.
    """

    summary: str = dspy.InputField()
    possible_root_causes: list[PossibleRootCause] = dspy.InputField()
    tickets: list[JiraTicket] = dspy.OutputField()


def make_agent(worker: Worker, env: Env) -> dspy.ReAct:
    async def search_jira_issues(query: str) -> list[dict[str, str | None]]:
        """Searches jira issues using JQL (Jira query language).
        Returns list of issues with key, url, summary, status, and description.
        The 'url' field contains the full link to the JIRA ticket.

        JQL Query Syntax - IMPORTANT:
        - Text search: text ~ "error message" (quotes required for phrases)
        - Summary search: summary ~ "keyword"
        - Description search: description ~ "error text"
        - Multiple terms: summary ~ "cert-manager" AND text ~ "timeout"
        - OR condition: summary ~ "error" OR description ~ "failure"

        Valid operators: ~ (contains), !~, =, !=, IN, NOT IN
        Always use ~ for text searches with quoted strings."""
        if not env.jira:
            await worker.emit(
                "JIRA client not available. Set JIRA_URL, JIRA_API_KEY and JIRA_RCA_PROJECTS",
                "error",
            )
            return []

        await worker.emit(
            f"Searching issues with query: {query}",
            "progress",
        )
        return env.jira.search_jira_issues(query)

    return dspy.ReAct(JiraAgent, tools=[search_jira_issues])


async def call_agent(
    agent: dspy.ReAct,
    summary: str,
    possible_root_causes: list[PossibleRootCause],
    worker: Worker,
) -> list[JiraTicket]:
    await worker.emit("Calling JiraAgent", "progress")
    result = await agent.acall(
        summary=summary, possible_root_causes=possible_root_causes
    )
    await rcav2.model.emit_dspy_usage(result, worker)
    return result.tickets
