import sys
import json
import os
import math
import shutil
import base64
import os
from PyQt6.QtWidgets import (QGraphicsPixmapItem, QMessageBox)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGraphicsView, QGraphicsScene, QDialog, QLineEdit)
from PyQt6.QtWidgets import (QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFormLayout, QSpinBox, QHeaderView, QComboBox, QListWidget, QCheckBox, QTextEdit, QFileDialog)
from PyQt6.QtGui import QAction, QColor, QBrush, QPen, QPainter, QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QThread, pyqtSignal, QSettings
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

    def __init__(self, uri="ws://192.168.0.56:8081"):
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
    def __init__(self, parent=None, map_files=None, ws_client=None):
        super().__init__(parent)
        self.setWindowTitle("Открыть карту")
        self.setFixedSize(785, 400)
        self.map_files = map_files or []
        self.ws_client = ws_client
        self.parent_window = parent
        
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
        """ИСПРАВЛЕНО: Показываем только имена файлов, без загрузки данных"""
        self.table.setRowCount(len(self.map_files))
        for row, map_file in enumerate(self.map_files):
            map_name = map_file.replace(".json", "").replace("map_", "")
            # Показываем только имя, остальные колонки оставляем пустыми для быстрой загрузки
            for col, value in enumerate([map_name, "", ""]):
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
from globals_dialog import GlobalIssuesDialog

class MainWindow(QMainWindow):
    def __init__(self, user_login=None):
        super().__init__()
        self.setWindowIcon(QIcon("icon.ico"))
        self.open_maps = []
        self.active_map_id = None
        self.map_data = {}
        self.is_edit_mode = False
        self.setWindowTitle("Network Management System")

        # Сохраняем логин пользователя для записи в карты
        self.current_user = user_login or "Неизвестный"

        self.settings = QSettings("Network Management System", "UserSession")

        # WebSocket client - ИНИЦИАЛИЗИРУЕМ ДО load_open_maps()
        self.ws_client = WebSocketClient()
        self.ws_client.connected.connect(self.on_ws_connected)
        self.ws_client.message_received.connect(self.on_ws_message)
        self.ws_client.start()
        self.ws_connected = False
        self.pending_requests = {}

        # Умная синхронизация pingok каждые 12 секунд
        self.ping_sync_timer = QTimer(self)
        self.ping_sync_timer.timeout.connect(self.check_ping_updates)
        self.ping_sync_timer.start(12000)  # 12 секунд — оптимально

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
        global_issues_button = QPushButton("Глобальные неисправности")
        ping_button = QPushButton("Пинговать устройства")
        self.settings_button = QPushButton("Параметры карты")
        self.edit_button = QPushButton("Редактировать")
        global_issues_button.clicked.connect(self.show_global_issues_dialog)
        ping_button.clicked.connect(self.ping_switches)
        self.settings_button.clicked.connect(self.show_map_settings_dialog)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        self.settings_button.setEnabled(False)
        button_layout.addStretch()
        button_layout.addWidget(global_issues_button)
        button_layout.addWidget(ping_button)
        button_layout.addWidget(self.settings_button)
        button_layout.addWidget(self.edit_button)
        layout.addLayout(button_layout)
        for btn in [global_issues_button, ping_button, self.settings_button, self.edit_button]:
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
            QTabBar::tab { background-color: #333; color: #FFC107; padding: 8px 10px; border: 1px solid #555; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; height: }
            QTabBar::tab:selected { background-color: #FFC107; color: #333; }
            QTabBar::tab:hover:!selected { background-color: #444; }
            QTabBar::close-button { background-color: transparent; width: 16px; height: 16px; margin: 2px; padding: 2px; }
            QTabBar::close-button:selected { image: url(C:/PingerApp_to_serv/icons/closetab_act.png); }
            QTabBar::close-button:!selected { image: url(C:/PingerApp_to_serv/icons/closetab_inact.png); }
        """)

        self.setGeometry(100, 100, 1200, 900)

        # ИСПРАВЛЕНИЕ: Статус бар создается ДО загрузки карт
        self.status_bar = self.statusBar()
        self.status_bar.setFixedHeight(20)
        self.status_bar.setStyleSheet("""
            QStatusBar { background-color: #333; color: #FFC107; font-size: 12px; }
            QStatusBar::item { border: none; padding: 5px 20px; }
        """)
        
        # Добавляем индикатор связи в правой части статус бара
        self.connection_indicator = QLabel()
        self.connection_indicator.setStyleSheet("""
            QLabel {
                color: #FFC107;
                padding: 2px 10px;
                font-size: 11px;
            }
        """)
        self.status_bar.addPermanentWidget(self.connection_indicator)
        self.update_connection_indicator(False)  # Изначально нет связи

        # ИСПРАВЛЕНИЕ: Загрузка открытых карт ПОСЛЕ создания status_bar
        self.load_open_maps()

    def update_connection_indicator(self, connected):
        """Обновляет индикатор связи с сервером"""
        if connected:
            # Зеленый кружок Unicode: ●
            self.connection_indicator.setText("● Связь с сервером")
            self.connection_indicator.setStyleSheet("""
                QLabel {
                    color: #00ff00;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)
        else:
            # Красный кружок Unicode: ●
            self.connection_indicator.setText("● Нет связи")
            self.connection_indicator.setStyleSheet("""
                QLabel {
                    color: #ff0000;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
            """)

    def on_ws_connected(self, connected):
        self.ws_connected = connected
        self.update_connection_indicator(connected)
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

    def get_current_ping_hashes(self):
        """Возвращает словарь {индекс: хеш(pingok)} для текущей карты"""
        if not self.active_map_id:
            return {}
        switches = self.map_data.get(self.active_map_id, {}).get("switches", [])
        return {str(i): str(s.get("pingok", False)).lower() for i, s in enumerate(switches)}

    def check_ping_updates(self):
        """Спрашивает сервер: не изменились ли pingok?"""
        if not self.ws_connected or not self.active_map_id:
            return

        current_hashes = self.get_current_ping_hashes()

        request_id = self.ws_client.send_request(
            "check_ping_updates",
            map_id=self.active_map_id,
            hashes=current_hashes
        )

        if not request_id:
            return

        def on_updates_response(data):
            if not data.get("success"):
                return

            updates = data.get("updates", [])
            if not updates:
                return  # ничего не изменилось

            switches = self.map_data[self.active_map_id]["switches"]
            updated = False

            for upd in updates:
                idx = upd["index"]
                if idx < len(switches):
                    old = switches[idx].get("pingok")
                    new = upd["pingok"]
                    if old != new:
                        switches[idx]["pingok"] = new
                        updated = True

            if updated:
                current_tab = self.tabs.currentWidget()
                if current_tab:
                    current_tab.render_map()
                self.status_bar.showMessage(f"Обновлено статусов: {len(updates)}", 2000)

        self.pending_requests[request_id] = on_updates_response

    def load_open_maps(self):
        """ИСПРАВЛЕНО: Загружает открытые карты из файла open_maps.pkl"""
        try:
            pickle_file = "open_maps.pkl"
            if os.path.exists(pickle_file):
                with open(pickle_file, "rb") as f:
                    loaded_data = pickle.load(f)

                # Проверка типа: должен быть список словарей
                if isinstance(loaded_data, list):
                    # Фильтруем только словари с нужными ключами
                    self.open_maps = []
                    for item in loaded_data:
                        if isinstance(item, dict) and "id" in item and "name" in item:
                            self.open_maps.append(item)
                        elif isinstance(item, str):
                            # Если это строка, создаем словарь
                            self.open_maps.append({"id": item, "name": item})

                    if self.open_maps:
                        self.active_map_id = self.open_maps[0]["id"]
                        # ИСПРАВЛЕНИЕ: Счетчик для отслеживания загрузки всех карт
                        self.maps_to_load = len(self.open_maps)
                        self.maps_loaded_data = {}  # Кэш для загруженных данных
                        # Загружаем все открытые карты
                        for map_info in self.open_maps:
                            self.open_map(map_info["id"], is_initial_load=True)
                        print(f"Начата загрузка {len(self.open_maps)} открытых карт")
                else:
                    print("Некорректный формат данных в open_maps.pkl")
                    self.open_maps = []
        except Exception as e:
            print(f"Ошибка загрузки открытых карт: {e}")
            self.open_maps = []

    def save_open_maps(self):
        """Сохраняет открытые карты в файл open_maps.pkl"""
        try:
            pickle_file = "open_maps.pkl"
            # Сохраняем только id и name
            clean_maps = [
                {"id": m["id"], "name": m["name"]}
                for m in self.open_maps
                if isinstance(m, dict) and "id" in m and "name" in m
            ]
            with open(pickle_file, "wb") as f:
                pickle.dump(clean_maps, f)
            print(f"Сохранено {len(clean_maps)} открытых карт в {pickle_file}")
        except Exception as e:
            print(f"Ошибка сохранения открытых карт: {e}")

    def update_tabs(self):
        """ИСПРАВЛЕНО: Обновляет вкладки с проверкой наличия данных"""
        self.tabs.blockSignals(True)
        self.tabs.clear()
        for map_info in self.open_maps:
            map_data = self.map_data.get(map_info["id"], {})
            canvas = MapCanvas(map_data, self)
            canvas.is_edit_mode = self.is_edit_mode
            self.tabs.addTab(canvas, map_info["name"])
            if map_info["id"] == self.active_map_id:
                self.tabs.setCurrentWidget(canvas)
            # ИСПРАВЛЕНИЕ: Рендерим только если данные есть
            if map_data and "map" in map_data:
                canvas.render_map()
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
                dialog = OpenMapDialog(self, map_files, self.ws_client)
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

            # ИСПРАВЛЕНИЕ: Проверяем, что open_maps содержит словари
            open_map_ids = []
            for m in self.open_maps:
                if isinstance(m, dict) and "id" in m:
                    open_map_ids.append(m["id"])
                elif isinstance(m, str):
                    open_map_ids.append(m)

            if map_id not in open_map_ids:
                self.open_maps.append({"id": map_id, "name": map_id})
                self.active_map_id = map_id
                self.open_map(map_id)
                self.save_open_maps()
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
            # Обновляем время и пользователя
            self.map_data[self.active_map_id]["map"]["mod_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.map_data[self.active_map_id]["map"]["last_adm"] = self.current_user

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
        if not self.active_map_id:
            self.show_toast("Нет активной карты", "error")
            return

        if not self.ws_connected:
            self.show_toast("Нет связи с сервером", "error")
            return

        switches = self.map_data[self.active_map_id]["switches"]
        if not switches:
            self.show_toast("На карте нет устройств", "error")
            return

        # Подготавливаем данные: индекс + IP (индекс нужен для надёжного маппинга)
        ping_data = [
            {"index": idx, "ip": s.get("ip")}
            for idx, s in enumerate(switches)
            if s.get("ip") and isinstance(s.get("ip"), str) and s["ip"].strip()
        ]

        if not ping_data:
            self.show_toast("Нет устройств с IP-адресами", "error")
            return

        # Отправляем запрос серверу
        request_id = self.ws_client.send_request(
            "ping_switches",
            ping_data=ping_data,
            timeout_ms=3000  # можно взять из CONFIG клиента, если добавите
        )

        if not request_id:
            self.show_toast("Не удалось отправить запрос", "error")
            return

        def on_ping_response(data):
            if not data.get("success"):
                self.show_toast(f"Ошибка пинга: {data.get('error', 'unknown')}", "error")
                return

            results = data.get("results", [])
            result_map = {r["index"]: r["success"] for r in results}

            # Обновляем pingok в локальных данных
            for idx in result_map:
                if idx < len(switches):
                    switches[idx]["pingok"] = result_map[idx]

            # Перерисовываем только текущую карту (не пересоздаём все табы)
            current_tab = self.tabs.currentWidget()
            if current_tab:
                current_tab.render_map()

            self.update_status_bar()
            self.status_bar.showMessage("Пинг устройств завершён", 3000)
            QTimer.singleShot(3000, self.update_status_bar)

        self.pending_requests[request_id] = on_ping_response

        self.status_bar.showMessage("Пинг устройств в процессе...", 5000)

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
        if index < 0 or index >= len(self.open_maps):
            return
        map_id = self.open_maps[index]["id"]
        self.open_maps.pop(index)
        self.save_open_maps()
        if self.active_map_id == map_id:
            self.active_map_id = self.open_maps[0]["id"] if self.open_maps else None
            if self.active_map_id:
                self.open_map(self.active_map_id)
        self.update_tabs()

    def switch_tab(self, index):
        if index >= 0 and index < len(self.open_maps) and self.open_maps[index]["id"] != self.active_map_id:
            self.active_map_id = self.open_maps[index]["id"]
            self.update_tabs()

    def open_map(self, map_id, is_initial_load=False):
        """ИСПРАВЛЕНО: Загружает карту и принудительно обновляет Canvas"""
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
            # Если это начальная загрузка, уменьшаем счетчик
            if is_initial_load and hasattr(self, 'maps_to_load'):
                self.maps_to_load -= 1
                if self.maps_to_load == 0:
                    self.update_tabs()
                    self.update_status_bar()
            return

        # Request from server
        request_id = self.ws_client.send_request(
            "file_get",
            path=f"maps/map_{map_id}.json"
        )

        def on_load_response(data):
            if data.get("success"):
                self.map_data[map_id] = data.get("data")
                print(f"✓ Данные карты '{map_id}' загружены успешно")
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
                if not is_initial_load:
                    self.show_toast(f"Карта '{map_id}' не найдена на сервере, создана новая", "info")
            
            # ИСПРАВЛЕНИЕ: Обновляем табы только когда все карты загружены
            if is_initial_load and hasattr(self, 'maps_to_load'):
                self.maps_to_load -= 1
                print(f"Загружена карта '{map_id}', осталось: {self.maps_to_load}")
                if self.maps_to_load == 0:
                    print("✓ Все карты загружены, обновляем интерфейс")
                    self.update_tabs()
                    self.update_status_bar()
            else:
                # Для карт, открытых вручную, обновляем сразу
                self.update_tabs()
                self.update_status_bar()

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

    def show_global_issues_dialog(self):
        """Показывает диалог глобальных неисправностей"""
        dialog = GlobalIssuesDialog(self, self.ws_client)
        dialog.exec()
    
    def show_server_settings_dialog(self):
        """Показывает диалог настройки адреса сервера"""
        dialog = ServerSettingsDialog(self, self.ws_client)
        if dialog.exec():
            new_uri = dialog.get_server_uri()
            if new_uri:
                # Останавливаем текущее подключение
                self.ws_client.stop()
                self.ws_client.wait()
                
                # Создаем новое подключение с новым адресом
                self.ws_client = WebSocketClient(uri=new_uri)
                self.ws_client.connected.connect(self.on_ws_connected)
                self.ws_client.message_received.connect(self.on_ws_message)
                self.ws_client.start()
                
                self.status_bar.showMessage(f"Подключение к {new_uri}...", 3000)
    
    def keyPressEvent(self, event):
        """Обработка горячих клавиш"""
        # CTRL+G - Открыть глобальные неисправности
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_G:
                self.show_global_issues_dialog()
                event.accept()
                return
            # CTRL+O - Настройка сервера
            elif event.key() == Qt.Key.Key_O:
                self.show_server_settings_dialog()
                event.accept()
                return
        
        super().keyPressEvent(event)


class ServerSettingsDialog(QDialog):
    """Диалог настройки адреса сервера"""
    def __init__(self, parent=None, ws_client=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка сервера")
        self.setFixedSize(450, 180)
        self.ws_client = ws_client
        
        layout = QVBoxLayout()
        
        # Заголовок
        title = QLabel("Укажите адрес WebSocket сервера")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFC107; padding: 10px;")
        layout.addWidget(title)
        
        # Поле ввода адреса
        layout.addWidget(QLabel("Адрес сервера (например, ws://127.0.0.1:8081):"))
        self.server_input = QLineEdit()
        
        # Получаем текущий адрес из ws_client
        if ws_client:
            self.server_input.setText(ws_client.uri)
        else:
            self.server_input.setText("ws://127.0.0.1:8081")
        
        self.server_input.setPlaceholderText("ws://IP:PORT")
        layout.addWidget(self.server_input)
        
        # Кнопки
        buttons = QHBoxLayout()
        ok_button = QPushButton("Применить")
        cancel_button = QPushButton("Отмена")
        
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; }
            QLineEdit { 
                background-color: #444; 
                color: #FFC107; 
                border: 1px solid #555; 
                border-radius: 4px; 
                padding: 8px; 
                font-size: 13px;
            }
            QPushButton { 
                background-color: #444; 
                color: #FFC107; 
                border: 1px solid #555; 
                border-radius: 4px; 
                padding: 10px 20px; 
            }
            QPushButton:hover { background-color: #555; }
        """)
    
    def get_server_uri(self):
        """Возвращает введенный адрес сервера"""
        uri = self.server_input.text().strip()
        # Базовая валидация
        if not uri.startswith("ws://") and not uri.startswith("wss://"):
            QMessageBox.warning(self, "Ошибка", "Адрес должен начинаться с ws:// или wss://")
            return None
        return uri


def main():
    app = QApplication(sys.argv)

    # Показать диалог логина
    from login_dialog import LoginDialog
    login_dialog = LoginDialog()

    if login_dialog.exec() == QDialog.DialogCode.Accepted:
        # Логин успешен, получаем логин пользователя
        user_login = login_dialog.get_user_login()

        # Показываем главное окно с логином пользователя
        window = MainWindow(user_login=user_login)
        window.showMaximized()
        window.show()
        sys.exit(app.exec())
    else:
        # Логин отменен
        sys.exit(0)

if __name__ == "__main__":
    main()
