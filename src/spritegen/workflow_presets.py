"""Reusable workflow presets for common game-asset generation shapes."""

from __future__ import annotations

from dataclasses import dataclass, field

from .projects import AssetTypeSpec, EvolutionPlan


@dataclass(frozen=True)
class WorkflowPreset:
    key: str
    label: str
    description: str
    asset_type: str
    shared_prompt: str
    default_layout: str
    evolution_count: int = 1
    evolution_labels: tuple[str, ...] = field(default_factory=tuple)
    evolution_prompt: str = ""

    def to_asset_type(self, name: str | None = None) -> AssetTypeSpec:
        return AssetTypeSpec(
            name=name or self.asset_type,
            shared_prompt=self.shared_prompt,
            evolution=EvolutionPlan(
                count=self.evolution_count,
                labels=list(self.evolution_labels),
                shared_prompt=self.evolution_prompt,
            ),
            default_layout=self.default_layout,
        )


WORKFLOW_PRESETS: dict[str, WorkflowPreset] = {
    "tower_4_stage": WorkflowPreset(
        key="tower_4_stage",
        label="Tower: 4 Evolutions",
        description="Four separate tower upgrade stages that keep one identity.",
        asset_type="tower",
        shared_prompt=(
            "Readable game tower sprites with a clear role silhouette, consistent base shape, "
            "bold outlines, and materials that remain coherent across all upgrades."
        ),
        default_layout="single_sprite",
        evolution_count=4,
        evolution_labels=("base", "upgraded", "advanced", "ultimate"),
        evolution_prompt=(
            "Each stage keeps the same core tower identity while adding stronger scale, "
            "materials, effects, and threat/readability cues."
        ),
    ),
    "character_emotion_atlas": WorkflowPreset(
        key="character_emotion_atlas",
        label="Character: Full Body + 8 Emotions",
        description="One full-body character plus eight chibi emotion heads in one atlas.",
        asset_type="character",
        shared_prompt=(
            "Keep the same character identity, costume language, palette, hair, face shape, "
            "and material rendering across the full-body pose and every emotion head."
        ),
        default_layout="character_full_plus_8_emotions",
        evolution_count=1,
    ),
    "four_variant_atlas": WorkflowPreset(
        key="four_variant_atlas",
        label="Four Variant Atlas",
        description="One 2x2 generated atlas for variants, poses, or item states.",
        asset_type="asset_variant",
        shared_prompt=(
            "Create four clearly separated variants of the same asset family, keeping shared "
            "style, palette, camera angle, and scale across all cells."
        ),
        default_layout="four_stage_grid",
        evolution_count=1,
    ),
    "single_prop": WorkflowPreset(
        key="single_prop",
        label="Single Prop",
        description="One isolated prop, pickup, building, or object sprite.",
        asset_type="prop",
        shared_prompt=(
            "One isolated game prop with a readable silhouette, coherent material language, "
            "and enough shape detail to read at small in-game size."
        ),
        default_layout="single_sprite",
        evolution_count=1,
    ),
    "tile_single": WorkflowPreset(
        key="tile_single",
        label="Tile: Single",
        description="One terrain, floor, wall, or decorative tile region.",
        asset_type="tile",
        shared_prompt=(
            "Tile art with readable material patterning, consistent top-down or orthographic "
            "camera, and edges that can be aligned with neighboring tiles."
        ),
        default_layout="single_sprite",
        evolution_count=1,
    ),
    "ui_icon": WorkflowPreset(
        key="ui_icon",
        label="UI Icon",
        description="One crisp ability, item, resource, or menu icon.",
        asset_type="ui_icon",
        shared_prompt=(
            "Crisp game UI icon with centered composition, strong silhouette, high contrast, "
            "minimal background clutter, and no text labels."
        ),
        default_layout="single_sprite",
        evolution_count=1,
    ),
}


def list_workflow_presets() -> list[WorkflowPreset]:
    return [WORKFLOW_PRESETS[key] for key in sorted(WORKFLOW_PRESETS)]


def get_workflow_preset(key: str) -> WorkflowPreset:
    try:
        return WORKFLOW_PRESETS[key]
    except KeyError as exc:
        known = ", ".join(sorted(WORKFLOW_PRESETS))
        raise ValueError(f"Unknown workflow preset '{key}'. Available presets: {known}") from exc
