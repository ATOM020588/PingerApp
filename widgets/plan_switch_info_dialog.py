# widgets/plan_switch_info_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
)
from PyQt6.QtCore import Qt

class PlanSwitchInfoDialog(QDialog):
    def __init__(self, plan_switch_data, parent=None):
        super().__init__(parent)
        self.plan_switch_data = plan_switch_data
        self.setWindowTitle("Планируемый свитч")
        self.setFixedSize(500, 350)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Заголовок
        header = QHBoxLayout()
        title = QLabel(self.plan_switch_data.get("name", "Без названия"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFD700;")
        close_btn = QPushButton("X")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton { background: #FFD700; color: #333; border: none; border-radius: 15px; font-weight: bold; }
            QPushButton:hover { background: #e6c200; }
        """)
        close_btn.clicked.connect(self.close)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Основные данные
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)

        info_layout.addWidget(self.make_label(f"<b>Модель:</b> {self.plan_switch_data.get('model', '—')}"))
        info_layout.addWidget(self.make_label(
            f"<b>Координаты:</b> X: {self.plan_switch_data['xy']['x']}, Y: {self.plan_switch_data['xy']['y']}"
        ))

        # Примечание
        note = self.plan_switch_data.get("note", "").strip()
        if note:
            note_edit = QTextEdit()
            note_edit.setPlainText(note)
            note_edit.setReadOnly(True)
            note_edit.setFixedHeight(120)
            info_layout.addWidget(QLabel("<b>Примечание:</b>"))
            info_layout.addWidget(note_edit)
        else:
            info_layout.addWidget(QLabel("<i>Примечание отсутствует</i>"))

        layout.addLayout(info_layout)
        layout.addStretch()

        # Стили
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #FFD700; }
            QLabel { color: #FFD700; margin: 4px 0; }
            QTextEdit { background: #333; color: #FFD700; border: 1px solid #666; border-radius: 6px; padding: 6px; }
        """)

    def make_label(self, text):
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.RichText)
        return label