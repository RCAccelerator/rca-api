# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module handles the authentication logic.
"""

import os
import subprocess
import httpx
import time
from .config import SF_URL
from .env import Env


# TODO: make this async?
def ensure_kerberos():
    """Ensure kerberos ticket is configured."""
    try:
        subprocess.check_call(["klist", "-s"])
    except subprocess.CalledProcessError:
        if pwd := os.environ.get("KRB_PASS"):
            cmd = ["kinit", os.environ["KRB_USER"]]
            subprocess.run(
                cmd, input=pwd.encode("utf-8"), stdout=subprocess.PIPE
            ).check_returncode()
        else:
            raise RuntimeError("No kerberos auth available, please run kinit")


async def get_oidc_cookie(env: Env):
    """Fetch the OIDC cookie."""
    try:
        (await env.httpx.get(SF_URL, auth=env.auth)).raise_for_status()
    except httpx.ConnectError as e:
        raise RuntimeError(f"Connection to {SF_URL} failed: {e}. ") from e
    return env.httpx.cookies["mod_auth_openidc_session"]


async def ensure_cookie(env: Env):
    """Ensure the OIDC cookie is fresh in the env."""
    now = time.time()
    if not env.cookie or now - env.cookie_age > (23.8 * 3600):
        ensure_kerberos()
        env.cookie = await get_oidc_cookie(env)
        env.cookie_age = now
