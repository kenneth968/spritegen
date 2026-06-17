"""Right slide-in drawer with Project/Asset/Layouts/Providers/Advanced tabs."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...project_starters import list_project_starters
from ...projects import COLOR_TREATMENT_MODES
from ...provider_models import (
    MODEL_DISCOVERY_SOURCES,
    PROVIDER_LABELS,
)
from ...workflow_presets import list_workflow_presets
from ..model_picker import ModelPicker
from ..theme import set_button_role


COLOR_MODE_LABELS = {
    "full_color": "Full Color",
    "limited_palette": "Limited Palette",
    "black_white": "Black / White",
    "grayscale_value_map": "Grayscale Value Map",
    "single_hue_value_map": "Single-Hue Value Map",
}
MODEL_DISCOVERY_SOURCE_LABELS = {
    "auto": "Auto",
    "openrouter": "OpenRouter",
    "models-dev": "models.dev",
}
IMAGE_PROVIDERS = ["mock", "pollinations", "openai", "openrouter"]
PROMPT_PROVIDERS = ["mock", "pollinations", "openai", "openrouter"]


def _form_group(title: str) -> tuple[QGroupBox, QFormLayout]:
    group = QGroupBox(title)
    form = QFormLayout(group)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(8)
    form.setContentsMargins(12, 16, 12, 12)
    return group, form


def _provider_combo(providers: list[str]) -> QComboBox:
    combo = QComboBox()
    for provider in providers:
        combo.addItem(PROVIDER_LABELS.get(provider, provider), provider)
    return combo


class SettingsDrawer(QFrame):
    """Right-side drawer with five tabs."""

    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDrawer")
        self.setFrameShape(QFrame.NoFrame)
        self.setFixedWidth(420)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("drawerHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 12, 12)
        title = QLabel("Settings")
        title.setObjectName("sectionTitle")
        close_btn = QPushButton("✕")
        close_btn.setObjectName("iconButton")
        close_btn.setToolTip("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.closed.emit)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        outer.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_project_tab(), "Project")
        self.tabs.addTab(self._build_asset_tab(), "Asset")
        self.tabs.addTab(self._build_layout_tab(), "Layouts")
        self.tabs.addTab(self._build_providers_tab(), "Providers")
        self.tabs.addTab(self._build_advanced_tab(), "Advanced")
        outer.addWidget(self.tabs, 1)

    # ---- Tab: Project ----
    def _build_project_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        group, form = _form_group("Project Details")
        self.context_edit = QTextEdit()
        self.context_edit.setMinimumHeight(120)
        self.context_edit.setMaximumHeight(180)
        self.context_edit.setPlainText("Friendly fungal towers defending a forest floor.")
        form.addRow("Universe", self.context_edit)
        self.negative_prompt_edit = QLineEdit("photorealistic, watermark, text labels")
        form.addRow("Avoid", self.negative_prompt_edit)
        self.color_mode_combo = QComboBox()
        for mode in COLOR_TREATMENT_MODES:
            self.color_mode_combo.addItem(COLOR_MODE_LABELS[mode], mode)
        form.addRow("Color Mode", self.color_mode_combo)
        self.color_prompt_edit = QTextEdit()
        self.color_prompt_edit.setMinimumHeight(72)
        self.color_prompt_edit.setMaximumHeight(120)
        self.color_prompt_edit.setPlaceholderText("Optional color rules or recolor notes")
        form.addRow("Color Notes", self.color_prompt_edit)
        self.remove_background_check = QCheckBox("Remove simple backgrounds after slicing")
        self.remove_background_check.setChecked(True)
        form.addRow("Slicing", self.remove_background_check)
        layout.addWidget(group)

        group2, form2 = _form_group("Project Location")
        root_row = QHBoxLayout()
        self.project_root_edit = QLineEdit()
        self.browse_root_btn = QPushButton("Browse")
        set_button_role(self.browse_root_btn, "secondary")
        self.browse_root_btn.clicked.connect(self._browse_project_root)
        root_row.addWidget(self.project_root_edit, 1)
        root_row.addWidget(self.browse_root_btn)
        form2.addRow("Folder", root_row)
        layout.addWidget(group2)

        group3, form3 = _form_group("Starters")
        starter_row = QHBoxLayout()
        self.project_starter_combo = QComboBox()
        for starter in list_project_starters():
            self.project_starter_combo.addItem(starter.label, starter.key)
        self.create_project_starter_btn = QPushButton("Create Starter")
        set_button_role(self.create_project_starter_btn, "secondary")
        starter_row.addWidget(self.project_starter_combo, 1)
        starter_row.addWidget(self.create_project_starter_btn)
        form3.addRow("Template", starter_row)

        project_open_row = QHBoxLayout()
        self.project_combo = QComboBox()
        self.refresh_projects_btn = QPushButton("Refresh")
        set_button_role(self.refresh_projects_btn, "secondary")
        self.load_project_btn = QPushButton("Load")
        set_button_role(self.load_project_btn, "secondary")
        project_open_row.addWidget(self.project_combo, 1)
        project_open_row.addWidget(self.refresh_projects_btn)
        project_open_row.addWidget(self.load_project_btn)
        form3.addRow("Saved", project_open_row)

        self.improve_project_btn = QPushButton("Improve Project Brief")
        set_button_role(self.improve_project_btn, "accent")
        form3.addRow("AI", self.improve_project_btn)
        layout.addWidget(group3)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _browse_project_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Project Directory",
            self.project_root_edit.text(),
        )
        if folder:
            self.project_root_edit.setText(folder)

    # ---- Tab: Asset ----
    def _build_asset_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        group, form = _form_group("Asset Type")
        preset_row = QHBoxLayout()
        self.workflow_preset_combo = QComboBox()
        for preset in list_workflow_presets():
            self.workflow_preset_combo.addItem(preset.label, preset.key)
        self.apply_workflow_preset_btn = QPushButton("Apply Workflow")
        set_button_role(self.apply_workflow_preset_btn, "secondary")
        preset_row.addWidget(self.workflow_preset_combo, 1)
        preset_row.addWidget(self.apply_workflow_preset_btn)
        form.addRow("Preset", preset_row)
        self.asset_type_context_edit = QLineEdit("Readable tower upgrades at small game size")
        form.addRow("Type Rules", self.asset_type_context_edit)
        self.improve_type_btn = QPushButton("Improve Asset-Type Rules")
        set_button_role(self.improve_type_btn, "accent")
        form.addRow("AI Type", self.improve_type_btn)
        layout.addWidget(group)

        group2, form2 = _form_group("Evolution")
        self.evolution_context_edit = QLineEdit()
        self.evolution_context_edit.setPlaceholderText(
            "Optional: how stages should evolve while keeping identity"
        )
        form2.addRow("Stage Rules", self.evolution_context_edit)
        self.evolution_labels_edit = QLineEdit()
        self.evolution_labels_edit.setPlaceholderText("Optional labels, comma-separated")
        form2.addRow("Stage Labels", self.evolution_labels_edit)
        layout.addWidget(group2)

        group3, form3 = _form_group("Asset Notes")
        self.asset_details_edit = QTextEdit()
        self.asset_details_edit.setMinimumHeight(88)
        self.asset_details_edit.setMaximumHeight(150)
        self.asset_details_edit.setPlainText(
            "Soft white cap, playful shape language, area damage identity."
        )
        form3.addRow("Extra Details", self.asset_details_edit)
        self.enhanced_prompt_edit = QTextEdit()
        self.enhanced_prompt_edit.setMinimumHeight(120)
        self.enhanced_prompt_edit.setMaximumHeight(220)
        form3.addRow("Enhanced Prompt", self.enhanced_prompt_edit)
        layout.addWidget(group3)

        group4, form4 = _form_group("Saved Assets")
        asset_open_row = QHBoxLayout()
        self.asset_combo = QComboBox()
        self.refresh_assets_btn = QPushButton("Refresh")
        set_button_role(self.refresh_assets_btn, "secondary")
        self.load_asset_btn = QPushButton("Load")
        set_button_role(self.load_asset_btn, "secondary")
        self.new_asset_btn = QPushButton("New")
        set_button_role(self.new_asset_btn, "secondary")
        asset_open_row.addWidget(self.asset_combo, 1)
        asset_open_row.addWidget(self.refresh_assets_btn)
        asset_open_row.addWidget(self.load_asset_btn)
        asset_open_row.addWidget(self.new_asset_btn)
        form4.addRow("Asset", asset_open_row)
        layout.addWidget(group4)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ---- Tab: Layouts ----
    def _build_layout_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        group, form = _form_group("Custom Grid")
        self.layout_name_edit = QLineEdit("tower_contact_sheet")
        form.addRow("Name", self.layout_name_edit)
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
        form.addRow("Canvas", canvas_row)
        grid_row = QHBoxLayout()
        self.layout_rows_spin = QSpinBox()
        self.layout_rows_spin.setRange(1, 16)
        self.layout_rows_spin.setValue(2)
        self.layout_columns_spin = QSpinBox()
        self.layout_columns_spin.setRange(1, 16)
        self.layout_columns_spin.setValue(2)
        grid_row.addWidget(QLabel("Rows"))
        grid_row.addWidget(self.layout_rows_spin)
        grid_row.addWidget(QLabel("Cols"))
        grid_row.addWidget(self.layout_columns_spin)
        form.addRow("Grid", grid_row)
        self.layout_region_prefix_edit = QLineEdit("cell")
        form.addRow("Prefix", self.layout_region_prefix_edit)
        self.add_grid_layout_btn = QPushButton("Save Grid Layout")
        set_button_role(self.add_grid_layout_btn, "secondary")
        form.addRow("", self.add_grid_layout_btn)
        layout.addWidget(group)

        group2, form2 = _form_group("Hero + Grid")
        hero_row = QHBoxLayout()
        self.hero_width_spin = QSpinBox()
        self.hero_width_spin.setRange(64, 4096)
        self.hero_width_spin.setSingleStep(64)
        self.hero_width_spin.setValue(512)
        self.hero_region_name_edit = QLineEdit("full_body")
        hero_row.addWidget(QLabel("Width"))
        hero_row.addWidget(self.hero_width_spin)
        hero_row.addWidget(QLabel("Name"))
        hero_row.addWidget(self.hero_region_name_edit)
        form2.addRow("Hero", hero_row)
        self.add_hero_grid_layout_btn = QPushButton("Save Hero + Grid Layout")
        set_button_role(self.add_hero_grid_layout_btn, "secondary")
        form2.addRow("", self.add_hero_grid_layout_btn)
        layout.addWidget(group2)

        group3, form3 = _form_group("Layout Notes")
        self.layout_prompt_edit = QTextEdit()
        self.layout_prompt_edit.setMinimumHeight(72)
        self.layout_prompt_edit.setMaximumHeight(120)
        self.layout_prompt_edit.setPlaceholderText("Optional seam and composition instructions")
        form3.addRow("Notes", self.layout_prompt_edit)
        layout.addWidget(group3)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ---- Tab: Providers ----
    def _build_providers_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        group, form = _form_group("Image Generation")
        self.image_provider_combo = _provider_combo(IMAGE_PROVIDERS)
        form.addRow("Provider", self.image_provider_combo)
        self.image_model_edit = ModelPicker("mock")
        self.image_model_suggestions = self.image_model_edit
        form.addRow("Model", self.image_model_edit)
        self.image_api_key_edit = QLineEdit()
        self.image_api_key_edit.setEchoMode(QLineEdit.Password)
        self.image_api_key_edit.setPlaceholderText("Paste provider API key")
        self.api_key_override = self.image_api_key_edit
        form.addRow("API Key", self.image_api_key_edit)
        catalog_row = QHBoxLayout()
        self.model_catalog_source_combo = QComboBox()
        for source in MODEL_DISCOVERY_SOURCES:
            self.model_catalog_source_combo.addItem(
                MODEL_DISCOVERY_SOURCE_LABELS.get(source, source),
                source,
            )
        self.model_search_edit = QLineEdit()
        self.model_search_edit.setPlaceholderText("Search model IDs")
        self.refresh_models_btn = QPushButton("Load Models")
        set_button_role(self.refresh_models_btn, "secondary")
        catalog_row.addWidget(self.model_catalog_source_combo)
        catalog_row.addWidget(self.model_search_edit, 1)
        catalog_row.addWidget(self.refresh_models_btn)
        form.addRow("Catalog", catalog_row)
        self.check_provider_setup_btn = QPushButton("Check Model Setup")
        set_button_role(self.check_provider_setup_btn, "secondary")
        form.addRow("", self.check_provider_setup_btn)
        layout.addWidget(group)

        group2, form2 = _form_group("Prompt Improvement")
        self.prompt_provider_combo = _provider_combo(PROMPT_PROVIDERS)
        form2.addRow("Provider", self.prompt_provider_combo)
        self.prompt_model_edit = ModelPicker("mock")
        self.prompt_model_suggestions = self.prompt_model_edit
        form2.addRow("Model", self.prompt_model_edit)
        self.prompt_api_key_edit = QLineEdit()
        self.prompt_api_key_edit.setEchoMode(QLineEdit.Password)
        self.prompt_api_key_edit.setPlaceholderText("Paste provider API key")
        form2.addRow("API Key", self.prompt_api_key_edit)
        layout.addWidget(group2)

        self.save_provider_settings_btn = QPushButton("Save Models + Keys")
        set_button_role(self.save_provider_settings_btn, "secondary")
        self.clear_saved_keys_btn = QPushButton("Clear Saved Keys")
        set_button_role(self.clear_saved_keys_btn, "danger")
        self.open_folder_btn = QPushButton("Open Output Folder")
        set_button_role(self.open_folder_btn, "secondary")
        self.open_gallery_btn = QPushButton("Open Asset Gallery")
        set_button_role(self.open_gallery_btn, "secondary")

        actions_grid = QGridLayout()
        actions_grid.addWidget(self.save_provider_settings_btn, 0, 0)
        actions_grid.addWidget(self.clear_saved_keys_btn, 0, 1)
        actions_grid.addWidget(self.open_folder_btn, 1, 0)
        actions_grid.addWidget(self.open_gallery_btn, 1, 1)
        layout.addLayout(actions_grid)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ---- Tab: Advanced ----
    def _build_advanced_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        group, form = _form_group("Open Output")
        self.open_project_gallery_btn = QPushButton("Project Gallery")
        set_button_role(self.open_project_gallery_btn, "secondary")
        self.export_project_btn = QPushButton("Export Project Pack")
        set_button_role(self.export_project_btn, "secondary")
        self.export_sprites_btn = QPushButton("Export Asset")
        set_button_role(self.export_sprites_btn, "secondary")
        form.addRow("", self.open_project_gallery_btn)
        form.addRow("", self.export_project_btn)
        form.addRow("", self.export_sprites_btn)
        layout.addWidget(group)

        help_label = QLabel(
            "Keys are auto-saved when typed. Use the Clear Saved Keys button on the "
            "Providers tab to remove stored credentials. Environment variables "
            "(OPENAI_API_KEY, OPENROUTER_API_KEY) are detected automatically."
        )
        help_label.setObjectName("mutedLabel")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def open_tab(self, name: str) -> None:
        for index in range(self.tabs.count()):
            if self.tabs.tabText(index).lower().startswith(name.lower()):
                self.tabs.setCurrentIndex(index)
                return
