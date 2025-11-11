# widgets/add_planed_switch.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QTextEdit, QPushButton
)
from PyQt6.QtCore import QPointF, Qt
import json
import os

class AddPlanedSwitch(QDialog):
    def __init__(self, canvas, position, edit_data=None, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.position = position
        self.edit_data = edit_data
        self.is_edit = edit_data is not None

        self.setWindowTitle("Редактирование планируемого свитча" if self.is_edit else "Добавление планируемого свитча")
        self.setFixedSize(500, 230)
        self.setup_ui()

        if self.is_edit:
            self.name_input.setText(edit_data.get("name", ""))
            self.model_combo.setCurrentText(edit_data.get("model", ""))
            self.note_field.setPlainText(edit_data.get("note", ""))

    def setup_ui(self):
        outer_layout = QVBoxLayout()
        self.setLayout(outer_layout)

        # Заголовок
        title = QLabel("Планируемый управляемый свитч")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-weight: bold; margin: 5px;")
        outer_layout.addWidget(title)

        # Горизонтальный layout
        main_layout = QHBoxLayout()
        outer_layout.addLayout(main_layout)

        # Левая колонка
        left_layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setMaxLength(50)
        self.name_input.setFixedWidth(200)
        self.name_input.setFixedHeight(25)
        left_layout.addWidget(QLabel("Название свитча:"))
        left_layout.addWidget(self.name_input)
        left_layout.addWidget(QLabel("Выберите модель:"))
        self.model_combo = QComboBox()
        self.model_combo.setFixedWidth(200)
        self.model_combo.setFixedHeight(25)
        self.load_models()
        left_layout.addWidget(self.model_combo)
        left_layout.addStretch()

        # Правая колонка
        right_layout = QVBoxLayout()
        self.note_field = QTextEdit()
        self.note_field.setPlaceholderText("Введите примечание...")
        self.note_field.setFixedWidth(250)
        self.note_field.setFixedHeight(120)
        right_layout.addWidget(self.note_field)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("ОК")
        ok_button.setFixedWidth(100)
        ok_button.clicked.connect(self.accept_and_add)
        cancel_button = QPushButton("Отмена")
        cancel_button.setFixedWidth(100)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        button_layout.addStretch()
        outer_layout.addLayout(button_layout)

        # Стили
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #FFC107; }
            QLabel { color: #FFC107; font-size: 13px; }
            QLineEdit, QComboBox, QTextEdit {
                background-color: #444; color: #FFC107;
                border: 1px solid #666; border-radius: 4px; padding: 4px;
            }
            QPushButton { 
                background-color: #333; color: #FFC107;
                border: none; border-radius: 6px; padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #FFC107; color: #333; }
        """)

    def load_models(self):
        try:
            with open("models/models.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                models = data.get("models", []) if isinstance(data, dict) else data
                model_names = [m["model_name"] for m in models if isinstance(m, dict) and "model_name" in m]
                if model_names:
                    self.model_combo.addItems(model_names)
                else:
                    self.model_combo.addItem("Нет моделей")
        except Exception as e:
            print(f"Ошибка загрузки models.json: {e}")
            self.model_combo.addItem("Ошибка загрузки")

    def accept_and_add(self):
        name = self.name_input.text().strip()
        if not name:
            name = f"Планируемый свитч {len(self.canvas.map_data['plan_switches']) + 1}"

        model = self.model_combo.currentText()
        note = self.note_field.toPlainText().strip()

        if self.is_edit:
            self.edit_data["name"] = name
            self.edit_data["model"] = model
            self.edit_data["note"] = note
            print(f"Обновлен plan_switch в map_data: {self.edit_data}")
        else:
            new_id = self.canvas.get_next_id("plan_switches")
            new_switch = {
                "id": new_id,
                "name": name,
                "xy": {"x": self.position.x(), "y": self.position.y()},
                "model": model,
                "note": note
            }
            self.canvas.map_data["plan_switches"].append(new_switch)
            print(f"Добавлен plan_switch в map_data: {new_switch}")

        self.canvas.render_map()
        self.accept()