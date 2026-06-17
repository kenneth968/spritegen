"""Left column: project essentials and asset essentials."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...layouts import PRESET_LAYOUTS
from ..preview_panel import PaletteSwatchBar
from ..theme import set_button_role


class _FormGroup(QGroupBox):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._layout = QFormLayout(self)
        self._layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._layout.setHorizontalSpacing(12)
        self._layout.setVerticalSpacing(8)
        self._layout.setContentsMargins(12, 16, 12, 12)

    def add_row(self, label: str, widget: QWidget) -> None:
        self._layout.addRow(label, widget)


class ProjectPanel(QWidget):
    """Left column with the two essential form groups."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("projectPanel")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Project card
        self.project_group = _FormGroup("Project")
        self.project_name_edit = QLineEdit("MyceliumTD")
        self.project_group.add_row("Name", self.project_name_edit)

        self.project_summary_edit = QLineEdit("Fungal tower defense game")
        self.project_group.add_row("Pitch", self.project_summary_edit)

        self.style_edit = QTextEdit()
        self.style_edit.setMinimumHeight(72)
        self.style_edit.setMaximumHeight(110)
        self.style_edit.setPlainText(
            "clean cartoon tower defense sprites, bold outlines, bright readable shapes"
        )
        self.project_group.add_row("Art Style", self.style_edit)

        self.palette_edit = QLineEdit("#8B4513,#228B22,#9932CC,#00FA9A")
        self.palette_swatches = PaletteSwatchBar()
        self.palette_edit.textChanged.connect(self.palette_swatches.set_palette)
        self.palette_swatches.set_palette(self._parse_palette(self.palette_edit.text()))
        palette_widget = QWidget()
        palette_layout = QVBoxLayout(palette_widget)
        palette_layout.setContentsMargins(0, 0, 0, 0)
        palette_layout.setSpacing(0)
        palette_layout.addWidget(self.palette_edit)
        palette_layout.addWidget(self.palette_swatches)
        self.project_group.add_row("Palette", palette_widget)

        layout.addWidget(self.project_group)

        # Asset card
        self.asset_group = _FormGroup("Asset")
        self.asset_type_edit = QLineEdit("tower")
        self.asset_group.add_row("Type", self.asset_type_edit)

        self.asset_name_edit = QLineEdit("Puffball")
        self.asset_group.add_row("Name", self.asset_name_edit)

        self.asset_description_edit = QTextEdit()
        self.asset_description_edit.setMinimumHeight(80)
        self.asset_description_edit.setMaximumHeight(120)
        self.asset_description_edit.setPlainText(
            "A mushroom tower that attacks with spore clouds."
        )
        self.asset_group.add_row("Concept", self.asset_description_edit)

        output_row = QHBoxLayout()
        self.layout_combo = QComboBox()
        for name in sorted(PRESET_LAYOUTS):
            self.layout_combo.addItem(name, name)
        self.evolutions_spin = QSpinBox()
        self.evolutions_spin.setRange(1, 8)
        self.evolutions_spin.setValue(4)
        output_row.addWidget(self.layout_combo, 1)
        output_row.addWidget(QLabel("Stages"))
        output_row.addWidget(self.evolutions_spin)
        self.asset_group.add_row("Layout", output_row)

        self.enhance_before_generate_check = QCheckBox("Improve prompt before Generate")
        self.enhance_before_generate_check.setChecked(False)
        self.asset_group.add_row("AI", self.enhance_before_generate_check)

        self.improve_prompt_btn = QPushButton("Improve Prompt Now")
        set_button_role(self.improve_prompt_btn, "secondary")
        self.asset_group.add_row("", self.improve_prompt_btn)

        layout.addWidget(self.asset_group)
        layout.addStretch()

    @staticmethod
    def _parse_palette(text: str) -> list[str]:
        return [segment.strip() for segment in text.split(",") if segment.strip()]
