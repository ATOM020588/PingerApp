# widgets/vlan_management.py

import os
import re
import json
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QPushButton,
    QFormLayout, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication


class ToastWidget(QWidget):
    """Всплывающее уведомление (toast) — автономная копия для модуля."""
    def __init__(self, message, toast_type="info"):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        layout = QHBoxLayout()
        label = QLabel(message)
        layout.addWidget(label)
        self.setLayout(layout)
        self.setStyleSheet(f"""
            QWidget {{
                padding: 10px 20px;
                border-radius: 4px;
                color: #181818;
                font-size: 16px;
                font-weight: bold;
                background-color: {'#4CAF50' if toast_type == 'success' else '#F44336' if toast_type == 'error' else '#808080'};
            }}
        """)
        QTimer.singleShot(3000, self.close)


class VlanManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление VLAN")
        self.setFixedSize(800, 400)
        self.vlans = []
        self.selected_vlan_id = None
        self.setup_ui()
        self.load_vlan_list()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Редактирование VLAN")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        labels_layout = QHBoxLayout()
        vlan_list_label = QLabel("Список упр. VLAN")
        vlan_list_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vlan_form_label = QLabel("Параметры VLAN")
        vlan_form_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        labels_layout.addWidget(vlan_list_label, stretch=1)
        labels_layout.addWidget(vlan_form_label, stretch=1)
        labels_layout.setContentsMargins(10, 0, 10, 0)
        layout.addLayout(labels_layout)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        layout.addLayout(columns_layout)

        # Левая колонка — список VLAN
        vlan_list_column = QVBoxLayout()
        self.vlan_table = QTableWidget()
        self.vlan_table.setColumnCount(1)
        self.vlan_table.setHorizontalHeaderLabels(["ID"])
        self.vlan_table.verticalHeader().setVisible(False)
        self.vlan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.vlan_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.vlan_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.vlan_table.itemClicked.connect(self.update_vlan_form)
        vlan_list_column.addWidget(self.vlan_table)
        columns_layout.addLayout(vlan_list_column, stretch=1)

        # Правая колонка — форма редактирования
        vlan_form_column = QVBoxLayout()
        form_layout = QFormLayout()
        self.vlan_id_input = QLineEdit()
        self.vlan_gateway_input = QLineEdit()
        self.vlan_mask_input = QLineEdit()
        form_layout.addRow("ID:", self.vlan_id_input)
        form_layout.addRow("Default Gateway:", self.vlan_gateway_input)
        form_layout.addRow("Mask /XX:", self.vlan_mask_input)
        self.vlan_error_label = QLabel()
        self.vlan_error_label.setStyleSheet("color: #FFC107;")
        form_layout.addRow(self.vlan_error_label)
        vlan_form_column.addLayout(form_layout)
        columns_layout.addLayout(vlan_form_column, stretch=1)

        # Кнопки
        buttons_layout = QHBoxLayout()
        self.add_vlan_button = QPushButton("Добавить VLAN")
        self.edit_vlan_button = QPushButton("Изменить VLAN")
        self.delete_vlan_button = QPushButton("Удалить VLAN")
        buttons_layout.addWidget(self.add_vlan_button)
        buttons_layout.addWidget(self.edit_vlan_button)
        buttons_layout.addWidget(self.delete_vlan_button)
        layout.addLayout(buttons_layout)

        # Подключение кнопок
        self.add_vlan_button.clicked.connect(self.add_vlan)
        self.edit_vlan_button.clicked.connect(self.edit_vlan)
        self.delete_vlan_button.clicked.connect(self.delete_vlan)

        # Стили
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QTableWidget { background-color: #444; color: #FFC107; border: 1px solid #555; }
            QTableWidget::item:hover { background-color: #666; }
            QTableWidget::item:selected { background-color: #75736b; color: #333; }
            QHeaderView::section { background-color: #555; color: #FFC107; border: 1px solid #555; }
            QLineEdit { background-color: #333; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QLineEdit:focus { border-color: #FFC107; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px 20px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; font-size: 14px; }
            QFormLayout { margin: 15px; }
        """)

    def load_vlan_list(self):
        vlan_file = "lists/mngmtvlan.json"
        os.makedirs(os.path.dirname(vlan_file), exist_ok=True)
        try:
            if os.path.exists(vlan_file):
                with open(vlan_file, "r", encoding="utf-8") as f:
                    self.vlans = json.load(f)
            else:
                self.vlans = []
            self.update_vlan_table()
        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в {vlan_file}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле VLAN: {str(e)}", "error")
            self.vlans = []
            self.update_vlan_table()

    def update_vlan_table(self):
        self.vlan_table.setRowCount(len(self.vlans))
        for row, vlan in enumerate(self.vlans):
            item = QTableWidgetItem(vlan["id"])
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self.vlan_table.setItem(row, 0, item)
            if vlan["id"] == self.selected_vlan_id:
                self.vlan_table.selectRow(row)

    def update_vlan_form(self, item):
        row = self.vlan_table.row(item)
        self.selected_vlan_id = self.vlans[row]["id"]
        vlan = next((v for v in self.vlans if v["id"] == self.selected_vlan_id), None)
        if vlan:
            self.vlan_id_input.setText(vlan["id"])
            self.vlan_gateway_input.setText(vlan["gateway"])
            self.vlan_mask_input.setText(vlan["mask"])
        else:
            self.vlan_id_input.clear()
            self.vlan_gateway_input.clear()
            self.vlan_mask_input.clear()
        self.vlan_error_label.clear()

    def add_vlan(self):
        id_ = self.vlan_id_input.text().strip()
        gateway = self.vlan_gateway_input.text().strip()
        mask = self.vlan_mask_input.text().strip()

        if not id_ or not gateway or not mask:
            self.vlan_error_label.setText("Заполните все поля")
            return

        ip_regex = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(ip_regex, gateway):
            self.vlan_error_label.setText("Неверный формат Default Gateway")
            return

        mask_regex = r"^/([1-2]?[0-9]|3[0-2])$"
        if not re.match(mask_regex, mask):
            self.vlan_error_label.setText("Маска должна быть в формате /XX (1-32)")
            return

        if any(v["id"] == id_ for v in self.vlans):
            self.vlan_error_label.setText("VLAN с таким ID уже существует")
            return

        self.vlans.append({"id": id_, "gateway": gateway, "mask": mask})
        self.selected_vlan_id = id_
        self.save_vlan_list()
        self.update_vlan_table()
        self.update_vlan_form(self.vlan_table.item(self.vlan_table.currentRow(), 0))
        self.show_toast("VLAN добавлен", "success")

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

        ip_regex = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(ip_regex, gateway):
            self.vlan_error_label.setText("Неверный формат Default Gateway")
            return

        mask_regex = r"^/([1-2]?[0-9]|3[0-2])$"
        if not re.match(mask_regex, mask):
            self.vlan_error_label.setText("Маска должна быть в формате /XX (1-32)")
            return

        if id_ != self.selected_vlan_id and any(v["id"] == id_ for v in self.vlans):
            self.vlan_error_label.setText("VLAN с таким ID уже существует")
            return

        vlan_index = next((i for i, v in enumerate(self.vlans) if v["id"] == self.selected_vlan_id), -1)
        if vlan_index != -1:
            self.vlans[vlan_index] = {"id": id_, "gateway": gateway, "mask": mask}
            self.selected_vlan_id = id_
            self.save_vlan_list()
            self.update_vlan_table()
            self.update_vlan_form(self.vlan_table.item(self.vlan_table.currentRow(), 0))
            self.show_toast("VLAN изменён", "success")
        else:
            self.vlan_error_label.setText("Ошибка: VLAN не найден")
            self.show_toast("Ошибка при изменении VLAN", "error")

    def delete_vlan(self):
        if not self.selected_vlan_id:
            self.vlan_error_label.setText("Выберите VLAN для удаления")
            return
        self.vlans = [v for v in self.vlans if v["id"] != self.selected_vlan_id]
        self.selected_vlan_id = None
        self.save_vlan_list()
        self.update_vlan_table()
        self.vlan_id_input.clear()
        self.vlan_gateway_input.clear()
        self.vlan_mask_input.clear()
        self.vlan_error_label.clear()
        self.show_toast("VLAN удалён", "success")

    def save_vlan_list(self):
        vlan_file = "lists/mngmtvlan.json"
        os.makedirs(os.path.dirname(vlan_file), exist_ok=True)
        try:
            with open(vlan_file, "w", encoding="utf-8") as f:
                json.dump(self.vlans, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения VLAN: {str(e)}")
            self.show_toast(f"Ошибка сохранения VLAN: {str(e)}", "error")

    def show_toast(self, message, toast_type="info"):
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)