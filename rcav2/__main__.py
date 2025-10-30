# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module is the CLI entrypoint for debugging purpose.
"""

import argparse
import asyncio
import re
import os

import rcav2.env
import rcav2.model
import rcav2.workflows
from rcav2.config import COOKIE_FILE
from rcav2.worker import CLIWorker


def usage():
    parser = argparse.ArgumentParser(description="Root Cause Analysis (RCA)")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--workflow")
    parser.add_argument("URL", help="The build URL")
    return parser.parse_args()


async def run_cli() -> None:
    args = usage()
    env = rcav2.env.Env(args.debug, cookie_path=COOKIE_FILE)
    if ignore_str := os.environ.get("RCA_IGNORE_LINES"):
        env.ignore_lines = re.compile(ignore_str)
    try:
        # Prepare dspy
        rcav2.model.init_dspy()

        # Run workflow...
        await rcav2.workflows.run_workflow(
            env, None, args.workflow, args.URL, CLIWorker()
        )
    finally:
        env.close()


def main():
    asyncio.run(run_cli())
