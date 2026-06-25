import os
import shutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QLabel

from logs_manager import log

class TemplatesTab(QWidget):
    def __init__(self, templates_dir):
        super().__init__()
        self.templates_dir = templates_dir
        self.init_ui()
        self.load_templates()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        btn_layout = QHBoxLayout()
        btn_upload = QPushButton("Загрузить шаблон")
        btn_upload.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500;")
        btn_upload.clicked.connect(self.upload_template)
        btn_layout.addWidget(btn_upload)
        
        btn_reset = QPushButton("Сбросить")
        btn_reset.setStyleSheet("background: #ff3b30; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500;")
        btn_reset.clicked.connect(self.reset_templates)
        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.template_list = QListWidget()
        self.template_list.setStyleSheet("background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 4px;")
        layout.addWidget(self.template_list)
    
    def load_templates(self):
        self.template_list.clear()
        for filename in os.listdir(self.templates_dir):
            if filename.endswith('.html'):
                item = QListWidgetItem(filename)
                item.setData(Qt.UserRole, filename)
                self.template_list.addItem(item)
    
    def upload_template(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите шаблон", "", "HTML (*.html)")
        if file_path:
            filename = os.path.basename(file_path)
            shutil.copy2(file_path, os.path.join(self.templates_dir, filename))
            self.load_templates()
            log(f"Шаблон загружен: {filename}")
            QMessageBox.information(self, "Готово", "Шаблон загружен")
    
    def reset_templates(self):
        reply = QMessageBox.question(self, "Подтверждение", "Сбросить все шаблоны?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            shutil.rmtree(self.templates_dir, ignore_errors=True)
            os.makedirs(self.templates_dir, exist_ok=True)
            self.load_templates()
            log("Шаблоны сброшены")
            QMessageBox.information(self, "Готово", "Шаблоны сброшены")
