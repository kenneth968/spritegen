"""Desktop design tokens and Qt stylesheet for spritegen."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtWidgets import QWidget


DESIGN_TOKENS: dict[str, dict[str, str]] = {
    "color": {
        "app_background": "#eef2f4",
        "panel": "#f8fafb",
        "surface": "#ffffff",
        "surface_soft": "#f5f8fa",
        "border": "#cfdbe4",
        "border_strong": "#9eb2c0",
        "text": "#18232d",
        "muted": "#566979",
        "primary": "#1f7a8c",
        "primary_hover": "#176a79",
        "accent": "#f3b64b",
        "accent_hover": "#dea139",
        "danger": "#b94747",
        "danger_hover": "#9f3939",
        "success": "#287d52",
        "focus": "#2f8ea4",
    },
    "radius": {
        "sm": "4px",
        "md": "6px",
        "lg": "8px",
    },
    "spacing": {
        "xs": "4px",
        "sm": "8px",
        "md": "12px",
        "lg": "16px",
    },
    "type": {
        "family": "\"Segoe UI\", Arial, sans-serif",
        "mono": "\"Cascadia Mono\", Consolas, monospace",
        "base": "13px",
        "title": "26px",
        "section": "18px",
    },
}


def desktop_stylesheet(tokens: Mapping[str, Mapping[str, str]] | None = None) -> str:
    theme = tokens or DESIGN_TOKENS
    color = theme["color"]
    radius = theme["radius"]
    spacing = theme["spacing"]
    type_ = theme["type"]
    return f"""
    QWidget#appRoot {{
        background: {color["app_background"]};
    }}
    QWidget {{
        font-family: {type_["family"]};
        font-size: {type_["base"]};
        color: {color["text"]};
    }}
    QWidget#sidebarPanel,
    QWidget#workspacePanel {{
        background: {color["panel"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["lg"]};
    }}
    QWidget#actionFooter {{
        background: {color["surface"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["lg"]};
    }}
    QLabel#appTitle {{
        color: {color["text"]};
        font-size: {type_["title"]};
        font-weight: 700;
    }}
    QLabel#sectionTitle {{
        color: {color["text"]};
        font-size: {type_["section"]};
        font-weight: 700;
    }}
    QLabel#mutedLabel,
    QLabel#captionLabel,
    QLabel#emptyStateLabel {{
        color: {color["muted"]};
    }}
    QLabel#captionLabel {{
        font-size: 11px;
    }}
    QLabel#outputHeaderLabel {{
        color: {color["text"]};
        font-weight: 700;
        margin-top: {spacing["sm"]};
    }}
    QGroupBox {{
        background: {color["surface"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["lg"]};
        font-weight: 700;
        margin-top: {spacing["lg"]};
        padding: 14px 12px 12px 12px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {color["text"]};
        background: {color["surface"]};
    }}
    QLineEdit,
    QComboBox,
    QSpinBox {{
        background: {color["surface"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
        selection-background-color: {color["primary"]};
        min-height: 30px;
        padding: 4px 8px;
    }}
    QTextEdit {{
        background: {color["surface"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
        selection-background-color: {color["primary"]};
        padding: 8px;
    }}
    QLineEdit:focus,
    QComboBox:focus,
    QSpinBox:focus,
    QTextEdit:focus {{
        border: 1px solid {color["focus"]};
    }}
    QTextEdit#promptPreview {{
        background: {color["surface_soft"]};
        font-family: {type_["mono"]};
    }}
    QPushButton {{
        background: {color["surface"]};
        border: 1px solid {color["border_strong"]};
        border-radius: {radius["md"]};
        min-height: 32px;
        padding: 5px 12px;
    }}
    QPushButton:hover {{
        background: {color["surface_soft"]};
        border-color: {color["focus"]};
    }}
    QPushButton:disabled {{
        color: {color["muted"]};
        background: {color["surface_soft"]};
        border-color: {color["border"]};
    }}
    QPushButton[buttonRole="secondary"] {{
        background: {color["surface"]};
        border-color: {color["border"]};
        color: {color["text"]};
    }}
    QPushButton[buttonRole="primary"] {{
        background: {color["primary"]};
        border-color: {color["primary"]};
        color: white;
        font-weight: 700;
    }}
    QPushButton[buttonRole="primary"]:hover {{
        background: {color["primary_hover"]};
        border-color: {color["primary_hover"]};
    }}
    QPushButton[buttonRole="accent"] {{
        background: {color["accent"]};
        border-color: {color["accent_hover"]};
        color: {color["text"]};
        font-weight: 700;
    }}
    QPushButton[buttonRole="accent"]:hover {{
        background: {color["accent_hover"]};
    }}
    QPushButton[buttonRole="danger"] {{
        color: {color["danger"]};
        border-color: {color["danger"]};
    }}
    QPushButton[buttonRole="danger"]:hover {{
        background: {color["danger"]};
        border-color: {color["danger_hover"]};
        color: white;
    }}
    QTabWidget::pane {{
        border: 0;
        background: transparent;
    }}
    QTabBar::tab {{
        padding: 9px 18px;
        margin-right: 2px;
        min-width: 92px;
        background: #e6edf2;
        border: 1px solid {color["border"]};
        border-bottom: 0;
        border-top-left-radius: {radius["md"]};
        border-top-right-radius: {radius["md"]};
    }}
    QTabBar::tab:selected {{
        background: {color["surface"]};
        color: {color["primary"]};
        border-top: 3px solid {color["primary"]};
    }}
    QScrollArea {{
        border: 0;
        background: transparent;
    }}
    QProgressBar {{
        min-height: 24px;
        text-align: center;
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
        background: {color["surface_soft"]};
    }}
    QProgressBar::chunk {{
        background: {color["success"]};
        border-radius: {radius["sm"]};
    }}
    QSplitter::handle {{
        background: transparent;
        width: 12px;
    }}
    """


def set_button_role(widget: QWidget, role: str) -> None:
    widget.setProperty("buttonRole", role)
