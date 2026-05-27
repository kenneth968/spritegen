"""Data models for sprite generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import SheetLayout


@dataclass
class SpriteMetadata:
    name: str
    sprite_index: int
    position: tuple[int, int]
    size: tuple[int, int]
    prompt: str
    style_seed: str | None = None


@dataclass
class GeneratedSheet:
    image_data: bytes
    layout: SheetLayout
    sprites: list[SpriteMetadata]
    style_seed: str
    generation_params: dict

    @property
    def width(self) -> int:
        return self.layout.cell_width * self.layout.columns

    @property
    def height(self) -> int:
        return self.layout.cell_height * self.layout.rows

    def save_sheet(self, path: Path) -> None:
        path.write_bytes(self.image_data)

    def get_sprite_region(self, index: int) -> tuple[int, int, int, int]:
        meta = self.sprites[index]
        x, y = meta.position
        w, h = meta.size
        return (x, y, w, h)


@dataclass
class EvolutionChain:
    name: str
    species: str
    stages: list[EvolutionStage]


@dataclass
class EvolutionStage:
    stage_number: int
    name: str
    prompt_suffix: str
    size: tuple[int, int] = (64, 64)
