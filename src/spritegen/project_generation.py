"""Generate project assets from prompt packets and save outputs."""

from __future__ import annotations

import json
from html import escape
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

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
    gallery_path: Path
    outputs: list[GeneratedPacketOutput]

    def to_dict(self) -> dict:
        return {
            "project_slug": self.project_slug,
            "asset_slug": self.asset_slug,
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "gallery_path": str(self.gallery_path),
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
        gallery_path = self._write_generation_gallery(
            project=project,
            asset=asset,
            provider=image_provider,
            model=image_model,
            output_dir=base_output,
            manifest_path=manifest_path,
            outputs=outputs,
            variants_per_packet=variants_per_packet,
            remove_background=should_remove_background,
            reference_images=reference_images,
        )

        return ProjectGenerationResult(
            project_slug=project_slug,
            asset_slug=asset_slug,
            output_dir=base_output,
            manifest_path=manifest_path,
            gallery_path=gallery_path,
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
        if provider not in {"openrouter", "openai"}:
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
            preferred_variant = self._preferred_variant_index(project_slug, known_slug)
            raw_image = self._first_manifest_raw_image(
                manifest_path,
                variant_index=preferred_variant,
            )
            if raw_image is None or raw_image in seen:
                continue
            seen.add(raw_image)
            references.append(raw_image)
            if len(references) >= limit:
                break
        return references

    def _preferred_variant_index(self, project_slug: str, asset_slug: str) -> int | None:
        export_manifest = (
            self.store.project_dir(project_slug)
            / "exports"
            / asset_slug
            / "asset_export_manifest.json"
        )
        if not export_manifest.exists():
            return None
        try:
            manifest = json.loads(export_manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        selected = manifest.get("selected_variant")
        return selected if isinstance(selected, int) and selected >= 1 else None

    def _first_manifest_raw_image(
        self,
        manifest_path: Path,
        variant_index: int | None = None,
    ) -> Path | None:
        if not manifest_path.exists():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        for output in manifest.get("outputs", []):
            if not isinstance(output, dict):
                continue
            if not self._matches_variant(output, variant_index):
                continue
            raw_image = output.get("raw_image")
            if not isinstance(raw_image, str) or not raw_image:
                continue
            path = Path(raw_image)
            if path.exists():
                return path
            if not path.is_absolute():
                path = manifest_path.parent / path
            if path.exists():
                return path
        if variant_index is not None:
            return self._first_manifest_raw_image(manifest_path)
        return None

    def _matches_variant(self, output: dict, variant_index: int | None) -> bool:
        if variant_index is None:
            return True
        output_variant = output.get("variant_index")
        if output_variant is None:
            return variant_index == 1
        return output_variant == variant_index

    def _write_generation_gallery(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        provider: str,
        model: str,
        output_dir: Path,
        manifest_path: Path,
        outputs: list[GeneratedPacketOutput],
        variants_per_packet: int,
        remove_background: bool,
        reference_images: list[Path],
    ) -> Path:
        gallery_path = output_dir / "asset_gallery.html"
        sections = "\n".join(
            self._gallery_output_section(output, output_dir)
            for output in outputs
        )
        reference_links = "\n".join(
            f'<li><a href="{self._gallery_href(path, output_dir)}">'
            f"{escape(path.name)}</a></li>"
            for path in reference_images
        ) or "<li>None</li>"
        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(project.name)} / {escape(asset.name)} asset gallery</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #1f2933; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
    .pill {{ border: 1px solid #c8d1dc; border-radius: 999px; padding: 4px 10px; font-size: 13px; }}
    .output {{ border-top: 1px solid #d7dee8; padding: 18px 0; }}
    .grid {{ display: grid; grid-template-columns: minmax(220px, 360px) 1fr; gap: 18px; }}
    .raw img {{ width: 100%; max-height: 360px; object-fit: contain; background: #eef2f7; }}
    .slices {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 10px; }}
    .slice img {{ width: 100%; aspect-ratio: 1; object-fit: contain; background: #eef2f7; }}
    .caption {{ font-size: 12px; overflow-wrap: anywhere; color: #52606d; margin-top: 4px; }}
    .prompt {{ white-space: pre-wrap; background: #f5f7fa; padding: 12px; margin-top: 14px; font-size: 13px; }}
    a {{ color: #155e75; }}
    @media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr; }} body {{ margin: 14px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(project.name)} / {escape(asset.name)}</h1>
    <p>{escape(asset.description)}</p>
    <div class="meta">
      <span class="pill">provider: {escape(provider)}</span>
      <span class="pill">model: {escape(model)}</span>
      <span class="pill">variants per packet: {variants_per_packet}</span>
      <span class="pill">background removal: {str(remove_background).lower()}</span>
    </div>
    <p><a href="{self._gallery_href(manifest_path, output_dir)}">Open generation manifest</a></p>
    <h2>Reference Images</h2>
    <ul>{reference_links}</ul>
  </header>
  <main>
{sections}
  </main>
</body>
</html>
"""
        gallery_path.write_text(html, encoding="utf-8")
        return gallery_path

    def _gallery_output_section(
        self,
        output: GeneratedPacketOutput,
        output_dir: Path,
    ) -> str:
        title_parts = [output.stage_label or "single"]
        if output.variant_index:
            title_parts.append(f"variant {output.variant_index}")
        title = " / ".join(title_parts)
        slice_items = "\n".join(
            "          "
            f'<div class="slice"><a href="{self._gallery_href(path, output_dir)}">'
            f'<img src="{self._gallery_href(path, output_dir)}" alt="{escape(path.name)}"></a>'
            f'<div class="caption">{escape(path.name)}</div></div>'
            for path in output.slices
        ) or "          <p>No slices were written for this output.</p>"
        return f"""    <section class="output">
      <h2>{escape(title)} ({escape(output.layout_name)})</h2>
      <div class="grid">
        <div class="raw">
          <a href="{self._gallery_href(output.raw_image, output_dir)}">
            <img src="{self._gallery_href(output.raw_image, output_dir)}" alt="{escape(title)} raw atlas">
          </a>
          <div class="caption">{escape(output.raw_image.name)}</div>
        </div>
        <div>
          <div class="slices">
{slice_items}
          </div>
        </div>
      </div>
      <details>
        <summary>Prompt</summary>
        <div class="prompt">{escape(output.prompt)}</div>
      </details>
    </section>"""

    def _gallery_href(self, path: Path, output_dir: Path) -> str:
        try:
            relative = path.relative_to(output_dir)
        except ValueError:
            relative = path
        return quote(relative.as_posix())
