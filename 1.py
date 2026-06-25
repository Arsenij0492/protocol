import sys
import os
import json
import shutil
import zipfile
import re
from datetime import datetime
from PySide6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QCursor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QFileDialog,
    QMessageBox, QTabWidget, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QLineEdit, QComboBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from jinja2 import Template


# ============================================================
# 1. MACWINDOW — СТЕКЛЯННЫЙ СТИЛЬ
# ============================================================
class MacWindow(QWidget):
    RESIZE_MARGIN = 8

    def __init__(self, title="1С Протокол", min_size=(400, 300), default_size=(600, 400)):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.resize(*default_size)
        self.setMinimumSize(*min_size)

        self._drag_pos = None
        self._dragging = False
        self._resizing = False
        self._resize_dir = None
        self._normal_geometry = self.geometry()
        self._is_maximized = False
        self._is_animating = False
        self._target_maximize = False

        # Стеклянный фон
        self.content = QWidget(self)
        self.content.setMouseTracking(True)
        self.content.setStyleSheet("""
            QWidget {
                background: rgba(44, 44, 46, 0.92);
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)

        self._main_layout = QVBoxLayout(self.content)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Заголовок (как в macOS)
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setMouseTracking(True)
        self.title_bar.setStyleSheet("""
            QWidget {
                background: rgba(44, 44, 46, 0.8);
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            }
        """)

        self.close_btn = self._create_circle_button("#FF5F56", "#FF7B72")
        self.min_btn = self._create_circle_button("#FFBD2E", "#FFD860")
        self.max_btn = self._create_circle_button("#27C93F", "#4CD964")

        self.close_btn.clicked.connect(self.close)
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_max_restore)

        self.title_label = QLabel(f"{title}")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                color: #e8e8ec;
                font-size: 13px;
                font-weight: 500;
                font-family: -apple-system, "SF Pro Display", "Segoe UI", Arial, sans-serif;
            }
        """)

        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(12, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(self.close_btn)
        left_layout.addWidget(self.min_btn)
        left_layout.addWidget(self.max_btn)
        left_layout.addStretch()

        right_widget = QWidget()
        right_widget.setFixedWidth(left_widget.sizeHint().width())

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        title_layout.addWidget(left_widget)
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(right_widget)

        self._main_layout.addWidget(self.title_bar)

        # Тело окна (контент)
        self.body_widget = QWidget()
        self.body_widget.setMouseTracking(True)
        self.body_widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border-bottom-left-radius: 14px;
                border-bottom-right-radius: 14px;
            }
        """)
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(20, 20, 20, 20)
        self.body_layout.setSpacing(0)

        self._main_layout.addWidget(self.body_widget)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self._on_animation_finished)

    def setContentLayout(self, layout):
        self.body_layout.addLayout(layout)

    def _create_circle_button(self, color, hover_color):
        btn = QPushButton()
        btn.setFixedSize(13, 13)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 7px;
                border: 1px solid rgba(0,0,0,0.08);
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {color};
            }}
        """)
        return btn

    def toggle_max_restore(self):
        if self._is_animating:
            return
        screen_geom = self.screen().availableGeometry()
        self.animation.stop()
        start_geom = self.geometry()
        if self._is_maximized:
            self._target_maximize = False
            end_geom = self._normal_geometry
        else:
            self._normal_geometry = start_geom
            self._target_maximize = True
            end_geom = screen_geom
        self.animation.setStartValue(start_geom)
        self.animation.setEndValue(end_geom)
        self._is_animating = True
        self.animation.start()
        self._is_maximized = not self._is_maximized

    def _on_animation_finished(self):
        if self._target_maximize:
            self.setGeometry(self.screen().availableGeometry())
            super().showMaximized()
        else:
            self.setGeometry(self._normal_geometry)
            super().showNormal()
        self._is_animating = False

    def resizeEvent(self, event):
        self.content.setGeometry(self.rect())
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos()
            self._start_rect = self.geometry()
            self._resize_dir = self._get_resize_direction(event.pos())
            title_bar_pos = self.title_bar.mapFromParent(event.pos())
            if not self._resize_dir and self.title_bar.rect().contains(title_bar_pos):
                self._dragging = True
            elif self._resize_dir:
                self._resizing = True
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        global_pos = event.globalPos()
        if event.buttons() & Qt.LeftButton:
            if self._resizing:
                self._perform_resize(global_pos)
            elif self._dragging:
                delta = global_pos - self._drag_pos
                self.move(self._start_rect.topLeft() + delta)
        else:
            direction = self._get_resize_direction(pos)
            self._set_cursor_by_direction(direction)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging = False
        self._resizing = False
        self._resize_dir = None
        self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        title_bar_pos = self.title_bar.mapFromParent(event.pos())
        if self.title_bar.rect().contains(title_bar_pos):
            self.toggle_max_restore()
        super().mouseDoubleClickEvent(event)

    def _get_resize_direction(self, pos: QPoint):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = self.RESIZE_MARGIN
        left = x <= m
        right = x >= w - m
        top = y <= m
        bottom = y >= h - m
        if left and top:
            return "top_left"
        if right and bottom:
            return "bottom_right"
        if right and top:
            return "top_right"
        if left and bottom:
            return "bottom_left"
        if top:
            return "top"
        if bottom:
            return "bottom"
        if left:
            return "left"
        if right:
            return "right"
        return None

    def _set_cursor_by_direction(self, direction):
        cursors = {
            "top": Qt.SizeVerCursor,
            "bottom": Qt.SizeVerCursor,
            "left": Qt.SizeHorCursor,
            "right": Qt.SizeHorCursor,
            "top_left": Qt.SizeFDiagCursor,
            "bottom_right": Qt.SizeFDiagCursor,
            "top_right": Qt.SizeBDiagCursor,
            "bottom_left": Qt.SizeBDiagCursor,
        }
        if direction:
            self.setCursor(QCursor(cursors[direction]))
        else:
            self.setCursor(Qt.ArrowCursor)

    def _perform_resize(self, global_pos: QPoint):
        delta = global_pos - self._drag_pos
        rect = QRect(self._start_rect)
        min_w = self.minimumWidth()
        min_h = self.minimumHeight()
        dx = delta.x()
        dy = delta.y()
        d = self._resize_dir
        if d in ("left", "top_left", "bottom_left"):
            new_width = rect.width() - dx
            if new_width < min_w:
                dx = rect.width() - min_w
                new_width = min_w
            rect.setX(rect.x() + dx)
            rect.setWidth(new_width)
        elif d in ("right", "top_right", "bottom_right"):
            new_width = rect.width() + dx
            if new_width < min_w:
                new_width = min_w
            rect.setWidth(new_width)
        if d in ("top", "top_left", "top_right"):
            new_height = rect.height() - dy
            if new_height < min_h:
                dy = rect.height() - min_h
                new_height = min_h
            rect.setY(rect.y() + dy)
            rect.setHeight(new_height)
        elif d in ("bottom", "bottom_left", "bottom_right"):
            new_height = rect.height() + dy
            if new_height < min_h:
                new_height = min_h
            rect.setHeight(new_height)
        self.setGeometry(rect)


# ============================================================
# 2. ЛОГИРОВАНИЕ И КОНФИГ
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
BACKUPS_DIR = os.path.join(BASE_DIR, "backups")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

for d in [LOG_DIR, REPORTS_DIR, BACKUPS_DIR, TEMPLATES_DIR]:
    os.makedirs(d, exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(os.path.join(LOG_DIR, "app.log"), 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def log_error(error_data):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"error_{timestamp}.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, ensure_ascii=False, indent=2)

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"theme": "dark"}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================
# 3. ПАРСЕР
# ============================================================
def parse_cucumber_json(file_paths):
    tests = []
    for filepath in file_paths:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = [data]
            for feature in data:
                feature_name = feature.get('name', 'Без имени фичи')
                for scenario in feature.get('elements', []):
                    if scenario.get('type') != 'scenario':
                        continue
                    scenario_name = scenario.get('name', 'Без имени сценария')
                    steps = []
                    has_failed = False
                    error_text = ""
                    for step in scenario.get('steps', []):
                        result = step.get('result', {})
                        status = result.get('status', 'unknown')
                        duration = result.get('duration', 0)
                        error = result.get('error_message', '')
                        if status == 'failed':
                            has_failed = True
                            if not error_text:
                                error_text = error
                        step_name = step.get('name', '')
                        keyword = step.get('keyword', '')
                        steps.append({
                            'text': f"{keyword} {step_name}".strip(),
                            'status': status,
                            'duration': round(duration / 1000000, 1) if duration else 0
                        })
                    total_duration = round(sum(s['duration'] for s in steps), 1)
                    status = 'failed' if has_failed else 'passed'
                    tests.append({
                        'name': f"{feature_name} → {scenario_name}",
                        'status': status,
                        'time': total_duration,
                        'error': error_text,
                        'steps': steps,
                        'tags': [tag.get('name') for tag in scenario.get('tags', [])]
                    })
        except Exception as e:
            log_error({"file": filepath, "error": str(e), "timestamp": datetime.now().isoformat()})
    return tests

def prepare_data(tests, filename=""):
    total = len(tests)
    passed = len([t for t in tests if t['status'] == 'passed'])
    failed = len([t for t in tests if t['status'] == 'failed'])
    duration = sum(t['time'] for t in tests)
    return {
        'REPORT_TITLE': f'Протокол: {filename}' if filename else 'Протокол тестирования',
        'REPORT_DATE': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'TOTAL_TESTS': total,
        'PASSED': passed,
        'FAILED': failed,
        'DURATION': round(duration, 1),
        'TESTS': tests
    }

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ REPORT_TITLE }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background: #1c1c1e; padding: 30px; color: #e8e8ec; }
        .container { max-width: 1200px; margin: 0 auto; background: #2c2c2e; border-radius: 16px; padding: 35px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); }
        h1 { font-size: 26px; font-weight: 600; margin-bottom: 4px; color: #e8e8ec; }
        .subtitle { color: #8e8e93; font-size: 14px; margin-bottom: 25px; }
        .stats { display: flex; gap: 16px; margin-bottom: 25px; flex-wrap: wrap; }
        .stat { background: #3a3a3c; border-radius: 10px; padding: 12px 24px; text-align: center; flex: 1; min-width: 80px; }
        .stat .num { font-size: 28px; font-weight: 600; color: #e8e8ec; }
        .stat .label { font-size: 13px; color: #8e8e93; margin-top: 2px; }
        .stat.passed .num { color: #34c759; }
        .stat.failed .num { color: #ff3b30; }
        .stat.time .num { color: #007aff; font-size: 22px; }
        .test { background: #3a3a3c; border-radius: 10px; margin-bottom: 10px; padding: 16px 20px; }
        .test:hover { background: #4a4a4c; }
        .test-header { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }
        .test-status { font-size: 12px; font-weight: 600; padding: 2px 14px; border-radius: 20px; background: #1a3a2a; color: #34c759; text-transform: uppercase; }
        .test-status.failed { background: #3a1a1a; color: #ff3b30; }
        .test-name { font-weight: 500; font-size: 15px; flex: 1; color: #e8e8ec; }
        .test-time { color: #8e8e93; font-size: 13px; }
        .step-toggle { color: #007aff; font-size: 13px; cursor: pointer; background: none; border: none; font-family: inherit; padding: 2px 0; }
        .step-toggle:hover { opacity: 0.7; }
        .steps-container { margin-top: 8px; }
        .steps-container.hidden { display: none; }
        .steps { background: #2c2c2e; border-radius: 8px; padding: 10px 14px; font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; font-size: 13px; }
        .step { padding: 4px 0; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #4a4a4c; }
        .step:last-child { border-bottom: none; }
        .step-icon { min-width: 16px; }
        .step.passed .step-icon { color: #34c759; }
        .step.failed .step-icon { color: #ff3b30; }
        .step.skipped .step-icon { color: #f59e0b; }
        .step-text { flex: 1; word-break: break-word; color: #e8e8ec; }
        .step-duration { color: #8e8e93; font-size: 12px; }
        .error { background: #3a1a1a; padding: 12px 16px; border-radius: 8px; margin-top: 8px; font-family: 'SF Mono', 'Menlo', 'Consolas', monospace; font-size: 13px; white-space: pre-wrap; color: #ff6b60; }
        .error strong { color: #ff3b30; }
        .arrow { display: inline-block; transition: transform 0.2s; margin-right: 4px; }
        .arrow.open { transform: rotate(90deg); }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #4a4a4c; color: #8e8e93; font-size: 13px; text-align: center; }
        .hidden { display: none; }
        @media print { body { background: white; padding: 20px; } .container { box-shadow: none; border-radius: 0; padding: 20px; } .test { break-inside: avoid; } }
    </style>
    <script>
        function toggleSteps(id) {
            const container = document.getElementById('steps-' + id);
            const arrow = document.getElementById('arrow-' + id);
            if (container.classList.contains('hidden')) {
                container.classList.remove('hidden');
                arrow.classList.add('open');
            } else {
                container.classList.add('hidden');
                arrow.classList.remove('open');
            }
        }
        function downloadPDF() { window.print(); }
    </script>
</head>
<body>
<div class="container">
    <h1>{{ REPORT_TITLE }}</h1>
    <div class="subtitle">{{ REPORT_DATE }}</div>
    <div class="stats">
        <div class="stat"><div class="num">{{ TOTAL_TESTS }}</div><div class="label">Всего</div></div>
        <div class="stat passed"><div class="num">{{ PASSED }}</div><div class="label">Пройдено</div></div>
        <div class="stat failed"><div class="num">{{ FAILED }}</div><div class="label">Упало</div></div>
        <div class="stat time"><div class="num">{{ DURATION }}с</div><div class="label">Время</div></div>
    </div>
    <div style="margin-bottom: 16px;">
        <button onclick="downloadPDF()" style="padding: 8px 20px; background: #007aff; color: white; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; font-family: inherit;">Сохранить PDF</button>
    </div>
    {% for test in TESTS %}
    {% set id = loop.index %}
    <div class="test">
        <div class="test-header">
            <span class="test-status {% if test.status == 'failed' %}failed{% endif %}">{{ test.status }}</span>
            <span class="test-name">{{ test.name }}</span>
            <span class="test-time">{{ test.time }}с</span>
            {% if test.steps %}
            <button class="step-toggle" onclick="toggleSteps('{{ id }}')">
                <span class="arrow open" id="arrow-{{ id }}">▶</span> Шаги ({{ test.steps|length }})
            </button>
            {% endif %}
        </div>
        {% if test.tags %}
        <div class="test-tags" style="display: flex; gap: 6px; flex-wrap: wrap; margin: 6px 0 8px 0;">
            {% for tag in test.tags %}
            <span style="background: #4a4a4c; padding: 2px 12px; border-radius: 12px; font-size: 12px; color: #8e8e93;">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}
        {% if test.steps %}
        <div id="steps-{{ id }}">
            <div class="steps">
                {% for step in test.steps %}
                <div class="step {% if step.status == 'passed' %}passed{% elif step.status == 'skipped' %}skipped{% else %}failed{% endif %}">
                    <span class="step-icon">●</span>
                    <span class="step-text">{{ step.text }}</span>
                    <span class="step-duration">{{ step.duration }}мс</span>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        {% if test.status == 'failed' and test.error %}
        <div class="error"><strong>Ошибка:</strong> {{ test.error }}</div>
        {% endif %}
    </div>
    {% endfor %}
    <div class="footer">Сгенерировано автоматически</div>
</div>
</body>
</html>
"""

def get_protocols_list():
    protocols = []
    for filename in sorted(os.listdir(REPORTS_DIR), reverse=True):
        if filename.endswith('.html'):
            filepath = os.path.join(REPORTS_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    total_match = re.search(r'Всего.*?(\d+)', content)
                    passed_match = re.search(r'Пройдено.*?(\d+)', content)
                    failed_match = re.search(r'Упало.*?(\d+)', content)
                    duration_match = re.search(r'Время.*?([\d.]+)с', content)
                    protocols.append({
                        'filename': filename,
                        'name': filename.replace('.html', ''),
                        'date': datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%d.%m.%Y %H:%M'),
                        'total': total_match.group(1) if total_match else '0',
                        'passed': passed_match.group(1) if passed_match else '0',
                        'failed': failed_match.group(1) if failed_match else '0',
                        'duration': duration_match.group(1) if duration_match else '0',
                        'status': 'failed' if (failed_match and int(failed_match.group(1)) > 0) else 'passed'
                    })
            except:
                pass
    return protocols


# ============================================================
# 4. ГЛАВНОЕ ОКНО (СТИЛЬ КАК В ВЕБЕ)
# ============================================================
class MainWindow(MacWindow):
    def __init__(self):
        log("🚀 Запуск приложения")
        super().__init__(title="1С Протокол", min_size=(500, 400), default_size=(1200, 800))
        
        self.selected_files = []
        self.current_html = ""
        self.config = get_config()
        self.selected_protocols = set()
        self.all_protocols = []
        
        # ===== ГЛОБАЛЬНЫЙ СТИЛЬ (КАК В ВЕБЕ) =====
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                color: #e8e8ec;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Arial, sans-serif;
            }
            QTabWidget::pane {
                border: none;
                background: transparent;
                margin-top: -1px;
            }
            QTabBar::tab {
                padding: 8px 24px;
                margin: 0 4px;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 500;
                color: #8e8e93;
                background: transparent;
            }
            QTabBar::tab:hover {
                color: #e8e8ec;
                background: rgba(255, 255, 255, 0.04);
            }
            QTabBar::tab:selected {
                background: rgba(0, 122, 255, 0.12);
                color: #4a9aff;
            }
            QPushButton {
                background: #007aff;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 24px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #0066d9;
            }
            QPushButton:disabled {
                background: #3a3a3c;
                color: #8e8e93;
            }
            QPushButton#danger {
                background: #ed6a5e;
            }
            QPushButton#danger:hover {
                background: #e85a4e;
            }
            QListWidget {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 10px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px 14px;
                border-radius: 6px;
                color: #e8e8ec;
            }
            QListWidget::item:selected {
                background: rgba(0, 122, 255, 0.12);
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.04);
            }
            QTableWidget {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 8px 12px;
                color: #e8e8ec;
            }
            QTableWidget::item:selected {
                background: rgba(0, 122, 255, 0.12);
            }
            QHeaderView::section {
                background: rgba(255, 255, 255, 0.04);
                color: #8e8e93;
                padding: 8px;
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.04);
                font-weight: 500;
            }
            QLineEdit, QTextEdit, QComboBox {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.04);
                border-radius: 8px;
                padding: 8px 14px;
                color: #e8e8ec;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #007aff;
            }
            QTextEdit {
                background: rgba(255, 255, 255, 0.04);
            }
            QCheckBox {
                color: #e8e8ec;
            }
            QLabel {
                color: #e8e8ec;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)
        
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header = QHBoxLayout()
        title_label = QLabel("1С Протокол")
        title_label.setStyleSheet("font-size: 28px; font-weight: 700; color: #e8e8ec; margin-bottom: 8px;")
        header.addWidget(title_label)
        header.addStretch()
        self.status_label = QLabel("Готов")
        self.status_label.setStyleSheet("font-size: 13px; color: #8e8e93;")
        header.addWidget(self.status_label)
        layout.addLayout(header)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_main_tab(), "Главная")
        self.tabs.addTab(self.create_protocols_tab(), "Протоколы")
        self.tabs.addTab(self.create_statistics_tab(), "Статистика")
        self.tabs.addTab(self.create_templates_tab(), "Шаблоны")
        self.tabs.addTab(self.create_backups_tab(), "Бэкапы")
        self.tabs.addTab(self.create_logs_tab(), "Логи")
        self.tabs.addTab(self.create_settings_tab(), "Настройки")
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
        self.btn_clear.setObjectName("danger")
        self.btn_clear.clicked.connect(self.clear_files)
        btn_row.addWidget(self.btn_clear)
        
        btn_row.addStretch()
        self.lbl_count = QLabel("Файлов: 0")
        self.lbl_count.setStyleSheet("font-size: 13px; color: #8e8e93;")
        btn_row.addWidget(self.lbl_count)
        layout.addLayout(btn_row)
        
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(150)
        self.file_list.itemClicked.connect(self.on_file_click)
        layout.addWidget(self.file_list)
        
        self.btn_generate = QPushButton("Сгенерировать протокол")
        self.btn_generate.setEnabled(False)
        self.btn_generate.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 10px; padding: 14px; font-size: 16px; font-weight: 600;")
        self.btn_generate.clicked.connect(self.generate_report)
        layout.addWidget(self.btn_generate)
        
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.04);")
        layout.addWidget(self.web_view)
        
        bottom_row = QHBoxLayout()
        self.btn_pdf = QPushButton("Сохранить PDF")
        self.btn_pdf.setEnabled(False)
        self.btn_pdf.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 8px; padding: 8px 20px; font-size: 14px; font-weight: 500;")
        self.btn_pdf.clicked.connect(self.save_pdf)
        bottom_row.addWidget(self.btn_pdf)
        
        self.btn_html = QPushButton("Сохранить HTML")
        self.btn_html.setEnabled(False)
        self.btn_html.setStyleSheet("background: #007aff; color: white; border: none; border-radius: 8px; padding: 8px 20px; font-size: 14px; font-weight: 500;")
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
                html = f"<html><body style='font-family: Menlo, monospace; padding: 20px; background: #2c2c2e; white-space: pre-wrap; font-size: 12px; color: #e8e8ec;'><h3 style='color: #e8e8ec;'>{os.path.basename(file_path)}</h3><hr style='border-color: rgba(255,255,255,0.04);'>{content}</body></html>"
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
    
    def create_protocols_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.textChanged.connect(self.filter_protocols)
        search_layout.addWidget(self.search_input)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Все", "passed", "failed"])
        self.filter_combo.currentTextChanged.connect(self.filter_protocols)
        search_layout.addWidget(self.filter_combo)
        
        btn_refresh = QPushButton("Обновить")
        btn_refresh.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        btn_refresh.clicked.connect(self.load_protocols)
        search_layout.addWidget(btn_refresh)
        
        btn_select_all = QPushButton("Выбрать все")
        btn_select_all.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        btn_select_all.clicked.connect(self.select_all_protocols)
        search_layout.addWidget(btn_select_all)
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        self.action_panel = QWidget()
        self.action_panel.setVisible(False)
        self.action_panel.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 8px; padding: 8px 16px;")
        action_layout = QHBoxLayout(self.action_panel)
        
        self.selected_count_label = QLabel("Выбрано: 0")
        btn_zip = QPushButton("Скачать ZIP")
        btn_zip.setStyleSheet("background: #007aff; color: white;")
        btn_zip.clicked.connect(self.download_selected)
        action_layout.addWidget(self.selected_count_label)
        action_layout.addStretch()
        action_layout.addWidget(btn_zip)
        
        btn_delete = QPushButton("Удалить")
        btn_delete.setObjectName("danger")
        btn_delete.clicked.connect(self.delete_selected)
        action_layout.addWidget(btn_delete)
        
        btn_clear_sel = QPushButton("Отменить")
        btn_clear_sel.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        btn_clear_sel.clicked.connect(self.clear_selection)
        action_layout.addWidget(btn_clear_sel)
        
        layout.addWidget(self.action_panel)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["", "Имя", "Дата", "Всего", "Пройдено", "Упало", "Время", "Статус"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 200)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemDoubleClicked.connect(self.on_protocol_double_click)
        layout.addWidget(self.table)
        
        self.load_protocols()
        return widget
    
    def load_protocols(self):
        self.all_protocols = get_protocols_list()
        self.filter_protocols()
        log(f"Загружено протоколов: {len(self.all_protocols)}")
    
    def filter_protocols(self):
        search = self.search_input.text().lower()
        status_filter = self.filter_combo.currentText()
        filtered = [p for p in self.all_protocols if search in p['name'].lower() and (status_filter == 'Все' or p['status'] == status_filter)]
        
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
            status_item.setForeground(QColor("#34c759") if p['status'] == 'passed' else QColor("#ff3b30"))
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
        for p in self.all_protocols:
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
            filepath = os.path.join(REPORTS_DIR, filename)
            if os.path.exists(filepath):
                import webbrowser
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
                    filepath = os.path.join(REPORTS_DIR, filename)
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
            filepath = os.path.join(REPORTS_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted += 1
                log(f"Удалён протокол: {filename}")
        self.selected_protocols.clear()
        self.load_protocols()
        self.load_statistics()
        QMessageBox.information(self, "Готово", f"Удалено {deleted} протоколов")
    
    def create_statistics_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        
        self.stat_cards = []
        for label, color in [("Всего протоколов", "#e8e8ec"), ("Пройдено тестов", "#34c759"), ("Упало тестов", "#ff3b30"), ("Среднее время", "#007aff")]:
            card = QWidget()
            card.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 10px; padding: 14px 16px;")
            card_layout = QVBoxLayout(card)
            number = QLabel("0")
            number.setStyleSheet(f"font-size: 28px; font-weight: 600; color: {color};")
            number.setAlignment(Qt.AlignCenter)
            label_w = QLabel(label)
            label_w.setStyleSheet("font-size: 12px; color: #8e8e93;")
            label_w.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(number)
            card_layout.addWidget(label_w)
            self.stat_cards.append(number)
            stats_layout.addWidget(card)
        
        layout.addLayout(stats_layout)
        
        btn_refresh_stats = QPushButton("Обновить статистику")
        btn_refresh_stats.setStyleSheet("background: #007aff; color: white;")
        btn_refresh_stats.clicked.connect(self.load_statistics)
        layout.addWidget(btn_refresh_stats)
        
        self.load_statistics()
        layout.addStretch()
        return widget
    
    def load_statistics(self):
        protocols = get_protocols_list()
        total = len(protocols)
        passed = sum(int(p.get('passed', 0)) for p in protocols)
        failed = sum(int(p.get('failed', 0)) for p in protocols)
        durations = [float(p.get('duration', 0)) for p in protocols if p.get('duration')]
        avg = round(sum(durations) / len(durations), 1) if durations else 0
        
        self.stat_cards[0].setText(str(total))
        self.stat_cards[1].setText(str(passed))
        self.stat_cards[2].setText(str(failed))
        self.stat_cards[3].setText(f"{avg}с")
    
    def create_templates_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        btn_layout = QHBoxLayout()
        btn_upload = QPushButton("Загрузить шаблон")
        btn_upload.setStyleSheet("background: #007aff; color: white;")
        btn_upload.clicked.connect(self.upload_template)
        btn_layout.addWidget(btn_upload)
        
        btn_reset = QPushButton("Сбросить")
        btn_reset.setObjectName("danger")
        btn_reset.clicked.connect(self.reset_template)
        btn_layout.addWidget(btn_reset)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.template_list = QListWidget()
        layout.addWidget(self.template_list)
        
        self.load_templates()
        return widget
    
    def load_templates(self):
        self.template_list.clear()
        for filename in os.listdir(TEMPLATES_DIR):
            if filename.endswith('.html'):
                item = QListWidgetItem(filename)
                item.setData(Qt.UserRole, filename)
                self.template_list.addItem(item)
    
    def upload_template(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите шаблон", "", "HTML (*.html)")
        if file_path:
            shutil.copy2(file_path, os.path.join(TEMPLATES_DIR, os.path.basename(file_path)))
            self.load_templates()
            log(f"Шаблон загружен: {os.path.basename(file_path)}")
            QMessageBox.information(self, "Готово", "Шаблон загружен")
    
    def reset_template(self):
        reply = QMessageBox.question(self, "Подтверждение", "Сбросить все шаблоны?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            shutil.rmtree(TEMPLATES_DIR, ignore_errors=True)
            os.makedirs(TEMPLATES_DIR, exist_ok=True)
            self.load_templates()
            log("Шаблоны сброшены")
            QMessageBox.information(self, "Готово", "Шаблоны сброшены")
    
    def create_backups_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        btn_layout = QHBoxLayout()
        btn_create = QPushButton("Создать бэкап")
        btn_create.setStyleSheet("background: #007aff; color: white;")
        btn_create.clicked.connect(self.create_backup)
        btn_layout.addWidget(btn_create)
        
        btn_restore = QPushButton("Восстановить")
        btn_restore.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        btn_restore.clicked.connect(self.restore_backup)
        btn_layout.addWidget(btn_restore)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        self.backup_list = QListWidget()
        layout.addWidget(self.backup_list)
        
        self.load_backups()
        return widget
    
    def load_backups(self):
        self.backup_list.clear()
        for filename in sorted(os.listdir(BACKUPS_DIR), reverse=True):
            if filename.endswith('.zip'):
                filepath = os.path.join(BACKUPS_DIR, filename)
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%d.%m.%Y %H:%M')
                item = QListWidgetItem(f"{filename}  ({mtime})")
                item.setData(Qt.UserRole, filename)
                self.backup_list.addItem(item)
    
    def create_backup(self):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"backup_{timestamp}.zip"
            filepath = os.path.join(BACKUPS_DIR, filename)
            with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for f in os.listdir(REPORTS_DIR):
                    if f.endswith('.html'):
                        zip_file.write(os.path.join(REPORTS_DIR, f), f)
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
            filepath = os.path.join(BACKUPS_DIR, filename)
            with zipfile.ZipFile(filepath, 'r') as zip_file:
                zip_file.extractall(REPORTS_DIR)
            self.load_protocols()
            self.load_statistics()
            log(f"Восстановлен бэкап: {filename}")
            QMessageBox.information(self, "Готово", "Бэкап восстановлен")
        except Exception as e:
            log(f"Ошибка восстановления: {str(e)}")
            QMessageBox.critical(self, "Ошибка", str(e))
    
    def create_logs_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        btn_layout = QHBoxLayout()
        btn_clear = QPushButton("Очистить логи")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(self.clear_logs)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_clear)
        layout.addLayout(btn_layout)
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.04); border-radius: 8px; font-family: 'SF Mono', monospace; font-size: 12px; padding: 10px;")
        layout.addWidget(self.logs_text)
        
        self.load_logs()
        return widget
    
    def load_logs(self):
        log_path = os.path.join(LOG_DIR, "app.log")
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
            shutil.rmtree(LOG_DIR, ignore_errors=True)
            os.makedirs(LOG_DIR, exist_ok=True)
            self.logs_text.clear()
            log("Логи очищены")
            QMessageBox.information(self, "Готово", "Логи очищены")
    
    def create_settings_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        config = get_config()
        
        layout.addWidget(QLabel("Тема"))
        theme_layout = QHBoxLayout()
        self.btn_light = QPushButton("Светлая")
        self.btn_light.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        self.btn_dark = QPushButton("Тёмная")
        self.btn_dark.setStyleSheet("background: #007aff; color: white;")
        
        if config.get("theme") == "dark":
            self.btn_dark.setStyleSheet("background: #007aff; color: white;")
            self.btn_light.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        else:
            self.btn_light.setStyleSheet("background: #007aff; color: white;")
            self.btn_dark.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        
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
        
        self.status_label_settings = QLabel("")
        self.status_label_settings.setStyleSheet("color: #34c759;")
        layout.addWidget(self.status_label_settings)
        layout.addStretch()
        return widget
    
    def set_theme(self, theme):
        if theme == "dark":
            self.btn_dark.setStyleSheet("background: #007aff; color: white;")
            self.btn_light.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        else:
            self.btn_light.setStyleSheet("background: #007aff; color: white;")
            self.btn_dark.setStyleSheet("background: rgba(255,255,255,0.04); color: #e8e8ec;")
        self.config["theme"] = theme
        save_config(self.config)
        self.status_label_settings.setText("Тема изменена. Перезапустите приложение для применения.")
    
    def save_settings(self):
        save_config(self.config)
        self.status_label_settings.setText("Настройки сохранены")
        log("Настройки сохранены")
        QMessageBox.information(self, "Готово", "Настройки сохранены")


# ============================================================
# 5. ЗАПУСК
# ============================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())