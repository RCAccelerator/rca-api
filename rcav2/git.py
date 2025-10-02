# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
import urllib.parse
import asyncio


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
    return Path(f"~/.cache/rca/gits/{url.hostname}/{url.path}")


async def run_check(args: list[str], cwd: Path | None = None):
    proc = await asyncio.create_subprocess_exec(*args, cwd=cwd)
    if await proc.wait():
        raise RuntimeError("Command failed: %s" % " ".join(args))


async def ensure_repo(url: str, update: bool = False) -> Path:
    path = url_to_path(url).expanduser()
    if (path / ".git").exists():
        if update:
            await run_check(["git", "fetch"], cwd=path)
            await run_check(["git", "reset", "--hard", "FETCH_HEAD"], cwd=path)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        await run_check(["git", "clone", url, str(path)])
    return path
