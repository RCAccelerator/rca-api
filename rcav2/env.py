# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module defines the global environment shared by the other modules.
"""

import ssl
import re
import httpx
import pathlib
import logging
import time
from httpx_gssapi import HTTPSPNEGOAuth, OPTIONAL  # type: ignore
import rcav2.models.errors
from rcav2.tools.jira_client import Jira
from rcav2.tools.slack import SlackClient
from rcav2.models.zuul_info import ZuulInfo
from rcav2.config import Settings


class Env:
    """The RCAv2 application environment"""

    def __init__(
        self,
        debug,
        base_settings: Settings | None = None,
    ):
        if not base_settings:
            # pydantic is magic and it auto load the missing named argument from the environment.
            settings = Settings()  # type: ignore
        else:
            settings = base_settings
        self.settings = settings
        self.sf_url = f"https://{settings.SF_DOMAIN}"

        lvl = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(format="%(asctime)s %(levelname)9s %(message)s", level=lvl)
        self.cookie = None
        self.cookie_path = settings.COOKIE_FILE
        self.cookie_age = 0.0
        self.logjuicer_report: rcav2.models.errors.Report | None = None
        self.zuul_info: ZuulInfo | None = None
        self.zuul_info_age = 0.0
        self.httpx = make_httpx_client(
            settings.SF_DOMAIN, settings.CA_BUNDLE_PATH, settings.COOKIE_FILE
        )
        self.auth = HTTPSPNEGOAuth(mutual_authentication=OPTIONAL)
        self.log = logging.getLogger("rcav2")
        self.jira: Jira | None = None
        self.slack: SlackClient | None = None
        self.extra_description: str | None = None

        self.ignore_lines: re.Pattern | None = None
        if settings.RCA_IGNORE_LINES:
            self.ignore_lines = re.compile(settings.RCA_IGNORE_LINES)

        # Initialize JIRA client if credentials are available
        if settings.JIRA_URL and settings.JIRA_API_KEY and settings.JIRA_RCA_PROJECTS:
            self.jira = Jira(
                settings.JIRA_URL,
                settings.JIRA_API_KEY,
                settings.JIRA_RCA_PROJECTS,
            )

        # Initialize Slack client if credentials are available
        if settings.SLACK_API_KEY and settings.SLACK_SEARCH_CHANNELS:
            self.slack = SlackClient(
                settings.SLACK_API_KEY, settings.SLACK_SEARCH_CHANNELS
            )

    def close(self):
        if self.cookie and self.cookie_path:
            with open(self.cookie_path, "w") as f:
                f.write(self.cookie)


def make_httpx_client(
    sf_domain: str, ca_bundle_path: str, cookie_path: str | None
) -> httpx.AsyncClient:
    """Setup the httpx client using local CA."""
    # Load local CA
    verify = True
    if pathlib.Path(ca_bundle_path).exists():
        verify = ssl.create_default_context(cafile=ca_bundle_path)  # type: ignore

    # Restore cookies
    cookies = httpx.Cookies()
    if cookie_path:
        cookie_file = pathlib.Path(cookie_path)
        try:
            if time.time() - cookie_file.stat().st_mtime > 24 * 3600:
                cookie_file.unlink()
            else:
                cookie = cookie_file.read_text()
                cookies.set("mod_auth_openidc_session", cookie, domain=sf_domain)
        except FileNotFoundError:
            pass

    # Create the client
    return httpx.AsyncClient(follow_redirects=True, verify=verify, cookies=cookies)
