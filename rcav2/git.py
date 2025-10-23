# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

"""
This module contains helper to work with git.
"""

from pathlib import Path
import urllib.parse
import asyncio


workspace_root = Path("~/.cache/rca/gits")


def url_to_path(urlstring: str) -> Path:
    """Convert a git url into a local path

    >>> url_to_path("git@gitlab.local:my/project")
    PosixPath('~/.cache/rca/gits/gitlab.local/my/project')
    >>> url_to_path("https://gitlab.local/my/project")
    PosixPath('~/.cache/rca/gits/gitlab.local/my/project')
    """
    if urlstring.startswith("git@"):
        [host, path] = urlstring.split(":", 1)
        urlstring = f"git://{host}/{path}"
    url = urllib.parse.urlparse(urlstring, scheme="git")
    if not url.hostname or not url.path:
        raise RuntimeError(f"{urlstring}: invalid url: {url}")
    path = url.path[1:]
    if path.endswith(".git"):
        path = path[:-4]
    return workspace_root / url.hostname / path


async def run_check(args: list[str], cwd: Path | None = None):
    proc = await asyncio.create_subprocess_exec(*args, cwd=cwd)
    if await proc.wait():
        raise RuntimeError("Command failed: %s" % " ".join(args))


async def ensure_repo(url: str, update: bool = False) -> Path:
    path = url_to_path(url).expanduser()
    if (path / ".git").exists():
        if update:
            print(f"Updating {path}...")
            await run_check(["git", "fetch"], cwd=path)
            await run_check(["git", "reset", "--hard", "FETCH_HEAD"], cwd=path)
    else:
        print(f"Cloning {path}...")
        path.parent.mkdir(parents=True, exist_ok=True)
        await run_check(["git", "clone", url, str(path)])
    return path
