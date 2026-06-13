"""Desktop design tokens and Qt stylesheet for spritegen."""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtWidgets import QWidget


DESIGN_TOKENS: dict[str, dict[str, str]] = {
    "color": {
        "app_background": "#e8eef2",
        "panel": "#f7f9fb",
        "surface": "#ffffff",
        "surface_soft": "#eef4f7",
        "surface_sunken": "#e2eaf0",
        "border": "#c7d5df",
        "border_strong": "#8fa7b6",
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
        background: qlineargradient(
            x1: 0, y1: 0, x2: 1, y2: 1,
            stop: 0 {color["surface"]},
            stop: 0.48 {color["app_background"]},
            stop: 1 {color["surface_sunken"]}
        );
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
    QDialog#toolDialog {{
        background: {color["panel"]};
    }}
    QWidget#previewPanel {{
        background: {color["surface_sunken"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["lg"]};
    }}
    QWidget#previewContent {{
        background: transparent;
    }}
    QWidget#spriteCell {{
        background: {color["surface"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
    }}
    QLabel#appTitle {{
        color: {color["text"]};
        font-size: {type_["title"]};
        font-weight: 700;
    }}
    QLabel#dialogTitle {{
        color: {color["text"]};
        font-size: {type_["section"]};
        font-weight: 700;
        padding: 0 0 {spacing["sm"]} 0;
    }}
    QLabel#sectionTitle {{
        color: {color["text"]};
        font-size: {type_["section"]};
        font-weight: 700;
    }}
    QLabel#workflowStrip,
    QLabel#runSummaryLabel {{
        background: {color["surface_soft"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
        color: {color["muted"]};
        font-weight: 700;
        padding: 8px 10px;
    }}
    QLabel#statusLabel {{
        background: {color["surface_soft"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
        color: {color["muted"]};
        padding: 7px 9px;
    }}
    QLabel#mutedLabel,
    QLabel#captionLabel,
    QLabel#emptyStateLabel {{
        color: {color["muted"]};
    }}
    QLabel#emptyStateLabel {{
        background: {color["surface"]};
        border: 1px dashed {color["border_strong"]};
        border-radius: {radius["lg"]};
        min-height: 180px;
        padding: {spacing["lg"]};
    }}
    QLabel#captionLabel {{
        font-size: 11px;
    }}
    QLabel#assetImage {{
        background: {color["surface"]};
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
        padding: {spacing["sm"]};
    }}
    QLabel#outputHeaderLabel {{
        color: {color["text"]};
        font-weight: 700;
        margin-top: {spacing["sm"]};
    }}
    QLabel#paletteSwatch {{
        border: 1px solid {color["border_strong"]};
        border-radius: {radius["sm"]};
        min-width: 66px;
        max-width: 86px;
        min-height: 28px;
        padding: 2px 6px;
        font-size: 10px;
        font-weight: 700;
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
        border-color: {color["border_strong"]};
        font-family: {type_["mono"]};
    }}
    QPushButton {{
        background: {color["surface"]};
        border: 1px solid {color["border_strong"]};
        border-radius: {radius["md"]};
        min-height: 32px;
        padding: 5px 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: {color["surface_soft"]};
        border-color: {color["focus"]};
    }}
    QPushButton:pressed {{
        background: {color["surface_sunken"]};
        padding-top: 6px;
        padding-bottom: 4px;
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
    QPushButton[buttonRole="primary"]:pressed {{
        background: {color["primary_hover"]};
        border-color: {color["primary_hover"]};
        color: white;
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
    QPushButton[buttonRole="accent"]:pressed {{
        background: {color["accent_hover"]};
        color: {color["text"]};
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
    QPushButton[buttonRole="danger"]:pressed {{
        background: {color["danger_hover"]};
        border-color: {color["danger_hover"]};
        color: white;
    }}
    QTabWidget::pane {{
        border: 0;
        background: transparent;
    }}
    QTabBar::tab {{
        padding: 8px 10px;
        margin-right: 2px;
        margin-bottom: 6px;
        min-width: 72px;
        background: transparent;
        color: {color["muted"]};
        border: 1px solid transparent;
        border-radius: {radius["md"]};
        font-weight: 700;
    }}
    QTabBar::tab:hover {{
        background: {color["surface_soft"]};
        border-color: {color["border"]};
        color: {color["text"]};
    }}
    QTabBar::tab:selected {{
        background: {color["surface"]};
        color: {color["text"]};
        border: 1px solid {color["border_strong"]};
        border-bottom: 3px solid {color["primary"]};
    }}
    QScrollArea {{
        border: 0;
        background: transparent;
    }}
    QProgressBar#generationProgress {{
        min-height: 18px;
        text-align: center;
        border: 1px solid {color["border"]};
        border-radius: {radius["md"]};
        background: {color["surface_soft"]};
    }}
    QProgressBar#generationProgress::chunk {{
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
