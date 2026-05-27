"""Reusable image atlas layouts for game assets.

Layouts describe where generated sub-assets live inside a larger image. They
let the prompt builder ask for a precise composition and let the slicer cut the
result back into game-ready files.
"""

from __future__ import annotations

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
