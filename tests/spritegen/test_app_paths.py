from __future__ import annotations

from pathlib import Path

import pytest


def test_default_project_root_is_independent_of_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from spritegen.ui.app_paths import default_project_root

    documents = tmp_path / "Documents"
    first_cwd = tmp_path / "first"
    second_cwd = tmp_path / "second"
    first_cwd.mkdir()
    second_cwd.mkdir()

    monkeypatch.chdir(first_cwd)
    first = default_project_root(str(documents))
    monkeypatch.chdir(second_cwd)
    second = default_project_root(str(documents))

    assert first == documents / "Spritegen" / "projects"
    assert second == first
    assert first.is_absolute()


def test_default_project_root_falls_back_to_home(tmp_path: Path) -> None:
    from spritegen.ui.app_paths import default_project_root

    assert default_project_root("", home=tmp_path) == tmp_path / "Spritegen" / "projects"


def test_ensure_writable_project_root_creates_and_cleans_probe(tmp_path: Path) -> None:
    from spritegen.ui.app_paths import ensure_writable_project_root

    root = ensure_writable_project_root(tmp_path / "projects")

    assert root.is_dir()
    assert not (root / ".spritegen-write-test").exists()


def test_ensure_writable_project_root_translates_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from spritegen.ui.app_paths import ProjectRootError, ensure_writable_project_root

    original_write_text = Path.write_text

    def deny_probe(path: Path, *args: str, **kwargs: str) -> int:
        if path.name == ".spritegen-write-test":
            raise PermissionError("blocked")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", deny_probe)

    with pytest.raises(ProjectRootError, match="Choose another project folder"):
        ensure_writable_project_root(tmp_path / "blocked")
