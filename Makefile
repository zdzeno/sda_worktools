.PHONY: help install dev lint smoke docker-smoke

POETRY ?= poetry
PYTHON ?= python3

help:
	@echo "Targets:"
	@echo "  install       Install dependencies with Poetry"
	@echo "  dev           Launch SDA Document Filler (desktop)"
	@echo "  lint          Run Ruff"
	@echo "  smoke         Import smoke test (no GUI window)"
	@echo "  docker-smoke  Run import smoke test in Docker"

install:
	@command -v $(POETRY) >/dev/null 2>&1 || { echo "Install Poetry first: https://python-poetry.org/docs/#installation"; exit 1; }
	$(POETRY) install

dev: install
	$(POETRY) run document-filler

lint:
	$(POETRY) run ruff check apps/document_filler

smoke: install
	$(POETRY) run python -c "from document_filler.gui import DocumentFillerWindow; from document_filler.main import main; print('smoke ok:', main.__name__)"

docker-smoke:
	docker compose run --rm document-filler