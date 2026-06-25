import os
import shutil
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QMessageBox
from PySide6.QtCore import Qt

from logs_manager import log

class LogsTab(QWidget):
    def __init__(self, logs_dir):
        super().__init__()
        self.logs_dir = logs_dir
        self.init_ui()
        self.load_logs()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        btn_layout = QHBoxLayout()
        btn_clear = QPushButton("Очистить логи")
        btn_clear.setStyleSheet("background: #ff3b30; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500;")
        btn_clear.clicked.connect(self.clear_logs)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_clear)
        layout.addLayout(btn_layout)
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("background: #f8f9fa; border: 1px solid #d1d1d6; border-radius: 8px; font-family: monospace; font-size: 12px; padding: 10px;")
        layout.addWidget(self.logs_text)
    
    def load_logs(self):
        log_path = os.path.join(self.logs_dir, "app.log")
        if os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='utf-8') as f:
                    self.logs_text.setText(f.read())
            except Exception as e:
                self.logs_text.setText(f"Ошибка чтения логов: {str(e)}")
        else:
            self.logs_text.setText("Логов пока нет")
    
    def clear_logs(self):
        reply = QMessageBox.question(self, "Подтверждение", "Удалить все логи?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            shutil.rmtree(self.logs_dir, ignore_errors=True)
            os.makedirs(self.logs_dir, exist_ok=True)
            self.logs_text.clear()
            log("Логи очищены")
            QMessageBox.information(self, "Готово", "Логи очищены")