"""Post-processing slicer for sprite sheets.

Takes a generated sprite sheet and slices it into individual
transparent PNG sprites for use in game engines.

Usage:
    slicer = Slicer(output_dir="output/sprites")
    slicer.slice_and_save(sheet)

    # Or process manually:
    slicer.extract_sprite(sheet, index=0)
    slicer.save_sprite(sheet, index=0, path="output/sprites/sprite0.png")
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Literal

from .config import SpriteConfig
from .models import GeneratedSheet, SpriteMetadata


try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class SlicerError(Exception):
    pass


class Slicer:
    def __init__(
        self,
        output_dir: Path | str | None = None,
        config: SpriteConfig | None = None,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else Path("output/sprites")
        self.config = config or SpriteConfig()
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_sprite(
        self,
        sheet: GeneratedSheet,
        index: int,
    ) -> Image.Image | None:
        if not HAS_PIL:
            raise SlicerError(
                "PIL/Pillow is required for slicing. Install with: pip install pillow"
            )

        img = Image.open(io.BytesIO(sheet.image_data))

        if img.mode != "RGBA":
            img = img.convert("RGBA")

        sprite_meta = sheet.sprites[index]
        x, y = sprite_meta.position
        w, h = sprite_meta.size

        sprite = img.crop((x, y, x + w, y + h))

        if self.config.transparent_bg:
            sprite = self._make_transparent(sprite)

        return sprite

    def _make_transparent(self, img: Image.Image) -> Image.Image:
        """Remove background using adaptive flood-fill from edges.

        Detects background color by sampling edge pixels (not just corners),
        uses majority-vote to handle dark/light/colored backgrounds, then
        flood-fills from edges. A second pass removes isolated bg-colored
        pixels that weren't connected due to gradients or glow effects.
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        pixels = img.load()
        width, height = img.size

        # Sample background color from ALL edge pixels (much more robust than corners)
        edge_samples = []
        for x in range(width):
            edge_samples.append(pixels[x, 0][:3])
            edge_samples.append(pixels[x, height - 1][:3])
        for y in range(1, height - 1):
            edge_samples.append(pixels[0, y][:3])
            edge_samples.append(pixels[width - 1, y][:3])

        if not edge_samples:
            return img

        # Classify edge pixels as light or dark to handle mixed-bg images
        dark_count = sum(1 for r, g, b in edge_samples if r + g + b < 384)
        light_count = len(edge_samples) - dark_count

        # Use median of the dominant group (more robust than mean against outliers)
        if dark_count > light_count:
            group = sorted(
                [s for s in edge_samples if s[0] + s[1] + s[2] < 384],
                key=lambda s: s[0] + s[1] + s[2],
            )
        else:
            group = sorted(
                [s for s in edge_samples if s[0] + s[1] + s[2] >= 384],
                key=lambda s: s[0] + s[1] + s[2],
            )

        mid = len(group) // 2
        bg_r, bg_g, bg_b = group[mid] if group else (255, 255, 255)

        # Flood-fill from all edge pixels — works for any background color
        tolerance = 65  # Higher tolerance for gradients/glow near edges
        visited = set()
        to_remove = set()
        queue = []

        # Seed from all edge pixels
        for x in range(width):
            queue.append((x, 0))
            queue.append((x, height - 1))
        for y in range(1, height - 1):
            queue.append((0, y))
            queue.append((width - 1, y))

        while queue:
            x, y = queue.pop()
            if (x, y) in visited:
                continue
            if x < 0 or x >= width or y < 0 or y >= height:
                continue
            visited.add((x, y))

            r, g, b, a = pixels[x, y]

            if a < 10:
                to_remove.add((x, y))
                for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                    if (nx, ny) not in visited:
                        queue.append((nx, ny))
                continue

            if (abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)) <= tolerance * 3:
                to_remove.add((x, y))
                for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                    if (nx, ny) not in visited:
                        queue.append((nx, ny))

        # Second pass: soften edges with alpha gradient for pixels near the
        # removal boundary (anti-aliasing). Also catch stray bg-colored pixels
        # that weren't flood-connected (common with glow/particle effects).
        target = img.copy()
        target_pixels = target.load()

        for x, y in to_remove:
            target_pixels[x, y] = (0, 0, 0, 0)

        # Edge-feathering: pixels adjacent to removed ones that are close to bg
        # get partial transparency for smoother cutouts
        feather_tolerance = 40
        for x in range(width):
            for y in range(height):
                if (x, y) in to_remove:
                    continue
                r, g, b, a = target_pixels[x, y]
                if a == 0:
                    continue
                # Check if this pixel borders a removed pixel
                neighbors_removed = 0
                for nx, ny in [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]:
                    if (nx, ny) in to_remove:
                        neighbors_removed += 1
                if neighbors_removed == 0:
                    continue
                # If close to bg color, apply partial transparency
                diff = abs(r - bg_r) + abs(g - bg_g) + abs(b - bg_b)
                if diff <= feather_tolerance * 3:
                    # Scale alpha based on color distance from bg
                    alpha_factor = diff / (feather_tolerance * 3)
                    new_alpha = int(a * alpha_factor)
                    target_pixels[x, y] = (r, g, b, new_alpha)

        return target

    def save_sprite(
        self,
        sheet: GeneratedSheet,
        index: int,
        path: Path | str | None = None,
    ) -> Path:
        if not HAS_PIL:
            raise SlicerError("PIL/Pillow is required for slicing")

        sprite = self.extract_sprite(sheet, index)
        if sprite is None:
            raise SlicerError(f"Failed to extract sprite at index {index}")

        if path is None:
            sprite_meta = sheet.sprites[index]
            path = self.output_dir / f"{sprite_meta.name}.png"

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        sprite.save(str(path), format="PNG")
        return path

    def slice_and_save(
        self,
        sheet: GeneratedSheet,
        prefix: str | None = None,
    ) -> list[Path]:
        saved_paths = []
        for i in range(len(sheet.sprites)):
            sprite_meta = sheet.sprites[i]
            filename = f"{prefix}_{sprite_meta.name}" if prefix else sprite_meta.name
            path = self.output_dir / f"{filename}.png"
            saved = self.save_sprite(sheet, i, path)
            saved_paths.append(saved)

        return saved_paths

    def slice_to_grid(
        self,
        sheet: GeneratedSheet,
        rows: int | None = None,
        cols: int | None = None,
    ) -> list[Image.Image]:
        if not HAS_PIL:
            raise SlicerError("PIL/Pillow is required for slicing")

        rows = rows or sheet.layout.rows
        cols = cols or sheet.layout.columns

        layout = sheet.layout
        sprites: list[Image.Image] = []

        img = Image.open(io.BytesIO(sheet.image_data))
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        for idx in range(min(layout.sprite_count, len(sheet.sprites))):
            row = idx // cols
            col = idx % cols
            x = col * layout.cell_width + layout.margin
            y = row * layout.cell_height + layout.margin
            w = layout.cell_width - layout.padding
            h = layout.cell_height - layout.padding

            sprite = img.crop((x, y, x + w, y + h))
            sprites.append(sprite)

        return sprites

    def save_metadata(
        self,
        sheet: GeneratedSheet,
        path: Path | str | None = None,
    ) -> Path:
        metadata = {
            "style_seed": sheet.style_seed,
            "layout": {
                "rows": sheet.layout.rows,
                "columns": sheet.layout.columns,
                "cell_width": sheet.layout.cell_width,
                "cell_height": sheet.layout.cell_height,
            },
            "sprites": [
                {
                    "name": s.name,
                    "index": s.sprite_index,
                    "position": s.position,
                    "size": s.size,
                    "prompt": s.prompt,
                }
                for s in sheet.sprites
            ],
            "generation_params": sheet.generation_params,
        }

        if path is None:
            path = self.output_dir / "sprite_metadata.json"
        else:
            path = Path(path)

        path.parent.mkdir(parents=True, exist_ok=True)
        import json

        path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return path
