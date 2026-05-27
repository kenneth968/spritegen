"""Smoke tests for the desktop project workflow."""

from __future__ import annotations

import os

import pytest


def test_main_window_saves_project_plan(tmp_path):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")

    from PySide6.QtWidgets import QApplication
    from spritegen.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.project_root_edit.setText(str(tmp_path / "projects"))
    window.project_name_edit.setText("MyceliumTD")
    window.asset_name_edit.setText("Puffball")

    project, asset = window._save_current_specs()

    assert project.slug == "myceliumtd"
    assert asset.slug == "puffball"
    assert (tmp_path / "projects" / "myceliumtd" / "project.json").exists()
    assert (tmp_path / "projects" / "myceliumtd" / "assets" / "puffball.json").exists()

    window.close()
    app.processEvents()
