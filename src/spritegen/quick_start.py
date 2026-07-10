from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from .projects import AssetSpec, ProjectSpec, ProviderDefaults, slugify
from .workflow_presets import WorkflowPreset, get_workflow_preset


QUICK_START_NAME = "Quick Start"
QUICK_START_SLUG = "quick-start"
QUICK_OUTPUT_PRESETS = {
    "single_sprite": "single_prop",
    "evolution_chain": "tower_4_stage",
    "character_sheet": "character_emotion_atlas",
}
_NAME_STOP_WORDS = frozenset({"a", "an", "and", "for", "in", "of", "on", "the", "to", "with"})


@dataclass(frozen=True, slots=True)
class QuickRequest:
    description: str
    output_type: str = "single_sprite"


@dataclass(frozen=True, slots=True)
class QuickStartError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


def build_quick_specs(
    request: QuickRequest,
    *,
    provider_defaults: ProviderDefaults,
    existing_project: ProjectSpec | None = None,
    existing_assets: Sequence[AssetSpec] = (),
) -> tuple[ProjectSpec, AssetSpec]:
    description = request.description.strip()
    if not description:
        raise QuickStartError("Describe the asset before generating it.")
    preset = _preset_for_output_type(request.output_type)
    project = existing_project or ProjectSpec(
        name=QUICK_START_NAME,
        slug=QUICK_START_SLUG,
        summary="Fast, one-asset game-art generation.",
        visual_style="Readable game-ready sprite art.",
        shared_context="",
        provider_defaults=provider_defaults,
    )
    project.provider_defaults = provider_defaults
    asset_type = project.asset_types.get(preset.asset_type)
    if asset_type is None:
        asset_type = preset.to_asset_type()
        project.add_asset_type(asset_type)
    name, slug = _unique_asset_name(description, existing_assets)
    return project, AssetSpec(
        name=name,
        slug=slug,
        asset_type=asset_type.name,
        description=description,
        layout=asset_type.default_layout,
    )


def _preset_for_output_type(output_type: str) -> WorkflowPreset:
    preset_key = QUICK_OUTPUT_PRESETS.get(output_type)
    if preset_key is None:
        raise QuickStartError("Choose a supported output type before generating.")
    return get_workflow_preset(preset_key)


def _unique_asset_name(
    description: str, existing_assets: Sequence[AssetSpec]
) -> tuple[str, str]:
    base_name = _asset_name_from_description(description)
    used_slugs = {asset.slug or slugify(asset.name) for asset in existing_assets}
    base_slug = slugify(base_name)
    if base_slug not in used_slugs:
        return base_name, base_slug
    suffix = 2
    while f"{base_slug}-{suffix}" in used_slugs:
        suffix += 1
    return f"{base_name} {suffix}", f"{base_slug}-{suffix}"


def _asset_name_from_description(description: str) -> str:
    words = [
        word
        for word in re.findall(r"[A-Za-z0-9]+", description)
        if word.lower() not in _NAME_STOP_WORDS
    ]
    if not words:
        raise QuickStartError("Describe the asset with a few meaningful words.")
    return " ".join(word.capitalize() for word in words[:4])
