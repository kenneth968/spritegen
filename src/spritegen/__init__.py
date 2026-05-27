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
    ColorTreatment,
    PostProcessSettings,
    ProjectSpec,
    ProjectStore,
    PromptPlanner,
    apply_asset_type_enhancement,
    apply_project_enhancement,
)
from .enhancement import PromptEnhancer
from .provider_models import (
    IMAGE_ROLE,
    MODEL_ROLES,
    PROMPT_ROLE,
    ModelSuggestion,
    default_model,
    model_source_urls,
    model_suggestions,
)
from .project_export import ProjectAssetExporter, ProjectExportResult
from .project_generation import ProjectAssetGenerator, ProjectGenerationResult
from .workflow_presets import WorkflowPreset, get_workflow_preset, list_workflow_presets
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
    "ColorTreatment",
    "PostProcessSettings",
    "ProjectSpec",
    "ProjectStore",
    "PromptPlanner",
    "apply_asset_type_enhancement",
    "apply_project_enhancement",
    "PromptEnhancer",
    "IMAGE_ROLE",
    "MODEL_ROLES",
    "PROMPT_ROLE",
    "ModelSuggestion",
    "default_model",
    "model_source_urls",
    "model_suggestions",
    "ProjectAssetExporter",
    "ProjectExportResult",
    "ProjectAssetGenerator",
    "ProjectGenerationResult",
    "WorkflowPreset",
    "get_workflow_preset",
    "list_workflow_presets",
    "create_mycomed_style",
    "mycomed",
]
