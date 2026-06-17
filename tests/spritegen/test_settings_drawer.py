"""Tests for the right-side settings drawer."""

from __future__ import annotations

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


def _qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_drawer_starts_hidden(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    assert window.settings_drawer.isHidden()
    window.close()
    app.processEvents()


def test_drawer_toggle(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))

    window._open_settings_drawer()
    assert not window.settings_drawer.isHidden()
    window._open_settings_drawer()
    assert window.settings_drawer.isHidden()

    window._open_settings_drawer()
    assert not window.settings_drawer.isHidden()
    window._close_settings_drawer()
    assert window.settings_drawer.isHidden()

    window.close()
    app.processEvents()


def test_drawer_has_five_tabs(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    tab_labels = [
        window.settings_drawer.tabs.tabText(i)
        for i in range(window.settings_drawer.tabs.count())
    ]
    assert tab_labels == ["Project", "Asset", "Layouts", "Providers", "Advanced"]
    window.close()
    app.processEvents()


def test_drawer_opens_providers_tab_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window._open_settings_drawer()
    assert window.settings_drawer.tabs.currentWidget() is not None
    assert window.settings_drawer.tabs.tabText(
        window.settings_drawer.tabs.currentIndex()
    ) == "Providers"
    window.close()
    app.processEvents()


def test_drawer_open_tab_by_name(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window.settings_drawer.open_tab("Asset")
    assert window.settings_drawer.tabs.tabText(
        window.settings_drawer.tabs.currentIndex()
    ) == "Asset"
    window.settings_drawer.open_tab("Layout")
    assert window.settings_drawer.tabs.tabText(
        window.settings_drawer.tabs.currentIndex()
    ) == "Layouts"
    window.close()
    app.processEvents()
