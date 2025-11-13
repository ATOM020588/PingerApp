# login_dialog.py

import os
import json
import hashlib
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStatusBar, QWidget, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QPixmap
import asyncio
import websockets
from websockets.protocol import State


class WebSocketLoginClient(QThread):
    connected = pyqtSignal(bool)
    login_response = pyqtSignal(dict)

    def __init__(self, uri="ws://127.0.0.1:8081"):
        super().__init__()
        self.uri = uri
        self.websocket = None
        self.loop = None
        self.running = True
        print(f"[WS] Инициализация клиента: {uri}")

    def run(self):
        print("[WS] Запуск потока WebSocket...")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main())
        print("[WS] Поток завершён")

    async def _main(self):
        while self.running:
            try:
                print(f"[WS] Попытка подключения к {self.uri}...")
                async with websockets.connect(
                    self.uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ) as ws:
                    self.websocket = ws
                    print("[WS] УСПЕШНО подключено!")
                    self.connected.emit(True)

                    while self.running and ws.state == State.OPEN:
                        await asyncio.sleep(1)

                    if ws.state == State.OPEN:
                        print("[WS] Закрываем соединение...")
                        await ws.close()

            except Exception as e:
                print(f"[WS] ОШИБКА подключения: {e}")
                self.connected.emit(False)
                if self.running:
                    print("[WS] Повторная попытка через 2 сек...")
                    await asyncio.sleep(2)
            finally:
                self.websocket = None
                self.connected.emit(False)

        print("[WS] Цикл завершён")
        self.connected.emit(False)

    def send_login(self, login, password_hash):
        if self.websocket and self.isRunning():
            asyncio.run_coroutine_threadsafe(
                self._send_login(login, password_hash), self.loop
            )

    async def _send_login(self, login, password_hash):
        try:
            request = {
                "action": "auth_login",
                "login": login,
                "password_hash": password_hash
            }
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            data = json.loads(response)
            self.login_response.emit(data)
        except Exception as e:
            self.login_response.emit({"success": False, "error": str(e)})

    def stop(self):
        self.running = False


class LoginDialog(QDialog):
    login_successful = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в систему")
        self.setFixedSize(400, 500)
        self.setStyleSheet("background-color: #333; color: #FFC107;")
        
        self.ws_client = WebSocketLoginClient()
        self.ws_client.connected.connect(self.on_connection_changed)
        self.ws_client.login_response.connect(self.on_login_response)
        self.ws_client.start()

        self.is_connected = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        self.setLayout(layout)

        # === ЛОГОТИП ===
        logo_label = QLabel()
        logo_path = "logo/mainlogo.png"
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(
                200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("LOGO")
            logo_label.setStyleSheet("font-size: 48px; font-weight: bold;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # === ЗАГОЛОВОК ===
        title = QLabel("Network Management System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # === ПОЛЯ ВВОДА ===
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Login")
        self.login_input.setStyleSheet(self.input_style())

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(self.input_style())

        form_layout.addWidget(QLabel("Login:"))
        form_layout.addWidget(self.login_input)
        form_layout.addWidget(QLabel("Password:"))
        form_layout.addWidget(self.password_input)
        layout.addLayout(form_layout)

        # === КНОПКА ВХОДА ===
        self.login_button = QPushButton("Войти")
        self.login_button.setFixedWidth(300)
        self.login_button.setStyleSheet(self.button_style())
        self.login_button.clicked.connect(self.attempt_login)
        self.login_button.setEnabled(False)
        layout.addWidget(self.login_button)

        # === STATUSBAR ===
        self.status_bar = QStatusBar()
        self.status_bar.setFixedSize(300,40)
        self.status_bar.setStyleSheet("color: #FFC107; background-color: #444; border: none;")
        layout.addWidget(self.status_bar)

        # === ТАЙМЕР ОБНОВЛЕНИЯ СТАТУСА ===
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)

    def input_style(self):
        return """
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; height: 18px; padding: 6px; }
            QLineEdit:focus { border: 2px solid #FFC107; }
        """

    def button_style(self):
        return """
            QPushButton { background-color: #444; color: #FFC107; border: none; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #FFB300; }
            QPushButton:disabled { background-color: #555; color: #888; }
        """

    def on_connection_changed(self, is_connected):
        print(f"[GUI] Статус подключения: {is_connected}")
        self.is_connected = is_connected
        self.login_button.setEnabled(is_connected)
        self.update_status()

    def update_status(self):
        if self.is_connected:
            self.status_bar.showMessage("Сервер: активен", 3000)
        else:
            self.status_bar.showMessage("Ожидание подключения к серверу...", 3000)

    def attempt_login(self):
        if not self.is_connected:
            self.status_bar.showMessage("Нет связи с сервером", 5000)
            return

        login = self.login_input.text().strip()
        password = self.password_input.text()

        if not login or not password:
            self.status_bar.showMessage("Заполните все поля", 3000)
            return

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        self.login_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.login_button.setEnabled(False)

        self.ws_client.send_login(login, password_hash)

    def on_login_response(self, response):
        self.login_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.login_button.setEnabled(self.is_connected)

        if response.get("success"):
            self.status_bar.showMessage("Вход успешен", 3000)
            QTimer.singleShot(500, lambda: self.login_successful.emit(response.get("user", {})))
            self.accept()
        else:
            error = response.get("error", "Неизвестная ошибка")
            self.status_bar.showMessage(f"Ошибка: {error}", 5000)
            self.password_input.clear()

    def closeEvent(self, event):
        self.ws_client.running = False
        self.ws_client.wait()
        super().closeEvent(event)
