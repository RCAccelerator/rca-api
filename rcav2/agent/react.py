# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
A next-gen rca agent that reads the errors as needed
"""

import dspy  # type: ignore[import-untyped]

import rcav2.models.errors
import rcav2.model
import rcav2.agent.ansible
from rcav2.worker import Worker
from rcav2.models.report import Report


class RCAAccelerator(dspy.Signature):
    """You are a CI engineer, your goal is to find the RCA of this build failure.

    Your investigation strategy should be as follows:
    1.  **Start with `job-output.txt`:** Use the `read_errors` tool on this file first to identify the final error or symptom of the failure.
    2.  **Trace back to the root cause:** The errors in `job-output.txt` are often just symptoms. The actual root cause likely occurred earlier. The earlier logs are critical for finding the initial point of failure.
    3.  **Follow the error trail:** Within each file you inspect, follow the sequence of errors to understand the full context of how the problem developed. The ultimate root cause is somewhere in the available logs. Don't stop reading errors until the root cause is fully diagnosed.
    4.  **Synthesize your findings:** Connect the events from the early logs with the final failure shown in `job-output.txt` to build a complete and accurate root cause analysis.

    You should identify all possible root causes of the failure.
    For each root cause, you should provide the following information:
    - cause: The root cause of the failure
    - evidences: The evidence that supports the root cause

    You should order the root causes by the likelihood of the root cause being the actual root cause,
    starting with the most likely root cause.

    After identifying the root causes, ALWAYS search for related Jira tickets to correlate with known issues:
    1. Search for similar error messages - extract key error terms and search in Jira
    2. Look for known bugs or issues that match the failure pattern
    3. Find recent failures reported in the same area or component

    Use search_jira_issues with proper JQL syntax. Examples:
    - search_jira_issues('text ~ "cert-manager secrets not found"')
    - search_jira_issues('summary ~ "timeout" AND text ~ "openstackcontrolplane"')
    Remember: Use ~ operator with quoted strings for text searches!

    You can also search for information on Slack to find discussions related to the failure:
    - Use `search_slack_messages` to search for error messages or keywords.
    - Example: `search_slack_messages('cert-manager secrets not found')`

    IMPORTANT: Populate the jira_tickets field in your report with all relevant JIRA tickets you found.
    For each ticket, include:
    - key: The JIRA ticket key (e.g., "OSPCIX-1234")
    - url: The full URL to the ticket
    - summary: The ticket summary/title
    Use the results from search_jira_issues to populate this field.
    """

    job: rcav2.agent.ansible.Job = dspy.InputField()

    errors: dict[str, int] = dspy.InputField(
        desc="list of source and their error count"
    )

    report: Report = dspy.OutputField()


def make_agent(errors: rcav2.models.errors.Report, worker: Worker, env) -> dspy.ReAct:
    async def read_errors(source: str) -> list[rcav2.models.errors.Error]:
        """Read the errors contained in a source log, including the before after context"""
        await worker.emit(f"Checking {source}", "progress")
        for logfile in errors.logfiles:
            if logfile.source == source:
                return logfile.errors
        return []

    async def search_jira_issues(
        query: str, max_results: int | None = 50
    ) -> list[dict[str, str | None]]:
        """Searches jira issues using JQL (Jira query language).
        Returns list of issues with key, url, summary, status, and description.
        The 'url' field contains the full link to the JIRA ticket.
        Returns 50 results by default, for more results set max_results.
        Use the 'key' field from results with get_jira_issue for more details.
        If JIRA_RCA_PROJECT is configured, automatically filters to that project.

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
                "JIRA client not available. Set JIRA_URL and JIRA_API_KEY", "error"
            )
            return []

        await worker.emit(
            f"Searching issues with query: {query}, max_results: {max_results}",
            "progress",
        )
        return env.jira.search_jira_issues(query, max_results)

    async def search_slack_messages(
        query: str, count: int | None = 20
    ) -> list[dict[str, str | None]]:
        """Searches slack messages.
        Returns list of messages with text, user, permalink, and channel.
        Returns 20 results by default, for more results set count.
        """
        if not env.slack:
            await worker.emit(
                "Slack client not available. Set SLACK_API_KEY and SLACK_SEARCH_CHANNELS",
                "error",
            )
            return []

        await worker.emit(
            f"Searching slack with query: {query}, count: {count}",
            "progress",
        )
        return env.slack.search_messages(query, count)

    return dspy.ReAct(
        RCAAccelerator, tools=[read_errors, search_jira_issues, search_slack_messages]
    )


async def call_agent(
    agent: dspy.ReAct,
    job: rcav2.agent.ansible.Job | None,
    errors: rcav2.models.errors.Report,
    worker: Worker,
) -> Report:
    if not job:
        job = rcav2.agent.ansible.Job(description="", actions=[])
    await worker.emit("Calling RCAAccelerator", "progress")
    errors_count = dict()
    for logfile in errors.logfiles:
        errors_count[logfile.source] = len(logfile.errors)
    agent.set_lm(rcav2.model.get_lm("gemini-2.5-pro", max_tokens=1024 * 1024))
    result = await agent.acall(job=job, errors=errors_count)
    await rcav2.model.emit_dspy_usage(result, worker)
    return result.report
