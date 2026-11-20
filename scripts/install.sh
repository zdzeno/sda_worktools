#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v poetry >/dev/null 2>&1; then
  echo "Poetry is not installed."
  echo "Install: https://python-poetry.org/docs/#installation"
  exit 1
fi

poetry install
echo "Done. Run: make dev  (or: poetry run document-filler)"