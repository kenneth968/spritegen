"""Editable combo box that stores provider model IDs as item data."""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox


class ModelPicker(QComboBox):
    def __init__(self, default_model_id: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.lineEdit().setPlaceholderText("Choose or paste a model ID")
        if default_model_id:
            self.setText(default_model_id)

    def text(self) -> str:
        current_text = self.currentText().strip()
        current_index = self.currentIndex()
        if current_index >= 0 and current_text == self.itemText(current_index):
            data = self.currentData()
            if data:
                return str(data).strip()
        return current_text

    def setText(self, value: str) -> None:
        model_id = value.strip()
        if not model_id:
            self.setCurrentIndex(-1)
            self.setEditText("")
            return
        index = self.findData(model_id)
        if index >= 0:
            self.setCurrentIndex(index)
        else:
            self.setCurrentIndex(-1)
            self.setEditText(model_id)
