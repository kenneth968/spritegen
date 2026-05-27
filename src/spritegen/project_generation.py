"""Generate project assets from prompt packets and save outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import SpriteConfig
from .generator import SpriteGenerator
from .projects import AssetSpec, ProjectSpec, ProjectStore, PromptPacket, PromptPlanner
from .slicer import Slicer
from .style import StylePreset, StyleManager


@dataclass
class GeneratedPacketOutput:
    stage_index: int | None
    stage_label: str | None
    variant_index: int | None
    variant_count: int
    layout_name: str
    prompt: str
    raw_image: Path
    slices: list[Path] = field(default_factory=list)
    reference_images: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "stage_index": self.stage_index,
            "stage_label": self.stage_label,
            "variant_index": self.variant_index,
            "variant_count": self.variant_count,
            "layout_name": self.layout_name,
            "prompt": self.prompt,
            "raw_image": str(self.raw_image),
            "slices": [str(path) for path in self.slices],
            "reference_images": [str(path) for path in self.reference_images],
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
        variants_per_packet: int = 1,
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
            variants_per_packet=variants_per_packet,
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
        variants_per_packet: int = 1,
    ) -> ProjectGenerationResult:
        if variants_per_packet < 1:
            raise ValueError("variants_per_packet must be at least 1")

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
        reference_images = self._collect_reference_images(
            project,
            asset,
            packets,
            provider=image_provider,
        )
        outputs: list[GeneratedPacketOutput] = []

        for packet in packets:
            layout = project.get_layout(packet.layout_name)
            for variant_index in range(1, variants_per_packet + 1):
                output_name = self._output_filename(packet, variant_index, variants_per_packet)
                raw_path = base_output / f"{output_name}.png"

                kwargs = {"reference_images": reference_images} if reference_images else {}
                image_data = generator.generate_raw_image(
                    prompt=packet.prompt,
                    negative_prompt=packet.negative_prompt,
                    width=layout.width,
                    height=layout.height,
                    **kwargs,
                )
                raw_path.write_bytes(image_data)

                slice_dir = base_output / output_name
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
                    prefix=output_name,
                )

                outputs.append(
                    GeneratedPacketOutput(
                        stage_index=packet.stage_index,
                        stage_label=packet.stage_label,
                        variant_index=(
                            variant_index if variants_per_packet > 1 else None
                        ),
                        variant_count=variants_per_packet,
                        layout_name=packet.layout_name,
                        prompt=packet.prompt,
                        raw_image=raw_path,
                        slices=slice_paths,
                        reference_images=reference_images,
                    )
                )

        manifest_path = base_output / "generation_manifest.json"
        manifest = {
            "project": project.to_dict(),
            "asset": asset.to_dict(),
            "provider": image_provider,
            "model": image_model,
            "variants_per_packet": variants_per_packet,
            "postprocess": {
                "remove_background": should_remove_background,
            },
            "reference_images": [str(path) for path in reference_images],
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

    def _output_filename(
        self,
        packet: PromptPacket,
        variant_index: int,
        variant_count: int,
    ) -> str:
        stage_name = self._stage_filename(packet)
        if variant_count == 1:
            return stage_name
        return f"{stage_name}-v{variant_index:02d}"

    def _collect_reference_images(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        packets: list[PromptPacket],
        provider: str,
        limit: int = 4,
    ) -> list[Path]:
        if provider != "openrouter":
            return []

        project_slug = project.slug or project.name
        current_slug = asset.slug or asset.name
        references: list[Path] = []
        seen: set[Path] = set()
        known_assets = [
            known
            for packet in packets
            for known in packet.metadata.get("known_assets", [])
            if isinstance(known, dict)
        ]
        for known in known_assets:
            known_slug = str(known.get("slug") or "")
            if not known_slug or known_slug == current_slug:
                continue
            manifest_path = (
                self.store.generated_dir(project_slug)
                / known_slug
                / "generation_manifest.json"
            )
            raw_image = self._first_manifest_raw_image(manifest_path)
            if raw_image is None or raw_image in seen:
                continue
            seen.add(raw_image)
            references.append(raw_image)
            if len(references) >= limit:
                break
        return references

    def _first_manifest_raw_image(self, manifest_path: Path) -> Path | None:
        if not manifest_path.exists():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        for output in manifest.get("outputs", []):
            if not isinstance(output, dict):
                continue
            raw_image = output.get("raw_image")
            if not isinstance(raw_image, str) or not raw_image:
                continue
            path = Path(raw_image)
            if not path.is_absolute():
                path = manifest_path.parent / path
            if path.exists():
                return path
        return None
