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
