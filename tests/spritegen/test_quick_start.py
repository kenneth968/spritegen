from __future__ import annotations

import pytest


def test_build_quick_specs_creates_an_ordinary_single_sprite_project():
    from spritegen.projects import ProviderDefaults
    from spritegen.quick_start import QuickRequest, build_quick_specs

    project, asset = build_quick_specs(
        QuickRequest(description="a glowing mushroom tower", output_type="single_sprite"),
        provider_defaults=ProviderDefaults(
            image_provider="pollinations",
            image_model="flux",
            prompt_provider="pollinations",
            prompt_model="openai",
        ),
    )

    assert project.name == "Quick Start"
    assert project.slug == "quick-start"
    assert project.provider_defaults.image_provider == "pollinations"
    assert asset.name == "Glowing Mushroom Tower"
    assert asset.asset_type == "prop"
    assert asset.layout == "single_sprite"


def test_build_quick_specs_maps_evolution_chain_to_existing_prompt_packets():
    from spritegen.projects import PromptPlanner, ProviderDefaults
    from spritegen.quick_start import QuickRequest, build_quick_specs

    project, asset = build_quick_specs(
        QuickRequest(description="fungal flame tower", output_type="evolution_chain"),
        provider_defaults=ProviderDefaults(),
    )

    packets = PromptPlanner().build_prompt_packets(project, asset)

    assert asset.asset_type == "tower"
    assert asset.layout == "single_sprite"
    assert [packet.stage_label for packet in packets] == [
        "base",
        "upgraded",
        "advanced",
        "ultimate",
    ]


def test_build_quick_specs_maps_character_sheet_to_existing_layout():
    from spritegen.projects import ProviderDefaults
    from spritegen.quick_start import QuickRequest, build_quick_specs

    project, asset = build_quick_specs(
        QuickRequest(description="brave forest ranger", output_type="character_sheet"),
        provider_defaults=ProviderDefaults(),
    )

    assert asset.asset_type == "character"
    assert asset.layout == "character_full_plus_8_emotions"
    assert project.get_layout(asset.layout).name == "character_full_plus_8_emotions"


def test_build_quick_specs_makes_asset_slugs_unique_within_quick_start():
    from spritegen.projects import ProviderDefaults
    from spritegen.quick_start import QuickRequest, build_quick_specs

    request = QuickRequest(description="glowing mushroom tower", output_type="single_sprite")
    first_project, first_asset = build_quick_specs(
        request,
        provider_defaults=ProviderDefaults(),
    )
    _, second_asset = build_quick_specs(
        request,
        provider_defaults=ProviderDefaults(),
        existing_project=first_project,
        existing_assets=[first_asset],
    )

    assert second_asset.name == "Glowing Mushroom Tower 2"
    assert second_asset.slug == "glowing-mushroom-tower-2"


@pytest.mark.parametrize(
    ("description", "output_type", "message"),
    [
        ("", "single_sprite", "Describe the asset"),
        ("mushroom", "unknown", "Choose a supported output type"),
    ],
)
def test_build_quick_specs_rejects_incomplete_requests(
    description: str, output_type: str, message: str
):
    from spritegen.projects import ProviderDefaults
    from spritegen.quick_start import QuickRequest, QuickStartError, build_quick_specs

    with pytest.raises(QuickStartError, match=message):
        build_quick_specs(
            QuickRequest(description=description, output_type=output_type),
            provider_defaults=ProviderDefaults(),
        )
