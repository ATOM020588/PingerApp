from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidgetItem, QMessageBox, QApplication,
    QTableWidget, QHeaderView, QTextEdit
)
from PyQt6.QtGui import QPixmap, QColor, QFont
from PyQt6.QtCore import Qt
import base64
import re


class SwitchInfoDialog(QDialog):
    """
    Диалоговое окно для отображения подробной информации о сетевом коммутаторе.

    Атрибуты:
        parent_window: Ссылка на родительское окно (MainWindow).
        switch_data (dict): Словарь с данными о коммутаторе.
        status_label (QLabel): Метка для отображения статуса коммутатора.
        image_label (QLabel): Метка для отображения изображения коммутатора.
    """
    def __init__(self, switch_data, parent=None):
        """
        Инициализация диалогового окна SwitchInfoDialog.

        Args:
            switch_data (dict): Словарь с данными о коммутаторе.
            parent (QWidget, optional): Родительский виджет. Defaults to None.
        """
        super().__init__(parent)

        self.parent_window = parent  # ← СОХРАНЯЕМ MainWindow
        self.switch_data = switch_data
        self.ports_count = 24  # По умолчанию 24 порта

        switch_name = switch_data.get("name", "Без названия")
        self.setWindowTitle(switch_name)

        self.setFixedSize(650, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(False)

        # Загружаем количество портов из модели
        self.load_ports_count()
        
        self.setup_ui()
        self.load_image_from_server()  # ← ТЕПЕРЬ КАРТИНКА С СЕРВЕРА

    # ============================================================
    # Загрузка количества портов
    # ============================================================
    
    def load_ports_count(self):
        """Загружает количество портов из файла модели"""
        model = self.switch_data.get("model", "")
        if not model:
            # Если модели нет, используем порты из данных
            self.update_ports_table()
            return
        
        # Преобразуем имя модели в имя файла
        model_filename = model.replace(" ", "_")
        model_filename = re.sub(r'[^\w.-]', '_', model_filename)
        
        # Запрос данных модели
        if self.parent_window and hasattr(self.parent_window, 'ws_client'):
            request_id = self.parent_window.ws_client.send_request(
                "file_get",
                path=f"data/models/model_{model_filename}.json"
            )
            
            if request_id:
                def on_model_response(data):
                    if data.get("success") and data.get("data"):
                        model_data = data.get("data", {})
                        ports_count_str = model_data.get("ports_count", "24")
                        try:
                            self.ports_count = int(ports_count_str)
                        except (ValueError, TypeError):
                            self.ports_count = 24
                    else:
                        # Если не удалось загрузить, используем максимум из данных
                        ports = self.switch_data.get("ports", [])
                        if ports:
                            max_port = 0
                            for port in ports:
                                port_num_str = port.get("number", "0")
                                try:
                                    num_match = re.match(r'(\d+)', port_num_str)
                                    if num_match:
                                        num = int(num_match.group(1))
                                        max_port = max(max_port, num)
                                except (ValueError, AttributeError):
                                    pass
                            if max_port > 0:
                                self.ports_count = max_port
                    
                    # Обновляем таблицу портов ПОСЛЕ получения данных
                    self.update_ports_table()
                
                if hasattr(self.parent_window, 'pending_requests'):
                    self.parent_window.pending_requests[request_id] = on_model_response
        else:
            # Если нет ws_client, обновляем таблицу сразу
            self.update_ports_table()

    # ============================================================
    # UI
    # ============================================================

    def setup_ui(self):
        """
        Настраивает пользовательский интерфейс диалогового окна.
        Создает макеты, виджеты и устанавливает стили.
        ""
"""
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
        self.status_label = QLabel(f"<b>Статус:</b> <span style='color:{status_color}'>{status}</span>")
        top_info_layout.addWidget(self.status_label)

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
        right.addWidget(self.make_label(f"<b>Uptime:</b> —")) # Uptime не отображается в данных, ставим заглушку
        right.addWidget(self.make_label(f"<b>Мастер:</b> {self.switch_data.get('master', '—')}"))
        right.addWidget(self.make_label(f"<b>Питание:</b> {self.switch_data.get('power', '—')}"))

        # === Таблица портов ===
        self.ports_table = QTableWidget()
        self.ports_table.setColumnCount(2)
        self.ports_table.setHorizontalHeaderLabels(["Порт", "Описание"])
        self.ports_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.ports_table.verticalHeader().setVisible(False)
        
        # Включаем горизонтальную прокрутку
        self.ports_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.ports_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        # Настройка ширины колонок
        header = self.ports_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.ports_table.setColumnWidth(0, 80)  # Фиксированная ширина для "Порт"
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.ports_table.setColumnWidth(1, 340)

        # Порты будут заполнены после загрузки данных модели
        # НЕ вызываем update_ports_table() здесь!

        right.addWidget(QLabel("<b>Порты:</b>"))
        right.addWidget(self.ports_table, 1) # Растягиваем таблицу

        # === Основной блок ===
        info = QHBoxLayout()
        info.addLayout(left, 1) # Левая часть занимает 1 долю
        info.addLayout(right, 2) # Правая часть занимает 2 доли
        layout.addLayout(info, 1) # Основной блок занимает 1 долю

        # Примечание
        note = self.switch_data.get("note", "").strip()
        if note:
            note_edit = QTextEdit()
            note_edit.setPlainText(note)
            note_edit.setReadOnly(True)
            note_edit.setFixedHeight(80) # Ограничиваем высоту
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
            QPushButton { background-color: #333; color: #FFC107; border: none; padding: 8px; border-radius: 4px;}
            QPushButton:hover { background-color: #555; }
            QTableWidget { background: #333; color: #FFC107; border: none; }
            QHeaderView::section { background-color: #444; color: #FFC107; padding: 6px; border: 1px solid #555;}
            QTableWidget::item { border-bottom: 1px solid #555; } /* Горизонтальные разделители для строк */
            QTextEdit { background-color: #333; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 5px;}
        """)

    def update_ports_table(self):
        """Обновляет таблицу портов с учетом всех портов модели"""
        # Создаем словарь портов из данных для быстрого поиска
        ports_data = {}
        for port in self.switch_data.get("ports", []):
            port_number = port.get("number", "")
            if port_number:
                ports_data[port_number] = port
        
        # Устанавливаем количество строк
        self.ports_table.setRowCount(self.ports_count)
        
        # Заполняем все порты
        for i in range(self.ports_count):
            port_number = str(i + 1)
            
            # Колонка "Порт" - всегда желтый цвет
            num_item = QTableWidgetItem(port_number)
            num_item.setForeground(QColor("#FFC107"))
            num_item.setFlags(num_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ports_table.setItem(i, 0, num_item)
            
            # Колонка "Описание"
            port_info = ports_data.get(port_number, None)
            
            if port_info:
                # Порт с данными
                description = port_info.get("description", "")
                color = port_info.get("color", "#FFC107")
                bold = port_info.get("bold", False)
                
                desc_item = QTableWidgetItem(description)
                desc_item.setForeground(QColor(color))
                
                if bold:
                    font = desc_item.font()
                    font.setBold(True)
                    desc_item.setFont(font)
            else:
                # Порт без данных - пустое описание с цветом по умолчанию
                desc_item = QTableWidgetItem("")
                desc_item.setForeground(QColor("#FFC107"))
            
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ports_table.setItem(i, 1, desc_item)

    # ============================================================
    # Загрузка изображения с сервера
    # ============================================================

    def load_image_from_server(self):
        """
        Загружает изображение коммутатора с сервера по его модели.
        Пытается загрузить изображения с разными расширениями и регистрами.
        """
        model = self.switch_data.get("model", "")
        if not model:
            self.image_label.setText("<i>Модель не указана</i>")
            return

        # ИСПРАВЛЕНИЕ: Правильный порядок обработки имени модели
        # 1. Сначала заменяем пробелы на подчеркивания
        model_clean = model.replace(" ", "_")
        # 2. Затем удаляем/заменяем недопустимые символы (оставляем буквы, цифры, дефис, точку, подчеркивание)
        # \w соответствует буквам, цифрам и подчеркиванию. Добавляем дефис и точку.
        model_clean = re.sub(r'[^\w.-]', '_', model_clean) 
        # 3. НЕ делаем lower() - сохраняем оригинальный регистр, но будем пробовать и в нижнем регистре
        
        # Создаем список кандидатов с учетом возможных вариантов регистра и расширений
        candidates = [
            # Точное соответствие (с сохранением регистра)
            f"model_{model_clean}.png",
            f"model_{model_clean}.jpg",
            f"model_{model_clean}.jpeg",
            # Вариант в нижнем регистре (для обратной совместимости)
            f"model_{model_clean.lower()}.png",
            f"model_{model_clean.lower()}.jpg",
            f"model_{model_clean.lower()}.jpeg",
            # Дополнительные форматы
            f"model_{model_clean}.bmp",
            f"model_{model_clean}.gif",
            f"model_{model_clean.lower()}.bmp",
            f"model_{model_clean.lower()}.gif",
        ]

        def try_load(index=0):
            """
            Рекурсивная функция для попытки загрузки изображений из списка кандидатов.
            
            Args:
                index (int): Индекс текущего кандидата в списке.
            """
            if index >= len(candidates):
                self.image_label.setText("<i>Изображение отсутствует</i>")
                self.image_label.setStyleSheet("color: #888;") # Серый цвет для отсутствующего изображения
                return

            filename = candidates[index]

            # Отправляем запрос на скачивание изображения через WebSocket
            req = self.parent_window.ws_client.send_request(
                "download_image",
                filename=filename
            )

            def callback(resp):
                """
                Обработчик ответа от сервера.
                
                Args:
                    resp (dict): Ответ от сервера.
                """
                if resp.get("success") and resp.get("image"):
                    pix = QPixmap()
                    pix.loadFromData(base64.b64decode(resp["image"]))
                    # Масштабируем изображение, игнорируя соотношение сторон, чтобы оно соответствовало размеру QLabel
                    pix = pix.scaled(200, 150, Qt.AspectRatioMode.IgnoreAspectRatio) 
                    self.image_label.setPixmap(pix)
                else:
                    # Если изображение не найдено, пробуем следующее
                    try_load(index + 1)

            # Сохраняем callback для обработки ответа по этому запросу
            self.parent_window.pending_requests[req] = callback

        try_load() # Начинаем попытку загрузки с первого кандидата

    # ============================================================
    # WebSocket ПИНГ
    # ============================================================

    def refresh_ping_ws(self):
        """
        Выполняет проверку доступности коммутатора (пинг) через WebSocket.
        Обновляет данные о статусе в родительском окне и перерисовывает карту.
        """
        ip = self.switch_data.get("ip")
        if not ip:
            QMessageBox.information(self, "Инфо", "IP не указан")
            return

        # Отправляем запрос на пинг
        req = self.parent_window.ws_client.send_request("ping", ip=ip)

        def callback(resp):
            """
            Обработчик ответа на пинг.
            
            Args:
                resp (dict): Ответ от сервера с результатом пинга.
            """
            ok = resp.get("success", False)
            self.switch_data["pingok"] = ok

            # ИСПРАВЛЕНО: Правильное получение main_window
            # Пытаемся получить main_window разными способами, чтобы обеспечить совместимость
            main_window = None
            
            # Способ 1: parent_window это и есть main_window (если у него есть map_data и active_map_id)
            if hasattr(self.parent_window, 'map_data') and hasattr(self.parent_window, 'active_map_id'):
                main_window = self.parent_window
            # Способ 2: parent_window это MapCanvas, его parent() - main_window
            elif hasattr(self.parent_window, 'parent') and callable(self.parent_window.parent):
                potential_parent = self.parent_window.parent()
                if potential_parent and hasattr(potential_parent, 'map_data') and hasattr(potential_parent, 'active_map_id'):
                    main_window = potential_parent
            
            # Если main_window не найден, просто показываем сообщение
            if not main_window or not hasattr(main_window, 'map_data') or not hasattr(main_window, 'active_map_id'):
                QMessageBox.information(self, "Инфо", "Данные обновлены")
                return

            # ИСПРАВЛЕНИЕ: Проверяем наличие active_map_id перед обращением к map_data
            active_map = main_window.active_map_id
            if not active_map or active_map not in main_window.map_data:
                QMessageBox.information(self, "Инфо", "Данные обновлены")
                return

            # Определяем ключ для списка коммутаторов в зависимости от типа
            # Если это не 'plan_switch', то это обычный коммутатор ('switches')
            list_key = "switches" if self.switch_data.get("type") != "plan_switch" else "plan_switches"

            # ОСНОВНОЕ ИСПРАВЛЕНИЕ: Добавляем active_map_id для корректного обращения к данным
            # Было: main_window.map_data[list_key]
            # Стало: main_window.map_data[active_map][list_key]
            if active_map not in main_window.map_data or list_key not in main_window.map_data[active_map]:
                QMessageBox.information(self, "Инфо", "Данные обновлены")
                return

            # Обновляем данные о коммутаторе в map_data
            for i, s in enumerate(main_window.map_data[active_map][list_key]):
                if s.get("id") == self.switch_data.get("id"): # Используем get для безопасности
                    main_window.map_data[active_map][list_key][i] = self.switch_data
                    break

            # Перерисовываем карту, если функция render_map существует
            if hasattr(main_window, 'render_map'):
                main_window.render_map()
            
            # Обновляем отображение статуса в окне
            self.update_status_display()
            
            # Показываем сообщение об успешном обновлении
            QMessageBox.information(self, "Инфо", "Данные обновлены")

        # Сохраняем callback для обработки ответа на пинг
        self.parent_window.pending_requests[req] = callback

    # ============================================================
    # Разное
    # ============================================================

    def copy_to_clipboard(self, text, label):
        """
        Копирует указанный текст в буфер обмена и показывает информационное сообщение.

        Args:
            text (str): Текст для копирования.
            label (str): Название копируемого элемента (для сообщения).
        """
        QApplication.clipboard().setText(text)
        QMessageBox.information(self, "Инфо", f"{label} скопирован")

    def open_details(self):
        """
        Открывает внешний веб-сайт для получения дополнительной информации о коммутаторе.
        """
        ip = self.switch_data.get("ip")
        if ip:
            import webbrowser
            # Указывается URL, где ожидается обработка IP и параметра flood
            webbrowser.open(f"http://another-site/neotools/usersonline/index.php?ip={ip}&flood=1")

    def make_label(self, text):
        """
        Создает QLabel с установленным форматом текста RichText.

        Args:
            text (str): Текст для метки.

        Returns:
            QLabel: Созданная метка QLabel.
        """
        lbl = QLabel(text)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        return lbl

    def show_message(self, text):
        """
        Отображает стандартное информационное сообщение.

        Args:
            text (str): Текст сообщения.
        """
        QMessageBox.information(self, "Инфо", text)
    
    def update_status_display(self):
        """
        Обновляет отображение статуса коммутатора в виджете self.status_label
        на основе текущих данных self.switch_data.
        """
        status = "UP" if self.switch_data.get("pingok") else "DOWN"
        status_color = "#4CAF50" if self.switch_data.get("pingok") else "#F44336"
        self.status_label.setText(f"<b>Статус:</b> <span style='color:{status_color}'>{status}</span>")
    
    def mousePressEvent(self, event):
        """
        Обрабатывает клик мыши в диалоге.
        Закрывает окно при клике в пустом месте.
        """
        # Проверяем, произошел ли клик вне виджетов
        widget = self.childAt(event.pos())
        if widget is None or widget == self:
            # Клик в пустом месте - закрываем окно
            self.close()
        else:
            # Передаем событие дальше
            super().mousePressEvent(event)
