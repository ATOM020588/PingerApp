# widgets/models_management.py
# -*- coding: utf-8 -*-

import os
import json
import shutil

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QFormLayout,
    QLineEdit, QCheckBox, QComboBox, QTextEdit, QPushButton,
    QWidget, QFileDialog, QApplication
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QTimer


class ModelsManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление моделями")
        self.setMinimumSize(1350, 900)

        # Пути
        self.models_path = os.path.join("models", "models.json")
        self.models_dir = "models"
        self.images_dir = "images"
        self.firmware_path = os.path.join("lists", "firmware.json")

        # Данные
        self.selected_model_id = None
        self.current_syntax_data = {}
        self.selected_syntax_type = None
        self.firmware_data = []
        self.image_path = None

        self.init_ui()
        self.load_models()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # === Заголовки ===
        header_layout = QHBoxLayout()
        models_header = QWidget()
        models_header_label = QLabel("Список моделей")
        models_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        models_header_layout = QVBoxLayout()
        models_header_layout.addWidget(models_header_label)
        models_header.setLayout(models_header_layout)
        models_header.setFixedWidth(163)

        details_header = QWidget()
        details_header_label = QLabel("Модель")
        details_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details_header_layout = QVBoxLayout()
        details_header_layout.addWidget(details_header_label)
        details_header.setLayout(details_header_layout)
        details_header.setFixedWidth(373)

        syntax_header = QWidget()
        syntax_header_label = QLabel("Синтаксис")
        syntax_header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        syntax_header_layout = QVBoxLayout()
        syntax_header_layout.addWidget(syntax_header_label)
        syntax_header.setLayout(syntax_header_layout)
        syntax_header.setFixedWidth(744)

        header_layout.addWidget(models_header)
        header_layout.addWidget(details_header)
        header_layout.addWidget(syntax_header)
        main_layout.addLayout(header_layout)

        # === Контент ===
        content_layout = QHBoxLayout()

        # --- Колонка 1: Список моделей ---
        models_column = QVBoxLayout()
        self.models_list = QListWidget()
        self.models_list.itemClicked.connect(self.on_model_selected)
        models_column.addWidget(self.models_list)

        delete_button = QPushButton("Удалить модель")
        delete_button.clicked.connect(self.delete_model)
        models_column.addWidget(delete_button)

        models_widget = QWidget()
        models_widget.setStyleSheet("border-radius: 4px; padding: 5px;")
        models_widget.setLayout(models_column)
        models_widget.setFixedWidth(163)
        content_layout.addWidget(models_widget)

        # --- Колонка 2: Форма модели ---
        details_column = QVBoxLayout()
        form_widget = QWidget()
        form_layout = QFormLayout()

        self.model_name = QLineEdit()
        self.model_name.setPlaceholderText("Введите имя модели")
        self.olt = QCheckBox("OLT")
        self.neobills = QComboBox()
        self.neobills.addItems(["", "neobills1", "neobills2", "neobills3"])
        self.uplink = QLineEdit()
        self.ports_count = QLineEdit()
        self.mag_ports = QLineEdit()
        self.firmware = QComboBox()
        self.load_firmware_options()

        form_layout.addRow(QLabel("Имя:"), self.model_name)
        form_layout.addRow(QLabel("OLT:"), self.olt)
        form_layout.addRow(QLabel("Neobills:"), self.neobills)
        form_layout.addRow(QLabel("Uplink:"), self.uplink)
        form_layout.addRow(QLabel("Кол-во портов:"), self.ports_count)
        form_layout.addRow(QLabel("Маг. порты:"), self.mag_ports)
        form_layout.addRow(QLabel("Прошивка:"), self.firmware)

        form_widget.setLayout(form_layout)
        details_column.addWidget(form_widget)

        # Предпросмотр изображения
        self.preview_image = QLabel()
        self.preview_image.setFixedSize(300, 300)
        self.preview_image.setStyleSheet("border-radius: 4px; background-color: #555;")
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details_column.addWidget(QLabel("Предпросмотр картинки"))
        details_column.addWidget(self.preview_image)

        self.upload_image = QPushButton("Выбрать изображение")
        self.upload_image.clicked.connect(self.upload_image_file)
        details_column.addWidget(self.upload_image)

        # Кнопки
        buttons_layout = QHBoxLayout()
        add_button = QPushButton("Добавить модель")
        add_button.clicked.connect(self.add_model)
        edit_button = QPushButton("Изменить модель")
        edit_button.clicked.connect(self.save_model_changes)
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(edit_button)
        details_column.addLayout(buttons_layout)

        details_widget = QWidget()
        details_widget.setStyleSheet("border-radius: 4px; padding: 5px;")
        details_widget.setLayout(details_column)
        details_widget.setFixedWidth(373)
        content_layout.addWidget(details_widget)

        # --- Колонка 3: Синтаксис ---
        syntax_column = QVBoxLayout()
        syntax_layout = QHBoxLayout()

        # Типы синтаксиса
        syntax_type = QWidget()
        syntax_type_layout = QVBoxLayout()
        syntax_type_layout.addWidget(QLabel("Тип"))
        self.syntax_list = QListWidget()
        syntax_types = [
            "Общие", "Hostname", "Упр. VLAN", "Аккаунты", "IP", "Default Route",
            "Создание VLAN", "Доб. портов Untag", "Доб. портов Tag", "Description",
            "DHCP Enable", "DHCP Vlans", "DHCP Ports", "Address Binding", "RSTP",
            "RSTP Priority", "Save", "---", "SNMP"
        ]
        self.syntax_list.addItems(syntax_types)
        self.syntax_list.itemClicked.connect(self.on_syntax_type_selected)
        syntax_type_layout.addWidget(self.syntax_list)
        syntax_type.setLayout(syntax_type_layout)
        syntax_type.setFixedWidth(186)
        syntax_layout.addWidget(syntax_type)

        # Поле ввода
        syntax_info = QWidget()
        syntax_info_layout = QVBoxLayout()
        syntax_info_layout.addWidget(QLabel("Инфо"))
        self.syntax_info_text = QTextEdit()
        self.syntax_info_text.setPlaceholderText("Введите информацию для выбранного типа")
        syntax_info_layout.addWidget(self.syntax_info_text)
        syntax_info.setLayout(syntax_info_layout)
        syntax_info.setFixedWidth(558)
        syntax_layout.addWidget(syntax_info)

        syntax_column.addLayout(syntax_layout)

        save_syntax_button = QPushButton("Сохранить изменения")
        save_syntax_button.clicked.connect(self.save_syntax)
        syntax_column.addWidget(save_syntax_button)

        syntax_widget = QWidget()
        syntax_widget.setStyleSheet("border-radius: 4px; padding: 5px;")
        syntax_widget.setLayout(syntax_column)
        syntax_widget.setFixedWidth(744)
        content_layout.addWidget(syntax_widget)

        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)

        # === Стили ===
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-size: 14px; border: none; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #444;
                color: #FFC107;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                background-color: #444;
                color: #FFC107;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #555; }
            QCheckBox { color: #FFC107; border: none; }
            QCheckBox::indicator {
                background-color: #444;
                border: 1px solid #FFC107;
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:checked { background-color: #FFC107; }
            QListWidget {
                background-color: #444;
                color: #FFC107;
                border-radius: 4px;
                padding: 8px;
            }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
        """)

    # --------------------------------------------------------------------- #
    # Данные
    # --------------------------------------------------------------------- #
    def load_firmware_options(self):
        try:
            if not os.path.exists(self.firmware_path):
                self.parent().show_toast(f"Файл прошивок не найден: {self.firmware_path}", "error")
                return
            with open(self.firmware_path, "r", encoding="utf-8") as f:
                self.firmware_data = json.load(f)
            self.firmware.clear()
            self.firmware.addItem("")
            for item in self.firmware_data:
                if "model_name" in item:
                    self.firmware.addItem(item["model_name"])
        except Exception as e:
            self.parent().show_toast(f"Ошибка загрузки прошивок: {str(e)}", "error")

    def load_models(self):
        try:
            os.makedirs(self.models_dir, exist_ok=True)
            if not os.path.exists(self.models_path):
                with open(self.models_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=4)
            with open(self.models_path, "r", encoding="utf-8") as f:
                models = json.load(f)
            self.models_list.clear()
            for model in models:
                item = self.models_list.addItem(model["model_name"])
                self.models_list.item(self.models_list.count() - 1).setData(Qt.ItemDataRole.UserRole, model["id"])
        except Exception as e:
            self.parent().show_toast(f"Ошибка загрузки списка моделей: {str(e)}", "error")

    # --------------------------------------------------------------------- #
    # Обработчики
    # --------------------------------------------------------------------- #
    def on_model_selected(self, item):
        self.selected_model_id = item.data(Qt.ItemDataRole.UserRole)
        model_path = os.path.join(self.models_dir, f"{self.selected_model_id}.json")
        try:
            if not os.path.exists(model_path):
                self.parent().show_toast(f"Файл модели не найден: {model_path}", "error")
                return
            with open(model_path, "r", encoding="utf-8") as f:
                model = json.load(f)

            self.model_name.setText(model.get("model_name", ""))
            self.olt.setChecked(model.get("olt", False))
            self.neobills.setCurrentText(model.get("neobills", ""))
            self.uplink.setText(model.get("uplink", ""))
            self.ports_count.setText(model.get("ports_count", ""))
            self.mag_ports.setText(model.get("mag_ports", ""))
            firmware = model.get("firmware", {})
            if isinstance(firmware, dict) and "model_name" in firmware:
                self.firmware.setCurrentText(firmware["model_name"])
            else:
                self.firmware.setCurrentText("")

            self.current_syntax_data = model.get("syntax", {})
            self.syntax_info_text.setPlainText("")
            self.syntax_list.clearSelection()
            self.selected_syntax_type = None

            image = model.get("image", "")
            if image and os.path.exists(os.path.join(self.images_dir, image)):
                pixmap = QPixmap(os.path.join(self.images_dir, image))
                self.preview_image.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio))
                self.image_path = os.path.join(self.images_dir, image)
            else:
                self.preview_image.clear()
                self.image_path = None
        except Exception as e:
            self.parent().show_toast(f"Ошибка загрузки модели: {str(e)}", "error")

    def on_syntax_type_selected(self, item):
        self.selected_syntax_type = item.text()
        if self.selected_syntax_type == "---":
            self.selected_syntax_type = None
            self.syntax_info_text.setPlainText("")
            return
        self.syntax_info_text.setPlainText(self.current_syntax_data.get(self.selected_syntax_type, ""))

    def upload_image_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            self.preview_image.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio))

    def add_model(self):
        if not self.model_name.text():
            self.parent().show_toast("Заполните имя модели", "error")
            return

        model_id = f"model_{self.model_name.text().replace(' ', '_')}"
        selected_firmware_name = self.firmware.currentText()
        firmware_data = next((item for item in self.firmware_data if item.get("model_name") == selected_firmware_name), {}) if selected_firmware_name else {}

        model_data = {
            "id": model_id,
            "model_name": self.model_name.text(),
            "olt": self.olt.isChecked(),
            "neobills": self.neobills.currentText(),
            "uplink": self.uplink.text(),
            "ports_count": self.ports_count.text(),
            "mag_ports": self.mag_ports.text(),
            "firmware": firmware_data,
            "syntax": self.current_syntax_data
        }

        if self.image_path:
            image_ext = os.path.splitext(self.image_path)[1]
            image_name = f"{model_id}{image_ext}"
            model_data["image"] = image_name
            os.makedirs(self.images_dir, exist_ok=True)
            destination = os.path.join(self.images_dir, image_name)
            if self.image_path != destination:
                shutil.copy(self.image_path, destination)

        try:
            with open(self.models_path, "r", encoding="utf-8") as f:
                models = json.load(f)
            if any(m["id"] == model_id for m in models):
                self.parent().show_toast("Модель с таким именем уже существует", "error")
                return
            models.append({"id": model_id, "model_name": self.model_name.text()})
            with open(self.models_path, "w", encoding="utf-8") as f:
                json.dump(models, f, ensure_ascii=False, indent=4)

            os.makedirs(self.models_dir, exist_ok=True)
            with open(os.path.join(self.models_dir, f"{model_id}.json"), "w", encoding="utf-8") as f:
                json.dump(model_data, f, ensure_ascii=False, indent=4)

            self.parent().show_toast("Модель добавлена", "success")
            self.load_models()
            self.reset_form()
        except Exception as e:
            self.parent().show_toast(f"Ошибка добавления модели: {str(e)}", "error")

    def save_model_changes(self):
        if not self.selected_model_id:
            self.parent().show_toast("Выберите модель для редактирования", "error")
            return
        if not self.model_name.text():
            self.parent().show_toast("Заполните имя модели", "error")
            return

        model_id = self.selected_model_id
        selected_firmware_name = self.firmware.currentText()
        firmware_data = next((item for item in self.firmware_data if item.get("model_name") == selected_firmware_name), {}) if selected_firmware_name else {}

        model_data = {
            "id": model_id,
            "model_name": self.model_name.text(),
            "olt": self.olt.isChecked(),
            "neobills": self.neobills.currentText(),
            "uplink": self.uplink.text(),
            "ports_count": self.ports_count.text(),
            "mag_ports": self.mag_ports.text(),
            "firmware": firmware_data,
            "syntax": self.current_syntax_data
        }

        if self.image_path:
            image_ext = os.path.splitext(self.image_path)[1]
            image_name = f"{model_id}{image_ext}"
            model_data["image"] = image_name
            os.makedirs(self.images_dir, exist_ok=True)
            destination = os.path.join(self.images_dir, image_name)
            if self.image_path != destination:
                shutil.copy(self.image_path, destination)

        try:
            with open(self.models_path, "r", encoding="utf-8") as f:
                models = json.load(f)
            for model in models:
                if model["id"] == model_id:
                    model["model_name"] = self.model_name.text()
                    break
            with open(self.models_path, "w", encoding="utf-8") as f:
                json.dump(models, f, ensure_ascii=False, indent=4)

            with open(os.path.join(self.models_dir, f"{model_id}.json"), "w", encoding="utf-8") as f:
                json.dump(model_data, f, ensure_ascii=False, indent=4)

            self.parent().show_toast("Модель обновлена", "success")
            self.load_models()
            self.reset_form()
        except Exception as e:
            self.parent().show_toast(f"Ошибка обновления модели: {str(e)}", "error")

    def delete_model(self):
        if not self.selected_model_id:
            self.parent().show_toast("Выберите модель для удаления", "error")
            return

        model_path = os.path.join(self.models_dir, f"{self.selected_model_id}.json")
        try:
            with open(self.models_path, "r", encoding="utf-8") as f:
                models = json.load(f)
            models = [m for m in models if m["id"] != self.selected_model_id]
            with open(self.models_path, "w", encoding="utf-8") as f:
                json.dump(models, f, ensure_ascii=False, indent=4)

            if os.path.exists(model_path):
                os.remove(model_path)

            self.parent().show_toast("Модель удалена", "success")
            self.load_models()
            self.reset_form()
        except Exception as e:
            self.parent().show_toast(f"Ошибка удаления модели: {str(e)}", "error")

    def save_syntax(self):
        if not self.selected_syntax_type:
            self.parent().show_toast("Выберите тип синтаксиса", "error")
            return
        if not self.selected_model_id:
            self.parent().show_toast("Выберите модель для редактирования", "error")
            return

        self.current_syntax_data[self.selected_syntax_type] = self.syntax_info_text.toPlainText()
        model_path = os.path.join(self.models_dir, f"{self.selected_model_id}.json")
        try:
            if not os.path.exists(model_path):
                self.parent().show_toast(f"Файл модели не найден: {model_path}", "error")
                return
            with open(model_path, "r", encoding="utf-8") as f:
                model_data = json.load(f)
            model_data["syntax"] = self.current_syntax_data
            with open(model_path, "w", encoding="utf-8") as f:
                json.dump(model_data, f, ensure_ascii=False, indent=4)

            self.parent().show_toast("Синтаксис обновлен", "success")
            self.syntax_info_text.setPlainText("")
            self.syntax_list.clearSelection()
            self.selected_syntax_type = None
        except Exception as e:
            self.parent().show_toast(f"Ошибка сохранения синтаксиса: {str(e)}", "error")

    def reset_form(self):
        self.model_name.clear()
        self.olt.setChecked(False)
        self.neobills.setCurrentIndex(0)
        self.uplink.clear()
        self.ports_count.clear()
        self.mag_ports.clear()
        self.firmware.setCurrentIndex(0)
        self.preview_image.clear()
        self.image_path = None
        self.current_syntax_data = {}
        self.syntax_info_text.setPlainText("")
        self.syntax_list.clearSelection()
        self.selected_syntax_type = None
        self.selected_model_id = None