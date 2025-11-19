import json
import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QLineEdit, QPushButton, QFormLayout
)
from PyQt6.QtCore import Qt


class VlanManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Управление VLAN")
        self.setFixedSize(800, 400)

        self.vlans = []
        self.selected_vlan_id = None

        self.setup_ui()
        self.load_vlan_list_from_server()

    # ============================================================
    # UI
    # ============================================================

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addSpacing(10)
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        layout.addLayout(columns_layout)

        # -------- Левая колонка — список VLAN --------
        vlan_list_column = QVBoxLayout()
        vlan_list_label = QLabel("Список упр. VLAN")
        vlan_list_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vlan_list_column.addWidget(vlan_list_label)

        self.vlan_list = QListWidget()
        self.vlan_list.setMinimumHeight(280)
        self.vlan_list.itemClicked.connect(self.update_vlan_form)
        vlan_list_column.addWidget(self.vlan_list)
        vlan_list_column.addStretch()

        columns_layout.addLayout(vlan_list_column, stretch=1)

        # -------- Правая колонка — форма --------
        vlan_form_column = QVBoxLayout()
        vlan_form_label = QLabel("Параметры VLAN")
        vlan_form_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vlan_form_column.addWidget(vlan_form_label)

        form_layout = QFormLayout()

        self.vlan_id_input = QLineEdit()
        self.vlan_id_input.setMaximumWidth(250)

        self.vlan_gateway_input = QLineEdit()
        self.vlan_gateway_input.setMaximumWidth(250)

        self.vlan_mask_input = QLineEdit()
        self.vlan_mask_input.setMaximumWidth(250)

        form_layout.addRow("VLAN ID:", self.vlan_id_input)
        form_layout.addRow("Default Gateway:", self.vlan_gateway_input)
        form_layout.addRow("Mask /XX:", self.vlan_mask_input)

        self.vlan_error_label = QLabel()
        self.vlan_error_label.setStyleSheet("color: #FFC107;")
        form_layout.addRow(self.vlan_error_label)

        vlan_form_column.addLayout(form_layout)
        vlan_form_column.addStretch()

        columns_layout.addLayout(vlan_form_column, stretch=1)

        # -------- Кнопки --------
        buttons_layout = QHBoxLayout()
        layout.addSpacing(10)

        self.add_vlan_button = QPushButton("Добавить VLAN")
        self.edit_vlan_button = QPushButton("Изменить VLAN")
        self.delete_vlan_button = QPushButton("Удалить VLAN")

        buttons_layout.addWidget(self.add_vlan_button)
        buttons_layout.addWidget(self.edit_vlan_button)
        buttons_layout.addWidget(self.delete_vlan_button)
        layout.addLayout(buttons_layout)

        # подключение
        self.add_vlan_button.clicked.connect(self.add_vlan)
        self.edit_vlan_button.clicked.connect(self.edit_vlan)
        self.delete_vlan_button.clicked.connect(self.delete_vlan)

        # -------- Стили --------
        self.setStyleSheet("""
            QLabel { color: #FFC107; font-size: 12px; }
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; height: 18px; padding: 6px; }
            QPushButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)

    # ============================================================
    # Загрузка VLAN с сервера
    # ============================================================

    def load_vlan_list_from_server(self):
        req_id = self.parent().ws_client.send_request("list_mngmt_vlan")

        if req_id:
            self.parent().pending_requests[req_id] = self.on_vlan_list_loaded

    def on_vlan_list_loaded(self, response):
        if not response.get("success"):
            self.parent().show_toast("Ошибка загрузки VLAN с сервера", "error")
            return

        self.vlans = response.get("vlans", [])
        self.update_vlan_list()

    # ============================================================
    # Обновление списка
    # ============================================================

    def update_vlan_list(self):
        self.vlan_list.clear()

        for vlan in self.vlans:
            self.vlan_list.addItem(vlan["id"])

        if self.selected_vlan_id:
            items = self.vlan_list.findItems(self.selected_vlan_id, Qt.MatchFlag.MatchExactly)
            if items:
                self.vlan_list.setCurrentItem(items[0])

    # ============================================================
    # Заполнение формы
    # ============================================================

    def update_vlan_form(self, item):
        if not item:
            return

        self.selected_vlan_id = item.text()
        vlan = next((v for v in self.vlans if v["id"] == self.selected_vlan_id), None)

        if vlan:
            self.vlan_id_input.setText(vlan["id"])
            self.vlan_gateway_input.setText(vlan["gateway"])
            self.vlan_mask_input.setText(vlan["mask"])

        self.vlan_error_label.clear()

    # ============================================================
    # Добавить
    # ============================================================

    def add_vlan(self):
        id_ = self.vlan_id_input.text().strip()
        gateway = self.vlan_gateway_input.text().strip()
        mask = self.vlan_mask_input.text().strip()

        # проверки
        if not id_ or not gateway or not mask:
            self.vlan_error_label.setText("Заполните все поля")
            return

        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", gateway):
            self.vlan_error_label.setText("Неверный формат Default Gateway")
            return

        if not re.match(r"^/([0-9]|[1-2][0-9]|3[0-2])$", mask):
            self.vlan_error_label.setText("Маска должна быть /XX")
            return

        if any(v["id"] == id_ for v in self.vlans):
            self.vlan_error_label.setText("VLAN с таким ID уже существует")
            return

        # добавление
        self.vlans.append({"id": id_, "gateway": gateway, "mask": mask})
        self.selected_vlan_id = id_

        self.save_vlans_to_server()
        self.update_vlan_list()

        self.parent().show_toast("VLAN добавлен", "success")

    # ============================================================
    # Изменить
    # ============================================================

    def edit_vlan(self):
        if not self.selected_vlan_id:
            self.vlan_error_label.setText("Выберите VLAN для редактирования")
            return

        id_ = self.vlan_id_input.text().strip()
        gateway = self.vlan_gateway_input.text().strip()
        mask = self.vlan_mask_input.text().strip()

        if not id_ or not gateway or not mask:
            self.vlan_error_label.setText("Заполните все поля")
            return

        if not re.match(r"^(\d{1,3}\.){3}\d{1,3}$", gateway):
            self.vlan_error_label.setText("Неверный gateway")
            return

        if not re.match(r"^/([0-9]|[1-2][0-9]|3[0-2])$", mask):
            self.vlan_error_label.setText("Маска должна быть /XX")
            return

        if id_ != self.selected_vlan_id and any(v["id"] == id_ for v in self.vlans):
            self.vlan_error_label.setText("VLAN с таким ID уже существует")
            return

        # обновить
        idx = next((i for i, v in enumerate(self.vlans) if v["id"] == self.selected_vlan_id), -1)
        if idx == -1:
            self.vlan_error_label.setText("Ошибка: VLAN не найден")
            return

        self.vlans[idx] = {"id": id_, "gateway": gateway, "mask": mask}
        self.selected_vlan_id = id_

        self.save_vlans_to_server()
        self.update_vlan_list()

        self.parent().show_toast("VLAN изменён", "success")

    # ============================================================
    # Удалить
    # ============================================================

    def delete_vlan(self):
        if not self.selected_vlan_id:
            self.vlan_error_label.setText("Выберите VLAN для удаления")
            return

        self.vlans = [v for v in self.vlans if v["id"] != self.selected_vlan_id]
        self.selected_vlan_id = None

        self.save_vlans_to_server()
        self.update_vlan_list()

        self.vlan_id_input.clear()
        self.vlan_gateway_input.clear()
        self.vlan_mask_input.clear()

        self.parent().show_toast("VLAN удалён", "success")

    # ============================================================
    # Сохранение на сервер
    # ============================================================

    def save_vlans_to_server(self):
        req_id = self.parent().ws_client.send_request(
            "save_mngmt_vlan",
            vlans=self.vlans
        )

        if req_id:
            self.parent().pending_requests[req_id] = self.on_vlans_saved

    def on_vlans_saved(self, response):
        if not response.get("success"):
            self.parent().show_toast("Ошибка сохранения VLAN", "error")
