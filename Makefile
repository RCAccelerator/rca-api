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

.PHONY: serve
serve: frontend-build backend-serve ## Run RCAv2 app with compiled assets

.PHONY: release
release: ## Create a release version of the app
	npm run release
	uv build

.PHONY: backend-serve
backend-serve: ## Serve the backend API server
	@uv run fastapi dev --host 0.0.0.0 --port 8080 ./rcav2/api.py
.PHONY: frontend-install

frontend-install:
	npm install

.PHONY: frontend-serve
frontend-serve: frontend-install ## Start the frontend dev server
	npm run dev

.PHONY: frontend-build ## Build a static version to be served by the api
frontend-build:
	npm run build
