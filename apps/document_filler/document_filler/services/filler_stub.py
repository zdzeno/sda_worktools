"""Placeholder for docxtpl / python-docx integration."""


def project_status() -> dict[str, object]:
    return {
        "implemented": False,
        "message": "Template parsing and export are not implemented yet.",
        "planned_exports": ["docx", "pdf", "print"],
        "dependencies_ready": ["docxtpl", "python-docx"],
    }