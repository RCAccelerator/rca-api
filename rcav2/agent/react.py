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
    """
    You are a CI engineer, your goal is to find the RCA of this build failure.

    ============================================================================
    INVESTIGATION STRATEGY
    ============================================================================

    1. **Determine Build Stage (REQUIRED if log_url is provided):**
       - This identifies which stage of the build process was reached before failure
       - You MUST use the `check_build_log_directory` tool to determine the stage
       - Check for `logs/controller-0` → If absent, failure was in OpenShift deployment
       - Check for `logs/controller-0/ci-framework-data/tests/` → If present, failure was in tests
       - Otherwise, failure was in OpenStack deployment
       - Use this information to prioritize your error analysis
       - Follow the instructions in the job description for stage-specific analysis

    2. **Examine Final Symptoms:**
       - Examine the errors in `job-output.txt` first
       - This identifies the final error or symptom of the failure

    3. **Trace Back to Root Cause:**
       - The errors in `job-output.txt` are often just symptoms
       - The actual root cause likely occurred earlier
       - The earlier logs are critical for finding the initial point of failure
       - Follow the error trail and try to understand the full context of how the problem developed.
       - It is possible that you do not have the root cause in the errors provided.

    4. **Synthesize Your Findings:**
       - Connect the events from the early logs with the final failure shown in `job-output.txt`
       - The errors closest the event are most likely to be related.
       - Errors that are much earlier though are probably not related.  They may be transient
         or other ignored errors.  You may still want to include them as a potential secondary issues.
       - Build a complete and accurate root cause analysis

    ============================================================================
    TEMPORAL CAUSAL ANALYSIS (CRITICAL)
    ============================================================================

    To identify root causes, you MUST perform temporal analysis with constraints:

    1. **Define Temporal Window:**
       - The final symptom (test failure, deployment error) has a timestamp
       - ONLY consider errors within 30 minutes BEFORE the final symptom
       - Errors hours earlier are likely UNRELATED transient issues
       - Exception: If a service NEVER started, look back to deployment start

    2. **Construct Timeline (Recent Errors Only):**
       - List errors in chronological order within the 30-minute window
       - Include timestamp deltas from final failure
       - Example: "Error at T-25min, Error at T-10min, Failure at T-0min"

    3. **Apply Temporal Causality:**
       - Root cause should be within 30 minutes of symptom
       - Typical causal chains are minutes, not hours
       - Rule: If error A is >1 hour before error B, they are likely unrelated
         UNLESS there is continuous evidence of the issue throughout

    4. **Identify the Causal Chain:**
       - Start from errors close to the failure time
       - Trace backward only if evidence shows continuous problem
       - Document: "Error A (T-20min) → caused → Error B (T-5min) → caused → Failure"
       - DO NOT create chains spanning multiple hours without evidence

    5. **Temporal Validation:**
       - ✅ VALID: Error 10 minutes before failure, clear causal link
       - ⚠️ QUESTIONABLE: Error 1 hour before, may be unrelated
       - ❌ INVALID: Error 6+ hours before, almost certainly unrelated

    Example:
    - ❌ WRONG: "OVN error at 19:15 caused test timeout at 04:38"
      (9 hours apart - likely unrelated)
    - ✅ CORRECT: "OVN errors began at 04:15, continuous throughout,
      tests failed at 04:38" (23 minutes of consistent errors)
    - ✅ CORRECT: "Database unreachable at 04:30, tests timed out at 04:38"
      (8 minutes apart - plausible causal link)

    ============================================================================
    EVIDENCE PRIORITIZATION
    ============================================================================

    When multiple potential root causes exist, prioritize using this hierarchy:

    **Priority 1: Infrastructure Failures** (Most likely root causes)
    - Platform instability (OpenShift/Kubernetes control plane)
    - Core service failures (etcd, API server)
    - Network infrastructure (OVN/OVS, CNI)

    **Priority 2: Service Layer Failures**
    - Database/message queue connectivity
    - Storage service failures
    - Load balancer issues

    **Priority 3: Application Layer Failures**
    - API timeouts
    - Service-specific errors
    - Configuration errors

    **Priority 4: Test Failures** (Usually symptoms, not root causes)
    - Test timeouts
    - Test assertion failures
    - UI unresponsiveness

    Rule: If you find evidence at Priority 1, investigate that FIRST before
    concluding a Priority 3 or 4 issue is the root cause.

    ============================================================================
    ROOT CAUSE REPORTING
    ============================================================================

    Provide a Summary:
       - Provide a concise summary of the root cause analysis
       - The summary should be a brief overview that helps someone quickly understand what went wrong
       - The summary should include the stage at which the root cause occurred
       - The summary MUST also include a small table showing a timeline of ALL of the errors
         in the log files (including those unrelated to the root cause).  Make sure
         the table is well formatted and easy to read.

    You MUST identify at least 2-3 possible root causes of the failure, ranked by likelihood.

    **REQUIRED: Provide Alternative Root Causes:**

    You MUST identify at least 2-3 possible root causes, ranked by likelihood:

    - **Primary Root Cause**: Your highest confidence hypothesis
    - **Secondary Root Cause**: An alternative explanation if primary is wrong
    - **Tertiary Root Cause**: Another plausible explanation (if applicable)

    Why this is critical:
    - Your primary hypothesis may be incorrect
    - Alternative causes give users fallback options
    - Different levels in a cascading failure may all be "root" from different perspectives

    For each root cause, provide:
    - cause: The root cause of the failure, including the stage at which it occurred
    - evidences: The evidence that supports the root cause

    Order root causes by likelihood:
    - Start with the most likely root cause
    - Continue with less likely alternatives
    - ALWAYS provide at least 2 root causes, even if one is much more likely

    **Acknowledge Missing Root Cause:**

    If you cannot find a clear root cause in the logs, you MUST state in your summary:

    "IMPORTANT: The actual root cause may not be present in the available logs.
    Possible external factors:
    - Infrastructure issues (network, storage, hardware)
    - External service dependencies
    - Resource exhaustion (memory, disk, network)
    - Timing/race conditions that don't leave clear log traces

    Recommendation: Investigate system-level metrics, external dependencies,
    and infrastructure health during the failure window."

    Criteria for "missing root cause":
    - No clear errors within 30 minutes of failure
    - All errors are symptoms (timeouts, connection losses)
    - Errors appear simultaneously across multiple services
    - Pattern suggests external trigger not internal cause


    ============================================================================
    JIRA TICKET SEARCH (REQUIRED)
    ============================================================================

    Only AFTER identifying all possible root causes, ALWAYS search for related Jira tickets:

    1. Search for similar error messages
       - Extract key error terms and search in Jira

    2. Look for known bugs or issues
       - Match the failure pattern

    3. Find recent failures
       - Reported in the same area or component

    Use `search_jira_issues` with proper JQL syntax:

    Examples:
    - search_jira_issues('text ~ "cert-manager secrets not found"')
    - search_jira_issues('summary ~ "timeout" AND text ~ "openstackcontrolplane"')

    Remember: Use ~ operator with quoted strings for text searches!

    IMPORTANT: Populate the jira_tickets field in your report with all relevant JIRA tickets.

    For each ticket, include:
    - key: The JIRA ticket key (e.g., "OSPCIX-1234")
    - url: The full URL to the ticket
    - summary: The ticket summary/title

    ============================================================================
    SLACK SEARCH
    ============================================================================

    You can also search for information on Slack:
    - Use `search_slack_messages` to search for error messages or keywords
    - Example: `search_slack_messages('cert-manager secrets not found')`

    ============================================================================
    EXAMPLE ANALYSIS
    ============================================================================

    Example Build: Database connection timeouts during tests

    INCORRECT Analysis:
    "The test failed due to database connection timeouts."
    Problem: This identifies a symptom, not the root cause. Also, it only provides
    one root cause without alternatives.

    CORRECT Analysis:
    1. Timeline construction:
       - 01:15:05 UTC: OVN controller logs "connection failed to br-int.mgmt"
       - 01:26:19 UTC: Cinder logs "Can't connect to MySQL server"
       - 04:38:42 UTC: Tests timeout

    2. Temporal validation:
       - OVN error at 01:15:05 is 3+ hours before test failure at 04:38:42
       - ⚠️ QUESTIONABLE: This is >1 hour gap, but there is continuous evidence
       - Database error at 01:26:19 is also 3+ hours before test failure
       - However, if errors are continuous throughout, this may be valid

    3. Causal chain:
       OVN failure (01:15:05) → network connectivity loss →
       database unreachable (01:26:19) → services non-functional →
       tests timeout (04:38:42)

    4. Root causes (with alternatives):
       PRIMARY: OVN controller connection failure at 01:15:05
       - Earliest independent failure
       - Explains all subsequent symptoms
       - Infrastructure layer (Priority 1)
       - Evidence: Multiple OVN logs show same error

       SECONDARY: Database connectivity loss at 01:26:19
       - May be symptom of #1, but could also be independent issue
       - Evidence: Database connection errors in Cinder and Nova logs
       - Note: If OVN is fixed, this should resolve, but worth investigating

       TERTIARY: Test infrastructure timeout at 04:38:42
       - Likely symptom, but could be test framework bug
       - Evidence: Test runner logs show timeout
       - Note: This is the final symptom, not the root cause

    5. Validation:
       ✓ Temporal: Primary cause occurred before symptoms (with continuous evidence)
       ✓ Causality: Network failure explains database unreachability
       ✓ Independence: No earlier failure explains OVN issue
       ✓ Consistency: Multiple OVN logs show same error
       ✓ Alternatives: Provided 3 root causes with clear ranking

    ============================================================================
    """

    job: rcav2.agent.ansible.Job = dspy.InputField()

    errors: list[rcav2.models.errors.LogFile] = dspy.InputField(
        desc="list of logfiles and their associated errors"
    )

    log_url: str | None = dspy.InputField(
        desc="URL to the build logs for stage analysis"
    )

    report: Report = dspy.OutputField()


def make_agent(errors: rcav2.models.errors.Report, worker: Worker, env) -> dspy.ReAct:
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
                "JIRA client not available. Set JIRA_URL, JIRA_API_KEY and JIRA_RCA_PROJECTS",
                "warning",
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
                "warning",
            )
            return []

        await worker.emit(
            f"Searching slack with query: {query}, count: {count}",
            "progress",
        )
        return env.slack.search_messages(query, count)

    async def check_build_log_directory(directory_path: str) -> dict[str, str | bool]:
        """Check if a directory exists in the build logs.

        Args:
            directory_path: The directory path to check for (e.g., '/tmp/build', '/workspace')

        Returns:
            Dictionary with 'exists' (bool) and 'message' (str) fields
        """
        if not errors.log_url:
            return {"exists": False, "message": "No log URL provided"}

        try:
            await worker.emit(
                f"Checking for directory '{directory_path}' in build logs", "progress"
            )

            # Construct the URL to check: log_url/directory_path
            # Remove leading slash from directory_path to avoid double slashes
            clean_path = directory_path.lstrip("/")
            check_url = f"{errors.log_url.rstrip('/')}/{clean_path}"

            # Try to access the directory URL
            response = await env.httpx.get(check_url, timeout=30.0)

            if response.status_code == 200:
                return {
                    "exists": True,
                    "message": f"Directory '{directory_path}' exists in build logs (accessible at {check_url})",
                }
            elif response.status_code == 404:
                return {
                    "exists": False,
                    "message": f"Directory '{directory_path}' not found in build logs (404 at {check_url})",
                }
            else:
                return {
                    "exists": False,
                    "message": f"Directory '{directory_path}' check failed with status {response.status_code} at {check_url}",
                }

        except Exception as e:
            return {"exists": False, "message": f"Error checking directory: {str(e)}"}

    return dspy.ReAct(
        RCAAccelerator,
        tools=[
            search_jira_issues,
            search_slack_messages,
            check_build_log_directory,
        ],
    )


def create_temporal_error_timeline(
    errors: rcav2.models.errors.Report,
) -> str:
    """Create a temporal error timeline summary from error logs.

    Attempts to extract timestamps and create a chronological timeline.
    Returns a formatted string to be added to the job description.
    """
    import re
    from datetime import datetime

    # Common timestamp patterns
    timestamp_patterns = [
        # ISO 8601: 2025-10-31T19:15:41Z or 2025-10-31 19:15:41
        r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})",
        # RFC3339: 2025-10-31T19:15:41.123Z
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)",
        # Unix timestamp (milliseconds)
        r"(\d{13})",
    ]

    timeline_entries = []

    # Collect all errors with their source
    for logfile in errors.logfiles:
        for error in logfile.errors:
            line = error.line
            timestamp = None
            timestamp_str = None

            # Try to extract timestamp
            for pattern in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    timestamp_str = match.group(1)
                    try:
                        # Try parsing ISO 8601 formats
                        if "T" in timestamp_str or " " in timestamp_str:
                            # Remove timezone if present
                            clean_ts = timestamp_str.replace("Z", "").split(".")[0]
                            timestamp = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                        elif len(timestamp_str) == 13:  # Unix timestamp in ms
                            timestamp = datetime.fromtimestamp(
                                int(timestamp_str) / 1000
                            )
                        break
                    except (ValueError, OverflowError):
                        continue

            # Extract error snippet (first 100 chars)
            error_snippet = line[:100].strip()
            if len(line) > 100:
                error_snippet += "..."

            timeline_entries.append(
                {
                    "timestamp": timestamp,
                    "timestamp_str": timestamp_str,
                    "source": logfile.source,
                    "error": error_snippet,
                }
            )

    # Sort by timestamp if available
    timeline_entries.sort(
        key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min
    )

    # Build timeline summary
    timeline_summary = "\n\n## TEMPORAL ERROR TIMELINE (chronological order):\n\n"
    timeline_summary += "| Timestamp | Source | Error Snippet |\n"
    timeline_summary += "|-----------|--------|---------------|\n"

    entries_with_ts = [e for e in timeline_entries if e["timestamp"]]
    entries_without_ts = [e for e in timeline_entries if not e["timestamp"]]

    # Show entries with timestamps first (up to 20 most recent)
    for entry in entries_with_ts[-20:]:
        entry_timestamp = entry.get("timestamp")
        if entry_timestamp and isinstance(entry_timestamp, datetime):
            ts_str = entry_timestamp.strftime("%Y-%m-%d %H:%M:%S")
        else:
            ts_str = str(entry.get("timestamp_str") or "N/A")
        source = str(entry["source"])[:40]  # type: ignore[index]
        error_snippet = str(entry["error"])[:60]  # type: ignore[index]
        timeline_summary += f"| {ts_str} | {source} | {error_snippet} |\n"

    # Show entries without timestamps if any
    if entries_without_ts:
        timeline_summary += (
            f"\n**Note:** {len(entries_without_ts)} errors could not be timestamped.\n"
        )

    timeline_summary += (
        "\n**Important:** Focus on errors within 30 minutes of the final failure.\n"
    )
    timeline_summary += "Errors hours earlier are likely unrelated transient issues.\n"

    return timeline_summary


async def call_agent(
    agent: dspy.ReAct,
    job: rcav2.agent.ansible.Job | None,
    errors: rcav2.models.errors.Report,
    worker: Worker,
) -> Report:
    if not job:
        job = rcav2.agent.ansible.Job(description="", actions=[])

    # Add log URL to job description if available
    if log_url := errors.log_url:
        job.description += f"\n\nBuild Log URL: {log_url}"

    # Add temporal error timeline to help with temporal analysis
    timeline_summary = create_temporal_error_timeline(errors)
    job.description += timeline_summary

    await worker.emit("Calling RCAAccelerator", "progress")
    # errors_count = dict()
    # for logfile in errors.logfiles:
    #    errors_count[logfile.source] = len(logfile.errors)
    agent.set_lm(rcav2.model.get_lm("gemini-2.5-pro", max_tokens=1024 * 1024))
    result = await agent.acall(job=job, errors=errors.logfiles, log_url=log_url)
    await rcav2.model.emit_dspy_usage(result, worker)
    return result.report
