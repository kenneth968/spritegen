"""Center column: run readiness, prompt plan, and output preview."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..preview_panel import PreviewPanel
from ..theme import set_button_role


class WorkspacePanel(QWidget):
    """Center column: run readiness header, run summary, prompt plan, preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workspacePanel")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Run readiness header
        readiness_header = QHBoxLayout()
        self.readiness_label = QLabel("Run Readiness")
        self.readiness_label.setObjectName("sectionTitle")
        readiness_header.addWidget(self.readiness_label)
        readiness_header.addStretch()
        self.check_run_btn = QPushButton("Check Run")
        set_button_role(self.check_run_btn, "secondary")
        self.preview_prompts_btn = QPushButton("View Plan")
        set_button_role(self.preview_prompts_btn, "secondary")
        readiness_header.addWidget(self.check_run_btn)
        readiness_header.addWidget(self.preview_prompts_btn)
        layout.addLayout(readiness_header)

        readiness_actions = QHBoxLayout()
        self.open_project_gallery_btn = QPushButton("Project Gallery")
        set_button_role(self.open_project_gallery_btn, "secondary")
        self.export_project_btn = QPushButton("Export Pack")
        set_button_role(self.export_project_btn, "secondary")
        readiness_actions.addWidget(self.open_project_gallery_btn)
        readiness_actions.addWidget(self.export_project_btn)
        readiness_actions.addStretch()
        layout.addLayout(readiness_actions)

        self.run_summary_label = QLabel("Check current run before generating.")
        self.run_summary_label.setObjectName("runSummaryLabel")
        self.run_summary_label.setWordWrap(True)
        layout.addWidget(self.run_summary_label)

        # Generated output header
        output_header = QHBoxLayout()
        self.output_label = QLabel("Generated Output")
        self.output_label.setObjectName("sectionTitle")
        self.export_variant_spin = QSpinBox()
        self.export_variant_spin.setRange(0, 8)
        self.export_variant_spin.setSpecialValueText("All")
        self.export_variant_spin.setValue(0)
        output_header.addWidget(self.output_label)
        output_header.addStretch()
        self.export_variant_label = QLabel("Variant")
        output_header.addWidget(self.export_variant_label)
        output_header.addWidget(self.export_variant_spin)
        layout.addLayout(output_header)

        output_actions = QHBoxLayout()
        self.export_sprites_btn = QPushButton("Export Asset")
        set_button_role(self.export_sprites_btn, "secondary")
        self.open_gallery_btn = QPushButton("Asset Gallery")
        set_button_role(self.open_gallery_btn, "secondary")
        self.open_folder_btn = QPushButton("Open Folder")
        set_button_role(self.open_folder_btn, "secondary")
        output_actions.addWidget(self.export_sprites_btn)
        output_actions.addWidget(self.open_gallery_btn)
        output_actions.addWidget(self.open_folder_btn)
        output_actions.addStretch()
        layout.addLayout(output_actions)

        # PreviewPanel (existing)
        self.preview_panel = PreviewPanel()
        self.preview_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.preview_panel, 1)

        # Prompt plan (hidden by default, toggled via View Prompt Plan)
        self.prompt_preview_edit = QTextEdit()
        self.prompt_preview_edit.setObjectName("promptPreview")
        self.prompt_preview_edit.setReadOnly(True)
        self.prompt_preview_edit.setMinimumHeight(180)
        self.prompt_preview_edit.setMaximumHeight(280)
        self.prompt_preview_edit.setVisible(False)
        layout.addWidget(self.prompt_preview_edit)
        self.set_output_available(False)

    def show_preflight(self, text: str) -> None:
        self.prompt_preview_edit.setPlainText(text)
        self._set_prompt_preview_expanded(True)
        self.preview_panel.setVisible(False)
        self.prompt_preview_edit.setVisible(True)
        self.prompt_preview_edit.setFocus()

    def show_generated_output(self) -> None:
        self._set_prompt_preview_expanded(False)
        self.prompt_preview_edit.setVisible(False)
        self.preview_panel.setVisible(True)
        self.set_output_available(True)

    def show_generation_pending(self) -> None:
        self._set_prompt_preview_expanded(False)
        self.prompt_preview_edit.setVisible(False)
        self.preview_panel.setVisible(True)
        self.set_output_available(False)

    def show_prompt_plan(self, visible: bool) -> None:
        self._set_prompt_preview_expanded(False)
        if visible:
            self.preview_panel.setVisible(True)
        self.prompt_preview_edit.setVisible(visible)

    def set_quick_mode(self, quick_mode: bool) -> None:
        for widget in (
            self.readiness_label,
            self.check_run_btn,
            self.preview_prompts_btn,
            self.open_project_gallery_btn,
            self.export_project_btn,
            self.run_summary_label,
        ):
            widget.setVisible(not quick_mode)

    def set_output_available(self, available: bool) -> None:
        for widget in (
            self.export_variant_label,
            self.export_variant_spin,
            self.export_sprites_btn,
            self.open_gallery_btn,
            self.open_folder_btn,
        ):
            widget.setVisible(available)

    def _set_prompt_preview_expanded(self, expanded: bool) -> None:
        if expanded:
            self.prompt_preview_edit.setMaximumHeight(16777215)
            self.prompt_preview_edit.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            return
        self.prompt_preview_edit.setMaximumHeight(280)
        self.prompt_preview_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
