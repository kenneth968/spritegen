"""Load bundled Markdown guidance for prompt improvement."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


class PromptGuideLibrary:
    """Small loader for Markdown prompt guides used as system instructions."""

    def __init__(self, guide_dir: Path | str | None = None) -> None:
        self.guide_dir = Path(guide_dir) if guide_dir else None

    def load(self, name: str) -> str:
        filename = name if name.endswith(".md") else f"{name}.md"
        if self.guide_dir:
            path = self.guide_dir / filename
            if path.exists():
                return path.read_text(encoding="utf-8").strip()
            return ""

        guide = resources.files("spritegen.prompt_guides").joinpath(filename)
        if guide.is_file():
            return guide.read_text(encoding="utf-8").strip()
        return ""

    def combined(self, names: list[str]) -> str:
        parts = [self.load(name) for name in names]
        return "\n\n".join(part for part in parts if part)
