"""Tests for project-aware game asset planning."""

from io import BytesIO

from spritegen.layouts import AssetLayout, get_layout
from spritegen.projects import (
    AssetSpec,
    AssetTypeSpec,
    EvolutionPlan,
    ProjectSpec,
    ProjectStore,
    PromptPlanner,
)
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
