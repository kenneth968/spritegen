"""Project and asset planning for coherent game-art generation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .layouts import AssetLayout, get_layout
from .prompt_guidance import PromptGuideLibrary


PROJECT_SCHEMA_VERSION = 1

COLOR_TREATMENT_MODES = {
    "full_color": "Full color",
    "limited_palette": "Limited palette",
    "black_white": "Black and white",
    "grayscale_value_map": "Grayscale value map",
    "single_hue_value_map": "Single-hue value map",
}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


@dataclass
class ProviderDefaults:
    image_provider: str = "openai"
    image_model: str = "gpt-image-2"
    prompt_provider: str = "openai"
    prompt_model: str = "gpt-5.5"
    quality: str = "medium"
    size: str = "1024x1024"

    def to_dict(self) -> dict[str, Any]:
        return {
            "image_provider": self.image_provider,
            "image_model": self.image_model,
            "prompt_provider": self.prompt_provider,
            "prompt_model": self.prompt_model,
            "quality": self.quality,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ProviderDefaults":
        if not data:
            return cls()
        return cls(
            image_provider=data.get("image_provider", "openai"),
            image_model=data.get("image_model", "gpt-image-2"),
            prompt_provider=data.get("prompt_provider", "openai"),
            prompt_model=data.get("prompt_model", "gpt-5.5"),
            quality=data.get("quality", "medium"),
            size=data.get("size", "1024x1024"),
        )


@dataclass
class ColorTreatment:
    mode: str = "full_color"
    custom_prompt: str = ""

    def __post_init__(self) -> None:
        if self.mode not in COLOR_TREATMENT_MODES:
            known = ", ".join(sorted(COLOR_TREATMENT_MODES))
            raise ValueError(f"Unknown color treatment '{self.mode}'. Known modes: {known}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "custom_prompt": self.custom_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ColorTreatment":
        if not data:
            return cls()
        return cls(
            mode=data.get("mode", "full_color"),
            custom_prompt=data.get("custom_prompt", ""),
        )

    def prompt_text(self, palette: list[str]) -> str:
        palette_text = ", ".join(palette)
        if self.mode == "full_color":
            text = "Use the project palette as full-color game art."
        elif self.mode == "limited_palette":
            text = (
                "Use a limited-palette production style. "
                f"Restrict hues to the project palette: {palette_text or 'the listed palette'}."
            )
        elif self.mode == "black_white":
            text = (
                "Render as black-and-white game art: clear inked silhouette, white fills, "
                "strong readable value separation, no color hue."
            )
        elif self.mode == "grayscale_value_map":
            text = (
                "Render as a grayscale value-map asset. Use stepped gray values as coded "
                "material or lighting indices, with clean separable bands and no hue."
            )
        elif self.mode == "single_hue_value_map":
            hue = palette[0] if palette else "one chosen hue"
            text = (
                f"Render as a single-hue value-map asset based on {hue}. Use controlled "
                "tints and shades so the image can be recolored or shader-mapped later."
            )
        else:
            text = "Use the project color treatment."

        if self.custom_prompt:
            text = f"{text} {self.custom_prompt}"
        return text


@dataclass
class PostProcessSettings:
    remove_background: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "remove_background": self.remove_background,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PostProcessSettings":
        if not data:
            return cls()
        return cls(remove_background=bool(data.get("remove_background", True)))

    def prompt_text(self) -> str:
        if self.remove_background:
            return (
                "Generated regions will be background-removed after slicing. Use a simple, "
                "plain, high-contrast background around the asset and avoid shadows that merge "
                "with the object silhouette."
            )
        return (
            "Keep the background or frame as part of the generated asset region. Do not rely "
            "on automatic transparency after slicing."
        )


@dataclass
class EvolutionPlan:
    count: int = 1
    labels: list[str] = field(default_factory=list)
    shared_prompt: str = ""

    def stage_label(self, index: int) -> str:
        if index < 1 or index > self.count:
            raise ValueError(f"Stage index {index} is outside 1..{self.count}")
        if index <= len(self.labels):
            return self.labels[index - 1]
        if self.count == 1:
            return "final"
        defaults = ["base", "upgraded", "advanced", "ultimate"]
        return defaults[index - 1] if index <= len(defaults) else f"stage {index}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "count": self.count,
            "labels": self.labels,
            "shared_prompt": self.shared_prompt,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EvolutionPlan":
        if not data:
            return cls()
        return cls(
            count=int(data.get("count", 1)),
            labels=list(data.get("labels", [])),
            shared_prompt=data.get("shared_prompt", ""),
        )


@dataclass
class AssetTypeSpec:
    name: str
    shared_prompt: str = ""
    evolution: EvolutionPlan = field(default_factory=EvolutionPlan)
    default_layout: str = "single_sprite"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "shared_prompt": self.shared_prompt,
            "evolution": self.evolution.to_dict(),
            "default_layout": self.default_layout,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetTypeSpec":
        return cls(
            name=data["name"],
            shared_prompt=data.get("shared_prompt", ""),
            evolution=EvolutionPlan.from_dict(data.get("evolution")),
            default_layout=data.get("default_layout", "single_sprite"),
        )


@dataclass
class ProjectSpec:
    name: str
    summary: str
    visual_style: str
    shared_context: str
    slug: str | None = None
    palette: list[str] = field(default_factory=list)
    negative_prompt: str = ""
    provider_defaults: ProviderDefaults = field(default_factory=ProviderDefaults)
    color_treatment: ColorTreatment = field(default_factory=ColorTreatment)
    postprocess: PostProcessSettings = field(default_factory=PostProcessSettings)
    asset_types: dict[str, AssetTypeSpec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

    def add_asset_type(self, asset_type: AssetTypeSpec) -> None:
        self.asset_types[asset_type.name] = asset_type

    def get_asset_type(self, name: str) -> AssetTypeSpec:
        try:
            return self.asset_types[name]
        except KeyError:
            known = ", ".join(sorted(self.asset_types)) or "none"
            raise ValueError(f"Unknown asset type '{name}'. Known asset types: {known}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": PROJECT_SCHEMA_VERSION,
            "name": self.name,
            "slug": self.slug,
            "summary": self.summary,
            "visual_style": self.visual_style,
            "shared_context": self.shared_context,
            "palette": self.palette,
            "negative_prompt": self.negative_prompt,
            "provider_defaults": self.provider_defaults.to_dict(),
            "color_treatment": self.color_treatment.to_dict(),
            "postprocess": self.postprocess.to_dict(),
            "asset_types": {
                name: asset_type.to_dict()
                for name, asset_type in sorted(self.asset_types.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectSpec":
        if data.get("version") != PROJECT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported project schema version: {data.get('version')}")
        project = cls(
            name=data["name"],
            slug=data.get("slug"),
            summary=data.get("summary", ""),
            visual_style=data.get("visual_style", ""),
            shared_context=data.get("shared_context", ""),
            palette=list(data.get("palette", [])),
            negative_prompt=data.get("negative_prompt", ""),
            provider_defaults=ProviderDefaults.from_dict(data.get("provider_defaults")),
            color_treatment=ColorTreatment.from_dict(data.get("color_treatment")),
            postprocess=PostProcessSettings.from_dict(data.get("postprocess")),
        )
        for asset_type_data in data.get("asset_types", {}).values():
            project.add_asset_type(AssetTypeSpec.from_dict(asset_type_data))
        return project


@dataclass
class AssetSpec:
    name: str
    asset_type: str
    description: str
    slug: str | None = None
    details: str = ""
    enhanced_prompt: str = ""
    layout: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": PROJECT_SCHEMA_VERSION,
            "name": self.name,
            "slug": self.slug,
            "asset_type": self.asset_type,
            "description": self.description,
            "details": self.details,
            "enhanced_prompt": self.enhanced_prompt,
            "layout": self.layout,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetSpec":
        if data.get("version") != PROJECT_SCHEMA_VERSION:
            raise ValueError(f"Unsupported asset schema version: {data.get('version')}")
        return cls(
            name=data["name"],
            slug=data.get("slug"),
            asset_type=data["asset_type"],
            description=data.get("description", ""),
            details=data.get("details", ""),
            enhanced_prompt=data.get("enhanced_prompt", ""),
            layout=data.get("layout"),
            notes=data.get("notes", ""),
        )


@dataclass
class PromptPacket:
    project_slug: str
    asset_slug: str
    asset_type: str
    stage_index: int | None
    stage_label: str | None
    layout_name: str
    prompt: str
    negative_prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_slug": self.project_slug,
            "asset_slug": self.asset_slug,
            "asset_type": self.asset_type,
            "stage_index": self.stage_index,
            "stage_label": self.stage_label,
            "layout_name": self.layout_name,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "metadata": self.metadata,
        }


class PromptPlanner:
    """Build image-generator-ready prompts from project context."""

    def __init__(self, guide_library: PromptGuideLibrary | None = None) -> None:
        self.guide_library = guide_library or PromptGuideLibrary()

    def build_project_enhancement_brief(self, project: ProjectSpec) -> str:
        return "\n".join(
            part
            for part in [
                "Improve this game-art project brief for future image generation.",
                "Return strict JSON with these keys only: "
                "summary, visual_style, shared_context, palette, negative_prompt, color_prompt.",
                "Do not include markdown fences or commentary.",
                f"Project: {project.name}",
                f"Current summary: {project.summary}",
                f"Current visual style: {project.visual_style}",
                f"Current shared universe: {project.shared_context}",
                f"Current palette: {', '.join(project.palette)}" if project.palette else "",
                f"Current negative prompt: {project.negative_prompt}" if project.negative_prompt else "",
                f"Current color mode: {project.color_treatment.mode}",
                f"Post-processing: {project.postprocess.prompt_text()}",
                (
                    f"Current color-mode notes: {project.color_treatment.custom_prompt}"
                    if project.color_treatment.custom_prompt
                    else ""
                ),
                "Keep the user's game idea intact. Make the style concrete and reusable.",
            ]
            if part
        )

    def build_project_enhancement_system_prompt(self) -> str:
        return self.guide_library.combined(["project", "color_modes"])

    def project_enhancement_fallback(self, project: ProjectSpec) -> dict[str, Any]:
        return {
            "summary": project.summary or f"{project.name} game-art project",
            "visual_style": ", ".join(
                part
                for part in [
                    project.visual_style,
                    "game-ready art direction",
                    "consistent silhouettes and readable shapes",
                ]
                if part
            ),
            "shared_context": project.shared_context,
            "palette": project.palette,
            "negative_prompt": project.negative_prompt,
            "color_prompt": project.color_treatment.custom_prompt,
        }

    def build_asset_type_enhancement_brief(
        self,
        project: ProjectSpec,
        asset_type: AssetTypeSpec,
    ) -> str:
        return "\n".join(
            part
            for part in [
                "Improve these reusable rules for one game-asset family.",
                "Return strict JSON with these keys only: "
                "shared_prompt, evolution_shared_prompt, evolution_labels.",
                "evolution_labels must be an array of concise labels.",
                "Do not include markdown fences or commentary.",
                f"Project: {project.name}",
                f"Project context: {project.shared_context}",
                f"Visual style: {project.visual_style}",
                f"Color treatment: {project.color_treatment.prompt_text(project.palette)}",
                f"Post-processing: {project.postprocess.prompt_text()}",
                f"Asset type: {asset_type.name}",
                f"Current asset-type rules: {asset_type.shared_prompt}",
                f"Evolution count: {asset_type.evolution.count}",
                (
                    f"Current evolution rules: {asset_type.evolution.shared_prompt}"
                    if asset_type.evolution.shared_prompt
                    else ""
                ),
                (
                    f"Current evolution labels: {', '.join(asset_type.evolution.labels)}"
                    if asset_type.evolution.labels
                    else ""
                ),
                f"Default layout: {asset_type.default_layout}",
                "Keep the rules reusable across many assets in this family.",
            ]
            if part
        )

    def build_asset_type_enhancement_system_prompt(self) -> str:
        return self.guide_library.combined(["project", "asset_type", "color_modes"])

    def asset_type_enhancement_fallback(self, asset_type: AssetTypeSpec) -> dict[str, Any]:
        labels = [
            asset_type.evolution.stage_label(index)
            for index in range(1, max(asset_type.evolution.count, 1) + 1)
        ]
        return {
            "shared_prompt": ", ".join(
                part
                for part in [
                    asset_type.shared_prompt,
                    "consistent family silhouette and rendering style",
                    "readable at small game scale",
                ]
                if part
            ),
            "evolution_shared_prompt": asset_type.evolution.shared_prompt,
            "evolution_labels": labels,
        }

    def build_enhancement_brief(
        self,
        project: ProjectSpec,
        asset_type: AssetTypeSpec,
        asset: AssetSpec,
        known_assets: list[AssetSpec] | None = None,
    ) -> str:
        known = self._known_asset_context(known_assets or [], exclude_slug=asset.slug)
        layout = get_layout(asset.layout or asset_type.default_layout)
        return "\n".join(
            part
            for part in [
                "Rewrite this rough game-asset idea into a concise image prompt.",
                "Preserve the user's intent while making it concrete for an image model.",
                f"Project: {project.name}",
                f"Project context: {project.shared_context}",
                f"Visual style: {project.visual_style}",
                f"Palette: {', '.join(project.palette)}" if project.palette else "",
                f"Color treatment: {project.color_treatment.prompt_text(project.palette)}",
                f"Post-processing: {project.postprocess.prompt_text()}",
                f"Asset type rules: {asset_type.shared_prompt}",
                f"Existing universe assets to harmonize with: {known}" if known else "",
                f"Raw asset idea: {asset.description}",
                f"Extra details: {asset.details}" if asset.details else "",
                f"Output layout: {layout.name}. {layout.prompt_instructions}",
                "Return only the improved prompt text.",
            ]
            if part
        )

    def build_enhancement_system_prompt(
        self,
        project: ProjectSpec,
        asset_type: AssetTypeSpec,
        asset: AssetSpec,
    ) -> str:
        layout = get_layout(asset.layout or asset_type.default_layout)
        guide_names = [
            "project",
            "asset_type",
            "asset",
            "color_modes",
            f"layout_{layout.name}",
        ]
        return self.guide_library.combined(guide_names)

    def build_prompt_packets(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        known_assets: list[AssetSpec] | None = None,
    ) -> list[PromptPacket]:
        asset_type = project.get_asset_type(asset.asset_type)
        layout = get_layout(asset.layout or asset_type.default_layout)
        count = max(asset_type.evolution.count, 1)
        packets: list[PromptPacket] = []
        for stage_index in range(1, count + 1):
            stage_label = asset_type.evolution.stage_label(stage_index) if count > 1 else None
            packets.append(
                self.build_prompt_packet(
                    project=project,
                    asset_type=asset_type,
                    asset=asset,
                    layout=layout,
                    known_assets=known_assets or [],
                    stage_index=stage_index if count > 1 else None,
                    stage_label=stage_label,
                )
            )
        return packets

    def build_prompt_packet(
        self,
        project: ProjectSpec,
        asset_type: AssetTypeSpec,
        asset: AssetSpec,
        layout: AssetLayout,
        known_assets: list[AssetSpec],
        stage_index: int | None,
        stage_label: str | None,
    ) -> PromptPacket:
        known_context = self._known_asset_context(known_assets, exclude_slug=asset.slug)
        stage_context = ""
        if stage_index is not None and stage_label:
            stage_context = (
                f"Evolution stage {stage_index} of {asset_type.evolution.count}: "
                f"{stage_label}. {asset_type.evolution.shared_prompt}"
            ).strip()

        prompt_parts = [
            f"Project: {project.name}. {project.summary}",
            f"Shared universe: {project.shared_context}",
            f"Visual style: {project.visual_style}",
            f"Color palette: {', '.join(project.palette)}" if project.palette else "",
            f"Color treatment: {project.color_treatment.prompt_text(project.palette)}",
            f"Post-processing: {project.postprocess.prompt_text()}",
            f"Asset type: {asset_type.name}. {asset_type.shared_prompt}",
            f"Existing related assets: {known_context}" if known_context else "",
            f"Current asset: {asset.name}. {asset.enhanced_prompt or asset.description}",
            f"Details: {asset.details}" if asset.details else "",
            stage_context,
            f"Layout: {layout.prompt_instructions}",
            self._region_prompt(layout),
            (
                "Keep the asset cohesive with the project universe, with matching line "
                "weight, material language, palette, camera angle, and rendering style."
            ),
            "No UI, no text labels, no watermark, no signature.",
        ]
        prompt = "\n".join(part for part in prompt_parts if part)

        return PromptPacket(
            project_slug=project.slug or slugify(project.name),
            asset_slug=asset.slug or slugify(asset.name),
            asset_type=asset_type.name,
            stage_index=stage_index,
            stage_label=stage_label,
            layout_name=layout.name,
            prompt=prompt,
            negative_prompt=project.negative_prompt,
            metadata={
                "provider_defaults": project.provider_defaults.to_dict(),
                "color_treatment": project.color_treatment.to_dict(),
                "postprocess": project.postprocess.to_dict(),
                "layout": layout.to_dict(),
            },
        )

    def _known_asset_context(
        self,
        assets: list[AssetSpec],
        exclude_slug: str | None,
    ) -> str:
        summaries = []
        for asset in assets:
            if exclude_slug and asset.slug == exclude_slug:
                continue
            summary = asset.enhanced_prompt or asset.description
            summaries.append(f"{asset.name}: {summary}")
        return " | ".join(summaries[:5])

    def _region_prompt(self, layout: AssetLayout) -> str:
        regions = [
            f"{r.name} at ({r.x},{r.y}) size {r.width}x{r.height}: {r.prompt_role}"
            for r in layout.regions
        ]
        return "Regions: " + "; ".join(regions)


class ProjectStore:
    def __init__(self, root: Path | str = "projects") -> None:
        self.root = Path(root)

    def project_dir(self, slug: str) -> Path:
        return self.root / slug

    def project_path(self, slug: str) -> Path:
        return self.project_dir(slug) / "project.json"

    def asset_dir(self, slug: str) -> Path:
        return self.project_dir(slug) / "assets"

    def generated_dir(self, slug: str) -> Path:
        return self.project_dir(slug) / "generated"

    def save_project(self, project: ProjectSpec) -> Path:
        path = self.project_path(project.slug or slugify(project.name))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
        return path

    def load_project(self, slug_or_path: str | Path) -> ProjectSpec:
        raw_path = Path(slug_or_path)
        if raw_path.exists():
            path = raw_path
        else:
            path = self.project_path(str(slug_or_path))
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProjectSpec.from_dict(data)

    def save_asset(self, project: ProjectSpec, asset: AssetSpec) -> Path:
        path = self.asset_dir(project.slug or slugify(project.name)) / f"{asset.slug}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asset.to_dict(), indent=2), encoding="utf-8")
        return path

    def load_asset(self, project: ProjectSpec, slug_or_path: str | Path) -> AssetSpec:
        raw_path = Path(slug_or_path)
        if raw_path.exists():
            path = raw_path
        else:
            path = self.asset_dir(project.slug or slugify(project.name)) / f"{slug_or_path}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return AssetSpec.from_dict(data)

    def load_assets(self, project: ProjectSpec) -> list[AssetSpec]:
        root = self.asset_dir(project.slug or slugify(project.name))
        if not root.exists():
            return []
        assets: list[AssetSpec] = []
        for path in sorted(root.glob("*.json")):
            assets.append(AssetSpec.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return assets

    def load_assets_for_slug(self, project_slug: str) -> list[AssetSpec]:
        root = self.asset_dir(project_slug)
        if not root.exists():
            return []
        assets: list[AssetSpec] = []
        for path in sorted(root.glob("*.json")):
            assets.append(AssetSpec.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return assets

    def list_projects(self) -> list[ProjectSpec]:
        if not self.root.exists():
            return []
        projects: list[ProjectSpec] = []
        for path in sorted(self.root.glob("*/project.json")):
            try:
                projects.append(ProjectSpec.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, ValueError, json.JSONDecodeError, KeyError):
                continue
        return projects

    def save_prompt_plan(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        packets: list[PromptPacket],
    ) -> Path:
        path = (
            self.project_dir(project.slug or slugify(project.name))
            / "prompt_plans"
            / f"{asset.slug}.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "project": project.slug,
            "asset": asset.slug,
            "packets": [packet.to_dict() for packet in packets],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path


def apply_project_enhancement(project: ProjectSpec, data: dict[str, Any]) -> ProjectSpec:
    project.summary = _string_value(data.get("summary"), project.summary)
    project.visual_style = _string_value(data.get("visual_style"), project.visual_style)
    project.shared_context = _string_value(data.get("shared_context"), project.shared_context)
    project.negative_prompt = _string_value(data.get("negative_prompt"), project.negative_prompt)
    project.color_treatment.custom_prompt = _string_value(
        data.get("color_prompt"),
        project.color_treatment.custom_prompt,
    )
    palette = data.get("palette")
    if isinstance(palette, list):
        project.palette = [str(value).strip() for value in palette if str(value).strip()]
    elif isinstance(palette, str):
        project.palette = [value.strip() for value in palette.split(",") if value.strip()]
    return project


def apply_asset_type_enhancement(
    asset_type: AssetTypeSpec,
    data: dict[str, Any],
) -> AssetTypeSpec:
    asset_type.shared_prompt = _string_value(data.get("shared_prompt"), asset_type.shared_prompt)
    asset_type.evolution.shared_prompt = _string_value(
        data.get("evolution_shared_prompt"),
        asset_type.evolution.shared_prompt,
    )
    labels = data.get("evolution_labels")
    if isinstance(labels, list):
        asset_type.evolution.labels = [str(value).strip() for value in labels if str(value).strip()]
    elif isinstance(labels, str):
        asset_type.evolution.labels = [value.strip() for value in labels.split(",") if value.strip()]
    return asset_type


def _string_value(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback
