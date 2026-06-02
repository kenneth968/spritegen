"""Configuration for sprite sheet generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class SpriteDefinition:
    name: str
    prompt: str
    index: int = 0


@dataclass
class SheetLayout:
    rows: int = 2
    columns: int = 2
    cell_width: int = 128
    cell_height: int = 128
    padding: int = 0
    margin: int = 0

    @property
    def sprite_count(self) -> int:
        return self.rows * self.columns


@dataclass
class SpriteConfig:
    output_dir: Path = Path("output/sprites")
    sheet_dir: Path = Path("output/sheets")
    sheet_width: int = 512
    sheet_height: int = 512
    sprite_width: int = 128
    sprite_height: int = 128
    transparent_bg: bool = True
    image_format: Literal["png"] = "png"
    api_provider: Literal[
        "openai", "anthropic", "replicate", "mock", "huggingface", "pollinations", "openrouter"
    ] = "openai"
    api_model: str = "dall-e-3"
    api_key: str | None = None
    style_file: Path | None = None

    def get_layout(self, sprite_count: int) -> SheetLayout:
        if sprite_count <= 4:
            rows, cols = 2, 2
        elif sprite_count <= 6:
            rows, cols = 2, 3
        elif sprite_count <= 9:
            rows, cols = 3, 3
        elif sprite_count <= 12:
            rows, cols = 3, 4
        else:
            rows, cols = 4, 4

        cell_w = self.sheet_width // cols
        cell_h = self.sheet_height // rows

        return SheetLayout(
            rows=rows,
            columns=cols,
            cell_width=cell_w,
            cell_height=cell_h,
        )

    def validate(self) -> list[str]:
        errors = []
        if self.sprite_width > self.sheet_width:
            errors.append("sprite_width cannot exceed sheet_width")
        if self.sprite_height > self.sheet_height:
            errors.append("sprite_height cannot exceed sheet_height")
        if self.output_dir and not self.output_dir.exists():
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                errors.append(f"Cannot create output_dir: {e}")
        return errors
