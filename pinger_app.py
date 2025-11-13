import sys
import json
import os
import math
import shutil
from PyQt6.QtWidgets import (QGraphicsPixmapItem, QMessageBox)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGraphicsView, QGraphicsScene, QDialog, QLineEdit)
from PyQt6.QtWidgets import (QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFormLayout, QSpinBox, QHeaderView, QComboBox, QListWidget, QCheckBox, QTextEdit, QFileDialog)
from PyQt6.QtGui import QAction, QColor, QBrush, QPen, QPainter, QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QThread, pyqtSignal
import pickle
import re
from datetime import datetime
import asyncio
import websockets
import uuid
from websockets.protocol import State 

# === WebSocket Client ===
class WebSocketClient(QThread):
    connected = pyqtSignal(bool)
    message_received = pyqtSignal(dict)
    
    def __init__(self, uri="ws://127.0.0.1:8081"):
        super().__init__()
        self.uri = uri
        self.websocket = None
        self.loop = None
        self.running = True
        self.pending_requests = {}
        
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main())
        
    async def _main(self):
        while self.running:
            try:
                async with websockets.connect(self.uri, ping_interval=20, ping_timeout=10) as ws:
                    self.websocket = ws
                    self.connected.emit(True)
                    
                    while self.running and ws.state == State.OPEN:
                        await asyncio.sleep(1)
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            data = json.loads(response)
                            self.message_received.emit(data)
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            print(f"[WS] Error receiving: {e}")
                            break
                            
            except Exception as e:
                print(f"[WS] Connection error: {e}")
                self.connected.emit(False)
                if self.running:
                    await asyncio.sleep(2)
            finally:
                self.websocket = None
                self.connected.emit(False)
                
    def send_request(self, action, **kwargs):
        if self.websocket and self.isRunning():
            request_id = str(uuid.uuid4())
            request = {"action": action, "request_id": request_id, **kwargs}
            asyncio.run_coroutine_threadsafe(
                self.websocket.send(json.dumps(request)), self.loop
            )
            return request_id
        return None
        
    def stop(self):
        self.running = False

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
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; height: 18px; padding: 4px 5px; }
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

class OpenMapDialog(QDialog):
    def __init__(self, parent=None, map_files=None):
        super().__init__(parent)
        self.setWindowTitle("Открыть карту")
        self.setFixedSize(785, 400)
        self.map_files = map_files or []
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
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
            QLabel { color: #FFC107; }
        """)

    def populate_table(self):
        self.table.setRowCount(len(self.map_files))
        for row, map_file in enumerate(self.map_files):
            map_name = map_file.replace(".json", "").replace("map_", "")
            for col, value in enumerate([map_name, "lasteditor", "lastpingdatetime"]):
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
        
        # WebSocket client
        self.ws_client = WebSocketClient()
        self.ws_client.connected.connect(self.on_ws_connected)
        self.ws_client.message_received.connect(self.on_ws_message)
        self.ws_client.start()
        self.ws_connected = False
        self.pending_requests = {}
        
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
                QPushButton { background-color: #333; color: #FFC107; font-size: 12px; border: none; border-radius: 2px; padding: 5px; }
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
        """)

        self.setGeometry(100, 100, 1200, 900)
        
        self.status_bar = self.statusBar()
        self.status_bar.setFixedHeight(20)
        self.status_bar.setStyleSheet("""
            QStatusBar { background-color: #333; color: #FFC107; font-size: 12px; }
            QStatusBar::item { border: none; padding: 5px 20px; }
        """)

        self.load_open_maps()

    def on_ws_connected(self, connected):
        self.ws_connected = connected
        if connected:
            self.status_bar.showMessage("Подключено к серверу", 3000)
        else:
            self.status_bar.showMessage("Нет связи с сервером", 3000)
            
    def on_ws_message(self, data):
        request_id = data.get("request_id")
        if request_id in self.pending_requests:
            callback = self.pending_requests.pop(request_id)
            callback(data)

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
        if not self.ws_connected:
            self.show_toast("Нет связи с сервером", "error")
            return
            
        # Request list of maps from server
        request_id = self.ws_client.send_request("list_maps")
        
        def on_list_response(data):
            if data.get("success"):
                map_files = data.get("files", [])
                dialog = OpenMapDialog(self, map_files)
                dialog.setModal(False)
                dialog.accepted.connect(lambda: self.on_open_map_accepted(dialog, map_files))
                dialog.show()
            else:
                self.show_toast(f"Ошибка загрузки списка карт: {data.get('error')}", "error")
                
        self.pending_requests[request_id] = on_list_response

    def on_open_map_accepted(self, dialog, map_files):
        if dialog.table.currentRow() >= 0:
            selected_file = map_files[dialog.table.currentRow()]
            map_name = selected_file.replace(".json", "").replace("map_", "")
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
            
        if not self.ws_connected:
            self.show_toast("Нет связи с сервером", "error")
            return
            
        try:
            self.map_data[self.active_map_id]["map"]["mod_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Send to server
            request_id = self.ws_client.send_request(
                "file_put",
                path=f"maps/map_{self.active_map_id}.json",
                data=self.map_data[self.active_map_id]
            )
            
            def on_save_response(data):
                if data.get("success"):
                    self.status_bar.showMessage("Карта успешно сохранена", 3000)
                    QTimer.singleShot(3000, self.update_status_bar)
                else:
                    self.status_bar.showMessage(f"Ошибка сохранения: {data.get('error')}", 3000)
                    QTimer.singleShot(3000, self.update_status_bar)
                    
            self.pending_requests[request_id] = on_save_response
            
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
                padding: 5px; 
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
                padding: 5px; 
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
        
        if not self.ws_connected:
            # Fallback to empty map
            self.map_data[map_id] = {
                "map": {"name": map_id, "width": "1200", "height": "800"},
                "switches": [],
                "plan_switches": [],
                "users": [],
                "soaps": [],
                "legends": [],
                "magistrals": []
            }
            return
            
        # Request from server
        request_id = self.ws_client.send_request(
            "file_get",
            path=f"maps/map_{map_id}.json"
        )
        
        def on_load_response(data):
            if data.get("success"):
                self.map_data[map_id] = data.get("data")
                self.update_tabs()
            else:
                self.map_data[map_id] = {
                    "map": {"name": map_id, "width": "1200", "height": "800"},
                    "switches": [],
                    "plan_switches": [],
                    "users": [],
                    "soaps": [],
                    "legends": [],
                    "magistrals": []
                }
                self.show_toast(f"Карта '{map_id}' не найдена на сервере, создана новая", "info")
                
        self.pending_requests[request_id] = on_load_response

    def show_toast(self, message, toast_type="info"):
        self.status_bar.showMessage(message, 3000)

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
    
    # Показать диалог логина
    from login_dialog import LoginDialog
    login_dialog = LoginDialog()
    
    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        # Логин успешен, показываем главное окно
        window = MainWindow()
        window.showMaximized()
        window.show()
        sys.exit(app.exec())
    else:
        # Логин отменен
        sys.exit(0)

if __name__ == "__main__":
    main()
