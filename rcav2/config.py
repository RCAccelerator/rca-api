# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the system configuration using pydantic_settings
"""

from typing import Annotated
from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


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
    OPIK_TAGS: Annotated[list[str], NoDecode] = []
    OPIK_URL_OVERRIDE: str | None = None

    # Jira config
    JIRA_URL: str | None = None
    JIRA_API_KEY: str | None = None
    # Comma-separated list of projects to search for related tickets during RCA
    JIRA_RCA_PROJECTS: Annotated[list[str], NoDecode] = []

    # Slack config
    SLACK_API_KEY: str | None = None
    SLACK_SEARCH_CHANNELS: Annotated[list[str], NoDecode] = []

    # Internal config
    CA_BUNDLE_PATH: str = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
    COOKIE_FILE: str = ".cookie"
    JOB_DESCRIPTION_FILE: str | None = None

    @field_validator("OPIK_TAGS", mode="before")
    @classmethod
    def parse_tags(cls, v):
        return parse_list(v)

    @field_validator("JIRA_RCA_PROJECTS", mode="before")
    @classmethod
    def parse_projects(cls, v):
        return parse_list(v)

    @field_validator("SLACK_SEARCH_CHANNELS", mode="before")
    @classmethod
    def parse_channels(cls, v):
        return parse_list(v)


def parse_list(v):
    """Parse comma separated list"""
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return v
