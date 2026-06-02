"""Reusable image atlas layouts for game assets.

Layouts describe where generated sub-assets live inside a larger image. They
let the prompt builder ask for a precise composition and let the slicer cut the
result back into game-ready files.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayoutRegion:
    name: str
    x: int
    y: int
    width: int
    height: int
    prompt_role: str = ""
    remove_background: bool = True

    def validate(self, canvas_width: int, canvas_height: int) -> list[str]:
        errors: list[str] = []
        if self.width <= 0 or self.height <= 0:
            errors.append(f"Region '{self.name}' must have positive dimensions")
        if self.x < 0 or self.y < 0:
            errors.append(f"Region '{self.name}' cannot start outside the canvas")
        if self.x + self.width > canvas_width or self.y + self.height > canvas_height:
            errors.append(f"Region '{self.name}' exceeds the canvas bounds")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "prompt_role": self.prompt_role,
            "remove_background": self.remove_background,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LayoutRegion":
        return cls(
            name=data["name"],
            x=int(data["x"]),
            y=int(data["y"]),
            width=int(data["width"]),
            height=int(data["height"]),
            prompt_role=data.get("prompt_role", ""),
            remove_background=bool(data.get("remove_background", True)),
        )


@dataclass
class AssetLayout:
    name: str
    width: int
    height: int
    regions: list[LayoutRegion] = field(default_factory=list)
    prompt_instructions: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.width <= 0 or self.height <= 0:
            errors.append("Layout canvas must have positive dimensions")

        seen: set[str] = set()
        for region in self.regions:
            if region.name in seen:
                errors.append(f"Duplicate layout region name: {region.name}")
            seen.add(region.name)
            errors.extend(region.validate(self.width, self.height))
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "regions": [region.to_dict() for region in self.regions],
            "prompt_instructions": self.prompt_instructions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetLayout":
        return cls(
            name=data["name"],
            width=int(data["width"]),
            height=int(data["height"]),
            regions=[LayoutRegion.from_dict(r) for r in data.get("regions", [])],
            prompt_instructions=data.get("prompt_instructions", ""),
        )

    @classmethod
    def single_sprite(cls, width: int = 1024, height: int = 1024) -> "AssetLayout":
        return cls(
            name="single_sprite",
            width=width,
            height=height,
            regions=[
                LayoutRegion(
                    name="sprite",
                    x=0,
                    y=0,
                    width=width,
                    height=height,
                    prompt_role="single centered asset",
                )
            ],
            prompt_instructions=(
                "Create one isolated game asset centered in the full canvas."
            ),
        )

    @classmethod
    def character_full_plus_8_emotions(cls) -> "AssetLayout":
        emotions = [
            "neutral",
            "happy",
            "angry",
            "sad",
            "surprised",
            "focused",
            "hurt",
            "victory",
        ]
        regions = [
            LayoutRegion(
                name="full_body",
                x=0,
                y=0,
                width=512,
                height=1024,
                prompt_role="full-body character pose",
            )
        ]
        for idx, emotion in enumerate(emotions):
            col = idx % 2
            row = idx // 2
            regions.append(
                LayoutRegion(
                    name=f"head_{emotion}",
                    x=512 + col * 256,
                    y=row * 256,
                    width=256,
                    height=256,
                    prompt_role=f"chibi emotion head, {emotion} expression",
                )
            )

        return cls(
            name="character_full_plus_8_emotions",
            width=1024,
            height=1024,
            regions=regions,
            prompt_instructions=(
                "Create a clean 1024x1024 character atlas. The left 512x1024 "
                "area is one full-body character. The right 512x1024 area is a "
                "2 by 4 grid of eight 256x256 chibi heads of the same character. "
                "Keep hard, straight seams at x=512 and between each 256x256 head "
                "cell so the image can be sliced exactly."
            ),
        )

    @classmethod
    def grid(
        cls,
        name: str,
        width: int,
        height: int,
        rows: int,
        columns: int,
        region_prefix: str = "cell",
    ) -> "AssetLayout":
        cell_w = width // columns
        cell_h = height // rows
        regions: list[LayoutRegion] = []
        for idx in range(rows * columns):
            row = idx // columns
            col = idx % columns
            regions.append(
                LayoutRegion(
                    name=f"{region_prefix}_{idx + 1}",
                    x=col * cell_w,
                    y=row * cell_h,
                    width=cell_w,
                    height=cell_h,
                    prompt_role=f"grid cell {idx + 1}",
                )
            )
        return cls(
            name=name,
            width=width,
            height=height,
            regions=regions,
            prompt_instructions=(
                f"Create a clean {columns} by {rows} atlas with equal cells. "
                "Keep each asset centered in its cell and keep cell seams clean."
            ),
        )

    @classmethod
    def hero_plus_grid(
        cls,
        name: str,
        width: int,
        height: int,
        hero_width: int,
        grid_rows: int,
        grid_columns: int,
        hero_region_name: str = "full_body",
        grid_region_prefix: str = "head",
        hero_side: str = "left",
    ) -> "AssetLayout":
        if hero_side not in {"left", "right"}:
            raise ValueError("hero_side must be left or right")
        if hero_width <= 0 or hero_width >= width:
            raise ValueError("hero_width must be smaller than the canvas width")
        if grid_rows < 1 or grid_columns < 1:
            raise ValueError("Grid rows and columns must be at least 1")

        grid_width = width - hero_width
        if grid_width % grid_columns or height % grid_rows:
            raise ValueError("Remaining grid area must divide evenly by rows and columns")

        hero_name = _layout_token(hero_region_name, "full_body")
        grid_prefix = _layout_token(grid_region_prefix, "cell")
        grid_cell_w = grid_width // grid_columns
        grid_cell_h = height // grid_rows
        hero_x = 0 if hero_side == "left" else width - hero_width
        grid_x = hero_width if hero_side == "left" else 0
        hero_label = "left" if hero_side == "left" else "right"
        grid_label = "right" if hero_side == "left" else "left"

        regions = [
            LayoutRegion(
                name=hero_name,
                x=hero_x,
                y=0,
                width=hero_width,
                height=height,
                prompt_role="large hero character or primary asset region",
            )
        ]
        for idx in range(grid_rows * grid_columns):
            row = idx // grid_columns
            col = idx % grid_columns
            regions.append(
                LayoutRegion(
                    name=f"{grid_prefix}_{idx + 1}",
                    x=grid_x + col * grid_cell_w,
                    y=row * grid_cell_h,
                    width=grid_cell_w,
                    height=grid_cell_h,
                    prompt_role=(
                        f"supporting variant cell {idx + 1}, same identity as "
                        f"{hero_name}"
                    ),
                )
            )

        return cls(
            name=_layout_token(name, "hero_grid"),
            width=width,
            height=height,
            regions=regions,
            prompt_instructions=(
                f"Create a clean {width}x{height} atlas. The {hero_label} "
                f"{hero_width}x{height} hero area is one large full-body or "
                f"primary asset. The {grid_label} {grid_width}x{height} area is "
                f"a {grid_columns} by {grid_rows} grid of {grid_cell_w}x{grid_cell_h} "
                "supporting cells that keep the same identity, costume, materials, "
                "palette, and rendering style as the hero area. Keep hard, straight "
                "seams between every region so the image can be sliced exactly."
            ),
        )


PRESET_LAYOUTS: dict[str, AssetLayout] = {
    "single_sprite": AssetLayout.single_sprite(),
    "character_full_plus_8_emotions": AssetLayout.character_full_plus_8_emotions(),
    "four_stage_grid": AssetLayout.grid(
        name="four_stage_grid",
        width=1024,
        height=1024,
        rows=2,
        columns=2,
        region_prefix="stage",
    ),
}


def get_layout(name: str) -> AssetLayout:
    try:
        return PRESET_LAYOUTS[name]
    except KeyError:
        known = ", ".join(sorted(PRESET_LAYOUTS))
        raise ValueError(f"Unknown layout '{name}'. Available layouts: {known}")


def _layout_token(value: str, fallback: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return token or fallback
