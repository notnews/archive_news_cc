.PHONY: check ci-docker

check:
	uv sync --frozen --group dev
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest -q
	uv run pre-commit run --all-files

ci-docker:
	@for version in 3.12 3.14; do \
	  COPYFILE_DISABLE=1 tar --exclude=._* --exclude=__pycache__ --exclude=.DS_Store --exclude=.git --exclude=.venv --exclude=data --exclude=dist --exclude=.ruff_cache --exclude=.pytest_cache -cf - . | \
	  docker run --rm -i -e PYTHONDONTWRITEBYTECODE=1 python:$$version-slim sh -ec 'mkdir /work; tar -xf - -C /work; cd /work; pip install -q uv; uv sync --frozen --group dev; uv run ruff check .; uv run ruff format --check .; uv run pytest -q' || exit $$?; \
	done
