# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the global environment shared by the other modules.
"""

import ssl
import httpx
import pathlib
import logging
import time
from httpx_gssapi import HTTPSPNEGOAuth, OPTIONAL  # type: ignore
import rcav2.models.errors
from rcav2.tools.jira_client import Jira
from rcav2.tools.slack import SlackClient
from rcav2.models.zuul_info import ZuulInfo
from rcav2.config import (
    SF_DOMAIN,
    CA_BUNDLE_PATH,
    JIRA_URL,
    JIRA_API_KEY,
    JIRA_RCA_PROJECTS,
    SLACK_API_KEY,
    SLACK_SEARCH_CHANNELS,
)


class Env:
    """The RCAv2 application environment"""

    def __init__(self, debug, cookie_path: str | None = None):
        lvl = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(format="%(asctime)s %(levelname)9s %(message)s", level=lvl)
        self.cookie = None
        self.cookie_path = cookie_path
        self.cookie_age = 0.0
        self.logjuicer_report: rcav2.models.errors.Report | None = None
        self.zuul_info: ZuulInfo | None = None
        self.zuul_info_age = 0.0
        self.httpx = make_httpx_client(cookie_path)
        self.auth = HTTPSPNEGOAuth(mutual_authentication=OPTIONAL)
        self.log = logging.getLogger("rcav2")
        self.jira: Jira | None = None
        self.slack: SlackClient | None = None
        self.extra_description: str | None = None

        # Initialize JIRA client if credentials are available
        if JIRA_URL and JIRA_API_KEY and JIRA_RCA_PROJECTS:
            self.jira = Jira(JIRA_URL, JIRA_API_KEY, JIRA_RCA_PROJECTS.split(","))

        # Initialize Slack client if credentials are available
        if SLACK_API_KEY and SLACK_SEARCH_CHANNELS:
            channels = SLACK_SEARCH_CHANNELS.split(",")
            self.slack = SlackClient(SLACK_API_KEY, channels)

    def close(self):
        if self.cookie and self.cookie_path:
            with open(self.cookie_path, "w") as f:
                f.write(self.cookie)


def make_httpx_client(cookie_path: str | None) -> httpx.AsyncClient:
    """Setup the httpx client using local CA."""
    # Load local CA
    verify = True
    if pathlib.Path(CA_BUNDLE_PATH).exists():
        verify = ssl.create_default_context(cafile=CA_BUNDLE_PATH)  # type: ignore

    # Restore cookies
    cookies = httpx.Cookies()
    if cookie_path:
        cookie_file = pathlib.Path(cookie_path)
        try:
            if time.time() - cookie_file.stat().st_mtime > 24 * 3600:
                cookie_file.unlink()
            else:
                cookie = cookie_file.read_text()
                cookies.set("mod_auth_openidc_session", cookie, domain=SF_DOMAIN)
        except FileNotFoundError:
            pass

    # Create the client
    return httpx.AsyncClient(follow_redirects=True, verify=verify, cookies=cookies)
