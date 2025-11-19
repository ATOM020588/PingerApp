# widgets/switch_info_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem, QMessageBox, QApplication,
    QTableWidget, QHeaderView, QTextEdit
)
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt
import base64
import re


class SwitchInfoDialog(QDialog):
    def __init__(self, switch_data, parent=None):
        super().__init__(parent)

        self.parent_window = parent  # ← СОХРАНЯЕМ MainWindow
        self.switch_data = switch_data

        switch_name = switch_data.get("name", "Без названия")
        self.setWindowTitle(switch_name)

        self.setFixedSize(800, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(False)

        self.setup_ui()
        self.load_image_from_server()  # ← ТЕПЕРЬ КАРТИНКА С СЕРВЕРА

    # ============================================================
    # UI
    # ============================================================

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # === Верхний блок: IP, статус, MAC ===
        top_info_layout = QHBoxLayout()
        top_info_layout.setContentsMargins(15, 10, 0, 10)
        top_info_layout.setSpacing(30)

        # IP — кликабельно
        ip = self.switch_data.get('ip', '—')
        ip_label = QLabel(f"<b>IP:</b> {ip}")
        ip_label.setStyleSheet("color: #FFC107; cursor: pointer;")
        ip_label.mousePressEvent = lambda e, text=ip: self.copy_to_clipboard(text, "IP")
        top_info_layout.addWidget(ip_label)

        # Статус
        status = "UP" if self.switch_data.get("pingok") else "DOWN"
        status_color = "#4CAF50" if self.switch_data.get("pingok") else "#F44336"
        status_label = QLabel(f"<b>Статус:</b> <span style='color:{status_color}'>{status}</span>")
        top_info_layout.addWidget(status_label)

        # MAC
        mac = self.switch_data.get('mac', '—')
        mac_label = QLabel(f"<b>MAC:</b> {mac}")
        mac_label.setStyleSheet("color: #FFC107; cursor: pointer;")
        mac_label.mousePressEvent = lambda e, text=mac: self.copy_to_clipboard(text, "MAC")
        top_info_layout.addWidget(mac_label)

        top_info_layout.addStretch()
        layout.addLayout(top_info_layout)

        # === Левая колонка: Изображение + кнопки ===
        left = QVBoxLayout()

        self.image_label = QLabel()
        self.image_label.setFixedSize(200, 150)
        self.image_label.setStyleSheet("background: #333; border-radius: 4px; border: 1px solid #FFC107;")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.image_label)

        # Кнопки
        details_btn = QPushButton("Подробнее")
        details_btn.clicked.connect(self.open_details)
        left.addWidget(details_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh_ping_ws)  # ← ПИНГ ЧЕРЕЗ WS
        left.addWidget(refresh_btn)

        left.addStretch()

        # === Правая колонка ===
        right = QVBoxLayout()

        right.addWidget(self.make_label(f"<b>Модель:</b> {self.switch_data.get('model', '—')}"))
        right.addWidget(self.make_label(f"<b>Uptime:</b> —"))
        right.addWidget(self.make_label(f"<b>Мастер:</b> {self.switch_data.get('master', '—')}"))
        right.addWidget(self.make_label(f"<b>Питание:</b> {self.switch_data.get('power', '—')}"))

        # === Таблица портов ===
        ports_table = QTableWidget()
        ports_table.setColumnCount(2)
        ports_table.setHorizontalHeaderLabels(["Порт", "Описание"])
        ports_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        ports_table.verticalHeader().setVisible(False)

        header = ports_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        ports_table.setColumnWidth(0, 20)

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
                    f = item.font()
                    f.setBold(True)
                    item.setFont(f)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            ports_table.setItem(i, 0, num_item)
            ports_table.setItem(i, 1, desc_item)

        right.addWidget(QLabel("<b>Порты:</b>"))
        right.addWidget(ports_table, 1)

        # === Основной блок ===
        info = QHBoxLayout()
        info.addLayout(left, 1)
        info.addLayout(right, 2)
        layout.addLayout(info, 1)

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

        # СТИЛИ
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #FFC107; }
            QLabel { color: #FFC107; }
            QPushButton { background-color: #333; color: #FFC107; border: none; padding: 8px; }
            QPushButton:hover { background-color: #555; }
            QTableWidget { background: #333; color: #FFC107; border: none; }
            QHeaderView::section { background-color: #444; color: #FFC107; padding: 6px; }
        """)

    # ============================================================
    # Загрузка изображения с сервера
    # ============================================================

    def load_image_from_server(self):
        model = self.switch_data.get("model", "")
        if not model:
            self.image_label.setText("<i>Модель не указана</i>")
            return

        model_clean = re.sub(r'[^\w.-]', '', model).replace(" ", "_").lower()

        candidates = [
            f"model_{model_clean}.png",
            f"model_{model_clean}.jpg",
            f"model_{model_clean}.jpeg",
            f"model_{model_clean}.bmp",
            f"model_{model_clean}.gif",
        ]

        def try_load(index=0):
            if index >= len(candidates):
                self.image_label.setText("<i>Изображение отсутствует</i>")
                self.image_label.setStyleSheet("color: #888;")
                return

            filename = candidates[index]

            req = self.parent_window.ws_client.send_request(
                "download_image",
                filename=filename
            )

            def callback(resp):
                if resp.get("success") and resp.get("image"):
                    pix = QPixmap()
                    pix.loadFromData(base64.b64decode(resp["image"]))
                    pix = pix.scaled(200, 150, Qt.AspectRatioMode.IgnoreAspectRatio)
                    self.image_label.setPixmap(pix)
                else:
                    try_load(index + 1)

            self.parent_window.pending_requests[req] = callback

        try_load()

    # ============================================================
    # WebSocket ПИНГ
    # ============================================================

    def refresh_ping_ws(self):
        ip = self.switch_data.get("ip")
        if not ip:
            QMessageBox.information(self, "Инфо", "IP не указан")
            return

        req = self.parent_window.ws_client.send_request("ping", ip=ip)

        def callback(resp):
            ok = resp.get("success", False)
            self.switch_data["pingok"] = ok

            main_window = self.parent_window.parent()  # ← ВОТ ТАК ПРАВИЛЬНО

            list_key = "switches" if self.switch_data.get("type") != "plan_switch" else "plan_switches"

            for i, s in enumerate(main_window.map_data[list_key]):
                if s["id"] == self.switch_data["id"]:
                    main_window.map_data[list_key][i] = self.switch_data
                    break

            main_window.render_map()
            self.close()
            main_window.show_switch_info(self.switch_data)

    # ============================================================
    # Разное
    # ============================================================

    def copy_to_clipboard(self, text, label):
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Инфо", f"{label} скопирован")

    def open_details(self):
        ip = self.switch_data.get("ip")
        if ip:
            import webbrowser
            webbrowser.open(f"http://another-site/neotools/usersonline/index.php?ip={ip}&flood=1")

    def make_label(self, text):
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        return lbl

    def show_message(self, text):
        QMessageBox.information(self, "Инфо", text)
