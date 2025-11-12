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
        self.setFixedSize(800, 600)
        self.models = []
        self.firmwares = []
        self.selected_model_id = None
        self.setup_ui()
        self.load_models()
        self.load_firmwares()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Управление прошивками")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
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
        self.save_button.clicked.connect(self.save_firmware)
        buttons_layout.addWidget(self.save_button)
        layout.addLayout(buttons_layout)

        # Стили
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-size: 14px; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QTextEdit { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px 20px; }
            QPushButton:hover { background-color: #555; }
        """)

    def load_models(self):
        model_file = "models/models.json"
        os.makedirs(os.path.dirname(model_file), exist_ok=True)
        try:
            if os.path.exists(model_file):
                with open(model_file, "r", encoding="utf-8") as f:
                    self.models = json.load(f)
            else:
                self.models = []
            self.update_model_list()
        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в {model_file}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле моделей: {str(e)}", "error")
            self.models = []
            self.update_model_list()

    def update_model_list(self):
        self.model_list.clear()
        for model in self.models:
            self.model_list.addItem(model["model_name"])
            if model["id"] == self.selected_model_id:
                self.model_list.setCurrentRow(self.models.index(model))

    def load_firmwares(self):
        firmware_file = "lists/firmware.json"
        os.makedirs(os.path.dirname(firmware_file), exist_ok=True)
        try:
            if os.path.exists(firmware_file):
                with open(firmware_file, "r", encoding="utf-8") as f:
                    self.firmwares = json.load(f)
            else:
                self.firmwares = []
        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в {firmware_file}: {str(e)}")
            self.parent().show_toast(f"Ошибка формата JSON в файле прошивок: {str(e)}", "error")
            self.firmwares = []

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
        firmware_file = "lists/firmware.json"
        os.makedirs(os.path.dirname(firmware_file), exist_ok=True)
        try:
            with open(firmware_file, "w", encoding="utf-8") as f:
                json.dump(self.firmwares, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения прошивок: {str(e)}")
            self.show_toast(f"Ошибка сохранения прошивок: {str(e)}", "error")