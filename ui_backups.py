import os
import zipfile
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QMessageBox, QLabel

from logs_manager import log

class BackupsTab(QWidget):
    def __init__(self, backups_dir, reports_dir):
        super().__init__()
        self.backups_dir = backups_dir
        self.reports_dir = reports_dir
        os.makedirs(self.backups_dir, exist_ok=True)
        self.init_ui()
        self.load_backups()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        btn_layout = QHBoxLayout()
        btn_create = QPushButton("Создать бэкап")
        btn_create.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500;")
        btn_create.clicked.connect(self.create_backup)
        btn_layout.addWidget(btn_create)
        
        btn_restore = QPushButton("Восстановить")
        btn_restore.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 8px 20px; font-size: 13px; font-weight: 500;")
        btn_restore.clicked.connect(self.restore_backup)
        btn_layout.addWidget(btn_restore)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.backup_list = QListWidget()
        self.backup_list.setStyleSheet("background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 4px;")
        layout.addWidget(self.backup_list)
    
    def load_backups(self):
        self.backup_list.clear()
        for filename in sorted(os.listdir(self.backups_dir), reverse=True):
            if filename.endswith('.zip'):
                filepath = os.path.join(self.backups_dir, filename)
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%d.%m.%Y %H:%M')
                item = QListWidgetItem(f"{filename}  ({mtime})")
                item.setData(Qt.UserRole, filename)
                self.backup_list.addItem(item)
    
    def create_backup(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_{timestamp}.zip"
            filepath = os.path.join(self.backups_dir, filename)
            
            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for f in os.listdir(self.reports_dir):
                    if f.endswith('.html'):
                        zip_file.write(os.path.join(self.reports_dir, f), f)
            
            self.load_backups()
            log(f"Создан бэкап: {filename}")
            QMessageBox.information(self, "Готово", f"Бэкап создан: {filename}")
        except Exception as e:
            log(f"Ошибка создания бэкапа: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
    
    def restore_backup(self):
        selected = self.backup_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Предупреждение", "Выберите бэкап")
            return
        filename = selected.data(Qt.UserRole)
        reply = QMessageBox.question(self, "Подтверждение", f"Восстановить из бэкапа '{filename}'?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            filepath = os.path.join(self.backups_dir, filename)
            with zipfile.ZipFile(filepath, 'r') as zip_file:
                zip_file.extractall(self.reports_dir)
            log(f"Восстановлен бэкап: {filename}")
            QMessageBox.information(self, "Готово", "Бэкап восстановлен")
        except Exception as e:
            log(f"Ошибка восстановления: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
