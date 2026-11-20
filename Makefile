.PHONY: help install dev lint docker-up docker-down

POETRY ?= poetry
PYTHON ?= python3

help:
	@echo "Targets:"
	@echo "  install     Install dependencies with Poetry"
	@echo "  dev         Run document filler on http://127.0.0.1:8000"
	@echo "  lint        Run Ruff"
	@echo "  docker-up   Start app in Docker Compose"
	@echo "  docker-down Stop Docker Compose"

install:
	@command -v $(POETRY) >/dev/null 2>&1 || { echo "Install Poetry first: https://python-poetry.org/docs/#installation"; exit 1; }
	$(POETRY) install

dev: install
	$(POETRY) run document-filler

lint:
	$(POETRY) run ruff check apps/document_filler

docker-up:
	docker compose up --build

docker-down:
	docker compose down

# Podman users: podman-compose up --build  (or: podman compose up --build)