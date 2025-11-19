# widgets/operators_dialog.py

import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QLineEdit,
    QComboBox, QCheckBox, QListWidget, QWidget, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon
import hashlib
import base64


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
        # parent expected to be MainWindow with ws_client and pending_requests
        self.parent_window = parent
        self.ws = getattr(parent, "ws_client", None)

        self.users_data = []      # visible user records (as used for table)
        self.users_full = []      # full user records (with password hashes) loaded from file_get
        self.groups_data = []     # groups

        self.setWindowTitle("Управление операторами")
        self.setFixedSize(800, 600)
        self.setup_ui()

        # Load from server
        self.load_groups()
        self.load_users()

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
        self.operators_table.setHorizontalHeaderLabels(
            ["Фамилия", "Имя", "Логин", "Отдел/Должность", "Последняя активность"]
        )
        self.operators_table.verticalHeader().setVisible(False)
        self.operators_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.operators_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.operators_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.operators_table.cellDoubleClicked.connect(lambda r, c: self.show_operator_modal("edit"))

        layout.addWidget(self.operators_table)

        # connect buttons
        self.configure_groups_button.clicked.connect(self.show_group_modal)
        self.create_operator_button.clicked.connect(lambda: self.show_operator_modal("create"))
        self.edit_operator_button.clicked.connect(lambda: self.show_operator_modal("edit"))
        self.delete_operator_button.clicked.connect(self.delete_operator)

        # styles (original look)
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

    # -------------------- Load groups & users from server --------------------

    def load_groups(self):
        """
        Load full groups list from server using file_get to preserve structure.
        """
        if not self.ws or not self.parent_window:
            # fallback: show toast
            self.show_toast("WebSocket client not available", "error")
            return

        req_id = self.ws.send_request("file_get", path="operators/groups.json")
        if not req_id:
            self.show_toast("Не удалось отправить запрос групп", "error")
            return

        def callback(resp):
            if resp.get("success"):
                data = resp.get("data", [])
                # server might return list or None
                self.groups_data = data if isinstance(data, list) else []
            else:
                # fallback to empty
                self.groups_data = []
            # nothing to refresh visually here until group modal is opened

        self.parent_window.pending_requests[req_id] = callback

    def load_users(self):
        """
        Load full users (with password hashes) via file_get, so we can preserve password on edits.
        Use file_get path "operators/users.json".
        """
        if not self.ws or not self.parent_window:
            self.show_toast("WebSocket client not available", "error")
            return

        req_id = self.ws.send_request("file_get", path="operators/users.json")
        if not req_id:
            self.show_toast("Не удалось отправить запрос операторов", "error")
            return

        def callback(resp):
            if resp.get("success"):
                data = resp.get("data", [])
                self.users_full = data if isinstance(data, list) else []
                # Build users_data for display (users without exposing password)
                self.users_data = [
                    {
                        "surname": u.get("surname", ""),
                        "name": u.get("name", ""),
                        "login": u.get("login", ""),
                        "department": u.get("department", ""),
                        "last_activity": u.get("last_activity", ""),
                        "id": u.get("id"),
                        "group": u.get("group"),
                        # do not include password in visible data
                    } for u in self.users_full
                ]
                self.populate_table()
            else:
                self.show_toast(f"Ошибка загрузки операторов: {resp.get('error', '')}", "error")
                self.users_full = []
                self.users_data = []
                self.populate_table()

        self.parent_window.pending_requests[req_id] = callback

    def populate_table(self):
        self.operators_table.setRowCount(len(self.users_data))
        for row, op in enumerate(self.users_data):
            vals = [
                op.get("surname", ""),
                op.get("name", ""),
                op.get("login", ""),
                op.get("department", ""),
                op.get("last_activity", "Нет данных")
            ]
            for col, value in enumerate(vals):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.operators_table.setItem(row, col, item)

    # -------------------- Operator modal (create/edit) --------------------

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

        # form fields (original order)
        surname_input = QLineEdit()
        name_input = QLineEdit()
        department_input = QLineEdit()
        login_input = QLineEdit()
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)  # hidden
        group_select = QComboBox()

        # populate group_select from self.groups_data (use 'name' as in your groups.json)
        group_select.clear()
        for group in self.groups_data:
            title = group.get("name") or group.get("group_name") or "Без имени"
            group_select.addItem(title, group.get("id"))

        operator_column.addWidget(QLabel("Фамилия:"))
        operator_column.addWidget(surname_input)
        operator_column.addWidget(QLabel("Имя:"))
        operator_column.addWidget(name_input)
        operator_column.addWidget(QLabel("Отдел:"))
        operator_column.addWidget(department_input)
        operator_column.addWidget(QLabel("Логин:"))
        operator_column.addWidget(login_input)
        operator_column.addWidget(QLabel("Пароль:"))  # added password field under login
        operator_column.addWidget(password_input)
        operator_column.addWidget(QLabel("Группа:"))
        operator_column.addWidget(group_select)

        permissions_column = QVBoxLayout()
        permissions_column.addWidget(QLabel("Права:"))
        self.permissions_checkboxes_local = {}
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
            self.permissions_checkboxes_local[key] = checkbox
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

        # apply styles for dialog (same as your original)
        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { font-size: 12px; color: #FFC107; padding: 4px 0px 0px 5px; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; height: 18px; padding: 6px; }
            QComboBox { background-color: #444; color: #FFC107; height: 20px; border-radius: 4px; padding: 6px; }
            QComboBox::drop-down { border: none; }
            QCheckBox { color: #FFC107; border: none; }
            QCheckBox::indicator { background-color: #444; border: 1px solid #FFC107; width: 14px; height: 14px; }
            QCheckBox::indicator:checked { background-color: #FFC107; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)

        operator_id = None
        if mode == "edit":
            # fill fields from selected operator; use users_full to get password if needed
            op = self.users_data[selected_row]
            operator_id = op.get("id")
            # find full record
            full = next((u for u in self.users_full if str(u.get("id")) == str(operator_id)), None)
            surname_input.setText(op.get("surname", ""))
            name_input.setText(op.get("name", ""))
            department_input.setText(op.get("department", ""))
            login_input.setText(op.get("login", ""))
            # group select by .group field (string id)
            gid = full.get("group") if full else op.get("group")
            if gid is not None:
                idx = group_select.findData(gid)
                if idx != -1:
                    group_select.setCurrentIndex(idx)
            # permissions
            perm_src = full.get("permissions") if full else {}
            for key, checkbox in self.permissions_checkboxes_local.items():
                checkbox.setChecked(bool(perm_src.get(key, False)))
            # password_input left empty — if left empty on save, old hash will be preserved

        def on_save():
            # collect operator data
            op = {
                "surname": surname_input.text().strip(),
                "name": name_input.text().strip(),
                "department": department_input.text().strip(),
                "login": login_input.text().strip(),
                "group": group_select.currentData(),
                "permissions": {k: bool(cb.isChecked()) for k, cb in self.permissions_checkboxes_local.items()},
            }

            pwd = password_input.text()
            if mode == "edit":
                op["id"] = operator_id
                # find full existing record to preserve password if pwd empty
                existing = next((u for u in self.users_full if str(u.get("id")) == str(operator_id)), None)
                if pwd:
                    op["password"] = hashlib.sha256(pwd.encode()).hexdigest()
                else:
                    # preserve existing hash if available
                    if existing and "password" in existing:
                        op["password"] = existing["password"]
            else:
                # create new
                op["id"] = str(int(datetime.now().timestamp() * 1000))
                if not pwd:
                    self.show_toast("Введите пароль", "error")
                    return
                op["password"] = hashlib.sha256(pwd.encode()).hexdigest()

            # update users_full list
            if mode == "edit":
                self.users_full = [u if str(u.get("id")) != str(op["id"]) else {**u, **op} for u in self.users_full]
            else:
                self.users_full.append(op)

            # send save to server
            self.save_users_to_server()
            dialog.accept()

        save_button.clicked.connect(on_save)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    # -------------------- Saving users to server --------------------

    def save_users_to_server(self):
        """
        Send save_operators with 'operators' key expected by server.
        """
        if not self.ws or not self.parent_window:
            self.show_toast("WebSocket client not available", "error")
            return

        req_id = self.ws.send_request("save_operators", operators=self.users_full)
        if not req_id:
            self.show_toast("Не удалось отправить запрос на сервер", "error")
            return

        def callback(resp):
            if resp.get("success"):
                # reload users to reflect any server-side normalizations
                self.load_users()
                self.show_toast("Операторы сохранены", "success")
            else:
                self.show_toast(f"Ошибка сохранения: {resp.get('error', '')}", "error")

        self.parent_window.pending_requests[req_id] = callback

    # -------------------- Delete operator --------------------

    def delete_operator(self):
        selected_row = self.operators_table.currentRow()
        if selected_row == -1:
            self.show_toast("Выберите оператора для удаления", "error")
            return

        op = self.users_data[selected_row]
        op_id = op.get("id")
        # remove from full list
        self.users_full = [u for u in self.users_full if str(u.get("id")) != str(op_id)]
        # save
        self.save_users_to_server()

    # -------------------- Group modal --------------------

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
        group_list = QListWidget()
        for group in self.groups_data:
            group_list.addItem(group.get("name", ""))
        group_list_column.addWidget(group_list)

        permissions_column = QVBoxLayout()
        permissions_column.addWidget(QLabel("Настройки группы:"))
        group_name_input = QLineEdit()
        permissions_column.addWidget(QLabel("Название группы:"))
        permissions_column.addWidget(group_name_input)
        group_permissions_checkboxes = {}
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
            group_permissions_checkboxes[key] = checkbox
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
            QCheckBox { color: #FFC107; border: none; }
            QCheckBox::indicator { background-color: #444; border: 1px solid #FFC107; width: 14px; height: 14px; }
            QCheckBox::indicator:checked { background-color: #FFC107; }
            QToolButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 6px; } 
            QToolButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

        def load_group(item):
            group_name = item.text()
            group = next((g for g in self.groups_data if (g.get("name") or "") == group_name), None)
            if group:
                group_name_input.setText(group.get("name", ""))
                for key, checkbox in group_permissions_checkboxes.items():
                    checkbox.setChecked(group.get("permissions", {}).get(key, False))
                dialog._editing_group_id = group.get("id")

        def add_group():
            name = group_name_input.text().strip()
            if not name:
                self.show_toast("Введите название группы!", "error")
                return
            # build group object
            gid = getattr(dialog, "_editing_group_id", None)
            group = {
                "name": name,
                "permissions": {k: bool(cb.isChecked()) for k, cb in group_permissions_checkboxes.items()}
            }
            if gid:
                group["id"] = gid
                # replace in list
                self.groups_data = [g if str(g.get("id")) != str(gid) else group for g in self.groups_data]
            else:
                group["id"] = str(int(datetime.now().timestamp() * 1000))
                self.groups_data.append(group)

            # save groups to server
            self.save_groups_to_server()
            # refresh group list widget
            group_list.clear()
            for g in self.groups_data:
                group_list.addItem(g.get("name", ""))
            dialog._editing_group_id = None
            group_name_input.clear()

        def delete_group():
            sel = group_list.currentItem()
            if not sel:
                self.show_toast("Выберите группу для удаления", "error")
                return
            name = sel.text()
            g = next((x for x in self.groups_data if (x.get("name") or "") == name), None)
            if g:
                self.groups_data = [x for x in self.groups_data if x.get("id") != g.get("id")]
                self.save_groups_to_server()
                group_list.clear()
                for gg in self.groups_data:
                    group_list.addItem(gg.get("name", ""))

        group_list.itemClicked.connect(load_group)
        add_group_button.clicked.connect(add_group)
        delete_group_button.clicked.connect(delete_group)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    # -------------------- Save groups to server --------------------

    def save_groups_to_server(self):
        if not self.ws or not self.parent_window:
            self.show_toast("WebSocket client not available", "error")
            return

        req_id = self.ws.send_request("save_groups", groups=self.groups_data)
        if not req_id:
            self.show_toast("Не удалось отправить запрос групп", "error")
            return

        def callback(resp):
            if resp.get("success"):
                self.show_toast("Группы сохранены", "success")
                # maybe reload groups from server
                self.load_groups()
            else:
                self.show_toast(f"Ошибка сохранения групп: {resp.get('error','')}", "error")

        self.parent_window.pending_requests[req_id] = callback

    # -------------------- Show toast --------------------

    def show_toast(self, message, toast_type="info"):
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)
