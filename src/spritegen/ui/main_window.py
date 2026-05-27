"""Main window for the spritegen desktop application."""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..layouts import PRESET_LAYOUTS, AssetLayout
from ..projects import (
    AssetSpec,
    AssetTypeSpec,
    COLOR_TREATMENT_MODES,
    ColorTreatment,
    EvolutionPlan,
    ProjectSpec,
    ProjectStore,
    PostProcessSettings,
    ProviderDefaults,
    PromptPlanner,
    apply_asset_type_enhancement,
    apply_project_enhancement,
    slugify,
)
from ..user_settings import UserSettings, UserSettingsStore
from .generation_thread import (
    AssetTypeEnhancementThread,
    EnhancementThread,
    ProjectEnhancementThread,
    ProjectGenerationThread,
)


IMAGE_PROVIDERS = ["mock", "pollinations", "openai", "openrouter"]
PROMPT_PROVIDERS = ["mock", "pollinations", "openai", "openrouter"]
KEYED_PROVIDERS = {"openai", "openrouter"}

PROVIDER_LABELS = {
    "mock": "Mock",
    "pollinations": "Pollinations",
    "openai": "OpenAI",
    "openrouter": "OpenRouter",
}

DEFAULT_IMAGE_MODELS = {
    "mock": "mock",
    "pollinations": "flux",
    "openai": "gpt-image-2",
    "openrouter": "google/gemini-3.1-flash-image-preview",
}

DEFAULT_PROMPT_MODELS = {
    "mock": "mock",
    "pollinations": "openai",
    "openai": "gpt-5.5",
    "openrouter": "openai/gpt-5.5",
}

COLOR_MODE_LABELS = {
    "full_color": "Full Color",
    "limited_palette": "Limited Palette",
    "black_white": "Black / White",
    "grayscale_value_map": "Grayscale Value Map",
    "single_hue_value_map": "Single-Hue Value Map",
}


class PreviewPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._image_paths: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)

        self._add_placeholder()

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    @property
    def image_paths(self) -> list[Path]:
        return list(self._image_paths)

    def _add_placeholder(self) -> None:
        self.placeholder = QLabel("No generated assets yet.")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
        self.container_layout.addWidget(self.placeholder)

    def clear(self) -> None:
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._image_paths.clear()
        self._add_placeholder()

    def add_image_path(self, path: Path) -> None:
        self.add_generation_output(path, [])

    def add_generation_output(
        self,
        raw_path: Path | None,
        slice_paths: list[Path],
        title: str | None = None,
    ) -> None:
        if raw_path is None and not slice_paths:
            return
        self.placeholder.hide()
        header = QLabel(title or self._group_title(raw_path, slice_paths))
        header.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 8px;")
        self.container_layout.addWidget(header)

        if raw_path is not None and raw_path.exists():
            raw_label = QLabel(f"Raw atlas: {raw_path.name}")
            raw_label.setStyleSheet("color: #555;")
            self.container_layout.addWidget(raw_label)
            self._add_scaled_image(raw_path, max_width=480, max_height=480)

        existing_slices = [path for path in slice_paths if path.exists()]
        if existing_slices:
            slices_label = QLabel(f"Sliced sprites ({len(existing_slices)})")
            slices_label.setStyleSheet("color: #555; margin-top: 6px;")
            self.container_layout.addWidget(slices_label)
            self._add_slice_grid(existing_slices)

    def _group_title(self, raw_path: Path | None, slice_paths: list[Path]) -> str:
        if raw_path is not None:
            return raw_path.stem.replace("_", " ")
        if slice_paths:
            return slice_paths[0].parent.name.replace("_", " ")
        return "Generated output"

    def _add_scaled_image(self, path: Path, max_width: int, max_height: int) -> None:
        pixmap = QPixmap.fromImage(QImage(str(path)))
        if pixmap.isNull():
            return
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setPixmap(
            pixmap.scaled(
                max_width,
                max_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.container_layout.addWidget(image_label)
        self._image_paths.append(path)

    def _add_slice_grid(self, slice_paths: list[Path]) -> None:
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        for index, path in enumerate(slice_paths):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(4)

            pixmap = QPixmap.fromImage(QImage(str(path)))
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setMinimumSize(96, 96)
            if not pixmap.isNull():
                image_label.setPixmap(
                    pixmap.scaled(
                        128,
                        128,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
                self._image_paths.append(path)
            cell_layout.addWidget(image_label)

            name_label = QLabel(path.name)
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setWordWrap(True)
            name_label.setStyleSheet("font-size: 11px; color: #555;")
            cell_layout.addWidget(name_label)

            row, column = divmod(index, 4)
            grid.addWidget(cell, row, column)

        self.container_layout.addWidget(grid_widget)


class MainWindow(QWidget):
    def __init__(self, settings_store: UserSettingsStore | None = None) -> None:
        super().__init__()
        self._thread = None
        self._current_project: ProjectSpec | None = None
        self._settings_store = settings_store or UserSettingsStore()
        self._user_settings = self._settings_store.load()
        self._project_root = str(Path("projects").absolute())
        self._last_output_dir = str(Path("projects").absolute())
        self._setup_ui()
        self._apply_user_settings()
        self._refresh_project_list()

    def _setup_ui(self) -> None:
        self.setWindowTitle("spritegen")
        self.setMinimumSize(1180, 820)

        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        left_panel = self._create_left_panel()
        left_panel.setMaximumWidth(540)
        main_layout.addWidget(left_panel)

        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, 1)

    def _create_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        title = QLabel("spritegen")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        project_group = QGroupBox("Project")
        project_layout = QFormLayout(project_group)

        self.project_name_edit = QLineEdit("MyceliumTD")
        project_layout.addRow("Name:", self.project_name_edit)

        self.project_summary_edit = QLineEdit("Fungal tower defense game")
        project_layout.addRow("Summary:", self.project_summary_edit)

        self.style_edit = QTextEdit()
        self.style_edit.setMaximumHeight(80)
        self.style_edit.setPlainText("clean cartoon tower defense sprites, bold outlines")
        project_layout.addRow("Style:", self.style_edit)

        self.context_edit = QTextEdit()
        self.context_edit.setMaximumHeight(90)
        self.context_edit.setPlainText("Friendly fungal towers defending a forest floor.")
        project_layout.addRow("Universe:", self.context_edit)

        self.palette_edit = QLineEdit("#8B4513,#228B22,#9932CC,#00FA9A")
        project_layout.addRow("Palette:", self.palette_edit)

        self.negative_prompt_edit = QLineEdit("photorealistic, watermark, text labels")
        project_layout.addRow("Avoid:", self.negative_prompt_edit)

        self.color_mode_combo = QComboBox()
        for mode in COLOR_TREATMENT_MODES:
            self.color_mode_combo.addItem(COLOR_MODE_LABELS[mode], mode)
        project_layout.addRow("Color Mode:", self.color_mode_combo)

        self.color_prompt_edit = QTextEdit()
        self.color_prompt_edit.setMaximumHeight(58)
        self.color_prompt_edit.setPlaceholderText(
            "Optional color rules, value bands, recolor map notes, etc."
        )
        project_layout.addRow("Color Notes:", self.color_prompt_edit)

        self.remove_background_check = QCheckBox("Remove simple backgrounds after slicing")
        self.remove_background_check.setChecked(True)
        project_layout.addRow("Post:", self.remove_background_check)

        root_row = QHBoxLayout()
        self.project_root_edit = QLineEdit(self._project_root)
        self.project_root_edit.editingFinished.connect(self._refresh_project_list)
        root_btn = QPushButton("Browse")
        root_btn.clicked.connect(self._browse_project_root)
        root_row.addWidget(self.project_root_edit)
        root_row.addWidget(root_btn)
        project_layout.addRow("Project Dir:", root_row)

        project_open_row = QHBoxLayout()
        self.project_combo = QComboBox()
        self.refresh_projects_btn = QPushButton("Refresh")
        self.refresh_projects_btn.clicked.connect(self._refresh_project_list)
        self.load_project_btn = QPushButton("Load")
        self.load_project_btn.clicked.connect(self._on_load_project)
        project_open_row.addWidget(self.project_combo, 1)
        project_open_row.addWidget(self.refresh_projects_btn)
        project_open_row.addWidget(self.load_project_btn)
        project_layout.addRow("Open Project:", project_open_row)

        self.improve_project_btn = QPushButton("Improve Project")
        self.improve_project_btn.clicked.connect(self._on_improve_project)
        project_layout.addRow("AI:", self.improve_project_btn)

        layout.addWidget(project_group)

        asset_group = QGroupBox("Asset")
        asset_layout = QFormLayout(asset_group)

        self.asset_type_edit = QLineEdit("tower")
        asset_layout.addRow("Type:", self.asset_type_edit)

        self.asset_type_context_edit = QLineEdit("Readable tower upgrades at small game size")
        asset_layout.addRow("Type Rules:", self.asset_type_context_edit)

        self.evolutions_spin = QSpinBox()
        self.evolutions_spin.setRange(1, 8)
        self.evolutions_spin.setValue(4)
        asset_layout.addRow("Evolutions:", self.evolutions_spin)

        self.evolution_context_edit = QLineEdit()
        self.evolution_context_edit.setPlaceholderText(
            "Optional: how stages should evolve while keeping identity"
        )
        asset_layout.addRow("Evolution Rules:", self.evolution_context_edit)

        self.evolution_labels_edit = QLineEdit()
        self.evolution_labels_edit.setPlaceholderText("Optional labels, comma-separated")
        asset_layout.addRow("Stage Labels:", self.evolution_labels_edit)

        self.improve_type_btn = QPushButton("Improve Type Rules")
        self.improve_type_btn.clicked.connect(self._on_improve_asset_type)
        asset_layout.addRow("AI Type:", self.improve_type_btn)

        self.layout_combo = QComboBox()
        self._refresh_layout_combo()
        asset_layout.addRow("Layout:", self.layout_combo)

        custom_layout_group = QGroupBox("Custom Layout")
        custom_layout_form = QFormLayout(custom_layout_group)

        self.layout_name_edit = QLineEdit("tower_contact_sheet")
        custom_layout_form.addRow("Name:", self.layout_name_edit)

        canvas_row = QHBoxLayout()
        self.layout_width_spin = QSpinBox()
        self.layout_width_spin.setRange(64, 4096)
        self.layout_width_spin.setSingleStep(64)
        self.layout_width_spin.setValue(1024)
        self.layout_height_spin = QSpinBox()
        self.layout_height_spin.setRange(64, 4096)
        self.layout_height_spin.setSingleStep(64)
        self.layout_height_spin.setValue(1024)
        canvas_row.addWidget(self.layout_width_spin)
        canvas_row.addWidget(QLabel("x"))
        canvas_row.addWidget(self.layout_height_spin)
        custom_layout_form.addRow("Canvas:", canvas_row)

        grid_row = QHBoxLayout()
        self.layout_rows_spin = QSpinBox()
        self.layout_rows_spin.setRange(1, 16)
        self.layout_rows_spin.setValue(2)
        self.layout_columns_spin = QSpinBox()
        self.layout_columns_spin.setRange(1, 16)
        self.layout_columns_spin.setValue(2)
        grid_row.addWidget(QLabel("Rows"))
        grid_row.addWidget(self.layout_rows_spin)
        grid_row.addWidget(QLabel("Columns"))
        grid_row.addWidget(self.layout_columns_spin)
        custom_layout_form.addRow("Grid:", grid_row)

        self.layout_region_prefix_edit = QLineEdit("cell")
        custom_layout_form.addRow("Region Prefix:", self.layout_region_prefix_edit)

        self.layout_prompt_edit = QTextEdit()
        self.layout_prompt_edit.setMaximumHeight(54)
        self.layout_prompt_edit.setPlaceholderText("Optional seam and composition instructions")
        custom_layout_form.addRow("Prompt Notes:", self.layout_prompt_edit)

        self.add_grid_layout_btn = QPushButton("Add Grid Layout")
        self.add_grid_layout_btn.clicked.connect(self._on_add_grid_layout)
        custom_layout_form.addRow("Save:", self.add_grid_layout_btn)

        asset_layout.addRow(custom_layout_group)

        asset_open_row = QHBoxLayout()
        self.asset_combo = QComboBox()
        self.refresh_assets_btn = QPushButton("Refresh")
        self.refresh_assets_btn.clicked.connect(self._refresh_asset_list)
        self.load_asset_btn = QPushButton("Load")
        self.load_asset_btn.clicked.connect(self._on_load_asset)
        self.new_asset_btn = QPushButton("New")
        self.new_asset_btn.clicked.connect(self._on_new_asset)
        asset_open_row.addWidget(self.asset_combo, 1)
        asset_open_row.addWidget(self.refresh_assets_btn)
        asset_open_row.addWidget(self.load_asset_btn)
        asset_open_row.addWidget(self.new_asset_btn)
        asset_layout.addRow("Saved Asset:", asset_open_row)

        self.asset_name_edit = QLineEdit("Puffball")
        asset_layout.addRow("Name:", self.asset_name_edit)

        self.asset_description_edit = QTextEdit()
        self.asset_description_edit.setMaximumHeight(90)
        self.asset_description_edit.setPlainText("A mushroom tower that attacks with spore clouds.")
        asset_layout.addRow("Concept:", self.asset_description_edit)

        self.asset_details_edit = QTextEdit()
        self.asset_details_edit.setMaximumHeight(70)
        self.asset_details_edit.setPlainText("Soft white cap, playful shape language, area damage identity.")
        asset_layout.addRow("Details:", self.asset_details_edit)

        self.enhanced_prompt_edit = QTextEdit()
        self.enhanced_prompt_edit.setMaximumHeight(110)
        asset_layout.addRow("Enhanced:", self.enhanced_prompt_edit)

        layout.addWidget(asset_group)

        config_group = QGroupBox("Providers")
        config_layout = QFormLayout(config_group)

        self.image_provider_combo = self._provider_combo(IMAGE_PROVIDERS)
        self.image_provider_combo.currentIndexChanged.connect(self._on_image_provider_changed)
        config_layout.addRow("Image Provider:", self.image_provider_combo)

        self.image_model_edit = QLineEdit(DEFAULT_IMAGE_MODELS["mock"])
        config_layout.addRow("Image Model:", self.image_model_edit)

        self.prompt_provider_combo = self._provider_combo(PROMPT_PROVIDERS)
        self.prompt_provider_combo.currentIndexChanged.connect(self._on_prompt_provider_changed)
        config_layout.addRow("Prompt Provider:", self.prompt_provider_combo)

        self.prompt_model_edit = QLineEdit(DEFAULT_PROMPT_MODELS["mock"])
        config_layout.addRow("Prompt Model:", self.prompt_model_edit)

        self.image_api_key_edit = QLineEdit()
        self.image_api_key_edit.setEchoMode(QLineEdit.Password)
        self.image_api_key_edit.setPlaceholderText("Paste image provider key")
        self.api_key_override = self.image_api_key_edit
        config_layout.addRow("Image API Key:", self.image_api_key_edit)

        self.prompt_api_key_edit = QLineEdit()
        self.prompt_api_key_edit.setEchoMode(QLineEdit.Password)
        self.prompt_api_key_edit.setPlaceholderText("Paste prompt provider key")
        config_layout.addRow("Prompt API Key:", self.prompt_api_key_edit)

        model_help = QLabel(
            '<a href="https://models.dev/?search=minim">Find provider model IDs</a>'
        )
        model_help.setOpenExternalLinks(True)
        config_layout.addRow("Model Names:", model_help)

        provider_actions = QHBoxLayout()
        self.check_provider_setup_btn = QPushButton("Check Setup")
        self.check_provider_setup_btn.clicked.connect(self._on_check_provider_setup)
        self.save_provider_settings_btn = QPushButton("Save Local Setup")
        self.save_provider_settings_btn.clicked.connect(self._on_save_provider_settings)
        self.clear_saved_keys_btn = QPushButton("Clear Saved Keys")
        self.clear_saved_keys_btn.clicked.connect(self._on_clear_saved_keys)
        provider_actions.addWidget(self.check_provider_setup_btn)
        provider_actions.addWidget(self.save_provider_settings_btn)
        provider_actions.addWidget(self.clear_saved_keys_btn)
        config_layout.addRow("Local Setup:", provider_actions)

        layout.addWidget(config_group)

        actions = QHBoxLayout()
        self.save_btn = QPushButton("Save Plan")
        self.save_btn.clicked.connect(self._on_save_plan)
        self.enhance_btn = QPushButton("Enhance Asset")
        self.enhance_btn.clicked.connect(self._on_enhance)
        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self._on_generate)
        actions.addWidget(self.save_btn)
        actions.addWidget(self.enhance_btn)
        actions.addWidget(self.generate_btn)
        layout.addLayout(actions)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        layout.addStretch()
        return panel

    def _create_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)

        header = QHBoxLayout()
        header_label = QLabel("Generated Output")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        header.addWidget(header_label)
        header.addStretch()
        header.addWidget(self.open_folder_btn)
        layout.addLayout(header)

        self.preview_panel = PreviewPanel()
        layout.addWidget(self.preview_panel)
        return panel

    def _provider_combo(self, providers: list[str]) -> QComboBox:
        combo = QComboBox()
        for provider in providers:
            combo.addItem(PROVIDER_LABELS[provider], provider)
        return combo

    def _on_image_provider_changed(self, *_args) -> None:
        provider = self.image_provider_combo.currentData()
        self.image_model_edit.setText(DEFAULT_IMAGE_MODELS.get(provider, ""))
        self._refresh_api_key_field("image")

    def _on_prompt_provider_changed(self, *_args) -> None:
        provider = self.prompt_provider_combo.currentData()
        self.prompt_model_edit.setText(DEFAULT_PROMPT_MODELS.get(provider, ""))
        self._refresh_api_key_field("prompt")

    def _apply_user_settings(self) -> None:
        self._set_combo_value(self.image_provider_combo, self._user_settings.image_provider)
        self.image_model_edit.setText(
            self._user_settings.image_model
            or DEFAULT_IMAGE_MODELS.get(self.image_provider_combo.currentData(), "")
        )
        self._set_combo_value(self.prompt_provider_combo, self._user_settings.prompt_provider)
        self.prompt_model_edit.setText(
            self._user_settings.prompt_model
            or DEFAULT_PROMPT_MODELS.get(self.prompt_provider_combo.currentData(), "")
        )
        self._refresh_api_key_fields()

    def _refresh_api_key_fields(self) -> None:
        self._refresh_api_key_field("image")
        self._refresh_api_key_field("prompt")

    def _refresh_api_key_field(self, purpose: str) -> None:
        if not hasattr(self, "image_api_key_edit"):
            return
        if purpose == "prompt":
            provider = self.prompt_provider_combo.currentData()
            edit = self.prompt_api_key_edit
        else:
            provider = self.image_provider_combo.currentData()
            edit = self.image_api_key_edit
        needs_key = provider in KEYED_PROVIDERS
        edit.setEnabled(needs_key)
        edit.setPlaceholderText("Paste provider API key" if needs_key else "No key needed")
        if needs_key:
            edit.setText(self._configured_api_key_for(provider))
        else:
            edit.clear()

    def _browse_project_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Directory",
            self.project_root_edit.text(),
        )
        if folder:
            self.project_root_edit.setText(folder)
            self._refresh_project_list()

    def _refresh_project_list(self, selected_slug: str | None = None) -> None:
        if not hasattr(self, "project_combo"):
            return
        selected = selected_slug or self.project_combo.currentData()
        self.project_combo.clear()
        store = ProjectStore(self.project_root_edit.text())
        for project in store.list_projects():
            self.project_combo.addItem(f"{project.name} ({project.slug})", project.slug)
        if selected:
            index = self.project_combo.findData(selected)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)
        self._refresh_asset_list()

    def _refresh_asset_list(self, selected_slug: str | None = None) -> None:
        if not hasattr(self, "asset_combo"):
            return
        selected = selected_slug or self.asset_combo.currentData()
        self.asset_combo.clear()
        project_slug = self._project_slug_from_fields()
        if not project_slug:
            return
        store = ProjectStore(self.project_root_edit.text())
        for asset in store.load_assets_for_slug(project_slug):
            self.asset_combo.addItem(f"{asset.name} ({asset.asset_type})", asset.slug)
        if selected:
            index = self.asset_combo.findData(selected)
            if index >= 0:
                self.asset_combo.setCurrentIndex(index)

    def _refresh_layout_combo(
        self,
        project: ProjectSpec | None = None,
        selected_name: str | None = None,
    ) -> None:
        if not hasattr(self, "layout_combo"):
            return
        selected = selected_name or self.layout_combo.currentData()
        self.layout_combo.clear()
        for name in sorted(PRESET_LAYOUTS):
            self.layout_combo.addItem(name, name)
        if project:
            for name in sorted(project.custom_layouts):
                self.layout_combo.addItem(f"{name} (project)", name)
        if selected:
            self._set_combo_value(self.layout_combo, selected)

    def _on_load_project(self) -> None:
        slug = self.project_combo.currentData()
        if not slug:
            self.status_label.setText("No saved project selected")
            return
        try:
            project = ProjectStore(self.project_root_edit.text()).load_project(slug)
            self._apply_project_spec(project)
            self._refresh_asset_list()
            self.status_label.setText(f"Loaded project: {project.name}")
        except Exception as exc:
            QMessageBox.warning(self, "Load Project Failed", str(exc))

    def _on_load_asset(self) -> None:
        slug = self.asset_combo.currentData()
        if not slug:
            self.status_label.setText("No saved asset selected")
            return
        try:
            store = ProjectStore(self.project_root_edit.text())
            project = self._current_project or store.load_project(self._project_slug_from_fields())
            asset = store.load_asset(project, slug)
            self._apply_asset_spec(project, asset)
            self._load_asset_preview(project, asset)
            self.status_label.setText(f"Loaded asset: {asset.name}")
        except Exception as exc:
            QMessageBox.warning(self, "Load Asset Failed", str(exc))

    def _on_new_asset(self) -> None:
        self.asset_name_edit.clear()
        self.asset_description_edit.clear()
        self.asset_details_edit.clear()
        self.enhanced_prompt_edit.clear()
        self.preview_panel.clear()
        self.status_label.setText("Ready for a new asset")

    def _on_save_plan(self) -> None:
        try:
            project, asset = self._save_current_specs()
            self._refresh_project_list(project.slug)
            self._refresh_asset_list(asset.slug)
            self.status_label.setText(f"Saved {project.name} / {asset.name}")
        except Exception as exc:
            QMessageBox.warning(self, "Save Failed", str(exc))

    def _on_add_grid_layout(self) -> None:
        try:
            project = self._build_project_spec()
            layout = self._build_grid_layout()
            project.add_layout(layout)
            asset_type_name = self.asset_type_edit.text().strip() or "asset"
            if asset_type_name in project.asset_types:
                project.asset_types[asset_type_name].default_layout = layout.name
            self._current_project = project
            store = ProjectStore(self.project_root_edit.text())
            store.save_project(project)
            self._refresh_project_list(project.slug)
            self._refresh_layout_combo(project, layout.name)
            self.status_label.setText(
                f"Saved layout {layout.name}: "
                f"{layout.width}x{layout.height}, {len(layout.regions)} regions"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Layout Failed", str(exc))

    def _build_grid_layout(self) -> AssetLayout:
        name = self.layout_name_edit.text().strip()
        if not name:
            raise ValueError("Layout name is required")
        layout_name = slugify(name).replace("-", "_")
        if not layout_name:
            raise ValueError("Layout name is required")
        width = self.layout_width_spin.value()
        height = self.layout_height_spin.value()
        rows = self.layout_rows_spin.value()
        columns = self.layout_columns_spin.value()
        if width % columns or height % rows:
            raise ValueError("Canvas width and height must divide evenly by the grid")
        prefix = self.layout_region_prefix_edit.text().strip() or "cell"
        region_prefix = slugify(prefix).replace("-", "_") or "cell"
        layout = AssetLayout.grid(
            name=layout_name,
            width=width,
            height=height,
            rows=rows,
            columns=columns,
            region_prefix=region_prefix,
        )
        prompt_instructions = self.layout_prompt_edit.toPlainText().strip()
        if prompt_instructions:
            layout.prompt_instructions = prompt_instructions
        return layout

    def _on_check_provider_setup(self) -> None:
        missing = []
        if not self.image_model_edit.text().strip():
            missing.append("image model")
        if not self.prompt_model_edit.text().strip():
            missing.append("prompt model")
        image_provider = self.image_provider_combo.currentData()
        prompt_provider = self.prompt_provider_combo.currentData()
        if image_provider in KEYED_PROVIDERS and not self._api_key_for(image_provider, "image"):
            missing.append(f"{PROVIDER_LABELS[image_provider]} image key")
        if prompt_provider in KEYED_PROVIDERS and not self._api_key_for(prompt_provider, "prompt"):
            missing.append(f"{PROVIDER_LABELS[prompt_provider]} prompt key")
        if missing:
            self.status_label.setText("Provider setup needs: " + ", ".join(missing))
            return
        self.status_label.setText(
            "Provider setup ready: "
            f"image {PROVIDER_LABELS[image_provider]} / prompt {PROVIDER_LABELS[prompt_provider]}"
        )

    def _on_save_provider_settings(self) -> None:
        settings = UserSettings(
            image_provider=self.image_provider_combo.currentData(),
            image_model=self.image_model_edit.text().strip(),
            prompt_provider=self.prompt_provider_combo.currentData(),
            prompt_model=self.prompt_model_edit.text().strip(),
            api_keys=dict(self._user_settings.api_keys),
        )
        image_key = self.image_api_key_edit.text()
        prompt_key = self.prompt_api_key_edit.text()
        if settings.image_provider == settings.prompt_provider:
            settings.set_api_key(settings.image_provider, prompt_key or image_key)
        else:
            settings.set_api_key(settings.image_provider, image_key)
            settings.set_api_key(settings.prompt_provider, prompt_key)
        path = self._settings_store.save(settings)
        self._user_settings = settings
        self.status_label.setText(f"Saved local provider setup to {path}")

    def _on_clear_saved_keys(self) -> None:
        self._user_settings.api_keys.clear()
        self._settings_store.save(self._user_settings)
        self._refresh_api_key_fields()
        self.status_label.setText("Cleared saved local API keys")

    def _on_improve_project(self) -> None:
        try:
            project = self._build_project_spec()
        except Exception as exc:
            QMessageBox.warning(self, "Improve Project Failed", str(exc))
            return

        provider = self.prompt_provider_combo.currentData()
        api_key = self._api_key_for(provider, "prompt")
        if not self._provider_can_run(provider, api_key):
            return

        self._set_busy(True, "Improving project art direction...")
        self._thread = ProjectEnhancementThread(
            project=project,
            provider=provider,
            model=self.prompt_model_edit.text().strip(),
            api_key=api_key,
        )
        self._thread.finished.connect(lambda data: self._on_project_improved(data, project))
        self._thread.error.connect(self._on_thread_error)
        self._thread.start()

    def _on_project_improved(self, data: dict, project: ProjectSpec) -> None:
        apply_project_enhancement(project, data)
        self._apply_project_spec(project)
        store = ProjectStore(self.project_root_edit.text())
        store.save_project(project)
        self._refresh_project_list(project.slug)
        self._set_busy(False, "Project art direction improved")
        self._thread = None

    def _on_improve_asset_type(self) -> None:
        try:
            project = self._build_project_spec()
            asset_type = project.get_asset_type(self.asset_type_edit.text().strip() or "asset")
        except Exception as exc:
            QMessageBox.warning(self, "Improve Type Failed", str(exc))
            return

        provider = self.prompt_provider_combo.currentData()
        api_key = self._api_key_for(provider, "prompt")
        if not self._provider_can_run(provider, api_key):
            return

        self._set_busy(True, "Improving asset-type rules...")
        self._thread = AssetTypeEnhancementThread(
            project=project,
            asset_type=asset_type,
            provider=provider,
            model=self.prompt_model_edit.text().strip(),
            api_key=api_key,
        )
        self._thread.finished.connect(lambda data: self._on_asset_type_improved(data, project, asset_type))
        self._thread.error.connect(self._on_thread_error)
        self._thread.start()

    def _on_asset_type_improved(
        self,
        data: dict,
        project: ProjectSpec,
        asset_type: AssetTypeSpec,
    ) -> None:
        apply_asset_type_enhancement(asset_type, data)
        project.add_asset_type(asset_type)
        self._current_project = project
        self._apply_asset_type_spec(asset_type)
        store = ProjectStore(self.project_root_edit.text())
        store.save_project(project)
        self._refresh_project_list(project.slug)
        self._set_busy(False, "Asset-type rules improved")
        self._thread = None

    def _on_enhance(self) -> None:
        try:
            project, asset = self._save_current_specs()
        except Exception as exc:
            QMessageBox.warning(self, "Enhance Failed", str(exc))
            return

        provider = self.prompt_provider_combo.currentData()
        api_key = self._api_key_for(provider, "prompt")
        if not self._provider_can_run(provider, api_key):
            return

        self._set_busy(True, "Enhancing asset prompt...")
        self._thread = EnhancementThread(
            project=project,
            asset=asset,
            project_root=self.project_root_edit.text(),
            provider=provider,
            model=self.prompt_model_edit.text().strip(),
            api_key=api_key,
        )
        self._thread.finished.connect(lambda text: self._on_enhance_finished(text, project, asset))
        self._thread.error.connect(self._on_thread_error)
        self._thread.start()

    def _on_enhance_finished(self, enhanced: str, project: ProjectSpec, asset: AssetSpec) -> None:
        asset.enhanced_prompt = enhanced
        self.enhanced_prompt_edit.setPlainText(enhanced)
        store = ProjectStore(self.project_root_edit.text())
        store.save_asset(project, asset)
        known_assets = store.load_assets(project)
        packets = PromptPlanner().build_prompt_packets(project, asset, known_assets=known_assets)
        store.save_prompt_plan(project, asset, packets)
        self._refresh_asset_list(asset.slug)
        self._set_busy(False, "Enhanced prompt saved")
        self._thread = None

    def _on_generate(self) -> None:
        try:
            project, asset = self._save_current_specs()
        except Exception as exc:
            QMessageBox.warning(self, "Generate Failed", str(exc))
            return

        provider = self.image_provider_combo.currentData()
        api_key = self._api_key_for(provider, "image")
        if not self._provider_can_run(provider, api_key):
            return

        output_root = (
            Path(self.project_root_edit.text())
            / (project.slug or project.name)
            / "generated"
            / (asset.slug or asset.name)
        )
        self.preview_panel.clear()
        self._set_busy(True, "Generating asset...")
        self._thread = ProjectGenerationThread(
            project=project,
            asset=asset,
            project_root=self.project_root_edit.text(),
            output_root=str(output_root),
            provider=provider,
            model=self.image_model_edit.text().strip(),
            api_key=api_key,
        )
        self._thread.progress.connect(self.status_label.setText)
        self._thread.finished.connect(self._on_generation_finished)
        self._thread.error.connect(self._on_thread_error)
        self._thread.start()

    def _on_generation_finished(self, result) -> None:
        self._last_output_dir = str(result.output_dir)
        for output in result.outputs:
            title = self._generation_output_title(
                stage_label=output.stage_label,
                stage_index=output.stage_index,
                layout_name=output.layout_name,
            )
            self.preview_panel.add_generation_output(
                output.raw_image,
                output.slices,
                title=title,
            )
        self._set_busy(False, f"Generated {len(result.outputs)} image(s)")
        self._refresh_asset_list(result.asset_slug)
        self._thread = None

    def _on_thread_error(self, message: str) -> None:
        self._set_busy(False, f"Error: {message}")
        QMessageBox.warning(self, "spritegen", message)
        self._thread = None

    def _save_current_specs(self) -> tuple[ProjectSpec, AssetSpec]:
        project = self._build_project_spec()
        asset = self._build_asset_spec()
        store = ProjectStore(self.project_root_edit.text())
        store.save_project(project)
        store.save_asset(project, asset)
        known_assets = store.load_assets(project)
        packets = PromptPlanner().build_prompt_packets(project, asset, known_assets=known_assets)
        store.save_prompt_plan(project, asset, packets)
        self._current_project = project
        return project, asset

    def _build_project_spec(self) -> ProjectSpec:
        name = self.project_name_edit.text().strip()
        if not name:
            raise ValueError("Project name is required")
        asset_type = self.asset_type_edit.text().strip() or "asset"
        slug = slugify(name)
        project = ProjectSpec(
            name=name,
            summary=self.project_summary_edit.text().strip(),
            visual_style=self.style_edit.toPlainText().strip(),
            shared_context=self.context_edit.toPlainText().strip(),
            palette=self._palette_values(),
            negative_prompt=self.negative_prompt_edit.text().strip(),
            provider_defaults=ProviderDefaults(
                image_provider=self.image_provider_combo.currentData(),
                image_model=self.image_model_edit.text().strip(),
                prompt_provider=self.prompt_provider_combo.currentData(),
                prompt_model=self.prompt_model_edit.text().strip(),
            ),
            color_treatment=ColorTreatment(
                mode=self.color_mode_combo.currentData(),
                custom_prompt=self.color_prompt_edit.toPlainText().strip(),
            ),
            postprocess=PostProcessSettings(
                remove_background=self.remove_background_check.isChecked(),
            ),
        )
        existing_project = self._existing_project(slug)
        if existing_project:
            for layout in existing_project.custom_layouts.values():
                project.add_layout(layout)
            for existing_asset_type in existing_project.asset_types.values():
                project.add_asset_type(existing_asset_type)
        project.add_asset_type(
            AssetTypeSpec(
                name=asset_type,
                shared_prompt=self.asset_type_context_edit.text().strip(),
                evolution=EvolutionPlan(
                    count=self.evolutions_spin.value(),
                    labels=self._evolution_labels(),
                    shared_prompt=self.evolution_context_edit.text().strip(),
                ),
                default_layout=self.layout_combo.currentData(),
            )
        )
        return project

    def _build_asset_spec(self) -> AssetSpec:
        name = self.asset_name_edit.text().strip()
        if not name:
            raise ValueError("Asset name is required")
        return AssetSpec(
            name=name,
            asset_type=self.asset_type_edit.text().strip() or "asset",
            description=self.asset_description_edit.toPlainText().strip(),
            details=self.asset_details_edit.toPlainText().strip(),
            enhanced_prompt=self.enhanced_prompt_edit.toPlainText().strip(),
            layout=self.layout_combo.currentData(),
        )

    def _palette_values(self) -> list[str]:
        return [value.strip() for value in self.palette_edit.text().split(",") if value.strip()]

    def _evolution_labels(self) -> list[str]:
        return [
            value.strip()
            for value in self.evolution_labels_edit.text().split(",")
            if value.strip()
        ]

    def _existing_project(self, project_slug: str) -> ProjectSpec | None:
        if self._current_project and self._current_project.slug == project_slug:
            return self._current_project
        store = ProjectStore(self.project_root_edit.text())
        path = store.project_path(project_slug)
        if not path.exists():
            return None
        try:
            return store.load_project(path)
        except Exception:
            return None

    def _project_slug_from_fields(self) -> str:
        name = self.project_name_edit.text().strip()
        if self._current_project and self._current_project.name == name:
            return self._current_project.slug or slugify(name)
        return slugify(name) if name else ""

    def _apply_project_spec(self, project: ProjectSpec) -> None:
        self._current_project = project
        self.project_name_edit.setText(project.name)
        self.project_summary_edit.setText(project.summary)
        self.style_edit.setPlainText(project.visual_style)
        self.context_edit.setPlainText(project.shared_context)
        self.palette_edit.setText(",".join(project.palette))
        self.negative_prompt_edit.setText(project.negative_prompt)
        self._set_combo_value(self.image_provider_combo, project.provider_defaults.image_provider)
        self.image_model_edit.setText(project.provider_defaults.image_model)
        self._set_combo_value(self.prompt_provider_combo, project.provider_defaults.prompt_provider)
        self.prompt_model_edit.setText(project.provider_defaults.prompt_model)
        self._set_combo_value(self.color_mode_combo, project.color_treatment.mode)
        self.color_prompt_edit.setPlainText(project.color_treatment.custom_prompt)
        self.remove_background_check.setChecked(project.postprocess.remove_background)
        self._refresh_layout_combo(project)
        if project.asset_types:
            self._apply_asset_type_spec(next(iter(project.asset_types.values())))

    def _apply_asset_type_spec(self, asset_type: AssetTypeSpec) -> None:
        self.asset_type_edit.setText(asset_type.name)
        self.asset_type_context_edit.setText(asset_type.shared_prompt)
        self.evolution_context_edit.setText(asset_type.evolution.shared_prompt)
        self.evolution_labels_edit.setText(", ".join(asset_type.evolution.labels))
        self.evolutions_spin.setValue(
            max(
                self.evolutions_spin.minimum(),
                min(self.evolutions_spin.maximum(), asset_type.evolution.count),
            )
        )
        self._set_combo_value(self.layout_combo, asset_type.default_layout)

    def _apply_asset_spec(self, project: ProjectSpec, asset: AssetSpec) -> None:
        if asset.asset_type in project.asset_types:
            self._apply_asset_type_spec(project.asset_types[asset.asset_type])
        self.asset_type_edit.setText(asset.asset_type)
        self.asset_name_edit.setText(asset.name)
        self.asset_description_edit.setPlainText(asset.description)
        self.asset_details_edit.setPlainText(asset.details)
        self.enhanced_prompt_edit.setPlainText(asset.enhanced_prompt)
        if asset.layout:
            self._set_combo_value(self.layout_combo, asset.layout)

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _load_asset_preview(self, project: ProjectSpec, asset: AssetSpec) -> None:
        self.preview_panel.clear()
        store = ProjectStore(self.project_root_edit.text())
        output_dir = store.generated_dir(project.slug or slugify(project.name)) / (
            asset.slug or slugify(asset.name)
        )
        self._last_output_dir = str(output_dir)
        manifest_path = output_dir / "generation_manifest.json"
        if not manifest_path.exists():
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for output in manifest.get("outputs", []):
            if not isinstance(output, dict):
                continue
            raw_image = self._manifest_image_path(output.get("raw_image"), output_dir)
            slice_paths = [
                path
                for value in output.get("slices", [])
                if (path := self._manifest_image_path(value, output_dir)) is not None
            ]
            if raw_image is not None or slice_paths:
                title = self._generation_output_title(
                    stage_label=output.get("stage_label"),
                    stage_index=output.get("stage_index"),
                    layout_name=output.get("layout_name"),
                )
                self.preview_panel.add_generation_output(
                    raw_image,
                    slice_paths,
                    title=title,
                )

    def _manifest_image_path(self, value: object, base_dir: Path) -> Path | None:
        if not isinstance(value, str) or not value:
            return None
        path = Path(value)
        if not path.is_absolute():
            path = base_dir / path
        return path if path.exists() else None

    def _generation_output_title(
        self,
        stage_label: object,
        stage_index: object,
        layout_name: object,
    ) -> str:
        layout = str(layout_name) if layout_name else "layout"
        if stage_label:
            return f"{stage_label} ({layout})"
        if stage_index is not None:
            return f"Stage {stage_index} ({layout})"
        return f"Generated asset ({layout})"

    def _api_key_for(self, provider: str, purpose: str = "image") -> str:
        primary = self.prompt_api_key_edit if purpose == "prompt" else self.image_api_key_edit
        primary_key = primary.text().strip()
        if primary_key:
            return primary_key
        secondary = self.image_api_key_edit if purpose == "prompt" else self.prompt_api_key_edit
        secondary_provider = (
            self.image_provider_combo.currentData()
            if purpose == "prompt"
            else self.prompt_provider_combo.currentData()
        )
        secondary_key = secondary.text().strip()
        if secondary_provider == provider and secondary_key:
            return secondary_key
        configured = self._configured_api_key_for(provider)
        if configured:
            return configured
        return ""

    def _configured_api_key_for(self, provider: str) -> str:
        configured = self._user_settings.api_key_for(provider)
        if configured:
            return configured
        if provider == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        if provider == "openrouter":
            return os.environ.get("OPENROUTER_API_KEY", "")
        return ""

    def _provider_can_run(self, provider: str, api_key: str) -> bool:
        if provider in {"mock", "pollinations"}:
            return True
        if api_key:
            return True
        QMessageBox.warning(
            self,
            "API Key Required",
            f"Enter an API key or set {provider.upper()}_API_KEY in the environment.",
        )
        return False

    def _set_busy(self, busy: bool, status: str) -> None:
        self.save_btn.setEnabled(not busy)
        self.improve_project_btn.setEnabled(not busy)
        self.improve_type_btn.setEnabled(not busy)
        self.enhance_btn.setEnabled(not busy)
        self.generate_btn.setEnabled(not busy)
        self.add_grid_layout_btn.setEnabled(not busy)
        self.check_provider_setup_btn.setEnabled(not busy)
        self.save_provider_settings_btn.setEnabled(not busy)
        self.clear_saved_keys_btn.setEnabled(not busy)
        self.progress_bar.setRange(0, 0 if busy else 1)
        self.progress_bar.setValue(0 if busy else 1)
        self.status_label.setText(status)

    def _open_output_folder(self) -> None:
        folder = self._last_output_dir
        if os.name == "nt":
            os.startfile(folder)
        elif os.name == "posix":
            import subprocess

            subprocess.run(["open", folder] if sys.platform == "darwin" else ["xdg-open", folder])


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
