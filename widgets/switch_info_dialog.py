# widgets/switch_info_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt
import requests
import webbrowser
import os


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

        # Заголовок
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

        # Изображение
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

        # Текст
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