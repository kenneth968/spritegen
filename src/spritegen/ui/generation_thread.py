"""Background workers for the desktop project workflow."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..enhancement import PromptEnhancer
from ..provider_models import (
    IMAGE_ROLE,
    PROMPT_ROLE,
    discover_model_suggestions,
)
from ..project_generation import ProjectAssetGenerator
from ..projects import AssetSpec, AssetTypeSpec, ProjectSpec, ProjectStore, PromptPlanner


class ModelDiscoveryThread(QThread):
    finished = Signal(object)

    def __init__(
        self,
        image_provider: str,
        prompt_provider: str,
        search: str = "",
        source: str = "auto",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.image_provider = image_provider
        self.prompt_provider = prompt_provider
        self.search = search.strip()
        self.source = source

    def run(self) -> None:
        suggestions = {}
        errors = []
        for role, provider in (
            (IMAGE_ROLE, self.image_provider),
            (PROMPT_ROLE, self.prompt_provider),
        ):
            try:
                discovered = discover_model_suggestions(
                    provider,
                    role,
                    search=self.search,
                    limit=30,
                    source=self.source,
                )
            except Exception as exc:
                errors.append(f"{provider} {role}: {exc}")
                continue
            if discovered:
                suggestions[(role, provider)] = discovered
        self.finished.emit({"suggestions": suggestions, "errors": errors})


class ProjectEnhancementThread(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        project: ProjectSpec,
        provider: str,
        model: str,
        api_key: str | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def run(self) -> None:
        try:
            planner = PromptPlanner()
            result = PromptEnhancer().enhance_json(
                planner.build_project_enhancement_brief(self.project),
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                system_prompt=planner.build_project_enhancement_system_prompt(),
                fallback=planner.project_enhancement_fallback(self.project),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class AssetTypeEnhancementThread(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        project: ProjectSpec,
        asset_type: AssetTypeSpec,
        provider: str,
        model: str,
        api_key: str | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.asset_type = asset_type
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def run(self) -> None:
        try:
            planner = PromptPlanner()
            result = PromptEnhancer().enhance_json(
                planner.build_asset_type_enhancement_brief(self.project, self.asset_type),
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                system_prompt=planner.build_asset_type_enhancement_system_prompt(),
                fallback=planner.asset_type_enhancement_fallback(self.asset_type),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class EnhancementThread(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        project_root: str,
        provider: str,
        model: str,
        api_key: str | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.asset = asset
        self.project_root = project_root
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def run(self) -> None:
        try:
            store = ProjectStore(self.project_root)
            planner = PromptPlanner()
            asset_type = self.project.get_asset_type(self.asset.asset_type)
            known_assets = store.load_assets(self.project)
            brief = planner.build_enhancement_brief(
                self.project,
                asset_type,
                self.asset,
                known_assets,
            )
            enhanced = PromptEnhancer().enhance(
                brief,
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                system_prompt=planner.build_enhancement_system_prompt(
                    self.project,
                    asset_type,
                    self.asset,
                ),
            )
            self.finished.emit(enhanced)
        except Exception as exc:
            self.error.emit(str(exc))


class ProjectGenerationThread(QThread):
    progress = Signal(str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        project: ProjectSpec,
        asset: AssetSpec,
        project_root: str,
        output_root: str,
        provider: str,
        model: str,
        api_key: str | None,
        variants_per_packet: int = 1,
        enhance_before_generate: bool = False,
        prompt_provider: str = "mock",
        prompt_model: str = "mock",
        prompt_api_key: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.project = project
        self.asset = asset
        self.project_root = project_root
        self.output_root = output_root
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.variants_per_packet = variants_per_packet
        self.enhance_before_generate = enhance_before_generate
        self.prompt_provider = prompt_provider
        self.prompt_model = prompt_model
        self.prompt_api_key = prompt_api_key

    def run(self) -> None:
        try:
            store = ProjectStore(self.project_root)
            known_assets = store.load_assets(self.project)
            if self.enhance_before_generate:
                self.progress.emit("Improving asset prompt...")
                planner = PromptPlanner()
                asset_type = self.project.get_asset_type(self.asset.asset_type)
                enhanced = PromptEnhancer().enhance(
                    planner.build_enhancement_brief(
                        self.project,
                        asset_type,
                        self.asset,
                        known_assets,
                    ),
                    provider=self.prompt_provider,
                    model=self.prompt_model,
                    api_key=self.prompt_api_key,
                    system_prompt=planner.build_enhancement_system_prompt(
                        self.project,
                        asset_type,
                        self.asset,
                    ),
                )
                self.asset.enhanced_prompt = enhanced
                store.save_asset(self.project, self.asset)
                known_assets = store.load_assets(self.project)
            self.progress.emit("Building prompt packets...")
            result = ProjectAssetGenerator(store=store).generate(
                project=self.project,
                asset=self.asset,
                known_assets=known_assets,
                provider=self.provider,
                model=self.model,
                api_key=self.api_key,
                output_root=Path(self.output_root),
                variants_per_packet=self.variants_per_packet,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
