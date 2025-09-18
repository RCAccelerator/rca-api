green := \033[36m
white := \033[0m

executables = uv npm
T := $(foreach exec,$(executables),\
        $(if $(shell which $(exec)),WARNING,$(error "No $(exec) in PATH")))

.PHONY: help
help: ## Prints help for targets with comments.
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | awk 'BEGIN {FS = ":.*?## "}; {printf "$(green)%-30s$(white) %s\n", $$1, $$2}'

.PHONY: ci
ci: ## Run tests, linting and type checking
	@uv run ruff check --fix
	@uv run ruff format
	@uv run mypy rcav2
	@uv run pytest --doctest-modules

.PHONY: backend
backend: ## Run the backend server
	@uv run fastapi dev --host 0.0.0.0 --port 8080 ./rcav2/api.py

.PHONY: frontend
frontend: frontend-install frontend-build frontend-dev ## Run the frontend dev server

.PHONY: release
release: ## Create a release version of the app
	npm run release
	uv build

.PHONY: frontend-install
frontend-install:
	npm install

.PHONY: frontend-dev
frontend-dev:
	npm run dev

.PHONY: frontend-build
frontend-build:
	npm run build
