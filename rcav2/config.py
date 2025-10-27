# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the system configuration from the process os.environ.
"""

import os

try:
    SF_DOMAIN = os.environ["SF_DOMAIN"]
except KeyError:
    raise ValueError("The SF_DOMAIN environment variable must be set") from None

SF_URL = f"https://{SF_DOMAIN}"

# JIRA configuration (optional - only needed if using JIRA tools)
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_API_KEY = os.environ.get("JIRA_API_KEY")
# Comma-separated list of projects to search for related tickets during RCA
JIRA_RCA_PROJECTS = os.environ.get("JIRA_RCA_PROJECTS")

# Slack configuration (optional - only needed if using slack tools)
SLACK_API_KEY = os.environ.get("SLACK_API_KEY")
SLACK_SEARCH_CHANNELS = os.environ.get("SLACK_SEARCH_CHANNELS")

CA_BUNDLE_PATH = os.environ.get(
    "CA_BUNDLE_PATH", "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
)
COOKIE_FILE = os.environ.get("COOKIE_FILE", ".cookie")
DATABASE_FILE = os.environ.get("DATABASE_FILE", ".db.sqlite3")
JOB_DESCRIPTION_FILE = os.environ.get("JOB_DESCRIPTION_FILE")

# Opik configuration
OPIK_API_KEY = os.environ.get("OPIK_API_KEY")
OPIK_PROJECT_NAME = os.environ.get("OPIK_PROJECT_NAME", "rca-mcp")
OPIK_URL_OVERRIDE = os.environ.get("OPIK_URL_OVERRIDE")  # For self-hosted deployments
OPIK_WORKSPACE = os.environ.get("OPIK_WORKSPACE")  # For cloud deployments
