"""Top bar with logo, project/asset pills, provider chip, and gear icon."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...provider_models import PROVIDER_LABELS
from ...user_settings import UserSettings


PROVIDER_FREE = "pollinations"
PROVIDER_MOCK = "mock"
KEYED_PROVIDERS = {"openai", "openrouter"}
ENV_VAR_FOR_PROVIDER = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def env_key_for(provider: str) -> str:
    return os.environ.get(ENV_VAR_FOR_PROVIDER.get(provider, ""), "").strip()


def provider_status(provider: str, api_key: str) -> str:
    if provider == PROVIDER_MOCK:
        return "mock"
    if provider == PROVIDER_FREE:
        return "free"
    if env_key_for(provider) or api_key:
        return "ok"
    return "missing"


def provider_chip_text(provider: str, api_key: str) -> str:
    label = PROVIDER_LABELS.get(provider, provider.title())
    status = provider_status(provider, api_key)
    if status == "mock":
        return f"{label} · Placeholder"
    if status == "free":
        return f"{label} · No key needed"
    if status == "ok":
        return f"{label} · Key loaded"
    return f"{label} · Key missing"


class ProviderBar(QWidget):
    """Persistent top bar showing project, asset, and provider status."""

    project_pill_clicked = Signal()
    asset_pill_clicked = Signal()
    settings_clicked = Signal()
    mode_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topBar")
        self._mode = "quick"
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 8, 20, 8)
        outer.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.title_label = QLabel("spritegen")
        self.title_label.setObjectName("topBarTitle")
        self.tagline_label = QLabel("AI sprite sheet generator")
        self.tagline_label.setObjectName("topBarTagline")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.tagline_label)
        outer.addLayout(title_box)

        outer.addSpacing(12)

        self.project_pill = QPushButton("No project")
        self.project_pill.setObjectName("pillButton")
        self.project_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.project_pill.clicked.connect(self.project_pill_clicked.emit)
        outer.addWidget(self.project_pill)

        self.asset_pill = QPushButton("No asset")
        self.asset_pill.setObjectName("pillButton")
        self.asset_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.asset_pill.clicked.connect(self.asset_pill_clicked.emit)
        outer.addWidget(self.asset_pill)

        self.mode_button = QPushButton("Advanced setup")
        self.mode_button.setObjectName("modeButton")
        self.mode_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_button.clicked.connect(self._toggle_mode)
        outer.addWidget(self.mode_button)

        outer.addStretch()

        self.provider_chip = QPushButton("Provider: Mock")
        self.provider_chip.setObjectName("providerChip")
        self.provider_chip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.provider_chip.clicked.connect(self.settings_clicked.emit)
        outer.addWidget(self.provider_chip)

        self.gear_btn = QPushButton("⚙")
        self.gear_btn.setObjectName("iconButton")
        self.gear_btn.setToolTip("Settings")
        self.gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gear_btn.clicked.connect(self.settings_clicked.emit)
        outer.addWidget(self.gear_btn)

    def set_project_label(self, text: str) -> None:
        self.project_pill.setText(f"Project: {text}" if text else "No project")

    def set_asset_label(self, text: str) -> None:
        self.asset_pill.setText(f"Asset: {text}" if text else "No asset")

    def set_provider(self, provider: str, api_key: str) -> None:
        self.provider_chip.setText(provider_chip_text(provider, api_key))
        self.provider_chip.setProperty("providerStatus", provider_status(provider, api_key))
        self.provider_chip.style().unpolish(self.provider_chip)
        self.provider_chip.style().polish(self.provider_chip)

    def set_provider_from_settings(self, settings: UserSettings) -> None:
        provider = settings.image_provider
        api_key = settings.api_key_for(provider)
        self.set_provider(provider, api_key)

    def _toggle_mode(self) -> None:
        mode = "advanced" if self._mode == "quick" else "quick"
        self.set_mode(mode)
        self.mode_requested.emit(mode)

    def set_mode(self, mode: str) -> None:
        if mode not in {"quick", "advanced"}:
            raise ValueError(f"Unknown app mode: {mode}")
        self._mode = mode
        self.mode_button.setText(
            "Quick start" if mode == "advanced" else "Advanced setup"
        )
