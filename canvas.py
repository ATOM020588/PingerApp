# canvas.py with fixes for real-time group move and perimeter grab
#Управление канвасом canvas.py
# Автор: Grok
# Обновлено: November 11, 2025, 11:30 AM CET
# Страна: NL

import sys
import json
import os
import math
import webbrowser
import requests
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem, QMessageBox, QGraphicsTextItem, QGraphicsRectItem, QGraphicsLineItem,
    QGraphicsView, QGraphicsScene, QMenu, QDialog, QLineEdit,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QTextEdit
)
from PyQt6.QtGui import QAction, QColor, QBrush, QPen, QPainter, QPixmap
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF

# Импорт диалогов из отдельной папки
from widgets import SwitchInfoDialog, PlanSwitchInfoDialog, AddPlanedSwitch


# Класс отрисовки карты
class MapCanvas(QGraphicsView):
    def __init__(self, map_data=None, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # ИНИЦИАЛИЗАЦИЯ map_data ПЕРВОЙ!
        self.map_data = map_data or {
            "map": {"name": "Unnamed", "width": "1200", "height": "800"},
            "switches": [], "plan_switches": [], "users": [], "soaps": [], "legends": [], "magistrals": []
        }

        # --- Остальные атрибуты ПОСЛЕ ---
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
        self.magistral_items = []

        # --- Размеры иконок ---
        self.icon_sizes = {
            "switch": (60, 60),
            "plan_switch": (60, 60),
            "user": (50, 50),
            "soap": (50, 50)
        }

        # --- Наведение для диалогов (2 сек) ---
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_hover_dialog)
        self.current_hover_node = None
        self.current_hover_type = None

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        # ← Только после инициализации ВСЕГО!
        self.render_map()

    def render_map(self):
        print("Rendering map...")
        self.scene.clear()
        self.magistral_items = []
        self.node_items.clear()
        self.selection_graphics.clear()  # ← Очистка старых выделений
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
                key = (node["id"], "legend")
                self.node_items[key] = [legend, text]

        # === МАГИСТРАЛИ ===
        self.update_magistrals(all_nodes)

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

            self.node_items[key] = items

        # === Обновляем выделение ===
        self.update_selection_graphics()

    def update_node_graphics(self, node, ntype):
        key = (node["id"], ntype)
        if key not in self.node_items:
            return
        items = self.node_items[key]
        x = node["xy"]["x"]
        y = node["xy"]["y"]
        
        if ntype == "legend":
            w = float(node.get("width", 100))
            h = float(node.get("height", 50))
            rect_item = next((i for i in items if isinstance(i, QGraphicsRectItem)), None)
            text_item = next((i for i in items if isinstance(i, QGraphicsTextItem)), None)
            if rect_item:
                rect_item.setRect(x, y, w, h)
            if text_item:
                text_rect = text_item.boundingRect()
                text_item.setPos(x + (w - text_rect.width()) / 2, y + (h - text_rect.height()) / 2)
        else:
            main_item = next((i for i in items if isinstance(i, QGraphicsPixmapItem) or isinstance(i, QGraphicsRectItem)), None)
            text_item = next((i for i in items if isinstance(i, QGraphicsTextItem)), None)
            overlay_item = next((i for i in items if isinstance(i, QGraphicsPixmapItem) and i != main_item), None)
            
            if isinstance(main_item, QGraphicsPixmapItem):
                w, h = main_item.pixmap().width(), main_item.pixmap().height()
                main_item.setPos(x - w/2, y - h/2)
                if overlay_item:
                    overlay_item.setPos(x - w/2, y - h/2)
            elif isinstance(main_item, QGraphicsRectItem):
                w, h = 15, 13  # fixed for no image
                main_item.setRect(x - 7.5, y - 6.5, w, h)
            
            if text_item:
                text_item.setPos(x - text_item.boundingRect().width()/2, y + h/2 + 15)

    def update_magistrals(self, all_nodes=None):
        # Remove old magistral items
        for item in self.magistral_items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)
        self.magistral_items = []

        if all_nodes is None:
            all_nodes = [
                *[{**s, "type": "switch", "x": s["xy"]["x"], "y": s["xy"]["y"]} for s in self.map_data.get("switches", [])],
                *[{**p, "type": "plan_switch", "x": p["xy"]["x"], "y": p["xy"]["y"]} for p in self.map_data.get("plan_switches", [])],
                *[{**u, "type": "user", "x": u["xy"]["x"], "y": u["xy"]["y"]} for u in self.map_data.get("users", [])],
                *[{**s, "type": "soap", "x": s["xy"]["x"], "y": s["xy"]["y"]} for s in self.map_data.get("soaps", [])],
                *[{**l, "type": "legend", "x": l["xy"]["x"], "y": l["xy"]["y"], "name": l["text"]} for l in self.map_data.get("legends", [])]
            ]

        for link in self.map_data.get("magistrals", []):
            source = next((n for n in all_nodes if n["id"] == link["startid"]), None)
            target = next((n for n in all_nodes if n["id"] == link["endid"]), None)
            if source and target:
                pen = QPen(QColor(link.get("color", "#000")), float(link.get("width", 1)))
                if link.get("style") == "psdot":
                    pen.setDashPattern([5, 5])
                line = self.scene.addLine(source["x"], source["y"], target["x"], target["y"], pen)
                self.magistral_items.append(line)

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
                        sq_rect = self.scene.addRect(px - sq_w/2, py - sq_h/2, sq_w, sq_h,
                            pen=QPen(QColor(link.get("color", "#000")), 1),
                            brush=QBrush(QColor("#008080")))
                        sq_rect.setZValue(0)
                        port_text.setPos(px - rect.width()/2, py - rect.height()/2)
                        port_text.setZValue(1)
                        self.magistral_items.append(sq_rect)
                        self.magistral_items.append(port_text)

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

            # Режим редактирования: начать перетаскивание, но для legend только если на периметре
            if self.is_edit_mode and result:
                node, ntype, key = result
                if ntype == "legend":
                    rect = self.get_node_rect(node, ntype)
                    if not self.is_on_perimeter(scene_pos, rect):
                        result = None  # Не начинать drag, если не на периметре
                if result:
                    self.dragged_node = node
                    self.dragged_type = ntype
                    self.drag_start_pos = scene_pos
                    # Добавляем выделение при старте перемещения
                    if (node, ntype, key) not in self.selected_nodes:
                        self.selected_nodes.append((node, ntype, key))
                    self.update_selection_graphics()
                    event.accept()
                    return

            # Групповое перетаскивание
            if self.is_edit_mode and result and any(n[0] is result[0] for n in self.selected_nodes):
                self.drag_group = True
                self.drag_start_pos = scene_pos
                self.group_drag_offset = [(scene_pos.x() - n[0]["xy"]["x"], scene_pos.y() - n[0]["y"]) for n in self.selected_nodes]
                self.update_selection_graphics()  # Показываем выделение
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
                node["xy"]["x"] = new_x
                node["xy"]["y"] = new_y
                self.update_node_graphics(node, ntype)
            self.update_magistrals()
            self.update_selection_graphics()
            event.accept()
            return

        # === Одиночное перетаскивание ===
        if self.dragged_node:
            self.dragged_node["xy"]["x"] = scene_pos.x()
            self.dragged_node["xy"]["y"] = scene_pos.y()
            self.update_node_graphics(self.dragged_node, self.dragged_type)
            self.update_magistrals()
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

        # === Наведение с задержкой 2 сек ===
        if not self.is_edit_mode:
            result = self.find_node_by_position(scene_pos)
            if result:
                node, ntype, _ = result
                if ntype in ("switch", "plan_switch"):
                    if self.current_hover_node != node:
                        self.current_hover_node = node
                        self.current_hover_type = ntype
                        self.hover_timer.start(2000)
                    return
            if self.current_hover_node:
                self.hover_timer.stop()
                self.current_hover_node = None
                self.current_hover_type = None

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())

            # === Группа ===
            if self.drag_group:
                self.drag_group = False
                self.save_map_to_file()
                self.show_status_saved()
                event.accept()
                return

            # === Один узел ===
            if self.dragged_node:
                self.dragged_node = None
                self.save_map_to_file()
                self.show_status_saved()
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

    # === Диалог при наведении ===
    def show_hover_dialog(self):
        if self.current_hover_node and self.current_hover_type == "switch":
            dialog = SwitchInfoDialog(self.current_hover_node, self)
            dialog.exec()
        elif self.current_hover_node and self.current_hover_type == "plan_switch":
            dialog = PlanSwitchInfoDialog(self.current_hover_node, self)
            dialog.exec()
        self.current_hover_node = None
        self.current_hover_type = None

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
                item_rect = self.get_node_rect(item, ntype)
                if rect.intersects(item_rect):
                    self.selected_nodes.append((item, ntype, key))
        self.update_selection_graphics()

    def update_selection_graphics(self):
        self.clear_selection_graphics()
        if not self.selected_nodes:
            return

        padding = 2

        for node, ntype, _ in self.selected_nodes:
            node_rect = self.get_node_rect(node, ntype)
            padded = node_rect.adjusted(-padding, -padding, padding, padding)

            pen = QPen(QColor("#FFC107"), 1, Qt.PenStyle.DashLine)
            pen.setDashPattern([2, 2])

            border = self.scene.addRect(padded, pen=pen)
            border.setZValue(999)
            self.selection_graphics.append(border)

    def clear_selection_graphics(self):
        for item in self.selection_graphics[:]:
            try:
                if item.scene() is not None:
                    item.scene().removeItem(item)
            except:
                pass
        self.selection_graphics.clear()

    def remove_from_selection(self, node, ntype, key):
        self.selected_nodes = [n for n in self.selected_nodes if n[0] is not node]
        self.update_selection_graphics()

    # === УТИЛИТЫ ===
    def is_on_perimeter(self, pos, rect, thickness=5):
        inner_rect = rect.adjusted(thickness, thickness, -thickness, -thickness)
        return rect.contains(pos) and not inner_rect.contains(pos)

    def find_node_by_position(self, pos):
        closest = None
        min_dist = float('inf')
        for items, ntype, key in [
            (self.map_data.get("switches", []), "switch", "switches"),
            (self.map_data.get("plan_switches", []), "plan_switch", "plan_switches"),
            (self.map_data.get("users", []), "user", "users"),
            (self.map_data.get("soaps", []), "soap", "soaps")
        ]:
            for item in items:
                item_rect = self.get_node_rect(item, ntype)
                if item_rect.contains(pos):
                    dist = math.hypot(pos.x() - item["xy"]["x"], pos.y() - item["xy"]["y"])
                    if dist < min_dist:
                        min_dist = dist
                        closest = (item, ntype, key)

        for item in self.map_data.get("legends", []):
            x = item["xy"]["x"]
            y = item["xy"]["y"]
            w = float(item.get("width", 100))
            h = float(item.get("height", 50))
            item_rect = QRectF(x, y, w, h)
            if self.is_on_perimeter(pos, item_rect):
                dist = 0  # Priority for perimeter
                if dist < min_dist:
                    min_dist = dist
                    closest = (item, "legend", "legends")

        return closest

    def get_node_rect(self, node, ntype):
        x = node["xy"]["x"]
        y = node["xy"]["y"]
        if ntype == "legend":
            w = float(node.get("width", 100))
            h = float(node.get("height", 50))
            return QRectF(x, y, w, h)
        else:
            key = (node["id"], ntype)
            items = self.node_items.get(key, [])
            pixmap_item = next((i for i in items if isinstance(i, QGraphicsPixmapItem)), None)
            if pixmap_item:
                w, h = pixmap_item.pixmap().width(), pixmap_item.pixmap().height()
            else:
                w, h = self.icon_sizes.get(ntype, (50, 50))
            return QRectF(x - w/2, y - h/2, w, h)

    def save_map_to_file(self):
        if hasattr(self.parent, "current_map_file") and self.parent.current_map_file:
            with open(self.parent.current_map_file, 'w', encoding='utf-8') as f:
                json.dump(self.map_data, f, ensure_ascii=False, indent=2)

    def show_status_saved(self):
        if hasattr(self.parent, "status_bar"):
            self.parent.status_bar.showMessage("Карта успешно сохранена", 3000)

    def trigger_parent_edit_button(self):
        QTimer.singleShot(0, self._toggle_edit_mode)

    def _toggle_edit_mode(self):
        if hasattr(self.parent, "edit_button"):
            self.parent.edit_button.click()
        else:
            self.is_edit_mode = not self.is_edit_mode
            if not self.is_edit_mode:
                self.show_status_saved()
            self.render_map()

    def trigger_parent_settings_button(self):
        QTimer.singleShot(0, self._open_settings)

    def _open_settings(self):
        if hasattr(self.parent, "settings_button"):
            self.parent.settings_button.click()

    def add_planed_switch(self, position):
        scene_pos = self.mapToScene(position)
        dialog = AddPlanedSwitch(self, scene_pos)
        dialog.exec()

    def add_node(self, node_type, position):
        scene_pos = self.mapToScene(position)
        print(f"Adding {node_type} at scene position ({scene_pos.x()}, {scene_pos.y()})")

    def edit_plan_switch(self, plan_switch):
        position = QPointF(plan_switch["xy"]["x"], plan_switch["xy"]["y"])
        dialog = AddPlanedSwitch(self, position, plan_switch)
        if dialog.exec():
            self.render_map()
            self.save_map_to_file()
            self.show_status_saved()

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
            self.show_status_saved()

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

    def get_next_id(self, key):
        """Возвращает следующий свободный числовой ID для списка `key`."""
        items = self.map_data.get(key, [])
        valid_ids = []
        for item in items:
            raw_id = item.get("id")
            if raw_id is None:
                continue
            try:
                valid_ids.append(int(raw_id))
            except (ValueError, TypeError):
                continue
        return max(valid_ids) + 1 if valid_ids else 1

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
        add_plan_switch_action.triggered.connect(lambda: self.add_planed_switch(position))
        add_user_action.triggered.connect(lambda: self.add_node("user", position))
        add_magistral_action.triggered.connect(lambda: self.add_node("magistral", position))
        add_soap_action.triggered.connect(lambda: self.add_node("soap", position))
        add_legend_action.triggered.connect(lambda: self.add_node("legend", position))

        map_settings_action = menu.addAction("Параметры карты")
        map_settings_action.setEnabled(self.is_edit_mode)
        map_settings_action.triggered.connect(self.trigger_parent_settings_button)

        menu.exec(self.mapToGlobal(position))

    def show_plan_switch_context_menu(self, position, node):
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

        edit_action.triggered.connect(lambda: self.edit_plan_switch(node))
        config_action.triggered.connect(lambda: self.show_message("Настройка не реализована"))
        delete_action.triggered.connect(lambda: self.delete_plan_switch(node))

        menu.exec(self.mapToGlobal(position))