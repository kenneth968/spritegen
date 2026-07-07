"""Tests for the top provider bar widget."""

from __future__ import annotations

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


def _qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_provider_bar_chip_status_for_mock(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    # Default provider after skip is mock
    window._set_combo_value(window.image_provider_combo, "mock")
    window._on_image_provider_changed()
    window._refresh_provider_chip()
    app.processEvents()
    assert window.provider_bar.provider_chip.property("providerStatus") == "mock"
    assert "Mock" in window.provider_bar.provider_chip.text()
    window.close()
    app.processEvents()


def test_provider_bar_chip_status_for_pollinations(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window._set_combo_value(window.image_provider_combo, "pollinations")
    window._on_image_provider_changed()
    window._refresh_provider_chip()
    app.processEvents()
    assert window.provider_bar.provider_chip.property("providerStatus") == "free"
    assert "Pollinations" in window.provider_bar.provider_chip.text()
    assert "No key needed" in window.provider_bar.provider_chip.text()
    window.close()
    app.processEvents()


def test_provider_bar_chip_status_for_keyed_provider_with_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window._set_combo_value(window.image_provider_combo, "openrouter")
    window._on_image_provider_changed()
    window.image_api_key_edit.setText("sk-or-test")
    window._refresh_provider_chip()
    app.processEvents()
    assert window.provider_bar.provider_chip.property("providerStatus") == "ok"
    assert "OpenRouter" in window.provider_bar.provider_chip.text()
    assert "Key loaded" in window.provider_bar.provider_chip.text()
    window.close()
    app.processEvents()


def test_provider_bar_chip_status_for_keyed_provider_missing_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    window._set_combo_value(window.image_provider_combo, "openai")
    window._on_image_provider_changed()
    window.image_api_key_edit.clear()
    window._refresh_provider_chip()
    app.processEvents()
    assert window.provider_bar.provider_chip.property("providerStatus") == "missing"
    assert "OpenAI" in window.provider_bar.provider_chip.text()
    assert "Key missing" in window.provider_bar.provider_chip.text()
    window.close()
    app.processEvents()


def test_provider_bar_click_opens_settings_drawer(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettings, UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    settings_store = UserSettingsStore(tmp_path / "settings.json")
    settings_store.save(UserSettings(has_seen_welcome=True, image_provider="mock"))
    app = _qapp()
    window = MainWindow(settings_store=settings_store)
    assert window.settings_drawer.isHidden()
    window.provider_bar.provider_chip.click()
    app.processEvents()
    assert not window.settings_drawer.isHidden()
    window.close()
    app.processEvents()
