import os
import zipfile
import webbrowser
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QCheckBox, QFileDialog, QMessageBox, QLabel
)

from parsers import get_protocols_list
from logs_manager import log

class ProtocolsTab(QWidget):
    def __init__(self, reports_dir):
        super().__init__()
        self.reports_dir = reports_dir
        self.protocols = []
        self.selected_protocols = set()
        self.init_ui()
        self.load_protocols()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setStyleSheet("padding: 6px 12px; border: 1px solid #d1d1d6; border-radius: 6px; font-size: 13px;")
        self.search_input.textChanged.connect(self.filter_protocols)
        search_layout.addWidget(self.search_input)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "passed", "failed"])
        self.filter_combo.setStyleSheet("padding: 6px 12px; border: 1px solid #d1d1d6; border-radius: 6px; font-size: 13px;")
        self.filter_combo.currentTextChanged.connect(self.filter_protocols)
        search_layout.addWidget(self.filter_combo)
        
        btn_refresh = QPushButton("Обновить")
        btn_refresh.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px; font-weight: 500;")
        btn_refresh.clicked.connect(self.load_protocols)
        search_layout.addWidget(btn_refresh)
        
        btn_select_all = QPushButton("Выбрать все")
        btn_select_all.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px; font-weight: 500;")
        btn_select_all.clicked.connect(self.select_all_protocols)
        search_layout.addWidget(btn_select_all)
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        self.action_panel = QWidget()
        self.action_panel.setVisible(False)
        self.action_panel.setStyleSheet("background: #f8f9fa; border-radius: 8px; padding: 8px 16px;")
        action_layout = QHBoxLayout(self.action_panel)
        
        self.selected_count_label = QLabel("Выбрано: 0")
        btn_zip = QPushButton("Скачать ZIP")
        btn_zip.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px; font-weight: 500;")
        btn_zip.clicked.connect(self.download_selected)
        action_layout.addWidget(self.selected_count_label)
        action_layout.addStretch()
        action_layout.addWidget(btn_zip)
        
        btn_delete = QPushButton("Удалить")
        btn_delete.setStyleSheet("background: #ff3b30; color: white; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px; font-weight: 500;")
        btn_delete.clicked.connect(self.delete_selected)
        action_layout.addWidget(btn_delete)
        
        btn_clear_sel = QPushButton("Отменить")
        btn_clear_sel.setStyleSheet("background: #e8e8ec; color: #1c1c1e; border: none; border-radius: 6px; padding: 6px 16px; font-size: 13px; font-weight: 500;")
        btn_clear_sel.clicked.connect(self.clear_selection)
        action_layout.addWidget(btn_clear_sel)
        
        layout.addWidget(self.action_panel)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["", "Имя", "Дата", "Всего", "Пройдено", "Упало", "Время", "Статус"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 200)
        self.table.setStyleSheet("QTableWidget { border: 1px solid #e9ecef; border-radius: 8px; background: white; }")
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.on_protocol_double_click)
        layout.addWidget(self.table)
    
    def load_protocols(self):
        self.protocols = get_protocols_list(self.reports_dir)
        self.filter_protocols()
        log(f"Загружено протоколов: {len(self.protocols)}")
    
    def filter_protocols(self):
        search = self.search_input.text().lower()
        status_filter = self.filter_combo.currentText()
        filtered = [p for p in self.protocols if search in p['name'].lower() and (status_filter == 'Все' or p['status'] == status_filter)]
        
        self.table.setRowCount(len(filtered))
        for row, p in enumerate(filtered):
            checkbox = QCheckBox()
            checkbox.setChecked(p['filename'] in self.selected_protocols)
            checkbox.stateChanged.connect(lambda state, f=p['filename']: self.toggle_protocol(f, state))
            self.table.setCellWidget(row, 0, checkbox)
            
            self.table.setItem(row, 1, QTableWidgetItem(p['name']))
            self.table.setItem(row, 2, QTableWidgetItem(p['date']))
            self.table.setItem(row, 3, QTableWidgetItem(str(p['total'])))
            self.table.setItem(row, 4, QTableWidgetItem(str(p['passed'])))
            self.table.setItem(row, 5, QTableWidgetItem(str(p['failed'])))
            self.table.setItem(row, 6, QTableWidgetItem(f"{p['duration']}с"))
            
            status_item = QTableWidgetItem(p['status'])
            status_item.setForeground(Qt.green if p['status'] == 'passed' else Qt.red)
            self.table.setItem(row, 7, status_item)
            self.table.item(row, 1).setData(Qt.UserRole, p['filename'])
        
        self.update_action_panel()
    
    def toggle_protocol(self, filename, state):
        if state == Qt.Checked:
            self.selected_protocols.add(filename)
        else:
            self.selected_protocols.discard(filename)
        self.update_action_panel()
    
    def select_all_protocols(self):
        for p in self.protocols:
            self.selected_protocols.add(p['filename'])
        self.filter_protocols()
    
    def clear_selection(self):
        self.selected_protocols.clear()
        self.filter_protocols()
    
    def update_action_panel(self):
        count = len(self.selected_protocols)
        self.selected_count_label.setText(f"Выбрано: {count}")
        self.action_panel.setVisible(count > 0)
    
    def on_protocol_double_click(self, item):
        filename = item.data(Qt.UserRole)
        if filename:
            filepath = os.path.join(self.reports_dir, filename)
            if os.path.exists(filepath):
                webbrowser.open(filepath)
                log(f"Открыт протокол: {filename}")
    
    def download_selected(self):
        if not self.selected_protocols:
            return
        save_path, _ = QFileDialog.getSaveFileName(self, "Сохранить ZIP", "protocols.zip", "ZIP Files (*.zip)")
        if not save_path:
            return
        try:
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename in self.selected_protocols:
                    filepath = os.path.join(self.reports_dir, filename)
                    if os.path.exists(filepath):
                        zip_file.write(filepath, filename)
            log(f"Скачано {len(self.selected_protocols)} протоколов в ZIP")
            QMessageBox.information(self, "Готово", f"Скачано {len(self.selected_protocols)} протоколов")
        except Exception as e:
            log(f"Ошибка создания ZIP: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
    
    def delete_selected(self):
        if not self.selected_protocols:
            return
        reply = QMessageBox.question(self, "Подтверждение", f"Удалить {len(self.selected_protocols)} протоколов?", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        deleted = 0
        for filename in list(self.selected_protocols):
            filepath = os.path.join(self.reports_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted += 1
                log(f"Удалён протокол: {filename}")
        self.selected_protocols.clear()
        self.load_protocols()
        QMessageBox.information(self, "Готово", f"Удалено {deleted} протоколов")
