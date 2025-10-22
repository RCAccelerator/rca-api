# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0
import os

try:
    SF_DOMAIN = os.environ["SF_DOMAIN"]
except KeyError:
    raise ValueError("The SF_DOMAIN environment variable must be set") from None

SF_URL = f"https://{SF_DOMAIN}"

# JIRA configuration (optional - only needed if using JIRA tools)
JIRA_URL = os.environ.get("JIRA_URL")
JIRA_API_KEY = os.environ.get("JIRA_API_KEY")
JIRA_RCA_PROJECT = os.environ.get(
    "JIRA_RCA_PROJECT"
)  # Comma-separated list of projects to search for related tickets during RCA
CA_BUNDLE_PATH = os.environ.get(
    "CA_BUNDLE_PATH", "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
)
COOKIE_FILE = os.environ.get("COOKIE_FILE", ".cookie")
DATABASE_FILE = os.environ.get("DATABASE_FILE", ".db.sqlite3")
