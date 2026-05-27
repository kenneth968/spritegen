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


def test_main_window_applies_project_and_type_improvements(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.project_root_edit.setText(str(tmp_path / "projects"))
    project = window._build_project_spec()

    window._on_project_improved(
        {
            "summary": "Improved fungal defense project",
            "visual_style": "inked tactical sprites",
            "shared_context": "fungi defend the damp forest",
            "palette": ["#101010", "#E0E0E0"],
            "negative_prompt": "watermark",
            "color_prompt": "Use remappable value bands.",
        },
        project,
    )

    assert window.project_summary_edit.text() == "Improved fungal defense project"
    assert window.style_edit.toPlainText() == "inked tactical sprites"
    assert window.palette_edit.text() == "#101010,#E0E0E0"
    assert window.color_prompt_edit.toPlainText() == "Use remappable value bands."

    updated_project = window._build_project_spec()
    asset_type = updated_project.get_asset_type("tower")
    window._on_asset_type_improved(
        {
            "shared_prompt": "Round fungal tower silhouettes.",
            "evolution_shared_prompt": "Grow caps, spores, and glow each stage.",
            "evolution_labels": ["sprout", "bloom", "elder", "ancient"],
        },
        updated_project,
        asset_type,
    )

    assert window.asset_type_context_edit.text() == "Round fungal tower silhouettes."
    assert window.evolution_context_edit.text() == "Grow caps, spores, and glow each stage."
    assert window.evolution_labels_edit.text() == "sprout, bloom, elder, ancient"

    window.close()
    app.processEvents()
