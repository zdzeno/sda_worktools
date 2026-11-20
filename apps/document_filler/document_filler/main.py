"""FastAPI entrypoint for the document filler app."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from document_filler.api import router as api_router

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="SDA Document Filler",
    description="Local tool to fill Word templates and export docx/PDF (logic not implemented yet).",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def run() -> None:
    """Console script: start the dev server."""
    import uvicorn

    uvicorn.run(
        "document_filler.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(Path(__file__).resolve().parent.parent)],
    )