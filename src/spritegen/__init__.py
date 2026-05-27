"""Sprite sheet generation pipeline for game sprites.

Architecture:
1. Generator: Creates sprite sheets using AI image generation
2. Slicer: Post-processes sheets into individual transparent PNGs
3. StyleManager: Maintains style consistency across generations

Usage:
    from spritegen import SpriteGenerator, Slicer, StyleManager

    style = StyleManager.load("mycomed_towers")
    generator = SpriteGenerator(style=style)
    sheet = generator.generate_sheet("puffball_evolution", sprites=4)
    slicer = Slicer(output_dir="output/sprites")
    slicer.slice_and_save(sheet)
"""

__version__ = "0.1.0"

from .config import SpriteConfig, SheetLayout, SpriteDefinition
from .generator import SpriteGenerator, create_mycomed_style
from .slicer import Slicer
from .style import StyleManager
from .models import GeneratedSheet, SpriteMetadata
from .layouts import AssetLayout, LayoutRegion
from .projects import (
    AssetSpec,
    AssetTypeSpec,
    ProjectSpec,
    ProjectStore,
    PromptPlanner,
)
from .enhancement import PromptEnhancer
from .project_generation import ProjectAssetGenerator, ProjectGenerationResult
from . import mycomed

__all__ = [
    "SpriteConfig",
    "SheetLayout",
    "SpriteDefinition",
    "SpriteGenerator",
    "Slicer",
    "StyleManager",
    "GeneratedSheet",
    "SpriteMetadata",
    "AssetLayout",
    "LayoutRegion",
    "AssetSpec",
    "AssetTypeSpec",
    "ProjectSpec",
    "ProjectStore",
    "PromptPlanner",
    "PromptEnhancer",
    "ProjectAssetGenerator",
    "ProjectGenerationResult",
    "create_mycomed_style",
    "mycomed",
]
