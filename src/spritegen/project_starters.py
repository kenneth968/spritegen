"""Starter project templates for first-run game asset workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from .layouts import AssetLayout
from .projects import (
    AssetSpec,
    AssetTypeSpec,
    ColorTreatment,
    EvolutionPlan,
    PostProcessSettings,
    ProjectSpec,
    ProviderDefaults,
)


@dataclass(frozen=True)
class ProjectStarter:
    key: str
    label: str
    description: str
    project_name: str
    summary: str
    visual_style: str
    shared_context: str
    palette: tuple[str, ...]
    negative_prompt: str
    asset_types: tuple[AssetTypeSpec, ...]
    first_asset: AssetSpec
    color_mode: str = "full_color"
    color_prompt: str = ""
    remove_background: bool = True
    custom_layouts: tuple[AssetLayout, ...] = field(default_factory=tuple)

    def build_project(
        self,
        image_provider: str = "mock",
        image_model: str = "mock",
        prompt_provider: str = "mock",
        prompt_model: str = "mock",
    ) -> ProjectSpec:
        project = ProjectSpec(
            name=self.project_name,
            summary=self.summary,
            visual_style=self.visual_style,
            shared_context=self.shared_context,
            palette=list(self.palette),
            negative_prompt=self.negative_prompt,
            provider_defaults=ProviderDefaults(
                image_provider=image_provider,
                image_model=image_model,
                prompt_provider=prompt_provider,
                prompt_model=prompt_model,
            ),
            color_treatment=ColorTreatment(
                mode=self.color_mode,
                custom_prompt=self.color_prompt,
            ),
            postprocess=PostProcessSettings(remove_background=self.remove_background),
        )
        for asset_type in self.asset_types:
            project.add_asset_type(AssetTypeSpec.from_dict(asset_type.to_dict()))
        for layout in self.custom_layouts:
            project.add_layout(AssetLayout.from_dict(layout.to_dict()))
        return project

    def build_first_asset(self) -> AssetSpec:
        return AssetSpec.from_dict(self.first_asset.to_dict())


PROJECT_STARTERS: dict[str, ProjectStarter] = {
    "mycelium_td": ProjectStarter(
        key="mycelium_td",
        label="MyceliumTD tower defense",
        description="Fungal tower-defense project with a four-stage starter tower.",
        project_name="MyceliumTD",
        summary="Fungal tower defense game on a damp forest floor",
        visual_style=(
            "clean cartoon tower-defense sprites, bold readable outlines, soft organic "
            "mushroom materials, bright but earthy palette, friendly tactical game feel"
        ),
        shared_context=(
            "Friendly fungal towers defend a living mycelium colony on a mossy forest "
            "floor from tiny slime pests and burrowing insects."
        ),
        palette=("#8B4513", "#228B22", "#9932CC", "#00FA9A", "#F7E7CE"),
        negative_prompt="photorealistic, gritty horror, watermark, text labels, UI text",
        color_mode="limited_palette",
        color_prompt=(
            "Keep each tower readable at small scale and reserve glow colors for attack "
            "identity or upgrade power."
        ),
        asset_types=(
            AssetTypeSpec(
                name="tower",
                shared_prompt=(
                    "Readable tower sprites with a consistent base silhouette, organic "
                    "fungal materials, clean outlines, and a clear attack role."
                ),
                evolution=EvolutionPlan(
                    count=4,
                    labels=["base", "upgraded", "advanced", "ultimate"],
                    shared_prompt=(
                        "Each upgrade keeps the same mushroom identity while adding more "
                        "cap structure, spores, glow, and gameplay power cues."
                    ),
                ),
                default_layout="single_sprite",
            ),
        ),
        first_asset=AssetSpec(
            name="Puffball",
            asset_type="tower",
            description="A mushroom tower that attacks by releasing spore clouds.",
            details=(
                "Soft white cap, round friendly silhouette, teal spore puffs, area damage "
                "identity, grows denser and brighter through upgrades."
            ),
        ),
    ),
    "rogue_character": ProjectStarter(
        key="rogue_character",
        label="Rogue character expression atlas",
        description="Character project using the full-body plus eight emotion heads atlas.",
        project_name="ShadowGuild",
        summary="Stylized fantasy rogue character portraits and sprites",
        visual_style=(
            "clean tactical RPG character art, crisp inked outlines, expressive faces, "
            "readable costume shapes, subtle cel shading"
        ),
        shared_context=(
            "A moonlit guild of agile rogues, assassins, scouts, and spies in a stylized "
            "fantasy tactics game."
        ),
        palette=("#1B1B2F", "#4E4B7A", "#B84A62", "#F2D6A2", "#7DD3C7"),
        negative_prompt="photorealistic, watermark, text labels, extra limbs, inconsistent face",
        color_mode="limited_palette",
        color_prompt="Keep hair, skin, eye, and costume colors identical across every atlas cell.",
        asset_types=(
            AssetTypeSpec(
                name="character",
                shared_prompt=(
                    "Keep the same character identity, face shape, hair, costume language, "
                    "palette, and rendering style across the full body and every expression."
                ),
                evolution=EvolutionPlan(count=1, labels=["atlas"]),
                default_layout="character_full_plus_8_emotions",
            ),
        ),
        first_asset=AssetSpec(
            name="Rogue Assassin",
            asset_type="character",
            description="A female rogue assassin with a sharp hooded silhouette.",
            details=(
                "Full-body pose with twin daggers, confident stance, dark violet hood, "
                "teal accents, and eight chibi emotion heads of the same character."
            ),
            layout="character_full_plus_8_emotions",
        ),
    ),
}


def list_project_starters() -> list[ProjectStarter]:
    return [PROJECT_STARTERS[key] for key in sorted(PROJECT_STARTERS)]


def get_project_starter(key: str) -> ProjectStarter:
    try:
        return PROJECT_STARTERS[key]
    except KeyError as exc:
        known = ", ".join(sorted(PROJECT_STARTERS))
        raise ValueError(f"Unknown project starter '{key}'. Available starters: {known}") from exc
