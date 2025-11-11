import sys
import json
import uuid
import os
import math
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QGraphicsView, QGraphicsScene, QDialog, QLineEdit, QPushButton, QLabel,
                             QTableWidget, QTableWidgetItem, QFormLayout, QSpinBox, QFrame, QHeaderView)
from PyQt6.QtGui import QAction, QColor, QBrush, QPen, QPainter, QPixmap
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
import pickle
from datetime import datetime

class Session:
    def __init__(self):
        self.user_id = "12345"
        self.permissions = {"create_map": True, "edit_maps": True}

class MapCanvas(QGraphicsView):
    def __init__(self, map_data=None):
        super().__init__()
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

        # Render legends first to place them in the background
        for node in all_nodes:
            if node["type"] == "legend":
                fill_color = "transparent" if node.get("zalivka") == "0" else node.get("zalivkacolor", "#fff")
                legend_width = float(node.get("width", 100))
                legend_height = float(node.get("height", 50))
                x, y = node["x"] - legend_width / 2, node["y"] - legend_height / 2
                legend = self.scene.addRect(
                    x, y, legend_width, legend_height,
                    pen=QPen(QColor(node.get("bordercolor", "#000")), float(node.get("borderwidth", 2))),
                    brush=QBrush(QColor(fill_color))
                )
                legend.setZValue(-1)  # Place legends behind other items
                print(f"Added legend at ({x}, {y}) with size {legend_width}x{legend_height}")
                # Add legend text
                text = self.scene.addText(node.get("name") or node.get("text") or "")
                text.setDefaultTextColor(QColor(node.get("textcolor", "#000")))
                text_width = text.boundingRect().width()
                text_x = x - text_width * 0.25
                text_y = y - 2
                text.setPos(text_x, text_y)
                font = text.font()
                font.setPixelSize(int(node.get("textsize", 14)))
                font.setBold(True)
                text.setFont(font)
                text.setZValue(-1)  # Ensure text is also in the background
                print(f"Added legend text '{node.get('name') or node.get('text') or ''}' at ({text_x}, {text_y})")

        # Render magistrals (lines connecting nodes)
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

                # Render port numbers
                for port, node, other_node, port_key, far_key, color_key in [
                    (link.get("startport"), source_node, target_node, "startport", "startportfar", "startportcolor"),
                    (link.get("endport"), target_node, source_node, "endport", "endportfar", "endportcolor")
                ]:
                    if port and port != "0":  # Skip if port is "0"
                        # Calculate position at distance specified by far_key from the node along the line
                        dx = other_node["x"] - node["x"]
                        dy = other_node["y"] - node["y"]
                        length = math.sqrt(dx**2 + dy**2)
                        distance = float(link.get(far_key, 10))  # Default to 10 if far_key is missing
                        if length > 0:
                            # Normalize direction vector and move by specified distance
                            dx, dy = dx / length, dy / length
                            port_x = node["x"] + dx * distance
                            port_y = node["y"] + dy * distance
                        else:
                            port_x, port_y = node["x"] + distance, node["y"]

                        # Add port text
                        port_text = self.scene.addText(str(port))
                        port_text.setDefaultTextColor(QColor(link.get(color_key, "#000080")))  # Default to #000080
                        font = port_text.font()
                        font.setPixelSize(12)  # Font size 12px
                        port_text.setFont(font)
                        text_rect = port_text.boundingRect()
                        # Add square outline (13x13 px) in magistral color, centered on magistral line
                        square = self.scene.addRect(
                            port_x - 6.5, port_y - 6.5, 13, 13,
                            pen=QPen(QColor(link.get("color", "#000")), 1)
                        )
                        square.setZValue(0)  # Ensure square is above legends
                        # Center text inside the square
                        port_text.setPos(port_x - text_rect.width() / 2, port_y - text_rect.height() / 2)
                        port_text.setZValue(1)  # Ensure text is above square
                        print(f"Added port {port_key} '{port}' at ({port_x - text_rect.width() / 2}, {port_y - text_rect.height() / 2}) with distance {distance} and color {link.get(color_key, '#000080')}")

        # Render other nodes (switches, plan_switches, users, soaps)
        for node in all_nodes:
            if node["type"] != "legend":
                # Calculate offsets based on node type
                image_path = None
                if node["type"] == "switch":
                    image_path = "canvas/Router_off.png" if node.get("notinstalled") == "-1" else "canvas/Router.png"
                elif node["type"] == "plan_switch":
                    image_path = "canvas/Router_plan.png"
                elif node["type"] == "user":
                    image_path = "canvas/Computer.png"
                elif node["type"] == "soap":
                    image_path = "canvas/Switch.png"
                
                if image_path:
                    try:
                        pixmap = QPixmap(image_path)
                        image_width = pixmap.width()
                        image_height = pixmap.height()
                        offset_x = image_width / 2
                        offset_y = image_height / 2
                    except Exception as e:
                        print(f"Error loading image {image_path}: {str(e)}")
                        image_width = 45  # Fallback size
                        image_height = 45
                        offset_x = image_width / 2
                        offset_y = image_height / 2
                else:
                    image_width = 45
                    image_height = 45
                    offset_x = image_width / 2
                    offset_y = image_height / 2

                x, y = node["x"] - offset_x, node["y"] - offset_y

                if node["type"] in ["switch", "plan_switch", "user", "soap"]:
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
                            item.setPos(x, y)
                            item.setZValue(2)  # Ensure nodes are above magistrals and legends
                            image_width = pixmap.width()
                            print(f"Added {node['type']} image '{image_path}' at ({x}, {y}) with size {pixmap.width()}x{pixmap.height()}")
                        except Exception as e:
                            print(f"Error loading image {image_path}: {str(e)}")
                            color = {"switch": "#555", "plan_switch": "#888", "user": "#00f", "soap": "#0f0"}.get(node["type"])
                            item = self.scene.addRect(x, y, 45, 45, brush=QBrush(QColor(color)))
                            item.setZValue(2)
                            image_width = 45
                            print(f"Fallback: Added {node['type']} rect at ({x}, {y}) with color {color}")

                    if overlay_image:
                        try:
                            overlay_pixmap = QPixmap(overlay_image)
                            item = self.scene.addPixmap(overlay_pixmap)
                            item.setPos(x, y)
                            item.setZValue(3)  # Ensure overlays are above nodes
                            print(f"Added overlay image '{overlay_image}' at ({x}, {y}) with size {overlay_pixmap.width()}x{overlay_pixmap.height()}")
                        except Exception as e:
                            print(f"Error loading overlay image {overlay_image}: {str(e)}")

                # Add text with 25% right offset
                text = self.scene.addText(node.get("name") or node.get("text") or "")
                text.setDefaultTextColor(QColor("#dbdbdb"))
                text_width = text.boundingRect().width()
                text_x = x - text_width * 0.25
                text_y = y + offset_y + 15
                text.setPos(text_x, text_y)
                font = text.font()
                font.setPixelSize(12)
                font.setBold(True)
                text.setFont(font)
                text.setZValue(4)  # Ensure text is above all other items
                print(f"Added text '{node.get('name') or node.get('text') or ''}' at ({text_x}, {text_y})")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position() - self._last_pos
            self._last_pos = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

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
            QHeaderView::section { background-color: #333333; color: #FFC107; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QLabel { color: #FFC107; }
        """)

    def populate_table(self):
        maps_dir = "maps"
        if not os.path.exists(maps_dir):
            os.makedirs(maps_dir)
        map_files = [f for f in os.listdir(maps_dir) if f.endswith(".json")]
        print(f"Found map files: {map_files}")
        self.table.setRowCount(len(map_files))
        for row, map_file in enumerate(map_files):
            try:
                with open(os.path.join(maps_dir, map_file), "r", encoding="utf-8") as f:
                    map_data = json.load(f)
                map_name = map_data.get("map", {}).get("name", map_file[:-5] if not map_file.startswith("map_") else map_file[4:-5])
                mod_time = map_data.get("map", {}).get("mod_time", "Неизвестно")
                last_editor = map_data.get("map", {}).get("last_adm", "Неизвестно")
                self.table.setItem(row, 0, QTableWidgetItem(map_name))
                self.table.setItem(row, 1, QTableWidgetItem(mod_time))
                self.table.setItem(row, 2, QTableWidgetItem(f"Последний редактор: {last_editor}"))
                print(f"Loaded map {map_file}: name={map_name}, mod_time={mod_time}, last_editor={last_editor}")
            except Exception as e:
                print(f"Error loading {map_file}: {str(e)}")
                self.table.setItem(row, 0, QTableWidgetItem(map_file[:-5]))
                self.table.setItem(row, 1, QTableWidgetItem("Ошибка"))
                self.table.setItem(row, 2, QTableWidgetItem(f"Ошибка загрузки: {str(e)}"))

class MapSettingsDialog(QDialog):
    def __init__(self, parent=None, map_data=None):
        super().__init__(parent)
        self.map_data = map_data
        self.setWindowTitle("Параметры карты")
        self.setFixedSize(300, 150)
        layout = QFormLayout()
        self.width_input = QSpinBox()
        self.width_input.setMinimum(100)
        self.width_input.setSingleStep(10)
        self.width_input.setValue(int(map_data["map"].get("width", 1200)) if map_data else 1200)
        self.height_input = QSpinBox()
        self.height_input.setMinimum(100)
        self.height_input.setSingleStep(10)
        self.height_input.setValue(int(map_data["map"].get("height", 800)) if map_data else 800)
        layout.addRow("Ширина:", self.width_input)
        layout.addRow("Высота:", self.height_input)
        buttons = QHBoxLayout()
        ok_button = QPushButton("ОК")
        cancel_button = QPushButton("Отмена")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QSpinBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; }
            QPushButton { background-color: #333; color: #FFC107; border: none; border-radius: 4px; padding: 10px; }
            QPushButton:hover { background-color: #555; }
        """)

class SwitchInfoDialog(QDialog):
    def __init__(self, parent=None, switch_data=None):
        super().__init__(parent)
        self.setWindowTitle("Информация о Switch")
        self.setFixedSize(400, 200)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Имя: {switch_data.get('name', 'Не указано')}"))
        layout.addWidget(QLabel(f"IP: {switch_data.get('ip', 'Не указано')}"))
        layout.addWidget(QLabel(f"Модель: {switch_data.get('model', 'Не указана')}"))
        layout.addWidget(QLabel(f"Мастер: {switch_data.get('master', 'Не указан')}"))
        layout.addWidget(QLabel(f"Питание: {switch_data.get('power', 'Не указано')}"))
        layout.addWidget(QLabel(f"Последний редактор: {switch_data.get('lasteditor', 'Неизвестно')}"))
        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.reject)
        layout.addWidget(close_button)
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QPushButton { background-color: #FFC107; color: #333; border: none; border-radius: 4px; padding: 4px 8px; }
            QPushButton:hover { background-color: #e6ac00; }
        """)

class MainWindow(QMainWindow):
    def __init__(self, session):
        super().__init__()
        self.session = session
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
        save_map = QAction("Сохранить", self)
        logout = QAction("Выйти", self)
        create_map.triggered.connect(self.show_create_map_dialog)
        open_map.triggered.connect(self.show_open_map_dialog)
        save_map.triggered.connect(self.save_map)
        logout.triggered.connect(self.logout)
        file_menu.addAction(create_map)
        file_menu.addAction(open_map)
        file_menu.addAction(save_map)
        file_menu.addAction(logout)

        options_menu = menubar.addMenu("Опции")
        for opt in ["Операторы", "Техники", "Модели", "Упр. VLAN", "Прошивки"]:
            action = QAction(opt, self)
            action.triggered.connect(lambda: self.show_toast(f"Открытие {opt} не реализовано"))
            options_menu.addAction(action)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        button_layout = QHBoxLayout()
        ping_button = QPushButton("Пинговать устройства")
        settings_button = QPushButton("Параметры карты")
        self.edit_button = QPushButton("Редактировать")
        logout_button = QPushButton("Выйти")
        ping_button.clicked.connect(self.ping_switches)
        settings_button.clicked.connect(self.show_map_settings_dialog)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        logout_button.clicked.connect(self.logout)
        button_layout.addStretch()
        button_layout.addWidget(ping_button)
        button_layout.addWidget(settings_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(logout_button)
        layout.addLayout(button_layout)
        ping_button.setStyleSheet("""
            QPushButton { background-color: #333; color: #FFC107; font-size: 12px; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QPushButton:pressed { background-color: #FFC107; color: #333; }
        """)
        settings_button.setStyleSheet("""
            QPushButton { background-color: #333; color: #FFC107; font-size: 12px; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QPushButton:pressed { background-color: #FFC107; color: #333; }
        """)
        self.edit_button.setStyleSheet("""
            QPushButton { background-color: #333; color: #FFC107; font-size: 12px; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QPushButton:pressed { background-color: #FFC107; color: #333; }
        """)
        logout_button.setStyleSheet("""
            QPushButton { background-color: #333; color: #FFC107; font-size: 12px; border: none; border-radius: 2px; padding: 10px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
            QPushButton:pressed { background-color: #FFC107; color: #333; }
        """)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.switch_tab)
        layout.addWidget(self.tabs)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { 
                background-color: #333; 
                border: 1px solid #555; 
            }
            QTabBar { 
                alignment: left; 
            }
            QTabBar::tab { 
                background-color: #333; 
                color: #FFC107; 
                padding-left: 10px;
                padding-right: 10px;
                padding-top: 8px;
                padding-bottom: 8px;
                border: 1px solid #555; 
                border-bottom: none; 
                border-top-left-radius: 4px; 
                border-top-right-radius: 4px; 
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                background-color: #FFC107; 
                color: #333; 
            }
            QTabBar::close-button { 
                background-color: transparent;
                width: 16px; 
                height: 16px; 
                margin: 2px;
                padding: 2px;
                subcontrol-position: right; 
                subcontrol-origin: padding;
            }
            QTabBar::close-button:!selected { 
                background-color: #FFC107;
                image: url(C:/PingerApp/icons/closetab_inact.png);
            }
            QTabBar::close-button:selected { 
                background-color: #333;
                image: url(C:/PingerApp/icons/closetab_act.png);
            }
            QTabBar::close-button:hover { 
                background-color: transparent; 
            }
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
            print(f"Error loading open_maps.pkl: {str(e)}")

    def save_open_maps(self):
        try:
            with open("open_maps.pkl", "wb") as f:
                pickle.dump(self.open_maps, f)
        except Exception as e:
            self.show_toast(f"Ошибка сохранения открытых карт: {str(e)}", "error")
            print(f"Error saving open_maps.pkl: {str(e)}")

    def update_tabs(self):
        print("Updating tabs...")
        self.tabs.blockSignals(True)
        self.tabs.clear()
        for map_info in self.open_maps:
            canvas = MapCanvas(self.map_data.get(map_info["id"], {}))
            self.tabs.addTab(canvas, map_info["name"])
            if map_info["id"] == self.active_map_id:
                self.tabs.setCurrentWidget(canvas)
        self.tabs.blockSignals(False)

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
        if not self.session.permissions.get("edit_maps"):
            self.show_toast("У вас недостаточно прав", "info")
            return
        if not self.active_map_id:
            self.show_toast("Нет активной карты для сохранения", "info")
            return
        try:
            maps_dir = "maps"
            if not os.path.exists(maps_dir):
                os.makedirs(maps_dir)
            with open(os.path.join(maps_dir, f"map_{self.active_map_id}.json"), "w", encoding="utf-8") as f:
                json.dump(self.map_data[self.active_map_id], f, ensure_ascii=False)
            self.show_toast("Карта успешно сохранена", "success")
        except Exception as e:
            self.show_toast(f"Ошибка сохранения карты: {str(e)}", "error")
            print(f"Error saving map_{self.active_map_id}.json: {str(e)}")

    def show_map_settings_dialog(self):
        if not self.session.permissions.get("edit_maps"):
            self.show_toast("У вас недостаточно прав", "info")
            return
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
        self.map_data[self.active_map_id]["map"]["width"] = str(width)
        self.map_data[self.active_map_id]["map"]["height"] = str(height)
        self.update_tabs()
        self.save_map()

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
            background-color: #FFC107; 
            color: #333; 
            font-size: 12px; 
            border: none; 
            border-radius: 2px; 
            padding: 10px;
        """ if self.is_edit_mode else """
            background-color: #333; 
            color: #FFC107; 
            font-size: 12px; 
            border: none; 
            border-radius: 2px; 
            padding: 10px;
        """)
        self.show_toast(f"Режим редактирования: {'включен' if self.is_edit_mode else 'выключен'}", "info")
        if self.tabs.currentWidget():
            self.tabs.currentWidget().is_edit_mode = self.is_edit_mode

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
            print(f"Switching to tab {index}: {self.open_maps[index]['id']}")
            self.active_map_id = self.open_maps[index]["id"]
            self.update_tabs()

    def open_map(self, map_id):
        self.active_map_id = map_id
        map_file = os.path.join("maps", f"map_{map_id}.json")
        print(f"Attempting to load map file: {map_file}")
        try:
            if os.path.exists(map_file):
                with open(map_file, "r", encoding="utf-8") as f:
                    loaded_data = json.load(f)
                self.map_data[map_id] = loaded_data
                print(f"Successfully loaded map data for {map_id}: {loaded_data}")
            else:
                print(f"Map file {map_file} not found, checking alternative naming")
                alt_map_file = os.path.join("maps", f"{map_id}.json")
                if os.path.exists(alt_map_file):
                    with open(alt_map_file, "r", encoding="utf-8") as f:
                        loaded_data = json.load(f)
                    self.map_data[map_id] = loaded_data
                    print(f"Successfully loaded map data from {alt_map_file}: {loaded_data}")
                else:
                    print(f"Map file {alt_map_file} also not found, using default data")
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
            print(f"JSON decode error for {map_file}: {str(e)}")
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
        except Exception as e:
            print(f"Unexpected error loading map {map_id}: {str(e)}")
            self.show_toast(f"Ошибка загрузки карты '{map_id}': {str(e)}", "error")
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

    def logout(self):
        self.show_toast("Выход выполнен", "info")
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    session = Session()
    if not session.user_id:
        print("Пожалуйста, войдите в систему")
        return
    window = MainWindow(session)
    window.showMaximized()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()