# switch_edit_dialog.py
# Диалог редактирования свитча
# Автор: E1

import re
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QCheckBox, QPushButton, QLabel, QTableWidget, QTableWidgetItem, QComboBox,
    QHeaderView, QSpinBox, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt6.QtGui import QColor
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
        
        self.init_ui()
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
        self.copy_btn = QPushButton("Копия")
        self.copy_btn.setMaximumWidth(80)
        checkbox_layout.addWidget(self.not_installed_cb)
        checkbox_layout.addWidget(self.not_configured_cb)
        checkbox_layout.addWidget(self.copy_btn)
        checkbox_layout.addStretch()
        left_column.addLayout(checkbox_layout)
        
        # Имя
        name_layout = QFormLayout()
        self.name_input = QLineEdit()
        name_layout.addRow(QLabel("Имя"), self.name_input)
        left_column.addLayout(name_layout)
        
        # Модель
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.load_models()
        name_layout.addRow(QLabel("Модель"), self.model_combo)
        
        # Питание
        self.power_input = QLineEdit()
        name_layout.addRow(QLabel("Питание"), self.power_input)
        
        # Локация
        self.location_input = QLineEdit()
        name_layout.addRow(QLabel("Локация"), self.location_input)
        
        # Примечание
        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(120)
        name_layout.addRow(QLabel("Примечание"), self.note_input)
        
        # Последний редактор
        self.last_editor_input = QLineEdit()
        self.last_editor_input.setReadOnly(True)
        name_layout.addRow(QLabel("Последний редактор"), self.last_editor_input)
        
        left_column.addLayout(name_layout)
        top_section.addLayout(left_column, 2)
        
        # Средняя колонка: IP, Mac, Мастер
        middle_column = QVBoxLayout()
        middle_form = QFormLayout()
        
        self.ip_input = QLineEdit()
        middle_form.addRow(QLabel("IP"), self.ip_input)
        
        self.mac_input = QLineEdit()
        middle_form.addRow(QLabel("Mac"), self.mac_input)
        
        self.master_combo = QComboBox()
        self.master_combo.setEditable(True)
        self.load_masters()
        middle_form.addRow(QLabel("Мастер"), self.master_combo)
        
        # Время реакции (мин)
        self.reaction_time_input = QSpinBox()
        self.reaction_time_input.setRange(0, 9999)
        self.reaction_time_input.setValue(60)
        middle_form.addRow(QLabel("Время реакции (мин)"), self.reaction_time_input)
        
        middle_column.addLayout(middle_form)
        top_section.addLayout(middle_column, 1)
        
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
        
        # Кнопки управления портами
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
        
        # Таблица портов
        self.ports_table = QTableWidget()
        self.ports_table.setColumnCount(1)
        self.ports_table.setHorizontalHeaderLabels(["Описание порта"])
        self.ports_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ports_table.verticalHeader().setVisible(True)
        self.ports_table.setMinimumHeight(400)
        
        right_column.addWidget(self.ports_table)
        top_section.addLayout(right_column, 2)
        
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
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
    def load_models(self):
        """Загрузка списка моделей"""
        # TODO: Загрузить из БД через ws_client
        default_models = [
            "DES-3200-18 rev C",
            "DES-3200-28 rev B",
            "DGS-1100-06/ME",
            "DGS-1210-10P",
            "DGS-3120-24TC",
        ]
        self.model_combo.addItems(default_models)
        
    def load_masters(self):
        """Загрузка списка мастеров"""
        # TODO: Загрузить из БД через ws_client
        default_masters = [
            "Шепель А. В.",
            "Иванов И. И.",
            "Петров П. П.",
        ]
        self.master_combo.addItems(default_masters)
        
    def load_data(self):
        """Загрузка данных свитча в форму"""
        if not self.switch_data:
            return
            
        # Чекбоксы
        self.not_installed_cb.setChecked(self.switch_data.get("notinstalled") == "-1")
        self.not_configured_cb.setChecked(self.switch_data.get("notsettings") == "-1")
        
        # Основные поля
        self.name_input.setText(self.switch_data.get("name", ""))
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
        
        # Мастер
        master = self.switch_data.get("master", "")
        if master:
            index = self.master_combo.findText(master)
            if index >= 0:
                self.master_combo.setCurrentIndex(index)
            else:
                self.master_combo.setCurrentText(master)
        
        # Остальные поля
        self.power_input.setText(self.switch_data.get("power", ""))
        self.location_input.setText(self.switch_data.get("location", ""))
        self.reaction_time_input.setValue(int(self.switch_data.get("reaction_time", 60)))
        self.note_input.setPlainText(self.switch_data.get("note", ""))
        self.last_editor_input.setText(self.switch_data.get("last_editor", ""))
        
        # Загрузка портов
        ports = self.switch_data.get("ports", [])
        self.ports_table.setRowCount(len(ports))
        for i, port in enumerate(ports):
            item = QTableWidgetItem(port.get("description", ""))
            self.ports_table.setItem(i, 0, item)
            self.ports_table.setVerticalHeaderItem(i, QTableWidgetItem(str(i + 1)))
    
    def validate_ip(self, ip):
        """Валидация IP-адреса"""
        pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(pattern, ip):
            return False
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    
    def validate_mac(self, mac):
        """Валидация MAC-адреса"""
        # Поддержка форматов: XX:XX:XX:XX:XX:XX или XXXXXXXXXXXX
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
        """Сохранение данных из формы в switch_data"""
        # Чекбоксы
        self.switch_data["notinstalled"] = "-1" if self.not_installed_cb.isChecked() else "0"
        self.switch_data["notsettings"] = "-1" if self.not_configured_cb.isChecked() else "0"
        
        # Основные поля
        self.switch_data["name"] = self.name_input.text().strip()
        self.switch_data["ip"] = self.ip_input.text().strip()
        self.switch_data["mac"] = self.mac_input.text().strip()
        self.switch_data["model"] = self.model_combo.currentText().strip()
        self.switch_data["master"] = self.master_combo.currentText().strip()
        self.switch_data["power"] = self.power_input.text().strip()
        self.switch_data["location"] = self.location_input.text().strip()
        self.switch_data["reaction_time"] = str(self.reaction_time_input.value())
        self.switch_data["note"] = self.note_input.toPlainText().strip()
        
        # Обновление последнего редактора и времени
        if hasattr(self.parent_window, 'current_user'):
            self.switch_data["last_editor"] = self.parent_window.current_user
        self.switch_data["mod_time"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # Сохранение портов
        ports = []
        for i in range(self.ports_table.rowCount()):
            item = self.ports_table.item(i, 0)
            if item and item.text().strip():
                ports.append({
                    "port_num": i + 1,
                    "description": item.text().strip()
                })
        self.switch_data["ports"] = ports
    
    def add_port(self):
        """Добавление нового порта"""
        row = self.ports_table.rowCount()
        self.ports_table.insertRow(row)
        self.ports_table.setVerticalHeaderItem(row, QTableWidgetItem(str(row + 1)))
        self.ports_table.setItem(row, 0, QTableWidgetItem(""))
        self.ports_table.editItem(self.ports_table.item(row, 0))
    
    def remove_port(self):
        """Удаление выбранного порта"""
        current_row = self.ports_table.currentRow()
        if current_row >= 0:
            self.ports_table.removeRow(current_row)
            # Обновление номеров портов
            for i in range(self.ports_table.rowCount()):
                self.ports_table.setVerticalHeaderItem(i, QTableWidgetItem(str(i + 1)))
    
    def toggle_bold_port(self):
        """Переключение жирного шрифта для выбранного порта"""
        current_row = self.ports_table.currentRow()
        if current_row >= 0:
            item = self.ports_table.item(current_row, 0)
            if item:
                font = item.font()
                font.setBold(not font.bold())
                item.setFont(font)
    
    def copy_to_clipboard(self):
        """Копирование данных свитча в буфер обмена"""
        from PyQt6.QtGui import QGuiApplication
        
        text = f"Имя: {self.name_input.text()}\n"
        text += f"IP: {self.ip_input.text()}\n"
        text += f"MAC: {self.mac_input.text()}\n"
        text += f"Модель: {self.model_combo.currentText()}\n"
        text += f"Мастер: {self.master_combo.currentText()}\n"
        text += f"Питание: {self.power_input.text()}\n"
        text += f"Локация: {self.location_input.text()}\n"
        
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        
        # Показать уведомление
        if hasattr(self.parent_window, 'status_bar'):
            self.parent_window.status_bar.showMessage("Данные скопированы в буфер обмена", 2000)
    
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
