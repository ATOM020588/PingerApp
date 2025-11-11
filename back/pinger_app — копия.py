import sys
import json
import uuid
import os
import math
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QGraphicsView, QGraphicsScene, QDialog, QLineEdit, QPushButton, QLabel,
                             QTableWidget, QTableWidgetItem, QFormLayout, QSpinBox, QFrame, QHeaderView, QComboBox, QListWidget, QCheckBox)
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

        # Отрисовка легенд в первую очередь, чтобы они были на заднем плане
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
                legend.setZValue(-1)  # Легенды позади остальных элементов
                print(f"Added legend at ({x}, {y}) with size {legend_width}x{legend_height}")
                # Добавление текста легенды
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
                text.setZValue(-1)  # Текст легенды также на заднем плане
                print(f"Added legend text '{node.get('name') or node.get('text') or ''}' at ({text_x}, {text_y})")

        # Отрисовка магистралей (линий между узлами)
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

                # Отрисовка номеров портов
                for port, node, other_node, port_key, far_key, color_key in [
                    (link.get("startport"), source_node, target_node, "startport", "startportfar", "startportcolor"),
                    (link.get("endport"), target_node, source_node, "endport", "endportfar", "endportcolor")
                ]:
                    if port and port != "0":  # Пропуск порта "0"
                        dx = other_node["x"] - node["x"]
                        dy = other_node["y"] - node["y"]
                        length = math.sqrt(dx**2 + dy**2)
                        distance = float(link.get(far_key, 10))  # По умолчанию 10, если far_key отсутствует
                        if length > 0:
                            dx, dy = dx / length, dy / length
                            port_x = node["x"] + dx * distance
                            port_y = node["y"] + dy * distance
                        else:
                            port_x, port_y = node["x"] + distance, node["y"]

                        # Добавление текста порта
                        port_text = self.scene.addText(str(port))
                        port_text.setDefaultTextColor(QColor(link.get(color_key, "#000080")))  # По умолчанию #000080
                        font = port_text.font()
                        font.setPixelSize(12)  # Размер шрифта 12px
                        port_text.setFont(font)
                        text_rect = port_text.boundingRect()
                        # Добавление квадратной рамки (13x13 px) в цвете магистрали
                        square = self.scene.addRect(
                            port_x - 6.5, port_y - 6.5, 16, 14,
                            pen=QPen(QColor(link.get("color", "#000")), 1)
                        )
                        square.setBrush(QBrush(QColor("#008080")))
                        square.setZValue(0)  # Квадрат выше легенд
                        port_text.setPos(port_x - text_rect.width() / 2, port_y - text_rect.height() / 2)
                        port_text.setZValue(1)  # Текст выше квадрата
                        print(f"Added port {port_key} '{port}' at ({port_x - text_rect.width() / 2}, {port_y - text_rect.height() / 2}) with distance {distance} and color {link.get(color_key, '#000080')}")

        # Отрисовка остальных узлов (switches, plan_switches, users, soaps)
        for node in all_nodes:
            if node["type"] != "legend":
                # Определение пути к изображению в зависимости от типа узла
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
                        print(f"Ошибка загрузки изображения {image_path}: {str(e)}")
                        image_width = 15  # Резервный размер
                        image_height = 13
                        offset_x = image_width / 2
                        offset_y = image_height / 2
                else:
                    image_width = 15
                    image_height = 13
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
                            item.setZValue(2)  # Узлы выше магистралей и легенд
                            image_width = pixmap.width()
                            print(f"Добавлено изображение {node['type']} '{image_path}' в ({x}, {y}) размером {pixmap.width()}x{pixmap.height()}")
                        except Exception as e:
                            print(f"Ошибка загрузки изображения {image_path}: {str(e)}")
                            color = {"switch": "#555", "plan_switch": "#888", "user": "#00f", "soap": "#0f0"}.get(node["type"])
                            item = self.scene.addRect(x, y, 15, 13, brush=QBrush(QColor(color)))
                            item.setZValue(2)
                            image_width = 15
                            print(f"Резерв: Добавлен прямоугольник {node['type']} в ({x}, {y}) с цветом {color}")

                    if overlay_image:
                        try:
                            overlay_pixmap = QPixmap(overlay_image)
                            item = self.scene.addPixmap(overlay_pixmap)
                            item.setPos(x, y)
                            item.setZValue(3)  # Оверлей выше узлов
                            print(f"Добавлено оверлей-изображение '{overlay_image}' в ({x}, {y}) размером {overlay_pixmap.width()}x{overlay_pixmap.height()}")
                        except Exception as e:
                            print(f"Ошибка загрузки оверлей-изображения {overlay_image}: {str(e)}")

                # Добавление текста, центрированного по горизонтали под изображением
                text = self.scene.addText(node.get("name") or node.get("text") or f"{node['type'].capitalize()} {node['id']}")
                text.setDefaultTextColor(QColor("#dbdbdb"))
                text_width = text.boundingRect().width()
                text_x = x + (image_width - text_width) / 2  # Центрирование текста по горизонтали
                text_y = y + offset_y + 15
                text.setPos(text_x, text_y)
                font = text.font()
                font.setPixelSize(12)
                font.setBold(True)
                text.setFont(font)
                text.setZValue(4)  # Текст выше всех элементов
                print(f"Добавлен текст '{node.get('name') or node.get('text') or f'{node['type'].capitalize()} {node['id']}'}' в ({text_x}, {text_y})")

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
        # Запрет редактирования ячеек и выделение строк
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
        # Заполнение таблицы карт
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
                # Установка элементов таблицы с флагами только для выбора
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

class OperatorsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление операторами")
        self.setFixedSize(800, 600)
        self.setup_ui()

    def setup_ui(self):
        # Настройка основного макета диалога
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Кнопки управления операторами
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

        # Таблица операторов
        self.operators_table = QTableWidget()
        self.operators_table.setColumnCount(5)
        self.operators_table.setHorizontalHeaderLabels(["Фамилия", "Имя", "Логин", "Отдел/Должность", "Последняя активность"])
        self.operators_table.verticalHeader().setVisible(False)  # Скрытие нумерации строк
        self.operators_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Запрет редактирования ячеек и выделение строк
        self.operators_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.operators_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.operators_table)

        # Подключение кнопок к методам
        self.configure_groups_button.clicked.connect(self.show_group_modal)
        self.create_operator_button.clicked.connect(lambda: self.show_operator_modal("create"))
        self.edit_operator_button.clicked.connect(lambda: self.show_operator_modal("edit"))
        self.delete_operator_button.clicked.connect(self.delete_operator)

        # Загрузка данных
        self.load_groups()
        self.load_operators()

        # Применение стилей, соответствующих OpenMapDialog, без выделения заголовков
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
        # Загрузка данных операторов из файла
        users_path = "operators/users.json"
        # Проверка и создание директории operators/, если она не существует
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
                item.setTextAlignment(Qt.AlignCenter)
                self.operators_table.setItem(0, 0, item)
                self.operators_table.setSpan(0, 0, 1, 5)
        except json.JSONDecodeError as e:
            # Обработка ошибки формата JSON
            print(f"Ошибка формата JSON в {users_path}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле операторов: {str(e)}", "error")
            self.users_data = []
            self.operators_table.setRowCount(1)
            item = QTableWidgetItem("Ошибка загрузки операторов")
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignCenter)
            self.operators_table.setItem(0, 0, item)
            self.operators_table.setSpan(0, 0, 1, 5)

    def load_groups(self):
        # Загрузка данных групп из файла
        groups_path = "operators/groups.json"
        # Проверка и создание директории operators/, если она не существует
        os.makedirs(os.path.dirname(groups_path), exist_ok=True)
        try:
            if os.path.exists(groups_path):
                with open(groups_path, "r", encoding="utf-8") as f:
                    self.groups_data = json.load(f)
            else:
                self.groups_data = []
        except json.JSONDecodeError as e:
            # Обработка ошибки формата JSON
            print(f"Ошибка формата JSON в {groups_path}: {str(e)}")
            self.show_toast(f"Ошибка формата JSON в файле групп: {str(e)}", "error")
            self.groups_data = []

    def show_operator_modal(self, mode):
        # Отображение модального окна для создания/редактирования оператора
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

        # Применение стилей, соответствующих OpenMapDialog
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
        # Сохранение данных оператора
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
        os.makedirs(os.path.dirname(users_path), exist_ok=True)  # Создание директории, если не существует
        with open(users_path, "w", encoding="utf-8") as f:
            json.dump(self.users_data + [operator] if mode == "create" else [op if op["id"] != operator["id"] else operator for op in self.users_data], f, ensure_ascii=False, indent=4)

        self.load_operators()
        dialog.accept()

    def delete_operator(self):
        # Удаление выбранного оператора
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
        # Отображение модального окна для настройки групп
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройка групп")
        dialog.setFixedSize(600, 600)
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
        permissions_column.addWidget(QLabel("Настройки группы"))
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

        # Применение стилей с увеличенной высотой для поля "Название группы"
        dialog.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QListWidget { background-color: #444; color: #FFC107; border: 1px solid #555; }
            QListWidget::item:hover { background-color: #555; }
            QListWidget::item:selected { background-color: #75736b; color: #333; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 5px; height: 20px; }
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
        # Загрузка данных выбранной группы
        group_name = item.text()
        group = next((g for g in self.groups_data if g["name"] == group_name), None)
        if group:
            self.group_name_input.setText(group["name"])
            for key, checkbox in self.group_permissions_checkboxes.items():
                checkbox.setChecked(group.get("permissions", {}).get(key, False))
            self.group_id = group["id"]

    def save_group(self, dialog):
        # Сохранение данных группы
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
        # Удаление выбранной группы
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
        # Отображение уведомления
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)

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
        operators = QAction("Операторы", self)
        operators.triggered.connect(self.show_operators_dialog)
        options_menu.addAction(operators)
        for opt in ["Техники", "Модели", "Упр. VLAN", "Прошивки"]:
            action = QAction(opt, self)
            action.triggered.connect(lambda checked, o=opt: self.show_toast(f"Открытие {o} не реализовано", "info"))
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
        for btn in [ping_button, settings_button, self.edit_button, logout_button]:
            btn.setStyleSheet("""
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
            QTabWidget::pane { background-color: #333; border: 1px solid #555; }
            QTabBar { alignment: left; }
            QTabBar::tab { background-color: #333; color: #FFC107; padding: 8px 10px; border: 1px solid #555; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background-color: #FFC107; color: #333; }
            QTabBar::tab:hover:!selected { background-color: #444; }
            QTabBar::close-button { background-color: transparent; width: 16px; height: 16px; margin: 2px; padding: 2px; }
            QTabBar::close-button:!selected { background-color: #FFC107; image: url(C:/PingerApp/icons/closetab_inact.png); }
            QTabBar::close-button:selected { background-color: #333; image: url(C:/PingerApp/icons/closetab_act.png); }
            QTabBar::close-button:hover { background-color: #F44336; }
        """)

        self.setGeometry(100, 100, 1200, 900)
        self.load_open_maps()

    def load_open_maps(self):
        # Загрузка открытых карт
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
        # Сохранение открытых карт
        try:
            with open("open_maps.pkl", "wb") as f:
                pickle.dump(self.open_maps, f)
        except Exception as e:
            self.show_toast(f"Ошибка сохранения открытых карт: {str(e)}", "error")

    def update_tabs(self):
        # Обновление вкладок
        self.tabs.blockSignals(True)
        self.tabs.clear()
        for map_info in self.open_maps:
            canvas = MapCanvas(self.map_data.get(map_info["id"], {}))
            self.tabs.addTab(canvas, map_info["name"])
            if map_info["id"] == self.active_map_id:
                self.tabs.setCurrentWidget(canvas)
        self.tabs.blockSignals(False)

    def show_create_map_dialog(self):
        # Отображение диалога создания карты
        dialog = MapNameDialog(self)
        dialog.setModal(False)
        dialog.accepted.connect(lambda: self.on_create_map_accepted(dialog))
        dialog.show()

    def on_create_map_accepted(self, dialog):
        # Обработка создания новой карты
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
        # Отображение диалога открытия карты
        dialog = OpenMapDialog(self)
        dialog.setModal(False)
        dialog.accepted.connect(lambda: self.on_open_map_accepted(dialog))
        dialog.show()

    def on_open_map_accepted(self, dialog):
        # Обработка открытия карты
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
        # Сохранение текущей карты
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

    def show_map_settings_dialog(self):
        # Отображение диалога настроек карты
        if not self.active_map_id:
            self.show_toast("Нет активной карты для настройки", "info")
            return
        dialog = MapSettingsDialog(self, self.map_data.get(self.active_map_id))
        dialog.setModal(False)
        dialog.accepted.connect(lambda: self.on_map_settings_accepted(dialog))
        dialog.show()

    def on_map_settings_accepted(self, dialog):
        # Обработка изменений настроек карты
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
        # Пинг устройств на карте
        if not self.active_map_id or not self.map_data.get(self.active_map_id, {}).get("switches"):
            self.show_toast("Нет устройств для пинга", "error")
            return
        for switch_device in self.map_data[self.active_map_id]["switches"]:
            switch_device["pingok"] = bool(switch_device.get("ip"))
        self.update_tabs()
        self.show_toast("Пинг устройств завершен", "success")

    def toggle_edit_mode(self):
        # Переключение режима редактирования
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
        # Закрытие вкладки
        map_id = self.open_maps[index]["id"]
        self.open_maps.pop(index)
        self.save_open_maps()
        if self.active_map_id == map_id:
            self.active_map_id = self.open_maps[0]["id"] if self.open_maps else None
            if self.active_map_id:
                self.open_map(self.active_map_id)
        self.update_tabs()

    def switch_tab(self, index):
        # Переключение вкладки
        if index >= 0 and self.open_maps[index]["id"] != self.active_map_id:
            self.active_map_id = self.open_maps[index]["id"]
            self.update_tabs()

    def open_map(self, map_id):
        # Открытие карты
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
        # Отображение уведомления
        toast = ToastWidget(message, toast_type)
        toast.show()
        desktop = QApplication.primaryScreen().geometry()
        toast.move(desktop.width() - toast.width() - 20, desktop.height() - toast.height() - 20)

    def logout(self):
        # Выход из системы
        self.show_toast("Выход выполнен", "info")
        QApplication.quit()

    def show_operators_dialog(self):
        # Отображение диалога управления операторами
        dialog = OperatorsDialog(self)
        dialog.exec()

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