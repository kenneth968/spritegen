"""Tests for project-aware game asset planning."""

from io import BytesIO

from spritegen.layouts import AssetLayout, get_layout
from spritegen.projects import (
    AssetSpec,
    AssetTypeSpec,
    ColorTreatment,
    EvolutionPlan,
    ProjectSpec,
    ProjectStore,
    PromptPlanner,
    apply_asset_type_enhancement,
    apply_project_enhancement,
)
from spritegen.enhancement import PromptEnhancer
from spritegen.project_generation import ProjectAssetGenerator
from spritegen.slicer import Slicer


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
    assert plan_path.exists()


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
    )
    asset = AssetSpec(
        name="Rook",
        asset_type="character",
        description="A rogue female assassin with silver daggers.",
    )

    packet = PromptPlanner().build_prompt_packets(project, asset, known_assets=[existing])[0]

    assert "Vera: An archer with a crescent hood" in packet.prompt
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
