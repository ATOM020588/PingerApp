# widgets/switch_info_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem, QMessageBox,
    QTableWidget, QHeaderView, QTextEdit, QApplication
)
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt
import requests
import webbrowser
import os
import re


class SwitchInfoDialog(QDialog):
    def __init__(self, switch_data, parent=None):
        super().__init__(parent)
        self.switch_data = switch_data
        switch_name = switch_data.get("name", "Без названия")
        self.setWindowTitle(switch_name)

        self.setFixedSize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(False)

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # === Верхняя строка: IP, Статус, MAC ===
        top_info_layout = QHBoxLayout()
        top_info_layout.setContentsMargins(15, 10, 0, 10)
        top_info_layout.setSpacing(30)

        # --- IP (кликабельный) ---
        ip = self.switch_data.get('ip', '—')
        ip_label = QLabel(f"<b>IP:</b> {ip}")
        ip_label.setStyleSheet("color: #FFC107; cursor: pointer;")
        ip_label.setToolTip("Клик — скопировать IP")
        ip_label.mousePressEvent = lambda event, text=ip: self.copy_to_clipboard(text, "IP")
        top_info_layout.addWidget(ip_label)

        # --- Статус (некликабельный) ---
        status = "UP" if self.switch_data.get("pingok") else "DOWN"
        status_color = "#4CAF50" if self.switch_data.get("pingok") else "#F44336"
        status_label = QLabel(f"<b>Статус:</b> <span style='color:{status_color}'>{status}</span>")
        top_info_layout.addWidget(status_label)

        # --- MAC (кликабельный) ---
        mac = self.switch_data.get('mac', '—')
        mac_label = QLabel(f"<b>MAC:</b> {mac}")
        mac_label.setStyleSheet("color: #FFC107; cursor: pointer;")
        mac_label.setToolTip("Клик — скопировать MAC")
        mac_label.mousePressEvent = lambda event, text=mac: self.copy_to_clipboard(text, "MAC")
        top_info_layout.addWidget(mac_label)

        top_info_layout.addStretch()
        layout.addLayout(top_info_layout)

        # === Левая колонка: Изображение + Кнопки ===
        left = QVBoxLayout()

        # Изображение
        image_label = QLabel()
        image_label.setFixedSize(200, 150)
        image_label.setStyleSheet("background: #333; border-radius: 4px; border: 1px solid #FFC107;")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        model = self.switch_data.get("model", "—")
        if model == "—":
            image_label.setText("<i>Модель не указана</i>")
            image_label.setStyleSheet(image_label.styleSheet() + " color: #888;")
        else:
            model_clean = re.sub(r'[^\w\s.-]', '', model)
            model_clean = re.sub(r'\s+', ' ', model_clean).strip().lower()

            image_dir = "images"
            image_found = False
            if os.path.exists(image_dir):
                candidates = [
                    f"model_{model_clean}",
                    f"model_{model_clean.replace(' ', '_')}",
                    f"model_{model_clean.replace(' ', '-')}",
                ]
                for base_name in candidates:
                    for ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                        img_path = os.path.join(image_dir, f"{base_name}{ext}")
                        if os.path.exists(img_path):
                            pixmap = QPixmap(img_path)
                            if not pixmap.isNull():
                                scaled = pixmap.scaled(
                                    200, 150,
                                    Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation
                                )
                                image_label.setPixmap(scaled)
                                image_found = True
                            break
                    if image_found:
                        break

            if not image_found:
                image_label.setText("<i>Изображение отсутствует</i>")
                image_label.setStyleSheet(image_label.styleSheet() + " color: #888;")

        left.addWidget(image_label)

        # Кнопки
        details_btn = QPushButton("Подробнее")
        details_btn.clicked.connect(self.open_details)
        left.addWidget(details_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh_ping)
        left.addWidget(refresh_btn)

        left.addStretch()

        # === Правая колонка: Остальная информация + Таблица ===
        right = QVBoxLayout()

        right.addWidget(self.make_label(f"<b>Модель:</b> {self.switch_data.get('model', '—')}"))
        right.addWidget(self.make_label(f"<b>Uptime:</b> —"))
        right.addWidget(self.make_label(f"<b>Мастер:</b> {self.switch_data.get('master', '—')}"))
        right.addWidget(self.make_label(f"<b>Питание:</b> {self.switch_data.get('power', '—')}"))

        # === Таблица портов ===
        ports_table = QTableWidget()
        ports_table.setColumnCount(2)
        ports_table.setHorizontalHeaderLabels(["Порт", "Описание"])

        # Без выделения
        ports_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # Убираем нумерацию строк
        ports_table.verticalHeader().setVisible(False)

        # Колонка "Порт" — 20px, "Описание" — остальное
        header = ports_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        ports_table.setColumnWidth(0, 20)

        # Заполнение таблицы
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

            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            ports_table.setItem(i, 0, num_item)
            ports_table.setItem(i, 1, desc_item)

        right.addWidget(QLabel("<b>Порты:</b>"))
        right.addWidget(ports_table, stretch=1)

        # === Основной layout ===
        info = QHBoxLayout()
        info.addLayout(left, 1)
        info.addLayout(right, 2)
        layout.addLayout(info, stretch=1)

        # Примечание
        note = self.switch_data.get("note", "").strip()
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

        # === СТИЛИ ===
        self.setStyleSheet("""
            QDialog { 
                background: #2b2b2b; 
                color: #FFC107; 
                border: none; 
                border-radius: 0px;
            }
            QLabel { color: #FFC107; border: none; }
            QPushButton { 
                background-color: #333; color: #FFC107; border: none; 
                border-radius: 4px; padding: 8px 12px; min-width: 80px;
            }
            QPushButton:hover { background-color: #555; }
            QTableWidget { 
                background: #333; color: #FFC107; border: none; 
                gridline-color: #444; 
                border-radius: 0px;
            }
            QHeaderView::section { 
                background-color: #444;
                color: #FFC107;
                padding: 6px;
                border: none !important;
                border-radius: 0px !important;
                margin: 0px;
                font-weight: bold;
            }
            QHeaderView {
                background-color: #444;
                border: none;
                border-radius: 0px;
                show-decoration-selected: 0;
            }
            QTableWidget::item { padding: 4px; border: none; }
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
            # ← ПИНГ ЧЕРЕЗ СЕРВЕР НА ПОРТУ 8081
            response = requests.get(f"http://localhost:8081/ping?ip={ip}", timeout=3)
            result = response.json()
            self.switch_data["pingok"] = result.get("success", False)

            # ← ИСПРАВЛЕНИЕ: self.parent() — это MapCanvas, а нужно MainWindow
            main_window = self.parent().parent  # ← ВОТ ТАК

            list_key = "switches" if self.switch_data.get("type") != "plan_switch" else "plan_switches"
            for i, s in enumerate(main_window.map_data[list_key]):
                if s["id"] == self.switch_data["id"]:
                    main_window.map_data[list_key][i] = self.switch_data
                    break

            main_window.render_map()
            self.close()
            main_window.show_switch_info(self.switch_data)  # ← Теперь работает

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