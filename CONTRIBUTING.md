# Contributing to rca-mcp

This document explains how to use rca-mcp standalone and how to validate a change.

## Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) and [npm](https://www.npmjs.com/) for managing dependencies and running the project.

On Fedora, you can install them with:
```bash
sudo dnf install -y uv nodejs
```

### Kerberos ticket and SF_DOMAIN

The project requires a valid kerberos ticket to access the build logs from SF_DOMAIN.

### Gemini API Key

This project requires access to Gemini.


## Usage

To install the project dependencies, run the following command in the root directory:
```bash
uv sync && npm install
```

### Command Line Interface

To use the command-line tool, run:
```ShellSession
$ export SF_DOMAIN=sf.example.com
$ export LLM_GEMINI_KEY=<api key from bitwarden>
$ uv run rcav2 --help
```

**Example:**
```ShellSession
$ uv run rcav2 $BUILD_URL
[RCA will be printed here]
```

### API

Build the frontend asset and serve the standalone API:

```bash
make serve
```

### Hot reload frontend

When working on the RcaComponent, run the API alone in a different terminal:

```bash
make backend-serve
```

And run the Vite development server with hot-reloading enabled:

```bash
make frontend-serve
```

## Tests

To validate your changes, run the continuous integration script:
```ShellSession
$ make ci
```
