# canvas.py — ПОЛНОСТЬЮ ИСПРАВЛЕНО: нет KeyError, легенды работают, Shift + клик, групповое перемещение
# Автор: Grok
# Обновлено: November 11, 2025, 16:40 CET
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

from widgets import SwitchInfoDialog, PlanSwitchInfoDialog, AddPlanedSwitch


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

        self.dragged_node = None
        self.dragged_type = None
        self.drag_start_pos = None
        self.drag_group = False
        self.group_drag_offset = []

        self.selection_rect = None
        self.selection_start = None
        self.selected_nodes = []
        self.selection_graphics = []

        self._panning = False
        self._last_pos = None
        self._context_menu_pos = None
        self._moved_during_rmb = False

        self.node_items = {}
        self.magistral_items = []

        self.icon_sizes = {
            "switch": (60, 60),
            "plan_switch": (60, 60),
            "user": (50, 50),
            "soap": (50, 50)
        }

        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.show_hover_dialog)
        self.current_hover_node = None
        self.current_hover_type = None

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.render_map()

    # === КООРДИНАТЫ — ЕДИНЫЙ ИСТОЧНИК: xy["x"], xy["y"] ===
    def get_node_xy(self, node, ntype):
        """Возвращает (x, y) — ВСЕГДА из xy"""
        return node["xy"]["x"], node["xy"]["y"]

    def set_node_xy(self, node, ntype, x, y):
        """Устанавливает xy — ВСЕГДА в xy"""
        node["xy"]["x"] = x
        node["xy"]["y"] = y

    # === ОТРИСОВКА ===
    def render_map(self):
        print("Rendering map...")
        self.scene.clear()
        self.magistral_items = []
        self.node_items.clear()
        self.selection_graphics.clear()
        self.scene.setBackgroundBrush(QBrush(QColor("#008080")))

        # === ЛЕГЕНДЫ ===
        for legend in self.map_data.get("legends", []):
            fill_color = "transparent" if legend.get("zalivka") == "0" else legend.get("zalivkacolor", "#fff")
            w = float(legend.get("width", 100))
            h = float(legend.get("height", 50))
            x, y = self.get_node_xy(legend, "legend")
            rect_item = self.scene.addRect(x, y, w, h,
                pen=QPen(QColor(legend.get("bordercolor", "#000")), float(legend.get("borderwidth", 2))),
                brush=QBrush(QColor(fill_color)))
            rect_item.setZValue(-1)

            text = self.scene.addText(legend.get("name") or legend.get("text") or "")
            text.setDefaultTextColor(QColor(legend.get("textcolor", "#000")))
            text_rect = text.boundingRect()
            text.setPos(x + (w - text_rect.width()) / 2, y + (h - text_rect.height()) / 2)
            font = text.font()
            font.setPixelSize(int(legend.get("textsize", 14)))
            font.setBold(True)
            text.setFont(font)
            text.setZValue(-1)
            key = (legend["id"], "legend")
            self.node_items[key] = [rect_item, text]

        # === МАГИСТРАЛИ ===
        self.update_magistrals()

        # === УЗЛЫ ===
        for node_list, node_type in [
            (self.map_data.get("switches", []), "switch"),
            (self.map_data.get("plan_switches", []), "plan_switch"),
            (self.map_data.get("users", []), "user"),
            (self.map_data.get("soaps", []), "soap")
        ]:
            for node in node_list:
                node_id = node["id"]
                key = (node_id, node_type)
                x, y = self.get_node_xy(node, node_type)
                items = []

                # Иконка
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

                w = h = 0
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

                if overlay_path and os.path.exists(overlay_path):
                    overlay = QPixmap(overlay_path)
                    overlay_item = self.scene.addPixmap(overlay)
                    overlay_item.setPos(x - w/2, y - h/2)
                    overlay_item.setZValue(3)
                    items.append(overlay_item)

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

        self.update_selection_graphics()

    def update_node_graphics(self, node, ntype):
        key = (node["id"], ntype)
        if key not in self.node_items:
            return
        items = self.node_items[key]
        x, y = self.get_node_xy(node, ntype)

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
                w, h = 15, 13
                main_item.setRect(x - 7.5, y - 6.5, w, h)

            if text_item:
                text_item.setPos(x - text_item.boundingRect().width()/2, y + h/2 + 15)

    def update_magistrals(self):
        for item in self.magistral_items:
            if item.scene() == self.scene:
                self.scene.removeItem(item)
        self.magistral_items = []

        nodes_by_id = {}
        for node_list, ntype in [
            (self.map_data.get("switches", []), "switch"),
            (self.map_data.get("plan_switches", []), "plan_switch"),
            (self.map_data.get("users", []), "user"),
            (self.map_data.get("soaps", []), "soap"),
            (self.map_data.get("legends", []), "legend")
        ]:
            for node in node_list:
                nodes_by_id[node["id"]] = (node, ntype)

        for link in self.map_data.get("magistrals", []):
            start_node, start_type = nodes_by_id.get(link["startid"], (None, None))
            end_node, end_type = nodes_by_id.get(link["endid"], (None, None))
            if not start_node or not end_node:
                continue

            sx, sy = self.get_node_xy(start_node, start_type)
            ex, ey = self.get_node_xy(end_node, end_type)

            pen = QPen(QColor(link.get("color", "#000")), float(link.get("width", 1)))
            if link.get("style") == "psdot":
                pen.setDashPattern([5, 5])
            line = self.scene.addLine(sx, sy, ex, ey, pen)
            self.magistral_items.append(line)

            # Порты
            for port, node, other, pkey, fkey, ckey in [
                (link.get("startport"), start_node, end_node, "startport", "startportfar", "startportcolor"),
                (link.get("endport"), end_node, start_node, "endport", "endportfar", "endportcolor")
            ]:
                if not port or port == "0":
                    continue
                dx = self.get_node_xy(other, nodes_by_id[link["endid"] if pkey == "startport" else link["startid"]][1])[0] - self.get_node_xy(node, nodes_by_id[link["startid"] if pkey == "startport" else link["endid"]][1])[0]
                dy = self.get_node_xy(other, ...)[1] - self.get_node_xy(node, ...)[1]
                length = math.hypot(dx, dy)
                dist = float(link.get(fkey, 10))
                if length > 0:
                    dx, dy = dx / length, dy / length
                    px = self.get_node_xy(node, ...)[0] + dx * dist
                    py = self.get_node_xy(node, ...)[1] + dy * dist
                else:
                    px, py = self.get_node_xy(node, ...)[0] + dist, self.get_node_xy(node, ...)[1]

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
                self.magistral_items.extend([sq_rect, port_text])

    # === МЫШЬ ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            result = self.find_node_by_position(scene_pos)

            # Shift + клик
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                if result:
                    node, ntype, key = result
                    tup = (node, ntype, key)
                    if tup in self.selected_nodes:
                        self.selected_nodes.remove(tup)
                    else:
                        self.selected_nodes.append(tup)
                    self.update_selection_graphics()
                    event.accept()
                    return
                event.accept()
                return

# === ОДИНОЧНОЕ ИЛИ ГРУППОВОЕ ПЕРЕМЕЩЕНИЕ ===
            if self.is_edit_mode:
                # 1. Проверяем, попал ли клик в любой из ВЫДЕЛЕННЫХ объектов
                if self.selected_nodes:
                    clicked_on_selected = any(
                        self.get_node_rect(n[0], n[1]).contains(scene_pos)
                        for n in self.selected_nodes
                    )
                    if clicked_on_selected:
                        # ← ГРУППОВОЕ ПЕРЕМЕЩЕНИЕ
                        self.drag_group = True
                        self.drag_start_pos = scene_pos
                        self.group_drag_offset = [
                            (scene_pos.x() - self.get_node_xy(n[0], n[1])[0],
                             scene_pos.y() - self.get_node_xy(n[0], n[1])[1])
                            for n in self.selected_nodes
                        ]
                        self.update_selection_graphics()
                        event.accept()
                        return

                # 2. Если НЕ в группе — проверяем одиночное
                if result:
                    node, ntype, key = result
                    # Легенды — только по периметру
                    if ntype == "legend" and not self.is_on_perimeter(scene_pos, self.get_node_rect(node, ntype)):
                        result = None
                    if result:
                        self.dragged_node = node
                        self.dragged_type = ntype
                        self.drag_start_pos = scene_pos
                        # Если не в группе — создаём новое выделение
                        if (node, ntype, key) not in self.selected_nodes:
                            self.selected_nodes = [(node, ntype, key)]
                        self.update_selection_graphics()
                        event.accept()
                        return

            # Рамка
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

        if self.drag_group:
            dx = scene_pos.x() - self.drag_start_pos.x()
            dy = scene_pos.y() - self.drag_start_pos.y()
            for (node, ntype, _), (ox, oy) in zip(self.selected_nodes, self.group_drag_offset):
                new_x = self.drag_start_pos.x() - ox + dx
                new_y = self.drag_start_pos.y() - oy + dy
                self.set_node_xy(node, ntype, new_x, new_y)
                self.update_node_graphics(node, ntype)
            self.update_magistrals()
            self.update_selection_graphics()
            event.accept()
            return

        if self.dragged_node:
            x, y = scene_pos.x(), scene_pos.y()
            self.set_node_xy(self.dragged_node, self.dragged_type, x, y)
            self.update_node_graphics(self.dragged_node, self.dragged_type)
            self.update_magistrals()
            self.update_selection_graphics()
            event.accept()
            return

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
            if self.drag_group:
                self.drag_group = False
                self.save_map_to_file()
                self.show_status_saved()
                event.accept()
                return
            if self.dragged_node:
                self.dragged_node = None
                self.save_map_to_file()
                self.show_status_saved()
                event.accept()
                return
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
                if rect.intersects(self.get_node_rect(item, ntype)):
                    self.selected_nodes.append((item, ntype, key))
        self.update_selection_graphics()

    def update_selection_graphics(self):
        self.clear_selection_graphics()
        if not self.selected_nodes:
            return
        padding = 2
        pen = QPen(QColor("#FFC107"), 1, Qt.PenStyle.DashLine)
        pen.setDashPattern([2, 2])  # ← Пунктир здесь
        for node, ntype, _ in self.selected_nodes:
            r = self.get_node_rect(node, ntype).adjusted(-padding, -padding, padding, padding)
            border = self.scene.addRect(r, pen=pen)
            border.setZValue(999)
            self.selection_graphics.append(border)

    def clear_selection_graphics(self):
        for item in self.selection_graphics[:]:
            try:
                if item.scene():
                    self.scene.removeItem(item)
            except:
                pass
        self.selection_graphics.clear()

    # === УТИЛИТЫ ===
    def is_on_perimeter(self, pos, rect, thickness=6):
        inner = rect.adjusted(thickness, thickness, -thickness, -thickness)
        return rect.contains(pos) and not inner.contains(pos)

    def find_node_by_position(self, pos):
        closest = None
        min_dist = float('inf')

        # Обычные узлы
        for items, ntype, key in [
            (self.map_data.get("switches", []), "switch", "switches"),
            (self.map_data.get("plan_switches", []), "plan_switch", "plan_switches"),
            (self.map_data.get("users", []), "user", "users"),
            (self.map_data.get("soaps", []), "soap", "soaps")
        ]:
            for item in items:
                rect = self.get_node_rect(item, ntype)
                if rect.contains(pos):
                    x, y = self.get_node_xy(item, ntype)
                    dist = math.hypot(pos.x() - x, pos.y() - y)
                    if dist < min_dist:
                        min_dist = dist
                        closest = (item, ntype, key)

        # Легенды — только по периметру
        for item in self.map_data.get("legends", []):
            rect = self.get_node_rect(item, "legend")
            if self.is_on_perimeter(pos, rect):
                x, y = self.get_node_xy(item, "legend")
                dist = math.hypot(pos.x() - x, pos.y() - y)
                if dist < min_dist:
                    min_dist = dist
                    closest = (item, "legend", "legends")

        return closest

    def get_node_rect(self, node, ntype):
        x, y = self.get_node_xy(node, ntype)
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

    # === СОХРАНЕНИЕ ===
    def save_map_to_file(self):
        if hasattr(self.parent, "current_map_file") and self.parent.current_map_file:
            with open(self.parent.current_map_file, 'w', encoding='utf-8') as f:
                json.dump(self.map_data, f, ensure_ascii=False, indent=2)

    def show_status_saved(self):
        if hasattr(self.parent, "status_bar"):
            self.parent.status_bar.showMessage("Карта успешно сохранена", 3000)

    # === КНОПКИ ===
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

    # === ДИАЛОГИ ===
    def add_planed_switch(self, position):
        scene_pos = self.mapToScene(position)
        dialog = AddPlanedSwitch(self, scene_pos)
        dialog.exec()

    def add_node(self, node_type, position):
        scene_pos = self.mapToScene(position)
        print(f"Adding {node_type} at ({scene_pos.x()}, {scene_pos.y()})")

    def edit_plan_switch(self, plan_switch):
        dialog = AddPlanedSwitch(self, QPointF(plan_switch["xy"]["x"], plan_switch["xy"]["y"]), plan_switch)
        if dialog.exec():
            self.render_map()
            self.save_map_to_file()
            self.show_status_saved()

    def delete_plan_switch(self, plan_switch):
        msg = self.styled_messagebox("Удаление", f"Удалить '<b>{plan_switch['name']}</b>'?", QMessageBox.Icon.Question)
        yes = msg.addButton("Да", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Нет", QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(yes)
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
            QPushButton { background-color: #333; color: #FFC107; border: 1px solid #444; border-radius: 4px; padding: 5px; min-width: 80px; }
            QPushButton:hover { background-color: #FFC107; color: #333; }
        """)
        return msg

    def get_next_id(self, key):
        items = self.map_data.get(key, [])
        ids = [int(i["id"]) for i in items if i.get("id") and str(i["id"]).isdigit()]
        return max(ids) + 1 if ids else 1

    # === КОНТЕКСТНОЕ МЕНЮ ===
    def show_context_menu(self, position):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }")
        toggle = menu.addAction("Выключить редактирование" if self.is_edit_mode else "Включить редактирование")
        toggle.triggered.connect(self.trigger_parent_edit_button)

        add_menu = menu.addMenu("Добавить")
        add_menu.setEnabled(self.is_edit_mode)
        for text, typ in [("Упр. свитч", "switch"), ("Планируемый свитч", "plan_switch"), ("Клиент", "user"), ("Мыльница", "soap"), ("Таблица", "legend")]:
            action = add_menu.addAction(text)
            action.triggered.connect(lambda _, t=typ: self.add_node(t, position) if t != "plan_switch" else self.add_planed_switch(position))

        settings = menu.addAction("Параметры карты")
        settings.setEnabled(self.is_edit_mode)
        settings.triggered.connect(self.trigger_parent_settings_button)

        menu.exec(self.mapToGlobal(position))

    def show_plan_switch_context_menu(self, position, node):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }")
        menu.addAction("Редактировать").triggered.connect(lambda: self.edit_plan_switch(node))
        menu.addAction("Настроить").triggered.connect(lambda: self.show_message("Не реализовано"))
        menu.addAction("Удалить").triggered.connect(lambda: self.delete_plan_switch(node))
        menu.exec(self.mapToGlobal(position))

    def show_hover_dialog(self):
        if self.current_hover_node and self.current_hover_type == "switch":
            SwitchInfoDialog(self.current_hover_node, self).exec()
        elif self.current_hover_node and self.current_hover_type == "plan_switch":
            PlanSwitchInfoDialog(self.current_hover_node, self).exec()
        self.current_hover_node = None
        self.current_hover_type = None