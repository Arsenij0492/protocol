import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from parsers import get_protocols_list

class StatisticsTab(QWidget):
    def __init__(self, reports_dir):
        super().__init__()
        self.reports_dir = reports_dir
        self.cards = []
        self.init_ui()
        self.load_statistics()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        for label, color in [("Всего протоколов", "#1c1c1e"), ("Пройдено тестов", "#28a745"), ("Упало тестов", "#ed6a5e"), ("Среднее время", "#007aff")]:
            card = QWidget()
            card.setStyleSheet(f"background: #f8f9fa; border-radius: 10px; padding: 14px 16px;")
            card_layout = QVBoxLayout(card)
            number = QLabel("0")
            number.setStyleSheet(f"font-size: 28px; font-weight: 600; color: {color};")
            number.setAlignment(Qt.AlignCenter)
            label_w = QLabel(label)
            label_w.setStyleSheet("font-size: 12px; color: #8e8e93;")
            label_w.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(number)
            card_layout.addWidget(label_w)
            self.cards.append(number)
            stats_layout.addWidget(card)
        
        layout.addLayout(stats_layout)
        layout.addStretch()
    
    def load_statistics(self):
        protocols = get_protocols_list(self.reports_dir)
        total = len(protocols)
        passed = sum(int(p.get('passed', 0)) for p in protocols)
        failed = sum(int(p.get('failed', 0)) for p in protocols)
        durations = [float(p.get('duration', 0)) for p in protocols if p.get('duration')]
        avg = round(sum(durations) / len(durations), 1) if durations else 0
        
        self.cards[0].setText(str(total))
        self.cards[1].setText(str(passed))
        self.cards[2].setText(str(failed))
        self.cards[3].setText(f"{avg}с")
