# widgets/models_management.py
# -*- coding: utf-8 -*-

import os
import json
import base64
import shutil

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QFormLayout,
    QLineEdit, QCheckBox, QComboBox, QTextEdit, QPushButton,
    QWidget, QFileDialog
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

class ModelsManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление моделями")
        self.setFixedSize(1350, 900)

        # Состояние
        self.selected_model_id = None
        self.current_syntax_data = {}
        self.selected_syntax_type = None
        self.firmware_data = []
        self.image_path = None

        # UI-инициализация
        self.init_ui()

        # Загружаем сначала прошивки (они используются в форме), затем список моделей
        self.load_firmware_options()
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
        self.firmware.addItem("")  # будет заполнено в load_firmware_options()
        form_layout.addRow(QLabel("Имя:"), self.model_name)
        form_layout.addRow(QLabel("OLT:"), self.olt)
        form_layout.addRow(QLabel("Neobills:"), self.neobills)
        form_layout.addRow(QLabel("Uplink:"), self.uplink)
        form_layout.addRow(QLabel("Кол-во портов:"), self.ports_count)
        form_layout.addRow(QLabel("Маг. порты:"), self.mag_ports)
        form_layout.addRow(QLabel("Прошивка:"), self.firmware)
        form_widget.setLayout(form_layout)
        details_column.addWidget(form_widget)

        preview_label = QLabel("Предпросмотр картинки")
        preview_label.setStyleSheet("padding-top: 20px;")
        form_layout.addWidget(preview_label)

        # Предпросмотр изображения (поднимаем выше)
        self.preview_image = QLabel()
        self.preview_image.setFixedSize(360, 300)
        self.preview_image.setStyleSheet("border-radius: 4px; border: 1px solid #FFC107; ")
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignTop)
        details_column.addWidget(self.preview_image)
        self.upload_image = QPushButton("Выбрать изображение")
        self.upload_image.clicked.connect(self.upload_image_file)
        self.upload_image.setStyleSheet("margin-top: 50px;")
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
        self.syntax_info_text.setMaximumWidth(520)
        self.syntax_info_text.setPlaceholderText("Введите информацию для выбранного типа")
        syntax_info_layout.addWidget(self.syntax_info_text)
        syntax_info.setLayout(syntax_info_layout)
        syntax_info.setFixedWidth(558)
        syntax_layout.addWidget(syntax_info)
        syntax_column.addLayout(syntax_layout, stretch=1)

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
            QLabel { color: #FFC107; font-size: 12px; border: none; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 2px; height: 20px; }
            QComboBox { background-color: #444; color: #FFC107; height: 20px; border-radius: 4px; padding: 6px; }
            QComboBox::drop-down { border: none; }
            QTextEdit { background-color: #444; color: #FFC107; border-radius: 4px; padding: 8px; border: 1px solid #FFC107; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
            QCheckBox { color: #FFC107; border: none; }
            QCheckBox::indicator { background-color: #444; border: 1px solid #FFC107; width: 14px; height: 14px; }
            QCheckBox::indicator:checked { background-color: #FFC107; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
        """)

    # --------------------------------------------------------------------- #
    # Работа с сервера через WebSocket
    # --------------------------------------------------------------------- #
    def load_firmware_options(self):
        """Запрашивает список прошивок с сервера (data/lists/firmware.json)"""
        parent = self.parent()
        if not parent or not getattr(parent, "ws_connected", False):
            if parent:
                parent.show_toast("Нет связи с сервером", "error")
            return

        req = parent.ws_client.send_request("list_firmwares")

        def on_resp(data):
            if not data.get("success"):
                parent.show_toast("Ошибка загрузки прошивок", "error")
                return

            self.firmware_data = data.get("firmwares", [])
            self.firmware.clear()
            self.firmware.addItem("")
            for item in self.firmware_data:
                if "model_name" in item:
                    self.firmware.addItem(item["model_name"])

        parent.pending_requests[req] = on_resp

    def load_models(self):
        """Запрашивает список моделей с сервера (data/models/models.json)"""
        parent = self.parent()
        if not parent or not getattr(parent, "ws_connected", False):
            if parent:
                parent.show_toast("Нет связи с сервером", "error")
            return

        req = parent.ws_client.send_request("list_models")

        def on_resp(data):
            if not data.get("success"):
                parent.show_toast("Ошибка загрузки списка моделей", "error")
                return

            models = data.get("models", [])
            self.models_list.clear()
            for model in models:
                self.models_list.addItem(model["model_name"])
                self.models_list.item(self.models_list.count() - 1).setData(Qt.ItemDataRole.UserRole, model["id"])

        parent.pending_requests[req] = on_resp

    def on_model_selected(self, item):
        """Загружает выбранную модель с сервера (data/models/<id>.json)"""
        parent = self.parent()
        self.selected_model_id = item.data(Qt.ItemDataRole.UserRole)
        if not parent or not getattr(parent, "ws_connected", False):
            parent.show_toast("Нет связи с сервером", "error")
            return

        req = parent.ws_client.send_request("load_model", id=self.selected_model_id)

        def on_resp(data):
            if not data.get("success"):
                parent.show_toast("Ошибка загрузки модели", "error")
                return

            model = data.get("model", {})

            # Заполняем форму
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
                self.firmware.setCurrentIndex(0)

            self.current_syntax_data = model.get("syntax", {})
            self.syntax_info_text.setPlainText("")
            self.syntax_list.clearSelection()
            self.selected_syntax_type = None

            image_name = model.get("image", "")
            if image_name:
                # Запрос изображения с сервера
                self.download_image_from_server(image_name)
            else:
                self.preview_image.clear()

        parent.pending_requests[req] = on_resp

    def download_image_from_server(self, filename):
        """Запрашивает изображение (Base64) и отображает его"""
        parent = self.parent()
        if not parent or not getattr(parent, "ws_connected", False):
            return

        req = parent.ws_client.send_request("download_image", filename=filename)

        def on_resp(data):
            if not data.get("success"):
                self.preview_image.clear()
                return

            b64 = data.get("image")
            if not b64:
                self.preview_image.clear()
                return

            try:
                img_bytes = base64.b64decode(b64)
                pixmap = QPixmap()
                pixmap.loadFromData(img_bytes)
                self.preview_image.setPixmap(pixmap.scaled(360, 300, Qt.AspectRatioMode.KeepAspectRatio))
            except Exception:
                self.preview_image.clear()

        parent.pending_requests[req] = on_resp

    def upload_image_file(self):
        """Выбор изображения локально — картинка будет загружена на сервер при сохранении/добавлении модели"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите изображение", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            pixmap = QPixmap(file_path)
            self.preview_image.setPixmap(pixmap.scaled(360, 300, Qt.AspectRatioMode.KeepAspectRatio))

    def upload_image_to_server(self, filename):
        """Отправляет изображение в base64 на сервер (upload_image)"""
        parent = self.parent()
        if not parent or not getattr(parent, "ws_connected", False):
            parent.show_toast("Нет связи с сервером", "error")
            return

        try:
            with open(self.image_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()

            # fire-and-forget, сервер сохранит файл
            parent.ws_client.send_request("upload_image", filename=filename, image=b64)
        except Exception as e:
            parent.show_toast(f"Ошибка загрузки изображения: {str(e)}", "error")

    def add_model(self):
        parent = self.parent()
        if not self.model_name.text():
            parent.show_toast("Заполните имя модели", "error")
            return

        model_id = f"model_{self.model_name.text().replace(' ', '_')}"
        selected_fw = self.firmware.currentText()
        fw_data = next((x for x in self.firmware_data if x.get("model_name") == selected_fw), {})

        model_data = {
            "id": model_id,
            "model_name": self.model_name.text(),
            "olt": self.olt.isChecked(),
            "neobills": self.neobills.currentText(),
            "uplink": self.uplink.text(),
            "ports_count": self.ports_count.text(),
            "mag_ports": self.mag_ports.text(),
            "firmware": fw_data,
            "syntax": self.current_syntax_data,
        }

        # изображение: загружаем на сервер и указываем имя в модели
        if self.image_path:
            ext = os.path.splitext(self.image_path)[1]
            img_name = f"{model_id}{ext}"
            model_data["image"] = img_name
            self.upload_image_to_server(img_name)

        if not parent or not getattr(parent, "ws_connected", False):
            if parent:
                parent.show_toast("Нет связи с сервером", "error")
            return

        req = parent.ws_client.send_request("save_model", id=model_id, model=model_data)

        def on_resp(data):
            if data.get("success"):
                parent.show_toast("Модель добавлена", "success")
                self.load_models()
                self.reset_form()
            else:
                parent.show_toast(f"Ошибка добавления модели: {data.get('error')}", "error")

        parent.pending_requests[req] = on_resp

    def save_model_changes(self):
        parent = self.parent()
        if not self.selected_model_id:
            parent.show_toast("Выберите модель", "error")
            return
        if not self.model_name.text():
            parent.show_toast("Заполните имя модели", "error")
            return

        selected_fw = self.firmware.currentText()
        fw_data = next((x for x in self.firmware_data if x.get("model_name") == selected_fw), {})

        model_data = {
            "id": self.selected_model_id,
            "model_name": self.model_name.text(),
            "olt": self.olt.isChecked(),
            "neobills": self.neobills.currentText(),
            "uplink": self.uplink.text(),
            "ports_count": self.ports_count.text(),
            "mag_ports": self.mag_ports.text(),
            "firmware": fw_data,
            "syntax": self.current_syntax_data
        }

        # изображение: загружаем на сервер и указываем имя в модели
        if self.image_path:
            ext = os.path.splitext(self.image_path)[1]
            img_name = f"{self.selected_model_id}{ext}"
            model_data["image"] = img_name
            self.upload_image_to_server(img_name)

        if not parent or not getattr(parent, "ws_connected", False):
            parent.show_toast("Нет связи с сервером", "error")
            return

        req = parent.ws_client.send_request("save_model", id=self.selected_model_id, model=model_data)

        def on_resp(data):
            if data.get("success"):
                parent.show_toast("Модель обновлена", "success")
                self.load_models()
                self.reset_form()
            else:
                parent.show_toast(f"Ошибка обновления модели: {data.get('error')}", "error")

        parent.pending_requests[req] = on_resp

    def delete_model(self):
        parent = self.parent()
        if not self.selected_model_id:
            parent.show_toast("Выберите модель", "error")
            return

        if not parent or not getattr(parent, "ws_connected", False):
            parent.show_toast("Нет связи с сервером", "error")
            return

        req = parent.ws_client.send_request("delete_model", id=self.selected_model_id)

        def on_resp(data):
            if data.get("success"):
                parent.show_toast("Модель удалена", "success")
                self.load_models()
                self.reset_form()
            else:
                parent.show_toast(f"Ошибка удаления модели: {data.get('error')}", "error")

        parent.pending_requests[req] = on_resp

    def on_syntax_type_selected(self, item):
        self.selected_syntax_type = item.text()
        if self.selected_syntax_type == "---":
            self.selected_syntax_type = None
            self.syntax_info_text.setPlainText("")
            return
        self.syntax_info_text.setPlainText(self.current_syntax_data.get(self.selected_syntax_type, ""))

    def save_syntax(self):
        parent = self.parent()
        if not self.selected_syntax_type:
            parent.show_toast("Выберите тип синтаксиса", "error")
            return
        if not self.selected_model_id:
            parent.show_toast("Выберите модель", "error")
            return

        # Обновляем локально, затем сохраняем модель на сервер
        self.current_syntax_data[self.selected_syntax_type] = self.syntax_info_text.toPlainText()

        if not parent or not getattr(parent, "ws_connected", False):
            parent.show_toast("Нет связи с сервером", "error")
            return

        # Загружаем текущую модель, обновляем и сохраняем
        req = parent.ws_client.send_request("load_model", id=self.selected_model_id)

        def on_loaded(data):
            if not data.get("success"):
                parent.show_toast("Ошибка загрузки модели для сохранения синтаксиса", "error")
                return

            mdl = data.get("model", {})
            mdl["syntax"] = self.current_syntax_data

            req2 = parent.ws_client.send_request("save_model", id=self.selected_model_id, model=mdl)

            def on_saved(resp):
                if resp.get("success"):
                    parent.show_toast("Синтаксис сохранён", "success")
                    self.syntax_info_text.setPlainText("")
                    self.syntax_list.clearSelection()
                    self.selected_syntax_type = None
                else:
                    parent.show_toast(f"Ошибка сохранения синтаксиса: {resp.get('error')}", "error")

            parent.pending_requests[req2] = on_saved

        parent.pending_requests[req] = on_loaded

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
