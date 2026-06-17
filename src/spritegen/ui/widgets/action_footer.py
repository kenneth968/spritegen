"""Bottom action bar: save, improve prompt, generate + progress + status."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..theme import set_button_role


class ActionFooter(QFrame):
    """Bottom action bar with primary Generate button and status feedback."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("actionFooter")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        set_button_role(self.save_btn, "secondary")
        self.enhance_btn = QPushButton("Improve Prompt")
        set_button_role(self.enhance_btn, "accent")
        self.generate_btn = QPushButton("Generate")
        set_button_role(self.generate_btn, "primary")

        self.generation_variants_spin = QSpinBox()
        self.generation_variants_spin.setRange(1, 8)
        self.generation_variants_spin.setValue(1)
        self.generation_variants_label = QLabel("Variants")

        actions.addWidget(self.save_btn)
        actions.addWidget(self.enhance_btn)
        actions.addStretch()
        actions.addWidget(self.generation_variants_label)
        actions.addWidget(self.generation_variants_spin)
        actions.addWidget(self.generate_btn)
        layout.addLayout(actions)

        # Progress + status row
        status_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("generationProgress")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        self.status_flash = QLabel("")
        self.status_flash.setObjectName("statusFlash")
        self.status_flash.setVisible(False)
        status_row.addWidget(self.progress_bar, 2)
        status_row.addWidget(self.status_flash, 0, Qt.AlignVCenter)
        status_row.addWidget(self.status_label, 3)
        layout.addLayout(status_row)

    def set_progress_range(self, maximum: int) -> None:
        self.progress_bar.setRange(0, maximum)

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def set_busy(self, busy: bool) -> None:
        self.generate_btn.setEnabled(not busy)
        self.enhance_btn.setEnabled(not busy)
        self.save_btn.setEnabled(not busy)

    def flash_status(self, text: str, state: str = "success") -> None:
        from PySide6.QtCore import QTimer

        self.status_flash.setProperty("flashState", state)
        self.status_flash.setText(text)
        self.status_flash.setVisible(True)
        self.status_flash.style().unpolish(self.status_flash)
        self.status_flash.style().polish(self.status_flash)
        QTimer.singleShot(
            2000,
            lambda: (
                self.status_flash.setVisible(False),
                self.status_flash.setText(""),
            ),
        )
