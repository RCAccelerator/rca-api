# Contributing to rca-api

This document explains how to use rca-api standalone and how to validate a change.

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

### LLM Configuration

The language model configuration can be controlled via environment variables:

- **LLM_TEMPERATURE**: Controls the randomness/creativity of the model responses. Defaults to `0.5`.
  - Lower values (0.0-0.3): More deterministic, focused responses
  - Medium values (0.5-0.7): Balanced creativity and accuracy
  - Higher values (0.8-2.0): More creative, diverse responses
  - Example: `export LLM_TEMPERATURE=0.3` for more consistent results

### Opik Integration

This project includes integration with [Opik](https://www.comet.com/docs/opik/) for tracing and observability of LLM interactions. Opik helps track and analyze the prompts and responses sent to language models during RCA analysis.

#### Local Opik Server

By default, the integration assumes a local Opik server is running. No additional configuration is required - traces will be automatically sent to the local Opik instance.
Setting up a local Opik server is super easy.  Just follow the instructions at [Local Deployment](https://www.comet.com/docs/opik/self-host/local_deployment/)

#### Opik Server on Fedora 42 with docker-podman
To run Opik server on Fedora 42 with podman-docker, follow these steps:

1.  Install podman:
    ```bash
    sudo dnf install -y podman podman-docker podman-compose
    ```

2.  Start podman and podman socket:
    ```bash
    sudo systemctl enable podman
    sudo systemctl start podman

    sudo systemctl --user enable podman.socket
    sudo systemctl --user start podman.socket


3. Set DOCKER_HOST env variable:
    ```bash
    export DOCKER_HOST="unix://$XDG_RUNTIME_DIR/podman/podman.sock"
    ```

3.  Run the Opik server using docker-compose:
    ```bash
    git clone https://github.com/comet-ml/opik.git
    cd opik/deployment/docker-compose
    curl https://raw.githubusercontent.com/RCAccelerator/rca-api/refs/heads/main/deployment/opik/docker-compose.patch | git apply -v
    docker compose --profile opik up --detach
    ```
4. Teardown the Opik server:
    ```bash
    cd opik/deployment/docker-compose
    docker compose --profile opik down --volumes
    ```

#### Pull limits when deploying the Opik server
To workaraund pull limits you can modify `~/.config/containers/registries.conf`:
```toml
[[registry]]
    location = "docker.io"
    insecure = false

[[registry.mirror]]
    location = "mirror.gcr.io"
    insecure = false
```

#### Cloud Opik Deployment
To use Opik Cloud or a custom Opik deployment, set the following environment variables:

```bash
export OPIK_API_KEY=your-opik-api-key
export OPIK_PROJECT_NAME=your-project-name  # Optional, defaults to "rca-api"
```

#### Disabling Opik Integration

To explicitly disable Opik integration, set the following environment variable:

```bash
export OPIK_DISABLED=true
```

If you don't set this variable, the application will automatically fall back to running without Opik integration if the Opik server is unavailable or if there are configuration issues.

#### Additional Opik Tags

You can add additional tags to Opik traces using the `OPIK_TAGS` environment variable. Tags are useful for filtering and organizing traces in Opik.

```bash
# Comma-separated tags (recommended)
export OPIK_TAGS="production,experiment,test-run"

# Space-separated tags
export OPIK_TAGS="production experiment test-run"

# Tags are added to the default tags (project name and workflow type)
```

Tags are parsed automatically:
- If commas are present, tags are split by comma
- If no commas are present, tags are split by whitespace
- Empty tags are automatically filtered out

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

### System-Wide CLI Installation

For convenience, you can install the `rcav2` executable globally on your system, making it available from any terminal without needing to be in the project directory or use `uv run`.

This process uses `pipx`, a tool for installing and running Python applications in isolated environments.

**1. Install pipx**

First, you need to install `pipx`. It is recommended to install it using `uv` into your system's Python environment.

```bash
sudo uv pip install --system pipx
```

**2. Use the Makefile tasks**

The `Makefile` provides convenient tasks to manage the global installation:

-   `make cli-install`: Builds and installs the `rcav2` command using `pipx`. It also runs `pipx ensurepath` to make sure the executable is in your system's `PATH`.
-   `make cli-uninstall`: Removes the `rcav2` command from your system.
-   `make cli-reinstall`: Forces a re-installation of the command, which is useful after you've made changes to the code.

After running `make cli-install`, you can invoke the tool directly:
```bash
export OPIK_DISABLED=true
export SF_DOMAIN=sf.example.com
export LLM_GEMINI_KEY=<api key from bitwarden>
rcav2 --help
rcav2 $BUILD_URL
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

## Clear RCAv2 app caches (~/.cache/rca & .db.sqlite3)
```bash
make clear-cache
```
