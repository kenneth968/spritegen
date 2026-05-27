"""Write a browser index for a saved game-asset project."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import Any

from .projects import AssetSpec, ProjectSpec, ProjectStore, slugify


@dataclass
class ProjectGalleryAsset:
    asset: AssetSpec
    asset_json: Path
    prompt_plan: Path | None = None
    generation_manifest: Path | None = None
    asset_gallery: Path | None = None
    export_manifest: Path | None = None
    thumbnail: Path | None = None
    output_count: int = 0
    slice_count: int = 0
    variant_count: int = 1
    selected_variant: int | None = None
    provider: str = ""
    model: str = ""
    references: list[Path] = field(default_factory=list)


class ProjectGalleryWriter:
    """Create a human-readable project overview that opens directly in a browser."""

    def __init__(self, store: ProjectStore | None = None) -> None:
        self.store = store or ProjectStore()

    def write(
        self,
        project: ProjectSpec,
        assets: list[AssetSpec] | None = None,
    ) -> Path:
        project_slug = project.slug or slugify(project.name)
        project_dir = self.store.project_dir(project_slug)
        project_dir.mkdir(parents=True, exist_ok=True)
        assets = assets if assets is not None else self.store.load_assets(project)
        gallery_assets = [
            self._asset_view(project_slug, asset)
            for asset in sorted(assets, key=lambda item: (item.asset_type, item.name))
        ]
        gallery_path = project_dir / "project_gallery.html"
        gallery_path.write_text(
            self._html(project=project, project_dir=project_dir, assets=gallery_assets),
            encoding="utf-8",
        )
        return gallery_path

    def _asset_view(self, project_slug: str, asset: AssetSpec) -> ProjectGalleryAsset:
        project_dir = self.store.project_dir(project_slug)
        asset_slug = asset.slug or slugify(asset.name)
        asset_json = self.store.asset_dir(project_slug) / f"{asset_slug}.json"
        prompt_plan = project_dir / "prompt_plans" / f"{asset_slug}.json"
        output_dir = self.store.generated_dir(project_slug) / asset_slug
        generation_manifest = output_dir / "generation_manifest.json"
        asset_gallery = output_dir / "asset_gallery.html"
        export_manifest = project_dir / "exports" / asset_slug / "asset_export_manifest.json"

        view = ProjectGalleryAsset(
            asset=asset,
            asset_json=asset_json,
            prompt_plan=prompt_plan if prompt_plan.exists() else None,
            generation_manifest=generation_manifest if generation_manifest.exists() else None,
            asset_gallery=asset_gallery if asset_gallery.exists() else None,
            export_manifest=export_manifest if export_manifest.exists() else None,
        )
        if view.generation_manifest:
            self._apply_generation_manifest(view, view.generation_manifest)
        if view.export_manifest:
            self._apply_export_manifest(view, view.export_manifest)
        return view

    def _apply_generation_manifest(
        self,
        view: ProjectGalleryAsset,
        manifest_path: Path,
    ) -> None:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        view.provider = str(manifest.get("provider") or "")
        view.model = str(manifest.get("model") or "")
        view.variant_count = int(manifest.get("variants_per_packet") or 1)
        view.references = [
            path
            for value in manifest.get("reference_images", [])
            if (path := self._resolve_path(value, manifest_path.parent)) is not None
        ]
        outputs = [item for item in manifest.get("outputs", []) if isinstance(item, dict)]
        view.output_count = len(outputs)
        for output in outputs:
            view.slice_count += len([item for item in output.get("slices", []) if item])
            if view.thumbnail is None:
                view.thumbnail = self._first_existing_path(
                    [*output.get("slices", []), output.get("raw_image")],
                    manifest_path.parent,
                )

    def _apply_export_manifest(
        self,
        view: ProjectGalleryAsset,
        manifest_path: Path,
    ) -> None:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        selected = manifest.get("selected_variant")
        view.selected_variant = selected if isinstance(selected, int) and selected >= 1 else None
        if view.thumbnail is None:
            sprites = manifest.get("sprites", [])
            if sprites and isinstance(sprites[0], dict):
                view.thumbnail = self._resolve_path(sprites[0].get("file"), manifest_path.parent)

    def _first_existing_path(self, values: list[Any], base_dir: Path) -> Path | None:
        for value in values:
            path = self._resolve_path(value, base_dir)
            if path:
                return path
        return None

    def _resolve_path(self, value: object, base_dir: Path) -> Path | None:
        if not isinstance(value, str) or not value:
            return None
        path = Path(value)
        if path.exists():
            return path
        if not path.is_absolute():
            path = base_dir / path
        return path if path.exists() else None

    def _html(
        self,
        project: ProjectSpec,
        project_dir: Path,
        assets: list[ProjectGalleryAsset],
    ) -> str:
        palette = "\n".join(self._palette_swatch(color) for color in project.palette)
        asset_cards = "\n".join(self._asset_card(project_dir, item) for item in assets)
        if not asset_cards:
            asset_cards = '<p class="empty">No saved assets yet.</p>'
        project_json = self._href(self.store.project_path(project.slug or slugify(project.name)), project_dir)
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(project.name)} project gallery</title>
  <style>
    :root {{ color-scheme: light; }}
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; color: #18212f; }}
    header {{ border-bottom: 1px solid #d7dee8; padding-bottom: 18px; margin-bottom: 22px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 0 0 12px; font-size: 19px; }}
    p {{ max-width: 920px; line-height: 1.45; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
    .pill {{ border: 1px solid #b9c4d0; border-radius: 999px; padding: 4px 10px; font-size: 13px; }}
    .palette {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
    .swatch {{ width: 34px; height: 24px; border: 1px solid #aab5c2; border-radius: 4px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }}
    .asset {{ border: 1px solid #d7dee8; border-radius: 8px; padding: 14px; background: #ffffff; }}
    .thumb {{ height: 190px; display: grid; place-items: center; background: #eef2f7; margin-bottom: 12px; }}
    .thumb img {{ max-width: 100%; max-height: 190px; object-fit: contain; }}
    .empty-thumb {{ color: #65758b; font-size: 13px; }}
    .caption {{ color: #52606d; font-size: 13px; margin: 4px 0; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    a {{ color: #155e75; }}
    .links a {{ border: 1px solid #bfd0dc; border-radius: 999px; padding: 4px 9px; text-decoration: none; font-size: 13px; }}
    .prompt {{ white-space: pre-wrap; background: #f5f7fa; padding: 10px; margin-top: 10px; font-size: 13px; }}
    .empty {{ color: #65758b; }}
    @media (max-width: 760px) {{ body {{ margin: 14px; }} .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(project.name)}</h1>
    <p>{escape(project.summary)}</p>
    <p>{escape(project.shared_context)}</p>
    <div class="meta">
      <span class="pill">Style: {escape(project.visual_style or "unspecified")}</span>
      <span class="pill">Color: {escape(project.color_treatment.mode)}</span>
      <span class="pill">Assets: {len(assets)}</span>
      <span class="pill">Image: {escape(project.provider_defaults.image_provider)} / {escape(project.provider_defaults.image_model)}</span>
      <span class="pill">Prompt: {escape(project.provider_defaults.prompt_provider)} / {escape(project.provider_defaults.prompt_model)}</span>
    </div>
    <div class="palette">{palette}</div>
    <p><a href="{project_json}">Project JSON</a></p>
  </header>
  <main>
    <h2>Assets</h2>
    <section class="grid">
      {asset_cards}
    </section>
  </main>
</body>
</html>
"""

    def _asset_card(self, project_dir: Path, item: ProjectGalleryAsset) -> str:
        asset = item.asset
        thumb = self._thumbnail_html(project_dir, item.thumbnail)
        links = self._asset_links(project_dir, item)
        selected = f"selected variant {item.selected_variant}" if item.selected_variant else "all variants"
        references = f"{len(item.references)} reference(s)" if item.references else "no visual references"
        provider = (
            f"{escape(item.provider)} / {escape(item.model)}"
            if item.provider or item.model
            else "not generated yet"
        )
        prompt = escape(asset.enhanced_prompt or asset.description or "No prompt summary yet.")
        details = f'<div class="caption">{escape(asset.details)}</div>' if asset.details else ""
        return f"""<article class="asset">
  {thumb}
  <h2>{escape(asset.name)}</h2>
  <div class="caption">Type: {escape(asset.asset_type)} | Layout: {escape(asset.layout or "default")}</div>
  {details}
  <div class="meta">
    <span class="pill">{item.output_count} output(s)</span>
    <span class="pill">{item.slice_count} slice(s)</span>
    <span class="pill">{item.variant_count} variant(s)</span>
    <span class="pill">{escape(selected)}</span>
    <span class="pill">{escape(references)}</span>
  </div>
  <div class="caption">Generated with: {provider}</div>
  <div class="prompt">{prompt}</div>
  <div class="links">{links}</div>
</article>"""

    def _thumbnail_html(self, project_dir: Path, thumbnail: Path | None) -> str:
        if thumbnail is None:
            return '<div class="thumb"><span class="empty-thumb">No generated preview</span></div>'
        return (
            '<div class="thumb">'
            f'<a href="{self._href(thumbnail, project_dir)}">'
            f'<img src="{self._href(thumbnail, project_dir)}" alt="Generated asset preview">'
            "</a></div>"
        )

    def _asset_links(self, project_dir: Path, item: ProjectGalleryAsset) -> str:
        links = [
            ("Asset JSON", item.asset_json),
            ("Prompt Plan", item.prompt_plan),
            ("Run Gallery", item.asset_gallery),
            ("Generation Manifest", item.generation_manifest),
            ("Export Manifest", item.export_manifest),
        ]
        links.extend(
            (f"Reference {index}", path)
            for index, path in enumerate(item.references, start=1)
        )
        return "\n".join(
            f'<a href="{self._href(path, project_dir)}">{escape(label)}</a>'
            for label, path in links
            if path is not None and path.exists()
        )

    def _palette_swatch(self, color: str) -> str:
        clean = color.strip()
        if not clean:
            return ""
        return f'<span class="swatch" title="{escape(clean)}" style="background:{escape(clean)}"></span>'

    def _href(self, path: Path, base_dir: Path) -> str:
        try:
            return path.relative_to(base_dir).as_posix()
        except ValueError:
            return path.as_posix()
