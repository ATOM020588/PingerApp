from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QCheckBox, QTableWidget,
    QTableWidgetItem, QTabWidget, QWidget, QGroupBox, QSpinBox,
    QHeaderView, QTextEdit, QRadioButton, QButtonGroup, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
import json
import os
import uuid

class AddSwitchDialog(QDialog):
    """Диалоговое окно для добавления и настройки управляемого свитча"""
    
    # Сигнал для добавления свитча на канвас
    switch_added = pyqtSignal(dict)

    def __init__(self, parent=None, ws_client=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка свитча")
        self.setMinimumSize(1400, 700)
        self.setStyleSheet(self.get_stylesheet())
        
        # WebSocket клиент из MainWindow
        self.ws_client = ws_client
        self.parent_window = parent
        
        # Инициализируем пустые данные
        self.models_data = []
        self.vlans_data = []
        self.masters_data = []
        self.firmware_data = []
        
        # Загружаем данные с сервера сначала
        self.load_data_from_server()
        self.init_ui()

    def get_stylesheet(self):
        """Стили окна в соответствии с общей темой приложения"""
        return """
            QDialog { background-color: #333; color: #FFC107; }
            QLabel { color: #FFC107; font-size: 12px; padding: 2px 0px 0px 5px; border: none; }
            QLineEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 6px 8px; height: 16px; } 
            QLineEdit:focus { border: 1px solid #FFC107; background-color: #555; }
            QComboBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 4px 8px; height: 22px; } 
            QComboBox::drop-down { border: none; width: 0px; } 
            QComboBox QAbstractItemView { background-color: #444; color: #FFC107; selection-background-color: #555; }
            QComboBox:focus {border: 1px solid #FFC107;}
            QSpinBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 4px 6px; }
            QSpinBox:focus {border: 1px solid #FFC107;}
            QTextEdit {background-color: #3d3d3d; color: #dbdbdb; border: 1px solid #555; border-radius: 3px; padding: 5px; }
            QTextEdit:focus {border: 1px solid #FFC107;}
            QTextEdit:focus {border: 1px solid #FFC107;}
            QPushButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 6px 16px; min-width: 60px; } 
            QPushButton:hover { background-color: #555; } 
            QPushButton:pressed { background-color: #666; }
            QCheckBox { color: #FFC107; padding: 3px; border: none; } 
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #555; background: #444; } 
            QCheckBox::indicator:checked { background: #FFC107; }
            QTableWidget { background-color: #444; color: #FFC107; border: 1px solid #555; gridline-color: #555; border-radius: 4px; } 
            QHeaderView::section { background-color: #555; color: #FFC107; padding: 6px; border: none; font-weight: bold; } 
            QTableWidget::item:hover { background-color: #555; } 
            QTableWidget::item:selected { background-color: #75736b; color: #333; } 
            QTableCornerButton::section { background-color: #555; border: none; }
            QHeaderView::section { background-color: #555; color: #FFC107; padding: 6px; border: none; font-weight: bold; }
            QTabBar::tab { background-color: #444; color: #FFC107; padding: 6px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; } 
            QTabBar::tab:selected { background-color: #75736b; color: #333; } 
            QTabBar::tab:hover { background-color: #555; }
            QGroupBox { border: 1px solid #555; border-radius: 6px; margin-top: 10px; padding: 8px; font-weight: bold; color: #FFC107; } 
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0px 3px; }
            QScrollArea { background: transparent; color: #FFC107; padding: 0px; border: none; }
            QRadioButton { color: #FFC107; border: none; padding: 0px; }
            QRadioButton::indicator { width: 14px; height: 14px; border: 1px solid #FFC107; border-radius: 7px; background: transparent; }
            QRadioButton::indicator:checked { background: #FFC107; }
            
        """

    def load_data_from_server(self):
        """Загрузка данных с сервера через WebSocket"""
        if not self.ws_client or not hasattr(self.parent_window, 'pending_requests'):
            print("WebSocket клиент недоступен")
            return
        
        # Счетчик ожидаемых ответов
        self.pending_responses = 4
        
        # Загрузка моделей
        request_id = self.ws_client.send_request("list_models")
        if request_id:
            self.parent_window.pending_requests[request_id] = self.on_models_loaded
        
        # Загрузка управляющих VLAN
        request_id = self.ws_client.send_request("list_mngmt_vlan")
        if request_id:
            self.parent_window.pending_requests[request_id] = self.on_vlans_loaded
        
        # Загрузка мастеров
        request_id = self.ws_client.send_request("list_masters")
        if request_id:
            self.parent_window.pending_requests[request_id] = self.on_masters_loaded
        
        # Загрузка прошивок
        request_id = self.ws_client.send_request("list_firmwares")
        if request_id:
            self.parent_window.pending_requests[request_id] = self.on_firmwares_loaded
    
    def on_models_loaded(self, data):
        """Обработчик загрузки моделей"""
        if data.get("success"):
            self.models_data = data.get("models", [])
            print(f"Загружено моделей: {len(self.models_data)}")
            self.populate_models()
        else:
            print(f"Не удалось загрузить модели: {data.get('error', '')}")
    
    def on_vlans_loaded(self, data):
        """Обработчик загрузки VLAN"""
        if data.get("success"):
            self.vlans_data = data.get("vlans", [])
            print(f"Загружено VLAN: {len(self.vlans_data)}")
            self.populate_vlans()
        else:
            print(f"Не удалось загрузить VLAN: {data.get('error', '')}")
    
    def on_masters_loaded(self, data):
        """Обработчик загрузки мастеров"""
        if data.get("success"):
            self.masters_data = data.get("masters", [])
            print(f"Загружено мастеров: {len(self.masters_data)}")
            self.populate_masters()
        else:
            print(f"Не удалось загрузить мастеров: {data.get('error', '')}")
    
    def on_firmwares_loaded(self, data):
        """Обработчик загрузки прошивок"""
        if data.get("success"):
            self.firmware_data = data.get("firmwares", [])
            print(f"Загружено прошивок: {len(self.firmware_data)}")
            self.populate_firmwares()
        else:
            print(f"Не удалось загрузить прошивки: {data.get('error', '')}")

    def init_ui(self):
        """Инициализация интерфейса с 4 колонками"""
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Колонка 1 - Основные настройки
        column1 = self.create_column1_main_settings()
        main_layout.addLayout(column1, stretch=1)

        # Колонка 2 - Neobills
        column2 = self.create_column2_neobills()
        main_layout.addWidget(column2, stretch=1)

        # Колонка 3 - DHCP
        column3 = self.create_column3_dhcp()
        main_layout.addLayout(column3, stretch=1)

        # Колонка 4 - Порты и Description
        column4 = self.create_column4_ports_description()
        main_layout.addLayout(column4, stretch=1)

        # Заполняем комбобоксы данными
        self.populate_combos()

    def create_column1_main_settings(self):
        """Создание колонки 1 - Основные настройки"""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Имя свитча - уменьшено в 2 раза и 3 строки
        layout.addWidget(QLabel("Имя свитча:"))
        self.name_text = QTextEdit()
        self.name_text.setMaximumHeight(70)  # 3 строки
        layout.addWidget(self.name_text)
        # Модель - загружается с сервера
        layout.addWidget(QLabel("Модель:"))
        self.model_combo = QComboBox()
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo)


        row = QHBoxLayout()
        row.addWidget(QLabel("Мастер"))
        row.addWidget(QLabel("Упр. VLAN"))
        layout.addLayout(row)
        row = QHBoxLayout()
        self.master_combo = QComboBox()
        #self.master_combo.setMaximumWidth(200)
        row.addWidget(self.master_combo)
        row.addSpacing(10)  # необязательно, просто для красоты
        self.vlan_combo = QComboBox()
        #self.vlan_combo.setMaximumWidth(150)
        row.addWidget(self.vlan_combo)
        # Добавляем строку в основной layout
        layout.addLayout(row)

        # Магистральные порты и UPLINK
        mags_uplink_layout = QHBoxLayout()

        # Магистральные порты
        mags_layout = QVBoxLayout()
        mags_layout.addWidget(QLabel("Серийный номер"))
        self.mags_edit = QLineEdit()
        mags_layout.addWidget(self.mags_edit)
        mags_uplink_layout.addLayout(mags_layout)

        # Uplink:
        uplink_layout = QVBoxLayout()
        uplink_layout.addWidget(QLabel("Uplink:"))
        self.uplink_edit = QLineEdit()
        self.uplink_edit.setEchoMode(QLineEdit.EchoMode.Password)
        uplink_layout.addWidget(self.uplink_edit)
        mags_uplink_layout.addLayout(uplink_layout)

        layout.addLayout(mags_uplink_layout)
        
        
        # MAC и IP в одной строке, уменьшены в 2 раза
        mac_ip_layout = QHBoxLayout()

        # MAC
        mac_layout = QVBoxLayout()
        mac_layout.addWidget(QLabel("MAC"))
        self.mac_edit = QLineEdit()
        #self.mac_edit.setMaximumWidth(95)  # Уменьшено в 2 раза
        mac_layout.addWidget(self.mac_edit)
        mac_ip_layout.addLayout(mac_layout)

        # IP
        ip_layout = QVBoxLayout()
        ip_layout.addWidget(QLabel("IP"))
        self.ip_edit = QLineEdit("172.27.4.7")
        self.ip_edit.setMaximumWidth(90)  # Уменьшено в 2 раза
        ip_layout.addWidget(self.ip_edit)
        mac_ip_layout.addLayout(ip_layout)

        # Кнопка IP
        ip_btn_layout = QVBoxLayout()
        ip_btn_layout.addWidget(QLabel(""))  # Пустая метка для выравнивания
        self.ip_button = QPushButton("Смена IP")
        self.ip_button.setMaximumWidth(20)
        ip_btn_layout.addWidget(self.ip_button)
        mac_ip_layout.addLayout(ip_btn_layout)

        layout.addLayout(mac_ip_layout)

        # Серийный номер и Пароль в одной строке, уменьшены в 2 раза
        serial_password_layout = QHBoxLayout()

        # Серийный номер
        serial_layout = QVBoxLayout()
        serial_layout.addWidget(QLabel("Серийный номер"))
        self.serial_edit = QLineEdit()
        #self.serial_edit.setMaximumWidth(95)
        serial_layout.addWidget(self.serial_edit)
        serial_password_layout.addLayout(serial_layout)

        # Пароль
        password_layout = QVBoxLayout()
        password_layout.addWidget(QLabel("Пароль"))
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        #self.password_edit.setMaximumWidth(95)
        password_layout.addWidget(self.password_edit)
        serial_password_layout.addLayout(password_layout)

        layout.addLayout(serial_password_layout)

        # Кнопки "В гугл" и "Настроить" в одну строку
        buttons_layout = QHBoxLayout()
        self.google_button = QPushButton("В гугл")
        self.config_button = QPushButton("Настроить")
        buttons_layout.addWidget(self.google_button)
        buttons_layout.addWidget(self.config_button)
        layout.addLayout(buttons_layout)

        # Прошивка с кнопкой "Прошить"
        layout.addWidget(QLabel("Прошивка"))
        firmware_layout = QHBoxLayout()
        self.firmware_combo = QComboBox()
        firmware_layout.addWidget(self.firmware_combo)
        self.flash_button = QPushButton("Прошить")
        self.flash_button.setMaximumWidth(80)
        firmware_layout.addWidget(self.flash_button)
        layout.addLayout(firmware_layout)

        # Поле "Реакция"
        layout.addWidget(QLabel("Реакция"))
        self.reaction_edit = QLineEdit()
        self.reaction_edit.setMaximumWidth(100)
        self.reaction_edit.setPlaceholderText("60")
        layout.addWidget(self.reaction_edit)

        # Добавляем растяжение перед кнопками внизу
        layout.addStretch()

        # Кнопки "Добавить" и "Сброс" внизу
        bottom_buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Добавить")
        self.add_button.setFixedHeight(65)
        self.add_button.clicked.connect(self.on_add_switch)
        self.reset_button = QPushButton("Сброс")
        self.reset_button.setFixedHeight(65)
        self.reset_button.clicked.connect(self.reset_fields)
        bottom_buttons_layout.addWidget(self.add_button)
        bottom_buttons_layout.addWidget(self.reset_button)
        layout.addLayout(bottom_buttons_layout)

        return layout

    def create_column2_neobills(self):
        """Создание колонки 2 — Neobills (фиксированная ширина)"""

        container = QWidget()
        container.setFixedWidth(260)  # ширина колонки

        layout = QVBoxLayout(container)
        layout.setSpacing(8)

        # ===== Neobilis =====
        neobilis_layout = QHBoxLayout()
        self.neobilis_check = QCheckBox()
        neobilis_label = QLabel("Neobilis")
        neobilis_layout.addWidget(self.neobilis_check)
        neobilis_layout.addWidget(neobilis_label)
        neobilis_layout.addStretch()
        layout.addLayout(neobilis_layout)

        # ===== Выбор устройства =====
        self.device_combo = QComboBox()
        self.device_combo.addItems([
            "D-Link DGS-3200-10 B1",
            "D-Link DGS-3100-24 A1",
            "D-Link DES-3028 A1"
        ])
        layout.addWidget(self.device_combo)

        # ===================== ЗАГОЛОВКИ =====================
        headers = QHBoxLayout()

        COL_W_NUM   = 30
        COL_W_MAC   = 70
        COL_W_PORT  = 60
        COL_W_NONE  = 60

        def mk_header(text, width):
            lbl = QLabel(text)
            lbl.setFixedWidth(width)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        headers.addWidget(mk_header("№", COL_W_NUM))
        headers.addWidget(mk_header("MAC", COL_W_MAC))
        headers.addWidget(mk_header("PORT", COL_W_PORT))
        headers.addWidget(mk_header("NONE", COL_W_NONE))

        layout.addLayout(headers)

        # ===================== SCROLL =====================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_widget.setFixedWidth(260)   # ← ВАЖНО: фиксируем ширину контента, не scroll

        self.ports_layout = QVBoxLayout(scroll_widget)
        self.ports_layout.setSpacing(4)

        self.port_radio_groups = []
        #self.create_port_rows(10)
        scroll_widget.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        return container


    def create_port_rows(self, num_ports):
        """Создание идеально ровных строк с радиокнопками"""

        while self.ports_layout.count():
            item = self.ports_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.port_radio_groups.clear()

        COL_W_NUM   = 30
        COL_W_MAC   = 70
        COL_W_PORT  = 60
        COL_W_NONE  = 60

        def centered_radio(width):
            """Создаёт виджет фиксированной ширины, центрирует радиокнопку внутри"""
            wrapper = QWidget()
            wrapper.setFixedWidth(width)
            w_layout = QHBoxLayout(wrapper)
            w_layout.setContentsMargins(0, 0, 0, 0)
            w_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            radio = QRadioButton()
            radio.setText("")       # обязательно
            w_layout.addWidget(radio)
            return wrapper, radio

        for port_num in range(1, num_ports + 1):

            row = QHBoxLayout()
            row.setSpacing(0)

            # ===== № =====
            lbl = QLabel(str(port_num))
            lbl.setFixedWidth(COL_W_NUM)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(lbl)

            button_group = QButtonGroup()

            # ===== MAC =====
            mac_widget, mac_radio = centered_radio(COL_W_MAC)
            button_group.addButton(mac_radio, 0)
            row.addWidget(mac_widget)

            # ===== PORT =====
            port_widget, port_radio = centered_radio(COL_W_PORT)
            button_group.addButton(port_radio, 1)
            row.addWidget(port_widget)

            # ===== NONE =====
            none_widget, none_radio = centered_radio(COL_W_NONE)
            none_radio.setChecked(True)
            button_group.addButton(none_radio, 2)
            row.addWidget(none_widget)

            self.port_radio_groups.append(button_group)
            self.ports_layout.addLayout(row)

        self.ports_layout.addStretch()


    def on_model_changed(self):
        """Обработчик изменения модели - обновляет количество портов"""
        model = self.model_combo.currentText()

        num_ports = 10  # по умолчанию

        if "3200-28" in model or "3028" in model or "3526" in model:
            num_ports = 28
        elif "3100-24" in model or "2424" in model:
            num_ports = 24
        elif "1210-28" in model:
            num_ports = 28
        elif "3200-10" in model:
            num_ports = 10
        elif "P3310" in model:
            num_ports = 10
        elif "P3600-04" in model:
            num_ports = 4
        elif "P3600-08" in model:
            num_ports = 8
        elif "P3600-16" in model:
            num_ports = 16

        self.create_port_rows(num_ports)


    def create_column3_dhcp(self):
        """Создание колонки 3 - DHCP"""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # DHCP секция
        dhcp_group = QGroupBox("DHCP")
        dhcp_layout = QVBoxLayout()

        self.dhcp_check = QCheckBox("DHCP")
        dhcp_layout.addWidget(self.dhcp_check)

        self.dhcp_ports_check = QCheckBox("DHCP по портам (ZTE)")
        dhcp_layout.addWidget(self.dhcp_ports_check)

        # DHCP VLANы
        dhcp_layout.addWidget(QLabel("DHCP VLANы"))
        dhcp_vlan_layout = QHBoxLayout()
        self.dhcp_vlan_edit = QLineEdit()
        dhcp_vlan_layout.addWidget(self.dhcp_vlan_edit)
        self.dhcp_vlan_add_button = QPushButton("X")
        self.dhcp_vlan_add_button.setMaximumWidth(30)
        dhcp_vlan_layout.addWidget(self.dhcp_vlan_add_button)
        dhcp_layout.addLayout(dhcp_vlan_layout)

        # Address binding
        self.address_binding_check = QCheckBox("Address binding")
        dhcp_layout.addWidget(self.address_binding_check)

        # VLANы
        dhcp_layout.addWidget(QLabel("VLANы"))
        self.vlan_edit = QLineEdit()
        dhcp_layout.addWidget(self.vlan_edit)

        # Порты
        dhcp_layout.addWidget(QLabel("Порты"))
        self.ports_edit = QLineEdit()
        dhcp_layout.addWidget(self.ports_edit)

        dhcp_group.setLayout(dhcp_layout)
        layout.addWidget(dhcp_group)

        # RSTP секция
        rstp_group = QGroupBox("RSTP")
        rstp_layout = QVBoxLayout()

        self.rstp_check = QCheckBox("RSTP")
        rstp_layout.addWidget(self.rstp_check)

        rstp_layout.addWidget(QLabel("Порты"))
        self.rstp_ports_edit = QLineEdit()
        rstp_layout.addWidget(self.rstp_ports_edit)

        rstp_layout.addWidget(QLabel("Приоритет"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["default", "4096", "8192", "16384", "32768"])
        rstp_layout.addWidget(self.priority_combo)

        rstp_group.setLayout(rstp_layout)
        layout.addWidget(rstp_group)

        # OLT VLAN
        layout.addWidget(QLabel("OLT VLAN"))
        self.qlt_vlan_edit = QLineEdit()
        layout.addWidget(self.qlt_vlan_edit)

        layout.addStretch()
        return layout

    def create_column4_ports_description(self):
        """Создание колонки 4 - Порты и Description"""
        layout = QVBoxLayout()

        # Вкладки
        self.tabs = QTabWidget()

        # Вкладка "Порты"
        ports_tab = QWidget()
        ports_tab_layout = QVBoxLayout(ports_tab)

        # VLAN иконка и заголовок
        vlan_header_layout = QHBoxLayout()
        vlan_label = QLabel("VLAN")
        vlan_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        vlan_header_layout.addWidget(vlan_label)
        vlan_header_layout.addStretch()
        ports_tab_layout.addLayout(vlan_header_layout)

        # Tag, Untag
        ports_tab_layout.addWidget(QLabel("Tag"))
        self.tag_edit = QLineEdit()
        ports_tab_layout.addWidget(self.tag_edit)

        ports_tab_layout.addWidget(QLabel("Untag"))
        untag_layout = QHBoxLayout()
        self.untag_edit = QLineEdit()
        untag_layout.addWidget(self.untag_edit)
        self.untag_remove_button = QPushButton("X")
        self.untag_remove_button.setMaximumWidth(30)
        self.untag_remove_button.setStyleSheet("background-color: #d32f2f; color: white;")
        untag_layout.addWidget(self.untag_remove_button)
        ports_tab_layout.addLayout(untag_layout)

        ports_tab_layout.addStretch()
        self.tabs.addTab(ports_tab, "Порты")

        # Вкладка "Description"
        description_tab = QWidget()
        description_tab_layout = QVBoxLayout(description_tab)

        # Порт иконка и заголовок
        port_header_layout = QHBoxLayout()
        port_label = QLabel("Порт")
        port_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        port_header_layout.addWidget(port_label)
        port_header_layout.addStretch()
        description_tab_layout.addLayout(port_header_layout)

        # Таблица Description
        self.description_table = QTableWidget(1, 2)
        self.description_table.setHorizontalHeaderLabels(["Порт", "Description"])
        self.description_table.horizontalHeader().setStretchLastSection(True)

        # Первая строка с данными
        port_item = QTableWidgetItem("10")
        port_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.description_table.setItem(0, 0, port_item)

        desc_layout_widget = QWidget()
        desc_layout = QHBoxLayout(desc_layout_widget)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_edit = QLineEdit("Uplink")
        desc_layout.addWidget(desc_edit)
        remove_desc_button = QPushButton("X")
        remove_desc_button.setMaximumWidth(30)
        remove_desc_button.setStyleSheet("background-color: #d32f2f; color: white;")
        desc_layout.addWidget(remove_desc_button)
        self.description_table.setCellWidget(0, 1, desc_layout_widget)

        description_tab_layout.addWidget(self.description_table)
        description_tab_layout.addStretch()
        self.tabs.addTab(description_tab, "Description")

        layout.addWidget(self.tabs)
        return layout

    def populate_combos(self):
        """Заполнение комбобоксов данными после создания UI"""
        # Вызываем отдельные методы для каждого типа данных
        self.populate_models()
        self.populate_vlans()
        self.populate_masters()
        self.populate_firmwares()
    
    def populate_models(self):
        """Заполнение списка моделей"""
        self.model_combo.clear()
        if self.models_data:
            model_names = [model.get("model_name", "") for model in self.models_data]
            self.model_combo.addItems(model_names)
        else:
            self.model_combo.addItem("Нет данных")
    
    def populate_vlans(self):
        """Заполнение списка VLAN"""
        self.vlan_combo.clear()
        if self.vlans_data:
            vlan_ids = [str(vlan.get("id", "")) for vlan in self.vlans_data]
            self.vlan_combo.addItems(vlan_ids)
        else:
            self.vlan_combo.addItem("Нет данных")
    
    def populate_masters(self):
        """Заполнение списка мастеров"""
        self.master_combo.clear()
        if self.masters_data:
            master_names = [master.get("fio", "") for master in self.masters_data]
            self.master_combo.addItems(master_names)
        else:
            self.master_combo.addItem("Нет данных")
    
    def populate_firmwares(self):
        """Заполнение списка прошивок"""
        self.firmware_combo.clear()
        if self.firmware_data:
            firmware_names = [fw.get("model_name", "") for fw in self.firmware_data]
            self.firmware_combo.addItems(firmware_names)
        else:
            self.firmware_combo.addItem("Нет данных")

    def reset_fields(self):
        """Очистка всех полей"""
        # Основные поля
        self.name_text.clear()
        self.mac_edit.clear()
        self.ip_edit.setText("172.27.4.7")
        self.serial_edit.clear()
        self.password_edit.clear()
        self.reaction_edit.setText("60")
        
        # Комбобоксы
        self.model_combo.setCurrentIndex(0)
        self.vlan_combo.setCurrentIndex(0)
        self.master_combo.setCurrentIndex(0)
        self.firmware_combo.setCurrentIndex(0)
        
        # DHCP
        self.dhcp_check.setChecked(False)
        self.dhcp_ports_check.setChecked(False)
        self.address_binding_check.setChecked(False)
        self.dhcp_vlan_edit.clear()
        self.vlan_edit.clear()
        self.ports_edit.clear()
        
        # RSTP
        self.rstp_check.setChecked(False)
        self.rstp_ports_edit.clear()
        self.priority_combo.setCurrentIndex(0)
        
        # OLT VLAN
        self.qlt_vlan_edit.clear()
        
        # Порты
        self.tag_edit.clear()
        self.untag_edit.clear()
        
        # Сброс радиокнопок в NONE
        for group in self.port_radio_groups:
            group.button(2).setChecked(True)  # NONE
        
        # Neobilis
        self.neobilis_check.setChecked(False)
        self.device_combo.setCurrentIndex(0)

    def on_add_switch(self):
        """Обработчик кнопки Добавить - собирает данные и передает наружу"""
        # Собираем данные свитча
        switch_data = {
            "name": self.name_text.toPlainText(),
            "model": self.model_combo.currentText(),
            "vlan": self.vlan_combo.currentText(),
            "master": self.master_combo.currentText(),
            "mac": self.mac_edit.text(),
            "ip": self.ip_edit.text(),
            "serial": self.serial_edit.text(),
            "password": self.password_edit.text(),
            "firmware": self.firmware_combo.currentText(),
            "reaction": self.reaction_edit.text(),
            
            # DHCP
            "dhcp": self.dhcp_check.isChecked(),
            "dhcp_ports": self.dhcp_ports_check.isChecked(),
            "dhcp_vlans": self.dhcp_vlan_edit.text(),
            "address_binding": self.address_binding_check.isChecked(),
            "vlans": self.vlan_edit.text(),
            "ports": self.ports_edit.text(),
            
            # RSTP
            "rstp": self.rstp_check.isChecked(),
            "rstp_ports": self.rstp_ports_edit.text(),
            "priority": self.priority_combo.currentText(),
            
            # OLT
            "olt_vlan": self.qlt_vlan_edit.text(),
            
            # Порты
            "tag": self.tag_edit.text(),
            "untag": self.untag_edit.text(),
            
            # Neobilis
            "neobilis": self.neobilis_check.isChecked(),
            "device": self.device_combo.currentText(),
            
            # Режимы портов
            "port_modes": []
        }
        
        # Собираем режимы портов
        for i, group in enumerate(self.port_radio_groups):
            mode_id = group.checkedId()
            mode_name = ["MAC", "PORT", "NONE"][mode_id]
            switch_data["port_modes"].append({
                "port": i + 1,
                "mode": mode_name
            })
        
        # Отправляем сигнал
        self.switch_added.emit(switch_data)
        
        # Показываем сообщение
        QMessageBox.information(self, "Успех", "Свитч добавлен на канвас!\nНастройки будут сохранены после нажатия кнопки 'Редактирование'.")
        
        # Закрываем диалог
        self.accept()

    def get_switch_data(self):
        """Получить данные свитча для сохранения"""
        return {
            "name": self.name_text.toPlainText(),
            "model": self.model_combo.currentText(),
            "vlan": self.vlan_combo.currentText(),
            "master": self.master_combo.currentText(),
            "mac": self.mac_edit.text(),
            "ip": self.ip_edit.text(),
            "serial": self.serial_edit.text(),
            "firmware": self.firmware_combo.currentText(),
            "reaction": self.reaction_edit.text(),
            "dhcp": self.dhcp_check.isChecked(),
            "rstp": self.rstp_check.isChecked(),
            "neobilis": self.neobilis_check.isChecked()
        }

# Для тестирования
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = AddSwitchDialog()
    
    # Подключаем сигнал для тестирования
    def on_switch_added(data):
        print("Свитч добавлен:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    
    dialog.switch_added.connect(on_switch_added)
    dialog.show()
    sys.exit(app.exec())
