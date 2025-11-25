green := \033[36m
white := \033[0m

cache := $(HOME)/.cache/rca
db := .db.sqlite3

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

.PHONY: cli-install
cli-install: ## Install the cli for system-wide use with pipx
	@pipx install .
	@pipx ensurepath

.PHONY: cli-uninstall
cli-uninstall: ## Uninstall the system-wide cli
	@pipx uninstall rcav2

.PHONY: cli-reinstall
cli-reinstall: ## Reinstall the system-wide cli
	@pipx install --force .
	@pipx ensurepath

.PHONY: release
release: ## Create a release version of the app
	npm run release
	uv build

.PHONY: backend-serve
backend-serve: ## Serve the backend API server
	@uv run fastapi dev --host 0.0.0.0 --port 8080 ./rcav2/standalone.py

.PHONY: frontend-install
frontend-install:
	npm install

.PHONY: frontend-serve
frontend-serve: frontend-install ## Start the frontend dev server
	npm run dev

.PHONY: frontend-build
frontend-build: ## Build a static version to be served by the api
	npm run build

.PHONY: clear-cache
clear-cache: ## Clear RCAv2 app cache and db.
	@if [ -d "$(cache)" ]; then \
		echo "Cache directory $(cache) exists. Deleting..."; \
		rm -rf "$(cache)"; else \
		echo "Cache directory $(cache) does not exist."; fi
	@if [ -f "$(db)" ]; then \
		echo "DB file $(db) exists. Deleting..."; \
		rm "$(db)"; else \
		echo "DB file $(db) does not exist."; fi
