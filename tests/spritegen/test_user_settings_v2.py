from __future__ import annotations

import json


def test_default_settings_have_welcome_false():
    from spritegen.user_settings import UserSettings, UserSettingsStore

    settings = UserSettingsStore("/nonexistent/path/settings.json").load()
    assert settings.has_seen_welcome is False
    assert settings.last_starter_key == ""
    assert isinstance(settings, UserSettings)


def test_round_trip_v3(tmp_path):
    from spritegen.user_settings import UserSettings, UserSettingsStore

    project_root = tmp_path / "projects"
    store = UserSettingsStore(tmp_path / "round_trip.json")
    settings = UserSettings(
        image_provider="openai",
        image_model="gpt-image-2",
        prompt_provider="openai",
        prompt_model="gpt-5.5",
        api_keys={"openai": "sk-test"},
        has_seen_welcome=True,
        last_starter_key="mycelium_td",
        project_root=str(project_root),
    )
    store.save(settings)
    loaded = store.load()
    assert loaded.image_provider == "openai"
    assert loaded.image_model == "gpt-image-2"
    assert loaded.api_key_for("openai") == "sk-test"
    assert loaded.has_seen_welcome is True
    assert loaded.last_starter_key == "mycelium_td"
    assert loaded.project_root == str(project_root)


def test_migrates_v1_settings_without_newer_fields(tmp_path):
    from spritegen.user_settings import UserSettingsStore

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "image_provider": "openrouter",
                "image_model": "google/gemini-3.1-flash-image-preview",
                "prompt_provider": "openrouter",
                "prompt_model": "openai/gpt-5.5",
                "api_keys": {"openrouter": "sk-or-v1"},
            }
        ),
        encoding="utf-8",
    )
    settings = UserSettingsStore(path).load()
    assert settings.image_provider == "openrouter"
    assert settings.api_key_for("openrouter") == "sk-or-v1"
    # New fields default when migrating from v1
    assert settings.has_seen_welcome is False
    assert settings.last_starter_key == ""
    assert settings.project_root == ""


def test_migrates_v2_settings_without_project_root(tmp_path):
    from spritegen.user_settings import UserSettingsStore

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "image_provider": "pollinations",
                "image_model": "flux",
                "prompt_provider": "pollinations",
                "prompt_model": "openai",
            }
        ),
        encoding="utf-8",
    )

    assert UserSettingsStore(path).load().project_root == ""


def test_clear_api_keys(tmp_path):
    from spritegen.user_settings import UserSettings, UserSettingsStore

    store = UserSettingsStore(tmp_path / "settings.json")
    store.save(
        UserSettings(
            image_provider="openai",
            api_keys={"openai": "sk-1", "openrouter": "sk-2"},
        )
    )
    settings = store.load()
    assert settings.api_keys == {"openai": "sk-1", "openrouter": "sk-2"}
    settings.clear_api_keys()
    store.save(settings)
    assert store.load().api_keys == {}


def test_mark_welcome_seen(tmp_path):
    from spritegen.user_settings import UserSettings, UserSettingsStore

    store = UserSettingsStore(tmp_path / "settings.json")
    settings = UserSettings()
    assert settings.has_seen_welcome is False
    settings.mark_welcome_seen()
    store.save(settings)
    assert store.load().has_seen_welcome is True


def test_unknown_version_returns_defaults(tmp_path):
    from spritegen.user_settings import UserSettingsStore

    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"version": 999, "image_provider": "openai"}),
        encoding="utf-8",
    )
    settings = UserSettingsStore(path).load()
    assert settings.image_provider == "mock"  # default
    assert settings.has_seen_welcome is False
