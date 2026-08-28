from __future__ import annotations

import json
import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


def _qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_quick_preflight_uses_quick_generation_options(tmp_path):
    from PySide6.QtWidgets import QApplication

    from spritegen.quick_start import QuickRequest, build_quick_specs
    from spritegen.projects import ProviderDefaults
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.enhance_before_generate_check.setChecked(True)
    window.generation_variants_spin.setValue(3)
    window.shared_provider_setup_check.setChecked(False)
    window._set_combo_value(window.prompt_provider_combo, "openai")
    window._on_prompt_provider_changed()
    project, asset = build_quick_specs(
        QuickRequest("glowing mushroom tower"),
        provider_defaults=ProviderDefaults(),
    )

    report = window.controller.build_generation_preflight(
        project,
        asset,
        image_api_key="",
        prompt_api_key="",
        quick_mode=True,
    )

    assert report.enhance_first is False
    assert report.variants_per_packet == 1
    assert report.ready is True
    window.close()
    QApplication.processEvents()


def test_switching_to_quick_preserves_busy_state(tmp_path):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window._set_app_mode("advanced")
    window.controller.set_busy(True, "Generating asset...")

    window._set_app_mode("quick")

    assert window.quick_composer.description_edit.isReadOnly() is True
    assert window.quick_composer.generate_btn.isEnabled() is False
    window.controller.set_busy(False, "Ready")
    window.close()
    QApplication.processEvents()


@pytest.mark.parametrize("provider", ["openai", "openrouter"])
def test_missing_key_recovery_focuses_the_selected_provider_key_field(
    tmp_path, monkeypatch, provider
):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.show()
    QApplication.processEvents()
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._set_combo_value(window.image_provider_combo, provider)
    window._on_image_provider_changed()
    window.quick_composer.description_edit.setPlainText("glowing mushroom tower")

    window.quick_composer.generate_btn.click()
    assert window.quick_composer.recovery_btn.text() == "Paste key"

    window.quick_composer.recovery_btn.click()
    QApplication.processEvents()

    assert window.settings_drawer.isHidden() is False
    assert window.image_api_key_edit.hasFocus() is True
    window.close()
    QApplication.processEvents()


def test_quick_retry_reuses_same_asset_after_generation_error(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui import main_window as main_window_mod
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    monkeypatch.setattr(main_window_mod.ProjectGenerationThread, "start", lambda self: None)
    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window.quick_composer.description_edit.setPlainText("glowing mushroom tower")
    window.quick_composer.generate_btn.click()
    first_thread = window.controller._thread

    window._set_app_mode("advanced")
    window.controller.on_thread_error("provider failed after preflight")
    assert window.quick_composer.recovery_label.isHidden() is False
    window.quick_composer.recovery_btn.click()

    retry_thread = window.controller._thread
    assert retry_thread is not None
    assert retry_thread.asset.slug == first_thread.asset.slug
    window.close()
    QApplication.processEvents()


def test_malformed_quick_start_records_are_recovered_inline(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from spritegen.projects import ProjectStore
    from spritegen.ui import main_window as main_window_mod
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    root = tmp_path / "projects"
    quick_dir = root / "quick-start"
    (quick_dir / "assets").mkdir(parents=True)
    (quick_dir / "project.json").write_text("not json", encoding="utf-8")
    (quick_dir / "assets" / "old.json").write_text("not json", encoding="utf-8")
    monkeypatch.setattr(main_window_mod.ProjectGenerationThread, "start", lambda self: None)

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(root))
    window.quick_composer.description_edit.setPlainText("glowing mushroom tower")
    window.quick_composer.generate_btn.click()

    assert window.controller._thread is not None
    assert window.quick_composer.recovery_label.isHidden() is True
    assert ProjectStore(root).load_project("quick-start").name == "Quick Start"
    window.close()
    QApplication.processEvents()


def test_advanced_thread_error_uses_job_origin_after_switching_to_quick(
    tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui import controller as controller_mod
    from spritegen.ui import main_window as main_window_mod
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    monkeypatch.setattr(main_window_mod.ProjectGenerationThread, "start", lambda self: None)
    warnings: list[tuple] = []
    monkeypatch.setattr(
        controller_mod.QMessageBox,
        "warning",
        lambda *args: warnings.append(args),
    )

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._set_app_mode("advanced")
    project, asset = window.controller.save_current_specs()
    window.controller._start_generation(project, asset, quick_mode=False)
    window._set_app_mode("quick")

    window.controller.on_thread_error("advanced generation failed")

    assert warnings
    assert window.quick_composer.recovery_label.isHidden() is True
    window.close()
    QApplication.processEvents()


def test_missing_saved_provider_key_falls_back_to_pollinations(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from spritegen.provider_models import IMAGE_ROLE, PROMPT_ROLE, default_model
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettings, UserSettingsStore

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings_store = UserSettingsStore(tmp_path / "settings.json")
    settings_store.save(
        UserSettings(
            image_provider="openai",
            image_model="gpt-image-2",
            prompt_provider="openrouter",
            prompt_model="openai/gpt-5.5",
            shared_provider_setup=False,
        )
    )

    _qapp()
    window = MainWindow(settings_store=settings_store)

    assert window.image_provider_combo.currentData() == "pollinations"
    assert window.prompt_provider_combo.currentData() == "pollinations"
    assert window.image_model_edit.text() == default_model("pollinations", IMAGE_ROLE)
    assert window.prompt_model_edit.text() == default_model("pollinations", PROMPT_ROLE)
    window.close()
    QApplication.processEvents()


def test_new_asset_hides_stale_output_actions(tmp_path):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.workspace_panel.show_generated_output()
    assert window.workspace_panel.export_sprites_btn.isHidden() is False

    window._on_new_asset()

    assert window.workspace_panel.export_sprites_btn.isHidden() is True
    assert window.workspace_panel.open_gallery_btn.isHidden() is True
    assert window.workspace_panel.open_folder_btn.isHidden() is True
    window.close()
    QApplication.processEvents()


def test_quick_run_resets_composer_when_mode_changes_before_completion(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from spritegen.project_generation import ProjectGenerationResult
    from spritegen.ui import main_window as main_window_mod
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    started = {"value": False}

    def fake_start(self):
        started["value"] = True

    monkeypatch.setattr(main_window_mod.ProjectGenerationThread, "start", fake_start)

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window.quick_composer.description_edit.setPlainText("glowing mushroom tower")
    window.quick_composer.generate_btn.click()
    assert started["value"] is True
    assert window.quick_composer.generate_btn.isEnabled() is False

    window.provider_bar.mode_button.click()
    result = ProjectGenerationResult(
        project_slug="quick-start",
        asset_slug="glowing-mushroom-tower",
        output_dir=tmp_path / "projects" / "quick-start" / "generated" / "glowing-mushroom-tower",
        manifest_path=tmp_path / "manifest.json",
        gallery_path=tmp_path / "gallery.html",
        outputs=[],
    )
    window._on_generation_finished(result)

    assert window.quick_composer.generate_btn.isEnabled() is True
    assert window.quick_composer.description_edit.isReadOnly() is False
    window.close()
    QApplication.processEvents()


def test_advanced_run_releases_quick_composer_after_switching_modes(
    tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QApplication

    from spritegen.project_generation import ProjectGenerationResult
    from spritegen.ui import main_window as main_window_mod
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    monkeypatch.setattr(main_window_mod.ProjectGenerationThread, "start", lambda self: None)

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._set_app_mode("advanced")
    project, asset = window.controller.save_current_specs()
    window.controller._start_generation(project, asset, quick_mode=False)

    window._set_app_mode("quick")
    assert window.quick_composer.generate_btn.isEnabled() is False

    result = ProjectGenerationResult(
        project_slug=project.slug,
        asset_slug=asset.slug,
        output_dir=tmp_path / "projects" / project.slug / "generated" / asset.slug,
        manifest_path=tmp_path / "manifest.json",
        gallery_path=tmp_path / "gallery.html",
        outputs=[],
    )
    window._on_generation_finished(result)

    assert window.quick_composer.generate_btn.isEnabled() is True
    assert window.quick_composer.description_edit.isReadOnly() is False
    window.close()
    QApplication.processEvents()


@pytest.mark.parametrize(
    "raw_settings",
    [
        "not json",
        json.dumps({"version": 999}),
        json.dumps({"version": 3, "api_keys": []}),
    ],
)
def test_invalid_saved_settings_use_first_run_provider_repair(
    tmp_path, monkeypatch, raw_settings
):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings_store = UserSettingsStore(tmp_path / "settings.json")
    settings_store.path.write_text(raw_settings, encoding="utf-8")

    _qapp()
    window = MainWindow(settings_store=settings_store)

    assert window.image_provider_combo.currentData() == "pollinations"
    assert settings_store.load().image_provider == "pollinations"
    window.close()
    QApplication.processEvents()


def test_loading_saved_asset_with_manifest_reenables_output_actions(tmp_path):
    from PySide6.QtWidgets import QApplication

    from spritegen.projects import AssetSpec, ProjectSpec, ProjectStore
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    store = ProjectStore(tmp_path / "projects")
    project = ProjectSpec(
        name="My Game",
        slug="my-game",
        summary="A small game.",
        visual_style="Readable sprites.",
        shared_context="",
    )
    asset = AssetSpec(
        name="Puffball",
        slug="puffball",
        asset_type="prop",
        description="A puffball sprite.",
        layout="single_sprite",
    )
    store.save_project(project)
    store.save_asset(project, asset)
    output_dir = store.generated_dir(project.slug) / asset.slug
    output_dir.mkdir(parents=True)
    (output_dir / "generation_manifest.json").write_text("{}", encoding="utf-8")

    _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._refresh_project_list()
    window.project_combo.setCurrentIndex(window.project_combo.findData(project.slug))
    window._on_load_project()
    window.asset_combo.setCurrentIndex(window.asset_combo.findData(asset.slug))
    window._on_load_asset()

    assert window.export_sprites_btn.isHidden() is False
    assert window.open_gallery_btn.isHidden() is False
    assert window.open_folder_btn.isHidden() is False
    window.close()
    QApplication.processEvents()


def test_project_root_editing_finished_persists_without_provider_save(tmp_path):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    _qapp()
    settings_store = UserSettingsStore(tmp_path / "settings.json")
    window = MainWindow(settings_store=settings_store)
    chosen_root = tmp_path / "chosen-projects"
    window.project_root_edit.setText(str(chosen_root))
    window.project_root_edit.editingFinished.emit()

    assert settings_store.load().project_root == str(chosen_root.resolve())
    window.close()
    QApplication.processEvents()


def test_browsing_project_root_persists_the_selected_folder(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from spritegen.ui import main_window as main_window_mod
    from spritegen.ui.main_window import MainWindow
    from spritegen.user_settings import UserSettingsStore

    _qapp()
    settings_store = UserSettingsStore(tmp_path / "settings.json")
    window = MainWindow(settings_store=settings_store)
    chosen_root = tmp_path / "browsed-projects"
    monkeypatch.setattr(
        main_window_mod.QFileDialog,
        "getExistingDirectory",
        lambda *args: str(chosen_root),
    )

    window._browse_project_root()

    assert settings_store.load().project_root == str(chosen_root.resolve())
    window.close()
    QApplication.processEvents()
