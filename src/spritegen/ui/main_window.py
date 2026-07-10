"""Main window for the spritegen desktop application.

The window composes a top provider bar, a left project/asset form panel, a
center workspace with the run check and asset preview, a bottom action
footer, a right-side settings drawer, and an optional welcome overlay.
Business logic lives in :mod:`spritegen.ui.controller`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..projects import ProjectSpec
from ..provider_models import IMAGE_ROLE, PROMPT_ROLE, ModelSuggestion
from ..user_settings import UserSettingsStore
from .controller import MainWindowController
from .theme import desktop_stylesheet
from .widgets.action_footer import ActionFooter
from .widgets.project_panel import ProjectPanel
from .widgets.provider_bar import ProviderBar
from .widgets.quick_composer import QuickComposer
from .widgets.welcome_overlay import (
    openai_defaults,
    openrouter_defaults,
    pollinations_defaults,
)
from .widgets.settings_drawer import SettingsDrawer
from .widgets.welcome_overlay import WelcomeOverlay
from .widgets.workspace_panel import WorkspacePanel
from .app_paths import default_project_root


class MainWindow(QWidget):
    def __init__(self, settings_store: UserSettingsStore | None = None) -> None:
        super().__init__()
        self._thread = None
        self._current_project: ProjectSpec | None = None
        self._settings_store = settings_store or UserSettingsStore()
        self._user_settings = self._settings_store.load()
        self._online_model_suggestions: dict[tuple[str, str], list[ModelSuggestion]] = {}
        self._project_root = self._user_settings.project_root or str(default_project_root())
        self._last_output_dir = self._project_root
        self._last_gallery_path = ""
        self._last_project_gallery_path = ""
        self._app_mode = "quick"

        self.controller = MainWindowController(self)
        self._auto_save_timer = QTimer(self)
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(800)
        self._auto_save_timer.timeout.connect(self.controller.on_save_provider_settings)

        self._build_ui()
        self._wire_signals()
        self._apply_user_settings()
        self._set_app_mode("quick")
        self.controller.refresh_project_list()
        self._show_welcome_if_needed()
        self._refresh_provider_chip()
        self._update_project_pills()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.setObjectName("appRoot")
        self.setWindowTitle("spritegen")
        self.setMinimumSize(1180, 720)
        self.resize(1500, 940)
        self.setStyleSheet(desktop_stylesheet())

        outer = QStackedLayout(self)
        outer.setStackingMode(QStackedLayout.StackingMode.StackAll)

        # Background page = main app
        background = QWidget()
        background.setObjectName("appBackground")
        self.app_background = background
        background_layout = QVBoxLayout(background)
        background_layout.setContentsMargins(0, 0, 0, 0)
        background_layout.setSpacing(0)

        self.provider_bar = ProviderBar()
        background_layout.addWidget(self.provider_bar)

        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(12)

        self.setup_stack = QStackedWidget()
        self.project_panel = ProjectPanel()
        self.project_panel.setMinimumWidth(420)
        self.project_panel.setMaximumWidth(560)
        self.quick_composer = QuickComposer()
        self.setup_stack.addWidget(self.project_panel)
        self.setup_stack.addWidget(self.quick_composer)
        body.addWidget(self.setup_stack, 0)

        self.workspace_panel = WorkspacePanel()
        body.addWidget(self.workspace_panel, 1)

        self.settings_drawer = SettingsDrawer()
        self.settings_drawer.setVisible(False)
        self.settings_drawer.setMinimumWidth(0)
        self.settings_drawer.setMaximumWidth(0)
        body.addWidget(self.settings_drawer, 0)

        background_layout.addLayout(body, 1)

        self.action_footer = ActionFooter()
        background_layout.addWidget(self.action_footer)

        outer.addWidget(background)

        # Foreground page = welcome overlay
        self.welcome_overlay = WelcomeOverlay(background)
        self.welcome_overlay.setVisible(False)
        outer.addWidget(self.welcome_overlay)

        # Backwards-compat object names on self
        # Add workflow_strip to top bar (legacy attribute)
        self.provider_bar.tagline_label.setObjectName("topBarTagline")
        # Backwards-compat: legacy workflow_strip is hidden but available as object
        self.workflow_strip = QLabel("Idea > Style > Asset > Check > Generate > Choose")
        self.workflow_strip.setObjectName("workflowStrip")
        self._alias_widget_attributes()

    def _alias_widget_attributes(self) -> None:
        """Expose sub-widget attributes on self for tests and signal wiring."""
        pp = self.project_panel
        dp = self.settings_drawer
        ws = self.workspace_panel
        af = self.action_footer

        # workflow_strip already created in _build_ui
        # Tag the provider bar tagline for the design system tokens
        self.provider_bar.tagline_label.setObjectName("topBarTagline")

        # Project panel
        self.project_name_edit = pp.project_name_edit
        self.project_summary_edit = pp.project_summary_edit
        self.style_edit = pp.style_edit
        self.palette_edit = pp.palette_edit
        self.palette_swatches = pp.palette_swatches
        self.asset_type_edit = pp.asset_type_edit
        self.asset_name_edit = pp.asset_name_edit
        self.asset_description_edit = pp.asset_description_edit
        self.layout_combo = pp.layout_combo
        self.evolutions_spin = pp.evolutions_spin
        self.enhance_before_generate_check = pp.enhance_before_generate_check
        self.improve_prompt_btn = pp.improve_prompt_btn

        # Drawer
        self.context_edit = dp.context_edit
        self.negative_prompt_edit = dp.negative_prompt_edit
        self.color_mode_combo = dp.color_mode_combo
        self.color_prompt_edit = dp.color_prompt_edit
        self.remove_background_check = dp.remove_background_check
        self.project_root_edit = dp.project_root_edit
        self.project_starter_combo = dp.project_starter_combo
        self.create_project_starter_btn = dp.create_project_starter_btn
        self.try_sample_run_btn = dp.try_sample_run_btn
        self.project_combo = dp.project_combo
        self.refresh_projects_btn = dp.refresh_projects_btn
        self.load_project_btn = dp.load_project_btn
        self.improve_project_btn = dp.improve_project_btn
        self.workflow_preset_combo = dp.workflow_preset_combo
        self.apply_workflow_preset_btn = dp.apply_workflow_preset_btn
        self.asset_type_context_edit = dp.asset_type_context_edit
        self.evolution_context_edit = dp.evolution_context_edit
        self.evolution_labels_edit = dp.evolution_labels_edit
        self.improve_type_btn = dp.improve_type_btn
        self.asset_details_edit = dp.asset_details_edit
        self.enhanced_prompt_edit = dp.enhanced_prompt_edit
        self.asset_combo = dp.asset_combo
        self.refresh_assets_btn = dp.refresh_assets_btn
        self.load_asset_btn = dp.load_asset_btn
        self.new_asset_btn = dp.new_asset_btn
        self.layout_name_edit = dp.layout_name_edit
        self.layout_width_spin = dp.layout_width_spin
        self.layout_height_spin = dp.layout_height_spin
        self.layout_rows_spin = dp.layout_rows_spin
        self.layout_columns_spin = dp.layout_columns_spin
        self.hero_width_spin = dp.hero_width_spin
        self.hero_region_name_edit = dp.hero_region_name_edit
        self.layout_region_prefix_edit = dp.layout_region_prefix_edit
        self.layout_prompt_edit = dp.layout_prompt_edit
        self.add_grid_layout_btn = dp.add_grid_layout_btn
        self.add_hero_grid_layout_btn = dp.add_hero_grid_layout_btn
        self.image_provider_combo = dp.image_provider_combo
        self.image_model_edit = dp.image_model_edit
        self.image_model_suggestions = dp.image_model_suggestions
        self.image_api_key_edit = dp.image_api_key_edit
        self.api_key_override = dp.api_key_override
        self.model_catalog_source_combo = dp.model_catalog_source_combo
        self.model_search_edit = dp.model_search_edit
        self.refresh_models_btn = dp.refresh_models_btn
        self.check_provider_setup_btn = dp.check_provider_setup_btn
        self.prompt_provider_combo = dp.prompt_provider_combo
        self.prompt_model_edit = dp.prompt_model_edit
        self.prompt_model_suggestions = dp.prompt_model_suggestions
        self.prompt_api_key_edit = dp.prompt_api_key_edit
        self.prompt_provider_form = dp.prompt_provider_form
        self.prompt_provider_group = dp.prompt_provider_group
        self.shared_provider_setup_check = dp.shared_provider_setup_check
        self.save_provider_settings_btn = dp.save_provider_settings_btn
        self.clear_saved_keys_btn = dp.clear_saved_keys_btn
        self.open_project_gallery_btn = dp.open_project_gallery_btn
        self.export_project_btn = dp.export_project_btn
        self.export_sprites_btn = dp.export_sprites_btn
        self.open_folder_btn = dp.open_folder_btn
        self.open_gallery_btn = dp.open_gallery_btn

        # Workspace
        self.check_run_btn = ws.check_run_btn
        self.preview_prompts_btn = ws.preview_prompts_btn
        self.preview_panel = ws.preview_panel
        self.prompt_preview_edit = ws.prompt_preview_edit
        self.export_variant_spin = ws.export_variant_spin

        # Action footer
        self.save_btn = af.save_btn
        self.enhance_btn = af.enhance_btn
        self.generate_btn = af.generate_btn
        self.generation_variants_spin = af.generation_variants_spin
        self.progress_bar = af.progress_bar
        self.status_label = af.status_label
        self.run_summary_label = ws.run_summary_label

        # Aliases for legacy tests that look for the dialog-button object names
        self.project_style_btn = self.open_project_gallery_btn
        self.asset_details_btn = self.export_sprites_btn
        self.layout_builder_btn = self.open_folder_btn
        self.models_keys_btn = self.settings_drawer  # legacy alias; tests may probe this

        # Tool dialogs (legacy dict; tests inspect keys)
        self._tool_dialogs = {
            "project": self.settings_drawer,
            "asset": self.settings_drawer,
            "layout": self.settings_drawer,
            "models": self.settings_drawer,
            "prompt": self.settings_drawer,
        }

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------
    def _wire_signals(self) -> None:
        # Provider changes
        self.image_provider_combo.currentIndexChanged.connect(
            self.controller.on_image_provider_changed
        )
        self.prompt_provider_combo.currentIndexChanged.connect(
            self.controller.on_prompt_provider_changed
        )
        self.shared_provider_setup_check.stateChanged.connect(
            self.controller.on_shared_provider_setup_changed
        )
        self.image_model_suggestions.activated.connect(
            lambda _index: self.controller.apply_model_suggestion(IMAGE_ROLE)
        )
        self.prompt_model_suggestions.activated.connect(
            lambda _index: self.controller.apply_model_suggestion(PROMPT_ROLE)
        )

        # Auto-save provider settings
        self.image_provider_combo.currentIndexChanged.connect(self._schedule_auto_save)
        self.prompt_provider_combo.currentIndexChanged.connect(self._schedule_auto_save)
        self.shared_provider_setup_check.stateChanged.connect(self._schedule_auto_save)
        self.image_api_key_edit.textChanged.connect(self._schedule_auto_save)
        self.prompt_api_key_edit.textChanged.connect(self._schedule_auto_save)
        self.image_model_edit.editTextChanged.connect(self._schedule_auto_save)
        self.prompt_model_edit.editTextChanged.connect(self._schedule_auto_save)

        # Palette / layout refresh
        self.palette_edit.textChanged.connect(
            lambda text: self.palette_swatches.set_palette(
                [segment.strip() for segment in text.split(",") if segment.strip()]
            )
        )

        # Project / asset
        self.refresh_projects_btn.clicked.connect(self.controller.refresh_project_list)
        self.load_project_btn.clicked.connect(self.controller.on_load_project)
        self.refresh_assets_btn.clicked.connect(self.controller.refresh_asset_list)
        self.load_asset_btn.clicked.connect(self.controller.on_load_asset)
        self.new_asset_btn.clicked.connect(self.controller.on_new_asset)
        self.create_project_starter_btn.clicked.connect(
            self.controller.on_apply_project_starter
        )
        self.try_sample_run_btn.clicked.connect(self.controller.on_try_sample_run)
        self.apply_workflow_preset_btn.clicked.connect(
            self.controller.on_apply_workflow_preset
        )
        self.project_root_edit.editingFinished.connect(self.controller.refresh_project_list)
        self.improve_project_btn.clicked.connect(self.controller.on_improve_project)
        self.improve_type_btn.clicked.connect(self.controller.on_improve_asset_type)
        self.improve_prompt_btn.clicked.connect(self.controller.on_enhance)

        # Layouts
        self.add_grid_layout_btn.clicked.connect(self.controller.on_add_grid_layout)
        self.add_hero_grid_layout_btn.clicked.connect(
            self.controller.on_add_hero_grid_layout
        )

        # Providers
        self.save_provider_settings_btn.clicked.connect(
            self.controller.on_save_provider_settings
        )
        self.clear_saved_keys_btn.clicked.connect(self.controller.on_clear_saved_keys)
        self.check_provider_setup_btn.clicked.connect(
            self.controller.on_check_provider_setup
        )
        self.refresh_models_btn.clicked.connect(self.controller.on_refresh_models)

        # Workspace
        self.check_run_btn.clicked.connect(self.controller.on_check_run)
        self.preview_prompts_btn.clicked.connect(self.controller.on_preview_prompts)
        self.export_sprites_btn.clicked.connect(self.controller.on_export_asset)
        self.export_project_btn.clicked.connect(self.controller.on_export_project)
        self.open_project_gallery_btn.clicked.connect(
            self.controller.on_open_project_gallery
        )
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        self.open_gallery_btn.clicked.connect(self._open_gallery)

        # Action footer
        self.save_btn.clicked.connect(self.controller.on_save_plan)
        self.enhance_btn.clicked.connect(self.controller.on_enhance)
        self.generate_btn.clicked.connect(self.controller.on_generate)

        # Top bar
        self.provider_bar.project_pill_clicked.connect(self._open_project_menu)
        self.provider_bar.asset_pill_clicked.connect(self._open_asset_menu)
        self.provider_bar.settings_clicked.connect(self._open_settings_drawer)
        self.provider_bar.mode_requested.connect(self._set_app_mode)
        self.quick_composer.advanced_requested.connect(
            lambda: self._set_app_mode("advanced")
        )
        self.quick_composer.generate_requested.connect(self.controller.on_quick_generate)
        self.quick_composer.recovery_requested.connect(self.controller.on_quick_recovery)

        # Settings drawer
        self.settings_drawer.closed.connect(self._close_settings_drawer)

        # Welcome overlay
        self.welcome_overlay.pollinations_clicked.connect(self._welcome_pollinations)
        self.welcome_overlay.openrouter_clicked.connect(self._welcome_openrouter)
        self.welcome_overlay.openai_clicked.connect(self._welcome_openai)
        self.welcome_overlay.open_project_clicked.connect(self._welcome_open_project)
        self.welcome_overlay.skip_clicked.connect(self._welcome_skip)

    def _schedule_auto_save(self) -> None:
        self._auto_save_timer.start()

    # ------------------------------------------------------------------
    # Settings / welcome
    # ------------------------------------------------------------------
    def _apply_user_settings(self) -> None:
        self.project_root_edit.setText(self._project_root)
        self.controller.apply_user_settings()
        self._refresh_provider_chip()

    def _refresh_provider_chip(self) -> None:
        provider = self.image_provider_combo.currentData()
        api_key = self.image_api_key_edit.text().strip() or self._user_settings.api_key_for(
            provider
        )
        self.provider_bar.set_provider(provider, api_key)
        self.quick_composer.set_provider_status(self.provider_bar.provider_chip.text())

    def update_provider_chip(self) -> None:
        self._refresh_provider_chip()

    def _update_project_pills(self) -> None:
        project = self._current_project
        asset_name = self.asset_name_edit.text().strip() if hasattr(self, "asset_name_edit") else ""
        if self._app_mode == "quick":
            self.provider_bar.set_project_label("Quick Start")
            self.provider_bar.set_asset_label(asset_name if project else "")
            return
        if project:
            self.provider_bar.set_project_label(project.name)
        else:
            self.provider_bar.set_project_label(self.project_name_edit.text().strip())
        self.provider_bar.set_asset_label(asset_name)

    def update_project_pills(self) -> None:
        self._update_project_pills()

    def _show_welcome_if_needed(self) -> None:
        self._set_welcome_visible(False)

    def _set_app_mode(self, mode: str) -> None:
        if mode not in {"quick", "advanced"}:
            raise ValueError(f"Unknown app mode: {mode}")
        quick_mode = mode == "quick"
        self._app_mode = mode
        self.setup_stack.setCurrentWidget(
            self.quick_composer if quick_mode else self.project_panel
        )
        self.action_footer.setVisible(not quick_mode)
        self.workspace_panel.set_quick_mode(quick_mode)
        self.provider_bar.set_mode(mode)

    def _set_welcome_visible(self, visible: bool) -> None:
        self.welcome_overlay.setVisible(visible)
        self.app_background.setEnabled(not visible)
        if visible:
            self.welcome_overlay.raise_()
            self.welcome_overlay.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        else:
            self.setFocus(Qt.FocusReason.OtherFocusReason)

    def _welcome_pollinations(self) -> None:
        img_prov, img_model, prompt_prov, prompt_model = pollinations_defaults()
        self._apply_welcome_choice(
            image_provider=img_prov,
            image_model=img_model,
            prompt_provider=prompt_prov,
            prompt_model=prompt_model,
            api_key="",
            starter_key="mycelium_td",
        )

    def _welcome_openrouter(self, api_key: str) -> None:
        img_prov, img_model, prompt_prov, prompt_model = openrouter_defaults()
        self._apply_welcome_choice(
            image_provider=img_prov,
            image_model=img_model,
            prompt_provider=prompt_prov,
            prompt_model=prompt_model,
            api_key=api_key,
            starter_key="",
        )

    def _welcome_openai(self, api_key: str) -> None:
        img_prov, img_model, prompt_prov, prompt_model = openai_defaults()
        self._apply_welcome_choice(
            image_provider=img_prov,
            image_model=img_model,
            prompt_provider=prompt_prov,
            prompt_model=prompt_model,
            api_key=api_key,
            starter_key="",
        )

    def _apply_welcome_choice(
        self,
        image_provider: str,
        image_model: str,
        prompt_provider: str,
        prompt_model: str,
        api_key: str,
        starter_key: str,
    ) -> None:
        self._user_settings.image_provider = image_provider
        self._user_settings.image_model = image_model
        self._user_settings.prompt_provider = prompt_provider
        self._user_settings.prompt_model = prompt_model
        if api_key:
            self._user_settings.set_api_key(image_provider, api_key)
        if prompt_provider != image_provider and api_key:
            self._user_settings.set_api_key(prompt_provider, api_key)
        self._user_settings.last_starter_key = starter_key
        self._user_settings.mark_welcome_seen()
        self._settings_store.save(self._user_settings)
        self.controller.apply_user_settings()
        self._refresh_provider_chip()
        if starter_key:

            self.project_starter_combo.setCurrentIndex(
                self.project_starter_combo.findData(starter_key)
            )
            self.controller.on_apply_project_starter()
        self._set_welcome_visible(False)
        self.flash_status("Ready to generate", "success")
        self.status_label.setText(
            f"Welcome! {image_provider.title()} is set up. Click Generate when ready."
        )

    def _welcome_open_project(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select projects directory", self.project_root_edit.text()
        )
        if folder:
            self.project_root_edit.setText(folder)
        self._user_settings.mark_welcome_seen()
        self._settings_store.save(self._user_settings)
        self._set_welcome_visible(False)
        self.controller.refresh_project_list()

    def _welcome_skip(self) -> None:
        self._user_settings.mark_welcome_seen()
        self._settings_store.save(self._user_settings)
        self._set_welcome_visible(False)
        self.status_label.setText("Ready. Pick a project or start from a starter.")

    # ------------------------------------------------------------------
    # Drawer / pill menus
    # ------------------------------------------------------------------
    def _open_settings_drawer(self) -> None:
        was_hidden = self.settings_drawer.isHidden()
        self.settings_drawer.setVisible(was_hidden)
        if was_hidden:
            self.settings_drawer.open_tab("Providers")
        self._adjust_layout_for_drawer()

    def _close_settings_drawer(self) -> None:
        self.settings_drawer.setVisible(False)
        self._adjust_layout_for_drawer()

    def _adjust_layout_for_drawer(self) -> None:
        if self.settings_drawer.isVisible():
            self.settings_drawer.setMinimumWidth(420)
            self.settings_drawer.setMaximumWidth(560)
        else:
            self.settings_drawer.setMinimumWidth(0)
            self.settings_drawer.setMaximumWidth(0)

    def _open_project_menu(self) -> None:
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.addAction("Open Settings…", self._open_settings_drawer)
        menu.addAction("Refresh projects", self.controller.refresh_project_list)
        menu.addSeparator()
        for index in range(self.project_combo.count()):
            action = menu.addAction(self.project_combo.itemText(index))
            slug = self.project_combo.itemData(index)
            action.triggered.connect(
                lambda _checked=False, slug=slug: (
                    self.project_combo.setCurrentIndex(
                        self.project_combo.findData(slug)
                    ),
                    self.controller.on_load_project(),
                )
            )
        menu.exec_(self.provider_bar.project_pill.mapToGlobal(
            self.provider_bar.project_pill.rect().bottomLeft()
        ))

    def _open_asset_menu(self) -> None:
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.addAction("Open Settings…", self._open_settings_drawer)
        menu.addAction("Refresh assets", self.controller.refresh_asset_list)
        menu.addAction("New asset", self.controller.on_new_asset)
        menu.addSeparator()
        for index in range(self.asset_combo.count()):
            action = menu.addAction(self.asset_combo.itemText(index))
            slug = self.asset_combo.itemData(index)
            action.triggered.connect(
                lambda _checked=False, slug=slug: (
                    self.asset_combo.setCurrentIndex(self.asset_combo.findData(slug)),
                    self.controller.on_load_asset(),
                )
            )
        menu.exec_(self.provider_bar.asset_pill.mapToGlobal(
            self.provider_bar.asset_pill.rect().bottomLeft()
        ))

    # ------------------------------------------------------------------
    # Helpers exposed for tests and other widgets
    # ------------------------------------------------------------------
    def show_prompt_plan(self, visible: bool) -> None:
        self.workspace_panel.show_prompt_plan(visible)

    def show_preflight(self, text: str) -> None:
        self.workspace_panel.show_preflight(text)

    def show_generated_output(self) -> None:
        self.workspace_panel.show_generated_output()

    def show_generation_pending(self) -> None:
        self.workspace_panel.show_generation_pending()

    def flash_status(self, text: str, state: str = "success") -> None:
        self.action_footer.flash_status(text, state)

    def set_busy_state(self, busy: bool) -> None:
        self.action_footer.set_busy(busy)
        # Disable provider/model inputs during long operations
        for widget in (
            self.image_provider_combo,
            self.image_model_edit,
            self.image_api_key_edit,
            self.prompt_provider_combo,
            self.prompt_model_edit,
            self.prompt_api_key_edit,
        ):
            widget.setEnabled(not busy)
        self.save_btn.setEnabled(not busy)
        self.enhance_btn.setEnabled(not busy)
        self.generate_btn.setEnabled(not busy)
        self.check_run_btn.setEnabled(not busy)
        self.preview_prompts_btn.setEnabled(not busy)
        self.export_sprites_btn.setEnabled(not busy)
        self.export_project_btn.setEnabled(not busy)
        self.open_project_gallery_btn.setEnabled(not busy)
        self.open_folder_btn.setEnabled(not busy)
        self.open_gallery_btn.setEnabled(not busy)
        self.try_sample_run_btn.setEnabled(not busy)

    def open_local_path(self, path) -> None:
        path = str(path)
        if os.name == "nt":
            os.startfile(path)
        elif os.name == "posix":
            import subprocess

            subprocess.run(["open", path] if sys.platform == "darwin" else ["xdg-open", path])

    def _open_output_folder(self) -> None:
        self.open_local_path(self._last_output_dir)

    def _open_gallery(self) -> None:
        if not self._last_gallery_path:
            self.status_label.setText("No generated gallery is available yet")
            return
        gallery_path = Path(self._last_gallery_path)
        if not gallery_path.exists():
            self.status_label.setText(f"Gallery not found: {gallery_path}")
            return
        self.open_local_path(gallery_path)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and not self.welcome_overlay.isHidden():
            self._welcome_skip()
            return
        if event.key() == Qt.Key.Key_Escape and not self.settings_drawer.isHidden():
            self._close_settings_drawer()
            return
        super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Backwards-compatible method names
    # ------------------------------------------------------------------
    def _on_save_plan(self) -> None:
        self.controller.on_save_plan()

    def _on_load_project(self) -> None:
        self.controller.on_load_project()

    def _on_load_asset(self) -> None:
        self.controller.on_load_asset()

    def _on_new_asset(self) -> None:
        self.controller.on_new_asset()

    def _on_apply_project_starter(self) -> None:
        self.controller.on_apply_project_starter()

    def _on_try_sample_run(self) -> None:
        self.controller.on_try_sample_run()

    def _on_apply_workflow_preset(self) -> None:
        self.controller.on_apply_workflow_preset()

    def _on_preview_prompts(self) -> None:
        self.controller.on_preview_prompts()

    def _on_check_run(self) -> None:
        self.controller.on_check_run()

    def _on_check_provider_setup(self) -> None:
        self.controller.on_check_provider_setup()

    def _on_save_provider_settings(self) -> None:
        self.controller.on_save_provider_settings()

    def _on_clear_saved_keys(self) -> None:
        self.controller.on_clear_saved_keys()

    def _on_refresh_models(self) -> None:
        self.controller.on_refresh_models()

    def _on_improve_project(self) -> None:
        self.controller.on_improve_project()

    def _on_improve_asset_type(self) -> None:
        self.controller.on_improve_asset_type()

    def _on_enhance(self) -> None:
        self.controller.on_enhance()

    def _on_generate(self) -> None:
        self.controller.on_generate()

    def _on_export_asset(self) -> None:
        self.controller.on_export_asset()

    def _on_export_project(self) -> None:
        self.controller.on_export_project()

    def _on_open_project_gallery(self) -> None:
        self.controller.on_open_project_gallery()

    def _on_image_provider_changed(self, *_args) -> None:
        self.controller.on_image_provider_changed()

    def _on_prompt_provider_changed(self, *_args) -> None:
        self.controller.on_prompt_provider_changed()

    def _on_shared_provider_setup_changed(self, *_args) -> None:
        self.controller.on_shared_provider_setup_changed()

    def _on_footer_save(self) -> None:
        self.controller.on_save_plan()

    def _on_thread_error(self, message: str) -> None:
        self.controller.on_thread_error(message)

    # ------------------------------------------------------------------
    # Internal back-compat shims for tests poking at private methods
    # ------------------------------------------------------------------
    def _save_current_specs(self):
        return self.controller.save_current_specs()

    def _build_project_spec(self):
        return self.controller.build_project_spec()

    def _build_asset_spec(self):
        return self.controller.build_asset_spec()

    def _apply_project_spec(self, project: ProjectSpec) -> None:
        self.controller.apply_project_spec(project)

    def _apply_asset_spec(self, project: ProjectSpec, asset) -> None:
        self.controller.apply_asset_spec(project, asset)

    def _apply_asset_type_spec(self, asset_type) -> None:
        self.controller.apply_asset_type_spec(asset_type)

    def _load_asset_preview(self, project: ProjectSpec, asset) -> None:
        self.controller.load_asset_preview(project, asset)

    def _refresh_project_list(self, selected_slug: str | None = None) -> None:
        self.controller.refresh_project_list(selected_slug)

    def _refresh_asset_list(self, selected_slug: str | None = None) -> None:
        self.controller.refresh_asset_list(selected_slug)

    def _refresh_layout_combo(
        self, project: ProjectSpec | None = None, selected_name: str | None = None
    ) -> None:
        self.controller.refresh_layout_combo(project, selected_name)

    def _refresh_api_key_fields(self) -> None:
        self.controller.refresh_api_key_fields()

    def _refresh_api_key_field(self, purpose: str) -> None:
        self.controller.refresh_api_key_field(purpose)

    def _refresh_palette_swatches(self) -> None:
        self.palette_swatches.set_palette(
            [segment.strip() for segment in self.palette_edit.text().split(",") if segment.strip()]
        )

    def _refresh_model_suggestions(self, role: str, provider: str) -> None:
        self.controller.refresh_model_suggestions(role, provider)

    def _apply_model_suggestion(self, role: str) -> None:
        self.controller.apply_model_suggestion(role)

    def _on_save_provider_settings(self) -> None:  # type: ignore[no-redef]
        self.controller.on_save_provider_settings()

    def _on_clear_saved_keys(self) -> None:  # type: ignore[no-redef]
        self.controller.on_clear_saved_keys()

    def _on_model_discovery_finished(self, result: dict) -> None:
        self.controller.on_model_discovery_finished(result)

    def _on_project_improved(self, data: dict, project: ProjectSpec) -> None:
        self.controller.on_project_improved(data, project)

    def _on_asset_type_improved(self, data, project, asset_type) -> None:
        self.controller.on_asset_type_improved(data, project, asset_type)

    def _on_enhance_finished(self, enhanced: str, project: ProjectSpec, asset) -> None:
        self.controller.on_enhance_finished(enhanced, project, asset)

    def _on_generation_finished(self, result) -> None:
        self.controller.on_generation_finished(result)

    def _on_add_grid_layout(self) -> None:
        self.controller.on_add_grid_layout()

    def _on_add_hero_grid_layout(self) -> None:
        self.controller.on_add_hero_grid_layout()

    def _save_custom_layout(self, layout) -> None:
        self.controller.save_custom_layout(layout)

    def _build_grid_layout(self):
        return self.controller.build_grid_layout()

    def _build_hero_grid_layout(self):
        return self.controller.build_hero_grid_layout()

    def _build_generation_preflight(self, project, asset, image_api_key, prompt_api_key):
        return self.controller.build_generation_preflight(
            project, asset, image_api_key, prompt_api_key
        )

    def _write_project_gallery(self, project: ProjectSpec | None = None) -> str:
        return self.controller.write_project_gallery(project)

    def _format_prompt_packets(self, packets) -> str:
        return self.controller.format_prompt_packets(packets)

    def _format_generation_preflight(self, preflight) -> str:
        return self.controller.format_generation_preflight(preflight)

    def _generation_output_title(self, stage_label, stage_index, layout_name, variant_index=None):
        return self.controller.generation_output_title(
            stage_label, stage_index, layout_name, variant_index
        )

    def _validate_current_model(self, role: str, provider: str, model: str):
        return self.controller.validate_current_model(role, provider, model)

    def _api_key_for(self, provider: str, purpose: str = "image") -> str:
        return self.controller.api_key_for(provider, purpose)

    def _configured_api_key_for(self, provider: str) -> str:
        return self.controller.configured_api_key_for(provider)

    def _provider_can_run(self, provider: str, api_key: str) -> bool:
        return self.controller.provider_can_run(provider, api_key)

    def _using_shared_provider_setup(self) -> bool:
        return self.controller.using_shared_provider_setup()

    def _set_busy(self, busy: bool, status: str) -> None:
        self.controller.set_busy(busy, status)

    def _set_combo_value(self, combo, value) -> None:
        self.controller.set_combo_value(combo, value)

    def _palette_values(self) -> list[str]:
        return self.controller.palette_values()

    def _evolution_labels(self) -> list[str]:
        return self.controller.evolution_labels()

    def _existing_project(self, slug):
        return self.controller.existing_project(slug)

    def _project_slug_from_fields(self) -> str:
        return self.controller.project_slug_from_fields()

    def _browse_project_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Project Directory", self.project_root_edit.text()
        )
        if folder:
            self.project_root_edit.setText(folder)
            self.controller.refresh_project_list()

    def _manifest_image_path(self, value, base_dir):
        return self.controller.manifest_image_path(value, base_dir)

    def _open_tool_dialog(self, name: str) -> None:
        # Legacy: route to settings drawer instead
        self._open_settings_drawer()

    def _open_local_path(self, path) -> None:
        self.open_local_path(path)

    def welcome_pollinations(self) -> None:
        self._welcome_pollinations()

    def welcome_openrouter(self, key: str) -> None:
        self._welcome_openrouter(key)

    def welcome_openai(self, key: str) -> None:
        self._welcome_openai(key)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


# Backwards-compatible re-exports so tests can do
# ``from spritegen.ui.main_window import PreviewPanel`` etc.
from .preview_panel import PaletteSwatchBar, PreviewPanel  # noqa: E402,F401
from .model_picker import ModelPicker  # noqa: E402,F401
from .generation_thread import (  # noqa: E402,F401
    ModelDiscoveryThread,
    ProjectGenerationThread,
    EnhancementThread,
    ProjectEnhancementThread,
    AssetTypeEnhancementThread,
)


# Bind the thread classes to the module so monkeypatch tests that do
# ``monkeypatch.setattr(main_window_mod, "ModelDiscoveryThread", FakeClass)``
# work, and so the controller can look them up via ``self.main.<Class>``.
MainWindow.ModelDiscoveryThread = ModelDiscoveryThread  # type: ignore[attr-defined]
MainWindow.ProjectGenerationThread = ProjectGenerationThread  # type: ignore[attr-defined]
MainWindow.EnhancementThread = EnhancementThread  # type: ignore[attr-defined]
MainWindow.ProjectEnhancementThread = ProjectEnhancementThread  # type: ignore[attr-defined]
MainWindow.AssetTypeEnhancementThread = AssetTypeEnhancementThread  # type: ignore[attr-defined]
