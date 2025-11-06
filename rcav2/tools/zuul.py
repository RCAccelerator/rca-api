# Copyright © 2025 Red Hat
# SPDX-License-Identifier: Apache-2.0

import asyncio
import time
from pathlib import Path

import rcav2.auth
import rcav2.tools.git
from rcav2.env import Env
from rcav2.models.zuul_info import ZuulInfo, JobInfo, ProjectInfo, ProviderInfo


async def fetch_weeder_export(env: Env) -> dict:
    """Fetch the raw weeder export"""
    # Ensure we are authenticated, otherwise the redirection will fail to PUT
    await rcav2.auth.ensure_cookie(env)
    url = f"{env.sf_url}/weeder/export"
    return (await env.httpx.get(url, auth=env.auth)).raise_for_status().json()


def read_weeder_export(export: dict) -> ZuulInfo:
    """Process the weeder export"""
    res = ZuulInfo({}, {}, {})
    for job, variants in export["jobs"].items():
        mains = filter(lambda v: v[0]["branch"] in ["main", "master"], variants)
        try:
            [loc, info] = list(mains)[0]
        except IndexError:
            continue
        project = loc["project"]
        project_name = project["project"]
        if project_name not in res.projects:
            provider = project["provider"]
            res.projects[project_name] = ProjectInfo(
                project_name, loc["branch"], provider
            )
            url = loc["url"]
            res.providers.setdefault(
                provider,
                ProviderInfo(provider, url["contents"].rstrip("/"), url["tag"]),
            )
        res.jobs[job] = JobInfo(job, info.get("parent"), loc["path"], project_name)
    return res


def print_job_url(info: ZuulInfo, job_name: str):
    job = info.jobs.get(job_name)
    if not job:
        print(f"Unknown job: {job_name}")
        return
    print(f"{job_name}: {info.job_url(job_name)}")
    if parent := job.parent:
        print_job_url(info, parent)


async def fetch_job_repos(info: ZuulInfo, job_name: str):
    job = info.jobs.get(job_name)
    if not job:
        print(f"Unknown job: {job_name}")
        return
    if url := info.project_git(job.project):
        print(f"{job_name}: {url}")
        await rcav2.tools.git.ensure_repo(url)
    if parent := job.parent:
        await fetch_job_repos(info, parent)


def read_job(path: Path, job_name: str) -> dict | None:
    import yaml

    for obj in yaml.safe_load(open(path)):
        if job := obj.get("job"):
            if job.get("name") == job_name:
                return job
    return None


def as_list(item: str | list[str]) -> list[str]:
    if not isinstance(item, list):
        return [item]
    return item


async def get_job_playbooks(info: ZuulInfo, job_name: str):
    plays: list[Path] = []
    while True:
        job = info.jobs.get(job_name)
        if not job:
            print(f"Unknown job: {job_name}")
            break
        if url := info.project_git(job.project):
            path = await rcav2.tools.git.ensure_repo(url)
            if job_def := read_job(path / job.path, job_name):
                plays.extend(
                    map(lambda play: path / play, as_list(job_def.get("run", [])))
                )
            else:
                print(f"{path}: Couldn't find job: {job_name}")
        if not job.parent:
            break
        job_name = job.parent
    return plays


async def ensure_zuul_info(env: Env) -> ZuulInfo:
    now = time.time()
    if not env.zuul_info or now - env.zuul_info_age > 24 * 3600:
        export = await fetch_weeder_export(env)
        env.zuul_info = read_weeder_export(export)
        env.zuul_info_age = now
    return env.zuul_info


async def amain() -> None:
    import json
    import sys

    env = Env(True)
    try:
        export = json.load(open(".zuul-export.json"))
    except Exception:
        export = await fetch_weeder_export(env)
        json.dump(export, open(".zuul-export.json", "w"))

    info = read_weeder_export(export)
    match sys.argv[1:]:
        case ["url", job_name]:
            print_job_url(info, job_name)
        case ["prepare-workspace", job_name]:
            await fetch_job_repos(info, job_name)
        case ["playbooks", job_name]:
            print(await get_job_playbooks(info, job_name))
        case _:
            print("usage: url job")


def main():
    asyncio.run(amain())
