"""Palette swatch and preview panel widgets for the spritegen UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class PaletteSwatchBar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("paletteSwatches")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 6, 0, 0)
        self._layout.setSpacing(6)

    def set_palette(self, values: list[str]) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for value in values[:10]:
            swatch = QLabel(value)
            swatch.setObjectName("paletteSwatch")
            swatch.setAlignment(Qt.AlignCenter)
            swatch.setToolTip(value)
            swatch.setStyleSheet(
                f"background: {value}; color: {self._text_color_for(value)};"
            )
            self._layout.addWidget(swatch)
        self._layout.addStretch()

    def _text_color_for(self, value: str) -> str:
        color = value.strip().lstrip("#")
        if len(color) == 3:
            color = "".join(character * 2 for character in color)
        if len(color) != 6:
            return "#18232d"
        try:
            red = int(color[0:2], 16)
            green = int(color[2:4], 16)
            blue = int(color[4:6], 16)
        except ValueError:
            return "#18232d"
        luminance = (0.299 * red) + (0.587 * green) + (0.114 * blue)
        return "#ffffff" if luminance < 145 else "#18232d"


class PreviewPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("previewPanel")
        self._image_paths: list[Path] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setObjectName("previewScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        self.container = QWidget()
        self.container.setObjectName("previewContent")
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(10)

        self._add_placeholder()

        scroll.setWidget(self.container)
        layout.addWidget(scroll)

    @property
    def image_paths(self) -> list[Path]:
        return list(self._image_paths)

    def _add_placeholder(self) -> None:
        self.placeholder = QLabel("No generated assets yet.")
        self.placeholder.setObjectName("emptyStateLabel")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.container_layout.addWidget(self.placeholder)

    def clear(self) -> None:
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._image_paths.clear()
        self._add_placeholder()

    def add_image_path(self, path: Path) -> None:
        self.add_generation_output(path, [])

    def add_generation_output(
        self,
        raw_path: Path | None,
        slice_paths: list[Path],
        title: str | None = None,
    ) -> None:
        if raw_path is None and not slice_paths:
            return
        self.placeholder.hide()
        header = QLabel(title or self._group_title(raw_path, slice_paths))
        header.setObjectName("outputHeaderLabel")
        self.container_layout.addWidget(header)

        if raw_path is not None and raw_path.exists():
            raw_label = QLabel(f"Raw atlas: {raw_path.name}")
            raw_label.setObjectName("mutedLabel")
            self.container_layout.addWidget(raw_label)
            self._add_scaled_image(raw_path, max_width=480, max_height=480)

        existing_slices = [path for path in slice_paths if path.exists()]
        if existing_slices:
            slices_label = QLabel(f"Sliced sprites ({len(existing_slices)})")
            slices_label.setObjectName("mutedLabel")
            self.container_layout.addWidget(slices_label)
            self._add_slice_grid(existing_slices)

    def _group_title(self, raw_path: Path | None, slice_paths: list[Path]) -> str:
        if raw_path is not None:
            return raw_path.stem.replace("_", " ")
        if slice_paths:
            return slice_paths[0].parent.name.replace("_", " ")
        return "Generated output"

    def _add_scaled_image(self, path: Path, max_width: int, max_height: int) -> None:
        pixmap = QPixmap.fromImage(QImage(str(path)))
        if pixmap.isNull():
            return
        image_label = QLabel()
        image_label.setObjectName("assetImage")
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setPixmap(
            pixmap.scaled(
                max_width,
                max_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        self.container_layout.addWidget(image_label)
        self._image_paths.append(path)

    def _add_slice_grid(self, slice_paths: list[Path]) -> None:
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        for index, path in enumerate(slice_paths):
            cell = QWidget()
            cell.setObjectName("spriteCell")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(8, 8, 8, 8)
            cell_layout.setSpacing(6)

            pixmap = QPixmap.fromImage(QImage(str(path)))
            image_label = QLabel()
            image_label.setObjectName("assetImage")
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setMinimumSize(96, 96)
            if not pixmap.isNull():
                image_label.setPixmap(
                    pixmap.scaled(
                        128,
                        128,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
                self._image_paths.append(path)
            cell_layout.addWidget(image_label)

            name_label = QLabel(path.name)
            name_label.setObjectName("captionLabel")
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setWordWrap(True)
            cell_layout.addWidget(name_label)

            row, column = divmod(index, 4)
            grid.addWidget(cell, row, column)

        self.container_layout.addWidget(grid_widget)
