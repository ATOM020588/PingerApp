# widgets/operators_dialog.py

import os
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLineEdit,
    QComboBox, QCheckBox, QListWidget, QWidget, QApplication
)
from PyQt6.QtCore import Qt, QTimer


class ToastWidget(QWidget):
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


class OperatorsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление операторами")
        self.setFixedSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        button_layout = QHBoxLayout()
        self.configure_groups_button = QPushButton("Настройка групп")
        self.create_operator_button = QPushButton("Создать оператора")
        self.edit_operator_button = QPushButton("Редактировать оператора")
        self.delete_operator_button = QPushButton("Удалить оператора")
        button_layout.addWidget(self.configure_groups_button)
        button_layout.addWidget(self.create_operator_button)
        button_layout.addWidget(self.edit_operator_button)
        button_layout.addWidget(self.delete_operator_button)
        layout.addLayout(button_layout)
        layout.setSpacing(10)
        self.operators_table = QTableWidget()
        self.operators_table.setColumnCount(5)
        self.operators_table.setHorizontalHeaderLabels(["Фамилия", "Имя", "Логин", "Отдел/Должность", "Последняя активность"])
        self.operators_table.verticalHeader().setVisible(False)
        self.operators_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.operators_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.operators_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.operators_table)

        self.configure_groups_button.clicked.connect(self.show_group_modal)
        self.create_operator_button.clicked.connect(lambda: self.show_operator_modal("create"))
        self.edit_operator_button.clicked.connect(lambda: self.show_operator_modal("edit"))
        self.delete_operator_button.clicked.connect(self.delete_operator)

        self.load_groups()
        self.load_operators()

        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QTableWidget { background-color: #444; color: #FFC107; border: 1px solid #555; }
            QTableWidget::item:hover { background-color: #555; }
            QTableWidget::item:selected { background-color: #75736b; color: #333; }
            QHeaderView::section { background-color: #333333; color: #FFC107; border: 1px solid #555; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

    def load_operators(self):
        users_path = "operators/users.json"
        os.makedirs(os.path.dirname(users_path), exist_ok=True)
        try:
            if os.path.exists(users_path):
                with open(users_path, "r", encoding="utf-8") as f:
                    self.users_data = json.load(f)
                self.operators_table.setRowCount(len(self.users_data))
                for row, op in enumerate(self.users_data):
                    for col, value in enumerate([
                        op.get("surname", ""),
                        op.get("name", ""),
                        op.get("login", ""),
                        op.get("department", ""),
                        op.get("last_activity", "Нет данных")
                    ]):
                        item = QTableWidgetItem(value)
                        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                        self.operators_table.setItem(row, col, item)
            else:
                self.users_data = []
                self.operators_table.setRowCount(1)
                item = QTableWidgetItem("Список операторов пуст")
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.operators_table.setItem(0, 0, item)
                self.operators_table.setSpan(0, 0, 1, 5)
        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в {users_path}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле операторов: {str(e)}", "error")
            self.users_data = []
            self.operators_table.setRowCount(1)
            item = QTableWidgetItem("Ошибка загрузки операторов")
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.operators_table.setItem(0, 0, item)
            self.operators_table.setSpan(0, 0, 1, 5)

    def load_groups(self):
        groups_path = "operators/groups.json"
        os.makedirs(os.path.dirname(groups_path), exist_ok=True)
        try:
            if os.path.exists(groups_path):
                with open(groups_path, "r", encoding="utf-8") as f:
                    self.groups_data = json.load(f)
            else:
                self.groups_data = []
        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в {groups_path}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле групп: {str(e)}", "error")
            self.groups_data = []

    def show_operator_modal(self, mode):
        selected_row = self.operators_table.currentRow()
        if mode == "edit" and selected_row == -1:
            self.show_toast("Выберите оператора для редактирования", "error")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Создать оператора" if mode == "create" else "Редактировать оператора")
        dialog.setFixedSize(600, 450)
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        form_layout = QHBoxLayout()
        operator_column = QVBoxLayout()
        operator_column.addWidget(QLabel("Оператор"))
        self.surname_input = QLineEdit()
        self.name_input = QLineEdit()
        self.department_input = QLineEdit()
        self.login_input = QLineEdit()
        self.group_select = QComboBox()
        for group in self.groups_data:
            self.group_select.addItem(group["name"], group["id"])
        operator_column.addWidget(QLabel("Фамилия:"))
        operator_column.addWidget(self.surname_input)
        operator_column.addWidget(QLabel("Имя:"))
        operator_column.addWidget(self.name_input)
        operator_column.addWidget(QLabel("Отдел:"))
        operator_column.addWidget(self.department_input)
        operator_column.addWidget(QLabel("Логин:"))
        operator_column.addWidget(self.login_input)
        operator_column.addWidget(QLabel("Группа:"))
        operator_column.addWidget(self.group_select)

        permissions_column = QVBoxLayout()
        permissions_column.addWidget(QLabel("Права:"))
        self.permissions_checkboxes = {}
        permissions = [
            ("edit_maps", "Изменение карт"),
            ("edit_syntax", "Изменение синтаксиса"),
            ("view_global_problems", "Просмотр глоб. проблем"),
            ("add_global_problems", "Добавлять глоб. проблемы"),
            ("view_operators", "Просмотр операторов"),
            ("edit_operators", "Изменение операторов"),
            ("telnet", "Telnet"),
            ("flood", "Flood"),
            ("configure_switch", "Настройка свитча"),
            ("reset_firewall", "Сброс Firewall"),
            ("edit_dhcp_mode", "Изменение DHCP режима"),
            ("inventory", "Инвентаризация"),
            ("add_discrepancies", "Добавлять несоответствия"),
            ("global_report_filter", "Фильтр в глоб. репорте"),
            ("add_global_no_call", "Добавлять глоб. без звонка")
        ]
        for key, label in permissions:
            checkbox = QCheckBox(label)
            self.permissions_checkboxes[key] = checkbox
            permissions_column.addWidget(checkbox)

        form_layout.addLayout(operator_column)
        form_layout.addLayout(permissions_column)
        layout.addLayout(form_layout)
        layout.addSpacing(20)
        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        save_button.setFixedWidth(150)
        cancel_button = QPushButton("Отмена")
        cancel_button.setFixedWidth(150)
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { font-size: 12px; color: #FFC107; padding: 4px 0px 0px 5px; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; height: 18px; padding: 6px; }
            QComboBox { background-color: #444; color: #FFC107; height: 20px; border-radius: 4px; padding: 6px; }
            QComboBox::drop-down { border: none; }
            QCheckBox { color: #FFC107; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)

        if mode == "edit":
            op = self.users_data[selected_row]
            self.surname_input.setText(op.get("surname", ""))
            self.name_input.setText(op.get("name", ""))
            self.department_input.setText(op.get("department", ""))
            self.login_input.setText(op.get("login", ""))
            group_index = self.group_select.findData(op.get("group", ""))
            if group_index != -1:
                self.group_select.setCurrentIndex(group_index)
            for key, checkbox in self.permissions_checkboxes.items():
                checkbox.setChecked(op.get("permissions", {}).get(key, False))
            self.operator_id = op["id"]

        save_button.clicked.connect(lambda: self.save_operator(dialog, mode))
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def save_operator(self, dialog, mode):
        operator = {
            "surname": self.surname_input.text(),
            "name": self.name_input.text(),
            "department": self.department_input.text(),
            "login": self.login_input.text(),
            "group": self.group_select.currentData(),
            "permissions": {key: checkbox.isChecked() for key, checkbox in self.permissions_checkboxes.items()}
        }
        if mode == "edit":
            operator["id"] = self.operator_id
        else:
            operator["id"] = str(int(datetime.now().timestamp() * 1000))

        users_path = "operators/users.json"
        os.makedirs(os.path.dirname(users_path), exist_ok=True)
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump(self.users_data + [operator] if mode == "create" else [op if op["id"] != operator["id"] else operator for op in self.users_data], f, ensure_ascii=False, indent=4)

        self.load_operators()
        dialog.accept()

    def delete_operator(self):
        selected_row = self.operators_table.currentRow()
        if selected_row == -1:
            self.show_toast("Выберите оператора для удаления", "error")
            return

        op_id = self.users_data[selected_row]["id"]
        self.users_data = [op for op in self.users_data if op["id"] != op_id]
        users_path = "operators/users.json"
        os.makedirs(os.path.dirname(users_path), exist_ok=True)
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump(self.users_data, f, ensure_ascii=False, indent=4)

        self.load_operators()

    def show_group_modal(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройка групп")
        dialog.setFixedSize(600, 600)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        dialog.setLayout(layout)

        form_layout = QHBoxLayout()
        group_list_column = QVBoxLayout()
        group_list_column.addWidget(QLabel("Список групп:"))
        self.group_list = QListWidget()
        for group in self.groups_data:
            self.group_list.addItem(group["name"])
        group_list_column.addWidget(self.group_list)

        permissions_column = QVBoxLayout()
        permissions_column.addWidget(QLabel("Настройки группы:"))
        self.group_name_input = QLineEdit()
        permissions_column.addWidget(QLabel("Название группы:"))
        permissions_column.addWidget(self.group_name_input)
        self.group_permissions_checkboxes = {}
        permissions = [
            ("edit_maps", "Изменение карт"),
            ("edit_syntax", "Изменение синтаксиса"),
            ("view_global_problems", "Просмотр глоб. проблем"),
            ("add_global_problems", "Добавлять глоб. проблемы"),
            ("view_operators", "Просмотр операторов"),
            ("edit_operators", "Изменение операторов"),
            ("telnet", "Telnet"),
            ("flood", "Flood"),
            ("configure_switch", "Настройка свитча"),
            ("reset_firewall", "Сброс Firewall"),
            ("edit_dhcp_mode", "Изменение DHCP режима"),
            ("inventory", "Инвентаризация"),
            ("add_discrepancies", "Добавлять несоответствия"),
            ("global_report_filter", "Фильтр в глоб. репорте"),
            ("add_global_no_call", "Добавлять глоб. без звонка")
        ]
        for key, label in permissions:
            checkbox = QCheckBox(label)
            self.group_permissions_checkboxes[key] = checkbox
            permissions_column.addWidget(checkbox)

        form_layout.addLayout(group_list_column)
        form_layout.addLayout(permissions_column)
        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        add_group_button = QPushButton("Добавить группу")
        delete_group_button = QPushButton("Удалить группу")
        cancel_button = QPushButton("Выйти")
        buttons_layout.addWidget(add_group_button)
        buttons_layout.addWidget(delete_group_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #555; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 2px; height: 20px; }
            QCheckBox { color: #FFC107; }
            QToolButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 6px; } 
            QToolButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

        self.group_list.itemClicked.connect(self.load_group)
        add_group_button.clicked.connect(lambda: self.save_group(dialog))
        delete_group_button.clicked.connect(self.delete_group)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def load_group(self, item):
        group_name = item.text()
        group = next((g for g in self.groups_data if g["name"] == group_name), None)
        if group:
            self.group_name_input.setText(group["name"])
            for key, checkbox in self.group_permissions_checkboxes.items():
                checkbox.setChecked(group.get("permissions", {}).get(key, False))
            self.group_id = group["id"]

    def save_group(self, dialog):
        group = {
            "name": self.group_name_input.text(),
            "permissions": {key: checkbox.isChecked() for key, checkbox in self.group_permissions_checkboxes.items()}
        }
        if self.group_name_input.text() == "":
            self.show_toast("Введите название группы!", "error")
            return
        if hasattr(self, 'group_id'):
            group["id"] = self.group_id
        else:
            group["id"] = str(int(datetime.now().timestamp() * 1000))

        groups_path = "operators/groups.json"
        os.makedirs(os.path.dirname(groups_path), exist_ok=True)
        with open(groups_path, "w", encoding="utf-8") as f:
            json.dump(self.groups_data + [group] if not hasattr(self, 'group_id') else [g if g["id"] != group["id"] else group for g in self.groups_data], f, ensure_ascii=False, indent=4)

        self.load_groups()
        dialog.accept()

    def delete_group(self):
        selected_item = self.group_list.currentItem()
        if not selected_item:
            self.show_toast("Выберите группу для удаления", "error")
            return

        group_name = selected_item.text()
        group = next((g for g in self.groups_data if g["name"] == group_name), None)
        if group:
            self.groups_data = [g for g in self.groups_data if g["id"] != group["id"]]
            groups_path = "operators/groups.json"
            os.makedirs(os.path.dirname(groups_path), exist_ok=True)
            with open(groups_path, "w", encoding="utf-8") as f:
                json.dump(self.groups_data, f, ensure_ascii=False, indent=4)
            self.load_groups()

    def show_toast(self, message, toast_type="info"):
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)