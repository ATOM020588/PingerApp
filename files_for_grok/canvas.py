import sys
import json
import os
import math
import shutil
from PyQt6.QtWidgets import (QGraphicsPixmapItem, QMessageBox)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGraphicsView, QGraphicsScene, QDialog, QLineEdit)
from PyQt6.QtWidgets import (QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFormLayout, QSpinBox, QHeaderView, QComboBox, QListWidget, QCheckBox, QTextEdit, QFileDialog)
from PyQt6.QtGui import QAction, QColor, QBrush, QPen, QPainter, QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
import pickle
import re
from datetime import datetime

class MapNameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создание карты")
        self.setFixedSize(300, 150)
        layout = QVBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Название карты")
        layout.addWidget(QLabel("Введите название карты"))
        layout.addWidget(self.input)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FFC107;")
        layout.addWidget(self.error_label)
        buttons = QHBoxLayout()
        ok_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QLabel { color: #FFC107; }
        """)

class OpenMapDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Открыть карту")
        self.setFixedSize(785, 400)
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Название", "Дата и время изменения", "Последние изменения"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.populate_table()
        layout.addWidget(QLabel("Выберите карту"))
        layout.addWidget(self.table)
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #FFC107;")
        layout.addWidget(self.error_label)
        buttons = QHBoxLayout()
        ok_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QTableWidget { background-color: #444; color: #FFC107; border: 1px solid #555; }
            QTableWidget::item:hover { background-color: #555; }
            QTableWidget::item:selected { background-color: #75736b; color: #333; }
            QHeaderView::section { background-color: #333333; color: #FFC107; border: 1px solid #555; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QLabel { color: #FFC107; }
        """)

    def populate_table(self):
        maps_dir = "maps"
        if not os.path.exists(maps_dir):
            os.makedirs(maps_dir)
        map_files = [f for f in os.listdir(maps_dir) if f.endswith(".json")]
        self.table.setRowCount(len(map_files))
        for row, map_file in enumerate(map_files):
            try:
                with open(os.path.join(maps_dir, map_file), "r", encoding="utf-8") as f:
                    map_data = json.load(f)
                map_name = map_data.get("map", {}).get("name", map_file[:-5] if not map_file.startswith("map_") else map_file[4:-5])
                mod_time = map_data.get("map", {}).get("mod_time", "Неизвестно")
                last_editor = map_data.get("map", {}).get("last_adm", "Неизвестно")
                for col, value in enumerate([map_name, mod_time, f"Последний редактор: {last_editor}"]):
                    item = QTableWidgetItem(value)
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    self.table.setItem(row, col, item)
            except Exception as e:
                for col, value in enumerate([map_file[:-5], "Ошибка", f"Ошибка загрузки: {str(e)}"]):
                    item = QTableWidgetItem(value)
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    self.table.setItem(row, col, item)

class MapSettingsDialog(QDialog):
    def __init__(self, parent=None, map_data=None):
        super().__init__(parent)
        self.setWindowTitle("Параметры карты")
        self.resize(200, 100)
        layout = QVBoxLayout()
        self.setLayout(layout)
        form_layout = QFormLayout()
        self.width_input = QSpinBox()
        self.width_input.setRange(100, 10000)
        self.width_input.setValue(int(map_data["map"].get("width", 1200)))
        self.height_input = QSpinBox()
        self.height_input.setRange(100, 10000)
        self.height_input.setValue(int(map_data["map"].get("height", 800)))
        width_label = QLabel("Ширина:")
        width_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        height_label = QLabel("Высота:")
        height_label.setStyleSheet("color: #FFC107; font-weight: bold;")
        form_layout.addRow(width_label, self.width_input)
        form_layout.addRow(height_label, self.height_input)
        layout.addLayout(form_layout)
        buttons = QHBoxLayout()
        ok_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107;}
            QSpinBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QSpinBox::up-button { width: 25px; height: 20px; }
            QSpinBox::down-button { width: 25px; height: 20px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px; }
            QPushButton:hover { background-color: #555; }
            QFormLayout > QLabel { color: #FFC107; }
        """)

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

        buttons_layout = QHBoxLayout()
        self.add_vlan_button = QPushButton("Добавить VLAN")
        self.edit_vlan_button = QPushButton("Изменить VLAN")
        self.delete_vlan_button = QPushButton("Удалить VLAN")
        buttons_layout.addWidget(self.add_vlan_button)
        buttons_layout.addWidget(self.edit_vlan_button)
        buttons_layout.addWidget(self.delete_vlan_button)
        layout.addLayout(buttons_layout)

        self.add_vlan_button.clicked.connect(self.add_vlan)
        self.edit_vlan_button.clicked.connect(self.edit_vlan)
        self.delete_vlan_button.clicked.connect(self.delete_vlan)

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
        id = self.vlan_id_input.text().strip()
        gateway = self.vlan_gateway_input.text().strip()
        mask = self.vlan_mask_input.text().strip()

        if not id or not gateway or not mask:
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

        vlan_index = next((i for i, v in enumerate(self.vlans) if v["id"] == id), -1)
        if vlan_index != -1:
            self.vlan_error_label.setText("VLAN с таким ID уже существует")
            return

        self.vlans.append({"id": id, "gateway": gateway, "mask": mask})
        self.selected_vlan_id = id
        self.save_vlan_list()
        self.update_vlan_table()
        self.update_vlan_form(self.vlan_table.item(self.vlan_table.currentRow(), 0) if self.vlan_table.currentRow() >= 0 else None)
        self.show_toast("VLAN добавлен", "success")

    def edit_vlan(self):
        if not self.selected_vlan_id:
            self.vlan_error_label.setText("Выберите VLAN для редактирования")
            return

        id = self.vlan_id_input.text().strip()
        gateway = self.vlan_gateway_input.text().strip()
        mask = self.vlan_mask_input.text().strip()

        if not id or not gateway or not mask:
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

        if id != self.selected_vlan_id and any(v["id"] == id for v in self.vlans):
            self.vlan_error_label.setText("VLAN с таким ID уже существует")
            return

        vlan_index = next((i for i, v in enumerate(self.vlans) if v["id"] == self.selected_vlan_id), -1)
        if vlan_index != -1:
            self.vlans[vlan_index] = {"id": id, "gateway": gateway, "mask": mask}
            self.selected_vlan_id = id
            self.save_vlan_list()
            self.update_vlan_table()
            self.update_vlan_form(self.vlan_table.item(self.vlan_table.currentRow(), 0) if self.vlan_table.currentRow() >= 0 else None)
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

        model_column = QVBoxLayout()
        model_label = QLabel("Модель")
        model_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        model_column.addWidget(model_label)
        self.model_list = QListWidget()
        self.model_list.setMinimumHeight(400)
        self.model_list.itemClicked.connect(self.update_firmware_text)
        model_column.addWidget(self.model_list)
        columns_layout.addLayout(model_column, stretch=2)

        firmware_column = QVBoxLayout()
        firmware_label = QLabel("Прошивки")
        firmware_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        firmware_column.addWidget(firmware_label)
        self.firmware_text = QTextEdit()
        self.firmware_text.setMinimumHeight(400)
        firmware_column.addWidget(self.firmware_text)
        columns_layout.addLayout(firmware_column, stretch=8)

        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Сохранить")
        self.save_button.clicked.connect(self.save_firmware)
        buttons_layout.addWidget(self.save_button)
        layout.addLayout(buttons_layout)

        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-size: 14px; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QTextEdit { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border-radius: 4px; padding: 8px 16px; }
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
            self.show_toast(f"Ошибка формата JSON в файле прошивок: {str(e)}", "error")
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
            self.show_toast("Выберите модель для сохранения прошивки", "error")
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

    def show_toast(self, message, toast_type="info"):
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)

class EngineersManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление сотрудниками СКС")
        self.setFixedSize(800, 600)
        self.masters = []
        self.engineers = []
        self.selected_master_id = None
        self.selected_engineer_id = None
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

        master_column = QVBoxLayout()
        master_label = QLabel("Мастер участка")
        master_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

        engineer_column = QVBoxLayout()
        engineer_label = QLabel("Техники")
        engineer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

        self.add_master_button.clicked.connect(self.add_master)
        self.edit_master_button.clicked.connect(self.edit_master)
        self.delete_master_button.clicked.connect(self.delete_master)
        self.add_engineer_button.clicked.connect(self.add_engineer)
        self.edit_engineer_button.clicked.connect(self.edit_engineer)
        self.delete_engineer_button.clicked.connect(self.delete_engineer)

        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-size: 14px; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; padding: 8px; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)

    def load_masters(self):
        masters_file = "lists/masters.json"
        os.makedirs(os.path.dirname(masters_file), exist_ok=True)
        try:
            if os.path.exists(masters_file):
                with open(masters_file, "r", encoding="utf-8") as f:
                    self.masters = json.load(f)
            else:
                self.masters = []
            self.update_master_list()
        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в {masters_file}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле мастеров: {str(e)}", "error")
            self.masters = []
            self.update_master_list()

    def update_master_list(self):
        self.master_list.clear()
        for master in self.masters:
            self.master_list.addItem(master["fio"])
            if master["id"] == self.selected_master_id:
                self.master_list.setCurrentRow(self.masters.index(master))

    def load_engineers(self):
        engineers_file = "lists/engineers.json"
        os.makedirs(os.path.dirname(engineers_file), exist_ok=True)
        try:
            if os.path.exists(engineers_file):
                with open(engineers_file, "r", encoding="utf-8") as f:
                    self.engineers = json.load(f)
            else:
                self.engineers = []
            self.update_engineer_list()
        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в {engineers_file}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле техников: {str(e)}", "error")
            self.engineers = []
            self.update_engineer_list()

    def update_engineer_list(self, item=None):
        if item:
            fio = item.text()
            master = next((m for m in self.masters if m["fio"] == fio), None)
            if master:
                self.selected_master_id = master["id"]
            else:
                self.selected_master_id = None
        if self.selected_master_id:
            filtered_engineers = [e for e in self.engineers if e.get("master_id") == self.selected_master_id]
        else:
            filtered_engineers = []
        self.engineer_list.clear()
        for engineer in filtered_engineers:
            self.engineer_list.addItem(engineer["fio"])

    def add_master(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление мастера")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        form_layout = QFormLayout()
        fio_input = QLineEdit()
        form_layout.addRow("Ф.И.О.:", fio_input)
        layout.addLayout(form_layout)

        error_label = QLabel()
        error_label.setStyleSheet("color: #FFC107;")
        layout.addWidget(error_label)

        buttons = QHBoxLayout()
        save_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

        def save_master():
            fio = fio_input.text().strip()
            if not fio:
                error_label.setText("Введите Ф.И.О.!")
                return
            master_data = {
                "id": str(int(datetime.now().timestamp() * 1000)),
                "fio": fio
            }
            self.masters.append(master_data)
            self.save_masters()
            self.load_masters()
            dialog.accept()
            self.show_toast("Мастер добавлен", "success")

        save_button.clicked.connect(save_master)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def edit_master(self):
        selected_item = self.master_list.currentItem()
        if not selected_item:
            self.show_toast("Выберите мастера для редактирования", "error")
            return

        fio = selected_item.text()
        master = next((m for m in self.masters if m["fio"] == fio), None)
        if not master:
            self.show_toast("Ошибка: мастер не найден", "error")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактирование мастера")
        dialog.setFixedSize(300, 150)
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        form_layout = QFormLayout()
        fio_input = QLineEdit()
        fio_input.setText(master["fio"])
        form_layout.addRow("Ф.И.О.:", fio_input)
        layout.addLayout(form_layout)

        error_label = QLabel()
        error_label.setStyleSheet("color: #FFC107;")
        layout.addWidget(error_label)

        buttons = QHBoxLayout()
        save_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

        def save_master():
            fio = fio_input.text().strip()
            if not fio:
                error_label.setText("Введите Ф.И.О.!")
                return
            master_index = next((i for i, m in enumerate(self.masters) if m["id"] == master["id"]), -1)
            if master_index != -1:
                self.masters[master_index]["fio"] = fio
                self.save_masters()
                self.load_masters()
                self.update_engineer_list()
                dialog.accept()
                self.show_toast("Мастер обновлен", "success")
            else:
                error_label.setText("Ошибка: мастер не найден")
                self.show_toast("Ошибка при обновлении мастера", "error")

        save_button.clicked.connect(save_master)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def delete_master(self):
        selected_item = self.master_list.currentItem()
        if not selected_item:
            self.show_toast("Выберите мастера для удаления", "error")
            return

        fio = selected_item.text()
        master = next((m for m in self.masters if m["fio"] == fio), None)
        if not master:
            self.show_toast("Ошибка: мастер не найден", "error")
            return

        # Проверка, есть ли инженеры, связанные с этим мастером
        linked_engineers = [e for e in self.engineers if e.get("master_id") == master["id"]]
        if linked_engineers:
            self.show_toast("Нельзя удалить мастера, у которого есть техники", "error")
            return

        self.masters = [m for m in self.masters if m["id"] != master["id"]]
        self.save_masters()
        self.load_masters()
        self.update_engineer_list()
        self.show_toast("Мастер удален", "success")

    def add_engineer(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление техника")
        dialog.setFixedSize(300, 200)
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        form_layout = QFormLayout()
        fio_input = QLineEdit()
        master_select = QComboBox()
        for master in self.masters:
            master_select.addItem(master["fio"], master["id"])
        form_layout.addRow("Ф.И.О.:", fio_input)
        form_layout.addRow("Мастер участка:", master_select)
        layout.addLayout(form_layout)

        error_label = QLabel()
        error_label.setStyleSheet("color: #FFC107;")
        layout.addWidget(error_label)

        buttons = QHBoxLayout()
        save_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QComboBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

        if self.selected_master_id:
            master_select.setCurrentIndex(master_select.findData(self.selected_master_id))

        def save_engineer():
            fio = fio_input.text().strip()
            master_id = master_select.currentData()
            if not fio:
                error_label.setText("Введите Ф.И.О.!")
                return
            if not master_id:
                error_label.setText("Выберите мастера участка!")
                return
            engineer_data = {
                "id": str(int(datetime.now().timestamp() * 1000)),
                "fio": fio,
                "master_id": master_id
            }
            self.engineers.append(engineer_data)
            self.save_engineers()
            self.update_engineer_list()
            dialog.accept()
            self.show_toast("Техник добавлен", "success")

        save_button.clicked.connect(save_engineer)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def edit_engineer(self):
        selected_item = self.engineer_list.currentItem()
        if not selected_item:
            self.show_toast("Выберите техника для редактирования", "error")
            return

        fio = selected_item.text()
        engineer = next((e for e in self.engineers if e["fio"] == fio), None)
        if not engineer:
            self.show_toast("Ошибка: техник не найден", "error")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Редактирование техника")
        dialog.setFixedSize(300, 200)
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        form_layout = QFormLayout()
        fio_input = QLineEdit()
        fio_input.setText(engineer["fio"])
        master_select = QComboBox()
        for master in self.masters:
            master_select.addItem(master["fio"], master["id"])
        master_select.setCurrentIndex(master_select.findData(engineer["master_id"]))
        form_layout.addRow("Ф.И.О.:", fio_input)
        form_layout.addRow("Мастер участка:", master_select)
        layout.addLayout(form_layout)

        error_label = QLabel()
        error_label.setStyleSheet("color: #FFC107;")
        layout.addWidget(error_label)

        buttons = QHBoxLayout()
        save_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QComboBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

        def save_engineer():
            fio = fio_input.text().strip()
            master_id = master_select.currentData()
            if not fio:
                error_label.setText("Введите Ф.И.О.!")
                return
            if not master_id:
                error_label.setText("Выберите мастера участка!")
                return
            engineer_index = next((i for i, e in enumerate(self.engineers) if e["id"] == engineer["id"]), -1)
            if engineer_index != -1:
                self.engineers[engineer_index] = {
                    "id": engineer["id"],
                    "fio": fio,
                    "master_id": master_id
                }
                self.save_engineers()
                self.update_engineer_list()
                dialog.accept()
                self.show_toast("Техник обновлен", "success")
            else:
                error_label.setText("Ошибка: техник не найден")
                self.show_toast("Ошибка при обновлении техника", "error")

        save_button.clicked.connect(save_engineer)
        cancel_button.clicked.connect(dialog.reject)

        dialog.exec()

    def delete_engineer(self):
        selected_item = self.engineer_list.currentItem()
        if not selected_item:
            self.show_toast("Выберите техника для удаления", "error")
            return

        fio = selected_item.text()
        engineer = next((e for e in self.engineers if e["fio"] == fio), None)
        if engineer:
            self.engineers = [e for e in self.engineers if e["id"] != engineer["id"]]
            self.save_engineers()
            self.update_engineer_list()
            self.show_toast("Техник удален", "success")

    def save_masters(self):
        masters_file = "lists/masters.json"
        os.makedirs(os.path.dirname(masters_file), exist_ok=True)
        try:
            with open(masters_file, "w", encoding="utf-8") as f:
                json.dump(self.masters, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения мастеров: {str(e)}")
            self.show_toast(f"Ошибка сохранения мастеров: {str(e)}", "error")

    def save_engineers(self):
        engineers_file = "lists/engineers.json"
        os.makedirs(os.path.dirname(engineers_file), exist_ok=True)
        try:
            with open(engineers_file, "w", encoding="utf-8") as f:
                json.dump(self.engineers, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения техников: {str(e)}")
            self.show_toast(f"Ошибка сохранения техников: {str(e)}", "error")

    def show_toast(self, message, toast_type="info"):
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)

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
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
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
        dialog.setFixedSize(600, 400)
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

        buttons_layout = QHBoxLayout()
        save_button = QPushButton("Сохранить")
        cancel_button = QPushButton("Отмена")
        buttons_layout.addWidget(save_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QComboBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: url(none); width: 10px; height: 10px; }
            QCheckBox { color: #FFC107; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QLabel { color: #FFC107; }
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
        dialog.setFixedSize(600, 450)
        layout = QVBoxLayout()
        layout.setSpacing(10)
        dialog.setLayout(layout)

        form_layout = QHBoxLayout()
        group_list_column = QVBoxLayout()
        group_list_column.addWidget(QLabel("Список групп"))
        self.group_list = QListWidget()
        for group in self.groups_data:
            self.group_list.addItem(group["name"])
        group_list_column.addWidget(self.group_list)

        permissions_column = QVBoxLayout()
        permissions_column.addWidget(QLabel("Настройка группы"))
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
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; height: 40px; }
            QCheckBox { color: #FFC107; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
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
        
        

class ModelsManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление моделями")
        self.setMinimumSize(1350, 900)
        self.models_path = os.path.join("models", "models.json")
        self.models_dir = "models"
        self.images_dir = "images"
        self.firmware_path = os.path.join("lists", "firmware.json")
        self.selected_model_id = None
        self.current_syntax_data = {}
        self.selected_syntax_type = None
        self.firmware_data = []
        self.init_ui()
        self.load_models()

    def init_ui(self):
        main_layout = QVBoxLayout()
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

        content_layout = QHBoxLayout()
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

        self.preview_image = QLabel()
        self.preview_image.setFixedSize(300, 300)
        self.preview_image.setStyleSheet("border-radius: 4px; background-color: #555;")
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        details_column.addWidget(QLabel("Предпросмотр картинки"))
        details_column.addWidget(self.preview_image)
        self.upload_image = QPushButton("Выбрать изображение")
        self.upload_image.clicked.connect(self.upload_image_file)
        details_column.addWidget(self.upload_image)
        self.image_path = None

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

        syntax_column = QVBoxLayout()
        syntax_layout = QHBoxLayout()
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
                self.models_list.addItem(model["model_name"])
                self.models_list.item(self.models_list.count() - 1).setData(Qt.ItemDataRole.UserRole, model["id"])
        except Exception as e:
            self.parent().show_toast(f"Ошибка загрузки списка моделей: {str(e)}", "error")

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
            print(f"Копирование файла: {self.image_path} в {destination}")  # Отладка
            if self.image_path != destination:  # Проверка, чтобы избежать SameFileError
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
            print(f"Копирование файла: {self.image_path} в {destination}")  # Отладка
            if self.image_path != destination:  # Проверка, чтобы избежать SameFileError
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
        self.neobills.setCurrentText("")
        self.uplink.clear()
        self.ports_count.clear()
        self.mag_ports.clear()
        self.firmware.setCurrentText("")
        self.preview_image.clear()
        self.image_path = None
        self.current_syntax_data = {}
        self.syntax_info_text.setPlainText("")
        self.syntax_list.clearSelection()
        self.selected_syntax_type = None
        self.selected_model_id = None

# Класс отрисовки карты
class MapCanvas(QGraphicsView):
    def __init__(self, map_data=None, parent=None):
        super().__init__(parent)
        self.parent = parent 
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.map_data = map_data or {
            "map": {"name": "Unnamed", "width": "1200", "height": "800"},
            "switches": [],
            "plan_switches": [],
            "users": [],
            "soaps": [],
            "legends": [],
            "magistrals": []
        }
        self.setStyleSheet("border-radius: 12px; border: 3px solid #3d3d3d;")
        self.setSceneRect(0, 0, int(self.map_data["map"].get("width", "1200")), int(self.map_data["map"].get("height", "800")))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.is_edit_mode = False
        self._panning = False
        self._last_pos = QPointF()
        self.dragged_node = None
        self.dragged_type = None
        self.dragged_key = None
        self.drag_start_pos = None
        self.dragged_type = None  # "switch", "plan_switch", "user", "soap", "legend"
        self.dragged_key = None   # Ключ в map_data: "switches", "plan_switches", ...
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        print(f"MapCanvas initialized with map_data: {self.map_data}")
        self.render_map()

    def render_map(self):
        print("Rendering map...")
        self.scene.clear()
        self.scene.setBackgroundBrush(QBrush(QColor("#008080")))

        all_nodes = [
            *[{**s, "type": "switch", "x": s["xy"]["x"], "y": s["xy"]["y"]} for s in self.map_data.get("switches", [])],
            *[{**p, "type": "plan_switch", "x": p["xy"]["x"], "y": p["xy"]["y"]} for p in self.map_data.get("plan_switches", [])],
            *[{**u, "type": "user", "x": u["xy"]["x"], "y": u["xy"]["y"]} for u in self.map_data.get("users", [])],
            *[{**s, "type": "soap", "x": s["xy"]["x"], "y": s["xy"]["y"]} for s in self.map_data.get("soaps", [])],
            *[{**l, "type": "legend", "x": l["xy"]["x"], "y": l["xy"]["y"], "name": l["text"]} for l in self.map_data.get("legends", [])]
        ]
        print(f"All nodes: {all_nodes}")

        for node in all_nodes:
            if node["type"] == "legend":
                fill_color = "transparent" if node.get("zalivka") == "0" else node.get("zalivkacolor", "#fff")
                legend_width = float(node.get("width", 100))
                legend_height = float(node.get("height", 50))
                x, y = node["x"], node["y"]
                legend = self.scene.addRect(
                    x, y, legend_width, legend_height,
                    pen=QPen(QColor(node.get("bordercolor", "#000")), float(node.get("borderwidth", 2))),
                    brush=QBrush(QColor(fill_color))
                )
                legend.setZValue(-1)
                print(f"Added legend at ({x}, {y}) with size {legend_width}x{legend_height}")
                text = self.scene.addText(node.get("name") or node.get("text") or "")
                text.setDefaultTextColor(QColor(node.get("textcolor", "#000")))
                text_width = text.boundingRect().width()
                text_height = text.boundingRect().height()
                text_x = x + (legend_width - text_width) / 2
                text_y = y + (legend_height - text_height) / 2
                text.setPos(text_x, text_y)
                font = text.font()
                font.setPixelSize(int(node.get("textsize", 14)))
                font.setBold(True)
                text.setFont(font)
                text.setZValue(-1)
                print(f"Added legend text '{node.get('name') or node.get('text') or ''}' at ({text_x}, {text_y})")

        for link in self.map_data.get("magistrals", []):
            source_node = next((n for n in all_nodes if n["id"] == link["startid"]), None)
            target_node = next((n for n in all_nodes if n["id"] == link["endid"]), None)
            if source_node and target_node:
                source_x, source_y = source_node["x"], source_node["y"]
                target_x, target_y = target_node["x"], target_node["y"]
                pen = QPen(QColor(link.get("color", "#000")), float(link.get("width", 1)))
                if link.get("style") == "psdot":
                    pen.setDashPattern([5, 5])
                self.scene.addLine(source_x, source_y, target_x, target_y, pen)
                print(f"Added line from {source_node['id']} ({source_x}, {source_y}) to {target_node['id']} ({target_x}, {target_y})")

                for port, node, other_node, port_key, far_key, color_key in [
                    (link.get("startport"), source_node, target_node, "startport", "startportfar", "startportcolor"),
                    (link.get("endport"), target_node, source_node, "endport", "endportfar", "endportcolor")
                ]:
                    if port and port != "0":
                        dx = other_node["x"] - node["x"]
                        dy = other_node["y"] - node["y"]
                        length = math.sqrt(dx**2 + dy**2)
                        distance = float(link.get(far_key, 10))
                        if length > 0:
                            dx, dy = dx / length, dy / length
                            port_x = node["x"] + dx * distance
                            port_y = node["y"] + dy * distance
                        else:
                            port_x, port_y = node["x"] + distance, node["y"]

                        port_text = self.scene.addText(str(port))
                        port_text.setDefaultTextColor(QColor(link.get(color_key, "#000080")))
                        font = port_text.font()
                        font.setPixelSize(12)
                        port_text.setFont(font)
                        text_rect = port_text.boundingRect()
                        square_width = text_rect.width() + 4
                        square_height = 15
                        square = self.scene.addRect(
                            port_x - square_width / 2,
                            port_y - square_height / 2,
                            square_width,
                            square_height,
                            pen=QPen(QColor(link.get("color", "#000")), 1),
                            brush=QBrush(QColor("#008080"))
                        )
                        square.setZValue(0)
                        port_text.setPos(port_x - text_rect.width() / 2, port_y - text_rect.height() / 2)
                        port_text.setZValue(1)
                        print(f"Added port {port_key} '{port}' at ({port_x - text_rect.width() / 2}, {port_y - text_rect.height() / 2}) with square {square_width}x{square_height}")

        for node in all_nodes:
            if node["type"] != "legend":
                image_path = None
                overlay_image = None
                if node["type"] == "switch":
                    if node.get("notinstalled") == "-1":
                        image_path = "canvas/Router_off.png"
                        overlay_image = "canvas/other/not_install.png"
                    elif node.get("notsettings") == "-1":
                        image_path = "canvas/Router.png"
                        overlay_image = "canvas/other/not_settings.png"
                    else:
                        image_path = "canvas/Router.png"
                elif node["type"] == "plan_switch":
                    image_path = "canvas/Router_plan.png"
                elif node["type"] == "user":
                    image_path = "canvas/Computer.png"
                elif node["type"] == "soap":
                    image_path = "canvas/Switch.png"

                if image_path:
                    try:
                        pixmap = QPixmap(image_path)
                        item = self.scene.addPixmap(pixmap)
                        image_width = pixmap.width()
                        image_height = pixmap.height()
                        offset_x = image_width / 2
                        offset_y = image_height / 2
                        x, y = node["x"] - offset_x, node["y"] - offset_y
                        item.setPos(x, y)
                        item.setZValue(2)
                        print(f"Added image {node['type']} '{image_path}' at ({x}, {y})")
                    except Exception as e:
                        print(f"Error loading image {image_path}: {str(e)}")
                        color = {"switch": "#555", "plan_switch": "#888", "user": "#00f", "soap": "#0f0"}.get(node["type"])
                        item = self.scene.addRect(node["x"] - 7.5, node["y"] - 6.5, 15, 13, brush=QBrush(QColor(color)))
                        item.setZValue(2)
                        image_width = 15
                        print(f"Fallback: Added rectangle {node['type']} at ({node['x'] - 7.5}, {node['y'] - 6.5})")

                if overlay_image:
                    try:
                        overlay_pixmap = QPixmap(overlay_image)
                        item = self.scene.addPixmap(overlay_pixmap)
                        item.setPos(x, y)
                        item.setZValue(3)
                        print(f"Added overlay image '{overlay_image}' at ({x}, {y})")
                    except Exception as e:
                        print(f"Error loading overlay image {overlay_image}: {str(e)}")

                text = self.scene.addText(node.get("name") or node.get("text") or f"{node['type'].capitalize()} {node['id']}")
                text.setDefaultTextColor(QColor("#dbdbdb"))
                text_width = text.boundingRect().width()
                text_x = node["x"] - text_width / 2
                text_y = node["y"] + offset_y + 15
                text.setPos(text_x, text_y)
                font = text.font()
                font.setPixelSize(12)
                font.setBold(True)
                text.setFont(font)
                text.setZValue(4)
                print(f"Added text '{node.get('name') or node.get('text') or f'{node['type'].capitalize()} {node['id']}'}' at ({text_x}, {text_y})")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            result = self.find_node_by_position(scene_pos)
            if result:
                node, node_type, key = result
                if self.is_edit_mode:
                    # Запускаем перетаскивание
                    self.dragged_node = node
                    self.dragged_type = node_type
                    self.dragged_key = key
                    self.drag_start_pos = scene_pos
                    event.accept()
                    return
                elif node_type == "switch":
                    self.show_switch_info(node)
                elif node_type == "plan_switch":
                    self.show_plan_switch_info(node)
                event.accept()
                return
        elif event.button() == Qt.MouseButton.RightButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            result = self.find_node_by_position(scene_pos)
            if result:
                node, node_type, key = result
                if node_type == "plan_switch":
                    self.show_plan_switch_context_menu(event.position().toPoint(), node)
                else:
                    self.show_context_menu(event.position().toPoint())
            else:
                self.show_context_menu(event.position().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, 'dragged_node') and self.dragged_node:
            scene_pos = self.mapToScene(event.position().toPoint())
            # Обновляем координаты в данных
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            # Перерисовываем
            self.render_map()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, 'dragged_node') and self.dragged_node:
            scene_pos = self.mapToScene(event.position().toPoint())
            # Финальное обновление
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.render_map()
            self.save_map_to_file()
            print(f"Перемещён {self.dragged_type} '{self.dragged_node.get('name', self.dragged_node.get('text', 'без имени'))}' → ({scene_pos.x():.1f}, {scene_pos.y():.1f})")
            # Сброс
            self.dragged_node = None
            self.dragged_type = None
            self.dragged_key = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; }
            QMenu::item { padding: 8px 16px; background-color: #333; }
            QMenu::item:selected { background-color: #555; }
            QMenu::item:disabled { color: #777; }
        """)

        toggle_edit_action = menu.addAction("Выключить редактирование" if self.is_edit_mode else "Включить редактирование")
        toggle_edit_action.triggered.connect(self.trigger_parent_edit_button)
            
        
        add_menu = menu.addMenu("Добавить")
        add_menu.setEnabled(self.is_edit_mode)
        add_switch_action = add_menu.addAction("Упр. свитч")
        add_plan_switch_action = add_menu.addAction("Планируемый упр. свитч")
        add_plan_switch_action.triggered.connect(lambda: self.add_planed_switch(position))
        add_user_action = add_menu.addAction("Клиента")
        add_magistral_action = add_menu.addAction("Магистраль")
        add_soap_action = add_menu.addAction("Мыльницу")
        add_legend_action = add_menu.addAction("Таблицу")

        add_switch_action.triggered.connect(lambda: self.add_node("switch", position))
        add_plan_switch_action.triggered.connect(lambda: self.add_node("plan_switch", position))
        add_user_action.triggered.connect(lambda: self.add_node("user", position))
        add_magistral_action.triggered.connect(lambda: self.add_node("magistral", position))
        add_soap_action.triggered.connect(lambda: self.add_node("soap", position))
        add_legend_action.triggered.connect(lambda: self.add_node("legend", position))

        map_settings_action = menu.addAction("Параметры карты")
        map_settings_action.setEnabled(self.is_edit_mode)
        map_settings_action.triggered.connect(self.trigger_parent_settings_button)

        global_pos = self.mapToGlobal(position)
        menu.exec(global_pos)

    def add_node(self, node_type, position):
        scene_pos = self.mapToScene(position)
        print(f"Adding {node_type} at scene position ({scene_pos.x()}, {scene_pos.y()})")
        
    def trigger_parent_edit_button(self):
        parent = self.window()  # получаем главное окно
        if hasattr(parent, "edit_button"):
            parent.edit_button.click()  #срабатывает сигнал clicked()
        else:
            print("Родительское окно не имеет кнопки edit_button")
            
    def trigger_parent_settings_button(self):
        parent = self.window()  # или self.parent(), если родитель напрямую MainWindow
        if hasattr(parent, "settings_button"):
            parent.settings_button.click()  #имитируем нажатие ЛКМ
            print("Имитация клика по кнопке 'Параметры карты'")
        else:
            print("Родительское окно не имеет кнопки settings_button")
    
    def add_planed_switch(self, position):
        scene_pos = self.mapToScene(position)
        dialog = AddPlanedSwitch(self, scene_pos)
        dialog.exec()

    def draw_planed_switch(self, name, model, note, position):
        image_path = "canvas/Router_plan.png"
        try:
            pixmap = QPixmap(image_path)
            item = self.scene.addPixmap(pixmap)
            item.setPos(position.x(), position.y())
            item.setZValue(2)

            text = self.scene.addText(f"{name} ({model})")
            text.setDefaultTextColor(QColor("#FFD700"))
            text.setPos(position.x(), position.y() + pixmap.height() + 5)
            font = text.font()
            font.setPixelSize(12)
            text.setFont(font)
            text.setZValue(3)

            print(f"Нарисован планируемый свитч '{name}' на ({position.x()}, {position.y()})")
        except Exception as e:
            print(f"Ошибка отрисовки свитча: {e}")
            
    #Генерирует следующий ID для списка (switches, plan_switches и т.д.)
    def get_next_id(self, key):
        items = self.map_data.get(key, [])
        if not items:
            return "1"
        ids = []
        for item in items:
            try:
                ids.append(int(item["id"]))
            except (ValueError, TypeError, KeyError):
                continue
        return str(max(ids) + 1) if ids else "1"

    def show_switch_info(self, switch_data):
        # Добавляем тип, если нет
        if "type" not in switch_data:
            switch_data["type"] = "switch" if switch_data in self.map_data["switches"] else "plan_switch"
        
        dialog = SwitchInfoDialog(switch_data, self)
        dialog.show()

    def show_plan_switch_info(self, plan_switch_data):
        dialog = PlanSwitchInfoDialog(plan_switch_data, self)
        dialog.show()

    def show_plan_switch_context_menu(self, position, plan_switch):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: #FFC107; border: 1px solid #FFC107; border-radius: 4px; }
            QMenu::item { padding: 8px 16px; background-color: #333; }
            QMenu::item:selected { background-color: #555; }
            QMenu::item:disabled { color: #777; }
        """)

        edit_action = menu.addAction("Редактировать")
        config_action = menu.addAction("Настроить")
        delete_action = menu.addAction("Удалить план. свитч")

        edit_action.setEnabled(self.is_edit_mode)
        config_action.setEnabled(self.is_edit_mode)
        delete_action.setEnabled(self.is_edit_mode)

        edit_action.triggered.connect(lambda: self.edit_plan_switch(plan_switch))
        config_action.triggered.connect(lambda: self.show_message("Настройка не реализована"))
        delete_action.triggered.connect(lambda: self.delete_plan_switch(plan_switch))

        global_pos = self.mapToGlobal(position)
        menu.exec(global_pos)

    def edit_plan_switch(self, plan_switch):
        position = QPointF(plan_switch["xy"]["x"], plan_switch["xy"]["y"])
        dialog = AddPlanedSwitch(self, position, plan_switch)
        if dialog.exec():
            self.render_map()
            self.save_map_to_file()

    def delete_plan_switch(self, plan_switch):
        msg = self.styled_messagebox(
            "Удаление",
            f"Удалить планируемый свитч '<b>{plan_switch['name']}</b>'?",
            QMessageBox.Icon.Question
        )
        yes_btn = msg.addButton("Да", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(yes_btn)

        if msg.exec() == 0:
            self.map_data["plan_switches"].remove(plan_switch)
            self.render_map()
            self.save_map_to_file()

    def save_map_to_file(self):
        # Предполагаем, что путь к файлу в self.parent.current_map_file
        if hasattr(self.parent, "current_map_file") and self.parent.current_map_file:
            with open(self.parent.current_map_file, 'w', encoding='utf-8') as f:
                json.dump(self.map_data, f, ensure_ascii=False, indent=2)
            print(f"Карта сохранена в {self.parent.current_map_file}")
        else:
            print("Путь к файлу карты не задан")

    def show_message(self, text):
        QMessageBox.information(self, "Инфо", text)

    def find_node_by_position(self, pos):
        tolerance = 50
        candidates = [
            (self.map_data.get("switches", []), "switch", "switches"),
            (self.map_data.get("plan_switches", []), "plan_switch", "plan_switches"),
            (self.map_data.get("users", []), "user", "users"),
            (self.map_data.get("soaps", []), "soap", "soaps"),
            (self.map_data.get("legends", []), "legend", "legends"),
        ]

        closest = None
        min_dist = float('inf')  # ← БЕЗ ТОЧКИ!

        for items, node_type, key in candidates:
            for item in items:
                x, y = item["xy"]["x"], item["xy"]["y"]
                dist = math.hypot(pos.x() - x, pos.y() - y)
                if dist < min_dist and dist < tolerance:
                    min_dist = dist
                    closest = (item, node_type, key)

        return closest  # (node, type, map_key)
    
    # === DRAG & DROP ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            result = self.find_node_by_position(scene_pos)
            if result:
                node, node_type, key = result  # ← 3 значения!
                if self.is_edit_mode:
                    # Запускаем перетаскивание
                    self.dragged_node = node
                    self.dragged_type = node_type
                    self.dragged_key = key
                    self.drag_start_pos = scene_pos
                    event.accept()
                    return
                elif node_type == "switch":
                    self.show_switch_info(node)
                elif node_type == "plan_switch":
                    self.show_plan_switch_info(node)
                event.accept()
                return
        elif event.button() == Qt.MouseButton.RightButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            result = self.find_node_by_position(scene_pos)
            if result:
                node, node_type, key = result  # ← 3 значения!
                if node_type == "plan_switch":
                    self.show_plan_switch_context_menu(event.position().toPoint(), node)
                else:
                    self.show_context_menu(event.position().toPoint())
            else:
                self.show_context_menu(event.position().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, 'dragged_node') and self.dragged_node:
            scene_pos = self.mapToScene(event.position().toPoint())
            # Обновляем позицию в данных
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            # Перерисовываем
            self.render_map()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and hasattr(self, 'dragged_node') and self.dragged_node:
            scene_pos = self.mapToScene(event.position().toPoint())
            # Финальное обновление
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.render_map()
            self.save_map_to_file()
            print(f"Перемещён {self.dragged_type} '{self.dragged_node.get('name')}' → ({scene_pos.x()}, {scene_pos.y()})")
            # Сбрасываем
            self.dragged_node = None
            self.dragged_type = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
            
    def styled_messagebox(self, title, text, icon=QMessageBox.Icon.Question, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        msg.setStyleSheet("""
            QMessageBox { background-color: #333; color: #FFC107; border: 1px solid #FFC107; border: 0px; }
            QMessageBox QLabel { color: #FFC107; font-size: 12px; border: 0px; }
            QMessageBox QPushButton { background-color: #333; color: #FFC107; border: 1px solid #444; border-radius: 4px; padding: 0px 0px; min-width: 100px; min-height: 35px; font-weight: bold; }
            QMessageBox QPushButton:hover { background-color: #FFC107; color: #333; }
            QMessageBox QPushButton:pressed { background-color: #e6b800; }
        """)
        return msg
    

#Информация о свитче на клик
class SwitchInfoDialog(QDialog):
    def __init__(self, switch_data, parent=None):
        super().__init__(parent)
        self.switch_data = switch_data
        self.setWindowTitle("Информация о свитче")
        self.setFixedSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        header = QHBoxLayout()
        title = QLabel(self.switch_data.get("name", "Без названия"))
        title.setStyleSheet("font-size: 12px; font-weight: bold; color: #FFC107;")
        
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Кнопки
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        pin_btn = QPushButton("Запинить")
        refresh_btn.clicked.connect(self.refresh_ping)
        pin_btn.clicked.connect(lambda: self.show_message("Пиннинг не реализован"))
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(pin_btn)
        layout.addLayout(btn_layout)

        # Основные данные
        info = QHBoxLayout()
        left = QVBoxLayout()
        right = QVBoxLayout()

        # Левая колонка: изображение
        model = self.switch_data.get("model", "").replace(" ", "_")
        img_label = QLabel()
        img_label.setFixedHeight(150)
        img_label.setStyleSheet("background: #444; border: 1px solid #666; border-radius: 6px;")
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        found = False
        for ext in ["png", "jpg", "jpeg", "gif"]:
            path = f"images/{model}.{ext}"
            if QPixmap(path).toImage().width() > 0:
                pixmap = QPixmap(path).scaled(200, 150, Qt.AspectRatioMode.KeepAspectRatio)
                img_label.setPixmap(pixmap)
                found = True
                break
        if not found:
            img_label.setText("Изображение не найдено")
        left.addWidget(img_label)

        details_btn = QPushButton("Подробнее")
        details_btn.clicked.connect(self.open_details)
        left.addWidget(details_btn)
        left.addStretch()

        # Правая колонка: текст
        right.addWidget(self.make_label(f"<b>IP:</b> {self.switch_data.get('ip', '—')}"))
        status = "UP" if self.switch_data.get("pingok") else "DOWN"
        color = "#4CAF50" if self.switch_data.get("pingok") else "#F44336"
        right.addWidget(self.make_label(f"<b>Статус:</b> <span style='color:{color}'>{status}</span>"))
        right.addWidget(self.make_label(f"<b>MAC:</b> {self.switch_data.get('mac', '—')}"))
        right.addWidget(self.make_label(f"<b>Модель:</b> {self.switch_data.get('model', '—')}"))
        right.addWidget(self.make_label(f"<b>Uptime:</b> —"))
        right.addWidget(self.make_label(f"<b>Мастер:</b> {self.switch_data.get('master', '—')}"))
        right.addWidget(self.make_label(f"<b>Питание:</b> {self.switch_data.get('power', '—')}"))

        # Порты
        ports_table = QTableWidget()
        ports_table.setColumnCount(2)
        ports_table.setHorizontalHeaderLabels(["Порт", "Описание"])
        ports_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        ports = self.switch_data.get("ports", [])
        ports_table.setRowCount(len(ports))
        for i, port in enumerate(ports):
            num_item = QTableWidgetItem(str(port.get("number", "")))
            desc_item = QTableWidgetItem(port.get("description", ""))
            color = port.get("color", "#FFC107")
            bold = port.get("bold", False)
            for item in (num_item, desc_item):
                item.setForeground(QColor(color))
                if bold:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
            ports_table.setItem(i, 0, num_item)
            ports_table.setItem(i, 1, desc_item)
        right.addWidget(QLabel("<b>Порты:</b>"))
        right.addWidget(ports_table)

        info.addLayout(left, 1)
        info.addLayout(right, 2)
        layout.addLayout(info)

        # Примечание
        note = self.switch_data.get("note", "")
        if note:
            note_edit = QTextEdit()
            note_edit.setPlainText(note)
            note_edit.setReadOnly(True)
            note_edit.setFixedHeight(80)
            layout.addWidget(QLabel("<b>Примечание:</b>"))
            layout.addWidget(note_edit)

        # Футер
        footer = QLabel(f"<b>Последний редактор:</b> {self.switch_data.get('lasteditor', '—')}")
        footer.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(footer)

        # Стили
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #FFC107; }
            QLabel { color: #FFC107; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px; }
            QPushButton:hover { background-color: #555; }
            QTableWidget { background: #333; color: #FFC107; border: 1px solid #666; }
            QHeaderView::section { background: #444; color: #FFC107; }
        """)

    def make_label(self, text):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.RichText)
        return label

    def refresh_ping(self):
        ip = self.switch_data.get("ip")
        if not ip:
            self.show_message("IP не указан")
            return
        try:
            response = requests.get(f"http://your-server/api.php?action=ping_switch&ip={ip}", timeout=3)
            result = response.json()
            self.switch_data["pingok"] = result.get("success", False)
            # Обновляем в map_data
            list_key = "switches" if self.switch_data.get("type") != "plan_switch" else "plan_switches"
            for i, s in enumerate(self.parent().map_data[list_key]):
                if s["id"] == self.switch_data["id"]:
                    self.parent().map_data[list_key][i] = self.switch_data
                    break
            self.parent().render_map()
            self.close()
            self.parent().show_switch_info(self.switch_data)
        except Exception as e:
            self.show_message(f"Ошибка пинга: {e}")

    def open_details(self):
        ip = self.switch_data.get("ip")
        if ip:
            webbrowser.open(f"http://another-site/neotools/usersonline/index.php?ip={ip}&flood=1")
        else:
            self.show_message("IP не указан")

    def show_message(self, text):
        QMessageBox.information(self, "Инфо", text)

#Окно для планируемого свитча
class PlanSwitchInfoDialog(QDialog):
    def __init__(self, plan_switch_data, parent=None):
        super().__init__(parent)
        self.plan_switch_data = plan_switch_data
        self.setWindowTitle("Планируемый свитч")
        self.setFixedSize(500, 350)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Заголовок
        header = QHBoxLayout()
        title = QLabel(self.plan_switch_data.get("name", "Без названия"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFD700;")
        close_btn = QPushButton("X")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton { background: #FFD700; color: #333; border: none; border-radius: 15px; font-weight: bold; }
            QPushButton:hover { background: #e6c200; }
        """)
        close_btn.clicked.connect(self.close)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Основные данные
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        info_layout.addWidget(self.make_label(f"<b>Модель:</b> {self.plan_switch_data.get('model', '—')}"))
        info_layout.addWidget(self.make_label(f"<b>Координаты:</b> X: {self.plan_switch_data['xy']['x']}, Y: {self.plan_switch_data['xy']['y']}"))

        # Примечание
        note = self.plan_switch_data.get("note", "").strip()
        if note:
            note_edit = QTextEdit()
            note_edit.setPlainText(note)
            note_edit.setReadOnly(True)
            note_edit.setFixedHeight(120)
            info_layout.addWidget(QLabel("<b>Примечание:</b>"))
            info_layout.addWidget(note_edit)
        else:
            info_layout.addWidget(QLabel("<i>Примечание отсутствует</i>"))

        layout.addLayout(info_layout)
        layout.addStretch()

        # Стили
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #FFD700; }
            QLabel { color: #FFD700; margin: 4px 0; }
            QTextEdit { background: #333; color: #FFD700; border: 1px solid #666; border-radius: 6px; padding: 6px; }
        """)

    def make_label(self, text):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.RichText)
        return label

# Окно добавления/редактирования
class AddPlanedSwitch(QDialog):
    def __init__(self, canvas, position, edit_data=None, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.position = position
        self.edit_data = edit_data
        self.is_edit = edit_data is not None

        self.setWindowTitle("Редактирование планируемого свитча" if self.is_edit else "Добавление планируемого свитча")
        self.setFixedSize(500, 230)
        self.setup_ui()

        if self.is_edit:
            self.name_input.setText(edit_data.get("name", ""))
            self.model_combo.setCurrentText(edit_data.get("model", ""))
            self.note_field.setPlainText(edit_data.get("note", ""))

    def setup_ui(self):
        outer_layout = QVBoxLayout()
        self.setLayout(outer_layout)

        # Заголовок
        title = QLabel("Планируемый управляемый свитч")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; margin: 5px;")
        outer_layout.addWidget(title)

        # Горизонтальный layout: лево + право
        main_layout = QHBoxLayout()
        #
        #main_layout.addWidget(QLabel("Примечание:"))
        outer_layout.addLayout(main_layout)

        # Левая колонка
        left_layout = QVBoxLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(50)
        self.name_input.setFixedWidth(200)
        self.name_input.setFixedHeight(25)
        left_layout.addWidget(QLabel("Название свитча:"))
        left_layout.addWidget(self.name_input)
        left_layout.addWidget(QLabel("Выберите модель:"))
        self.model_combo = QComboBox()
        self.model_combo.setFixedWidth(200)
        self.model_combo.setFixedHeight(25)
        self.load_models()
        left_layout.addWidget(self.model_combo)
        left_layout.addStretch()

        # Правая колонка
        right_layout = QVBoxLayout()
        
        self.note_field = QTextEdit()
        self.note_field.setPlaceholderText("Введите примечание...")
        self.note_field.setFixedWidth(250)
        self.note_field.setFixedHeight(120)
        right_layout.addWidget(self.note_field)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("ОК")
        ok_button.setFixedWidth(100)
        ok_button.clicked.connect(self.accept_and_add)

        cancel_button = QPushButton("Отмена")
        cancel_button.setFixedWidth(100)
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        outer_layout.addLayout(button_layout)

        # Стили
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #FFC107; }
            QLabel { color: #FFC107; font-size: 13px; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #444; color: #FFC107;
                border: 1px solid #666; border-radius: 4px; padding: 4px;
            }
            QPushButton { 
                background-color: #333; color: #FFC107;
                border: none; border-radius: 6px; padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #FFC107; color: #333; }
        """)

    def load_models(self):
        try:
            with open("models/models.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                models = data.get("models", []) if isinstance(data, dict) else data
                model_names = [m["model_name"] for m in models if isinstance(m, dict) and "model_name" in m]
                if model_names:
                    self.model_combo.addItems(model_names)
                else:
                    self.model_combo.addItem("Нет моделей")
        except Exception as e:
            print(f"Ошибка загрузки models.json: {e}")
            self.model_combo.addItem("Ошибка загрузки")

    def accept_and_add(self):
        name = self.name_input.text().strip()
        if not name:
            name = f"Планируемый свитч {len(self.canvas.map_data['plan_switches']) + 1}"

        model = self.model_combo.currentText()
        note = self.note_field.toPlainText().strip()

        if self.is_edit:
            # Обновляем существующий
            self.edit_data["name"] = name
            self.edit_data["model"] = model
            self.edit_data["note"] = note
            print(f"Обновлен plan_switch в map_data: {self.edit_data}")
        else:
            # Добавляем новый
            new_id = self.canvas.get_next_id("plan_switches")
            new_switch = {
                "id": new_id,
                "name": name,
                "xy": {"x": self.position.x(), "y": self.position.y()},
                "model": model,
                "note": note
            }
            self.canvas.map_data["plan_switches"].append(new_switch)
            print(f"Добавлен plan_switch в map_data: {new_switch}")

        self.canvas.render_map()
        self.accept()
        

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
        QTimer.singleShot(3000, self.hide)    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("icon.ico"))
        self.open_maps = []
        self.active_map_id = None
        self.map_data = {}
        self.is_edit_mode = False
        self.setWindowTitle("PINGER")
        self.setStyleSheet("""
            QMainWindow { background-color: #333; }
            QMenuBar { background-color: #333; color: #FFC107; border-bottom: 3px solid #FFC107; padding: 5px 0px 5px 0px; min-height: 15px; }
            QMenuBar::item { background-color: #333; color: #FFC107; }
            QMenuBar::item:selected { background-color: #555; }
            QMenu { background-color: #444; color: #FFC107; }
            QMenu::item:selected { background-color: #555; }
        """)

        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        create_map = QAction("Создать", self)
        open_map = QAction("Открыть", self)
        exit_action = QAction("Выйти", self)
        create_map.triggered.connect(self.show_create_map_dialog)
        open_map.triggered.connect(self.show_open_map_dialog)
        exit_action.triggered.connect(QApplication.quit)
        file_menu.addAction(create_map)
        file_menu.addAction(open_map)
        file_menu.addAction(exit_action)

        options_menu = menubar.addMenu("Опции")
        operators = QAction("Операторы", self)
        vlan_management = QAction("Упр. VLAN", self)
        firmware_management = QAction("Прошивки", self)
        engineers_management = QAction("Техники", self)
        models_management = QAction("Модели", self)
        operators.triggered.connect(self.show_operators_dialog)
        vlan_management.triggered.connect(self.show_vlan_management_dialog)
        firmware_management.triggered.connect(self.show_firmware_management_dialog)
        engineers_management.triggered.connect(self.show_engineers_management_dialog)
        models_management.triggered.connect(self.show_models_management_dialog)
        options_menu.addAction(operators)
        options_menu.addAction(vlan_management)
        options_menu.addAction(firmware_management)
        options_menu.addAction(engineers_management)
        options_menu.addAction(models_management)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        button_layout = QHBoxLayout()
        ping_button = QPushButton("Пинговать устройства")
        self.settings_button = QPushButton("Параметры карты")
        self.edit_button = QPushButton("Редактировать")
        ping_button.clicked.connect(self.ping_switches)
        self.settings_button.clicked.connect(self.show_map_settings_dialog)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        self.settings_button.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(ping_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addWidget(self.edit_button)
        layout.addLayout(button_layout)
        for btn in [ping_button, self.settings_button, self.edit_button]:
            btn.setStyleSheet("""
                QPushButton { background-color: #333; color: #FFC107; font-size: 12px; border: none; border-radius: 2px; padding: 10px; }
                QPushButton:hover { background-color: #FFC107; color: #333; }
                QPushButton:pressed { background-color: #FFC107; color: #333; }
                QPushButton:disabled { background-color: #555; color: #888; }
            """)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.switch_tab)
        layout.addWidget(self.tabs)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { background-color: #333; border: 1px solid #555; }
            QTabBar { alignment: left; }
            QTabBar::tab { background-color: #333; color: #FFC107; padding: 8px 10px; border: 1px solid #555; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #FFC107; color: #333; }
            QTabBar::tab:hover:!selected { background-color: #444; }
            QTabBar::close-button { background-color: transparent; width: 16px; height: 16px; margin: 2px; padding: 2px; }
            QTabBar::close-button:selected { image: url(C:/PingerApp/icons/closetab_act.png); }
            QTabBar::close-button:!selected { image: url(C:/PingerApp/icons/closetab_inact.png); }
        """)

        self.setGeometry(100, 100, 1200, 900)
        self.load_open_maps()

    def load_open_maps(self):
        try:
            if os.path.exists("open_maps.pkl"):
                with open("open_maps.pkl", "rb") as f:
                    self.open_maps = pickle.load(f)
                if self.open_maps:
                    self.active_map_id = self.open_maps[0]["id"]
                    self.open_map(self.active_map_id)
                    self.update_tabs()
        except Exception as e:
            self.show_toast(f"Ошибка загрузки открытых карт: {str(e)}", "error")

    def save_open_maps(self):
        try:
            with open("open_maps.pkl", "wb") as f:
                pickle.dump(self.open_maps, f)
        except Exception as e:
            self.show_toast(f"Ошибка сохранения открытых карт: {str(e)}", "error")

    def update_tabs(self):
        self.tabs.blockSignals(True)
        self.tabs.clear()
        for map_info in self.open_maps:
            canvas = MapCanvas(self.map_data.get(map_info["id"], {}), self)
            canvas.is_edit_mode = self.is_edit_mode
            self.tabs.addTab(canvas, map_info["name"])
            if map_info["id"] == self.active_map_id:
                self.tabs.setCurrentWidget(canvas)
        self.tabs.blockSignals(False)
        self.settings_button.setEnabled(self.is_edit_mode and bool(self.active_map_id))

    def show_create_map_dialog(self):
        dialog = MapNameDialog(self)
        dialog.setModal(False)
        dialog.accepted.connect(lambda: self.on_create_map_accepted(dialog))
        dialog.show()

    def on_create_map_accepted(self, dialog):
        name = dialog.input.text().strip()
        if not name:
            self.show_toast("Введите название карты", "error")
            return
        map_id = name
        self.open_maps.append({"id": map_id, "name": name})
        self.active_map_id = map_id
        self.map_data[map_id] = {
            "map": {
                "name": name,
                "width": "1200",
                "height": "800",
                "mod_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "switches": [],
            "plan_switches": [],
            "users": [],
            "soaps": [],
            "legends": [],
            "magistrals": []
        }
        self.save_map()
        self.save_open_maps()
        self.update_tabs()
        self.show_toast(f"Карта '{name}' создана", "success")

    def show_open_map_dialog(self):
        dialog = OpenMapDialog(self)
        dialog.setModal(False)
        dialog.accepted.connect(lambda: self.on_open_map_accepted(dialog))
        dialog.show()

    def on_open_map_accepted(self, dialog):
        if dialog.table.currentRow() >= 0:
            map_name = dialog.table.item(dialog.table.currentRow(), 0).text()
            map_id = map_name
            if map_id not in [m["id"] for m in self.open_maps]:
                self.open_maps.append({"id": map_id, "name": map_id})
                self.active_map_id = map_id
                self.open_map(map_id)
                self.update_tabs()
                self.show_toast(f"Карта '{map_id}' открыта", "success")
            else:
                self.active_map_id = map_id
                self.update_tabs()
                self.show_toast(f"Карта '{map_id}' уже открыта", "info")

    def save_map(self):
        if not self.active_map_id:
            self.show_toast("Нет активной карты для сохранения", "info")
            return
        try:
            maps_dir = "maps"
            if not os.path.exists(maps_dir):
                os.makedirs(maps_dir)
            map_file = os.path.join(maps_dir, f"map_{self.active_map_id}.json")
            self.map_data[self.active_map_id]["map"]["mod_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(map_file, "w", encoding="utf-8") as f:
                json.dump(self.map_data[self.active_map_id], f, ensure_ascii=False, indent=4)
            self.show_toast("Карта успешно сохранена", "success")
        except Exception as e:
            self.show_toast(f"Ошибка сохранения карты: {str(e)}", "error")

    def show_map_settings_dialog(self):
        if not self.active_map_id:
            self.show_toast("Нет активной карты для настройки", "info")
            return
        dialog = MapSettingsDialog(self, self.map_data.get(self.active_map_id))
        dialog.setModal(False)
        dialog.accepted.connect(lambda: self.on_map_settings_accepted(dialog))
        dialog.show()

    def on_map_settings_accepted(self, dialog):
        width = dialog.width_input.value()
        height = dialog.height_input.value()
        if width < 100 or height < 100:
            self.show_toast("Ширина и высота должны быть не менее 100", "error")
            return
        if self.active_map_id in self.map_data:
            self.map_data[self.active_map_id]["map"]["width"] = str(width)
            self.map_data[self.active_map_id]["map"]["height"] = str(height)
            current_tab = self.tabs.currentWidget()
            if current_tab:
                current_tab.map_data["map"]["width"] = str(width)
                current_tab.map_data["map"]["height"] = str(height)
                current_tab.setSceneRect(0, 0, width, height)
                current_tab.render_map()
            self.save_map()
            self.show_toast("Параметры карты обновлены", "success")
        else:
            self.show_toast("Ошибка: активная карта не найдена", "error")

    def ping_switches(self):
        if not self.active_map_id or not self.map_data.get(self.active_map_id, {}).get("switches"):
            self.show_toast("Нет устройств для пинга", "error")
            return
        for switch_device in self.map_data[self.active_map_id]["switches"]:
            switch_device["pingok"] = bool(switch_device.get("ip"))
        self.update_tabs()
        self.show_toast("Пинг устройств завершен", "success")

    def toggle_edit_mode(self):
        self.is_edit_mode = not self.is_edit_mode
        self.edit_button.setStyleSheet("""
            QPushButton { 
                background-color: #FFC107; 
                color: #333; 
                font-size: 12px; 
                border: none; 
                border-radius: 2px; 
                padding: 10px; 
            }
            QPushButton:hover { background-color: #FFCA28; color: #333; }
            QPushButton:pressed { background-color: #FFCA28; color: #333; }
        """ if self.is_edit_mode else """
            QPushButton { 
                background-color: #333; 
                color: #FFC107; 
                font-size: 12px; 
                border: none; 
                border-radius: 2px; 
                padding: 10px; 
            }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QPushButton:pressed { background-color: #FFC107; color: #333; }
        """)
        self.settings_button.setEnabled(self.is_edit_mode and bool(self.active_map_id))
        self.show_toast(f"Режим редактирования: {'включен' if self.is_edit_mode else 'выключен'}", "info")
        for index in range(self.tabs.count()):
            tab = self.tabs.widget(index)
            tab.is_edit_mode = self.is_edit_mode
            tab.render_map()
        if not self.is_edit_mode:
            self.save_map()
            
    def sync_edit_mode(self, is_edit_mode):
            self.is_edit_mode = is_edit_mode
            self.edit_button.setStyleSheet("""
            QPushButton { 
                background-color: #FFC107; 
                color: #333; 
                font-size: 12px; 
                border: none; 
                border-radius: 2px; 
                padding: 10px; 
            }
            QPushButton:hover { background-color: #FFCA28; color: #333; }
            QPushButton:pressed { background-color: #FFCA28; color: #333; }
        """ if self.is_edit_mode else """
            QPushButton { 
                background-color: #333; 
                color: #FFC107; 
                font-size: 12px; 
                border: none; 
                border-radius: 2px; 
                padding: 10px; 
            }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QPushButton:pressed { background-color: #FFC107; color: #333; }
        """)
            self.settings_button.setEnabled(self.is_edit_mode and bool(self.active_map_id))
            self.show_toast(f"Режим редактирования: {'включен' if self.is_edit_mode else 'выключен'}", "info")
            for index in range(self.tabs.count()):
                        tab = self.tabs.widget(index)
                        tab.is_edit_mode = self.is_edit_mode
                        tab.render_map()
            if not self.is_edit_mode:
                        self.save_map()

    def close_tab(self, index):
        map_id = self.open_maps[index]["id"]
        self.open_maps.pop(index)
        self.save_open_maps()
        if self.active_map_id == map_id:
            self.active_map_id = self.open_maps[0]["id"] if self.open_maps else None
            if self.active_map_id:
                self.open_map(self.active_map_id)
        self.update_tabs()

    def switch_tab(self, index):
        if index >= 0 and self.open_maps[index]["id"] != self.active_map_id:
            self.active_map_id = self.open_maps[index]["id"]
            self.update_tabs()

    def open_map(self, map_id):
        self.active_map_id = map_id
        map_file = os.path.join("maps", f"map_{map_id}.json")
        try:
            if os.path.exists(map_file):
                with open(map_file, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                self.map_data[map_id] = loaded_data
            else:
                alt_map_file = os.path.join("maps", f"{map_id}.json")
                if os.path.exists(alt_map_file):
                    with open(alt_map_file, "r", encoding="utf-8") as f:
                        loaded_data = json.load(f)
                    self.map_data[map_id] = loaded_data
                else:
                    self.map_data[map_id] = {
                        "map": {"name": map_id, "width": "1200", "height": "800"},
                        "switches": [{"id": "sw1", "xy": {"x": 200, "y": 200}, "name": "Switch1", "ip": "192.168.1.1", "pingok": True}],
                        "plan_switches": [],
                        "users": [],
                        "soaps": [],
                        "legends": [],
                        "magistrals": []
                    }
                    self.show_toast(f"Карта '{map_id}' не найдена, создана новая карта", "info")
        except json.JSONDecodeError as e:
            self.show_toast(f"Ошибка формата JSON в карте '{map_id}': {str(e)}", "error")
            self.map_data[map_id] = {
                "map": {"name": map_id, "width": "1200", "height": "800"},
                "switches": [{"id": "sw1", "xy": {"x": 200, "y": 200}, "name": "Switch1", "ip": "192.168.1.1", "pingok": True}],
                "plan_switches": [],
                "users": [],
                "soaps": [],
                "legends": [],
                "magistrals": []
            }

    def show_toast(self, message, toast_type="info"):
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)

    def show_operators_dialog(self):
        dialog = OperatorsDialog(self)
        dialog.exec()

    def show_vlan_management_dialog(self):
        dialog = VlanManagementDialog(self)
        dialog.exec()

    def show_firmware_management_dialog(self):
        dialog = FirmwareManagementDialog(self)
        dialog.exec()

    def show_engineers_management_dialog(self):
        dialog = EngineersManagementDialog(self)
        dialog.exec()
        
    def show_models_management_dialog(self):
        dialog = ModelsManagementDialog(self)
        dialog.exec()
        
        
    

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()