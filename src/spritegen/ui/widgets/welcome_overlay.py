"""First-run welcome overlay with three quick-start cards."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...provider_models import IMAGE_ROLE, PROMPT_ROLE, default_model


class WelcomeOverlay(QFrame):
    """Modal-style overlay shown on first run with three quick-start cards."""

    pollinations_clicked = Signal()
    openrouter_clicked = Signal(str)
    openai_clicked = Signal(str)
    open_project_clicked = Signal()
    skip_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("welcomeBackdrop")
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setAlignment(Qt.AlignCenter)

        panel = QFrame()
        panel.setObjectName("welcomePanel")
        panel.setMaximumWidth(960)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(28, 28, 28, 28)
        panel_layout.setSpacing(16)

        title = QLabel("Welcome to spritegen")
        title.setObjectName("welcomeTitle")
        panel_layout.addWidget(title)

        subtitle = QLabel(
            "Generate game-ready AI sprite sheets in a few clicks. "
            "Pick a provider to get started — you can change it any time."
        )
        subtitle.setObjectName("welcomeSubtitle")
        subtitle.setWordWrap(True)
        panel_layout.addWidget(subtitle)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(self._build_pollinations_card(), 1)
        cards_row.addWidget(self._build_openrouter_card(), 1)
        cards_row.addWidget(self._build_openai_card(), 1)
        panel_layout.addLayout(cards_row)

        footer = QHBoxLayout()
        open_btn = QPushButton("Open existing project…")
        open_btn.setObjectName("welcomeSkip")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(self.open_project_clicked.emit)
        skip_btn = QPushButton("Skip, take me to the app")
        skip_btn.setObjectName("welcomeSkip")
        skip_btn.setCursor(Qt.PointingHandCursor)
        skip_btn.clicked.connect(self.skip_clicked.emit)
        footer.addWidget(open_btn)
        footer.addStretch()
        footer.addWidget(skip_btn)
        panel_layout.addLayout(footer)

        outer.addWidget(panel, alignment=Qt.AlignCenter)

    def _build_pollinations_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("welcomeCard")
        card.setProperty("cardStyle", "primary")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        heading = QLabel("Try free with Pollinations")
        heading.setObjectName("welcomeCardTitle")
        layout.addWidget(heading)

        body = QLabel(
            "No signup, no API key. Uses the free Flux image model so you can "
            "generate a real sprite sheet right away."
        )
        body.setObjectName("welcomeCardBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        layout.addStretch()
        button = QPushButton("Start with Pollinations")
        button.setObjectName("welcomeCardButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self.pollinations_clicked.emit)
        layout.addWidget(button)
        return card

    def _build_openrouter_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("welcomeCard")
        card.setProperty("cardStyle", "outline")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        heading = QLabel("Use OpenRouter")
        heading.setObjectName("welcomeCardTitle")
        layout.addWidget(heading)

        body = QLabel(
            "Access many image and prompt models with one key. "
            "Paste your key to connect."
        )
        body.setObjectName("welcomeCardBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        self.openrouter_key_edit = QLineEdit()
        self.openrouter_key_edit.setEchoMode(QLineEdit.Password)
        self.openrouter_key_edit.setPlaceholderText("Paste OpenRouter key (sk-or-…)")
        layout.addWidget(self.openrouter_key_edit)

        link = QLabel('<a href="https://openrouter.ai/keys">Get a key at openrouter.ai/keys</a>')
        link.setOpenExternalLinks(True)
        link.setObjectName("mutedLabel")
        layout.addWidget(link)

        layout.addStretch()
        button = QPushButton("Save and start")
        button.setObjectName("welcomeCardButton")
        button.setProperty("cardStyle", "outline")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self._emit_openrouter)
        layout.addWidget(button)
        return card

    def _build_openai_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("welcomeCard")
        card.setProperty("cardStyle", "outline")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        heading = QLabel("Use OpenAI")
        heading.setObjectName("welcomeCardTitle")
        layout.addWidget(heading)

        body = QLabel(
            "Use DALL-E and GPT image models. Paste your OpenAI key to connect."
        )
        body.setObjectName("welcomeCardBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        self.openai_key_edit.setPlaceholderText("Paste OpenAI key (sk-…)")
        layout.addWidget(self.openai_key_edit)

        link = QLabel('<a href="https://platform.openai.com/api-keys">Get a key at platform.openai.com</a>')
        link.setOpenExternalLinks(True)
        link.setObjectName("mutedLabel")
        layout.addWidget(link)

        layout.addStretch()
        button = QPushButton("Save and start")
        button.setObjectName("welcomeCardButton")
        button.setProperty("cardStyle", "outline")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(self._emit_openai)
        layout.addWidget(button)
        return card

    def _emit_openrouter(self) -> None:
        key = self.openrouter_key_edit.text().strip()
        if not key:
            self.openrouter_key_edit.setPlaceholderText("Paste a key first…")
            return
        self.openrouter_clicked.emit(key)

    def _emit_openai(self) -> None:
        key = self.openai_key_edit.text().strip()
        if not key:
            self.openai_key_edit.setPlaceholderText("Paste a key first…")
            return
        self.openai_clicked.emit(key)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.skip_clicked.emit()
            return
        super().keyPressEvent(event)


def pollinations_defaults() -> tuple[str, str, str, str]:
    """Return (image_provider, image_model, prompt_provider, prompt_model) for free start."""
    return (
        "pollinations",
        default_model("pollinations", IMAGE_ROLE) or "flux",
        "pollinations",
        default_model("pollinations", PROMPT_ROLE) or "openai",
    )


def openrouter_defaults() -> tuple[str, str, str, str]:
    return (
        "openrouter",
        default_model("openrouter", IMAGE_ROLE) or "google/gemini-3.1-flash-image-preview",
        "openrouter",
        default_model("openrouter", PROMPT_ROLE) or "openai/gpt-5.5",
    )


def openai_defaults() -> tuple[str, str, str, str]:
    return (
        "openai",
        default_model("openai", IMAGE_ROLE) or "gpt-image-2",
        "openai",
        default_model("openai", PROMPT_ROLE) or "gpt-5.5",
    )
