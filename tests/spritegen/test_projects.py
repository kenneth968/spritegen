"""Tests for project-aware game asset planning."""

import json
from io import BytesIO

from spritegen.layouts import AssetLayout, get_layout
from spritegen.projects import (
    AssetSpec,
    AssetTypeSpec,
    ColorTreatment,
    EvolutionPlan,
    PostProcessSettings,
    ProjectSpec,
    ProjectStore,
    PromptPlanner,
    apply_asset_type_enhancement,
    apply_project_enhancement,
)
from spritegen.enhancement import PromptEnhancer
from spritegen.project_export import ProjectAssetExporter
from spritegen.project_generation import ProjectAssetGenerator
from spritegen.slicer import Slicer
from spritegen.workflow_presets import get_workflow_preset, list_workflow_presets


def test_character_emotion_layout_regions_are_exact():
    layout = get_layout("character_full_plus_8_emotions")

    assert layout.width == 1024
    assert layout.height == 1024
    assert len(layout.regions) == 9
    assert layout.regions[0].name == "full_body"
    assert layout.regions[0].width == 512
    assert layout.regions[0].height == 1024
    assert layout.regions[-1].name == "head_victory"
    assert layout.regions[-1].x == 768
    assert layout.regions[-1].y == 768
    assert layout.validate() == []


def test_hero_plus_grid_layout_regions_are_exact():
    layout = AssetLayout.hero_plus_grid(
        name="rogue_character_sheet",
        width=1024,
        height=1024,
        hero_width=512,
        grid_rows=4,
        grid_columns=2,
        hero_region_name="full_body",
        grid_region_prefix="head",
    )

    assert layout.width == 1024
    assert layout.height == 1024
    assert len(layout.regions) == 9
    assert layout.regions[0].name == "full_body"
    assert layout.regions[0].x == 0
    assert layout.regions[0].width == 512
    assert layout.regions[0].height == 1024
    assert layout.regions[1].name == "head_1"
    assert layout.regions[1].x == 512
    assert layout.regions[1].y == 0
    assert layout.regions[1].width == 256
    assert layout.regions[-1].name == "head_8"
    assert layout.regions[-1].x == 768
    assert layout.regions[-1].y == 768
    assert "left 512x1024 hero area" in layout.prompt_instructions
    assert "right 512x1024 area is a 2 by 4 grid" in layout.prompt_instructions
    assert layout.validate() == []


def test_workflow_presets_create_asset_type_specs():
    preset_keys = {preset.key for preset in list_workflow_presets()}
    assert {"tower_4_stage", "character_emotion_atlas", "ui_icon"} <= preset_keys

    tower = get_workflow_preset("tower_4_stage").to_asset_type()
    assert tower.name == "tower"
    assert tower.evolution.count == 4
    assert tower.evolution.labels == ["base", "upgraded", "advanced", "ultimate"]
    assert tower.default_layout == "single_sprite"

    character = get_workflow_preset("character_emotion_atlas").to_asset_type()
    assert character.name == "character"
    assert character.evolution.count == 1
    assert character.default_layout == "character_full_plus_8_emotions"


def test_project_layout_cli_adds_hero_plus_grid(monkeypatch, tmp_path, capsys):
    import sys
    from spritegen.cli import main

    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="clean cartoon sprites",
        shared_context="Friendly fungal towers.",
    )
    store = ProjectStore(tmp_path / "projects")
    store.save_project(project)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spritegen",
            "project",
            "--project-root",
            str(tmp_path / "projects"),
            "layout",
            "--project",
            "myceliumtd",
            "add-hero-grid",
            "--name",
            "Rogue Character Sheet",
            "--width",
            "1024",
            "--height",
            "1024",
            "--hero-width",
            "512",
            "--grid-rows",
            "4",
            "--grid-columns",
            "2",
            "--hero-region-name",
            "full body",
            "--grid-region-prefix",
            "head",
        ],
    )

    assert main() == 0

    output = capsys.readouterr().out
    saved = store.load_project("myceliumtd")
    layout = saved.custom_layouts["rogue_character_sheet"]
    assert "Saved layout: rogue_character_sheet" in output
    assert layout.regions[0].name == "full_body"
    assert layout.regions[-1].name == "head_8"


def test_project_store_round_trips_prompt_plan(tmp_path):
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="clean cartoon tower defense sprites with bold outlines",
        shared_context="A forest floor world of friendly fungal towers.",
        palette=["#8B4513", "#22AA66"],
        negative_prompt="photorealistic, watermark",
    )
    project.add_asset_type(
        AssetTypeSpec(
            name="tower",
            shared_prompt="Each tower has four readable upgrade stages.",
            evolution=EvolutionPlan(count=4, shared_prompt="Grow from sprout to ultimate."),
        )
    )
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="A mushroom that attacks with spore clouds.",
    )

    store = ProjectStore(tmp_path)
    project_path = store.save_project(project)
    loaded = store.load_project(project_path)
    store.save_asset(loaded, asset)
    known_assets = store.load_assets(loaded)

    packets = PromptPlanner().build_prompt_packets(loaded, asset, known_assets)
    plan_path = store.save_prompt_plan(loaded, asset, packets)

    assert loaded.slug == "myceliumtd"
    assert len(packets) == 4
    assert "A forest floor world" in packets[0].prompt
    assert "Evolution stage 1 of 4" in packets[0].prompt
    assert loaded.postprocess.remove_background is True
    assert plan_path.exists()


def test_project_custom_layout_round_trips_and_drives_prompt_plan(tmp_path):
    project = ProjectSpec(
        name="Portraits",
        summary="Character portrait set",
        visual_style="clean tactical RPG portraits",
        shared_context="Moonlit guild members.",
    )
    project.provider_defaults.image_provider = "mock"
    project.provider_defaults.image_model = "mock"
    layout = AssetLayout.grid(
        name="portrait_emotions",
        width=768,
        height=512,
        rows=2,
        columns=3,
        region_prefix="emotion",
    )
    layout.prompt_instructions = (
        "Create a 3 by 2 portrait emotion atlas with clean seams."
    )
    project.add_layout(layout)
    project.add_asset_type(
        AssetTypeSpec(
            name="portrait",
            shared_prompt="Same character, different expressions.",
            default_layout="portrait_emotions",
        )
    )
    asset = AssetSpec(
        name="Rook",
        asset_type="portrait",
        description="A rogue assassin portrait sheet.",
    )

    store = ProjectStore(tmp_path)
    loaded = store.load_project(store.save_project(project))
    packet = PromptPlanner().build_prompt_packets(loaded, asset)[0]
    result = ProjectAssetGenerator(ProjectStore(tmp_path / "generated-store")).generate(
        project=loaded,
        asset=asset,
        output_root=tmp_path / "generated",
    )

    assert loaded.get_layout("portrait_emotions").width == 768
    assert packet.layout_name == "portrait_emotions"
    assert "3 by 2 portrait emotion atlas" in packet.prompt
    assert "emotion_6" in packet.prompt
    assert len(result.outputs[0].slices) == 6


def test_prompt_uses_known_assets_for_universe_coherence():
    project = ProjectSpec(
        name="Dungeon portraits",
        summary="Character portrait set",
        visual_style="painted tactical RPG portraits",
        shared_context="All characters belong to the same moonlit thieves guild.",
    )
    project.add_asset_type(
        AssetTypeSpec(
            name="character",
            shared_prompt="Characters should share guild motifs.",
            default_layout="character_full_plus_8_emotions",
        )
    )
    existing = AssetSpec(
        name="Vera",
        asset_type="character",
        description="An archer with a crescent hood.",
        details="Moon-silver trim and smoky purple shadows.",
        layout="character_full_plus_8_emotions",
    )
    asset = AssetSpec(
        name="Rook",
        asset_type="character",
        description="A rogue female assassin with silver daggers.",
    )

    packet = PromptPlanner().build_prompt_packets(project, asset, known_assets=[existing])[0]

    assert "Vera [character]: An archer with a crescent hood" in packet.prompt
    assert "details: Moon-silver trim and smoky purple shadows" in packet.prompt
    assert packet.metadata["known_assets"][0]["slug"] == "vera"
    assert packet.metadata["known_assets"][0]["details"] == (
        "Moon-silver trim and smoky purple shadows."
    )
    assert packet.metadata["known_assets"][0]["layout"] == "character_full_plus_8_emotions"
    assert "character_full_plus_8_emotions" == packet.layout_name
    assert "left 512x1024" in packet.prompt
    assert "right 512x1024" in packet.prompt


def test_slicer_saves_named_layout_regions(tmp_path):
    from PIL import Image

    layout = AssetLayout.character_full_plus_8_emotions()
    image = Image.new("RGBA", (layout.width, layout.height), (255, 255, 255, 255))
    pixels = image.load()

    colors = [
        (255, 0, 0, 255),
        (0, 255, 0, 255),
        (0, 0, 255, 255),
        (255, 255, 0, 255),
        (255, 0, 255, 255),
        (0, 255, 255, 255),
        (128, 64, 255, 255),
        (255, 128, 64, 255),
        (64, 255, 128, 255),
    ]
    for region, color in zip(layout.regions, colors):
        for x in range(region.x + 8, region.x + region.width - 8):
            for y in range(region.y + 8, region.y + region.height - 8):
                pixels[x, y] = color

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    slicer = Slicer(output_dir=tmp_path)
    paths = slicer.slice_layout_image(buffer.getvalue(), layout, prefix="rogue")

    assert len(paths) == 9
    assert (tmp_path / "rogue_full_body.png").exists()
    assert (tmp_path / "rogue_head_victory.png").exists()
    assert (tmp_path / "rogue_layout_metadata.json").exists()


def test_mock_enhancer_adds_asset_context():
    brief = "\n".join(
        [
            "Raw asset idea: A mushroom tower that attacks with spore clouds",
            "Extra details: Soft white cap, area damage identity",
        ]
    )

    enhanced = PromptEnhancer().enhance(brief, provider="mock", model="mock")

    assert "spore clouds" in enhanced
    assert "Soft white cap" in enhanced
    assert "consistent palette" in enhanced


def test_project_generator_saves_manifest_and_slices(tmp_path):
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="clean cartoon tower defense sprites with bold outlines",
        shared_context="A forest floor world of friendly fungal towers.",
    )
    project.provider_defaults.image_provider = "mock"
    project.provider_defaults.image_model = "mock"
    project.add_asset_type(
        AssetTypeSpec(
            name="tower",
            shared_prompt="Each tower has readable upgrade stages.",
            evolution=EvolutionPlan(count=2, labels=["sprout", "ultimate"]),
        )
    )
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="A mushroom that attacks with spore clouds.",
    )

    result = ProjectAssetGenerator(ProjectStore(tmp_path / "projects")).generate(
        project=project,
        asset=asset,
        output_root=tmp_path / "generated",
    )

    assert result.manifest_path.exists()
    assert len(result.outputs) == 2
    assert result.outputs[0].raw_image.exists()
    assert result.outputs[0].slices
    assert result.outputs[0].slices[0].exists()


def test_project_exporter_copies_game_ready_slices(tmp_path):
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="clean cartoon tower defense sprites with bold outlines",
        shared_context="A forest floor world of friendly fungal towers.",
    )
    project.provider_defaults.image_provider = "mock"
    project.provider_defaults.image_model = "mock"
    project.add_asset_type(
        AssetTypeSpec(
            name="tower",
            shared_prompt="Each tower has readable upgrade stages.",
            evolution=EvolutionPlan(count=2, labels=["sprout", "ultimate"]),
        )
    )
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="A mushroom that attacks with spore clouds.",
    )
    store = ProjectStore(tmp_path / "projects")
    store.save_project(project)
    store.save_asset(project, asset)
    ProjectAssetGenerator(store).generate(project=project, asset=asset)

    result = ProjectAssetExporter(store).export_saved_asset(
        project=project,
        asset=asset,
        include_raw=True,
    )

    assert result.manifest_path.exists()
    assert len(result.sprites) == 2
    assert len(result.raw_images) == 2
    assert all(exported.path.exists() for exported in result.sprites)
    assert all(exported.path.parent.name == "sprites" for exported in result.sprites)
    export_manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert export_manifest["version"] == 1
    assert export_manifest["asset"]["slug"] == "puffball"
    assert export_manifest["sprites"][0]["file"].startswith("sprites/")


def test_project_generator_passes_session_api_key_to_image_generator(tmp_path, monkeypatch):
    seen = {}

    def fake_generate_raw_image(self, prompt, negative_prompt, width, height):
        seen["api_key"] = self.config.api_key
        from PIL import Image
        from io import BytesIO

        image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    monkeypatch.setattr(
        "spritegen.project_generation.SpriteGenerator.generate_raw_image",
        fake_generate_raw_image,
    )

    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="clean cartoon sprites",
        shared_context="Forest floor fungi.",
    )
    project.provider_defaults.image_provider = "openai"
    project.provider_defaults.image_model = "gpt-image-2"
    project.add_asset_type(AssetTypeSpec(name="tower", shared_prompt="Readable towers."))
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="Spore cloud tower.",
    )

    ProjectAssetGenerator(ProjectStore(tmp_path / "projects")).generate(
        project=project,
        asset=asset,
        output_root=tmp_path / "generated",
        api_key="session-image-key",
    )

    assert seen["api_key"] == "session-image-key"


def test_project_generator_passes_prior_generated_images_as_references(tmp_path, monkeypatch):
    from PIL import Image

    seen = {}

    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="clean cartoon sprites",
        shared_context="Forest floor fungi.",
    )
    project.provider_defaults.image_provider = "openrouter"
    project.provider_defaults.image_model = "google/test"
    project.add_asset_type(AssetTypeSpec(name="tower", shared_prompt="Readable towers."))
    existing = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="Spore cloud tower.",
    )
    next_asset = AssetSpec(
        name="Amanita",
        asset_type="tower",
        description="Poison mushroom tower.",
    )

    store = ProjectStore(tmp_path / "projects")
    store.save_project(project)
    store.save_asset(project, existing)
    previous_dir = store.generated_dir(project.slug) / existing.slug
    previous_dir.mkdir(parents=True)
    previous_raw = previous_dir / "single.png"
    Image.new("RGBA", (1024, 1024), (255, 0, 0, 255)).save(previous_raw)
    (previous_dir / "generation_manifest.json").write_text(
        json.dumps(
            {
                "outputs": [
                    {
                        "stage_index": None,
                        "stage_label": None,
                        "layout_name": "single_sprite",
                        "raw_image": str(previous_raw),
                        "slices": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def fake_generate_raw_image(
        self,
        prompt,
        negative_prompt,
        width,
        height,
        reference_images=None,
    ):
        seen["reference_images"] = reference_images
        image = Image.new("RGBA", (width, height), (255, 255, 255, 255))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    monkeypatch.setattr(
        "spritegen.project_generation.SpriteGenerator.generate_raw_image",
        fake_generate_raw_image,
    )

    result = ProjectAssetGenerator(store).generate(
        project=project,
        asset=next_asset,
        known_assets=[existing],
    )

    assert seen["reference_images"] == [previous_raw]
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["reference_images"] == [str(previous_raw)]
    assert manifest["outputs"][0]["reference_images"] == [str(previous_raw)]


def test_project_generator_can_keep_backgrounds(tmp_path):
    from PIL import Image

    project = ProjectSpec(
        name="TileSet",
        summary="Terrain tiles",
        visual_style="flat tile art",
        shared_context="Mossy stone dungeon tiles.",
        postprocess=PostProcessSettings(remove_background=False),
    )
    project.provider_defaults.image_provider = "mock"
    project.provider_defaults.image_model = "mock"
    project.add_asset_type(AssetTypeSpec(name="tile", shared_prompt="Keep full tile background."))
    asset = AssetSpec(
        name="Moss Stone",
        asset_type="tile",
        description="Square stone tile with moss.",
    )

    result = ProjectAssetGenerator(ProjectStore(tmp_path / "projects")).generate(
        project=project,
        asset=asset,
        output_root=tmp_path / "generated",
    )

    sprite_path = result.outputs[0].slices[0]
    with Image.open(sprite_path) as image:
        assert image.getpixel((0, 0))[3] == 255
    manifest = result.manifest_path.read_text(encoding="utf-8")
    assert '"remove_background": false' in manifest


def test_prompt_guides_and_color_treatment_feed_prompting():
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense game",
        visual_style="clean cartoon tower defense sprites with bold outlines",
        shared_context="A forest floor world of friendly fungal towers.",
        palette=["#111111", "#777777", "#EEEEEE"],
        negative_prompt="watermark",
        color_treatment=ColorTreatment(
            mode="grayscale_value_map",
            custom_prompt="Use four clear value bands for shader recoloring.",
        ),
    )
    project.add_asset_type(
        AssetTypeSpec(
            name="tower",
            shared_prompt="Each tower has readable upgrade stages.",
            default_layout="four_stage_grid",
        )
    )
    asset = AssetSpec(
        name="Puffball",
        asset_type="tower",
        description="A mushroom that attacks with spore clouds.",
    )

    planner = PromptPlanner()
    asset_type = project.get_asset_type("tower")
    brief = planner.build_enhancement_brief(project, asset_type, asset)
    system_prompt = planner.build_enhancement_system_prompt(project, asset_type, asset)
    packet = planner.build_prompt_packets(project, asset)[0]

    assert "grayscale value-map" in brief
    assert "four clear value bands" in packet.prompt
    assert "background-removed" in packet.prompt
    assert "Project Prompt Guide" in system_prompt
    assert "Four Stage Grid Layout Guide" in system_prompt
    assert packet.metadata["color_treatment"]["mode"] == "grayscale_value_map"


def test_enhancer_passes_system_prompt_to_openai_payload(monkeypatch):
    captured = {}

    def fake_post_json(self, url, payload, headers):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"output_text": "improved prompt"}

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(PromptEnhancer, "_post_json", fake_post_json)

    result = PromptEnhancer().enhance(
        "User brief",
        provider="openai",
        model="gpt-5.5",
        system_prompt="System guide",
    )

    assert result == "improved prompt"
    assert captured["payload"]["instructions"] == "System guide"
    assert captured["payload"]["input"] == "User brief"


def test_enhancer_passes_system_prompt_to_openrouter_messages(monkeypatch):
    captured = {}

    def fake_post_json(self, url, payload, headers):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "improved prompt"}}]}

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(PromptEnhancer, "_post_json", fake_post_json)

    result = PromptEnhancer().enhance(
        "User brief",
        provider="openrouter",
        model="openai/gpt-5.5",
        system_prompt="System guide",
    )

    assert result == "improved prompt"
    assert captured["payload"]["messages"][0] == {
        "role": "system",
        "content": "System guide",
    }
    assert captured["payload"]["messages"][1] == {
        "role": "user",
        "content": "User brief",
    }


def test_project_and_type_enhancement_apply_structured_results():
    project = ProjectSpec(
        name="MyceliumTD",
        summary="Fungal tower defense",
        visual_style="cartoon sprites",
        shared_context="forest floor",
        palette=["#111111"],
    )
    asset_type = AssetTypeSpec(
        name="tower",
        shared_prompt="tower upgrades",
        evolution=EvolutionPlan(count=3),
    )
    project.add_asset_type(asset_type)

    planner = PromptPlanner()
    project_brief = planner.build_project_enhancement_brief(project)
    type_brief = planner.build_asset_type_enhancement_brief(project, asset_type)

    apply_project_enhancement(
        project,
        {
            "summary": "Fungal tower-defense game with readable assets",
            "visual_style": "clean inked sprites with soft mushroom materials",
            "shared_context": "friendly fungi defend a damp forest floor",
            "palette": ["#222222", "#88AA66"],
            "negative_prompt": "watermark, text",
            "color_prompt": "Keep values easy to remap.",
        },
    )
    apply_asset_type_enhancement(
        asset_type,
        {
            "shared_prompt": "Each tower keeps a round fungal silhouette.",
            "evolution_shared_prompt": "Stages add caps, spores, and glow.",
            "evolution_labels": ["sprout", "bloom", "elder"],
        },
    )

    assert "strict JSON" in project_brief
    assert "strict JSON" in type_brief
    assert project.visual_style == "clean inked sprites with soft mushroom materials"
    assert project.palette == ["#222222", "#88AA66"]
    assert project.color_treatment.custom_prompt == "Keep values easy to remap."
    assert asset_type.shared_prompt == "Each tower keeps a round fungal silhouette."
    assert asset_type.evolution.labels == ["sprout", "bloom", "elder"]


def test_enhancer_extracts_json_from_markdown_fence(monkeypatch):
    def fake_enhance(self, brief, provider, model, api_key=None, system_prompt=None):
        return '```json\n{"summary": "Improved", "palette": ["#111111"]}\n```'

    monkeypatch.setattr(PromptEnhancer, "enhance", fake_enhance)

    result = PromptEnhancer().enhance_json(
        "brief",
        provider="openai",
        model="gpt-5.5",
        system_prompt="system",
    )

    assert result == {"summary": "Improved", "palette": ["#111111"]}
