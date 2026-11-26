"""Native desktop UI for the document filler (stub)."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from document_filler.services import filler_stub


class DocumentFillerWindow(QMainWindow):
    """Minimal placeholder window until template filling is implemented."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SDA Document Filler (stub)")
        self.setMinimumSize(480, 320)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        intro = QLabel(
            "Select a template category and template, then export. "
            "Filling logic is not wired yet."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form_box = QGroupBox("Template")
        form = QFormLayout(form_box)

        self.category_combo = QComboBox()
        self.category_combo.addItem("(placeholder) — no categories loaded")
        self.category_combo.setEnabled(False)
        form.addRow("Category", self.category_combo)

        self.template_combo = QComboBox()
        self.template_combo.addItem("(placeholder) — pick a category first")
        self.template_combo.setEnabled(False)
        form.addRow("Template", self.template_combo)

        layout.addWidget(form_box)

        export_box = QGroupBox("Export")
        export_layout = QHBoxLayout(export_box)

        self.export_docx = QPushButton("Export Word (.docx)")
        self.export_docx.setEnabled(False)
        self.export_docx.setToolTip("Coming soon")
        export_layout.addWidget(self.export_docx)

        self.export_pdf = QPushButton("Export PDF")
        self.export_pdf.setEnabled(False)
        self.export_pdf.setToolTip("Coming soon")
        export_layout.addWidget(self.export_pdf)

        self.print_btn = QPushButton("Print")
        self.print_btn.setEnabled(False)
        self.print_btn.setToolTip("Coming soon")
        export_layout.addWidget(self.print_btn)

        layout.addWidget(export_box)

        status = filler_stub.project_status()
        footer = QLabel(str(status.get("message", "")))
        footer.setWordWrap(True)
        footer.setStyleSheet("color: palette(mid);")
        layout.addWidget(footer)
        layout.addStretch()

        coming = QLabel("Export: coming soon")
        coming.setAlignment(Qt.AlignmentFlag.AlignCenter)
        coming.setStyleSheet("font-style: italic;")
        layout.addWidget(coming)