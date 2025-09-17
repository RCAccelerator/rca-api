.PHONY: ci
ci:
	@uv run ruff check --fix
	@uv run ruff format
	@uv run mypy rcav2
	@uv run pytest --doctest-modules

.PHONY: serve
serve:
	@uv run fastapi dev --host 0.0.0.0 --port 8080 ./rcav2/api.py

.PHONY: frontend-install
frontend-install:
	npm install

.PHONY: frontend-dev
frontend-dev:
	npm run dev

.PHONY: frontend-build
frontend-build:
	npm run build
