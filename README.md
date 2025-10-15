# rca-api

rca-api is a tool designed to assist CI engineers in determining the root cause of build failures.

## Overview

At a high level, the purpose of rca-api is to create a report to diagnose a build failure:

- Ingest the logs.
- Use LLM to summarize the errors.
- Contextual integration using tools to enrich the report.

rca-api is presently usable as a FastAPI but the goal is to make it available as
a LLM tool/MCP.

## Usage

To fully leverage rca-api, integrate the API and frontend into an existing dashboard:

### Integrate FastAPI

- Add `"rcav2 @ git+https://github.com/RCAccelerator/rca-api"` as a python dependency
- Setup the FastAPI (TBD).

### Integrate React

- Add `git+https://github.com/RCAccelerator/rca-api` to the package.json dependency.
- Instantiate the `<RcaComponent build={url} />` in an existing page.

## Contribute

Checkout the [CONTRIBUTING](./CONTRIBUTING.md) documentation.
