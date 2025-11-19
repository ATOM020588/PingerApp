# widgets/firmware_management.py

import os
import json

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QTextEdit, QPushButton, QWidget, QApplication
)
from PyQt6.QtCore import Qt, QTimer

class FirmwareManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление прошивками")
        self.setFixedSize(800, 700)
        self.models = []
        self.firmwares = []
        self.selected_model_id = None
        self.setup_ui()
        self.load_models()
        self.load_firmwares()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(15)
        layout.addLayout(columns_layout)

        # Левая колонка — список моделей
        model_column = QVBoxLayout()
        model_label = QLabel("Модель")
        model_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        model_column.addWidget(model_label)
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(400)
        self.model_list.itemClicked.connect(self.update_firmware_text)
        model_column.addWidget(self.model_list)
        columns_layout.addLayout(model_column, stretch=2)

        # Правая колонка — редактор прошивки
        firmware_column = QVBoxLayout()
        firmware_label = QLabel("Прошивки")
        firmware_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        firmware_column.addWidget(firmware_label)
        self.firmware_text = QTextEdit()
        self.firmware_text.setMinimumHeight(400)
        firmware_column.addWidget(self.firmware_text)
        columns_layout.addLayout(firmware_column, stretch=8)

        # Кнопка сохранения
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить")
        self.save_button.setFixedWidth(150)
        self.save_button.clicked.connect(self.save_firmware)
        layout.addSpacing(10)
        buttons_layout.addWidget(self.save_button)
        layout.addLayout(buttons_layout)
        layout.addSpacing(10)

        # Стили
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-size: 12px; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QTextEdit { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)

    def load_models(self):
        if not self.parent().ws_connected:
            self.models = []
            self.update_model_list()
            return

        req = self.parent().ws_client.send_request("list_models")

        def on_resp(data):
            if data.get("success"):
                self.models = data.get("models", [])
            else:
                self.models = []

            self.update_model_list()

            # Загружать прошивки ТОЛЬКО ПОСЛЕ моделей
            self.load_firmwares()

        self.parent().pending_requests[req] = on_resp


    def update_model_list(self):
        self.model_list.clear()
        for model in self.models:
            self.model_list.addItem(model["model_name"])
            if model["id"] == self.selected_model_id:
                self.model_list.setCurrentRow(self.models.index(model))

    def load_firmwares(self):
        if not self.parent().ws_connected:
            self.firmwares = []
            return

        req = self.parent().ws_client.send_request("list_firmwares")

        def on_resp(data):
            if data.get("success"):
                self.firmwares = data.get("firmwares", [])
            else:
                self.firmwares = []

            # если модель уже выбрана — обновить текст
            current = self.model_list.currentItem()
            if current:
                self.update_firmware_text(current)

        self.parent().pending_requests[req] = on_resp


    def update_firmware_text(self, item):
        model_name = item.text()
        model = next((m for m in self.models if m["model_name"] == model_name), None)
        if model:
            self.selected_model_id = model["id"]
            firmware = next((f for f in self.firmwares if f["id"] == self.selected_model_id), None)
            self.firmware_text.setPlainText(firmware["firmware"] if firmware else "")
        else:
            self.firmware_text.clear()
            self.selected_model_id = None

    def save_firmware(self):
        if not self.selected_model_id:
            self.parent().show_toast("Выберите модель для сохранения прошивки", "error")
            return

        firmware_text = self.firmware_text.toPlainText().strip()
        if not firmware_text:
            self.show_toast("Введите данные прошивки", "error")
            return

        firmware_index = next((i for i, f in enumerate(self.firmwares) if f["id"] == self.selected_model_id), -1)
        model = next((m for m in self.models if m["id"] == self.selected_model_id), None)
        if model:
            firmware_data = {
                "id": self.selected_model_id,
                "model_name": model["model_name"],
                "firmware": firmware_text
            }
            if firmware_index != -1:
                self.firmwares[firmware_index] = firmware_data
            else:
                self.firmwares.append(firmware_data)
            self.save_firmware_list()
            self.show_toast("Прошивка сохранена", "success")
        else:
            self.show_toast("Ошибка: модель не найдена", "error")

    def save_firmware_list(self):
        if not self.parent().ws_connected:
            self.show_toast("Нет связи с сервером", "error")
            return

        req = self.parent().ws_client.send_request(
            "save_firmwares",
            firmwares=self.firmwares
        )

        self.parent().pending_requests[req] = lambda data: None