# RCAv2

RCAv2 is a tool designed to assist CI engineers in determining the root cause of build failures.

## Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) and [npm](https://www.npmjs.com/) for managing dependencies and running the project.

### uv

On Fedora, you can install `uv` with:
```ShellSession
sudo dnf install -y uv
```

### Node.js and npm

Frontend development requires [Node.js](https://nodejs.org/) and [npm](https://www.npmjs.com/). The required Node.js version is specified in the `.nvmrc` file. We recommend using [nvm](https://github.com/nvm-sh/nvm) (Node Version Manager) to manage your Node.js versions.

To use the correct version of Node.js, run the following command from the root of the project:
```ShellSession
nvm use
```
If you don't have this version installed, you can install it with `nvm install`.

### Gemini API Key

This project requires access to gemini as it utilizes their llm.  The api key can be retrieved from [bitwarden](https://vault.bitwarden.com/).  You must be part of the Red Hat, Inc. vault to access the key. Please see https://redhat.service-now.com/help?id=kb_article_view&sysparm_article=KB0010984 for instructions.

## Installation

To install the project dependencies, run the following command in the root directory:
```ShellSession
uv sync
```

## Usage

### Command Line Interface

To use the command-line tool, run:
```ShellSession
$ export SF_DOMAIN=sf.apps.int.gpc.ocp-hub.prod.psi.redhat.com
$ export LLM_GEMINI_KEY=<api key from bitwarden>
$ uv run rcav2 --help
```

**Example:**
```ShellSession
$ uv run rcav2 $BUILD_URL
[RCA will be printed here]
```

## Development Environment

There are two primary ways to run the development environment, depending on your needs.

### 1. Serve Backend with Compiled Frontend Assets

This approach is ideal for testing the application as a single, unified service. The frontend is built into static assets and served directly by the backend.

To run the application in this mode, use the following command:

```ShellSession
make serve
```

This will:
1. Build the frontend assets.
2. Start the FastAPI backend server, which will also serve the frontend.

### 2. Run Backend and Frontend as Separate Instances

This setup is useful when you are actively developing the frontend and want to take advantage of hot-reloading features.

**Start the Backend:**
To run the backend API server, use:
```ShellSession
make backend-serve
```

**Start the Frontend:**
The frontend requires Node.js version 20.19.2. To install the dependencies and run the frontend development server, use:
```ShellSession
make frontend-serve
```

This will start the Vite development server with hot-reloading enabled.

## Tests

To validate your changes, run the continuous integration script:
```ShellSession
$ make ci
```
