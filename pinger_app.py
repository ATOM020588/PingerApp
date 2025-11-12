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

from widgets import (
    VlanManagementDialog,
    FirmwareManagementDialog,
    EngineersManagementDialog,
    OperatorsDialog,
    ModelsManagementDialog
)

#   ===Импорт класса MapCanvas===
from canvas import *

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
        self.status_bar = self.statusBar()
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
        
        
        self.status_bar = self.statusBar()
        self.status_bar.setFixedHeight(20)
        self.status_bar.setStyleSheet("""
            QStatusBar { background-color: #333; color: #FFC107; font-size: 12px; }
            QStatusBar::item { border: none; padding: 5px 20px; }
        """)

        self.load_open_maps()

    def update_status_bar(self):
        if self.active_map_id:
            map_info = self.map_data.get(self.active_map_id, {}).get("map", {})
            last_adm = map_info.get("last_adm", "Неизвестно")
            mod_time = map_info.get("mod_time", "Неизвестно")
            self.status_bar.showMessage(f"Последние изменения: {last_adm} в {mod_time}")
        else:
            self.status_bar.clearMessage()
    
    
    def load_open_maps(self):
        try:
            if os.path.exists("open_maps.pkl"):
                with open("open_maps.pkl", "rb") as f:
                    self.open_maps = pickle.load(f)
                if self.open_maps:
                    self.active_map_id = self.open_maps[0]["id"]
                    self.open_map(self.active_map_id)
                    self.update_tabs()
                    self.update_status_bar()
        except Exception as e:
            self.status_bar.showMessage("Ошибка загрузки открытых карт", 3000)
            QTimer.singleShot(3000, self.update_status_bar)

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
        self.update_status_bar()
        self.status_bar.showMessage("Карта успешно сохранена", 3000)
        QTimer.singleShot(3000, self.update_status_bar)

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
                self.update_status_bar()
                self.show_toast(f"Карта '{map_id}' открыта", "success")
            else:
                self.active_map_id = map_id
                self.update_tabs()
                self.update_status_bar()
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
            self.status_bar.showMessage("Карта успешно сохранена", 3000)
            QTimer.singleShot(3000, self.update_status_bar)
        except Exception as e:
            self.status_bar.showMessage("Ошибка сохранения карты", 3000)
            QTimer.singleShot(3000, self.update_status_bar)

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
        self.update_status_bar()
        self.status_bar.showMessage("Пинг устройств завершен", 3000)
        QTimer.singleShot(3000, self.update_status_bar)

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
        self.status_bar.showMessage(message, 3000)  # 3000 мс = 3 секунды, игнорируем toast_type (без цветов)

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