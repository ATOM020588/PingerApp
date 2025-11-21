# canvas.py — ИСПРАВЛЕНО: выделение и перемещение точек магистралей + overlay copy.png
# Автор: Grok / E1 / AI Assistant
# Обновлено: January 2025

import sys
import json
import os
import math
import webbrowser
import requests
from PyQt6.QtWidgets import (
    QGraphicsPixmapItem, QMessageBox, QGraphicsTextItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsItem, QGraphicsEllipseItem,
    QGraphicsView, QGraphicsScene, QMenu, QDialog, QLineEdit,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QTextEdit
)
from PyQt6.QtGui import QAction, QColor, QBrush, QPen, QPainter, QPixmap
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF

from widgets import SwitchInfoDialog, PlanSwitchInfoDialog, AddPlanedSwitch, SwitchEditDialog




# НОВЫЙ КЛАСС: Перемещаемая желтая точка магистрали
class MagistralPoint(QGraphicsEllipseItem):
    """Желтая точка магистрали с поддержкой перемещения"""
    def __init__(self, x, y, link, idx, canvas):
        super().__init__(-2, -2, 4, 4)  # Радиус 2px
        self.canvas = canvas
        self.link = link
        self.idx = idx
        
        self.setPen(QPen(QColor("#FFFF00"), 2))
        self.setBrush(QBrush(QColor("#FFFF00")))
        self.setPos(x, y)
        self.setZValue(999)
        
        # Устанавливаем флаги
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        
        # Обычный курсор
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Обновляем координаты в данных
            x, y = value.x(), value.y()
            self.canvas.update_magistral_point_data(self.link["id"], self.idx, x, y)
        return super().itemChange(change, value)
    
    def mouseReleaseEvent(self, event):
        """При отпускании мыши сохраняем карту"""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.canvas.save_map_to_file()
            self.canvas.show_status_saved()


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
        
        self.magistral_points = {}

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

        # Флаг загрузки данных
        self.is_data_loaded = False
        self.loading_text_item = None

    # === КООРДИНАТЫ — ЕДИНЫЙ ИСТОЧНИК: xy["x"], xy["y"] ===
    def get_node_xy(self, node, ntype):
        """Возвращает (x, y) — ВСЕГДА из xy
        
        ИСПРАВЛЕНИЕ: Обработка объектов MagistralPoint
        """
        if ntype == "magistral_point":
            # Для точек магистрали возвращаем позицию из QGraphicsItem
            pos = node.pos()
            return pos.x(), pos.y()
        # Для обычных узлов возвращаем из словаря
        return node["xy"]["x"], node["xy"]["y"]

    def set_node_xy(self, node, ntype, x, y):
        """Устанавливает xy — ВСЕГДА в xy"""
        node["xy"]["x"] = x
        node["xy"]["y"] = y
        
    def calculate_text_position(self, x, y, w, h, tw, th, align="5"):
        """Поддержка textalign 1-9 для легенд"""
        align = str(align)
        tx = x + (w - tw) / 2
        ty = y + (h - th) / 2
        if align == "1":   tx, ty = x + 4, y + 4
        elif align == "2": tx, ty = x + (w - tw)/2, y + 4
        elif align == "3": tx, ty = x + w - tw - 4, y + 4
        elif align == "4": tx, ty = x + 4, y + (h - th)/2
        elif align == "6": tx, ty = x + w - tw - 4, y + (h - th)/2
        elif align == "7": tx, ty = x + 4, y + h - th - 4
        elif align == "8": tx, ty = x + (w - tw)/2, y + h - th - 4
        elif align == "9": tx, ty = x + w - tw - 4, y + h - th - 4
        return tx, ty

    # === НОВЫЙ МЕТОД: Установка данных карты ===
    def set_map_data(self, map_data):
        """Устанавливает данные карты и запускает рендеринг"""
        if map_data and "map" in map_data:
            self.map_data = map_data
            self.is_data_loaded = True
            # Обновляем размеры сцены
            self.setSceneRect(0, 0, 
                int(self.map_data["map"].get("width", "1200")), 
                int(self.map_data["map"].get("height", "800")))
            # Рендерим карту
            self.render_map()
        else:
            print("Warning: Invalid map_data provided")
            self.show_loading_indicator()

    # === ОТРИСОВКА ===
    def render_map(self):
        """Проверка наличия данных перед рендерингом"""
        print(f"Rendering map... Data loaded: {bool(self.map_data and 'map' in self.map_data)}")

        # Проверяем, есть ли данные карты
        if not self.map_data or "map" not in self.map_data:
            self.show_loading_indicator()
            return

        # Данные есть - убираем индикатор загрузки
        self.hide_loading_indicator()
        self.is_data_loaded = True

        self.scene.clear()
        self.magistral_items = []
        self.magistral_points.clear()  # Очищаем словарь точек при полной перерисовке
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
            font = text.font()
            font.setPixelSize(int(legend.get("textsize", 14)))
            font.setBold(True)
            text.setFont(font)
            text_rect = text.boundingRect()
            # Вычисляем позицию текста с учетом textalign
            text_x, text_y = self.calculate_text_position(
                x, y, w, h, 
                text_rect.width(), text_rect.height(),
                legend.get("textalign", "5")
            )
            text.setPos(text_x, text_y)
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

                # ——— ОПРЕДЕЛЕНИЕ ИКОНКИ И ОВЕРЛЕЯ ———
                image_path = None
                overlay_path = None

                if node_type == "switch":
                    image_path = "canvas/Router.png"
                    overlay_path = None

                    # 1. ПИНГ — САМЫЙ ВЫСОКИЙ ПРИОРИТЕТ
                    if str(node.get("pingok", "")).lower() in ("false", "0", "", "none"):
                        image_path = "canvas/Router_off.png"
                        overlay_path = "canvas/other/ping_failed.png"

                    # 2. Не установлен
                    elif node.get("notinstalled") == "-1":
                        image_path = "canvas/Router_off.png"
                        overlay_path = "canvas/other/not_install.png"

                    # 3. Установлен, но не настроен
                    elif node.get("notsettings") == "-1":
                        image_path = "canvas/Router.png"
                        overlay_path = "canvas/other/not_settings.png"
                    
                    # 4. НОВОЕ: Копия (copyid установлен и не "none")
                    elif node.get("copyid") and node.get("copyid") not in ["none", ""]:
                        # Если нет других overlay, показываем copy.png
                        if not overlay_path:
                            overlay_path = "canvas/other/copy.png"

                elif node_type == "plan_switch":
                    image_path = "canvas/Router_plan.png"

                elif node_type == "user":
                    image_path = "canvas/Computer.png"

                elif node_type == "soap":
                    image_path = "canvas/Switch.png"

                # ——— РИСОВАНИЕ ОСНОВНОЙ ИКОНКИ ———
                w = h = 0
                if image_path and os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    pixmap_item = self.scene.addPixmap(pixmap)
                    w, h = pixmap.width(), pixmap.height()
                    pixmap_item.setPos(x - w/2, y - h/2)
                    pixmap_item.setZValue(2)
                    items.append(pixmap_item)
                else:
                    # Запасной вариант
                    color = {
                        "switch": "#00aa00", "plan_switch": "#888888",
                        "user": "#0088ff", "soap": "#ff8800"
                    }.get(node_type, "#555555")
                    rect_item = self.scene.addRect(x-25, y-25, 50, 50,
                        brush=QBrush(QColor(color)), pen=QPen(QColor("#000")))
                    rect_item.setZValue(2)
                    items.append(rect_item)
                    w, h = 50, 50

                # ——— ОВЕРЛЕЙ (если есть) ———
                if overlay_path and os.path.exists(overlay_path):
                    overlay = QPixmap(overlay_path)
                    overlay_item = self.scene.addPixmap(overlay)
                    overlay_item.setPos(x - w/2, y - h/2)
                    overlay_item.setZValue(3)
                    items.append(overlay_item)
                # ——— ИНДИКАТОР MAYAKUP (только для switch) ———
                if node_type == "switch" and "mayakup" in node:
                    mayakup_value = node.get("mayakup")
                    # Определяем цвет: зеленый если true, красный если false
                    if mayakup_value is True:
                        indicator_color = QColor("#00ff00")  # Зеленый
                    elif mayakup_value is False:
                        indicator_color = QColor("#ff0000")  # Красный
                    else:
                        indicator_color = None
                    
                    # Рисуем круг только если цвет определен
                    if indicator_color:
                        # Радиус 5px, диаметр 10px
                        radius = 5
                        # Позиция: правый верхний угол иконки
                        circle_x = x
                        circle_y = y
                        
                        # Создаем круг
                        circle_item = self.scene.addEllipse(
                            circle_x - radius, 
                            circle_y - radius, 
                            radius * 2, 
                            radius * 2,
                            pen=QPen(indicator_color, 1),
                            brush=QBrush(indicator_color)
                        )
                        circle_item.setZValue(5)  # Поверх всего
                        items.append(circle_item)

                # ——— ПОДПИСЬ ———
                text = node.get("name") or node.get("text") or ""
                if not text:
                    text = {"switch": "Свитч", "plan_switch": "План", "user": "Клиент", "soap": "Мыльница"}.get(node_type, node_type)
                text_item = self.scene.addText(text)
                text_item.setDefaultTextColor(QColor("#dbdbdb"))
                font = text_item.font()
                font.setPixelSize(12)
                font.setBold(True)
                text_item.setFont(font)
                text_item.setPos(x - text_item.boundingRect().width()/2, y + h/2 + 5)
                text_item.setZValue(4)
                items.append(text_item)

                self.node_items[key] = items

        self.update_selection_graphics()

    def show_loading_indicator(self):
        """Показывает индикатор загрузки"""
        if not self.loading_text_item:
            self.scene.clear()
            self.scene.setBackgroundBrush(QBrush(QColor("#008080")))

            self.loading_text_item = self.scene.addText("Загрузка данных карты...")
            self.loading_text_item.setDefaultTextColor(QColor("#FFC107"))
            font = self.loading_text_item.font()
            font.setPixelSize(24)
            font.setBold(True)
            self.loading_text_item.setFont(font)

            rect = self.sceneRect()
            text_rect = self.loading_text_item.boundingRect()
            self.loading_text_item.setPos(
                rect.center().x() - text_rect.width() / 2,
                rect.center().y() - text_rect.height() / 2
            )
            self.loading_text_item.setZValue(1000)

    def hide_loading_indicator(self):
        """Убирает индикатор загрузки"""
        if self.loading_text_item:
            self.scene.removeItem(self.loading_text_item)
            self.loading_text_item = None

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
            # ИСПРАВЛЕНИЕ: Находим индикатор MAYAKUP (круг)
            mayakup_circle = next((i for i in items if isinstance(i, QGraphicsEllipseItem)), None)

            if isinstance(main_item, QGraphicsPixmapItem):
                w, h = main_item.pixmap().width(), main_item.pixmap().height()
                main_item.setPos(x - w/2, y - h/2)
                if overlay_item:
                    overlay_item.setPos(x - w/2, y - h/2)
            elif isinstance(main_item, QGraphicsRectItem):
                w, h = 15, 13
                main_item.setRect(x - 7.5, y - 6.5, w, h)

            # ИСПРАВЛЕНИЕ: Обновляем позицию индикатора MAYAKUP
            if mayakup_circle:
                radius = 5
                mayakup_circle.setRect(x - radius, y - radius, radius * 2, radius * 2)

            if text_item:
                text_item.setPos(x - text_item.boundingRect().width()/2, y + h/2 + 15)

    def update_magistral_point_data(self, link_id, idx, x, y):
        """Обновляет координаты точки магистрали в данных"""
        for link in self.map_data.get("magistrals", []):
            if link["id"] == link_id:
                import re
                pts = []
                if link.get("nodes"):
                    pts = [(float(a), float(b)) for a, b in re.findall(r'([+-]?\d+(?:\.\d+)?)\s*;\s*([+-]?\d+(?:\.\d+)?)', str(link["nodes"]))]
                
                while len(pts) < idx:
                    pts.append((0.0, 0.0))
                
                pts[idx - 1] = (x, y)
                link["nodes"] = "".join(f"[{x:.1f};{y:.1f}]" for x, y in pts)
                break
        
        # Перерисовываем магистрали без рекурсии
        self.refresh_magistrals_only()

    def refresh_magistrals_only(self):
        """Обновляет только линии магистралей без пересоздания точек"""
        # Удаляем линии, прямоугольники и текстовые элементы, но НЕ точки (MagistralPoint)
        for item in self.magistral_items[:]:
            try:
                if not isinstance(item, MagistralPoint) and item.scene():
                    self.scene.removeItem(item)
            except (RuntimeError, AttributeError):
                # Объект уже удалён
                pass
        
        # Фильтруем список, сохраняя только точки
        self.magistral_items = [item for item in self.magistral_items if isinstance(item, MagistralPoint)]
        
        # Перерисовываем линии
        import re
        nodes_by_id = {}
        for lst, typ in [
            (self.map_data.get("switches", []), "switch"),
            (self.map_data.get("plan_switches", []), "plan_switch"),
            (self.map_data.get("users", []), "user"),
            (self.map_data.get("soaps", []), "soap"),
            (self.map_data.get("legends", []), "legend")
        ]:
            for node in lst:
                nodes_by_id[node["id"]] = (node, typ)

        def parse_nodes(s):
            if not s: return []
            return [(float(a), float(b)) for a, b in re.findall(r'([+-]?\d+(?:\.\d+)?)\s*;\s*([+-]?\d+(?:\.\d+)?)', str(s))]

        for link in self.map_data.get("magistrals", []):
            start = nodes_by_id.get(link.get("startid"))
            end = nodes_by_id.get(link.get("endid"))
            if not start or not end:
                continue

            sx, sy = self.get_node_xy(*start)
            ex, ey = self.get_node_xy(*end)
            intermediate = parse_nodes(link.get("nodes", ""))
            points = [(sx, sy)] + intermediate + [(ex, ey)]

            pen = QPen(QColor(link.get("color", "#000000")), float(link.get("width", 1)))
            if link.get("style") == "psdot":
                pen.setDashPattern([5, 5])

            for i in range(len(points) - 1):
                line = self.scene.addLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1], pen)
                line.setZValue(0)
                self.magistral_items.append(line)
            
            # НОВОЕ: Отображение номеров портов на магистралях
            self.draw_magistral_port_labels(link, points)

    def update_magistrals(self):
        # Очистка старого
        for item in self.magistral_items[:]:
            try:
                if item.scene():
                    self.scene.removeItem(item)
            except RuntimeError:
                # Объект уже удалён
                pass
        self.magistral_items.clear()

        # Безопасная очистка точек
        for key, dot in list(self.magistral_points.items()):
            try:
                if dot and dot.scene():
                    self.scene.removeItem(dot)
            except (RuntimeError, AttributeError):
                # Объект уже удалён
                pass
        
        if not self.is_edit_mode:
            self.magistral_points.clear()

        import re

        nodes_by_id = {}
        for lst, typ in [
            (self.map_data.get("switches", []), "switch"),
            (self.map_data.get("plan_switches", []), "plan_switch"),
            (self.map_data.get("users", []), "user"),
            (self.map_data.get("soaps", []), "soap"),
            (self.map_data.get("legends", []), "legend")
        ]:
            for node in lst:
                nodes_by_id[node["id"]] = (node, typ)

        def parse_nodes(s):
            if not s: return []
            return [(float(a), float(b)) for a, b in re.findall(r'([+-]?\d+(?:\.\d+)?)\s*;\s*([+-]?\d+(?:\.\d+)?)', str(s))]

        for link in self.map_data.get("magistrals", []):
            start = nodes_by_id.get(link.get("startid"))
            end = nodes_by_id.get(link.get("endid"))
            if not start or not end:
                continue

            sx, sy = self.get_node_xy(*start)
            ex, ey = self.get_node_xy(*end)
            intermediate = parse_nodes(link.get("nodes", ""))
            points = [(sx, sy)] + intermediate + [(ex, ey)]

            # Линии
            pen = QPen(QColor(link.get("color", "#000000")), float(link.get("width", 1)))
            if link.get("style") == "psdot":
                pen.setDashPattern([5, 5])

            for i in range(len(points) - 1):
                line = self.scene.addLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1], pen)
                line.setZValue(0)
                self.magistral_items.append(line)

            # НОВОЕ: Отображение номеров портов на магистралях
            self.draw_magistral_port_labels(link, points)

            # ЖЕЛТЫЕ ТОЧКИ — ИСПРАВЛЕНО: используем новый класс MagistralPoint
            if self.is_edit_mode and len(points) > 2:
                for idx in range(1, len(points) - 1):
                    px, py = points[idx]
                    
                    # Создаём точку с использованием нового класса
                    dot = MagistralPoint(px, py, link, idx, self)
                    
                    # Добавляем в сцену
                    self.scene.addItem(dot)
                    
                    # Сохраняем
                    self.magistral_points[(link["id"], idx)] = dot
                    self.magistral_items.append(dot)
    
    def draw_magistral_port_labels(self, link, points):
        """Отрисовка подписей портов на магистралях"""
        if len(points) < 2:
            return
        
        # Получаем данные портов
        start_port = link.get("startport", "")
        end_port = link.get("endport", "")
        
        # ИСПРАВЛЕНИЕ 1: Фильтрация портов с номером 0
        # Преобразуем в строку и проверяем значение
        if str(start_port).strip() == "0":
            start_port = ""
        if str(end_port).strip() == "0":
            end_port = ""
        
        # Если нет данных о портах, ничего не рисуем
        if not start_port and not end_port:
            return
        
        # ИСПРАВЛЕНИЕ 2: Используем цвет порта из startportcolor/endportcolor
        start_color = link.get("startportcolor", "#FFC107")
        end_color = link.get("endportcolor", "#FFC107")
        
        start_far = float(link.get("startportfar", 10))
        end_far = float(link.get("endportfar", 10))
        
        # Рисуем подпись начального порта
        if start_port:
            self.draw_port_label(
                start_port, 
                points[0], 
                points[1], 
                start_color,  # Цвет из startportcolor
                start_far, 
                is_start=True
            )
        
        # Рисуем подпись конечного порта
        if end_port:
            self.draw_port_label(
                end_port, 
                points[-1], 
                points[-2], 
                end_color,  # Цвет из endportcolor
                end_far, 
                is_start=False
            )
    
    def draw_port_label(self, port_text, pos, neighbor_pos, color, distance, is_start=True):
        """Рисует подпись порта с прямоугольником"""
        # ИСПРАВЛЕНИЕ: Вычисляем направление ОТ узла К соседней точке (вдоль магистрали)
        dx = neighbor_pos[0] - pos[0]
        dy = neighbor_pos[1] - pos[1]
        length = math.sqrt(dx*dx + dy*dy)
        
        if length == 0:
            return
        
        # Нормализуем направление
        dx /= length
        dy /= length
        
        # Позиционируем подпись ВДОЛЬ магистрали на расстоянии distance от узла
        # Двигаемся от узла в сторону соседней точки (вдоль линии магистрали)
        text_x = pos[0] + dx * distance
        text_y = pos[1] + dy * distance
        
        # Создаем текст
        text_item = self.scene.addText(str(port_text))
        text_item.setDefaultTextColor(QColor(color))
        font = text_item.font()
        # ИСПРАВЛЕНИЕ 4: Увеличиваем шрифт с 10 до 11
        font.setPixelSize(11)
        font.setBold(True)
        text_item.setFont(font)
        
        # Получаем размеры текста
        text_rect = text_item.boundingRect()
        text_width = text_rect.width()
        text_height = text_rect.height()
        
        # ИСПРАВЛЕНИЕ: Уменьшаем отступы квадрата от текста
        padding_horizontal = 1
        padding_vertical = 0
        
        rect_width = text_width + 2 * padding_horizontal
        rect_height = text_height + 2 * padding_vertical
        
        # Центрируем прямоугольник относительно text_x, text_y
        rect_x = text_x - rect_width / 2
        rect_y = text_y - rect_height / 2
        
        # ИСПРАВЛЕНИЕ 2: Рисуем рамку цветом порта (startportcolor/endportcolor)
        rect_item = self.scene.addRect(
            rect_x, rect_y, rect_width, rect_height,
            pen=QPen(QColor(color), 1),
            brush=QBrush(QColor("#008080"))
        )
        rect_item.setZValue(10)  # Поверх магистрали
        
        # Позиционируем текст с учетом отступов
        text_item.setPos(rect_x + padding_horizontal, rect_y + padding_vertical)
        text_item.setZValue(11)  # Поверх прямоугольника
        
        # Добавляем в список элементов магистрали
        self.magistral_items.append(rect_item)
        self.magistral_items.append(text_item)

    # === МЫШЬ ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            
            # ИСПРАВЛЕНИЕ: Проверяем, не кликнули ли на желтую точку магистрали
            item_at_pos = self.scene.itemAt(scene_pos, self.transform())
            if isinstance(item_at_pos, MagistralPoint):
                # Если это точка магистрали в режиме редактирования, пропускаем обработку
                # Позволяем QGraphicsItem обработать событие
                super().mousePressEvent(event)
                return
            
            result = self.find_node_by_position(scene_pos)

            # Shift + клик — добавление/снятие
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                if result:
                    node, ntype, key = result
                    node_rect = self.get_node_rect(node, ntype)
                    if node_rect.contains(scene_pos):
                        tup = (node, ntype, key)
                        if tup in self.selected_nodes:
                            self.selected_nodes.remove(tup)
                        else:
                            self.selected_nodes.append(tup)
                        self.update_selection_graphics()
                    return
                return

            # === ОДИНОЧНОЕ ИЛИ ГРУППОВОЕ ПЕРЕМЕЩЕНИЕ ===
            if self.is_edit_mode:
                # 1. Групповое — клик по любому объекту в группе
                if self.selected_nodes:
                    clicked_on_selected = any(
                        self.get_node_rect(n[0], n[1]).contains(scene_pos)
                        for n in self.selected_nodes
                    )
                    if clicked_on_selected:
                        self.drag_group = True
                        self.drag_start_pos = scene_pos
                        # ИСПРАВЛЕНИЕ: Учитываем точки магистралей при расчете смещений
                        self.group_drag_offset = []
                        for node, ntype, key_data in self.selected_nodes:
                            if ntype == "magistral_point":
                                # Для точки магистрали берем её текущую позицию
                                pos = node.pos()
                                self.group_drag_offset.append(
                                    (scene_pos.x() - pos.x(), scene_pos.y() - pos.y())
                                )
                            else:
                                # Для обычных узлов
                                x, y = self.get_node_xy(node, ntype)
                                self.group_drag_offset.append(
                                    (scene_pos.x() - x, scene_pos.y() - y)
                                )
                        self.update_selection_graphics()
                        return

                # 2. Одиночное — только если весь объект в клике
                if result:
                    node, ntype, key = result
                    node_rect = self.get_node_rect(node, ntype)
                    if node_rect.contains(scene_pos):
                        if ntype == "legend" and not self.is_on_perimeter(scene_pos, node_rect):
                            pass
                        else:
                            self.dragged_node = node
                            self.dragged_type = ntype
                            self.drag_start_pos = scene_pos
                            if (node, ntype, key) not in self.selected_nodes:
                                self.selected_nodes = [(node, ntype, key)]
                            self.update_selection_graphics()
                            return

            # Рамка — только в пустоту
            if not result:
                self.selection_start = scene_pos
                self.selected_nodes = []
                self.clear_selection_graphics()
                return

        # === ПКМ паннинг ===
        elif event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._last_pos = event.position().toPoint()
            self._context_menu_pos = event.position().toPoint()
            self._moved_during_rmb = False
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())

        if self.drag_group:
            dx = scene_pos.x() - self.drag_start_pos.x()
            dy = scene_pos.y() - self.drag_start_pos.y()
            for (node, ntype, key_data), (ox, oy) in zip(self.selected_nodes, self.group_drag_offset):
                new_x = self.drag_start_pos.x() - ox + dx
                new_y = self.drag_start_pos.y() - oy + dy
                # ИСПРАВЛЕНИЕ: Обрабатываем точки магистралей отдельно
                if ntype == "magistral_point":
                    # Для точки магистрали устанавливаем позицию напрямую
                    node.setPos(new_x, new_y)
                    # Обновление данных произойдет через itemChange
                else:
                    # Обычные узлы
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
                    elif ntype in ["switch", "user", "soap"]:
                        self.show_device_context_menu(self._context_menu_pos, node, ntype)
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
                item_rect = self.get_node_rect(item, ntype)
                if rect.contains(item_rect):
                    self.selected_nodes.append((item, ntype, key))
        
        # ИСПРАВЛЕНИЕ: Добавляем точки магистралей в выделение
        if self.is_edit_mode:
            for (link_id, idx), point in self.magistral_points.items():
                if point and point.scene():
                    point_pos = point.pos()
                    point_rect = QRectF(point_pos.x() - 5, point_pos.y() - 5, 10, 10)
                    if rect.intersects(point_rect):
                        # Добавляем точку как особый тип "magistral_point"
                        self.selected_nodes.append((point, "magistral_point", (link_id, idx)))
        
        self.update_selection_graphics()

    def update_selection_graphics(self):
        self.clear_selection_graphics()
        if not self.selected_nodes:
            return
        padding = 2
        pen = QPen(QColor("#FFC107"), 1, Qt.PenStyle.DashLine)
        pen.setDashPattern([2, 2])
        for node, ntype, key_data in self.selected_nodes:
            # ИСПРАВЛЕНИЕ: Обрабатываем точки магистралей отдельно
            if ntype == "magistral_point":
                # Рисуем круг вокруг точки магистрали
                point_pos = node.pos()
                circle_border = self.scene.addEllipse(
                    point_pos.x() - 6, point_pos.y() - 6, 12, 12,
                    pen=pen
                )
                circle_border.setZValue(1000)
                self.selection_graphics.append(circle_border)
            else:
                # Обычные узлы
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
        """Возвращает прямоугольник узла
        
        ИСПРАВЛЕНИЕ: Обработка объектов MagistralPoint
        """
        if ntype == "magistral_point":
            # Для точек магистрали возвращаем небольшой прямоугольник вокруг точки
            pos = node.pos()
            return QRectF(pos.x() - 5, pos.y() - 5, 10, 10)
        
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
        if hasattr(self.parent, "save_map"):
            self.parent.save_map()

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
        menu.setStyleSheet("""
        QMenu { background-color: #333; color: #FFC107; border: 1px solid #444; border-radius: 4px; padding: 4px; }
        QMenu::item { padding: 6px 20px; border-radius: 3px; }
        QMenu::item:selected { background-color: #555; }
        QMenu::item:disabled { color: #666; background-color: #333; }
    """)
        toggle = menu.addAction("Выключить редактирование" if self.is_edit_mode else "Включить редактирование")
        toggle.triggered.connect(self.trigger_parent_edit_button)

        add_menu = menu.addMenu("Добавить")
        add_menu.setEnabled(self.is_edit_mode)
        for text, typ in [("Упр. свитч", "switch"), ("Планируемый свитч", "plan_switch"), ("Клиент", "user"), ("Мыльница", "soap"), ("Таблица", "legend")]:
            action = add_menu.addAction(text)
            action.setEnabled(self.is_edit_mode)
            action.triggered.connect(lambda _, t=typ: self.add_node(t, position) if t != "plan_switch" else self.add_planed_switch(position))

        settings = menu.addAction("Параметры карты")
        settings.setEnabled(self.is_edit_mode)
        settings.triggered.connect(self.trigger_parent_settings_button)

        menu.exec(self.mapToGlobal(position))

    def show_plan_switch_context_menu(self, position, node):
        """Контекстное меню для планируемого свитча"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: #FFC107; border: 1px solid #444; border-radius: 4px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 3px; }
            QMenu::item:selected { background-color: #555; }
            QMenu::item:disabled { color: #666; background-color: #333; }
        """)
        
        edit_action = menu.addAction("Редактировать")
        edit_action.triggered.connect(lambda: self.edit_plan_switch(node))
        edit_action.setEnabled(self.is_edit_mode)
        
        config_action = menu.addAction("Настроить")
        config_action.triggered.connect(lambda: self.show_message("Не реализовано"))
        config_action.setEnabled(self.is_edit_mode)
        
        delete_action = menu.addAction("Удалить")
        delete_action.triggered.connect(lambda: self.delete_plan_switch(node))
        delete_action.setEnabled(self.is_edit_mode)
        
        menu.exec(self.mapToGlobal(position))

    def show_device_context_menu(self, position, node, ntype):
        """Контекстное меню для оборудования"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: #FFC107; border: 1px solid #444; border-radius: 4px; padding: 4px; }
            QMenu::item { padding: 6px 20px; border-radius: 3px; }
            QMenu::item:selected { background-color: #555; }
            QMenu::item:disabled { color: #666; background-color: #333; }
        """)

        ip = node.get("ip", "").strip()

        telnet_action = menu.addAction("Telnet")
        telnet_action.triggered.connect(lambda: self.run_telnet(ip))

        edit_action = menu.addAction("Редактировать")
        edit_action.triggered.connect(lambda: self.edit_switch(node, ntype))
        edit_action.setEnabled(self.is_edit_mode)

        add_call_menu = menu.addMenu("Добавить неисправность")
        
        switch_down_action = add_call_menu.addAction("Свитч лежит")
        switch_down_action.triggered.connect(lambda: self.add_call_switch_down(node, ntype))
        
        ports_issue_action = add_call_menu.addAction("Порты с проблемами")
        ports_issue_action.triggered.connect(lambda: self.add_call_ports_issue(node, ntype))

        find_report_action = menu.addAction("Найти в глоб репорте")
        find_report_action.triggered.connect(lambda: self.show_message("Найти в глоб репорте - функция в разработке"))

        ping_action = menu.addAction("Ping")
        ping_action.triggered.connect(lambda: self.run_ping(ip))

        flood_ping_action = menu.addAction("Flood ping")
        flood_ping_action.triggered.connect(lambda: self.show_message("Flood ping - функция в разработке"))

        dhcp_action = menu.addAction("Режим DHCP")
        dhcp_action.triggered.connect(lambda: self.show_message("Режим DHCP - функция в разработке"))

        tickets_action = menu.addAction("Заявки")
        tickets_action.triggered.connect(lambda: self.show_message("Заявки - функция в разработке"))

        replace_action = menu.addAction("Замена свитча")
        replace_action.triggered.connect(lambda: self.show_message("Замена свитча - функция в разработке"))
        replace_action.setEnabled(self.is_edit_mode)

        history_action = menu.addAction("История")
        history_action.triggered.connect(lambda: self.show_message("История - функция в разработке"))

        delete_action = menu.addAction("Удалить свитч")
        delete_action.triggered.connect(lambda: self.show_message("Удалить свитч - функция в разработке"))
        delete_action.setEnabled(self.is_edit_mode)

        menu.exec(self.mapToGlobal(position))

    def run_ping(self, ip):
        if not ip:
            self.show_message("У устройства нет IP")
            return

        import subprocess, platform

        count = "4" if platform.system().lower() == "windows" else "4"
        param = "-n" if platform.system().lower() == "windows" else "-c"

        try:
            subprocess.Popen(
                ["cmd", "/c", f"ping {param} {count} {ip}"],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception:
            os.system(f"xterm -e 'ping {param} {count} {ip}' &")

    def run_telnet(self, ip):
        if not ip:
            self.show_message("У устройства нет IP")
            return

        import subprocess

        possible_paths = [
            r"C:\Program Files\PuTTY\putty.exe",
            r"C:\Program Files (x86)\PuTTY\putty.exe",
        ]

        putty_path = None
        for p in possible_paths:
            if os.path.exists(p):
                putty_path = p
                break

        try:
            if putty_path:
                subprocess.Popen([putty_path, "-telnet", ip])
            else:
                subprocess.Popen(["cmd", "/c", f"start telnet {ip}"])
        except Exception as e:
            self.show_message(f"Ошибка запуска telnet:\n{e}")

    def add_call_switch_down(self, node, ntype):
        """Добавить неисправность: Свитч лежит"""
        from globals_dialog import AddIssueDialog

        device_info = {
            "type": ntype,
            "id": node.get("id", ""),
            "name": node.get("name", "Неизвестно"),
            "ip": node.get("ip", "Нет IP")
        }

        if hasattr(self.parent, "ws_client"):
            dialog = AddIssueDialog(self.parent, device_info=device_info, ws_client=self.parent.ws_client)
            
            device_name = device_info.get("name", "Неизвестно")
            device_ip = device_info.get("ip", "Нет IP")
            dialog.description_input.setPlainText(f"{device_ip} ({device_name}) down")
            
            if dialog.exec():
                issue_data = dialog.get_data()
                self.show_message(f"Неисправность добавлена: Свитч лежит - {device_name}")
        else:
            self.show_message("Нет связи с сервером")

    def add_call_ports_issue(self, node, ntype):
        """Добавить неисправность: Порты с проблемами"""
        from globals_dialog import AddIssueDialog
        from globals_dialog import PortsIssueDialog

        device_info = {
            "type": ntype,
            "id": node.get("id", ""),
            "name": node.get("name", "Неизвестно"),
            "ip": node.get("ip", "Нет IP")
        }

        if not hasattr(self, "map_data") or self.map_data is None:
            self.show_message("Карта не загружена, невозможно определить порты устройства.")
            return

        try:
            ports_dialog = PortsIssueDialog(
                self.parent,
                device_info=device_info,
                ws_client=self.parent.ws_client,
                map_data=self.map_data
            )
        except Exception as e:
            self.show_message(f"Ошибка запуска диалога выбора портов: {e}")
            return

        if ports_dialog.exec():
            selected_ports = ports_dialog.get_selected_ports()

            if not selected_ports:
                self.show_message("Не отмечено ни одного порта.")
                return

            dialog = AddIssueDialog(
                self.parent,
                device_info=device_info,
                ws_client=self.parent.ws_client
            )

            dialog.description_input.setPlainText(ports_dialog.get_description())

            if dialog.exec():
                issue_data = dialog.get_data()
                device_name = device_info.get("name", "Неизвестно")
                self.show_message(f"Неисправность добавлена: Порты с проблемами — {device_name}")

    def edit_switch(self, node, ntype):
        """Открыть диалог редактирования свитча"""
        from widgets import SwitchEditDialog
        
        if ntype not in ["switch", "user", "soap"]:
            self.show_message(f"Редактирование для типа '{ntype}' не поддерживается")
            return
        
        ws_client = None
        if hasattr(self.parent, "ws_client"):
            ws_client = self.parent.ws_client
        
        dialog = SwitchEditDialog(self.parent, node, ws_client)
        
        if dialog.exec():
            self.render_map()
            self.save_map_to_file()
            self.show_status_saved()
            
            device_name = node.get("name", "Устройство")
            if hasattr(self.parent, 'status_bar'):
                self.parent.status_bar.showMessage(
                    f"Устройство '{device_name}' успешно обновлено", 3000
                )

    def show_hover_dialog(self):
        if not self.current_hover_node:
            return
        if self.current_hover_type == "switch":
            from widgets import SwitchInfoDialog
            SwitchInfoDialog(self.current_hover_node, self.parent).exec()
        elif self.current_hover_type == "plan_switch":
            from widgets import PlanSwitchInfoDialog
            PlanSwitchInfoDialog(self.current_hover_node, self.parent).exec()
        self.current_hover_node = None
        self.current_hover_type = None
