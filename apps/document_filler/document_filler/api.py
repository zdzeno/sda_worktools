"""HTTP API routes (stubs until template filling is implemented)."""

from fastapi import APIRouter

from document_filler.services import filler_stub

router = APIRouter(tags=["document-filler"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "document-filler"}


@router.get("/status")
def status() -> dict[str, object]:
    return filler_stub.project_status()