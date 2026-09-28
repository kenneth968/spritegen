from __future__ import annotations

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


def _qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_quick_composer_defaults_and_emits_generate_intent():
    from spritegen.ui.widgets.quick_composer import QuickComposer

    _qapp()
    composer = QuickComposer()
    captured: list[tuple[str, str]] = []
    composer.generate_requested.connect(lambda description, output_type: captured.append((description, output_type)))

    assert composer.output_type_combo.currentData() == "single_sprite"
    assert composer.description_edit.placeholderText() == "Describe the asset you want to generate"
    assert composer.description_edit.maximumHeight() == 180

    composer.description_edit.setPlainText("glowing mushroom tower")
    composer.generate_btn.click()

    assert captured == [("glowing mushroom tower", "single_sprite")]


def test_quick_composer_renders_recovery_and_busy_states():
    from spritegen.ui.widgets.quick_composer import QuickComposer

    _qapp()
    composer = QuickComposer()

    composer.set_recovery("Paste an OpenAI key to continue.", "Paste key")
    assert composer.recovery_label.text() == "Paste an OpenAI key to continue."
    assert composer.recovery_btn.text() == "Paste key"
    assert composer.recovery_btn.isHidden() is False

    composer.set_busy(True)
    assert composer.generate_btn.isEnabled() is False
    assert composer.description_edit.isReadOnly() is True

    composer.clear_recovery()
    composer.set_busy(False)
    assert composer.recovery_label.isHidden() is True
    assert composer.recovery_btn.isHidden() is True
    assert composer.generate_btn.isEnabled() is True
    assert composer.description_edit.isReadOnly() is False


def test_workspace_discloses_output_actions_after_generation():
    from spritegen.ui.widgets.workspace_panel import WorkspacePanel

    _qapp()
    workspace = WorkspacePanel()

    assert workspace.export_sprites_btn.isHidden() is True
    assert workspace.open_gallery_btn.isHidden() is True
    assert workspace.open_folder_btn.isHidden() is True

    workspace.show_generated_output()

    assert workspace.export_sprites_btn.isHidden() is False
    assert workspace.open_gallery_btn.isHidden() is False
    assert workspace.open_folder_btn.isHidden() is False
