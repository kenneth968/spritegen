"""Style consistency manager for sprite generation.

Maintains consistent style across sprite generations using style seeds
and prompt templates. A style captures visual characteristics like:
- Color palette
- Line weight and style
- shading approach
- Overall aesthetic

Usage:
    manager = StyleManager()
    manager.create_style("my_towers", base_prompt="pixel art, 64x64, crisp edges")
    style = manager.load("my_towers")

    generator = SpriteGenerator(style=style)
"""

from __future__ import annotations

import hashlib
import json
import random
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


STYLE_DIR = Path("styles")
STYLE_FILE_VERSION = 1


@dataclass
class StylePreset:
    name: str
    base_prompt: str
    negative_prompt: str
    color_palette: list[str]
    visual_tags: list[str]
    seed: str
    generation_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": STYLE_FILE_VERSION,
            "name": self.name,
            "base_prompt": self.base_prompt,
            "negative_prompt": self.negative_prompt,
            "color_palette": self.color_palette,
            "visual_tags": self.visual_tags,
            "seed": self.seed,
            "generation_count": self.generation_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StylePreset:
        if data.get("version") != STYLE_FILE_VERSION:
            raise ValueError(f"Incompatible style version: {data.get('version')}")
        return cls(
            name=data["name"],
            base_prompt=data["base_prompt"],
            negative_prompt=data["negative_prompt"],
            color_palette=data["color_palette"],
            visual_tags=data["visual_tags"],
            seed=data["seed"],
            generation_count=data.get("generation_count", 0),
            metadata=data.get("metadata", {}),
        )


class StyleManager:
    def __init__(self, style_dir: Path | None = None) -> None:
        self.style_dir = style_dir or STYLE_DIR
        self._styles: dict[str, StylePreset] = {}
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        self.style_dir.mkdir(parents=True, exist_ok=True)

    def _style_path(self, name: str) -> Path:
        safe = name.replace("/", "_").replace("\\", "_").replace("..", "_")
        return self.style_dir / f"{safe}.json"

    def _generate_seed(self) -> str:
        chars = string.ascii_lowercase + string.digits
        return "".join(random.choice(chars) for _ in range(16))

    def _compute_seed_hash(self, seed: str, prompt: str) -> str:
        combined = f"{seed}:{prompt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:8]

    def create_style(
        self,
        name: str,
        base_prompt: str,
        negative_prompt: str = "",
        color_palette: list[str] | None = None,
        visual_tags: list[str] | None = None,
        seed: str | None = None,
    ) -> StylePreset:
        style = StylePreset(
            name=name,
            base_prompt=base_prompt,
            negative_prompt=negative_prompt,
            color_palette=color_palette or [],
            visual_tags=visual_tags or [],
            seed=seed or self._generate_seed(),
        )
        self._styles[name] = style
        self.save_style(style)
        return style

    def save_style(self, style: StylePreset) -> None:
        path = self._style_path(style.name)
        path.write_text(json.dumps(style.to_dict(), indent=2), encoding="utf-8")

    def load(self, name: str) -> StylePreset | None:
        if name in self._styles:
            return self._styles[name]

        path = self._style_path(name)
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        style = StylePreset.from_dict(data)
        self._styles[name] = style
        return style

    def exists(self, name: str) -> bool:
        return self._style_path(name).exists() or name in self._styles

    def delete(self, name: str) -> bool:
        path = self._style_path(name)
        if path.exists():
            path.unlink()
        if name in self._styles:
            del self._styles[name]
        return True

    def build_prompt(
        self,
        style: StylePreset,
        subject_prompt: str,
        include_style_tags: bool = True,
    ) -> str:
        parts = [subject_prompt]
        if include_style_tags:
            parts.append(style.base_prompt)
            if style.color_palette:
                palette_str = ", ".join(style.color_palette[:5])
                parts.append(f"colors: {palette_str}")
        return " | ".join(parts)

    def build_negative_prompt(self, style: StylePreset) -> str:
        negatives = [style.negative_prompt] if style.negative_prompt else []
        negatives.extend(
            [
                "blurry",
                "low quality",
                "distorted",
                "watermark",
                "signature",
            ]
        )
        return ", ".join(negatives)

    def get_generation_seed(self, style: StylePreset, prompt: str) -> str:
        return self._compute_seed_hash(style.seed, prompt)

    def record_generation(self, name: str) -> None:
        style = self.load(name)
        if style:
            style.generation_count += 1
            self.save_style(style)


PRESET_STYLES = {
    "pixel_art": StylePreset(
        name="pixel_art",
        base_prompt="pixel art, 8-bit style, crisp pixel edges, video game sprite",
        negative_prompt="photorealistic, blurry, anti-aliased, smooth gradients",
        color_palette=["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF"],
        visual_tags=["pixel", "retro", "game"],
        seed="pixel_default",
    ),
    "handdrawn": StylePreset(
        name="handdrawn",
        base_prompt="hand-drawn illustration, cartoon style, clean lines, vector art",
        negative_prompt="photorealistic, 3D render, photographic",
        color_palette=["#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6"],
        visual_tags=["cartoon", "illustration", "hand-drawn"],
        seed="handdrawn_default",
    ),
    "lowpoly": StylePreset(
        name="lowpoly",
        base_prompt="low poly 3D render, flat shading, geometric, game asset",
        negative_prompt="high poly, smooth shading, photorealistic, organic curves",
        color_palette=["#1ABC9C", "#3498DB", "#9B59B6", "#E67E22", "#E74C3C"],
        visual_tags=["3D", "geometric", "low-poly"],
        seed="lowpoly_default",
    ),
}
