# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the system configuration using pydantic_settings
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SF_DOMAIN: str
    LLM_GEMINI_KEY: str

    # Model config
    LLM_TEMPERATURE: float = 0.5
    RCA_IGNORE_LINES: str | None = None
    DSPY_CACHE: bool = False
    DSPY_DEBUG: bool = False

    # Opik configuration
    OPIK_DISABLED: bool = False
    OPIK_PROJECT_NAME: str = "rca-api"
    OPIK_TAGS: str = ""
    OPIK_URL_OVERRIDE: str = ""

    # Jira config
    JIRA_URL: str
    JIRA_API_KEY: str
    # Comma-separated list of projects to search for related tickets during RCA
    JIRA_RCA_PROJECTS: str

    # Slack config
    SLACK_API_KEY: str = ""
    SLACK_SEARCH_CHANNELS: str = ""

    # Internal config
    CA_BUNDLE_PATH: str = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
    COOKIE_FILE: str = ".cookie"
    JOB_DESCRIPTION_FILE: str = "JOB_DESCRIPTION_FILE"


def get_opik_tags(tags_str) -> list[str]:
    """Get additional Opik tags from environment variable, defaulting to empty list.

    Supports both comma-separated and space-separated tags:
    - Comma-separated: "tag1,tag2,tag3" or "tag1, tag2, tag3"
    - Space-separated: "tag1 tag2 tag3"
    - Mixed: "tag1, tag2 tag3" (comma takes precedence)
    """
    if not tags_str:
        return []
    # Support both comma-separated and space-separated tags
    # If comma is present, split by comma; otherwise split by space
    if "," in tags_str:
        # Comma-separated: split by comma and strip each tag
        tags = [tag.strip() for tag in tags_str.split(",")]
    else:
        # Space-separated: split by whitespace
        tags = tags_str.split()
    # Filter out empty strings
    return [tag for tag in tags if tag]
