"""Local desktop settings that stay outside project files."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SETTINGS_SCHEMA_VERSION = 3


def default_settings_path() -> Path:
    override = os.environ.get("SPRITEGEN_SETTINGS_PATH")
    if override:
        return Path(override)
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "spritegen" / "settings.json"
    return Path.home() / ".spritegen" / "settings.json"


@dataclass
class UserSettings:
    image_provider: str = "mock"
    image_model: str = "mock"
    prompt_provider: str = "mock"
    prompt_model: str = "mock"
    shared_provider_setup: bool = True
    api_keys: dict[str, str] = field(default_factory=dict)
    has_seen_welcome: bool = False
    last_starter_key: str = ""
    project_root: str = ""

    def api_key_for(self, provider: str) -> str:
        return self.api_keys.get(provider, "")

    def set_api_key(self, provider: str, api_key: str) -> None:
        key = api_key.strip()
        if key:
            self.api_keys[provider] = key
        else:
            self.api_keys.pop(provider, None)

    def clear_api_keys(self) -> None:
        self.api_keys.clear()

    def mark_welcome_seen(self) -> None:
        self.has_seen_welcome = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SETTINGS_SCHEMA_VERSION,
            "image_provider": self.image_provider,
            "image_model": self.image_model,
            "prompt_provider": self.prompt_provider,
            "prompt_model": self.prompt_model,
            "shared_provider_setup": self.shared_provider_setup,
            "api_keys": dict(self.api_keys),
            "has_seen_welcome": self.has_seen_welcome,
            "last_starter_key": self.last_starter_key,
            "project_root": self.project_root,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserSettings":
        version = data.get("version")
        if version not in (1, 2, SETTINGS_SCHEMA_VERSION):
            return cls()
        api_keys = {
            str(provider): str(api_key)
            for provider, api_key in data.get("api_keys", {}).items()
            if api_key
        }
        image_provider = str(data.get("image_provider") or "mock")
        prompt_provider = str(data.get("prompt_provider") or "mock")
        raw_shared_setup = data.get("shared_provider_setup")
        shared_provider_setup = (
            image_provider == prompt_provider
            if raw_shared_setup is None
            else bool(raw_shared_setup)
        )
        return cls(
            image_provider=image_provider,
            image_model=str(data.get("image_model") or "mock"),
            prompt_provider=prompt_provider,
            prompt_model=str(data.get("prompt_model") or "mock"),
            shared_provider_setup=shared_provider_setup,
            api_keys=api_keys,
            has_seen_welcome=bool(data.get("has_seen_welcome", False)),
            last_starter_key=str(data.get("last_starter_key") or ""),
            project_root=str(data.get("project_root") or ""),
        )


class UserSettingsStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else default_settings_path()

    def load(self) -> UserSettings:
        if not self.path.exists():
            return UserSettings()
        try:
            return UserSettings.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return UserSettings()

    def save(self, settings: UserSettings) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
        if os.name != "nt":
            try:
                self.path.chmod(0o600)
            except OSError:
                pass
        return self.path
