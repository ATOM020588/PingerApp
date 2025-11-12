# widgets/engineers_management.py

import os
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QPushButton, QLineEdit, QFormLayout, QComboBox, QWidget,
    QApplication
)
from PyQt6.QtCore import Qt, QTimer

class EngineersManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление сотрудниками СКС")
        self.setFixedSize(800, 600)
        self.masters = []
        self.engineers = []
        self.selected_master_id = None
        self.setup_ui()
        self.load_masters()
        self.load_engineers()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        title = QLabel("Управление сотрудниками СКС")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        layout.addLayout(columns_layout)

        # Мастера
        master_column = QVBoxLayout()
        master_label = QLabel("Мастер участка")
        master_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        master_label.setStyleSheet("font-size: 12px;")
        master_column.addWidget(master_label)
        self.master_list = QListWidget()
        self.master_list.setMinimumHeight(400)
        self.master_list.itemClicked.connect(self.update_engineer_list)
        master_column.addWidget(self.master_list)
        master_buttons = QHBoxLayout()
        self.add_master_button = QPushButton("Добавить")
        self.edit_master_button = QPushButton("Редактировать")
        self.delete_master_button = QPushButton("Удалить")
        master_buttons.addWidget(self.add_master_button)
        master_buttons.addWidget(self.edit_master_button)
        master_buttons.addWidget(self.delete_master_button)
        master_column.addLayout(master_buttons)
        columns_layout.addLayout(master_column, stretch=1)

        # Техники
        engineer_column = QVBoxLayout()
        engineer_label = QLabel("Техники")
        engineer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        engineer_label.setStyleSheet("font-size: 12px;")
        engineer_column.addWidget(engineer_label)
        self.engineer_list = QListWidget()
        self.engineer_list.setMinimumHeight(400)
        engineer_column.addWidget(self.engineer_list)
        engineer_buttons = QHBoxLayout()
        self.add_engineer_button = QPushButton("Добавить")
        self.edit_engineer_button = QPushButton("Редактировать")
        self.delete_engineer_button = QPushButton("Удалить")
        engineer_buttons.addWidget(self.add_engineer_button)
        engineer_buttons.addWidget(self.edit_engineer_button)
        engineer_buttons.addWidget(self.delete_engineer_button)
        engineer_column.addLayout(engineer_buttons)
        columns_layout.addLayout(engineer_column, stretch=1)


        # Подключение
        self.add_master_button.clicked.connect(self.add_master)
        self.edit_master_button.clicked.connect(self.edit_master)
        self.delete_master_button.clicked.connect(self.delete_master)
        self.add_engineer_button.clicked.connect(self.add_engineer)
        self.edit_engineer_button.clicked.connect(self.edit_engineer)
        self.delete_engineer_button.clicked.connect(self.delete_engineer)

        # === ВОССТАНОВЛЕННЫЕ СТИЛИ ===
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-size: 14px; }
            QListWidget { 
                background-color: #444; 
                color: #FFC107; 
                border: 1px solid #FFC107; 
                border-radius: 4px; 
                padding: 8px;
            }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QPushButton { 
                background-color: #444; 
                color: #FFC107; 
                border: none; 
                border: 1px solid #555; 
                border-radius: 4px; 
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #555; }
            QLineEdit {
                background-color: #444;
                color: #FFC107;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
        """)

    def load_masters(self):
        file = "lists/masters.json"
        os.makedirs(os.path.dirname(file), exist_ok=True)
        try:
            if os.path.exists(file):
                with open(file, "r", encoding="utf-8") as f:
                    self.masters = json.load(f)
            else:
                self.masters = []
            self.update_master_list()
        except json.JSONDecodeError as e:
            self.show_toast(f"Ошибка в файле мастеров: {e}", "error")
            self.masters = []

    def update_master_list(self):
        self.master_list.clear()
        for master in self.masters:
            self.master_list.addItem(master["fio"])
            if master["id"] == self.selected_master_id:
                self.master_list.setCurrentRow(self.masters.index(master))

    def load_engineers(self):
        file = "lists/engineers.json"
        os.makedirs(os.path.dirname(file), exist_ok=True)
        try:
            if os.path.exists(file):
                with open(file, "r", encoding="utf-8") as f:
                    self.engineers = json.load(f)
            else:
                self.engineers = []
            self.update_engineer_list()
        except json.JSONDecodeError as e:
            self.show_toast(f"Ошибка в файле техников: {e}", "error")
            self.engineers = []

    def update_engineer_list(self, item=None):
        if item:
            fio = item.text()
            master = next((m for m in self.masters if m["fio"] == fio), None)
            self.selected_master_id = master["id"] if master else None
        engineers = [e for e in self.engineers if e.get("master_id") == self.selected_master_id]
        self.engineer_list.clear()
        for e in engineers:
            self.engineer_list.addItem(e["fio"])

    def add_master(self):
        self._edit_master_dialog("add")

    def edit_master(self):
        item = self.master_list.currentItem()
        if not item:
            self.show_toast("Выберите мастера", "error")
            return
        self._edit_master_dialog("edit", item.text())

    def _edit_master_dialog(self, mode, fio=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление мастера" if mode == "add" else "Редактирование мастера")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()
        form = QFormLayout()
        input_field = QLineEdit(fio or "")
        form.addRow("Ф.И.О.:", input_field)
        layout.addLayout(form)
        error = QLabel()
        error.setStyleSheet("color: #FFC107; ")
        layout.addWidget(error)
        buttons = QHBoxLayout()
        save = QPushButton("ОК")
        cancel = QPushButton("Отмена")
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        dialog.setLayout(layout)
        dialog.setStyleSheet("""
            QLabel { font-size: 12px; color: #FFC107; padding: 2px 0px 0px 5px; }
            QLineEdit { height: 18px; padding: 4px 5px; }
        """)

        def save_master():
            name = input_field.text().strip()
            if not name:
                error.setText("Введите Ф.И.О.!")
                return
            if mode == "add":
                self.masters.append({"id": str(int(datetime.now().timestamp() * 1000)), "fio": name})
            else:
                master = next(m for m in self.masters if m["fio"] == fio)
                master["fio"] = name
            self.save_masters()
            self.load_masters()
            dialog.accept()
            self.parent().show_toast(f"Мастер {'добавлен' if mode == 'add' else 'обновлён'}", "success")

        save.clicked.connect(save_master)
        cancel.clicked.connect(dialog.reject)
        dialog.exec()

    def delete_master(self):
        item = self.master_list.currentItem()
        if not item:
            self.show_toast("Выберите мастера", "error")
            return
        master = next(m for m in self.masters if m["fio"] == item.text())
        if any(e.get("master_id") == master["id"] for e in self.engineers):
            self.parent().show_toast("Нельзя удалить мастера с техниками", "error")
            return
        self.masters = [m for m in self.masters if m["id"] != master["id"]]
        self.save_masters()
        self.load_masters()
        self.show_toast("Мастер удалён", "success")

    def add_engineer(self):
        self._edit_engineer_dialog("add")

    def edit_engineer(self):
        item = self.engineer_list.currentItem()
        if not item:
            self.parent().show_toast("Выберите техника", "error")
            return
        self._edit_engineer_dialog("edit", item.text())

    def _edit_engineer_dialog(self, mode, fio=None):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление техника" if mode == "add" else "Редактирование техника")
        dialog.setFixedSize(300, 200)
        layout = QVBoxLayout()
        form = QFormLayout()
        form.setVerticalSpacing(20)
        fio_input = QLineEdit(fio or "")
        master_combo = QComboBox()
        for m in self.masters:
            master_combo.addItem(m["fio"], m["id"])
        master_combo.setStyleSheet("""
            QLabel { font-size: 12px; color: #FFC107; padding: 0px 0px 2px 5px; }
            QComboBox { background-color: #444; color: #FFC107; height: 20px; border-radius: 4px; padding: 4px; }
            QComboBox::drop-down { border: none; }
        """)
        form.addRow("Ф.И.О.:", fio_input)
        form.addRow("Мастер:", master_combo)
        layout.addLayout(form)
        error = QLabel()
        error.setStyleSheet("color: #FFC107;")
        layout.addWidget(error)
        buttons = QHBoxLayout()
        save = QPushButton("ОК")
        cancel = QPushButton("Отмена")
        buttons.addWidget(save)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        dialog.setLayout(layout)
        dialog.setStyleSheet("""
            QLabel { font-size: 12px; color: #FFC107; padding: 4px 0px 0px 5px; }
            QLineEdit { height: 18px; padding: 4px 5px; }
        """)

        def save_engineer():
            name = fio_input.text().strip()
            master_id = master_combo.currentData()
            if not name or not master_id:
                error.setText("Заполните все поля!")
                return
            if mode == "add":
                self.engineers.append({"id": str(int(datetime.now().timestamp() * 1000)), "fio": name, "master_id": master_id})
            else:
                eng = next(e for e in self.engineers if e["fio"] == fio)
                eng["fio"] = name
                eng["master_id"] = master_id
            self.save_engineers()
            self.update_engineer_list()
            dialog.accept()
            self.parent().show_toast(f"Техник {'добавлен' if mode == 'add' else 'обновлён'}", "success")

        save.clicked.connect(save_engineer)
        cancel.clicked.connect(dialog.reject)
        dialog.exec()

    def delete_engineer(self):
        item = self.engineer_list.currentItem()
        if not item:
            self.show_toast("Выберите техника", "error")
            return
        eng = next(e for e in self.engineers if e["fio"] == item.text())
        self.engineers = [e for e in self.engineers if e["id"] != eng["id"]]
        self.save_engineers()
        self.update_engineer_list()
        self.show_toast("Техник удалён", "success")

    def save_masters(self):
        file = "lists/masters.json"
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w", encoding="utf-8") as f:
            json.dump(self.masters, f, ensure_ascii=False, indent=4)

    def save_engineers(self):
        file = "lists/engineers.json"
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, "w", encoding="utf-8") as f:
            json.dump(self.engineers, f, ensure_ascii=False, indent=4)