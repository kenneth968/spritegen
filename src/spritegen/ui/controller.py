"""Orchestration methods for the desktop main window.

The controller holds the `_on_*` and `_build_*` methods that used to live on
``MainWindow``.  It is constructed with a reference to the main window so it
can read and write widget state, manage the settings store, and start
background threads.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QMessageBox

from ..layouts import AssetLayout
from ..preflight import (
    KEYED_PROVIDERS,
    PREFLIGHT_ERROR,
    GenerationPreflightReport,
    build_generation_preflight,
)
from ..project_export import ProjectAssetExporter
from ..project_gallery import ProjectGalleryWriter
from ..project_starters import get_project_starter
from ..projects import (
    AssetSpec,
    AssetTypeSpec,
    ColorTreatment,
    EvolutionPlan,
    PostProcessSettings,
    ProjectSpec,
    ProjectStore,
    ProviderDefaults,
    PromptPlanner,
    apply_asset_type_enhancement,
    apply_project_enhancement,
    slugify,
)
from ..provider_models import (
    IMAGE_ROLE,
    MODEL_VALIDATION_ERROR,
    MODEL_VALIDATION_WARNING,
    PROMPT_ROLE,
    ModelSuggestion,
    ModelValidationResult,
    PROVIDER_LABELS,
    default_model,
    validate_model_choice,
)
from ..user_settings import UserSettings
from ..workflow_presets import get_workflow_preset
from .generation_thread import (  # noqa: F401  (re-exported via main_window for tests)
    AssetTypeEnhancementThread,
    EnhancementThread,
    ModelDiscoveryThread,
    ProjectEnhancementThread,
    ProjectGenerationThread,
)


class MainWindowController:
    """Owns the orchestration logic for the desktop main window."""

    def __init__(self, main_window) -> None:
        self.main = main_window
        self._thread = None

    # ------------------------------------------------------------------
    # Attribute proxies so methods can read widget state in one place.
    # ------------------------------------------------------------------
    @property
    def _settings_store(self):
        return self.main._settings_store

    @property
    def _user_settings(self) -> UserSettings:
        return self.main._user_settings

    @_user_settings.setter
    def _user_settings(self, value: UserSettings) -> None:
        self.main._user_settings = value

    @property
    def _current_project(self):
        return self.main._current_project

    @_current_project.setter
    def _current_project(self, value) -> None:
        self.main._current_project = value

    @property
    def _last_output_dir(self) -> str:
        return self.main._last_output_dir

    @_last_output_dir.setter
    def _last_output_dir(self, value: str) -> None:
        self.main._last_output_dir = value

    @property
    def _last_gallery_path(self) -> str:
        return self.main._last_gallery_path

    @_last_gallery_path.setter
    def _last_gallery_path(self, value: str) -> None:
        self.main._last_gallery_path = value

    @property
    def _last_project_gallery_path(self) -> str:
        return self.main._last_project_gallery_path

    @_last_project_gallery_path.setter
    def _last_project_gallery_path(self, value: str) -> None:
        self.main._last_project_gallery_path = value

    @property
    def _online_model_suggestions(self):
        return self.main._online_model_suggestions

    @property
    def _project_root(self) -> str:
        return self.main._project_root

    # ------------------------------------------------------------------
    # Settings & API keys
    # ------------------------------------------------------------------
    def on_image_provider_changed(self, *_args) -> None:
        provider = self.main.image_provider_combo.currentData()
        self.refresh_model_suggestions(IMAGE_ROLE, provider)
        self.main.image_model_edit.setText(default_model(provider, IMAGE_ROLE))
        self.refresh_api_key_field("image")

    def on_prompt_provider_changed(self, *_args) -> None:
        provider = self.main.prompt_provider_combo.currentData()
        self.refresh_model_suggestions(PROMPT_ROLE, provider)
        self.main.prompt_model_edit.setText(default_model(provider, PROMPT_ROLE))
        self.refresh_api_key_field("prompt")

    def apply_user_settings(self) -> None:
        self.set_combo_value(
            self.main.image_provider_combo, self._user_settings.image_provider
        )
        self.refresh_model_suggestions(
            IMAGE_ROLE, self.main.image_provider_combo.currentData()
        )
        self.main.image_model_edit.setText(
            self._user_settings.image_model
            or default_model(self.main.image_provider_combo.currentData(), IMAGE_ROLE)
        )
        self.set_combo_value(
            self.main.prompt_provider_combo, self._user_settings.prompt_provider
        )
        self.refresh_model_suggestions(
            PROMPT_ROLE, self.main.prompt_provider_combo.currentData()
        )
        self.main.prompt_model_edit.setText(
            self._user_settings.prompt_model
            or default_model(self.main.prompt_provider_combo.currentData(), PROMPT_ROLE)
        )
        self.refresh_api_key_fields()

    def refresh_model_suggestions(self, role: str, provider: str) -> None:
        combo = (
            self.main.image_model_suggestions
            if role == IMAGE_ROLE
            else self.main.prompt_model_suggestions
        )
        current_model = combo.text() if hasattr(combo, "text") else combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        online = self._online_model_suggestions.get((role, provider), [])
        for suggestion in combined_model_suggestions_local(provider, role, online):
            combo.addItem(f"{suggestion.label} ({suggestion.model})", suggestion.model)
        combo.blockSignals(False)
        if hasattr(combo, "setText") and current_model:
            combo.setText(str(current_model))

    def apply_model_suggestion(self, role: str) -> None:
        combo = (
            self.main.image_model_suggestions
            if role == IMAGE_ROLE
            else self.main.prompt_model_suggestions
        )
        model = combo.currentData()
        if not model:
            return
        if role == IMAGE_ROLE:
            self.main.image_model_edit.setText(model)
        else:
            self.main.prompt_model_edit.setText(model)

    def refresh_api_key_fields(self) -> None:
        self.refresh_api_key_field("image")
        self.refresh_api_key_field("prompt")

    def refresh_api_key_field(self, purpose: str) -> None:
        if not hasattr(self.main, "image_api_key_edit"):
            return
        if purpose == "prompt":
            provider = self.main.prompt_provider_combo.currentData()
            edit = self.main.prompt_api_key_edit
        else:
            provider = self.main.image_provider_combo.currentData()
            edit = self.main.image_api_key_edit
        needs_key = provider in KEYED_PROVIDERS
        edit.setEnabled(needs_key)
        edit.setPlaceholderText("Paste provider API key" if needs_key else "No key needed")
        if needs_key:
            edit.setText(self.configured_api_key_for(provider))
        else:
            edit.clear()

    # ------------------------------------------------------------------
    # Project / asset load/save
    # ------------------------------------------------------------------
    def refresh_project_list(self, selected_slug: str | None = None) -> None:
        if not hasattr(self.main, "project_combo"):
            return
        selected = selected_slug or self.main.project_combo.currentData()
        self.main.project_combo.clear()
        store = ProjectStore(self.main.project_root_edit.text())
        for project in store.list_projects():
            self.main.project_combo.addItem(f"{project.name} ({project.slug})", project.slug)
        if selected:
            index = self.main.project_combo.findData(selected)
            if index >= 0:
                self.main.project_combo.setCurrentIndex(index)
        self.refresh_asset_list()

    def refresh_asset_list(self, selected_slug: str | None = None) -> None:
        if not hasattr(self.main, "asset_combo"):
            return
        selected = selected_slug or self.main.asset_combo.currentData()
        self.main.asset_combo.clear()
        project_slug = self.project_slug_from_fields()
        if not project_slug:
            return
        store = ProjectStore(self.main.project_root_edit.text())
        for asset in store.load_assets_for_slug(project_slug):
            self.main.asset_combo.addItem(f"{asset.name} ({asset.asset_type})", asset.slug)
        if selected:
            index = self.main.asset_combo.findData(selected)
            if index >= 0:
                self.main.asset_combo.setCurrentIndex(index)

    def refresh_layout_combo(
        self,
        project: ProjectSpec | None = None,
        selected_name: str | None = None,
    ) -> None:
        if not hasattr(self.main, "layout_combo"):
            return
        from ..layouts import PRESET_LAYOUTS

        selected = selected_name or self.main.layout_combo.currentData()
        self.main.layout_combo.clear()
        for name in sorted(PRESET_LAYOUTS):
            self.main.layout_combo.addItem(name, name)
        if project:
            for name in sorted(project.custom_layouts):
                self.main.layout_combo.addItem(f"{name} (project)", name)
        if selected:
            self.set_combo_value(self.main.layout_combo, selected)

    def on_load_project(self) -> None:
        slug = self.main.project_combo.currentData()
        if not slug:
            self.main.status_label.setText("No saved project selected")
            return
        try:
            project = ProjectStore(self.main.project_root_edit.text()).load_project(slug)
            self.apply_project_spec(project)
            self.refresh_asset_list()
            self.main.status_label.setText(f"Loaded project: {project.name}")
        except Exception as exc:
            QMessageBox.warning(self.main, "Load Project Failed", str(exc))

    def on_load_asset(self) -> None:
        slug = self.main.asset_combo.currentData()
        if not slug:
            self.main.status_label.setText("No saved asset selected")
            return
        try:
            store = ProjectStore(self.main.project_root_edit.text())
            project = self._current_project or store.load_project(self.project_slug_from_fields())
            asset = store.load_asset(project, slug)
            self.apply_asset_spec(project, asset)
            self.load_asset_preview(project, asset)
            self.main.status_label.setText(f"Loaded asset: {asset.name}")
        except Exception as exc:
            QMessageBox.warning(self.main, "Load Asset Failed", str(exc))

    def on_new_asset(self) -> None:
        self.main.asset_name_edit.clear()
        self.main.asset_description_edit.clear()
        self.main.asset_details_edit.clear()
        self.main.enhanced_prompt_edit.clear()
        self.main.preview_panel.clear()
        self.main.status_label.setText("Ready for a new asset")

    def on_save_plan(self) -> None:
        try:
            project, asset = self.save_current_specs()
            self.refresh_project_list(project.slug)
            self.refresh_asset_list(asset.slug)
            self.main.status_label.setText(f"Saved {project.name} / {asset.name}")
        except Exception as exc:
            QMessageBox.warning(self.main, "Save Failed", str(exc))

    # ------------------------------------------------------------------
    # Project starter / workflow preset
    # ------------------------------------------------------------------
    def on_apply_project_starter(self) -> None:
        try:
            starter = get_project_starter(self.main.project_starter_combo.currentData())
            image_provider = self.main.image_provider_combo.currentData()
            prompt_provider = self.main.prompt_provider_combo.currentData()
            project = starter.build_project(
                image_provider=image_provider,
                image_model=(
                    self.main.image_model_edit.text().strip()
                    or default_model(image_provider, IMAGE_ROLE)
                ),
                prompt_provider=prompt_provider,
                prompt_model=(
                    self.main.prompt_model_edit.text().strip()
                    or default_model(prompt_provider, PROMPT_ROLE)
                ),
            )
            asset = starter.build_first_asset()
            asset_type = project.get_asset_type(asset.asset_type)
            project.get_layout(asset.layout or asset_type.default_layout)

            self.apply_project_spec(project)
            self.apply_asset_spec(project, asset)

            store = ProjectStore(self.main.project_root_edit.text())
            store.save_project(project)
            store.save_asset(project, asset)
            known_assets = store.load_assets(project)
            packets = PromptPlanner().build_prompt_packets(
                project,
                asset,
                known_assets=known_assets,
            )
            store.save_prompt_plan(project, asset, packets)
            self.refresh_project_list(project.slug)
            self.refresh_asset_list(asset.slug)
            self.main.status_label.setText(
                f"Created starter {project.name} / {asset.name} ({len(packets)} prompt(s))"
            )
        except Exception as exc:
            QMessageBox.warning(self.main, "Starter Failed", str(exc))

    def on_apply_workflow_preset(self) -> None:
        try:
            preset = get_workflow_preset(self.main.workflow_preset_combo.currentData())
            asset_type = preset.to_asset_type()
            self.apply_asset_type_spec(asset_type)
            self.main.status_label.setText(f"Applied workflow preset: {preset.label}")
        except Exception as exc:
            QMessageBox.warning(self.main, "Preset Failed", str(exc))

    # ------------------------------------------------------------------
    # Prompt plan / run check
    # ------------------------------------------------------------------
    def on_preview_prompts(self) -> None:
        try:
            project, asset = self.save_current_specs()
            store = ProjectStore(self.main.project_root_edit.text())
            known_assets = store.load_assets(project)
            packets = PromptPlanner().build_prompt_packets(
                project,
                asset,
                known_assets=known_assets,
            )
            plan_path = store.save_prompt_plan(project, asset, packets)
            self.main.prompt_preview_edit.setPlainText(self.format_prompt_packets(packets))
            self.refresh_project_list(project.slug)
            self.refresh_asset_list(asset.slug)
            self.main.status_label.setText(f"Previewed {len(packets)} prompt(s): {plan_path}")
            self.main.run_summary_label.setText(f"Prompt plan ready: {len(packets)} prompt(s)")
            self.main.show_prompt_plan(True)
        except Exception as exc:
            QMessageBox.warning(self.main, "Prompt Preview Failed", str(exc))

    def format_prompt_packets(self, packets) -> str:
        sections = []
        for packet in packets:
            label = packet.stage_label or "single"
            sections.append(
                "\n".join(
                    [
                        f"--- {label} / {packet.layout_name} ---",
                        packet.prompt,
                        "",
                        f"Negative: {packet.negative_prompt}",
                    ]
                )
            )
        return "\n\n".join(sections)

    def on_check_run(self) -> None:
        try:
            project, asset = self.save_current_specs()
            preflight = self.build_generation_preflight(
                project,
                asset,
                image_api_key=self.api_key_for(
                    self.main.image_provider_combo.currentData(), "image"
                ),
                prompt_api_key=self.api_key_for(
                    self.main.prompt_provider_combo.currentData(), "prompt"
                ),
            )
            self.main.prompt_preview_edit.setPlainText(self.format_generation_preflight(preflight))
            self.refresh_project_list(project.slug)
            self.refresh_asset_list(asset.slug)
            status = "Run check ready" if preflight.ready else "Run check needs attention"
            summary = (
                f"{status}: {preflight.image_count} image(s), "
                f"{preflight.slice_count} slice(s)"
            )
            self.main.status_label.setText(summary)
            self.main.run_summary_label.setText(summary)
            self.main.show_prompt_plan(True)
        except Exception as exc:
            QMessageBox.warning(self.main, "Run Check Failed", str(exc))

    def format_generation_preflight(self, preflight: GenerationPreflightReport) -> str:
        lines = [
            f"Preflight: {preflight.status}",
            f"Project: {preflight.project_name}",
            f"Asset: {preflight.asset_name}",
            f"Image model: {preflight.image_provider} / {preflight.image_model}",
        ]
        if preflight.enhance_first:
            lines.append(
                f"Prompt model: {preflight.prompt_provider} / {preflight.prompt_model}"
            )
        else:
            lines.append("Prompt enhancement: disabled")
        lines.extend(
            [
                (
                    f"Images: {preflight.image_count} atlas image(s), "
                    f"{preflight.slice_count} sliced sprite(s)"
                ),
                f"Variants per prompt packet: {preflight.variants_per_packet}",
            ]
        )
        if preflight.layout_summaries:
            lines.append("Layouts:")
            lines.extend(
                f"- {name}: {summary}"
                for name, summary in preflight.layout_summaries.items()
            )
        if preflight.reference_asset_count:
            lines.append(f"Reference assets: {preflight.reference_asset_count}")
            for reference in preflight.reference_asset_summaries:
                lines.append(
                    f"- {reference.name} [{reference.asset_type}]: {reference.prompt}"
                )
                if reference.details:
                    lines.append(f"  details: {reference.details}")
                if reference.layout:
                    lines.append(f"  layout: {reference.layout}")
        if preflight.issues:
            lines.append("Issues:")
            lines.extend(
                f"- {issue.level.upper()}: {issue.message}"
                for issue in preflight.issues
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Layout builder
    # ------------------------------------------------------------------
    def on_add_grid_layout(self) -> None:
        try:
            self.save_custom_layout(self.build_grid_layout())
        except Exception as exc:
            QMessageBox.warning(self.main, "Layout Failed", str(exc))

    def on_add_hero_grid_layout(self) -> None:
        try:
            self.save_custom_layout(self.build_hero_grid_layout())
        except Exception as exc:
            QMessageBox.warning(self.main, "Layout Failed", str(exc))

    def save_custom_layout(self, layout: AssetLayout) -> None:
        project = self.build_project_spec()
        project.add_layout(layout)
        asset_type_name = self.main.asset_type_edit.text().strip() or "asset"
        if asset_type_name in project.asset_types:
            project.asset_types[asset_type_name].default_layout = layout.name
        self._current_project = project
        store = ProjectStore(self.main.project_root_edit.text())
        store.save_project(project)
        self.refresh_project_list(project.slug)
        self.refresh_layout_combo(project, layout.name)
        self.main.status_label.setText(
            f"Saved layout {layout.name}: "
            f"{layout.width}x{layout.height}, {len(layout.regions)} regions"
        )

    def build_grid_layout(self) -> AssetLayout:
        name = self.main.layout_name_edit.text().strip()
        if not name:
            raise ValueError("Layout name is required")
        layout_name = slugify(name).replace("-", "_")
        if not layout_name:
            raise ValueError("Layout name is required")
        width = self.main.layout_width_spin.value()
        height = self.main.layout_height_spin.value()
        rows = self.main.layout_rows_spin.value()
        columns = self.main.layout_columns_spin.value()
        if width % columns or height % rows:
            raise ValueError("Canvas width and height must divide evenly by the grid")
        prefix = self.main.layout_region_prefix_edit.text().strip() or "cell"
        region_prefix = slugify(prefix).replace("-", "_") or "cell"
        layout = AssetLayout.grid(
            name=layout_name,
            width=width,
            height=height,
            rows=rows,
            columns=columns,
            region_prefix=region_prefix,
        )
        prompt_instructions = self.main.layout_prompt_edit.toPlainText().strip()
        if prompt_instructions:
            layout.prompt_instructions = prompt_instructions
        return layout

    def build_hero_grid_layout(self) -> AssetLayout:
        name = self.main.layout_name_edit.text().strip()
        if not name:
            raise ValueError("Layout name is required")
        width = self.main.layout_width_spin.value()
        height = self.main.layout_height_spin.value()
        hero_width = self.main.hero_width_spin.value()
        rows = self.main.layout_rows_spin.value()
        columns = self.main.layout_columns_spin.value()
        hero_name = self.main.hero_region_name_edit.text().strip() or "full_body"
        prefix = self.main.layout_region_prefix_edit.text().strip() or "cell"
        layout = AssetLayout.hero_plus_grid(
            name=name,
            width=width,
            height=height,
            hero_width=hero_width,
            grid_rows=rows,
            grid_columns=columns,
            hero_region_name=hero_name,
            grid_region_prefix=prefix,
        )
        prompt_instructions = self.main.layout_prompt_edit.toPlainText().strip()
        if prompt_instructions:
            layout.prompt_instructions = prompt_instructions
        return layout

    # ------------------------------------------------------------------
    # Provider setup
    # ------------------------------------------------------------------
    def on_check_provider_setup(self) -> None:
        missing = []
        image_provider = self.main.image_provider_combo.currentData()
        prompt_provider = self.main.prompt_provider_combo.currentData()
        validations = [
            self.validate_current_model(
                IMAGE_ROLE, image_provider, self.main.image_model_edit.text()
            ),
            self.validate_current_model(
                PROMPT_ROLE, prompt_provider, self.main.prompt_model_edit.text()
            ),
        ]
        model_errors = [
            v.message
            for v in validations
            if v.status == MODEL_VALIDATION_ERROR
        ]
        model_warnings = [
            v.message
            for v in validations
            if v.status == MODEL_VALIDATION_WARNING
        ]
        if image_provider in KEYED_PROVIDERS and not self.api_key_for(
            image_provider, "image"
        ):
            missing.append(f"{PROVIDER_LABELS[image_provider]} image key")
        if prompt_provider in KEYED_PROVIDERS and not self.api_key_for(
            prompt_provider, "prompt"
        ):
            missing.append(f"{PROVIDER_LABELS[prompt_provider]} prompt key")
        if missing or model_errors:
            self.main.status_label.setText(
                "Provider setup needs: " + ", ".join([*missing, *model_errors])
            )
            return
        ready_status = (
            "Provider setup ready: "
            f"image {PROVIDER_LABELS[image_provider]} / "
            f"prompt {PROVIDER_LABELS[prompt_provider]}"
        )
        if model_warnings:
            self.main.status_label.setText(
                "Provider setup ready with notes: "
                f"image {PROVIDER_LABELS[image_provider]} / "
                f"prompt {PROVIDER_LABELS[prompt_provider]}; "
                + "; ".join(model_warnings)
            )
            return
        self.main.status_label.setText(ready_status)

    def validate_current_model(
        self, role: str, provider: str, model: str
    ) -> ModelValidationResult:
        other_role = PROMPT_ROLE if role == IMAGE_ROLE else IMAGE_ROLE
        return validate_model_choice(
            provider,
            role,
            model,
            extra=self._online_model_suggestions.get((role, provider), []),
            other_extra=self._online_model_suggestions.get(
                (other_role, provider), []
            ),
        )

    def on_save_provider_settings(self) -> None:
        settings = UserSettings(
            image_provider=self.main.image_provider_combo.currentData(),
            image_model=self.main.image_model_edit.text().strip(),
            prompt_provider=self.main.prompt_provider_combo.currentData(),
            prompt_model=self.main.prompt_model_edit.text().strip(),
            api_keys=dict(self._user_settings.api_keys),
        )
        image_key = self.main.image_api_key_edit.text()
        prompt_key = self.main.prompt_api_key_edit.text()
        if settings.image_provider == settings.prompt_provider:
            settings.set_api_key(settings.image_provider, prompt_key or image_key)
        else:
            settings.set_api_key(settings.image_provider, image_key)
            settings.set_api_key(settings.prompt_provider, prompt_key)
        path = self._settings_store.save(settings)
        self._user_settings = settings
        self.main.status_label.setText(f"Saved local provider setup to {path}")
        self.main.flash_status("Saved", "success")
        self.main.update_provider_chip()

    def on_clear_saved_keys(self) -> None:
        self._user_settings.api_keys.clear()
        self._settings_store.save(self._user_settings)
        self.refresh_api_key_fields()
        self.main.status_label.setText("Cleared saved local API keys")
        self.main.flash_status("Cleared", "warning")

    def on_refresh_models(self) -> None:
        self.set_busy(True, "Refreshing provider model lists...")
        self._thread = self._thread_class("ModelDiscoveryThread")(
            image_provider=self.main.image_provider_combo.currentData(),
            prompt_provider=self.main.prompt_provider_combo.currentData(),
            search=self.main.model_search_edit.text(),
            source=self.main.model_catalog_source_combo.currentData() or "auto",
        )
        self._thread.finished.connect(self.on_model_discovery_finished)
        self._thread.start()

    def on_model_discovery_finished(self, result: dict) -> None:
        suggestions = result.get("suggestions", {})
        for key, values in suggestions.items():
            self._online_model_suggestions[key] = values
        self.refresh_model_suggestions(
            IMAGE_ROLE, self.main.image_provider_combo.currentData()
        )
        self.refresh_model_suggestions(
            PROMPT_ROLE, self.main.prompt_provider_combo.currentData()
        )
        count = sum(len(values) for values in suggestions.values())
        errors = result.get("errors", [])
        if count:
            status = f"Loaded {count} online model suggestion(s)"
            if errors:
                status += f"; {len(errors)} provider refresh issue(s)"
        elif errors:
            status = "Could not refresh model lists: " + "; ".join(errors)
        else:
            status = "No online model suggestions available for selected providers"
        self.set_busy(False, status)
        self._thread = None

    # ------------------------------------------------------------------
    # AI Enhance / Improve / Generate
    # ------------------------------------------------------------------
    def on_improve_project(self) -> None:
        try:
            project = self.build_project_spec()
        except Exception as exc:
            QMessageBox.warning(self.main, "Improve Project Failed", str(exc))
            return

        provider = self.main.prompt_provider_combo.currentData()
        api_key = self.api_key_for(provider, "prompt")
        if not self.provider_can_run(provider, api_key):
            return

        self.set_busy(True, "Improving project art direction...")
        self._thread = self._thread_class("ProjectEnhancementThread")(
            project=project,
            provider=provider,
            model=self.main.prompt_model_edit.text().strip(),
            api_key=api_key,
        )
        self._thread.finished.connect(
            lambda data: self.on_project_improved(data, project)
        )
        self._thread.error.connect(self.on_thread_error)
        self._thread.start()

    def on_project_improved(self, data: dict, project: ProjectSpec) -> None:
        apply_project_enhancement(project, data)
        self.apply_project_spec(project)
        store = ProjectStore(self.main.project_root_edit.text())
        store.save_project(project)
        self.refresh_project_list(project.slug)
        self.set_busy(False, "Project art direction improved")
        self._thread = None

    def on_improve_asset_type(self) -> None:
        try:
            project = self.build_project_spec()
            asset_type = project.get_asset_type(
                self.main.asset_type_edit.text().strip() or "asset"
            )
        except Exception as exc:
            QMessageBox.warning(self.main, "Improve Type Failed", str(exc))
            return

        provider = self.main.prompt_provider_combo.currentData()
        api_key = self.api_key_for(provider, "prompt")
        if not self.provider_can_run(provider, api_key):
            return

        self.set_busy(True, "Improving asset-type rules...")
        self._thread = self._thread_class("AssetTypeEnhancementThread")(
            project=project,
            asset_type=asset_type,
            provider=provider,
            model=self.main.prompt_model_edit.text().strip(),
            api_key=api_key,
        )
        self._thread.finished.connect(
            lambda data: self.on_asset_type_improved(data, project, asset_type)
        )
        self._thread.error.connect(self.on_thread_error)
        self._thread.start()

    def on_asset_type_improved(
        self,
        data: dict,
        project: ProjectSpec,
        asset_type: AssetTypeSpec,
    ) -> None:
        apply_asset_type_enhancement(asset_type, data)
        project.add_asset_type(asset_type)
        self._current_project = project
        self.apply_asset_type_spec(asset_type)
        store = ProjectStore(self.main.project_root_edit.text())
        store.save_project(project)
        self.refresh_project_list(project.slug)
        self.set_busy(False, "Asset-type rules improved")
        self._thread = None

    def on_enhance(self) -> None:
        try:
            project, asset = self.save_current_specs()
        except Exception as exc:
            QMessageBox.warning(self.main, "Enhance Failed", str(exc))
            return

        provider = self.main.prompt_provider_combo.currentData()
        api_key = self.api_key_for(provider, "prompt")
        if not self.provider_can_run(provider, api_key):
            return

        self.set_busy(True, "Enhancing asset prompt...")
        self._thread = self._thread_class("EnhancementThread")(
            project=project,
            asset=asset,
            project_root=self.main.project_root_edit.text(),
            provider=provider,
            model=self.main.prompt_model_edit.text().strip(),
            api_key=api_key,
        )
        self._thread.finished.connect(
            lambda text: self.on_enhance_finished(text, project, asset)
        )
        self._thread.error.connect(self.on_thread_error)
        self._thread.start()

    def on_enhance_finished(
        self, enhanced: str, project: ProjectSpec, asset: AssetSpec
    ) -> None:
        asset.enhanced_prompt = enhanced
        self.main.enhanced_prompt_edit.setPlainText(enhanced)
        store = ProjectStore(self.main.project_root_edit.text())
        store.save_asset(project, asset)
        known_assets = store.load_assets(project)
        packets = PromptPlanner().build_prompt_packets(
            project, asset, known_assets=known_assets
        )
        store.save_prompt_plan(project, asset, packets)
        self.refresh_asset_list(asset.slug)
        self.set_busy(False, "Enhanced prompt saved")
        self._thread = None

    def on_generate(self) -> None:
        try:
            project, asset = self.save_current_specs()
        except Exception as exc:
            QMessageBox.warning(self.main, "Generate Failed", str(exc))
            return

        provider = self.main.image_provider_combo.currentData()
        api_key = self.api_key_for(provider, "image")
        prompt_provider = self.main.prompt_provider_combo.currentData()
        prompt_api_key = self.api_key_for(prompt_provider, "prompt")
        preflight = self.build_generation_preflight(
            project,
            asset,
            image_api_key=api_key,
            prompt_api_key=prompt_api_key,
        )
        if preflight.status == PREFLIGHT_ERROR:
            self.main.status_label.setText(
                "Preflight needs: "
                + "; ".join(issue.message for issue in preflight.errors[:3])
            )
            return

        output_root = (
            Path(self.main.project_root_edit.text())
            / (project.slug or project.name)
            / "generated"
            / (asset.slug or asset.name)
        )
        self.main.preview_panel.clear()
        self.set_busy(True, "Generating asset...")
        self._thread = self._thread_class("ProjectGenerationThread")(
            project=project,
            asset=asset,
            project_root=self.main.project_root_edit.text(),
            output_root=str(output_root),
            provider=provider,
            model=self.main.image_model_edit.text().strip(),
            api_key=api_key,
            variants_per_packet=self.main.generation_variants_spin.value(),
            enhance_before_generate=self.main.enhance_before_generate_check.isChecked(),
            prompt_provider=prompt_provider,
            prompt_model=self.main.prompt_model_edit.text().strip(),
            prompt_api_key=prompt_api_key,
        )
        self._thread.progress.connect(self.main.status_label.setText)
        self._thread.finished.connect(self.on_generation_finished)
        self._thread.error.connect(self.on_thread_error)
        self._thread.start()

    def build_generation_preflight(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        image_api_key: str,
        prompt_api_key: str,
    ) -> GenerationPreflightReport:
        store = ProjectStore(self.main.project_root_edit.text())
        known_assets = store.load_assets(project)
        return build_generation_preflight(
            project=project,
            asset=asset,
            known_assets=known_assets,
            provider=self.main.image_provider_combo.currentData(),
            model=self.main.image_model_edit.text().strip(),
            api_key=image_api_key,
            prompt_provider=self.main.prompt_provider_combo.currentData(),
            prompt_model=self.main.prompt_model_edit.text().strip(),
            prompt_api_key=prompt_api_key,
            enhance_first=self.main.enhance_before_generate_check.isChecked(),
            variants_per_packet=self.main.generation_variants_spin.value(),
            model_suggestions=self._online_model_suggestions,
        )

    def on_generation_finished(self, result) -> None:
        try:
            store = ProjectStore(self.main.project_root_edit.text())
            project = store.load_project(result.project_slug)
            asset = store.load_asset(project, result.asset_slug)
            self.main.enhanced_prompt_edit.setPlainText(asset.enhanced_prompt)
        except Exception:
            pass
        self._last_output_dir = str(result.output_dir)
        self._last_gallery_path = str(result.gallery_path)
        self._last_project_gallery_path = self.write_project_gallery()
        max_variant_count = max(
            (output.variant_count for output in result.outputs), default=1
        )
        self.main.export_variant_spin.setMaximum(max(8, max_variant_count))
        for output in result.outputs:
            title = self.generation_output_title(
                stage_label=output.stage_label,
                stage_index=output.stage_index,
                variant_index=output.variant_index,
                layout_name=output.layout_name,
            )
            self.main.preview_panel.add_generation_output(
                output.raw_image,
                output.slices,
                title=title,
            )
        self.set_busy(False, f"Generated {len(result.outputs)} image(s)")
        self.refresh_asset_list(result.asset_slug)
        self._thread = None

    # ------------------------------------------------------------------
    # Export / galleries
    # ------------------------------------------------------------------
    def on_export_asset(self) -> None:
        try:
            project, asset = self.save_current_specs()
            variant_index = self.main.export_variant_spin.value() or None
            store = ProjectStore(self.main.project_root_edit.text())
            result = ProjectAssetExporter(store).export_saved_asset(
                project=project,
                asset=asset,
                variant_index=variant_index,
            )
            self._last_output_dir = str(result.output_dir)
            self._last_project_gallery_path = self.write_project_gallery(project)
            variant_label = f" from variant {variant_index}" if variant_index else ""
            self.main.status_label.setText(
                f"Exported {len(result.sprites)} sprite(s){variant_label} to {result.output_dir}"
            )
        except Exception as exc:
            QMessageBox.warning(self.main, "Export Failed", str(exc))

    def on_export_project(self) -> None:
        try:
            project, _asset = self.save_current_specs()
            store = ProjectStore(self.main.project_root_edit.text())
            result = ProjectAssetExporter(store).export_project(project=project)
            self._last_output_dir = str(result.output_dir)
            self._last_project_gallery_path = self.write_project_gallery(project)
            self.refresh_project_list(project.slug)
            skipped = f", skipped {len(result.skipped)}" if result.skipped else ""
            self.main.status_label.setText(
                f"Exported project pack with {len(result.assets)} asset(s){skipped} "
                f"to {result.output_dir}"
            )
        except Exception as exc:
            QMessageBox.warning(self.main, "Export Project Failed", str(exc))

    def on_open_project_gallery(self) -> None:
        try:
            project, _asset = self.save_current_specs()
            gallery_path = self.write_project_gallery(project)
            self._last_project_gallery_path = str(gallery_path)
            self.refresh_project_list(project.slug)
            self.main._open_local_path(gallery_path)
            self.main.status_label.setText(f"Opened project gallery: {gallery_path}")
        except Exception as exc:
            QMessageBox.warning(self.main, "Project Gallery Failed", str(exc))

    def write_project_gallery(self, project: ProjectSpec | None = None) -> str:
        store = ProjectStore(self.main.project_root_edit.text())
        if project is None:
            project = self._current_project or store.load_project(
                self.project_slug_from_fields()
            )
        gallery_path = ProjectGalleryWriter(store=store).write(project)
        return str(gallery_path)

    def on_thread_error(self, message: str) -> None:
        self.set_busy(False, f"Error: {message}")
        QMessageBox.warning(self.main, "spritegen", message)
        self._thread = None

    # ------------------------------------------------------------------
    # Build / apply specs
    # ------------------------------------------------------------------
    def save_current_specs(self) -> tuple[ProjectSpec, AssetSpec]:
        project = self.build_project_spec()
        asset = self.build_asset_spec()
        store = ProjectStore(self.main.project_root_edit.text())
        store.save_project(project)
        store.save_asset(project, asset)
        known_assets = store.load_assets(project)
        packets = PromptPlanner().build_prompt_packets(
            project, asset, known_assets=known_assets
        )
        store.save_prompt_plan(project, asset, packets)
        self._current_project = project
        return project, asset

    def build_project_spec(self) -> ProjectSpec:
        name = self.main.project_name_edit.text().strip()
        if not name:
            raise ValueError("Project name is required")
        asset_type = self.main.asset_type_edit.text().strip() or "asset"
        slug = slugify(name)
        project = ProjectSpec(
            name=name,
            summary=self.main.project_summary_edit.text().strip(),
            visual_style=self.main.style_edit.toPlainText().strip(),
            shared_context=self.main.context_edit.toPlainText().strip(),
            palette=self.palette_values(),
            negative_prompt=self.main.negative_prompt_edit.text().strip(),
            provider_defaults=ProviderDefaults(
                image_provider=self.main.image_provider_combo.currentData(),
                image_model=self.main.image_model_edit.text().strip(),
                prompt_provider=self.main.prompt_provider_combo.currentData(),
                prompt_model=self.main.prompt_model_edit.text().strip(),
            ),
            color_treatment=ColorTreatment(
                mode=self.main.color_mode_combo.currentData(),
                custom_prompt=self.main.color_prompt_edit.toPlainText().strip(),
            ),
            postprocess=PostProcessSettings(
                remove_background=self.main.remove_background_check.isChecked(),
            ),
        )
        existing_project = self.existing_project(slug)
        if existing_project:
            for layout in existing_project.custom_layouts.values():
                project.add_layout(layout)
            for existing_asset_type in existing_project.asset_types.values():
                project.add_asset_type(existing_asset_type)
        project.add_asset_type(
            AssetTypeSpec(
                name=asset_type,
                shared_prompt=self.main.asset_type_context_edit.text().strip(),
                evolution=EvolutionPlan(
                    count=self.main.evolutions_spin.value(),
                    labels=self.evolution_labels(),
                    shared_prompt=self.main.evolution_context_edit.text().strip(),
                ),
                default_layout=self.main.layout_combo.currentData(),
            )
        )
        return project

    def build_asset_spec(self) -> AssetSpec:
        name = self.main.asset_name_edit.text().strip()
        if not name:
            raise ValueError("Asset name is required")
        return AssetSpec(
            name=name,
            asset_type=self.main.asset_type_edit.text().strip() or "asset",
            description=self.main.asset_description_edit.toPlainText().strip(),
            details=self.main.asset_details_edit.toPlainText().strip(),
            enhanced_prompt=self.main.enhanced_prompt_edit.toPlainText().strip(),
            layout=self.main.layout_combo.currentData(),
        )

    def palette_values(self) -> list[str]:
        return [
            value.strip()
            for value in self.main.palette_edit.text().split(",")
            if value.strip()
        ]

    def evolution_labels(self) -> list[str]:
        return [
            value.strip()
            for value in self.main.evolution_labels_edit.text().split(",")
            if value.strip()
        ]

    def existing_project(self, project_slug: str) -> ProjectSpec | None:
        if self._current_project and self._current_project.slug == project_slug:
            return self._current_project
        store = ProjectStore(self.main.project_root_edit.text())
        path = store.project_path(project_slug)
        if not path.exists():
            return None
        try:
            return store.load_project(path)
        except Exception:
            return None

    def project_slug_from_fields(self) -> str:
        name = self.main.project_name_edit.text().strip()
        if self._current_project and self._current_project.name == name:
            return self._current_project.slug or slugify(name)
        return slugify(name) if name else ""

    def apply_project_spec(self, project: ProjectSpec) -> None:
        self._current_project = project
        self.main.project_name_edit.setText(project.name)
        self.main.project_summary_edit.setText(project.summary)
        self.main.style_edit.setPlainText(project.visual_style)
        self.main.context_edit.setPlainText(project.shared_context)
        self.main.palette_edit.setText(",".join(project.palette))
        self.main.negative_prompt_edit.setText(project.negative_prompt)
        self.set_combo_value(
            self.main.image_provider_combo, project.provider_defaults.image_provider
        )
        self.main.image_model_edit.setText(project.provider_defaults.image_model)
        self.set_combo_value(
            self.main.prompt_provider_combo, project.provider_defaults.prompt_provider
        )
        self.main.prompt_model_edit.setText(project.provider_defaults.prompt_model)
        self.set_combo_value(self.main.color_mode_combo, project.color_treatment.mode)
        self.main.color_prompt_edit.setPlainText(project.color_treatment.custom_prompt)
        self.main.remove_background_check.setChecked(
            project.postprocess.remove_background
        )
        self.refresh_layout_combo(project)
        if project.asset_types:
            self.apply_asset_type_spec(next(iter(project.asset_types.values())))
        self.main.update_provider_chip()
        self.main.update_project_pills()

    def apply_asset_type_spec(self, asset_type: AssetTypeSpec) -> None:
        self.main.asset_type_edit.setText(asset_type.name)
        self.main.asset_type_context_edit.setText(asset_type.shared_prompt)
        self.main.evolution_context_edit.setText(asset_type.evolution.shared_prompt)
        self.main.evolution_labels_edit.setText(", ".join(asset_type.evolution.labels))
        self.main.evolutions_spin.setValue(
            max(
                self.main.evolutions_spin.minimum(),
                min(self.main.evolutions_spin.maximum(), asset_type.evolution.count),
            )
        )
        self.set_combo_value(self.main.layout_combo, asset_type.default_layout)

    def apply_asset_spec(self, project: ProjectSpec, asset: AssetSpec) -> None:
        if asset.asset_type in project.asset_types:
            self.apply_asset_type_spec(project.asset_types[asset.asset_type])
        self.main.asset_type_edit.setText(asset.asset_type)
        self.main.asset_name_edit.setText(asset.name)
        self.main.asset_description_edit.setPlainText(asset.description)
        self.main.asset_details_edit.setPlainText(asset.details)
        self.main.enhanced_prompt_edit.setPlainText(asset.enhanced_prompt)
        if asset.layout:
            self.set_combo_value(self.main.layout_combo, asset.layout)
        self.main.update_project_pills()

    def set_combo_value(self, combo: QComboBox, value: str) -> None:
        if value is None:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def load_asset_preview(self, project: ProjectSpec, asset: AssetSpec) -> None:
        self.main.preview_panel.clear()
        store = ProjectStore(self.main.project_root_edit.text())
        output_dir = store.generated_dir(project.slug or slugify(project.name)) / (
            asset.slug or slugify(asset.name)
        )
        self._last_output_dir = str(output_dir)
        manifest_path = output_dir / "generation_manifest.json"
        gallery_path = output_dir / "asset_gallery.html"
        self._last_gallery_path = str(gallery_path) if gallery_path.exists() else ""
        if not manifest_path.exists():
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for output in manifest.get("outputs", []):
            if not isinstance(output, dict):
                continue
            raw_image = self.manifest_image_path(output.get("raw_image"), output_dir)
            slice_paths = [
                path
                for value in output.get("slices", [])
                if (path := self.manifest_image_path(value, output_dir)) is not None
            ]
            if raw_image is not None or slice_paths:
                title = self.generation_output_title(
                    stage_label=output.get("stage_label"),
                    stage_index=output.get("stage_index"),
                    variant_index=output.get("variant_index"),
                    layout_name=output.get("layout_name"),
                )
                self.main.preview_panel.add_generation_output(
                    raw_image, slice_paths, title=title
                )

    def manifest_image_path(self, value: object, base_dir: Path) -> Path | None:
        if not isinstance(value, str) or not value:
            return None
        path = Path(value)
        if not path.is_absolute():
            path = base_dir / path
        return path if path.exists() else None

    def generation_output_title(
        self,
        stage_label: object,
        stage_index: object,
        layout_name: object,
        variant_index: object = None,
    ) -> str:
        layout = str(layout_name) if layout_name else "layout"
        variant = f" / Variant {variant_index}" if variant_index else ""
        if stage_label:
            return f"{stage_label}{variant} ({layout})"
        if stage_index is not None:
            return f"Stage {stage_index}{variant} ({layout})"
        return f"Generated asset{variant} ({layout})"

    # ------------------------------------------------------------------
    # API keys / providers
    # ------------------------------------------------------------------
    def api_key_for(self, provider: str, purpose: str = "image") -> str:
        primary = (
            self.main.prompt_api_key_edit if purpose == "prompt" else self.main.image_api_key_edit
        )
        primary_key = primary.text().strip()
        if primary_key:
            return primary_key
        secondary = (
            self.main.image_api_key_edit if purpose == "prompt" else self.main.prompt_api_key_edit
        )
        secondary_provider = (
            self.main.image_provider_combo.currentData()
            if purpose == "prompt"
            else self.main.prompt_provider_combo.currentData()
        )
        secondary_key = secondary.text().strip()
        if secondary_provider == provider and secondary_key:
            return secondary_key
        configured = self.configured_api_key_for(provider)
        if configured:
            return configured
        return ""

    def configured_api_key_for(self, provider: str) -> str:
        configured = self._user_settings.api_key_for(provider)
        if configured:
            return configured
        if provider == "openai":
            return os.environ.get("OPENAI_API_KEY", "")
        if provider == "openrouter":
            return os.environ.get("OPENROUTER_API_KEY", "")
        return ""

    def provider_can_run(self, provider: str, api_key: str) -> bool:
        if provider in {"mock", "pollinations"}:
            return True
        if api_key:
            return True
        QMessageBox.warning(
            self.main,
            "API Key Required",
            f"Enter an API key or set {provider.upper()}_API_KEY in the environment.",
        )
        return False

    # ------------------------------------------------------------------
    # Busy / status
    # ------------------------------------------------------------------
    def set_busy(self, busy: bool, status: str) -> None:
        self.main.set_busy_state(busy)
        self.main.status_label.setText(status)
        if busy and hasattr(self.main, "run_summary_label"):
            self.main.run_summary_label.setText(status)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _thread_class(self, name: str):
        """Look up a thread class on the main_window module.

        This indirection lets tests monkeypatch
        ``spritegen.ui.main_window.ModelDiscoveryThread`` to substitute fakes.
        """
        import sys

        main_module = sys.modules.get("spritegen.ui.main_window")
        if main_module is not None:
            cls = getattr(main_module, name, None)
            if cls is not None:
                return cls
        # Fallback to the static import
        fallback = {
            "ModelDiscoveryThread": ModelDiscoveryThread,
            "ProjectGenerationThread": ProjectGenerationThread,
            "EnhancementThread": EnhancementThread,
            "ProjectEnhancementThread": ProjectEnhancementThread,
            "AssetTypeEnhancementThread": AssetTypeEnhancementThread,
        }
        return fallback[name]


def combined_model_suggestions_local(
    provider: str, role: str, online: list[ModelSuggestion]
) -> list[ModelSuggestion]:
    """Mirror of ``provider_models.combined_model_suggestions`` for the controller."""
    from ..provider_models import combined_model_suggestions

    return combined_model_suggestions(provider, role, online)
