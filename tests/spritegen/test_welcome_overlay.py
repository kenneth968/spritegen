"""Tests for the welcome overlay and easy-start cards."""

from __future__ import annotations

import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")


def _qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_welcome_overlay_hidden_when_already_seen(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettings, UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = UserSettingsStore(tmp_path / "settings.json")
    store.save(UserSettings(has_seen_welcome=True, image_provider="mock"))

    app = _qapp()
    window = MainWindow(settings_store=store)

    assert window.welcome_overlay.isHidden() is True
    window.close()
    app.processEvents()


def test_welcome_overlay_shown_on_first_run(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))

    assert window.welcome_overlay.isHidden() is False
    window.close()
    app.processEvents()


def test_welcome_pollinations_dismisses_and_picks_provider(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    app = _qapp()
    window = MainWindow(settings_store=UserSettingsStore(tmp_path / "settings.json"))
    assert window.welcome_overlay.isHidden() is False

    # Simulate clicking the Pollinations card
    window.welcome_pollinations()
    app.processEvents()

    assert window.welcome_overlay.isHidden() is True
    assert window.image_provider_combo.currentData() == "pollinations"
    assert window._user_settings.has_seen_welcome is True
    # Pollinations is a no-key provider, so chip should say "No key needed"
    chip_text = window.provider_bar.provider_chip.text()
    assert "Pollinations" in chip_text
    assert "No key needed" in chip_text
    window.close()
    app.processEvents()


def test_welcome_openrouter_saves_key_and_dismisses(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = UserSettingsStore(tmp_path / "settings.json")
    app = _qapp()
    window = MainWindow(settings_store=store)

    window.welcome_openrouter("sk-or-test-key")
    app.processEvents()

    assert window.welcome_overlay.isHidden() is True
    assert window.image_provider_combo.currentData() == "openrouter"
    assert window._user_settings.api_key_for("openrouter") == "sk-or-test-key"
    assert "OpenRouter" in window.provider_bar.provider_chip.text()
    assert "Key loaded" in window.provider_bar.provider_chip.text()
    window.close()
    app.processEvents()


def test_welcome_openai_saves_key_and_dismisses(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = UserSettingsStore(tmp_path / "settings.json")
    app = _qapp()
    window = MainWindow(settings_store=store)

    window.welcome_openai("sk-test-openai-key")
    app.processEvents()

    assert window.welcome_overlay.isHidden() is True
    assert window.image_provider_combo.currentData() == "openai"
    assert window._user_settings.api_key_for("openai") == "sk-test-openai-key"
    assert "OpenAI" in window.provider_bar.provider_chip.text()
    assert "Key loaded" in window.provider_bar.provider_chip.text()
    window.close()
    app.processEvents()


def test_welcome_skip_marks_seen(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = UserSettingsStore(tmp_path / "settings.json")
    app = _qapp()
    window = MainWindow(settings_store=store)

    window._welcome_skip()
    app.processEvents()

    assert window.welcome_overlay.isHidden() is True
    assert store.load().has_seen_welcome is True
    window.close()
    app.processEvents()


def test_env_var_openai_key_auto_configures_on_first_run(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key-12345")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = UserSettingsStore(tmp_path / "settings.json")
    app = _qapp()
    window = MainWindow(settings_store=store)

    # Should auto-pick up the env var and NOT show the welcome overlay
    assert window.welcome_overlay.isHidden() is True
    assert window.image_provider_combo.currentData() == "openai"
    assert "OpenAI" in window.provider_bar.provider_chip.text()
    assert "Key loaded" in window.provider_bar.provider_chip.text()
    assert store.load().has_seen_welcome is True
    window.close()
    app.processEvents()


def test_env_var_openrouter_key_auto_configures_on_first_run(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-env-12345")

    from spritegen.user_settings import UserSettingsStore
    from spritegen.ui.main_window import MainWindow

    store = UserSettingsStore(tmp_path / "settings.json")
    app = _qapp()
    window = MainWindow(settings_store=store)

    assert window.welcome_overlay.isHidden() is True
    assert window.image_provider_combo.currentData() == "openrouter"
    assert "OpenRouter" in window.provider_bar.provider_chip.text()
    window.close()
    app.processEvents()
