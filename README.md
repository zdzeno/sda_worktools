# sda_worktools

A set of **local, workstation-only** productivity tools for the **SDA / Copyright** departments. The first app is **SDA Document Filler**: a native desktop program that will fill Word document templates and export `.docx`, PDF, and print.

This repository may be developed with Cursor **Projects** (cloud agents, shared docs), but the **document filler itself runs entirely on your machine** — there is no web server or browser UI as the primary experience.

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **[Poetry](https://python-poetry.org/docs/#installation)** for dependencies and virtualenvs
- A desktop OS with a display (**Linux, macOS, or Windows**) for the Qt GUI

## Why Poetry?

This repo is a small **monorepo** under `apps/`. Poetry provides:

- One `pyproject.toml` with **pinned** runtime dependencies (`PySide6`, `docxtpl`, `python-docx`, …)
- A committed **`poetry.lock`** for reproducible installs
- `poetry run document-filler` as the supported launch command

## Quick start (local desktop)

```bash
# From the repository root
make install    # poetry install
make dev        # opens the desktop window
```

Or:

```bash
./scripts/install.sh
./scripts/dev.sh
```

Equivalent:

```bash
poetry run document-filler
# or
poetry run python -m document_filler.main
```

You should see a window titled **SDA Document Filler (stub)** with placeholder category/template pickers and disabled export actions.

## Project structure

```text
sda_worktools/
├── apps/
│   └── document_filler/
│       └── document_filler/      # Python package
│           ├── main.py           # Desktop entry (Qt)
│           ├── gui.py            # Main window (PySide6)
│           └── services/         # docx/PDF logic (stubs for now)
├── Dockerfile                    # Optional: import smoke test in CI/containers
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── poetry.lock
└── scripts/
    ├── install.sh
    └── dev.sh
```

## Cloud Project vs local runtime

| Context | What runs where |
|--------|------------------|
| **Cursor Project** | Planning, docs, agent-assisted development in the cloud |
| **Document filler** | **Your workstation only** — native Qt window, no required FastAPI/uvicorn |

## Docker / Podman (optional, not for day-to-day GUI)

Containers do not provide a practical desktop GUI for this app. The bundled `Dockerfile` only verifies that the Python package **imports** (useful in headless CI). For real use, run via Poetry on the host.

```bash
docker compose run --rm document-filler
```

**Podman:** `podman compose run --rm document-filler` works the same way.

## Next steps (document filler)

1. Define how templates expose fields (content controls, bookmarks, or a YAML schema per template).
2. Implement filling with **docxtpl** / **python-docx** under `services/`.
3. Load categories/templates from disk and enable the pickers in `gui.py`.
4. Wire export buttons and choose a PDF path (e.g. LibreOffice headless).

Template parsing and export are **intentionally not implemented** in this bootstrap PR.

## Development commands

| Command        | Description                                |
|----------------|--------------------------------------------|
| `make install` | Install dependencies with Poetry           |
| `make dev`     | Launch the desktop app                     |
| `make lint`    | Ruff on `apps/document_filler`             |
| `make smoke`   | Import check without opening a window      |

## License

TBD.