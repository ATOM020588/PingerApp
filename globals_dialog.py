# globals_dialog.py - Диалог управления глобальными неисправностями
# Дата: Декабрь 2024

import csv
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QLineEdit, QTextEdit,
    QComboBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class AddIssueDialog(QDialog):
    """Диалог добавления/редактирования неисправности"""
    def __init__(self, parent=None, issue_data=None, device_info=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить неисправность" if not issue_data else "Редактировать неисправность")
        self.setFixedSize(600, 500)
        self.issue_data = issue_data
        self.device_info = device_info
        
        layout = QVBoxLayout()
        
        # Описание проблемы
        layout.addWidget(QLabel("Описание проблемы:"))
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        if issue_data:
            self.description_input.setPlainText(issue_data.get("description", ""))
        elif device_info:
            # Если создается из контекстного меню оборудования
            device_name = device_info.get("name", "")
            device_ip = device_info.get("ip", "")
            self.description_input.setPlainText(f"Устройство: {device_name} ({device_ip}) - не работает")
        layout.addWidget(self.description_input)
        
        # Мастер
        layout.addWidget(QLabel("Мастер:"))
        self.master_input = QLineEdit()
        if issue_data:
            self.master_input.setText(issue_data.get("master", ""))
        layout.addWidget(self.master_input)
        
        # Исполнитель
        layout.addWidget(QLabel("Исполнитель (техник):"))
        self.executor_input = QLineEdit()
        if issue_data:
            self.executor_input.setText(issue_data.get("executor", ""))
        layout.addWidget(self.executor_input)
        
        # История звонков
        layout.addWidget(QLabel("История звонков:"))
        self.call_history_input = QTextEdit()
        self.call_history_input.setMaximumHeight(80)
        if issue_data:
            self.call_history_input.setPlainText(issue_data.get("call_history", ""))
        layout.addWidget(self.call_history_input)
        
        # Информация об устройстве (только для отображения)
        if device_info:
            info_label = QLabel(f"<b>Устройство:</b> {device_info.get('name', 'N/A')} | "
                              f"<b>IP:</b> {device_info.get('ip', 'N/A')} | "
                              f"<b>Тип:</b> {device_info.get('type', 'N/A')}")
            info_label.setStyleSheet("color: #FFC107; padding: 5px; background-color: #444; border-radius: 3px;")
            layout.addWidget(info_label)
        
        # Кнопки
        buttons = QHBoxLayout()
        ok_button = QPushButton("Сохранить")
        cancel_button = QPushButton("Отмена")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; }
            QLineEdit, QTextEdit { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)
    
    def get_data(self):
        """Возвращает данные из формы"""
        data = {
            "description": self.description_input.toPlainText().strip(),
            "master": self.master_input.text().strip(),
            "executor": self.executor_input.text().strip(),
            "call_history": self.call_history_input.toPlainText().strip()
        }
        
        # Добавляем информацию об устройстве, если есть
        if self.device_info:
            data["device_type"] = self.device_info.get("type", "")
            data["device_id"] = self.device_info.get("id", "")
            data["device_name"] = self.device_info.get("name", "")
            data["device_ip"] = self.device_info.get("ip", "")
        
        return data


class AddCallDialog(QDialog):
    """Диалог добавления звонка к существующей неисправности"""
    def __init__(self, parent=None, issue_id=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить звонок")
        self.setFixedSize(400, 250)
        self.issue_id = issue_id
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Тип звонка:"))
        self.call_type = QComboBox()
        self.call_type.addItems(["Отзвон", "Начало работ", "Звонок техника", "Другое"])
        layout.addWidget(self.call_type)
        
        layout.addWidget(QLabel("Комментарий:"))
        self.comment_input = QTextEdit()
        self.comment_input.setMaximumHeight(100)
        layout.addWidget(self.comment_input)
        
        buttons = QHBoxLayout()
        ok_button = QPushButton("Добавить")
        cancel_button = QPushButton("Отмена")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: #FFC107; border: 1px solid #FFC107; }
            QLabel { color: #FFC107; }
            QLineEdit, QTextEdit, QComboBox { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #444; color: #FFC107; border: 1px solid #555; border-radius: 4px; padding: 8px 16px; }
            QPushButton:hover { background-color: #555; }
        """)
    
    def get_data(self):
        """Возвращает данные о звонке"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        call_type = self.call_type.currentText()
        comment = self.comment_input.toPlainText().strip()
        
        return {
            "timestamp": timestamp,
            "type": call_type,
            "comment": comment
        }


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
        
        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels([
            "ID", "Дата", "Описание проблемы", "Заявки", "Мастер", "Исполнитель",
            "Создана", "Передана", "Отзвон", "Начало работ", "История звонков",
            "Устройство", "IP"
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
            QTableWidget { background-color: #444; color: #FFC107; border: 1px solid #555; }
            QTableWidget::item:hover { background-color: #555; }
            QTableWidget::item:selected { background-color: #75736b; color: #333; }
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
        """Заполняет таблицу данными"""
        self.table.setRowCount(len(self.issues))
        
        for row, issue in enumerate(self.issues):
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(issue.get("id", ""))))
            # Дата
            self.table.setItem(row, 1, QTableWidgetItem(issue.get("date", "")))
            # Описание
            self.table.setItem(row, 2, QTableWidgetItem(issue.get("description", "")))
            # Заявки
            self.table.setItem(row, 3, QTableWidgetItem(issue.get("tickets", "")))
            # Мастер
            self.table.setItem(row, 4, QTableWidgetItem(issue.get("master", "")))
            # Исполнитель
            self.table.setItem(row, 5, QTableWidgetItem(issue.get("executor", "")))
            # Создана
            self.table.setItem(row, 6, QTableWidgetItem(issue.get("created", "")))
            # Передана
            self.table.setItem(row, 7, QTableWidgetItem(issue.get("transferred", "")))
            # Отзвон
            self.table.setItem(row, 8, QTableWidgetItem(issue.get("callback", "")))
            # Начало работ
            self.table.setItem(row, 9, QTableWidgetItem(issue.get("work_start", "")))
            # История звонков
            self.table.setItem(row, 10, QTableWidgetItem(issue.get("call_history", "")))
            # Устройство
            device_name = issue.get("device_name", "")
            self.table.setItem(row, 11, QTableWidgetItem(device_name))
            # IP
            device_ip = issue.get("device_ip", "")
            self.table.setItem(row, 12, QTableWidgetItem(device_ip))
    
    def add_issue(self, device_info=None):
        """Добавляет новую неисправность"""
        dialog = AddIssueDialog(self, device_info=device_info)
        if dialog.exec():
            data = dialog.get_data()
            if not data["description"]:
                self.show_message("Описание проблемы обязательно", "error")
                return
            
            # Генерируем ID
            max_id = max([int(issue.get("id", 0)) for issue in self.issues], default=0)
            new_issue = {
                "id": str(max_id + 1),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "description": data["description"],
                "tickets": "",
                "master": data["master"],
                "executor": data["executor"],
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "transferred": "",
                "callback": "",
                "work_start": "",
                "call_history": data["call_history"],
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
        dialog = AddIssueDialog(self, issue_data=issue)
        if dialog.exec():
            data = dialog.get_data()
            issue["description"] = data["description"]
            issue["master"] = data["master"]
            issue["executor"] = data["executor"]
            issue["call_history"] = data["call_history"]
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
        dialog = AddCallDialog(self, issue_id=issue.get("id"))
        if dialog.exec():
            call_data = dialog.get_data()
            timestamp = call_data["timestamp"]
            call_type = call_data["type"]
            comment = call_data["comment"]
            
            # Обновляем соответствующее поле даты
            if call_type == "Отзвон":
                issue["callback"] = timestamp
            elif call_type == "Начало работ":
                issue["work_start"] = timestamp
            
            # Добавляем в историю звонков
            history = issue.get("call_history", "")
            new_entry = f"[{timestamp}] {call_type}: {comment}"
            issue["call_history"] = f"{history}\n{new_entry}" if history else new_entry
            
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
