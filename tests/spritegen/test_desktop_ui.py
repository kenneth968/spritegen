"""Smoke tests for the desktop project workflow."""

from __future__ import annotations

import json
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
    window.remove_background_check.setChecked(False)

    project, asset = window._save_current_specs()

    assert project.slug == "myceliumtd"
    assert asset.slug == "puffball"
    assert project.color_treatment.mode == "single_hue_value_map"
    assert project.postprocess.remove_background is False
    assert (tmp_path / "projects" / "myceliumtd" / "project.json").exists()
    assert (tmp_path / "projects" / "myceliumtd" / "assets" / "puffball.json").exists()

    window.close()
    app.processEvents()


def test_main_window_loads_saved_project_and_asset(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from spritegen.projects import (
        AssetSpec,
        AssetTypeSpec,
        ColorTreatment,
        EvolutionPlan,
        ProjectSpec,
        ProjectStore,
    )
    from spritegen.layouts import AssetLayout
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
    project.postprocess.remove_background = False
    project.add_layout(
        AssetLayout.grid(
            name="tower_cards",
            width=768,
            height=512,
            rows=2,
            columns=3,
            region_prefix="card",
        )
    )
    project.add_asset_type(
        AssetTypeSpec(
            name="tower",
            shared_prompt="Readable tower upgrades.",
            evolution=EvolutionPlan(count=3),
            default_layout="tower_cards",
        )
    )
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="Spore cloud tower.",
        details="Soft cap.",
        enhanced_prompt="Improved spore cloud prompt.",
        layout="tower_cards",
    )
    store.save_project(project)
    store.save_asset(project, asset)
    output_dir = store.generated_dir(project.slug) / asset.slug
    slice_dir = output_dir / "single"
    slice_dir.mkdir(parents=True)
    raw_path = output_dir / "single.png"
    idle_path = slice_dir / "single_idle.png"
    attack_path = slice_dir / "single_attack.png"
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(raw_path)
    Image.new("RGBA", (16, 16), (0, 255, 0, 255)).save(idle_path)
    Image.new("RGBA", (16, 16), (0, 0, 255, 255)).save(attack_path)
    (output_dir / "generation_manifest.json").write_text(
        json.dumps(
            {
                "outputs": [
                    {
                        "stage_index": None,
                        "stage_label": None,
                        "layout_name": "tower_cards",
                        "raw_image": "single.png",
                        "slices": [
                            "single/single_idle.png",
                            "single/single_attack.png",
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

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
    assert window.remove_background_check.isChecked() is False
    assert window.layout_combo.findData("tower_cards") >= 0
    assert window.layout_combo.currentData() == "tower_cards"

    asset_index = window.asset_combo.findData("puffball")
    assert asset_index >= 0
    window.asset_combo.setCurrentIndex(asset_index)
    window._on_load_asset()

    assert window.asset_name_edit.text() == "Puffball"
    assert window.enhanced_prompt_edit.toPlainText() == "Improved spore cloud prompt."
    assert window.preview_panel.image_paths == [raw_path, idle_path, attack_path]

    window.close()
    app.processEvents()


def test_preview_panel_displays_raw_and_sliced_outputs(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PIL import Image
    from PySide6.QtWidgets import QApplication, QLabel
    from spritegen.ui.main_window import PreviewPanel

    raw_path = tmp_path / "atlas.png"
    idle_path = tmp_path / "idle.png"
    attack_path = tmp_path / "attack.png"
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(raw_path)
    Image.new("RGBA", (16, 16), (0, 255, 0, 255)).save(idle_path)
    Image.new("RGBA", (16, 16), (0, 0, 255, 255)).save(attack_path)

    app = QApplication.instance() or QApplication([])
    panel = PreviewPanel()
    panel.add_generation_output(raw_path, [idle_path, attack_path], title="Idle stage")

    labels = {label.text() for label in panel.findChildren(QLabel)}
    assert "Idle stage" in labels
    assert "Raw atlas: atlas.png" in labels
    assert "Sliced sprites (2)" in labels
    assert panel.image_paths == [raw_path, idle_path, attack_path]

    panel.clear()

    assert panel.image_paths == []
    labels = {label.text() for label in panel.findChildren(QLabel)}
    assert "No generated assets yet." in labels

    panel.close()
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
