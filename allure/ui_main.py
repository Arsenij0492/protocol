import os
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QWidget, QListWidget, QListWidgetItem, QFileDialog, QMessageBox
from PySide6.QtWebEngineWidgets import QWebEngineView
from jinja2 import Template

from mac_window import MacWindow
from logs_manager import log
from parsers import parse_cucumber_json, prepare_data, REPORT_TEMPLATE
from config_manager import get_config
from ui_protocols import ProtocolsTab
from ui_statistics import StatisticsTab
from ui_templates import TemplatesTab
from ui_backups import BackupsTab
from ui_logs import LogsTab
from ui_settings import SettingsTab

class MainWindow(MacWindow):
    def __init__(self):
        super().__init__(title="1С Протокол", min_size=(500, 400), default_size=(1200, 800))
        self.selected_files = []
        self.current_html = ""
        self.config = get_config()
        
        # Папки
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.reports_dir = os.path.join(self.base_dir, "reports")
        self.logs_dir = os.path.join(self.base_dir, "logs")
        self.backups_dir = os.path.join(self.base_dir, "backups")
        self.templates_dir = os.path.join(self.base_dir, "templates")
        
        for d in [self.reports_dir, self.logs_dir, self.backups_dir, self.templates_dir]:
            os.makedirs(d, exist_ok=True)
        
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        header = QHBoxLayout()
        title_label = QLabel("1С Протокол")
        title_label.setStyleSheet("font-size: 26px; font-weight: 600; color: #1d1d1f;")
        header.addWidget(title_label)
        header.addStretch()
        self.status_label = QLabel("Готов")
        self.status_label.setStyleSheet("font-size: 13px; color: #8e8e93;")
        header.addWidget(self.status_label)
        layout.addLayout(header)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_main_tab(), "Главная")
        self.tabs.addTab(ProtocolsTab(self.reports_dir), "Протоколы")
        self.tabs.addTab(StatisticsTab(self.reports_dir), "Статистика")
        self.tabs.addTab(TemplatesTab(self.templates_dir), "Шаблоны")
        self.tabs.addTab(BackupsTab(self.backups_dir, self.reports_dir), "Бэкапы")
        self.tabs.addTab(LogsTab(self.logs_dir), "Логи")
        self.tabs.addTab(SettingsTab(), "Настройки")
        layout.addWidget(self.tabs)
        
        self.body_layout.addWidget(central)
        log("✅ Приложение запущено")
    
    def create_main_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        
        btn_row = QHBoxLayout()
        self.btn_select = QPushButton("Выбрать JSON-файлы")
        self.btn_select.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 8px; padding: 10px 24px; font-size: 14px; font-weight: 500;")
        self.btn_select.clicked.connect(self.select_files)
        btn_row.addWidget(self.btn_select)
        
        self.btn_clear = QPushButton("Очистить")
        self.btn_clear.setStyleSheet("background: #ff3b30; color: white; border: none; border-radius: 8px; padding: 10px 24px; font-size: 14px; font-weight: 500;")
        self.btn_clear.clicked.connect(self.clear_files)
        btn_row.addWidget(self.btn_clear)
        
        btn_row.addStretch()
        self.lbl_count = QLabel("Файлов: 0")
        self.lbl_count.setStyleSheet("font-size: 13px; color: #8e8e93;")
        btn_row.addWidget(self.lbl_count)
        layout.addLayout(btn_row)
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        self.file_list.setStyleSheet("QListWidget { background: white; border: 1px solid #d1d1d6; border-radius: 10px; padding: 4px; }")
        self.file_list.itemClicked.connect(self.on_file_click)
        layout.addWidget(self.file_list)
        
        self.btn_generate = QPushButton("Сгенерировать протокол")
        self.btn_generate.setEnabled(False)
        self.btn_generate.setStyleSheet("QPushButton { background: #007aff; color: white; border: none; border-radius: 8px; padding: 12px; font-size: 16px; font-weight: 500; } QPushButton:hover { background: #0066d9; } QPushButton:disabled { background: #a8a8aa; color: #e9ecef; }")
        self.btn_generate.clicked.connect(self.generate_report)
        layout.addWidget(self.btn_generate)
        
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        bottom_row = QHBoxLayout()
        self.btn_pdf = QPushButton("Сохранить PDF")
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.setStyleSheet("QPushButton { background: #007aff; color: white; border: none; border-radius: 8px; padding: 8px 20px; font-size: 14px; font-weight: 500; } QPushButton:disabled { background: #a8a8aa; color: #e9ecef; }")
        self.btn_pdf.clicked.connect(self.save_pdf)
        bottom_row.addWidget(self.btn_pdf)
        
        self.btn_html = QPushButton("Сохранить HTML")
        self.btn_html.setEnabled(False)
        self.btn_html.setStyleSheet("QPushButton { background: #007aff; color: white; border: none; border-radius: 8px; padding: 8px 20px; font-size: 14px; font-weight: 500; } QPushButton:disabled { background: #a8a8aa; color: #e9ecef; }")
        self.btn_html.clicked.connect(self.save_html)
        bottom_row.addWidget(self.btn_html)
        
        bottom_row.addStretch()
        self.lbl_status = QLabel("Выберите JSON-файлы")
        self.lbl_status.setStyleSheet("font-size: 13px; color: #8e8e93;")
        bottom_row.addWidget(self.lbl_status)
        layout.addLayout(bottom_row)
        
        return widget
    
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите JSON-файлы", "", "JSON (*.json)")
        if files:
            self.selected_files.extend(files)
            self.update_file_list()
    
    def clear_files(self):
        self.selected_files = []
        self.file_list.clear()
        self.lbl_count.setText("Файлов: 0")
        self.web_view.setHtml("")
        self.btn_pdf.setEnabled(False)
        self.btn_html.setEnabled(False)
        self.lbl_status.setText("Список очищен")
        self.btn_generate.setEnabled(False)
    
    def update_file_list(self):
        self.file_list.clear()
        for file in self.selected_files:
            item = QListWidgetItem(os.path.basename(file))
            item.setData(Qt.UserRole, file)
            self.file_list.addItem(item)
        self.lbl_count.setText(f"Файлов: {len(self.selected_files)}")
        self.lbl_status.setText(f"Загружено: {len(self.selected_files)}")
        self.btn_generate.setEnabled(len(self.selected_files) > 0)
    
    def on_file_click(self, item):
        file_path = item.data(Qt.UserRole)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                html = f"<html><body style='font-family: Menlo, monospace; padding: 20px; background: #f8f9fa; white-space: pre-wrap; font-size: 12px; color: #1d1d1f;'><h3>{os.path.basename(file_path)}</h3><hr>{content}</body></html>"
                self.web_view.setHtml(html)
        except Exception as e:
            self.web_view.setHtml(f"<p style='color: #ff3b30;'>Ошибка: {e}</p>")
    
    def generate_report(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Ошибка", "Выберите JSON-файлы")
            return
        self.lbl_status.setText("Генерация...")
        tests = parse_cucumber_json(self.selected_files)
        if not tests:
            QMessageBox.warning(self, "Ошибка", "В файлах нет сценариев")
            self.lbl_status.setText("Тестов не найдено")
            return
        data = prepare_data(tests)
        template = Template(REPORT_TEMPLATE)
        html_content = template.render(**data)
        self.current_html = html_content
        self.web_view.setHtml(html_content)
        self.btn_pdf.setEnabled(True)
        self.btn_html.setEnabled(True)
        self.lbl_status.setText(f"Готово. Тестов: {len(tests)}")
        log(f"Сгенерирован отчёт, тестов: {len(tests)}")
    
    def save_pdf(self):
        if not self.current_html:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить PDF", "protocol.pdf", "PDF (*.pdf)")
        if path:
            self.web_view.page().printToPdf(path)
            self.lbl_status.setText(f"PDF сохранён: {os.path.basename(path)}")
            log(f"PDF сохранён: {path}")
    
    def save_html(self):
        if not self.current_html:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить HTML", "protocol.html", "HTML (*.html)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.current_html)
            self.lbl_status.setText(f"HTML сохранён: {os.path.basename(path)}")
            log(f"HTML сохранён: {path}")