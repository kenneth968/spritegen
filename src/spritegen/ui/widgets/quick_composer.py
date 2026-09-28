from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..theme import set_button_role


class QuickComposer(QWidget):
    generate_requested = Signal(str, str)
    advanced_requested = Signal()
    recovery_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("quickComposer")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Generate one asset")
        title.setObjectName("quickComposerTitle")
        layout.addWidget(title)

        description_label = QLabel("Describe your asset")
        description_label.setObjectName("quickComposerLabel")
        layout.addWidget(description_label)
        self.description_edit = QTextEdit()
        self.description_edit.setObjectName("quickDescription")
        self.description_edit.setPlaceholderText("Describe the asset you want to generate")
        self.description_edit.setMinimumHeight(112)
        self.description_edit.setMaximumHeight(180)
        layout.addWidget(self.description_edit)

        output_label = QLabel("Output type")
        output_label.setObjectName("quickComposerLabel")
        layout.addWidget(output_label)
        self.output_type_combo = QComboBox()
        self.output_type_combo.setObjectName("quickOutputType")
        self.output_type_combo.addItem("Single sprite", "single_sprite")
        self.output_type_combo.addItem("Evolution chain", "evolution_chain")
        self.output_type_combo.addItem("Character sheet", "character_sheet")
        layout.addWidget(self.output_type_combo)

        self.provider_status_label = QLabel()
        self.provider_status_label.setObjectName("quickProviderStatus")
        self.provider_status_label.setWordWrap(True)
        layout.addWidget(self.provider_status_label)

        recovery = QHBoxLayout()
        self.recovery_label = QLabel()
        self.recovery_label.setObjectName("quickRecovery")
        self.recovery_label.setWordWrap(True)
        self.recovery_label.setVisible(False)
        self.recovery_btn = QPushButton()
        self.recovery_btn.setObjectName("quickRecoveryButton")
        set_button_role(self.recovery_btn, "secondary")
        self.recovery_btn.setVisible(False)
        self.recovery_btn.clicked.connect(self.recovery_requested.emit)
        recovery.addWidget(self.recovery_label, 1)
        recovery.addWidget(self.recovery_btn, 0)
        layout.addLayout(recovery)

        actions = QHBoxLayout()
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.setObjectName("quickGenerate")
        set_button_role(self.generate_btn, "primary")
        self.generate_btn.clicked.connect(self._emit_generate)
        self.advanced_btn = QPushButton("Advanced project setup")
        self.advanced_btn.setObjectName("quickAdvanced")
        set_button_role(self.advanced_btn, "secondary")
        self.advanced_btn.clicked.connect(self.advanced_requested.emit)
        actions.addWidget(self.generate_btn)
        actions.addWidget(self.advanced_btn)
        actions.addStretch()
        layout.addLayout(actions)

    def _emit_generate(self) -> None:
        self.generate_requested.emit(
            self.description_edit.toPlainText().strip(),
            str(self.output_type_combo.currentData()),
        )

    def set_provider_status(self, text: str) -> None:
        self.provider_status_label.setText(text)

    def set_recovery(self, message: str, action_label: str) -> None:
        self.recovery_label.setText(message)
        self.recovery_btn.setText(action_label)
        self.recovery_label.setVisible(True)
        self.recovery_btn.setVisible(True)

    def clear_recovery(self) -> None:
        self.recovery_label.clear()
        self.recovery_label.setVisible(False)
        self.recovery_btn.setVisible(False)

    def set_busy(self, busy: bool) -> None:
        self.description_edit.setReadOnly(busy)
        self.output_type_combo.setEnabled(not busy)
        self.generate_btn.setEnabled(not busy)
        self.advanced_btn.setEnabled(not busy)
