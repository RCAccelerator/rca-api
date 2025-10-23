# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
A next-gen rca agent that reads the errors as needed
"""

from typing import Any

import dspy  # type: ignore[import-untyped]

import rcav2.errors
import rcav2.prompt
import rcav2.model
import rcav2.agent.zuul
from rcav2.worker import Worker
from rcav2.report import Report

from jira import JIRAError


class RCAAccelerator(dspy.Signature):
    """You are a CI engineer, your goal is to find the RCA of this build failure.

    You are given a description of the job and the list of logs file.
    Use the read_errors tool to identify the root cause.
    Starts with the job-output.txt, and check the other logs to collect evidence.
    Don't stop reading errors until the root cause is fully diagnosed.

    After identifying the root cause, ALWAYS search for related Jira tickets to correlate with known issues:
    1. Search for similar error messages - extract key error terms and search in Jira
    2. Look for known bugs or issues that match the failure pattern
    3. Find recent failures reported in the same area or component

    Use search_jira_issues with JQL queries to find relevant tickets, then use get_jira_issue
    to retrieve detailed information about promising matches.

    IMPORTANT: At the end of your report description, include a "Related Jira Tickets" section.
    List all relevant JIRA tickets you found as HTML links using this format:
    <a href="url">KEY - Summary</a>
    Use the 'url' field from search_jira_issues results. Include all relevant tickets.
    """

    job: rcav2.agent.zuul.Job = dspy.InputField()

    errors: dict[str, int] = dspy.InputField(
        desc="list of source and their error count"
    )

    report: Report = dspy.OutputField()


def make_agent(errors: rcav2.errors.Report, worker: Worker, env) -> dspy.Predict:
    async def read_errors(source: str) -> list[rcav2.errors.Error]:
        """Read the errors contained in a source log, including the before after context"""
        await worker.emit(f"Checking {source}", "progress")
        for logfile in errors.logfiles:
            if logfile.source == source:
                return logfile.errors
        return []

    async def search_jira_issues(
        query: str, max_results: int | None = 50
    ) -> list[dict[str, Any]]:
        """Searches jira issues using JQL (Jira query language).
        Returns list of issues with key, url, summary, status, and description.
        The 'url' field contains the full link to the JIRA ticket.
        Returns 50 results by default, for more results set max_results.
        Use the 'key' field from results with get_jira_issue for more details.
        If JIRA_RCA_PROJECT is configured, automatically filters to that project."""
        if not env.jira_client:
            await worker.emit(
                "JIRA client not available. Set JIRA_URL and JIRA_API_KEY", "error"
            )
            return []

        # Add project filter if configured
        final_query = query
        if env.jira_rca_project:
            # If query doesn't already contain "project =", add it
            if "project" not in query.lower():
                # Support multiple projects (comma-separated)
                projects = [p.strip() for p in env.jira_rca_project.split(",")]
                if len(projects) == 1:
                    final_query = f"project = {projects[0]} AND ({query})"
                else:
                    project_list = ", ".join(projects)
                    final_query = f"project IN ({project_list}) AND ({query})"

        await worker.emit(
            f"Searching issues with query: {final_query}, max_results: {max_results}",
            "progress",
        )
        try:
            result = env.jira_client.search_issues(final_query, maxResults=max_results)
            # Convert Issue objects to serializable dicts
            jira_base_url = env.jira_client._options["server"]
            result_list = []
            for issue in result if result else []:
                issue_dict = {
                    "key": issue.key,
                    "url": f"{jira_base_url}/browse/{issue.key}",
                    "summary": getattr(issue.fields, "summary", ""),
                    "status": str(getattr(issue.fields, "status", "")),
                    "description": getattr(issue.fields, "description", ""),
                }
                result_list.append(issue_dict)

            await worker.emit(
                f"Found {len(result_list)} issues for query: {final_query}",
                "progress",
            )
            return result_list
        except JIRAError as e:
            env.log.error(f"Failed to search issues with query '{final_query}': {e}")
            await worker.emit(f"JIRA search failed: {e}", "error")
            return []

    return dspy.ReAct(RCAAccelerator, tools=[read_errors, search_jira_issues])


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
