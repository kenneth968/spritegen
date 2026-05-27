"""Export generated project assets into engine-friendly folders."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .projects import AssetSpec, ProjectSpec, ProjectStore, slugify


EXPORT_MANIFEST_VERSION = 1
PROJECT_EXPORT_MANIFEST_VERSION = 1


@dataclass
class ExportedFile:
    source: Path
    path: Path
    stage_index: int | None = None
    stage_label: str | None = None
    variant_index: int | None = None
    variant_count: int = 1
    layout_name: str = ""

    def to_dict(self, base_dir: Path) -> dict[str, Any]:
        return {
            "source": str(self.source),
            "file": self.path.relative_to(base_dir).as_posix(),
            "stage_index": self.stage_index,
            "stage_label": self.stage_label,
            "variant_index": self.variant_index,
            "variant_count": self.variant_count,
            "layout_name": self.layout_name,
        }


@dataclass
class ProjectExportResult:
    output_dir: Path
    manifest_path: Path
    sprites: list[ExportedFile] = field(default_factory=list)
    raw_images: list[ExportedFile] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "sprites": [sprite.to_dict(self.output_dir) for sprite in self.sprites],
            "raw_images": [raw.to_dict(self.output_dir) for raw in self.raw_images],
        }


@dataclass
class ProjectPackAsset:
    asset: AssetSpec
    result: ProjectExportResult
    selected_variant: int | None = None

    def to_dict(self, base_dir: Path) -> dict[str, Any]:
        return {
            "asset": self.asset.to_dict(),
            "output_dir": self.result.output_dir.relative_to(base_dir).as_posix(),
            "manifest": self.result.manifest_path.relative_to(base_dir).as_posix(),
            "selected_variant": self.selected_variant,
            "sprites": [sprite.to_dict(base_dir) for sprite in self.result.sprites],
            "raw_images": [raw.to_dict(base_dir) for raw in self.result.raw_images],
        }


@dataclass
class ProjectPackSkippedAsset:
    asset: AssetSpec
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset": self.asset.to_dict(),
            "reason": self.reason,
        }


@dataclass
class ProjectPackExportResult:
    output_dir: Path
    manifest_path: Path
    assets: list[ProjectPackAsset] = field(default_factory=list)
    skipped: list[ProjectPackSkippedAsset] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_dir": str(self.output_dir),
            "manifest_path": str(self.manifest_path),
            "assets": [asset.to_dict(self.output_dir) for asset in self.assets],
            "skipped": [item.to_dict() for item in self.skipped],
        }


class ProjectAssetExporter:
    def __init__(self, store: ProjectStore | None = None) -> None:
        self.store = store or ProjectStore()

    def export_saved_asset(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        output_dir: Path | str | None = None,
        manifest_path: Path | str | None = None,
        include_raw: bool = False,
        variant_index: int | None = None,
    ) -> ProjectExportResult:
        project_slug = project.slug or slugify(project.name)
        asset_slug = asset.slug or slugify(asset.name)
        source_dir = self.store.generated_dir(project_slug) / asset_slug
        manifest = Path(manifest_path) if manifest_path else source_dir / "generation_manifest.json"
        target = (
            Path(output_dir)
            if output_dir
            else self.store.project_dir(project_slug) / "exports" / asset_slug
        )
        return self.export_manifest(
            manifest,
            target,
            include_raw=include_raw,
            variant_index=variant_index,
        )

    def export_project(
        self,
        project: ProjectSpec,
        assets: list[AssetSpec] | None = None,
        output_dir: Path | str | None = None,
        include_raw: bool = False,
        prefer_selected_variant: bool = True,
    ) -> ProjectPackExportResult:
        project_slug = project.slug or slugify(project.name)
        assets = assets if assets is not None else self.store.load_assets(project)
        target = (
            Path(output_dir)
            if output_dir
            else self.store.project_dir(project_slug) / "exports" / "_project_pack"
        )
        target.mkdir(parents=True, exist_ok=True)

        exported_assets: list[ProjectPackAsset] = []
        skipped_assets: list[ProjectPackSkippedAsset] = []
        for asset in sorted(assets, key=lambda item: (item.asset_type, item.name)):
            selected_variant = (
                self._selected_export_variant(project_slug, asset.slug or slugify(asset.name))
                if prefer_selected_variant
                else None
            )
            asset_target = target / "assets" / asset.asset_type / (asset.slug or slugify(asset.name))
            try:
                result = self.export_saved_asset(
                    project=project,
                    asset=asset,
                    output_dir=asset_target,
                    include_raw=include_raw,
                    variant_index=selected_variant,
                )
            except (FileNotFoundError, ValueError) as exc:
                skipped_assets.append(ProjectPackSkippedAsset(asset=asset, reason=str(exc)))
                continue
            exported_assets.append(
                ProjectPackAsset(
                    asset=asset,
                    result=result,
                    selected_variant=selected_variant,
                )
            )

        if not exported_assets:
            raise ValueError("No generated assets were available to export for this project")

        manifest_path = target / "project_export_manifest.json"
        manifest = {
            "version": PROJECT_EXPORT_MANIFEST_VERSION,
            "project": project.to_dict(),
            "include_raw": include_raw,
            "variant_policy": "selected_or_all" if prefer_selected_variant else "all",
            "assets": [asset.to_dict(target) for asset in exported_assets],
            "skipped": [item.to_dict() for item in skipped_assets],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return ProjectPackExportResult(
            output_dir=target,
            manifest_path=manifest_path,
            assets=exported_assets,
            skipped=skipped_assets,
        )

    def export_manifest(
        self,
        manifest_path: Path | str,
        output_dir: Path | str,
        include_raw: bool = False,
        variant_index: int | None = None,
    ) -> ProjectExportResult:
        if variant_index is not None and variant_index < 1:
            raise ValueError("variant_index must be at least 1")
        manifest_path = Path(manifest_path)
        output_dir = Path(output_dir)
        if not manifest_path.exists():
            raise FileNotFoundError(f"Generation manifest not found: {manifest_path}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        source_dir = manifest_path.parent
        sprites_dir = output_dir / "sprites"
        raw_dir = output_dir / "raw"
        sprites_dir.mkdir(parents=True, exist_ok=True)
        if include_raw:
            raw_dir.mkdir(parents=True, exist_ok=True)

        exported_sprites: list[ExportedFile] = []
        exported_raw: list[ExportedFile] = []
        used_names: set[str] = set()

        for output in manifest.get("outputs", []):
            if not isinstance(output, dict):
                continue
            if not self._matches_variant(output, variant_index):
                continue
            export_context = {
                "stage_index": output.get("stage_index"),
                "stage_label": output.get("stage_label"),
                "variant_index": output.get("variant_index"),
                "variant_count": output.get("variant_count") or 1,
                "layout_name": output.get("layout_name") or "",
            }
            for slice_value in output.get("slices", []):
                source = self._resolve_source(slice_value, source_dir)
                if not source:
                    continue
                target = sprites_dir / self._unique_name(source.name, used_names)
                shutil.copy2(source, target)
                exported_sprites.append(ExportedFile(source=source, path=target, **export_context))

            if include_raw:
                raw_source = self._resolve_source(output.get("raw_image"), source_dir)
                if raw_source:
                    raw_target = raw_dir / raw_source.name
                    shutil.copy2(raw_source, raw_target)
                    exported_raw.append(ExportedFile(source=raw_source, path=raw_target, **export_context))

        if not exported_sprites:
            filter_note = f" for variant {variant_index}" if variant_index else ""
            raise ValueError(
                f"No generated slice files were found in {manifest_path}{filter_note}"
            )

        export_manifest_path = output_dir / "asset_export_manifest.json"
        export_manifest = {
            "version": EXPORT_MANIFEST_VERSION,
            "source_manifest": str(manifest_path),
            "project": manifest.get("project", {}),
            "asset": manifest.get("asset", {}),
            "provider": manifest.get("provider"),
            "model": manifest.get("model"),
            "postprocess": manifest.get("postprocess", {}),
            "selected_variant": variant_index,
            "sprites": [sprite.to_dict(output_dir) for sprite in exported_sprites],
            "raw_images": [raw.to_dict(output_dir) for raw in exported_raw],
        }
        export_manifest_path.write_text(json.dumps(export_manifest, indent=2), encoding="utf-8")

        return ProjectExportResult(
            output_dir=output_dir,
            manifest_path=export_manifest_path,
            sprites=exported_sprites,
            raw_images=exported_raw,
        )

    def _matches_variant(self, output: dict[str, Any], variant_index: int | None) -> bool:
        if variant_index is None:
            return True
        output_variant = output.get("variant_index")
        if output_variant is None:
            return variant_index == 1
        return output_variant == variant_index

    def _selected_export_variant(self, project_slug: str, asset_slug: str) -> int | None:
        manifest_path = (
            self.store.project_dir(project_slug)
            / "exports"
            / asset_slug
            / "asset_export_manifest.json"
        )
        if not manifest_path.exists():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        selected = manifest.get("selected_variant")
        return selected if isinstance(selected, int) and selected >= 1 else None

    def _resolve_source(self, value: object, source_dir: Path) -> Path | None:
        if not isinstance(value, str) or not value:
            return None
        path = Path(value)
        if path.exists():
            return path
        if not path.is_absolute():
            path = source_dir / path
        return path if path.exists() else None

    def _unique_name(self, filename: str, used_names: set[str]) -> str:
        if filename not in used_names:
            used_names.add(filename)
            return filename
        path = Path(filename)
        index = 2
        while True:
            candidate = f"{path.stem}_{index}{path.suffix}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
            index += 1
