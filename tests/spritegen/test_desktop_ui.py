"""Smoke tests for the desktop project workflow."""

from __future__ import annotations

import json
import os

import pytest


def test_main_window_saves_project_plan(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
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


def test_main_window_writes_and_opens_project_gallery(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    opened = {}

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    monkeypatch.setattr(
        window,
        "_open_local_path",
        lambda path: opened.setdefault("path", str(path)),
    )

    window._on_open_project_gallery()

    gallery_path = tmp_path / "projects" / "myceliumtd" / "project_gallery.html"
    assert gallery_path.exists()
    assert opened["path"] == str(gallery_path)
    assert window._last_project_gallery_path == str(gallery_path)
    assert "Opened project gallery" in window.status_label.text()

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
    from spritegen.user_settings import UserSettingsStore
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
    gallery_path = output_dir / "asset_gallery.html"
    gallery_path.write_text("<html>gallery</html>", encoding="utf-8")
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
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
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
    assert window._last_gallery_path == str(gallery_path)

    window.close()
    app.processEvents()


def test_main_window_exports_loaded_asset_slices(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PIL import Image
    from PySide6.QtWidgets import QApplication
    from spritegen.projects import AssetSpec, AssetTypeSpec, ProjectSpec, ProjectStore
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = ProjectStore(tmp_path / "projects")
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="inked sprites",
        shared_context="Forest floor fungi.",
    )
    project.add_asset_type(AssetTypeSpec(name="tower"))
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="Spore cloud tower.",
    )
    store.save_project(project)
    store.save_asset(project, asset)
    output_dir = store.generated_dir(project.slug) / asset.slug
    slice_dir = output_dir / "single"
    slice_dir.mkdir(parents=True)
    raw_path = output_dir / "single.png"
    sprite_path = slice_dir / "single_sprite.png"
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(raw_path)
    Image.new("RGBA", (16, 16), (0, 255, 0, 255)).save(sprite_path)
    (output_dir / "generation_manifest.json").write_text(
        json.dumps(
            {
                "project": project.to_dict(),
                "asset": asset.to_dict(),
                "outputs": [
                    {
                        "stage_index": None,
                        "stage_label": None,
                        "layout_name": "single_sprite",
                        "raw_image": "single.png",
                        "slices": ["single/single_sprite.png"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._refresh_project_list()
    window.project_combo.setCurrentIndex(window.project_combo.findData("myceliumtd"))
    window._on_load_project()
    window.asset_combo.setCurrentIndex(window.asset_combo.findData("puffball"))
    window._on_load_asset()

    window._on_export_asset()

    exported = tmp_path / "projects" / "myceliumtd" / "exports" / "puffball"
    assert (exported / "sprites" / "single_sprite.png").exists()
    assert (exported / "asset_export_manifest.json").exists()
    assert str(exported) in window.status_label.text()
    assert window._last_output_dir == str(exported)

    window.close()
    app.processEvents()


def test_main_window_exports_selected_variant(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.projects import AssetSpec, AssetTypeSpec, ProjectSpec, ProjectStore
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = ProjectStore(tmp_path / "projects")
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="inked sprites",
        shared_context="Forest floor fungi.",
    )
    project.add_asset_type(AssetTypeSpec(name="tower"))
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="Spore cloud tower.",
    )
    store.save_project(project)
    store.save_asset(project, asset)
    output_dir = store.generated_dir(project.slug) / asset.slug
    output_dir.mkdir(parents=True)
    variant_1 = output_dir / "single-v01_sprite.png"
    variant_2 = output_dir / "single-v02_sprite.png"
    variant_1.write_bytes(b"variant-1")
    variant_2.write_bytes(b"variant-2")
    (output_dir / "generation_manifest.json").write_text(
        json.dumps(
            {
                "project": project.to_dict(),
                "asset": asset.to_dict(),
                "outputs": [
                    {
                        "stage_index": None,
                        "stage_label": None,
                        "variant_index": 1,
                        "variant_count": 2,
                        "layout_name": "single_sprite",
                        "slices": [variant_1.name],
                    },
                    {
                        "stage_index": None,
                        "stage_label": None,
                        "variant_index": 2,
                        "variant_count": 2,
                        "layout_name": "single_sprite",
                        "slices": [variant_2.name],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._refresh_project_list()
    window.project_combo.setCurrentIndex(window.project_combo.findData("myceliumtd"))
    window._on_load_project()
    window.asset_combo.setCurrentIndex(window.asset_combo.findData("puffball"))
    window._on_load_asset()
    window.export_variant_spin.setValue(2)

    window._on_export_asset()

    exported = tmp_path / "projects" / "myceliumtd" / "exports" / "puffball"
    manifest = json.loads((exported / "asset_export_manifest.json").read_text(encoding="utf-8"))
    assert manifest["selected_variant"] == 2
    assert [sprite["variant_index"] for sprite in manifest["sprites"]] == [2]
    assert (exported / "sprites" / variant_2.name).exists()
    assert not (exported / "sprites" / variant_1.name).exists()
    assert "from variant 2" in window.status_label.text()

    window.close()
    app.processEvents()


def test_main_window_exports_project_pack(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    project_root = tmp_path / "projects"
    generated_dir = project_root / "myceliumtd" / "generated" / "puffball"
    generated_dir.mkdir(parents=True)
    sprite_path = generated_dir / "single_sprite.png"
    sprite_path.write_bytes(b"sprite")
    (generated_dir / "generation_manifest.json").write_text(
        json.dumps(
            {
                "outputs": [
                    {
                        "stage_index": None,
                        "stage_label": None,
                        "layout_name": "single_sprite",
                        "slices": [sprite_path.name],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(project_root))

    window._on_export_project()

    pack_dir = project_root / "myceliumtd" / "exports" / "_project_pack"
    assert (pack_dir / "project_export_manifest.json").exists()
    assert (pack_dir / "assets" / "tower" / "puffball" / "sprites" / sprite_path.name).exists()
    assert window._last_output_dir == str(pack_dir)
    assert "Exported project pack with 1 asset" in window.status_label.text()

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
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
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


def test_main_window_adds_project_grid_layout(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.projects import ProjectStore
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window.project_name_edit.setText("MyceliumTD")
    window.asset_type_edit.setText("tower")
    window.layout_name_edit.setText("Tower Contact Sheet")
    window.layout_width_spin.setValue(1536)
    window.layout_height_spin.setValue(1024)
    window.layout_rows_spin.setValue(2)
    window.layout_columns_spin.setValue(3)
    window.layout_region_prefix_edit.setText("tower pose")
    window.layout_prompt_edit.setPlainText("Create six clean tower pose cells with hard seams.")

    window._on_add_grid_layout()

    assert window.layout_combo.currentData() == "tower_contact_sheet"
    assert "Saved layout tower_contact_sheet" in window.status_label.text()

    project = ProjectStore(tmp_path / "projects").load_project("myceliumtd")
    layout = project.custom_layouts["tower_contact_sheet"]
    assert layout.width == 1536
    assert layout.height == 1024
    assert len(layout.regions) == 6
    assert layout.regions[0].name == "tower_pose_1"
    assert layout.regions[-1].x == 1024
    assert layout.regions[-1].y == 512
    assert layout.prompt_instructions == "Create six clean tower pose cells with hard seams."
    assert project.asset_types["tower"].default_layout == "tower_contact_sheet"

    window.asset_name_edit.setText("Puffball Contact")
    _project, asset = window._save_current_specs()
    assert asset.layout == "tower_contact_sheet"

    window.close()
    app.processEvents()


def test_main_window_adds_project_hero_grid_layout(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.projects import ProjectStore
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window.project_name_edit.setText("MyceliumTD")
    window.asset_type_edit.setText("character")
    window.layout_name_edit.setText("Rogue Character Sheet")
    window.layout_width_spin.setValue(1024)
    window.layout_height_spin.setValue(1024)
    window.hero_width_spin.setValue(512)
    window.layout_rows_spin.setValue(4)
    window.layout_columns_spin.setValue(2)
    window.layout_region_prefix_edit.setText("head")
    window.hero_region_name_edit.setText("full body")

    window._on_add_hero_grid_layout()

    assert window.layout_combo.currentData() == "rogue_character_sheet"
    assert "Saved layout rogue_character_sheet" in window.status_label.text()

    project = ProjectStore(tmp_path / "projects").load_project("myceliumtd")
    layout = project.custom_layouts["rogue_character_sheet"]
    assert layout.width == 1024
    assert layout.height == 1024
    assert len(layout.regions) == 9
    assert layout.regions[0].name == "full_body"
    assert layout.regions[0].width == 512
    assert layout.regions[-1].name == "head_8"
    assert layout.regions[-1].x == 768
    assert layout.regions[-1].y == 768
    assert project.asset_types["character"].default_layout == "rogue_character_sheet"

    window.close()
    app.processEvents()


def test_main_window_applies_character_workflow_preset(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    index = window.workflow_preset_combo.findData("character_emotion_atlas")
    assert index >= 0
    window.workflow_preset_combo.setCurrentIndex(index)

    window._on_apply_workflow_preset()

    assert window.asset_type_edit.text() == "character"
    assert window.evolutions_spin.value() == 1
    assert window.layout_combo.currentData() == "character_full_plus_8_emotions"
    assert "same character identity" in window.asset_type_context_edit.text().lower()
    assert "Applied workflow preset" in window.status_label.text()

    window.close()
    app.processEvents()


def test_main_window_creates_project_starter(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.projects import ProjectStore
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    index = window.project_starter_combo.findData("mycelium_td")
    assert index >= 0
    window.project_starter_combo.setCurrentIndex(index)

    window._on_apply_project_starter()

    assert window.project_name_edit.text() == "MyceliumTD"
    assert window.asset_name_edit.text() == "Puffball"
    assert window.asset_type_edit.text() == "tower"
    assert window.evolutions_spin.value() == 4
    assert window.color_mode_combo.currentData() == "limited_palette"
    assert "Created starter MyceliumTD / Puffball" in window.status_label.text()

    store = ProjectStore(tmp_path / "projects")
    project = store.load_project("myceliumtd")
    asset = store.load_asset(project, "puffball")
    plan_path = tmp_path / "projects" / "myceliumtd" / "prompt_plans" / "puffball.json"

    assert project.get_asset_type("tower").evolution.labels == [
        "base",
        "upgraded",
        "advanced",
        "ultimate",
    ]
    assert asset.description == "A mushroom tower that attacks by releasing spore clouds."
    assert plan_path.exists()

    window.close()
    app.processEvents()


def test_main_window_labels_generation_variants(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))

    window.generation_variants_spin.setValue(3)

    assert window.generation_variants_spin.value() == 3
    assert (
        window._generation_output_title(
            stage_label="sprout",
            stage_index=1,
            variant_index=2,
            layout_name="single_sprite",
        )
        == "sprout / Variant 2 (single_sprite)"
    )

    window.close()
    app.processEvents()


def test_main_window_previews_prompt_plan_with_prior_assets(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.projects import AssetSpec, AssetTypeSpec, ProjectSpec, ProjectStore
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = ProjectStore(tmp_path / "projects")
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="inked mushroom tower sprites",
        shared_context="Friendly fungi defend a damp forest floor.",
    )
    project.add_asset_type(
        AssetTypeSpec(
            name="tower",
            shared_prompt="All towers use rounded silhouettes and mossy materials.",
        )
    )
    existing = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="Spore cloud tower.",
        details="White cap, teal spores, soft circular base.",
        enhanced_prompt="rounded puffball tower with teal spore puffs",
        layout="single_sprite",
    )
    store.save_project(project)
    store.save_asset(project, existing)

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window._refresh_project_list()
    window.project_combo.setCurrentIndex(window.project_combo.findData("myceliumtd"))
    window._on_load_project()
    window.asset_name_edit.setText("Amanita")
    window.asset_description_edit.setPlainText("Poison mushroom tower.")
    window.asset_details_edit.setPlainText("Red cap, warning spots, venom aura.")

    window._on_preview_prompts()

    preview = window.prompt_preview_edit.toPlainText()
    assert "Puffball [tower]: rounded puffball tower with teal spore puffs" in preview
    assert "details: White cap, teal spores, soft circular base." in preview
    assert "Poison mushroom tower." in preview
    assert "Previewed" in window.status_label.text()
    assert (
        tmp_path
        / "projects"
        / "myceliumtd"
        / "prompt_plans"
        / "amanita.json"
    ).exists()

    window.close()
    app.processEvents()


def test_main_window_saves_local_provider_setup(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettings, UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    settings_store = UserSettingsStore(tmp_path / "settings.json")
    settings_store.save(
        UserSettings(
            image_provider="openrouter",
            image_model="google/gemini-3.1-flash-image-preview",
            prompt_provider="openai",
            prompt_model="gpt-5.5",
            api_keys={
                "openrouter": "saved-openrouter-key",
                "openai": "saved-openai-key",
            },
        )
    )

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=settings_store)

    assert window.image_provider_combo.currentData() == "openrouter"
    assert window.prompt_provider_combo.currentData() == "openai"
    assert window.image_model_edit.text() == "google/gemini-3.1-flash-image-preview"
    assert window.prompt_model_edit.text() == "gpt-5.5"
    assert window.image_api_key_edit.text() == "saved-openrouter-key"
    assert window.prompt_api_key_edit.text() == "saved-openai-key"
    assert window._api_key_for("openrouter", "image") == "saved-openrouter-key"
    assert window._api_key_for("openai", "prompt") == "saved-openai-key"

    window.image_model_edit.setText("openrouter/image-model")
    window.prompt_model_edit.setText("openai/prompt-model")
    window.image_api_key_edit.setText("new-openrouter-key")
    window.prompt_api_key_edit.setText("new-openai-key")
    window._on_save_provider_settings()

    saved = settings_store.load()
    assert saved.image_provider == "openrouter"
    assert saved.image_model == "openrouter/image-model"
    assert saved.prompt_provider == "openai"
    assert saved.prompt_model == "openai/prompt-model"
    assert saved.api_key_for("openrouter") == "new-openrouter-key"
    assert saved.api_key_for("openai") == "new-openai-key"
    assert "Saved local provider setup" in window.status_label.text()

    window._on_clear_saved_keys()
    assert settings_store.load().api_keys == {}
    assert window.image_api_key_edit.text() == ""
    assert window.prompt_api_key_edit.text() == ""

    window.close()
    app.processEvents()


def test_main_window_model_suggestions_are_editable(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))

    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._on_image_provider_changed()
    assert window.image_model_suggestions.count() >= 2
    assert window.image_model_edit.text() == "google/gemini-3.1-flash-image-preview"

    image_index = window.image_model_suggestions.findData("openai/gpt-5.4-image-2")
    assert image_index >= 0
    window.image_model_suggestions.setCurrentIndex(image_index)
    window._apply_model_suggestion("image")
    assert window.image_model_edit.text() == "openai/gpt-5.4-image-2"

    window.image_model_edit.setText("custom/openrouter-image-model")
    assert window.image_model_edit.text() == "custom/openrouter-image-model"

    window._set_combo_value(window.prompt_provider_combo, "openrouter")
    window._on_prompt_provider_changed()
    assert window.prompt_model_edit.text() == "openai/gpt-5.5"
    prompt_index = window.prompt_model_suggestions.findData("minimax/minimax-m2.7")
    assert prompt_index >= 0
    window.prompt_model_suggestions.setCurrentIndex(prompt_index)
    window._apply_model_suggestion("prompt")
    assert window.prompt_model_edit.text() == "minimax/minimax-m2.7"

    window.close()
    app.processEvents()


def test_main_window_refreshes_online_model_suggestions_without_overwriting_text(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.provider_models import IMAGE_ROLE, PROMPT_ROLE, ModelSuggestion
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._set_combo_value(window.prompt_provider_combo, "openrouter")
    window._on_image_provider_changed()
    window._on_prompt_provider_changed()
    window.image_model_edit.setText("custom/image-model")
    window.prompt_model_edit.setText("custom/prompt-model")

    window._on_model_discovery_finished(
        {
            "suggestions": {
                (IMAGE_ROLE, "openrouter"): [
                    ModelSuggestion(
                        provider="openrouter",
                        role=IMAGE_ROLE,
                        model="live/image-model",
                        label="Live Image",
                    )
                ],
                (PROMPT_ROLE, "openrouter"): [
                    ModelSuggestion(
                        provider="openrouter",
                        role=PROMPT_ROLE,
                        model="live/prompt-model",
                        label="Live Prompt",
                    )
                ],
            },
            "errors": [],
        }
    )

    assert window.image_model_suggestions.findData("live/image-model") >= 0
    assert window.prompt_model_suggestions.findData("live/prompt-model") >= 0
    assert window.image_model_edit.text() == "custom/image-model"
    assert window.prompt_model_edit.text() == "custom/prompt-model"
    assert "Loaded 2 online model suggestion" in window.status_label.text()

    window.close()
    app.processEvents()


def test_main_window_checks_provider_setup_without_network(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._set_combo_value(window.prompt_provider_combo, "openai")
    window.image_api_key_edit.clear()
    window.prompt_api_key_edit.clear()

    window._on_check_provider_setup()

    assert "OpenRouter image key" in window.status_label.text()
    assert "OpenAI prompt key" in window.status_label.text()

    window.image_api_key_edit.setText("openrouter-key")
    window.prompt_api_key_edit.setText("openai-key")
    window._on_check_provider_setup()

    assert window.status_label.text() == "Provider setup ready: image OpenRouter / prompt OpenAI"

    window.close()
    app.processEvents()


def test_main_window_saves_shared_provider_key_once(tmp_path, monkeypatch):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from PySide6.QtWidgets import QApplication
    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    settings_store = UserSettingsStore(tmp_path / "settings.json")
    app = QApplication.instance() or QApplication([])
    window = MainWindow(settings_store=settings_store)
    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._set_combo_value(window.prompt_provider_combo, "openrouter")
    window.image_api_key_edit.setText("shared-openrouter-key")
    window.prompt_api_key_edit.clear()

    window._on_save_provider_settings()

    assert settings_store.load().api_key_for("openrouter") == "shared-openrouter-key"

    window.close()
    app.processEvents()
