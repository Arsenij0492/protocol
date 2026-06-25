from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QMessageBox

from config_manager import get_config, save_config
from logs_manager import log

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = get_config()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Тема"))
        theme_layout = QHBoxLayout()
        self.btn_light = QPushButton("Светлая")
        self.btn_light.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
        self.btn_dark = QPushButton("Тёмная")
        self.btn_dark.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
        
        if self.config.get("theme") == "dark":
            self.btn_dark.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
            self.btn_light.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
        
        self.btn_light.clicked.connect(lambda: self.set_theme("light"))
        self.btn_dark.clicked.connect(lambda: self.set_theme("dark"))
        
        theme_layout.addWidget(self.btn_light)
        theme_layout.addWidget(self.btn_dark)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)
        layout.addSpacing(20)
        
        btn_save = QPushButton("Сохранить настройки")
        btn_save.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 8px; padding: 10px 24px; font-size: 14px; font-weight: 500;")
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #28a745;")
        layout.addWidget(self.status_label)
        layout.addStretch()
    
    def set_theme(self, theme):
        if theme == "dark":
            self.btn_dark.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
            self.btn_light.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
        else:
            self.btn_light.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
            self.btn_dark.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px;")
    
    def save_settings(self):
        self.config["theme"] = "dark" if self.btn_dark.styleSheet().find("#007aff") != -1 else "light"
        save_config(self.config)
        self.status_label.setText("Настройки сохранены")
        log("Настройки сохранены")
        QMessageBox.information(self, "Готово", "Настройки сохранены")