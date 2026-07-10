from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass(frozen=True, slots=True)
class ProjectRootError(RuntimeError):
    root: Path

    def __str__(self) -> str:
        return f"Spritegen cannot write to {self.root}. Choose another project folder."


def default_project_root(
    documents_location: str | None = None, *, home: Path | None = None
) -> Path:
    location = documents_location
    if location is None:
        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
    base = Path(location) if location else (home or Path.home())
    return (base / "Spritegen" / "projects").expanduser().resolve()


def ensure_writable_project_root(root: Path | str) -> Path:
    resolved = Path(root).expanduser().resolve()
    probe = resolved / ".spritegen-write-test"
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        probe.write_text("spritegen", encoding="utf-8")
    except OSError as exc:
        raise ProjectRootError(resolved) from exc
    try:
        probe.unlink(missing_ok=True)
    except OSError as exc:
        raise ProjectRootError(resolved) from exc
    return resolved
