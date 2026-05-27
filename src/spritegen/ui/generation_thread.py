"""Background workers for the desktop project workflow."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..enhancement import PromptEnhancer
from ..project_generation import ProjectAssetGenerator
from ..projects import AssetSpec, ProjectSpec, ProjectStore, PromptPlanner


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

    def run(self) -> None:
        try:
            if self.api_key:
                self._set_provider_key()

            store = ProjectStore(self.project_root)
            known_assets = store.load_assets(self.project)
            self.progress.emit("Building prompt packets...")
            result = ProjectAssetGenerator(store=store).generate(
                project=self.project,
                asset=self.asset,
                known_assets=known_assets,
                provider=self.provider,
                model=self.model,
                output_root=Path(self.output_root),
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))

    def _set_provider_key(self) -> None:
        if self.provider == "openai":
            os.environ["OPENAI_API_KEY"] = self.api_key or ""
        elif self.provider == "openrouter":
            os.environ["OPENROUTER_API_KEY"] = self.api_key or ""
