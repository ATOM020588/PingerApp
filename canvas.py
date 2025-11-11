#Управление канвасом canvas.py
import sys
import json
import os
import math
import shutil
import webbrowser
import pickle
import requests
from PyQt6.QtWidgets import (QGraphicsPixmapItem, QMessageBox, QGraphicsTextItem)
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
            "switches": [], "plan_switches": [], "users": [], "soaps": [], "legends": [], "magistrals": []
        }
        self.setStyleSheet("border-radius: 12px; border: 3px solid #3d3d3d;")
        self.setSceneRect(0, 0, int(self.map_data["map"].get("width", "1200")), int(self.map_data["map"].get("height", "800")))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.is_edit_mode = False

        # --- Перетаскивание ---
        self.dragged_node = None
        self.dragged_type = None
        self.drag_start_pos = None
        self.drag_group = False
        self.group_drag_offset = []

        # --- Выделение ---
        self.selection_rect = None
        self.selection_start = None
        self.selected_nodes = []  # [(node, type, key), ...]
        self.selection_graphics = []

        # --- ПКМ паннинг ---
        self._panning = False
        self._last_pos = None
        self._context_menu_pos = None
        self._moved_during_rmb = False

        # --- Ссылки на графические элементы ---
        self.node_items = {}  # {(id, type): [QGraphicsItem, ...]}

        # --- Размеры иконок ---
        self.icon_sizes = {
            "switch": (60, 60),
            "plan_switch": (60, 60),
            "user": (50, 50),
            "soap": (50, 50)
        }

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.render_map()

    def render_map(self):
        print("Rendering map...")
        self.scene.clear()
        self.node_items.clear()
        self.scene.setBackgroundBrush(QBrush(QColor("#008080")))

        all_nodes = [
            *[{**s, "type": "switch", "x": s["xy"]["x"], "y": s["xy"]["y"]} for s in self.map_data.get("switches", [])],
            *[{**p, "type": "plan_switch", "x": p["xy"]["x"], "y": p["xy"]["y"]} for p in self.map_data.get("plan_switches", [])],
            *[{**u, "type": "user", "x": u["xy"]["x"], "y": u["xy"]["y"]} for u in self.map_data.get("users", [])],
            *[{**s, "type": "soap", "x": s["xy"]["x"], "y": s["xy"]["y"]} for s in self.map_data.get("soaps", [])],
            *[{**l, "type": "legend", "x": l["xy"]["x"], "y": l["xy"]["y"], "name": l["text"]} for l in self.map_data.get("legends", [])]
        ]

        # === ЛЕГЕНДЫ ===
        for node in all_nodes:
            if node["type"] == "legend":
                fill_color = "transparent" if node.get("zalivka") == "0" else node.get("zalivkacolor", "#fff")
                w = float(node.get("width", 100))
                h = float(node.get("height", 50))
                x, y = node["x"], node["y"]
                legend = self.scene.addRect(x, y, w, h,
                    pen=QPen(QColor(node.get("bordercolor", "#000")), float(node.get("borderwidth", 2))),
                    brush=QBrush(QColor(fill_color)))
                legend.setZValue(-1)

                text = self.scene.addText(node.get("name") or node.get("text") or "")
                text.setDefaultTextColor(QColor(node.get("textcolor", "#000")))
                text_rect = text.boundingRect()
                text.setPos(x + (w - text_rect.width()) / 2, y + (h - text_rect.height()) / 2)
                font = text.font()
                font.setPixelSize(int(node.get("textsize", 14)))
                font.setBold(True)
                text.setFont(font)
                text.setZValue(-1)

        # === МАГИСТРАЛИ ===
        for link in self.map_data.get("magistrals", []):
            source = next((n for n in all_nodes if n["id"] == link["startid"]), None)
            target = next((n for n in all_nodes if n["id"] == link["endid"]), None)
            if source and target:
                pen = QPen(QColor(link.get("color", "#000")), float(link.get("width", 1)))
                if link.get("style") == "psdot":
                    pen.setDashPattern([5, 5])
                self.scene.addLine(source["x"], source["y"], target["x"], target["y"], pen)

                for port, node, other, pkey, fkey, ckey in [
                    (link.get("startport"), source, target, "startport", "startportfar", "startportcolor"),
                    (link.get("endport"), target, source, "endport", "endportfar", "endportcolor")
                ]:
                    if port and port != "0":
                        dx = other["x"] - node["x"]
                        dy = other["y"] - node["y"]
                        length = math.hypot(dx, dy)
                        dist = float(link.get(fkey, 10))
                        if length > 0:
                            dx, dy = dx / length, dy / length
                            px = node["x"] + dx * dist
                            py = node["y"] + dy * dist
                        else:
                            px, py = node["x"] + dist, node["y"]

                        port_text = self.scene.addText(str(port))
                        port_text.setDefaultTextColor(QColor(link.get(ckey, "#000080")))
                        font = port_text.font()
                        font.setPixelSize(12)
                        port_text.setFont(font)
                        rect = port_text.boundingRect()
                        sq_w = rect.width() + 4
                        sq_h = 15
                        self.scene.addRect(px - sq_w/2, py - sq_h/2, sq_w, sq_h,
                            pen=QPen(QColor(link.get("color", "#000")), 1),
                            brush=QBrush(QColor("#008080"))).setZValue(0)
                        port_text.setPos(px - rect.width()/2, py - rect.height()/2)
                        port_text.setZValue(1)

        # === УЗЛЫ (switch, user и т.д.) ===
        for node in all_nodes:
            if node["type"] == "legend":
                continue

            node_id = node["id"]
            node_type = node["type"]
            key = (node_id, node_type)
            x, y = node["x"], node["y"]
            items = []

            # --- Иконка ---
            image_path = overlay_path = None
            if node_type == "switch":
                if node.get("notinstalled") == "-1":
                    image_path = "canvas/Router_off.png"
                    overlay_path = "canvas/other/not_install.png"
                elif node.get("notsettings") == "-1":
                    image_path = "canvas/Router.png"
                    overlay_path = "canvas/other/not_settings.png"
                else:
                    image_path = "canvas/Router.png"
            elif node_type == "plan_switch":
                image_path = "canvas/Router_plan.png"
            elif node_type == "user":
                image_path = "canvas/Computer.png"
            elif node_type == "soap":
                image_path = "canvas/Switch.png"

            pixmap_item = None
            w, h = 0, 0
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                pixmap_item = self.scene.addPixmap(pixmap)
                w, h = pixmap.width(), pixmap.height()
                pixmap_item.setPos(x - w/2, y - h/2)
                pixmap_item.setZValue(2)
                items.append(pixmap_item)
            else:
                color = {"switch": "#555", "plan_switch": "#888", "user": "#00f", "soap": "#0f0"}.get(node_type, "#555")
                rect_item = self.scene.addRect(x-7.5, y-6.5, 15, 13, brush=QBrush(QColor(color)))
                rect_item.setZValue(2)
                items.append(rect_item)
                w, h = 15, 13

            # --- Overlay ---
            if overlay_path and os.path.exists(overlay_path):
                overlay = QPixmap(overlay_path)
                overlay_item = self.scene.addPixmap(overlay)
                overlay_item.setPos(x - w/2, y - h/2)
                overlay_item.setZValue(3)
                items.append(overlay_item)

            # --- Текст ---
            text = node.get("name") or node.get("text") or f"{node_type.capitalize()} {node_id}"
            text_item = self.scene.addText(text)
            text_item.setDefaultTextColor(QColor("#dbdbdb"))
            font = text_item.font()
            font.setPixelSize(12)
            font.setBold(True)
            text_item.setFont(font)
            text_item.setPos(x - text_item.boundingRect().width()/2, y + h/2 + 15)
            text_item.setZValue(4)
            items.append(text_item)

            # --- Сохраняем ---
            self.node_items[key] = items

        # === Обновляем выделение ===
        self.update_selection_graphics()

    # === МЫШЬ ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            result = self.find_node_by_position(scene_pos)

            # Shift + ЛКМ — снять выделение
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and result:
                node, ntype, key = result
                self.remove_from_selection(node, ntype, key)
                event.accept()
                return

            # Режим редактирования: начать перетаскивание
            if self.is_edit_mode and result:
                node, ntype, key = result
                self.dragged_node = node
                self.dragged_type = ntype
                self.drag_start_pos = scene_pos
                event.accept()
                return

            # Клик по выделенному — начать групповое перетаскивание
            if result and any(n[0] is result[0] for n in self.selected_nodes):
                self.drag_group = True
                self.drag_start_pos = scene_pos
                self.group_drag_offset = [(scene_pos.x() - n[0]["xy"]["x"], scene_pos.y() - n[0]["xy"]["y"]) for n in self.selected_nodes]
                event.accept()
                return

            # Клик в пустоту — начать рамку
            if not result:
                self.selection_start = scene_pos
                self.selected_nodes = []
                self.clear_selection_graphics()
                event.accept()
                return

        elif event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_pos = event.position().toPoint()
            self._context_menu_pos = event.position().toPoint()
            self._moved_during_rmb = False
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())

        # === Групповое перетаскивание ===
        if self.drag_group:
            dx = scene_pos.x() - self.drag_start_pos.x()
            dy = scene_pos.y() - self.drag_start_pos.y()
            for (node, ntype, _), (ox, oy) in zip(self.selected_nodes, self.group_drag_offset):
                new_x = self.drag_start_pos.x() - ox + dx
                new_y = self.drag_start_pos.y() - oy + dy
                key = (node["id"], ntype)
                if key in self.node_items:
                    for item in self.node_items[key]:
                        if isinstance(item, QGraphicsPixmapItem):
                            w, h = item.pixmap().width(), item.pixmap().height()
                            item.setPos(new_x - w/2, new_y - h/2)
                        elif isinstance(item, QGraphicsTextItem):
                            item.setPos(new_x - item.boundingRect().width()/2, new_y + h/2 + 15)
            self.update_selection_graphics()
            event.accept()
            return

        # === Одиночное перетаскивание ===
        if self.dragged_node:
            key = (self.dragged_node["id"], self.dragged_type)
            if key in self.node_items:
                for item in self.node_items[key]:
                    if isinstance(item, QGraphicsPixmapItem):
                        w, h = item.pixmap().width(), item.pixmap().height()
                        item.setPos(scene_pos.x() - w/2, scene_pos.y() - h/2)
                    elif isinstance(item, QGraphicsTextItem):
                        item.setPos(scene_pos.x() - item.boundingRect().width()/2, scene_pos.y() + h/2 + 15)
            self.update_selection_graphics()
            event.accept()
            return

        # === Резиновая рамка ===
        if self.selection_start:
            if not self.selection_rect:
                self.selection_rect = self.scene.addRect(0, 0, 0, 0,
                    pen=QPen(QColor("#FFC107"), 1, Qt.PenStyle.DashLine))
                self.selection_rect.setZValue(1000)
            x1, y1 = self.selection_start.x(), self.selection_start.y()
            x2, y2 = scene_pos.x(), scene_pos.y()
            rect = QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
            self.selection_rect.setRect(rect)
            self.update_selection_from_rect(rect)
            event.accept()
            return

        # === ПКМ паннинг ===
        if self._panning:
            cur = event.position().toPoint()
            last = self._last_pos or cur
            delta = cur - last
            h = self.horizontalScrollBar()
            v = self.verticalScrollBar()
            h.setValue(max(h.minimum(), min(h.maximum(), h.value() - delta.x())))
            v.setValue(max(v.minimum(), min(v.maximum(), v.value() - delta.y())))
            self._last_pos = cur
            self._moved_during_rmb = True
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())

            # === Группа ===
            if self.drag_group:
                dx = scene_pos.x() - self.drag_start_pos.x()
                dy = scene_pos.y() - self.drag_start_pos.y()
                for (node, _, _), (ox, oy) in zip(self.selected_nodes, self.group_drag_offset):
                    node["xy"]["x"] = self.drag_start_pos.x() - ox + dx
                    node["xy"]["y"] = self.drag_start_pos.y() - oy + dy
                self.drag_group = False
                self.save_map_to_file()
                event.accept()
                return

            # === Один узел ===
            if self.dragged_node:
                self.dragged_node["xy"]["x"] = scene_pos.x()
                self.dragged_node["xy"]["y"] = scene_pos.y()
                self.dragged_node = None
                self.save_map_to_file()
                event.accept()
                return

            # === Рамка ===
            if self.selection_start:
                self.selection_start = None
                if self.selection_rect:
                    self.scene.removeItem(self.selection_rect)
                    self.selection_rect = None
                self.update_selection_graphics()
                event.accept()
                return

        elif event.button() == Qt.MouseButton.RightButton and self._panning:
            self._panning = False
            if not self._moved_during_rmb:
                scene_pos = self.mapToScene(self._context_menu_pos)
                result = self.find_node_by_position(scene_pos)
                if result:
                    node, ntype, _ = result
                    if ntype == "plan_switch":
                        self.show_plan_switch_context_menu(self._context_menu_pos, node)
                    else:
                        self.show_context_menu(self._context_menu_pos)
                else:
                    self.show_context_menu(self._context_menu_pos)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    # === ВЫДЕЛЕНИЕ ===
    def update_selection_from_rect(self, rect):
        self.selected_nodes = []
        for items, ntype, key in [
            (self.map_data.get("switches", []), "switch", "switches"),
            (self.map_data.get("plan_switches", []), "plan_switch", "plan_switches"),
            (self.map_data.get("users", []), "user", "users"),
            (self.map_data.get("soaps", []), "soap", "soaps"),
            (self.map_data.get("legends", []), "legend", "legends")
        ]:
            for item in items:
                x, y = item["xy"]["x"], item["xy"]["y"]
                if rect.contains(QPointF(x, y)):
                    self.selected_nodes.append((item, ntype, key))
        self.update_selection_graphics()

    def update_selection_graphics(self):
        self.clear_selection_graphics()
        if not self.selected_nodes:
            return

        padding = 2
        group_min_x = group_min_y = float('inf')
        group_max_x = group_max_y = float('-inf')

        for node, ntype, _ in self.selected_nodes:
            x, y = node["xy"]["x"], node["xy"]["y"]
            if ntype == "legend":
                w = float(node.get("width", 100))
                h = float(node.get("height", 50))
                rect = QRectF(x, y, w, h)
            else:
                w, h = self.icon_sizes.get(ntype, (50, 50))
                rect = QRectF(x - w/2, y - h/2, w, h)
            padded = rect.adjusted(-padding, -padding, padding, padding)
            border = self.scene.addRect(padded, pen=QPen(QColor("#FFC107"), 1, Qt.PenStyle.DashLine))
            border.setZValue(999)
            self.selection_graphics.append(border)

            group_min_x = min(group_min_x, padded.left())
            group_min_y = min(group_min_y, padded.top())
            group_max_x = max(group_max_x, padded.right())
            group_max_y = max(group_max_y, padded.bottom())

        if len(self.selected_nodes) > 1:
            group_rect = QRectF(group_min_x, group_min_y, group_max_x - group_min_x, group_max_y - group_min_y)
            group_rect.adjust(-padding, -padding, padding, padding)
            gborder = self.scene.addRect(group_rect, pen=QPen(QColor("#FFC107"), 1, Qt.PenStyle.DashLine))
            gborder.setZValue(998)
            self.selection_graphics.append(gborder)

    def clear_selection_graphics(self):
        for item in self.selection_graphics[:]:
            try:
                if item.scene():
                    item.scene().removeItem(item)
            except:
                pass
        self.selection_graphics.clear()

    def remove_from_selection(self, node, ntype, key):
        self.selected_nodes = [n for n in self.selected_nodes if n[0] is not node]
        self.update_selection_graphics()
        
    # === КОНТЕКСТНОЕ МЕНЮ ===
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
        
        

    # === УТИЛИТЫ ===
    def find_node_by_position(self, pos):
        tolerance = 50
        candidates = [
            (self.map_data.get("switches", []), "switch", "switches"),
            (self.map_data.get("plan_switches", []), "plan_switch", "plan_switches"),
            (self.map_data.get("users", []), "user", "users"),
            (self.map_data.get("soaps", []), "soap", "soaps"),
            (self.map_data.get("legends", []), "legend", "legends")
        ]
        closest = None
        min_dist = float('inf')
        for items, ntype, key in candidates:
            for item in items:
                dist = math.hypot(pos.x() - item["xy"]["x"], pos.y() - item["xy"]["y"])
                if dist < min_dist and dist < tolerance:
                    min_dist = dist
                    closest = (item, ntype, key)
        return closest

    def save_map_to_file(self):
        if hasattr(self.parent, "current_map_file") and self.parent.current_map_file:
            with open(self.parent.current_map_file, 'w', encoding='utf-8') as f:
                json.dump(self.map_data, f, ensure_ascii=False, indent=2)
                
    def trigger_parent_edit_button(self):
        parent = self.window()
        if hasattr(parent, "edit_button"):
            parent.edit_button.click()
        else:
            print("Родительское окно не имеет кнопки edit_button")

    def trigger_parent_settings_button(self):
        parent = self.window()
        if hasattr(parent, "settings_button"):
            parent.settings_button.click()
            print("Имитация клика по кнопке 'Параметры карты'")
        else:
            print("Родительское окно не имеет кнопки settings_button")

    def add_node(self, node_type, position):
        scene_pos = self.mapToScene(position)
        print(f"Adding {node_type} at scene position ({scene_pos.x()}, {scene_pos.y()})")
        # Реализуйте добавление по типу

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

    def show_message(self, text):
        QMessageBox.information(self, "Инфо", text)

    def styled_messagebox(self, title, text, icon=QMessageBox.Icon.Question):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(icon)
        msg.setStyleSheet("""
            QMessageBox { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QMessageBox QLabel { color: #FFC107; font-size: 12px; }
            QMessageBox QPushButton { background-color: #333; color: #FFC107; border: 1px solid #444; border-radius: 4px; padding: 0px 0px; min-width: 100px; min-height: 35px; font-weight: bold; }
            QMessageBox QPushButton:hover { background-color: #FFC107; color: #333; }
            QMessageBox QPushButton:pressed { background-color: #e6b800; }
        """)
        return msg
            
            
        
        
    # === MESSAGE BOX ===       
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