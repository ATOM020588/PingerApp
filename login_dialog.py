# login_dialog.py
import os
import json
import hashlib
import pickle
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStatusBar, QWidget, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSettings
from PyQt6.QtGui import QPixmap
import asyncio
import websockets
from websockets.protocol import State

class WebSocketLoginClient(QThread):
    connected = pyqtSignal(bool)
    login_response = pyqtSignal(dict)

    def __init__(self, uri="ws://192.168.0.56:8081"):
        super().__init__()
        self.uri = uri
        self.websocket = None
        self.loop = None
        self.running = True

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._main())

    async def _main(self):
        while self.running:
            try:
                async with websockets.connect(
                    self.uri,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ) as ws:
                    self.websocket = ws
                    self.connected.emit(True)

                    while self.running and ws.state == State.OPEN:
                        await asyncio.sleep(1)

            except Exception as e:
                self.connected.emit(False)
                if self.running:
                    await asyncio.sleep(2)
            finally:
                self.websocket = None
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
        self.setFixedSize(350, 540)
        self.setStyleSheet("background-color: #333; color: #FFC107;")

        # Инициализация QSettings для резервного сохранения
        self.settings = QSettings("Network Management System", "UserSession")

        # Переменные для сохраненных данных
        self.saved_login = ""
        self.saved_password_hash = ""

        self.ws_client = WebSocketLoginClient()
        self.ws_client.connected.connect(self.on_connection_changed)
        self.ws_client.login_response.connect(self.on_login_response)
        self.ws_client.start()

        self.is_connected = False
        self.setup_ui()

        # Загрузка сохраненных учетных данных (БЕЗ автологина)
        self.load_saved_credentials()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        self.setLayout(layout)

        # Логотип
        logo_label = QLabel()
        logo_path = "logo/mainlogo.png"
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            logo_label.setText("PINGER")
            logo_label.setStyleSheet("font-size: 32px; font-weight: bold;")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo_label)

        # Заголовок
        title = QLabel("Network Management System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        # Форма
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Login")
        self.login_input.setStyleSheet(self.input_style())

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(self.input_style())

        form_layout.addWidget(QLabel("Логин:"))
        form_layout.addWidget(self.login_input)
        form_layout.addWidget(QLabel("Пароль:"))
        form_layout.addWidget(self.password_input)

        # Чекбокс "Запомнить меня"
        self.remember_checkbox = QCheckBox("Запомнить меня")
        self.remember_checkbox.setChecked(True)
        self.remember_checkbox.setStyleSheet("""
            QCheckBox { color: #FFC107; font-size: 12px; spacing: 8px; padding: 4px; }
            QCheckBox::indicator { width: 12px; height: 12px; border-radius: 4px; border: 2px solid #555; background-color: #333; }
            QCheckBox::indicator:checked { background-color: #FFC107; border: 2px solid #FFC107; }
            QCheckBox::indicator:checked:hover { background-color: #FFB300; border: 2px solid #FFB300; }
            QCheckBox::indicator:hover { border: 2px solid #FFC107; }
        """)
        form_layout.addWidget(self.remember_checkbox)

        layout.addLayout(form_layout)

        # Кнопка входа
        self.login_button = QPushButton("Войти")
        self.login_button.setStyleSheet(self.button_style())
        self.login_button.clicked.connect(self.attempt_login)
        self.login_button.setEnabled(False)
        layout.addWidget(self.login_button)

        # Статус-бар
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #FFC107; background-color: #444; border-radius: 4px;")
        layout.addWidget(self.status_bar)

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)

    def input_style(self):
        return "QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 6px; } QLineEdit:focus { border: 2px solid #FFC107; }"

    def button_style(self):
        return "QPushButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 10px; } QPushButton:hover { background-color: #555; } QPushButton:disabled { background-color: #555; color: #888; }"

    def on_connection_changed(self, is_connected):
        self.is_connected = is_connected
        self.login_button.setEnabled(is_connected)
        self.update_status()

    def update_status(self):
        if self.is_connected:
            self.status_bar.showMessage("Сервер: активен", 0)
        else:
            self.status_bar.showMessage("Ожидание подключения к серверу...", 0)

    def load_saved_credentials(self):
        """Загружает сохраненные учетные данные из session.pkl или QSettings"""
        # Приоритет: session.pkl > QSettings
        session_file = "session.pkl"
        
        try:
            if os.path.exists(session_file):
                with open(session_file, "rb") as f:
                    session_data = pickle.load(f)
                    
                if isinstance(session_data, dict):
                    self.saved_login = session_data.get("login", "")
                    self.saved_password_hash = session_data.get("password_hash", "")
                    remember_me = session_data.get("remember_me", False)
                    
                    if self.saved_login and remember_me:
                        self.login_input.setText(self.saved_login)
                        # Пароль заполняем звездочками для визуализации
                        self.password_input.setText("********")
                        self.remember_checkbox.setChecked(True)
                        print(f"Загружены учетные данные из session.pkl для пользователя: {self.saved_login}")
                        return
        except Exception as e:
            print(f"Ошибка загрузки из session.pkl: {e}")
        
        # Fallback к QSettings
        self.saved_login = self.settings.value("saved_login", "")
        self.saved_password_hash = self.settings.value("saved_password_hash", "")
        remember_me = self.settings.value("remember_me", False, type=bool)

        if self.saved_login and self.saved_password_hash and remember_me:
            self.login_input.setText(self.saved_login)
            # Пароль заполняем звездочками для визуализации
            self.password_input.setText("********")
            self.remember_checkbox.setChecked(True)
            print(f"Загружены учетные данные из QSettings для пользователя: {self.saved_login}")

    def save_credentials(self, login, password_hash):
        """Сохраняет учетные данные в session.pkl и QSettings"""
        if self.remember_checkbox.isChecked():
            # Сохранение в session.pkl (основной способ)
            session_file = "session.pkl"
            session_data = {
                "login": login,
                "password_hash": password_hash,
                "remember_me": True
            }
            
            try:
                with open(session_file, "wb") as f:
                    pickle.dump(session_data, f)
                print(f"Учетные данные сохранены в session.pkl для пользователя: {login}")
            except Exception as e:
                print(f"Ошибка сохранения в session.pkl: {e}")
            
            # Резервное сохранение в QSettings
            self.settings.setValue("saved_login", login)
            self.settings.setValue("saved_password_hash", password_hash)
            self.settings.setValue("remember_me", True)
            self.settings.sync()
        else:
            # Если чекбокс не отмечен, удаляем сохраненные данные
            session_file = "session.pkl"
            if os.path.exists(session_file):
                try:
                    os.remove(session_file)
                    print("Файл session.pkl удален")
                except Exception as e:
                    print(f"Ошибка удаления session.pkl: {e}")
            
            self.settings.remove("saved_login")
            self.settings.remove("saved_password_hash")
            self.settings.setValue("remember_me", False)
            self.settings.sync()
            print("Учетные данные не сохранены (чекбокс не отмечен)")

    def attempt_login(self):
        if not self.is_connected:
            self.status_bar.showMessage("Нет связи с сервером", 5000)
            return

        login = self.login_input.text().strip()
        password = self.password_input.text()

        if not login or not password:
            self.status_bar.showMessage("Заполните все поля", 5000)
            return

        # Проверяем, использует ли пользователь сохраненный пароль
        if password == "********" and self.saved_password_hash:
            # Используем сохраненный хеш
            password_hash = self.saved_password_hash
        else:
            # Хешируем введенный пароль
            password_hash = hashlib.sha256(password.encode()).hexdigest()

        self.login_input.setEnabled(False)
        self.password_input.setEnabled(False)
        self.login_button.setEnabled(False)

        self.ws_client.send_login(login, password_hash)

    def on_login_response(self, response):
        self.login_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.login_button.setEnabled(self.is_connected)

        current_login = self.login_input.text().strip()
        current_password = self.password_input.text()
        
        # Получаем правильный хеш пароля
        if current_password == "********" and self.saved_password_hash:
            password_hash = self.saved_password_hash
        else:
            password_hash = hashlib.sha256(current_password.encode()).hexdigest()

        if response.get("success"):
            self.status_bar.showMessage("Вход успешен", 5000)

            # Сохранение учетных данных при успешном входе
            self.save_credentials(current_login, password_hash)

            user_data = response.get("user", {})
            user_data["login"] = current_login
            QTimer.singleShot(300, lambda: self.login_successful.emit(user_data))
            self.accept()

        else:
            error = response.get("error", "Ошибка входа")
            self.status_bar.showMessage(f"Ошибка: {error}", 6000)
            self.password_input.clear()
            self.password_input.setFocus()

    def get_credentials(self):
        """Возвращает логин и хеш пароля после успешного входа"""
        login = self.login_input.text().strip()
        password = self.password_input.text()
        
        if password == "********" and self.saved_password_hash:
            password_hash = self.saved_password_hash
        else:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        return login, password_hash

    def get_user_login(self):
        """Возвращает логин пользователя"""
        return self.login_input.text().strip()

    def closeEvent(self, event):
        self.ws_client.stop()
        self.ws_client.wait()
        super().closeEvent(event)
