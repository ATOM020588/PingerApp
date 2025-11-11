#Управление канвасом canvas.py
import sys
import json
import os
import math
import shutil
import webbrowser
import pickle
import requests
from PyQt6.QtWidgets import (QGraphicsPixmapItem, QMessageBox)
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenuBar, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGraphicsView, QGraphicsScene, QDialog, QLineEdit)
from PyQt6.QtWidgets import (QPushButton, QLabel, QTableWidget, QTableWidgetItem, QFormLayout, QSpinBox, QHeaderView, QComboBox, QListWidget, QCheckBox, QTextEdit, QFileDialog)
from PyQt6.QtGui import QAction, QColor, QBrush, QPen, QPainter, QPixmap, QIcon
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from datetime import datetime


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
        self._context_menu_pos = None
        self._moved_during_rmb = False
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
            # Сохраняем позицию как QPoint (целые координаты)
            self._panning = True
            self._last_pos = event.position().toPoint()        # ← QPoint!
            self._context_menu_pos = event.position().toPoint()
            self._moved_during_rmb = False
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
    # ------------------- ПАННИНГ ПКМ -------------------
        if getattr(self, '_panning', False):
            cur_pos = event.position().toPoint()           # QPoint
            last_pos = getattr(self, '_last_pos', cur_pos)  # уже QPoint

            delta = cur_pos - last_pos                     # QPoint → int
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()

            new_h = h_bar.value() - delta.x()
            new_v = v_bar.value() - delta.y()

            # Ограничиваем диапазон
            new_h = max(h_bar.minimum(), min(h_bar.maximum(), new_h))
            new_v = max(v_bar.minimum(), min(v_bar.maximum(), new_v))

            h_bar.setValue(new_h)
            v_bar.setValue(new_v)

            self._last_pos = cur_pos
            self._moved_during_rmb = True
            event.accept()
            return

        # ------------------- ПЕРЕТАСКИВАНИЕ УЗЛА -------------------
        if getattr(self, 'dragged_node', None) is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.render_map()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and getattr(self, 'dragged_node', None) is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.render_map()
            self.save_map_to_file()
            print(f"Перемещён {self.dragged_type} '{self.dragged_node.get('name')}' → ({scene_pos.x():.1f}, {scene_pos.y():.1f})")
            self.dragged_node = None
            self.dragged_type = None
            event.accept()

        elif event.button() == Qt.MouseButton.RightButton and getattr(self, '_panning', False):
            self._panning = False
            if not self._moved_during_rmb:
                scene_pos = self.mapToScene(self._context_menu_pos)
                result = self.find_node_by_position(scene_pos)
                if result:
                    node, node_type, _ = result
                    if node_type == "plan_switch":
                        self.show_plan_switch_context_menu(self._context_menu_pos, node)
                    else:
                        self.show_context_menu(self._context_menu_pos)
                else:
                    self.show_context_menu(self._context_menu_pos)
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
                node, node_type, key = result
                if self.is_edit_mode:
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
            # Сохраняем позицию как QPoint (целые координаты)
            self._panning = True
            self._last_pos = event.position().toPoint()        # ← QPoint!
            self._context_menu_pos = event.position().toPoint()
            self._moved_during_rmb = False
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
    # ------------------- ПАННИНГ ПКМ -------------------
        if getattr(self, '_panning', False):
            cur_pos = event.position().toPoint()           # QPoint
            last_pos = getattr(self, '_last_pos', cur_pos)  # уже QPoint

            delta = cur_pos - last_pos                     # QPoint → int
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()

            new_h = h_bar.value() - delta.x()
            new_v = v_bar.value() - delta.y()

            # Ограничиваем диапазон
            new_h = max(h_bar.minimum(), min(h_bar.maximum(), new_h))
            new_v = max(v_bar.minimum(), min(v_bar.maximum(), new_v))

            h_bar.setValue(new_h)
            v_bar.setValue(new_v)

            self._last_pos = cur_pos
            self._moved_during_rmb = True
            event.accept()
            return

        # ------------------- ПЕРЕТАСКИВАНИЕ УЗЛА -------------------
        if getattr(self, 'dragged_node', None) is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.render_map()
            event.accept()
            return

        super().mouseMoveEvent(event)

        # ------------------- ПЕРЕТАСКИВАНИЕ УЗЛА -------------------
        if getattr(self, 'dragged_node', None) is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.render_map()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and getattr(self, 'dragged_node', None) is not None:
            scene_pos = self.mapToScene(event.position().toPoint())
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.render_map()
            self.save_map_to_file()
            print(f"Перемещён {self.dragged_type} '{self.dragged_node.get('name')}' → ({scene_pos.x():.1f}, {scene_pos.y():.1f})")
            self.dragged_node = None
            self.dragged_type = None
            event.accept()

        elif event.button() == Qt.MouseButton.RightButton and getattr(self, '_panning', False):
            self._panning = False
            if not self._moved_during_rmb:
                scene_pos = self.mapToScene(self._context_menu_pos)
                result = self.find_node_by_position(scene_pos)
                if result:
                    node, node_type, _ = result
                    if node_type == "plan_switch":
                        self.show_plan_switch_context_menu(self._context_menu_pos, node)
                    else:
                        self.show_context_menu(self._context_menu_pos)
                else:
                    self.show_context_menu(self._context_menu_pos)
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