# sda_worktools

A set of local productivity tools for the **SDA / Copyright** departments. The first app fills Word document templates from a browser UI and will support `.docx` export, PDF, and print.

## Prerequisites

- **Python 3.11+** (3.12 recommended)
- **[Poetry](https://python-poetry.org/docs/#installation)** for dependency management and virtualenvs
- Optional: **Docker** or **Podman** for containerized runs (see below)

## Why Poetry (not plain `pip` + `venv`)?

This repo is a small **monorepo** that will grow with more apps under `apps/`. Poetry gives us:

- A single `pyproject.toml` with **pinned** runtime dependencies (`docxtpl`, `python-docx`, `fastapi`, `uvicorn`, …)
- A committed **`poetry.lock`** so everyone gets the same versions
- Simple scripts (`poetry run document-filler`) without hand-maintaining `requirements.txt` files

If you prefer `pip` only, you can still use `poetry export` later; for now, Poetry is the supported path.

## Quick start (local)

```bash
# From the repository root
make install    # poetry install
make dev        # http://127.0.0.1:8000
```

Or:

```bash
./scripts/install.sh
./scripts/dev.sh
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) — you should see the placeholder UI and a live `/api/health` check.

## Project structure

```text
sda_worktools/
├── apps/
│   └── document_filler/          # First app
│       ├── document_filler/      # Python package (FastAPI)
│       │   ├── main.py
│       │   ├── api.py
│       │   └── services/         # docx/PDF logic (stubs for now)
│       └── static/
│           └── index.html        # Browser UI placeholder
├── docker-compose.yml            # Optional container workflow
├── Dockerfile
├── Makefile
├── pyproject.toml
├── poetry.lock
└── scripts/
    ├── install.sh
    └── dev.sh
```

## Docker / Podman (optional)

If “Matt Podock” referred to a **container** workflow, use Compose:

```bash
docker compose up --build
# same URL: http://127.0.0.1:8000
```

**Podman:** Podman can run the same Compose file. Typical commands:

```bash
podman compose up --build
# or, with podman-compose: podman-compose up --build
```

Docker is not required for day-to-day development; Poetry on the host is enough.

## Next steps (document filler)

1. Define how templates expose fields (content controls, bookmarks, or a YAML schema per template).
2. Implement filling with **docxtpl** / **python-docx** under `apps/document_filler/document_filler/services/`.
3. Add upload/list endpoints and wire the HTML form to `/api/…`.
4. Choose a PDF path (e.g. LibreOffice headless vs OS-specific converters) and add print support.

Template parsing and export are **intentionally not implemented** in this bootstrap PR.

## Development commands

| Command        | Description                          |
|----------------|--------------------------------------|
| `make install` | Install dependencies                 |
| `make dev`     | Run FastAPI with auto-reload         |
| `make lint`    | Ruff on `apps/document_filler`       |
| `make docker-up` | Build and run via Docker Compose  |

## License

TBD.