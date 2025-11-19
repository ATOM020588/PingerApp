# globals_dialog.py - Диалог управления глобальными неисправностями
# Дата: Декабрь 2024
# Обновлено: с новым дизайном окон и цветовой индикацией, загрузкой инженеров

import csv
import os
import uuid
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QLineEdit, QTextEdit,
    QComboBox, QMessageBox, QFileDialog, QRadioButton, QButtonGroup,
    QSpinBox, QDateTimeEdit, QFormLayout, QGroupBox
)
from PyQt6.QtCore import Qt, QDateTime, QTimer
from PyQt6.QtGui import QColor

# Цветовая схема типов проблем
SEVERITY_COLORS = {
    "Информация": "#ADD8E6",      # Светло-голубой
    "Предупреждение": "#FFFF99",  # Желтый
    "Средняя": "#FFB366",          # Оранжевый
    "Высокая": "#FFB3BA",          # Розовый
    "Чрезвычайная": "#FF0000"     # Красный
}

class AddIssueDialog(QDialog):
    """Диалог добавления/редактирования неисправности"""
    def __init__(self, parent=None, issue_data=None, device_info=None, device_history=None, ws_client=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить глобальную проблему" if not issue_data else "Редактировать неисправность")
        self.setFixedSize(1200, 750)
        self.issue_data = issue_data
        self.device_info = device_info
        self.device_history = device_history or []
        self.ws_client = ws_client
        self.engineers_list = []
        self.parent_window = parent

        # Основной layout
        main_layout = QHBoxLayout()
        
        # Левая часть (основные поля)
        left_layout = QVBoxLayout()

        # Загружаем инженеров с сервера
        self.load_engineers()

        # === ВЕРХНЯЯ ПАНЕЛЬ: Дата, Мастер, Время реакции, Начало работ ===
        top_panel = QHBoxLayout()

        # Дата Время
        datetime_group = QVBoxLayout()
        datetime_label = QLabel("Дата Время")
        datetime_label.setStyleSheet("color: #FFC107; font-weight: bold; font-size: 12px;")
        datetime_group.addWidget(datetime_label)
        self.datetime_input = QDateTimeEdit()
        self.datetime_input.setCalendarPopup(True)
        self.datetime_input.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.datetime_input.setFixedWidth(150)
        if issue_data:
            # Парсим дату из строки
            date_str = issue_data.get("date", "")
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    self.datetime_input.setDateTime(QDateTime(dt))
                except:
                    self.datetime_input.setDateTime(QDateTime.currentDateTime())
            else:
                self.datetime_input.setDateTime(QDateTime.currentDateTime())
        else:
            self.datetime_input.setDateTime(QDateTime.currentDateTime())
        datetime_group.addWidget(self.datetime_input)
        top_panel.addLayout(datetime_group)

        # Мастер
        master_group = QVBoxLayout()
        master_label = QLabel("Мастер")
        master_label.setStyleSheet("color: #FFC107; font-weight: bold; font-size: 12px;")
        master_group.addWidget(master_label)
        self.master_input = QComboBox()
        self.master_input.setEditable(True)
        self.master_input.setFixedWidth(200)
        # Заполним список после загрузки инженеров
        if issue_data:
            self.master_input.setCurrentText(issue_data.get("master", ""))
        master_group.addWidget(self.master_input)
        top_panel.addLayout(master_group)

        # Время реакции (мин)
        reaction_group = QVBoxLayout()
        reaction_label = QLabel("Время реакции (мин)")
        reaction_label.setStyleSheet("color: #FFC107; font-weight: bold; font-size: 12px;")
        reaction_group.addWidget(reaction_label)
        self.reaction_time_input = QSpinBox()
        self.reaction_time_input.setRange(0, 999)
        self.reaction_time_input.setFixedWidth(100)
        if issue_data:
            self.reaction_time_input.setValue(int(issue_data.get("reaction_time", 60)))
        else:
            self.reaction_time_input.setValue(60)
        reaction_group.addWidget(self.reaction_time_input)
        top_panel.addLayout(reaction_group)

        # Начало работ
        work_start_group = QVBoxLayout()
        work_start_label = QLabel("Начало работ")
        work_start_label.setStyleSheet("color: #FFC107; font-weight: bold; font-size: 12px;")
        work_start_group.addWidget(work_start_label)
        self.work_start_input = QLineEdit()
        self.work_start_input.setFixedWidth(150)
        if issue_data:
            self.work_start_input.setText(issue_data.get("work_start", ""))
        work_start_group.addWidget(self.work_start_input)
        top_panel.addLayout(work_start_group)

        top_panel.addStretch()

        left_layout.addLayout(top_panel)

        # === ОПИСАНИЕ ПРОБЛЕМЫ ===
        layout.addWidget(QLabel("Описание проблемы"))
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        if issue_data:
            self.description_input.setPlainText(issue_data.get("description", ""))
        elif device_info:
            device_name = device_info.get("name", "")
            device_ip = device_info.get("ip", "")
            self.description_input.setPlainText(f"{device_ip} ({device_name}) down")
        layout.addWidget(self.description_input)

        # === СРЕДНЯЯ ПАНЕЛЬ: Типы проблем (радиокнопки) ===
        severity_panel = QHBoxLayout()

        self.severity_group = QButtonGroup(self)
        severity_types = [
            ("Информация", "#ADD8E6"),
            ("Предупреждение", "#FFFF99"),
            ("Средняя", "#FFB366"),
            ("Высокая", "#FFB3BA"),
            ("Чрезвычайная", "#FF0000")
        ]

        for severity_name, color in severity_types:
            radio = QRadioButton(severity_name)
            radio.setStyleSheet(f"""
                QRadioButton {{
                    background-color: {color};
                    color: #000000;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                QRadioButton::indicator {{
                    width: 20px;
                    height: 20px;
                }}
            """)
            self.severity_group.addButton(radio)
            severity_panel.addWidget(radio)

            # Устанавливаем значение по умолчанию
            if issue_data and issue_data.get("severity_type") == severity_name:
                radio.setChecked(True)
            elif not issue_data and severity_name == "Высокая":
                radio.setChecked(True)

        layout.addLayout(severity_panel)

        # === ИСТОРИЯ ===
        layout.addWidget(QLabel("История"))
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["Дата", "Описание", "Решение"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setMaximumHeight(200)

        # Загружаем историю устройства
        self.populate_history()

        layout.addWidget(self.history_table)

        # === КНОПКИ ===
        buttons = QHBoxLayout()

        ok_button = QPushButton("✓ OK")
        ok_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")

        cancel_button = QPushButton("✗ Отмена")
        cancel_button.setStyleSheet("background-color: #f44336; color: white; padding: 10px; font-weight: bold;")

        add_to_button = QPushButton("Добавить к")
        add_to_button.setStyleSheet("padding: 10px;")

        edit_data_button = QPushButton("Изменить данные")
        edit_data_button.setStyleSheet("padding: 10px;")

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        add_to_button.clicked.connect(self.add_to_existing)
        edit_data_button.clicked.connect(self.enable_edit_mode)

        buttons.addStretch()
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        buttons.addWidget(add_to_button)
        buttons.addWidget(edit_data_button)

        layout.addLayout(buttons)

        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-weight: bold; }
            QLineEdit, QTextEdit, QSpinBox, QComboBox, QDateTimeEdit {
                background-color: #444;
                color: #FFC107;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
            QTableWidget {
                background-color: #444;
                color: #000000;
                border: 1px solid #555;
            }
            QHeaderView::section {
                background-color: #333;
                color: #FFC107;
                border: 1px solid #555;
                padding: 5px;
            }
            QPushButton {
                background-color: #444;
                color: #FFC107;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #555; }
        """)

    def load_engineers(self):
        """ИСПРАВЛЕНО: Загружает список инженеров с сервера"""
        if not self.ws_client:
            # Fallback на дефолтные значения
            self.engineers_list = ["Вельковский К. А.", "Третяк А. В.", "Другой"]
            self.master_input.addItems(self.engineers_list)
            return

        request_id = self.ws_client.send_request("file_get", path="lists/engineers.json")

        if request_id:
            def on_response(data):
                if data.get("success"):
                    engineers_data = data.get("data", [])
                    # Извлекаем ФИО из структуры
                    self.engineers_list = [eng.get("fio", "") for eng in engineers_data if eng.get("fio")]
                    self.master_input.clear()
                    self.master_input.addItems(self.engineers_list)
                else:
                    # Fallback
                    self.engineers_list = ["Вельковский К. А.", "Третяк А. В.", "Другой"]
                    self.master_input.addItems(self.engineers_list)

            # ИСПРАВЛЕНО: Сохраняем callback в parent_window вместо parent()
            if self.parent_window and hasattr(self.parent_window, 'pending_requests'):
                self.parent_window.pending_requests[request_id] = on_response
            else:
                # Если нет pending_requests, используем QTimer для отложенной загрузки
                print("Warning: No pending_requests found, using fallback engineers list")
                self.engineers_list = ["Вельковский К. А.", "Третяк А. В.", "Другой"]
                QTimer.singleShot(0, lambda: self.master_input.addItems(self.engineers_list))

    def populate_history(self):
        """Заполняет таблицу историей предыдущих инцидентов"""
        self.history_table.setRowCount(len(self.device_history))

        for row, history_item in enumerate(self.device_history):
            # Дата
            date_item = QTableWidgetItem(history_item.get("date", ""))
            date_item.setForeground(QColor("#000000"))
            self.history_table.setItem(row, 0, date_item)

            # Описание
            desc_item = QTableWidgetItem(history_item.get("description", ""))
            desc_item.setForeground(QColor("#000000"))
            self.history_table.setItem(row, 1, desc_item)

            # Решение
            resolution_item = QTableWidgetItem(history_item.get("resolution", ""))
            resolution_item.setForeground(QColor("#000000"))
            self.history_table.setItem(row, 2, resolution_item)

            # Цветовая индикация по типу
            severity = history_item.get("severity_type", "Информация")
            color = SEVERITY_COLORS.get(severity, "#FFFFFF")
            for col in range(3):
                if self.history_table.item(row, col):
                    self.history_table.item(row, col).setBackground(QColor(color))

    def add_to_existing(self):
        """Открывает диалог выбора существующей неисправности для объединения"""
        # TODO: Реализовать выбор существующей неисправности
        QMessageBox.information(self, "Добавить к", "Функция объединения неисправностей в разработке")

    def enable_edit_mode(self):
        """Включает режим редактирования"""
        # Разблокируем все поля
        self.datetime_input.setEnabled(True)
        self.master_input.setEnabled(True)
        self.reaction_time_input.setEnabled(True)
        self.work_start_input.setEnabled(True)
        self.description_input.setEnabled(True)
        QMessageBox.information(self, "Режим редактирования", "Редактирование включено")

    def get_data(self):
        """Возвращает данные из формы"""
        # Определяем выбранный тип проблемы
        severity_type = "Высокая"  # По умолчанию
        for button in self.severity_group.buttons():
            if button.isChecked():
                severity_type = button.text()
                break

        data = {
            "date": self.datetime_input.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "description": self.description_input.toPlainText().strip(),
            "master": self.master_input.currentText().strip(),
            "reaction_time": str(self.reaction_time_input.value()),
            "work_start": self.work_start_input.text().strip(),
            "severity_type": severity_type
        }

        # Добавляем информацию об устройстве, если есть
        if self.device_info:
            data["device_type"] = self.device_info.get("type", "")
            data["device_id"] = self.device_info.get("id", "")
            data["device_name"] = self.device_info.get("name", "")
            data["device_ip"] = self.device_info.get("ip", "")

        return data

class AddCallDialog(QDialog):
    """ИСПРАВЛЕНО: Диалог добавления звонка к существующей неисправности - УБРАНЫ КНОПКИ"""
    def __init__(self, parent=None, issue_id=None, device_info=None, ws_client=None):
        super().__init__(parent)
        self.setWindowTitle("📞 Добавить звонок")
        self.setFixedSize(1000, 600)
        self.issue_id = issue_id
        self.device_info = device_info
        self.ws_client = ws_client
        self.engineers_list = []
        self.parent_window = parent

        layout = QVBoxLayout()

        # Загружаем инженеров с сервера
        self.load_engineers()

        # === ВЕРХНЯЯ ПАНЕЛЬ ===
        top_panel = QHBoxLayout()

        # Сортировка по мастеру / Техник
        master_group = QVBoxLayout()
        master_group.addWidget(QLabel("Техник"))
        self.master_combo = QComboBox()
        self.master_combo.setEditable(True)
        master_group.addWidget(self.master_combo)
        top_panel.addLayout(master_group)

        # Кто звонил / Кому звонили
        caller_group = QVBoxLayout()
        caller_group.addWidget(QLabel("Кто звонил / Кому звонили"))
        self.caller_input = QComboBox()
        self.caller_input.setEditable(True)
        caller_group.addWidget(self.caller_input)
        top_panel.addLayout(caller_group)

        # Начало работ
        work_start_group = QVBoxLayout()
        work_start_group.addWidget(QLabel("Начало работ"))
        self.work_start_input = QLineEdit()
        work_start_group.addWidget(self.work_start_input)
        top_panel.addLayout(work_start_group)

        layout.addLayout(top_panel)

        # === ИСПРАВЛЕНО: КНОПКИ "СВИТЧ ЛЕЖИТ" И "ПОРТЫ С ПРОБЛЕМАМИ" УБРАНЫ ===
        # Эти кнопки теперь находятся в контекстном меню canvas

        # === ОСНОВНАЯ ОБЛАСТЬ: Информация + Радиокнопки справа ===
        middle_panel = QHBoxLayout()

        # Информация переданная / полученная (большое поле слева)
        info_group = QVBoxLayout()
        info_group.addWidget(QLabel("Информация переданная / полученная"))
        self.info_input = QTextEdit()
        self.info_input.setMinimumHeight(300)
        info_group.addWidget(self.info_input)
        middle_panel.addLayout(info_group, 3)  # Занимает 3/4 ширины

        # Радиокнопки типа звонка (справа)
        call_type_group = QVBoxLayout()
        self.call_type_buttons = QButtonGroup(self)

        call_types = ["Передача", "Новая инфа", "Недозвон", "Инфо", "Отзвон", "Закрытие"]
        for call_type in call_types:
            radio = QRadioButton(call_type)
            radio.setStyleSheet("padding: 8px; font-size: 14px; color: #FFC107;")
            self.call_type_buttons.addButton(radio)
            call_type_group.addWidget(radio)
            if call_type == "Отзвон":
                radio.setChecked(True)

        call_type_group.addStretch()
        middle_panel.addLayout(call_type_group, 1)  # Занимает 1/4 ширины

        layout.addLayout(middle_panel)

        # === НИЖНЯЯ ПАНЕЛЬ: Приоритет (цветные радиокнопки) ===
        priority_panel = QHBoxLayout()
        self.priority_group = QButtonGroup(self)

        priorities = [
            ("Информация", "#ADD8E6"),
            ("Предупреждение", "#FFFF99"),
            ("Средняя", "#FFB366"),
            ("Высокая", "#FFB3BA"),
            ("Чрезвычайная", "#FF0000")
        ]

        for priority_name, color in priorities:
            radio = QRadioButton(priority_name)
            radio.setStyleSheet(f"""
                QRadioButton {{
                    background-color: {color};
                    color: #000000;
                    padding: 12px;
                    border-radius: 5px;
                    font-weight: bold;
                }}
            """)
            self.priority_group.addButton(radio)
            priority_panel.addWidget(radio)
            if priority_name == "Чрезвычайная":
                radio.setChecked(True)

        layout.addLayout(priority_panel)

        # === КНОПКИ ===
        buttons = QHBoxLayout()

        ok_button = QPushButton("✓ OK")
        ok_button.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-weight: bold; min-width: 120px;")

        cancel_button = QPushButton("✗ Cancel")
        cancel_button.setStyleSheet("background-color: #f44336; color: white; padding: 12px; font-weight: bold; min-width: 120px;")

        history_button = QPushButton("История")
        history_button.setStyleSheet("background-color: #888; color: white; padding: 12px; min-width: 120px;")

        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        history_button.clicked.connect(self.show_history)

        buttons.addStretch()
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        buttons.addWidget(history_button)

        layout.addLayout(buttons)

        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; font-weight: bold; }
            QLineEdit, QTextEdit, QComboBox {
                background-color: #444;
                color: #FFC107;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                border-radius: 4px;
            }
            QPushButton:hover { opacity: 0.8; }
        """)

    def load_engineers(self):
        """ИСПРАВЛЕНО: Загружает список инженеров с сервера"""
        if not self.ws_client:
            # Fallback на дефолтные значения
            self.engineers_list = ["Третяк А. В.", "Вельковский К. А.", "Другой"]
            self.master_combo.addItems(self.engineers_list)
            return

        request_id = self.ws_client.send_request("file_get", path="lists/engineers.json")

        if request_id:
            def on_response(data):
                if data.get("success"):
                    engineers_data = data.get("data", [])
                    # Извлекаем ФИО из структуры
                    self.engineers_list = [eng.get("fio", "") for eng in engineers_data if eng.get("fio")]
                    self.master_combo.clear()
                    self.master_combo.addItems(self.engineers_list)
                else:
                    # Fallback
                    self.engineers_list = ["Третяк А. В.", "Вельковский К. А.", "Другой"]
                    self.master_combo.addItems(self.engineers_list)

            # ИСПРАВЛЕНО: Сохраняем callback в parent_window вместо parent()
            if self.parent_window and hasattr(self.parent_window, 'pending_requests'):
                self.parent_window.pending_requests[request_id] = on_response
            else:
                # Если нет pending_requests, используем QTimer для отложенной загрузки
                print("Warning: No pending_requests found, using fallback engineers list")
                self.engineers_list = ["Третяк А. В.", "Вельковский К. А.", "Другой"]
                QTimer.singleShot(0, lambda: self.master_combo.addItems(self.engineers_list))

    def show_history(self):
        """Показывает историю звонков"""
        QMessageBox.information(self, "История", "История звонков будет здесь")

    def get_data(self):
        """Возвращает данные о звонке"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Определяем тип звонка
        call_type = "Отзвон"
        for button in self.call_type_buttons.buttons():
            if button.isChecked():
                call_type = button.text()
                break

        # Определяем приоритет
        priority = "Чрезвычайная"
        for button in self.priority_group.buttons():
            if button.isChecked():
                priority = button.text()
                break

        data = {
            "timestamp": timestamp,
            "master": self.master_combo.currentText(),
            "caller": self.caller_input.currentText(),
            "work_start": self.work_start_input.text(),
            "type": call_type,
            "priority": priority,
            "info": self.info_input.toPlainText().strip()
        }

        # Добавляем информацию об устройстве
        if self.device_info:
            data["device_type"] = self.device_info.get("type", "")
            data["device_id"] = self.device_info.get("id", "")
            data["device_name"] = self.device_info.get("name", "")
            data["device_ip"] = self.device_info.get("ip", "")

        return data

class GlobalIssuesDialog(QDialog):
    """Главный диалог управления глобальными неисправностями"""
    def __init__(self, parent=None, ws_client=None):
        super().__init__(parent)
        self.setWindowTitle("Глобальные неисправности")
        self.setFixedSize(1400, 700)
        self.ws_client = ws_client
        self.parent_window = parent
        self.issues = []

        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Глобальные неисправности")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFC107; padding: 10px;")
        layout.addWidget(title)

        # Таблица (УБРАНЫ КОЛОНКИ "Устройство" и "IP")
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "Описание проблемы", "Заявки", "Мастер", "Исполнитель",
            "Создана", "Передана", "Отзвон", "Начало работ", "История звонков"
        ])

        # Настройка ширины колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Дата
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Описание
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Заявки
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Мастер
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Исполнитель

        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Кнопки управления
        buttons = QHBoxLayout()
        add_button = QPushButton("Добавить")
        edit_button = QPushButton("Редактировать")
        delete_button = QPushButton("Удалить")
        add_call_button = QPushButton("Добавить звонок")
        export_button = QPushButton("Экспорт CSV")
        refresh_button = QPushButton("Обновить")
        close_button = QPushButton("Закрыть")

        add_button.clicked.connect(self.add_issue)
        edit_button.clicked.connect(self.edit_issue)
        delete_button.clicked.connect(self.delete_issue)
        add_call_button.clicked.connect(self.add_call_to_issue)
        export_button.clicked.connect(self.export_csv)
        refresh_button.clicked.connect(self.load_issues)
        close_button.clicked.connect(self.accept)

        buttons.addWidget(add_button)
        buttons.addWidget(edit_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(add_call_button)
        buttons.addWidget(export_button)
        buttons.addWidget(refresh_button)
        buttons.addStretch()
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; }
            QTableWidget { background-color: #444; color: #000000; border: 1px solid #555; }
            QTableWidget::item:hover { background-color: #555; }
            QTableWidget::item:selected { background-color: #75736b; color: #000000; }
            QHeaderView::section { background-color: #333; color: #FFC107; border: 1px solid #555; padding: 5px; }
            QPushButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)

        # Загружаем данные
        self.load_issues()

    def load_issues(self):
        """Загружает список неисправностей с сервера"""
        if not self.ws_client or not self.parent_window:
            self.show_message("Нет связи с сервером", "error")
            return

        request_id = self.ws_client.send_request("csv_read", path="globals/issues.csv")

        if request_id:
            def on_response(data):
                if data.get("success"):
                    self.issues = data.get("data", [])
                    self.populate_table()
                else:
                    # Если файл не найден, создаем пустую таблицу
                    self.issues = []
                    self.populate_table()

            self.parent_window.pending_requests[request_id] = on_response

    def populate_table(self):
        """Заполняет таблицу данными С ЦВЕТОВОЙ ИНДИКАЦИЕЙ И ЧЕРНЫМ ТЕКСТОМ"""
        self.table.setRowCount(len(self.issues))

        for row, issue in enumerate(self.issues):
            # ID
            item0 = QTableWidgetItem(str(issue.get("id", "")))
            item0.setForeground(QColor("#000000"))
            self.table.setItem(row, 0, item0)

            # Дата
            item1 = QTableWidgetItem(issue.get("date", ""))
            item1.setForeground(QColor("#000000"))
            self.table.setItem(row, 1, item1)

            # Описание
            item2 = QTableWidgetItem(issue.get("description", ""))
            item2.setForeground(QColor("#000000"))
            self.table.setItem(row, 2, item2)

            # Заявки
            item3 = QTableWidgetItem(issue.get("tickets", ""))
            item3.setForeground(QColor("#000000"))
            self.table.setItem(row, 3, item3)

            # Мастер
            item4 = QTableWidgetItem(issue.get("master", ""))
            item4.setForeground(QColor("#000000"))
            self.table.setItem(row, 4, item4)

            # Исполнитель
            item5 = QTableWidgetItem(issue.get("executor", ""))
            item5.setForeground(QColor("#000000"))
            self.table.setItem(row, 5, item5)

            # Создана
            item6 = QTableWidgetItem(issue.get("created", ""))
            item6.setForeground(QColor("#000000"))
            self.table.setItem(row, 6, item6)

            # Передана
            item7 = QTableWidgetItem(issue.get("transferred", ""))
            item7.setForeground(QColor("#000000"))
            self.table.setItem(row, 7, item7)

            # Отзвон
            item8 = QTableWidgetItem(issue.get("callback", ""))
            item8.setForeground(QColor("#000000"))
            self.table.setItem(row, 8, item8)

            # Начало работ
            item9 = QTableWidgetItem(issue.get("work_start", ""))
            item9.setForeground(QColor("#000000"))
            self.table.setItem(row, 9, item9)

            # История звонков
            item10 = QTableWidgetItem(issue.get("call_history", ""))
            item10.setForeground(QColor("#000000"))
            self.table.setItem(row, 10, item10)

            # ЦВЕТОВАЯ ИНДИКАЦИЯ ПО ТИПУ ПРОБЛЕМЫ
            severity_type = issue.get("severity_type", "Информация")
            color = SEVERITY_COLORS.get(severity_type, "#FFFFFF")

            for col in range(11):
                if self.table.item(row, col):
                    self.table.item(row, col).setBackground(QColor(color))

    def get_device_history(self, device_ip):
        """Получает историю инцидентов для устройства по IP"""
        history = []
        for issue in self.issues:
            if issue.get("device_ip") == device_ip and issue.get("id") != "new":
                history.append({
                    "date": issue.get("date", ""),
                    "description": issue.get("description", ""),
                    "resolution": issue.get("call_history", ""),
                    "severity_type": issue.get("severity_type", "Информация")
                })
        return history

    def add_issue(self, device_info=None):
        """Добавляет новую неисправность"""
        # Получаем историю устройства, если есть device_info
        device_history = []
        if device_info and device_info.get("ip"):
            device_history = self.get_device_history(device_info.get("ip"))

        dialog = AddIssueDialog(self, device_info=device_info, device_history=device_history, ws_client=self.ws_client)
        if dialog.exec():
            data = dialog.get_data()
            if not data["description"]:
                self.show_message("Описание проблемы обязательно", "error")
                return

            # Генерируем ID
            max_id = max([int(issue.get("id", 0)) for issue in self.issues], default=0)
            new_issue = {
                "id": str(max_id + 1),
                "date": data["date"],
                "description": data["description"],
                "tickets": "",
                "master": data["master"],
                "executor": "",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "transferred": "",
                "callback": "",
                "work_start": data["work_start"],
                "call_history": "",
                "reaction_time": data.get("reaction_time", "60"),
                "severity_type": data.get("severity_type", "Высокая"),
                "device_type": data.get("device_type", ""),
                "device_id": data.get("device_id", ""),
                "device_name": data.get("device_name", ""),
                "device_ip": data.get("device_ip", "")
            }

            self.issues.append(new_issue)
            self.save_issues()

    def edit_issue(self):
        """Редактирует выбранную неисправность"""
        row = self.table.currentRow()
        if row < 0:
            self.show_message("Выберите неисправность для редактирования", "info")
            return

        issue = self.issues[row]

        # Получаем историю устройства
        device_history = []
        if issue.get("device_ip"):
            device_history = self.get_device_history(issue.get("device_ip"))

        dialog = AddIssueDialog(self, issue_data=issue, device_history=device_history, ws_client=self.ws_client)
        if dialog.exec():
            data = dialog.get_data()
            issue["date"] = data["date"]
            issue["description"] = data["description"]
            issue["master"] = data["master"]
            issue["work_start"] = data["work_start"]
            issue["reaction_time"] = data.get("reaction_time", "60")
            issue["severity_type"] = data.get("severity_type", "Высокая")
            self.save_issues()

    def delete_issue(self):
        """Удаляет выбранную неисправность"""
        row = self.table.currentRow()
        if row < 0:
            self.show_message("Выберите неисправность для удаления", "info")
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                    "Вы уверены, что хотите удалить эту неисправность?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            del self.issues[row]
            self.save_issues()

    def add_call_to_issue(self):
        """Добавляет звонок к существующей неисправности"""
        row = self.table.currentRow()
        if row < 0:
            self.show_message("Выберите неисправность", "info")
            return

        issue = self.issues[row]

        # Получаем информацию об устройстве из issue
        device_info = None
        if issue.get("device_ip"):
            device_info = {
                "type": issue.get("device_type", ""),
                "id": issue.get("device_id", ""),
                "name": issue.get("device_name", ""),
                "ip": issue.get("device_ip", "")
            }

        dialog = AddCallDialog(self, issue_id=issue.get("id"), device_info=device_info, ws_client=self.ws_client)
        if dialog.exec():
            call_data = dialog.get_data()
            timestamp = call_data["timestamp"]
            call_type = call_data["type"]
            info = call_data["info"]
            priority = call_data["priority"]

            # Обновляем соответствующее поле даты
            if call_type == "Отзвон":
                issue["callback"] = timestamp
            elif "Начало" in call_type or call_data["work_start"]:
                issue["work_start"] = call_data["work_start"] or timestamp

            # Добавляем в историю звонков
            history = issue.get("call_history", "")
            new_entry = f"[{timestamp}] {call_type} ({priority}): {info}"
            issue["call_history"] = f"{history}\n{new_entry}" if history else new_entry

            # Обновляем приоритет, если он выше
            current_severity = issue.get("severity_type", "Информация")
            severity_order = ["Информация", "Предупреждение", "Средняя", "Высокая", "Чрезвычайная"]
            if severity_order.index(priority) > severity_order.index(current_severity):
                issue["severity_type"] = priority

            self.save_issues()

    def save_issues(self):
        """Сохраняет список неисправностей на сервер"""
        if not self.ws_client or not self.parent_window:
            self.show_message("Нет связи с сервером", "error")
            return

        request_id = self.ws_client.send_request(
            "csv_write",
            path="globals/issues.csv",
            data=self.issues
        )

        if request_id:
            def on_response(data):
                if data.get("success"):
                    self.load_issues()
                    self.show_message("Сохранено успешно", "success")
                else:
                    self.show_message(f"Ошибка сохранения: {data.get('error')}", "error")

            self.parent_window.pending_requests[request_id] = on_response

    def export_csv(self):
        """Экспортирует данные в CSV файл"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт CSV", "", "CSV Files (*.csv)"
        )

        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    if self.issues:
                        fieldnames = list(self.issues[0].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(self.issues)

                self.show_message(f"Экспортировано в {filename}", "success")
            except Exception as e:
                self.show_message(f"Ошибка экспорта: {e}", "error")

    def show_message(self, text, msg_type="info"):
        """Показывает сообщение пользователю"""
        if hasattr(self.parent_window, "status_bar"):
            self.parent_window.status_bar.showMessage(text, 3000)
