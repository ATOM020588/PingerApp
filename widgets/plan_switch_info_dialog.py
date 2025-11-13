# widgets/plan_switch_info_dialog.py
import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QPixmap, QIcon, QColor

class PlanSwitchInfoDialog(QDialog):
    def __init__(self, plan_switch_data, parent=None):
        super().__init__(parent)
        self.plan_switch_data = plan_switch_data

        # 1. Заголовок окна = имя свитча
        switch_name = plan_switch_data.get("name", "Без названия")
        self.setWindowTitle(switch_name)

        self.setFixedSize(520, 410)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setModal(False)  # Не блокирует родительское окно

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # === Создатель и дата ===
        creator = self.plan_switch_data.get("creator", "Неизвестно")
        created_date = self.plan_switch_data.get("created", "")
        if created_date:
            try:
                # Предполагаем ISO: "2025-11-12"
                date_obj = QDate.fromString(created_date.split("T")[0], "yyyy-MM-dd")
                formatted_date = date_obj.toString("dd.MM.yy")
            except:
                formatted_date = created_date
        else:
            formatted_date = ""

        creator_label = QLabel(f"<b>Создал:</b> {creator} <i> {formatted_date} </i>")
        creator_label.setStyleSheet("color: #FFD700; font-size: 12px; border: 0px; ")
        layout.addWidget(creator_label)

        # === Модель ===
        model = self.plan_switch_data.get("model", "—")
        model_label = QLabel(f"<b>Модель:</b> {model}")
        model_label.setStyleSheet("color: #FFD700; border: 0px; ")
        layout.addWidget(model_label)

        # === Изображение модели ===
        image_label = QLabel()
        image_label.setFixedSize(200, 120)   # Размер окна изображения
        image_label.setStyleSheet("background: #333; border-radius: 4px; border: 1px solid #FFC107;")
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Нормализация имени модели
        model = self.plan_switch_data.get("model", "—")
        if model == "—":
            image_label.setText("<i>Модель не указана</i>")
            image_label.setStyleSheet(image_label.styleSheet() + " color: #888;")
        else:
            # 1. Убираем всё, кроме букв, цифр, пробелов, дефисов, подчёркиваний
            # 2. Заменяем множественные пробелы на один
            # 3. Приводим к нижнему регистру
            import re
            model_clean = re.sub(r'[^\w\s.-]', '', model)           # Только безопасные символы
            model_clean = re.sub(r'\s+', ' ', model_clean).strip()  # Один пробел
            model_clean = model_clean.lower()                       # нижний регистр

            image_dir = "images"
            image_found = False

            if os.path.exists(image_dir):
                # Пробуем разные варианты имени файла
                candidates = [
                    f"model_{model_clean}",           # model_des-3200-10_rev_c
                    f"model_{model_clean.replace(' ', '_')}",  # model_des-3200-10_rev_c
                    f"model_{model_clean.replace(' ', '-')}",  # model_des-3200-10-rev-c
                ]

                for base_name in candidates:
                    for ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                        img_path = os.path.join(image_dir, f"{base_name}{ext}")
                        if os.path.exists(img_path):
                            pixmap = QPixmap(img_path)
                            if not pixmap.isNull():
                                # Растягиваем точно под размер image_label (250x200)
                                scaled_pixmap = pixmap.scaled(
                                    200, 120,
                                    Qt.AspectRatioMode.IgnoreAspectRatio,  # Растягиваем без сохранения пропорций
                                    Qt.TransformationMode.SmoothTransformation
                                )
                                image_label.setPixmap(scaled_pixmap)
                            else:
                                image_label.setText("<i>Ошибка загрузки</i>")
                                image_label.setStyleSheet(image_label.styleSheet() + " color: #f55;")
                            image_found = True
                            break
                    if image_found:
                        break

            if not image_found:
                image_label.setText("<i>Изображение отсутствует</i>")
                image_label.setStyleSheet(image_label.styleSheet() + " color: #888;")

        layout.addWidget(image_label)

        # === Примечание ===
        note = self.plan_switch_data.get("note", "").strip()
        note_label = QLabel("<b>Примечание:</b>")
        note_label.setStyleSheet("color: #FFD700; border: 0px; ")
        layout.addWidget(note_label)

        if note:
            note_edit = QTextEdit()
            note_edit.setPlainText(note)
            note_edit.setReadOnly(True)
            note_edit.setFixedHeight(150)
            note_edit.setStyleSheet("""
                QTextEdit { background: #333; color: #FFD700; border-radius: 6px; padding: 8px; font-size: 12px; border: 1px solid #FFC107;}
            """)
            layout.addWidget(note_edit)
        else:
            no_note = QLabel("<i>Примечание отсутствует</i>")
            no_note.setStyleSheet("color: #888; border: 1px solid #FFC107; ")
            no_note.setFixedHeight(150)
            layout.addWidget(no_note)

        layout.addStretch()

        # === Общие стили ===
        self.setStyleSheet("""
            QDialog { background: #2b2b2b; color: #FFD700; border: none;  }
            QLabel { color: #FFD700; margin: 2px 0; }
        """)