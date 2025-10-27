# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

from jira import JIRA, JIRAError
import logging

logger = logging.getLogger(__name__)


class Jira:
    def __init__(self, server: str, token: str, projects: list[str]):
        self.client = JIRA(server=server, token_auth=token)
        self.projects = projects

    def search_jira_issues(
        self, query: str, max_results: int = 50
    ) -> list[dict[str, str | None]]:
        # Add project filter if configured
        match self.projects:
            case []:
                pass
            case [project]:
                query = f"project = {project} AND ({query})"
            case projects:
                query = f"project IN ({', '.join(projects)}) AND ({query})"

        # Perform search
        logger.info("Searching JIRA: %s", query)
        try:
            results = self.client.search_issues(query, maxResults=max_results)
        except JIRAError as e:
            logger.exception(f"Failed to search issues with query '{query}': {e}")
            return []

        # Convert Issue objects to serializable dicts
        jira_base_url = self.client._options["server"]
        result_list = []
        for issue in results:
            issue_dict = dict(
                key=issue.key,
                url=f"{jira_base_url}/browse/{issue.key}",
                summary=getattr(issue.fields, "summary", None),
                status=str(getattr(issue.fields, "status", None)),
                description=getattr(issue.fields, "description", None),
            )
            result_list.append(issue_dict)
        return result_list
