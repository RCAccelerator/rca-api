# RCAv2

RCAv2 is a tool designed to assist CI engineers in determining the root cause of build failures.

## Prerequisites

This project uses [uv](https://docs.astral.sh/uv/), which is required for managing dependencies and running the project.

On Fedora, you can install it with:
```ShellSession
sudo dnf install -y uv
```

## Installation

To install the project dependencies, run the following command in the root directory:
```ShellSession
uv sync
```

## Usage

### Command Line Interface

To use the command-line tool, run:
```ShellSession
$ uv run rcav2 --help
```

**Example:**
```ShellSession
$ uv run rcav2 $BUILD_URL
[RCA will be printed here]
```

### Web API

The project also includes a FastAPI server. To run it for development:
```ShellSession
make serve
```

### Frontend

The frontend requires Node.js version 20.19.2.

To install the dependencies:
```ShellSession
make frontend-install
```

To run the frontend development server:
```ShellSession
make frontend-dev
```

To build the frontend:
```ShellSession
make frontend-build
```

## Development

To validate your changes, run the continuous integration script:
```ShellSession
$ make ci
```