.PHONY: ci
ci:
	@uv run ruff check --fix
	@uv run ruff format
	@uv run ty check
	@uv run pytest --doctest-modules

.PHONY: serve
serve:
	@uv run fastapi dev --host 0.0.0.0 --port 8080 ./rcav2/api.py
