# switch_edit_dialog.py
# Диалог редактирования свитча - ОБНОВЛЕНО
# Автор: E1 / AI Assistant
# Обновлено: January 2025

import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QCheckBox, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QSpinBox, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt
from datetime import datetime


class SwitchEditDialog(QDialog):
    """Диалог редактирования свитча с полной функциональностью"""
    
    def __init__(self, parent=None, switch_data=None, ws_client=None):
        super().__init__(parent)
        self.parent_window = parent
        self.switch_data = switch_data or {}
        self.ws_client = ws_client
        
        self.setWindowTitle("Редактирование свитча")
        self.setMinimumSize(1100, 700)
        
        # Словари для хранения загруженных данных
        self.models_list = []
        self.masters_list = []
        self.pending_requests = {}
        self.ports_count = 24  # По умолчанию
        
        self.init_ui()
        self.load_models()
        self.load_masters()
        self.load_data()
        self.apply_styles()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout()
        
        # === ВЕРХНЯЯ ЧАСТЬ: Чекбоксы и основные поля ===
        top_section = QHBoxLayout()
        
        # Левая колонка: Чекбоксы и поле "Имя"
        left_column = QVBoxLayout()
        
        # Чекбоксы
        checkbox_layout = QHBoxLayout()
        self.not_installed_cb = QCheckBox("Не установлен")
        self.not_configured_cb = QCheckBox("Недонастроен")
        self.copy_cb = QCheckBox("Копия")  # ИЗМЕНЕНО: кнопка -> чекбокс
        checkbox_layout.addWidget(self.not_installed_cb)
        checkbox_layout.addWidget(self.not_configured_cb)
        checkbox_layout.addWidget(self.copy_cb)
        checkbox_layout.addStretch()
        left_column.addLayout(checkbox_layout)
        
        # Имя - ИЗМЕНЕНО: многострочное
        name_layout = QFormLayout()
        self.name_input = QTextEdit()
        self.name_input.setMaximumHeight(60)  # ~3 строки
        name_layout.addRow(QLabel("Имя"), self.name_input)
        
        # Модель
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        name_layout.addRow(QLabel("Модель"), self.model_combo)
        
        # Питание - ИЗМЕНЕНО: однострочное
        self.power_input = QLineEdit()
        name_layout.addRow(QLabel("Питание"), self.power_input)
        
        # Локация
        self.location_input = QLineEdit()
        name_layout.addRow(QLabel("Локация"), self.location_input)
        
        # Примечание
        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(150)
        name_layout.addRow(QLabel("Примечание"), self.note_input)
        
        # Последний редактор
        self.last_editor_input = QLineEdit()
        self.last_editor_input.setReadOnly(True)
        name_layout.addRow(QLabel("Последний редактор"), self.last_editor_input)
        
        left_column.addLayout(name_layout)
        top_section.addLayout(left_column, 3)
        
        # Средняя колонка: IP, Mac, Мастер, Время реакции
        middle_column = QVBoxLayout()
        middle_form = QFormLayout()
        
        self.ip_input = QLineEdit()
        middle_form.addRow(QLabel("IP"), self.ip_input)
        
        self.mac_input = QLineEdit()
        middle_form.addRow(QLabel("Mac"), self.mac_input)
        
        self.master_combo = QComboBox()
        self.master_combo.setEditable(True)
        middle_form.addRow(QLabel("Мастер"), self.master_combo)
        
        # Время реакции (мин)
        self.reaction_time_input = QSpinBox()
        self.reaction_time_input.setRange(0, 9999)
        self.reaction_time_input.setValue(60)
        middle_form.addRow(QLabel("Время реакции (мин)"), self.reaction_time_input)
        
        middle_column.addLayout(middle_form)
        middle_column.addStretch()
        top_section.addLayout(middle_column, 2)
        
        # Правая колонка: Порты
        right_column = QVBoxLayout()
        
        # Заголовок и фильтр портов
        ports_header = QHBoxLayout()
        ports_label = QLabel("Порты")
        ports_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        # Радиокнопки фильтра
        self.filter_single_rb = QRadioButton("⊙ Построчно")
        self.filter_multiple_rb = QRadioButton("⊙ Несколько строк")
        self.filter_single_rb.setChecked(True)
        
        filter_group = QButtonGroup(self)
        filter_group.addButton(self.filter_single_rb)
        filter_group.addButton(self.filter_multiple_rb)
        
        # Кнопки управления портом
        self.add_port_btn = QPushButton("⊕")
        self.add_port_btn.setMaximumWidth(30)
        self.add_port_btn.setToolTip("Добавить порт")
        
        self.remove_port_btn = QPushButton("▬")
        self.remove_port_btn.setMaximumWidth(30)
        self.remove_port_btn.setToolTip("Удалить выбранный порт")
        
        self.bold_port_btn = QPushButton("B")
        self.bold_port_btn.setMaximumWidth(30)
        self.bold_port_btn.setToolTip("Жирный шрифт")
        
        ports_header.addWidget(ports_label)
        ports_header.addWidget(self.filter_single_rb)
        ports_header.addWidget(self.filter_multiple_rb)
        ports_header.addStretch()
        ports_header.addWidget(self.add_port_btn)
        ports_header.addWidget(self.remove_port_btn)
        ports_header.addWidget(self.bold_port_btn)
        
        right_column.addLayout(ports_header)
        
        # Таблица портов - ИЗМЕНЕНО: 2 колонки
        self.ports_table = QTableWidget()
        self.ports_table.setColumnCount(2)
        self.ports_table.setHorizontalHeaderLabels(["Порт", "Описание"])
        
        # Настройка колонок как в switch_info_dialog
        header = self.ports_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.ports_table.setColumnWidth(0, 80)  # Фиксированная ширина для "Порт"
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # "Описание" растягивается
        
        self.ports_table.verticalHeader().setVisible(False)
        self.ports_table.setMinimumHeight(500)
        
        right_column.addWidget(self.ports_table)
        top_section.addLayout(right_column, 3)
        
        main_layout.addLayout(top_section)
        
        # === НИЖНЯЯ ЧАСТЬ: Кнопки OK/Отмена ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.ok_btn = QPushButton("✓ OK")
        self.ok_btn.setMinimumWidth(100)
        self.cancel_btn = QPushButton("✗ Отмена")
        self.cancel_btn.setMinimumWidth(100)
        
        buttons_layout.addWidget(self.ok_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
        
        # Подключение сигналов
        self.ok_btn.clicked.connect(self.accept_changes)
        self.cancel_btn.clicked.connect(self.reject)
        self.add_port_btn.clicked.connect(self.add_port)
        self.remove_port_btn.clicked.connect(self.remove_port)
        self.bold_port_btn.clicked.connect(self.toggle_bold_port)
        
    def load_models(self):
        """Загрузка списка моделей из JSON через WebSocket"""
        if not self.ws_client:
            # Fallback к дефолтным значениям
            default_models = [
                "DES-3200-18 rev C",
                "DES-3200-28 rev B",
                "DGS-1100-06/ME",
                "DGS-1210-10P",
                "DGS-3120-24TC",
            ]
            self.model_combo.addItems(default_models)
            return
        
        # Запрос списка моделей
        request_id = self.ws_client.send_request(
            "file_get",
            path="data/models/models.json"
        )
        
        if request_id:
            def on_models_response(data):
                if data.get("success") and data.get("data"):
                    models_data = data.get("data", [])
                    self.models_list = models_data
                    
                    # Заполняем комбобокс
                    self.model_combo.clear()
                    for model in models_data:
                        self.model_combo.addItem(model.get("model_name", ""))
                else:
                    print(f"Ошибка загрузки моделей: {data.get('error')}")
            
            if hasattr(self.parent_window, 'pending_requests'):
                self.parent_window.pending_requests[request_id] = on_models_response
            else:
                self.pending_requests[request_id] = on_models_response
        
    def load_masters(self):
        """Загрузка списка мастеров из JSON через WebSocket"""
        if not self.ws_client:
            # Fallback к дефолтным значениям
            default_masters = [
                "Шепель А. В.",
                "Иванов И. И.",
                "Петров П. П.",
            ]
            self.master_combo.addItems(default_masters)
            return
        
        # Запрос списка мастеров
        request_id = self.ws_client.send_request(
            "file_get",
            path="data/lists/masters.json"
        )
        
        if request_id:
            def on_masters_response(data):
                if data.get("success") and data.get("data"):
                    masters_data = data.get("data", [])
                    self.masters_list = masters_data
                    
                    # Заполняем комбобокс
                    self.master_combo.clear()
                    for master in masters_data:
                        self.master_combo.addItem(master.get("fio", ""))
                else:
                    print(f"Ошибка загрузки мастеров: {data.get('error')}")
            
            if hasattr(self.parent_window, 'pending_requests'):
                self.parent_window.pending_requests[request_id] = on_masters_response
            else:
                self.pending_requests[request_id] = on_masters_response
    
    def on_model_changed(self, model_name):
        """Обработчик изменения модели - загружает количество портов"""
        if not model_name or not self.ws_client:
            return
        
        # Преобразуем имя модели в имя файла
        # "DES-3200-10 rev C" -> "DES-3200-10_rev_C"
        model_filename = model_name.replace(" ", "_")
        
        # Запрос данных модели
        request_id = self.ws_client.send_request(
            "file_get",
            path=f"data/models/model_{model_filename}.json"
        )
        
        if request_id:
            def on_model_data_response(data):
                if data.get("success") and data.get("data"):
                    model_data = data.get("data", {})
                    # Получаем ports_count как строку и конвертируем в int
                    ports_count_str = model_data.get("ports_count", "24")
                    try:
                        ports_count = int(ports_count_str)
                    except (ValueError, TypeError):
                        ports_count = 24
                    
                    # Обновляем количество портов в таблице
                    self.ports_count = ports_count
                    self.update_ports_table_structure()
                else:
                    print(f"Ошибка загрузки данных модели: {data.get('error')}")
            
            if hasattr(self.parent_window, 'pending_requests'):
                self.parent_window.pending_requests[request_id] = on_model_data_response
            else:
                self.pending_requests[request_id] = on_model_data_response
    
    def update_ports_table_structure(self):
        """Обновляет структуру таблицы портов при изменении модели"""
        current_rows = self.ports_table.rowCount()
        
        if self.ports_count != current_rows:
            # Сохраняем текущие данные портов
            current_ports = {}
            for row in range(current_rows):
                port_item = self.ports_table.item(row, 0)
                desc_item = self.ports_table.item(row, 1)
                if port_item and desc_item:
                    port_num = port_item.text()
                    if port_num:
                        # Сохраняем цвет и жирность описания
                        color = desc_item.foreground().color().name()
                        bold = desc_item.font().bold()
                        current_ports[port_num] = {
                            'description': desc_item.text(),
                            'color': color,
                            'bold': bold
                        }
            
            # Устанавливаем новое количество строк
            self.ports_table.setRowCount(self.ports_count)
            
            # Заполняем порты
            for i in range(self.ports_count):
                port_num = str(i + 1)
                
                # Колонка "Порт" - всегда стандартный цвет
                port_item = QTableWidgetItem(port_num)
                self.ports_table.setItem(i, 0, port_item)
                
                # Колонка "Описание"
                if port_num in current_ports:
                    desc_item = QTableWidgetItem(current_ports[port_num]['description'])
                    
                    # Применяем цвет
                    desc_item.setForeground(QColor(current_ports[port_num]['color']))
                    
                    # Применяем жирность
                    if current_ports[port_num]['bold']:
                        font = desc_item.font()
                        font.setBold(True)
                        desc_item.setFont(font)
                else:
                    desc_item = QTableWidgetItem("")
                    desc_item.setForeground(QColor("#FFC107"))
                
                self.ports_table.setItem(i, 1, desc_item)
    
    def load_data(self):
        """Загрузка данных свитча в форму"""
        if not self.switch_data:
            return
            
        # Чекбоксы
        self.not_installed_cb.setChecked(self.switch_data.get("notinstalled") == "-1")
        self.not_configured_cb.setChecked(self.switch_data.get("notsettings") == "-1")
        
        # НОВОЕ: Чекбокс "Копия" - загрузка из copyid
        copy_id = self.switch_data.get("copyid", "none")
        self.copy_cb.setChecked(copy_id != "none" and copy_id != "")
        
        # Основные поля
        self.name_input.setPlainText(self.switch_data.get("name", ""))  # ИЗМЕНЕНО: QTextEdit
        self.ip_input.setText(self.switch_data.get("ip", ""))
        self.mac_input.setText(self.switch_data.get("mac", ""))
        
        # Модель
        model = self.switch_data.get("model", "")
        if model:
            index = self.model_combo.findText(model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            else:
                self.model_combo.setCurrentText(model)
            
            # ИСПРАВЛЕНО: Загружаем количество портов из модели перед загрузкой портов
            self.load_model_ports_count(model)
        else:
            # Если модели нет, загружаем порты сразу
            self.load_ports_from_data()
        
        # Мастер
        master = self.switch_data.get("master", "")
        if master:
            index = self.master_combo.findText(master)
            if index >= 0:
                self.master_combo.setCurrentIndex(index)
            else:
                self.master_combo.setCurrentText(master)
        
        # Остальные поля
        self.power_input.setText(self.switch_data.get("power", ""))  # ИЗМЕНЕНО: QLineEdit
        self.location_input.setText(self.switch_data.get("location", ""))
        self.reaction_time_input.setValue(int(self.switch_data.get("reaction_time", 60)))
        self.note_input.setPlainText(self.switch_data.get("note", ""))
        self.last_editor_input.setText(self.switch_data.get("last_editor", ""))
    
    def load_model_ports_count(self, model_name):
        """Загружает количество портов из файла модели перед загрузкой данных"""
        if not model_name or not self.ws_client:
            # Если нет модели или ws_client, загружаем порты сразу
            self.load_ports_from_data()
            return
        
        # Преобразуем имя модели в имя файла
        model_filename = model_name.replace(" ", "_")
        model_filename = re.sub(r'[^\w.-]', '_', model_filename)
        
        # Запрос данных модели
        request_id = self.ws_client.send_request(
            "file_get",
            path=f"data/models/model_{model_filename}.json"
        )
        
        if request_id:
            def on_model_data_response(data):
                if data.get("success") and data.get("data"):
                    model_data = data.get("data", {})
                    ports_count_str = model_data.get("ports_count", "24")
                    try:
                        self.ports_count = int(ports_count_str)
                    except (ValueError, TypeError):
                        self.ports_count = 24
                
                # После получения количества портов загружаем порты
                self.load_ports_from_data()
            
            if hasattr(self.parent_window, 'pending_requests'):
                self.parent_window.pending_requests[request_id] = on_model_data_response
            else:
                self.pending_requests[request_id] = on_model_data_response
        else:
            # Если не удалось отправить запрос, загружаем порты сразу
            self.load_ports_from_data()
    
    def load_ports_from_data(self):
        """Загружает порты из данных свитча, показывая ВСЕ порты"""
        ports = self.switch_data.get("ports", [])
        
        # Создаем словарь портов для быстрого поиска
        ports_dict = {}
        max_port_num = 0
        
        for port in ports:
            # Поддержка как "number", так и "port_num"
            port_num_str = str(port.get("number", port.get("port_num", "")))
            if port_num_str:
                ports_dict[port_num_str] = port
                # Пытаемся извлечь числовую часть для определения максимума
                try:
                    # Извлекаем число из строки типа "17м"
                    num_match = re.match(r'(\d+)', port_num_str)
                    if num_match:
                        num = int(num_match.group(1))
                        max_port_num = max(max_port_num, num)
                except (ValueError, AttributeError):
                    pass
        
        # Используем количество портов из модели, но не меньше максимального из данных
        if max_port_num > self.ports_count:
            self.ports_count = max_port_num
        
        # Устанавливаем количество строк
        self.ports_table.setRowCount(self.ports_count)
        
        # Заполняем ВСЕ порты
        for i in range(self.ports_count):
            port_num = str(i + 1)
            
            # Колонка "Порт" - всегда стандартный цвет
            port_item = QTableWidgetItem(port_num)
            self.ports_table.setItem(i, 0, port_item)
            
            # Колонка "Описание"
            port_data = ports_dict.get(port_num, None)
            
            if port_data:
                # Порт с данными
                description = port_data.get("description", "")
                color = port_data.get("color", "#FFC107")
                bold = port_data.get("bold", False)
                
                desc_item = QTableWidgetItem(description)
                
                # ИСПРАВЛЕНО: Применяем цвет только к описанию
                desc_item.setForeground(QColor(color))
                
                # ИСПРАВЛЕНО: Применяем жирность только к описанию
                if bold:
                    font = desc_item.font()
                    font.setBold(True)
                    desc_item.setFont(font)
            else:
                # Порт без данных - пустое описание
                desc_item = QTableWidgetItem("")
                desc_item.setForeground(QColor("#FFC107"))
            
            self.ports_table.setItem(i, 1, desc_item)
    
    def validate_ip(self, ip):
        """Валидация IP-адреса"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    def validate_mac(self, mac):
        """Валидация MAC-адреса"""
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$|^[0-9A-Fa-f]{12}$'
        return re.match(pattern, mac) is not None
    
    def accept_changes(self):
        """Валидация и сохранение изменений"""
        # Валидация IP
        ip = self.ip_input.text().strip()
        if ip and not self.validate_ip(ip):
            QMessageBox.warning(self, "Ошибка", "Неверный формат IP-адреса")
            self.ip_input.setFocus()
            return
        
        # Валидация MAC
        mac = self.mac_input.text().strip()
        if mac and not self.validate_mac(mac):
            QMessageBox.warning(self, "Ошибка", "Неверный формат MAC-адреса")
            self.mac_input.setFocus()
            return
        
        # Сохранение данных
        self.save_data()
        self.accept()
    
    def save_data(self):
        """Сохранение данных"""
        # Чекбоксы
        self.switch_data["notinstalled"] = "-1" if self.not_installed_cb.isChecked() else "0"
        self.switch_data["notsettings"] = "-1" if self.not_configured_cb.isChecked() else "0"
        
        # НОВОЕ: Сохранение состояния чекбокса "Копия"
        if self.copy_cb.isChecked():
            # Если copyid еще не установлен, создаем новый
            if self.switch_data.get("copyid", "none") in ["none", ""]:
                import uuid
                self.switch_data["copyid"] = str(uuid.uuid4())
        else:
            self.switch_data["copyid"] = "none"
        
        # Основные поля
        self.switch_data["name"] = self.name_input.toPlainText().strip()  # ИЗМЕНЕНО: QTextEdit
        self.switch_data["ip"] = self.ip_input.text().strip()
        self.switch_data["mac"] = self.mac_input.text().strip()
        self.switch_data["model"] = self.model_combo.currentText().strip()
        self.switch_data["master"] = self.master_combo.currentText().strip()
        self.switch_data["power"] = self.power_input.text().strip()  # ИЗМЕНЕНО: QLineEdit
        self.switch_data["location"] = self.location_input.text().strip()
        self.switch_data["reaction_time"] = str(self.reaction_time_input.value())
        self.switch_data["note"] = self.note_input.toPlainText().strip()
        
        # Обновление последнего редактора и времени
        if hasattr(self.parent_window, 'current_user'):
            self.switch_data["last_editor"] = self.parent_window.current_user
        self.switch_data["mod_time"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # ИСПРАВЛЕНО: Сохранение ВСЕХ портов с их атрибутами
        ports = []
        for i in range(self.ports_table.rowCount()):
            port_item = self.ports_table.item(i, 0)
            desc_item = self.ports_table.item(i, 1)
            
            if port_item and desc_item:
                port_num_text = port_item.text().strip()
                desc_text = desc_item.text().strip()
                
                # Сохраняем порт, если есть номер
                if port_num_text:
                    # Получаем цвет и жирность из описания
                    color = desc_item.foreground().color().name()
                    font = desc_item.font()
                    is_bold = font.bold()
                    
                    port_data = {
                        "number": port_num_text,
                        "description": desc_text
                    }
                    
                    # Добавляем цвет, если он не по умолчанию
                    if color != "#ffc107":  # Qt возвращает в нижнем регистре
                        port_data["color"] = color.upper()
                    
                    # Добавляем bold, если установлен
                    if is_bold:
                        port_data["bold"] = True
                    
                    ports.append(port_data)
        
        self.switch_data["ports"] = ports
    
    def add_port(self):
        """Добавление нового порта"""
        row = self.ports_table.rowCount()
        self.ports_table.insertRow(row)
        
        # Колонка "Порт"
        port_item = QTableWidgetItem(str(row + 1))
        self.ports_table.setItem(row, 0, port_item)
        
        # Колонка "Описание"
        desc_item = QTableWidgetItem("")
        desc_item.setForeground(QColor("#FFC107"))
        self.ports_table.setItem(row, 1, desc_item)
        
        self.ports_table.editItem(desc_item)
    
    def remove_port(self):
        """Удаление выбранного порта"""
        current_row = self.ports_table.currentRow()
        if current_row >= 0:
            # Очищаем содержимое обеих колонок
            port_item = self.ports_table.item(current_row, 0)
            desc_item = self.ports_table.item(current_row, 1)
            
            if desc_item:
                desc_item.setText("")
                desc_item.setForeground(QColor("#FFC107"))
                # Убираем жирность
                font = desc_item.font()
                font.setBold(False)
                desc_item.setFont(font)
    
    def toggle_bold_port(self):
        """Переключение жирного шрифта для выбранного порта"""
        current_row = self.ports_table.currentRow()
        if current_row >= 0:
            # ИСПРАВЛЕНО: Применяем жирный шрифт ТОЛЬКО к описанию (колонка 1)
            desc_item = self.ports_table.item(current_row, 1)
            if desc_item:
                font = desc_item.font()
                font.setBold(not font.bold())
                desc_item.setFont(font)
    
    def apply_styles(self):
        """Применение стилей в стиле приложения"""
        self.setStyleSheet("""
            QDialog {
                background-color: #333;
                color: #FFC107;
                border: 1px solid #FFC107;
            }
            
            QLabel {
                color: #FFC107;
                font-size: 12px;
            }
            
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #444;
                color: #FFC107;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
            
            QLineEdit:read-only {
                background-color: #3a3a3a;
                color: #888;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
            }
            
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                background-color: #555;
            }
            
            QCheckBox, QRadioButton {
                color: #FFC107;
                font-size: 12px;
                spacing: 5px;
            }
            
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #444;
            }
            
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #FFC107;
            }
            
            QPushButton {
                background-color: #444;
                color: #FFC107;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: #555;
                border: 1px solid #FFC107;
            }
            
            QPushButton:pressed {
                background-color: #FFC107;
                color: #333;
            }
            
            QTableWidget {
                background-color: #444;
                color: #FFC107;
                border: 1px solid #555;
                gridline-color: #555;
            }
            
            QTableWidget::item {
                padding: 4px;
            }
            
            QTableWidget::item:selected {
                background-color: #75736b;
                color: #FFC107;
            }
            
            QHeaderView::section {
                background-color: #333;
                color: #FFC107;
                border: 1px solid #555;
                padding: 4px;
                font-weight: bold;
            }
            
            QScrollBar:vertical {
                background-color: #333;
                width: 12px;
                border: 1px solid #555;
            }
            
            QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 4px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #FFC107;
            }
        """)

    def get_data(self):
        """Получение сохраненных данных"""
        return self.switch_data
