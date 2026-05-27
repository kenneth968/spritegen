"""Smoke tests for the desktop project workflow."""

from __future__ import annotations

import os

import pytest


def test_main_window_saves_project_plan(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window.project_name_edit.setText("MyceliumTD")
    window.asset_name_edit.setText("Puffball")
    window.color_mode_combo.setCurrentIndex(
        window.color_mode_combo.findData("single_hue_value_map")
    )
    window.color_prompt_edit.setPlainText("Use cap color as tint band 3.")

    project, asset = window._save_current_specs()

    assert project.slug == "myceliumtd"
    assert asset.slug == "puffball"
    assert project.color_treatment.mode == "single_hue_value_map"
    assert (tmp_path / "projects" / "myceliumtd" / "project.json").exists()
    assert (tmp_path / "projects" / "myceliumtd" / "assets" / "puffball.json").exists()

    window.close()
    app.processEvents()


def test_main_window_loads_saved_project_and_asset(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.projects import (
        AssetSpec,
        AssetTypeSpec,
        ColorTreatment,
        EvolutionPlan,
        ProjectSpec,
        ProjectStore,
    )
    from spritegen.ui.main_window import MainWindow

    store = ProjectStore(tmp_path / "projects")
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="inked grayscale sprites",
        shared_context="Forest floor fungi defend the colony.",
        palette=["#222222", "#BBBBBB"],
        color_treatment=ColorTreatment(mode="grayscale_value_map"),
    )
    project.add_asset_type(
        AssetTypeSpec(
            name="tower",
            shared_prompt="Readable tower upgrades.",
            evolution=EvolutionPlan(count=3),
            default_layout="four_stage_grid",
        )
    )
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="Spore cloud tower.",
        details="Soft cap.",
        enhanced_prompt="Improved spore cloud prompt.",
        layout="four_stage_grid",
    )
    store.save_project(project)
    store.save_asset(project, asset)

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._refresh_project_list()

    project_index = window.project_combo.findData("myceliumtd")
    assert project_index >= 0
    window.project_combo.setCurrentIndex(project_index)
    window._on_load_project()

    assert window.style_edit.toPlainText() == "inked grayscale sprites"
    assert window.color_mode_combo.currentData() == "grayscale_value_map"
    assert window.layout_combo.currentData() == "four_stage_grid"

    asset_index = window.asset_combo.findData("puffball")
    assert asset_index >= 0
    window.asset_combo.setCurrentIndex(asset_index)
    window._on_load_asset()

    assert window.asset_name_edit.text() == "Puffball"
    assert window.enhanced_prompt_edit.toPlainText() == "Improved spore cloud prompt."

    window.close()
    app.processEvents()
