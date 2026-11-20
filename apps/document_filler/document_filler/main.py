"""Desktop entrypoint for the document filler app."""

import sys


def main() -> int:
    """Start the Qt event loop and show the main window."""
    from PySide6.QtWidgets import QApplication

    from document_filler.gui import DocumentFillerWindow

    app = QApplication(sys.argv)
    app.setApplicationName("SDA Document Filler")
    app.setApplicationDisplayName("SDA Document Filler (stub)")

    window = DocumentFillerWindow()
    window.show()
    return app.exec()


def run() -> None:
    """Console script registered in pyproject.toml."""
    raise SystemExit(main())