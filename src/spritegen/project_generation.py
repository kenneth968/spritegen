"""Generate project assets from prompt packets and save outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import SpriteConfig
from .generator import SpriteGenerator
from .layouts import get_layout
from .projects import AssetSpec, ProjectSpec, ProjectStore, PromptPacket, PromptPlanner
from .slicer import Slicer
from .style import StylePreset, StyleManager


@dataclass
class GeneratedPacketOutput:
    stage_index: int | None
    stage_label: str | None
    layout_name: str
    prompt: str
    raw_image: Path
    slices: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage_index": self.stage_index,
            "stage_label": self.stage_label,
            "layout_name": self.layout_name,
            "prompt": self.prompt,
            "raw_image": str(self.raw_image),
            "slices": [str(path) for path in self.slices],
        }


@dataclass
class ProjectGenerationResult:
    project_slug: str
    asset_slug: str
    output_dir: Path
    manifest_path: Path
    outputs: list[GeneratedPacketOutput]

    def to_dict(self) -> dict:
        return {
            "project_slug": self.project_slug,
            "asset_slug": self.asset_slug,
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "outputs": [output.to_dict() for output in self.outputs],
        }


class ProjectAssetGenerator:
    def __init__(self, store: ProjectStore | None = None) -> None:
        self.store = store or ProjectStore()

    def generate(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        known_assets: list[AssetSpec] | None = None,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        output_root: Path | str | None = None,
        remove_background: bool | None = None,
    ) -> ProjectGenerationResult:
        planner = PromptPlanner()
        packets = planner.build_prompt_packets(
            project,
            asset,
            known_assets=known_assets or [],
        )
        return self.generate_packets(
            project=project,
            asset=asset,
            packets=packets,
            provider=provider,
            model=model,
            api_key=api_key,
            output_root=output_root,
            remove_background=remove_background,
        )

    def generate_packets(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        packets: list[PromptPacket],
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        output_root: Path | str | None = None,
        remove_background: bool | None = None,
    ) -> ProjectGenerationResult:
        image_provider = provider or project.provider_defaults.image_provider
        image_model = model or project.provider_defaults.image_model
        project_slug = project.slug or project.name
        asset_slug = asset.slug or asset.name

        base_output = (
            Path(output_root)
            if output_root
            else self.store.generated_dir(project_slug) / asset_slug
        )
        base_output.mkdir(parents=True, exist_ok=True)
        should_remove_background = (
            project.postprocess.remove_background
            if remove_background is None
            else remove_background
        )

        generator = self._create_generator(
            project,
            image_provider,
            image_model,
            base_output,
            api_key=api_key,
        )
        outputs: list[GeneratedPacketOutput] = []

        for packet in packets:
            layout = get_layout(packet.layout_name)
            stage_name = self._stage_filename(packet)
            raw_path = base_output / f"{stage_name}.png"

            image_data = generator.generate_raw_image(
                prompt=packet.prompt,
                negative_prompt=packet.negative_prompt,
                width=layout.width,
                height=layout.height,
            )
            raw_path.write_bytes(image_data)

            slice_dir = base_output / stage_name
            slicer = Slicer(
                output_dir=slice_dir,
                config=SpriteConfig(
                    output_dir=slice_dir,
                    transparent_bg=should_remove_background,
                ),
            )
            slice_paths = slicer.slice_layout_image(
                image_data,
                layout,
                prefix=stage_name,
            )

            outputs.append(
                GeneratedPacketOutput(
                    stage_index=packet.stage_index,
                    stage_label=packet.stage_label,
                    layout_name=packet.layout_name,
                    prompt=packet.prompt,
                    raw_image=raw_path,
                    slices=slice_paths,
                )
            )

        manifest_path = base_output / "generation_manifest.json"
        manifest = {
            "project": project.to_dict(),
            "asset": asset.to_dict(),
            "provider": image_provider,
            "model": image_model,
            "postprocess": {
                "remove_background": should_remove_background,
            },
            "outputs": [output.to_dict() for output in outputs],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        return ProjectGenerationResult(
            project_slug=project_slug,
            asset_slug=asset_slug,
            output_dir=base_output,
            manifest_path=manifest_path,
            outputs=outputs,
        )

    def _create_generator(
        self,
        project: ProjectSpec,
        provider: str,
        model: str,
        output_dir: Path,
        api_key: str | None = None,
    ) -> SpriteGenerator:
        style = StylePreset(
            name=f"{project.slug or project.name}_project",
            base_prompt="",
            negative_prompt=project.negative_prompt,
            color_palette=project.palette,
            visual_tags=[],
            seed=project.slug or project.name,
        )
        config = SpriteConfig(
            api_provider=provider,
            api_model=model,
            api_key=api_key,
            sheet_width=1024,
            sheet_height=1024,
            sprite_width=1024,
            sprite_height=1024,
        )
        return SpriteGenerator(
            style=style,
            config=config,
            style_manager=StyleManager(style_dir=output_dir / "_style_state"),
        )

    def _stage_filename(self, packet: PromptPacket) -> str:
        if packet.stage_index is None:
            return "single"
        label = (packet.stage_label or f"stage-{packet.stage_index}").replace(" ", "-")
        return f"stage-{packet.stage_index:02d}-{label}"
