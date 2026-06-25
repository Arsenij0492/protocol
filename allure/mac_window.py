from PySide6.QtCore import Qt, QRect, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout


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

        self.content = QWidget(self)
        self.content.setMouseTracking(True)
        self.content.setStyleSheet(self._content_style())

        self._main_layout = QVBoxLayout(self.content)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(36)
        self.title_bar.setMouseTracking(True)
        self.title_bar.setStyleSheet(self._title_bar_style())

        self.close_btn = self._create_circle_button("#FF5F56")
        self.min_btn = self._create_circle_button("#FFBD2E")
        self.max_btn = self._create_circle_button("#27C93F")

        self.close_btn.clicked.connect(self.close)
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self.toggle_max_restore)

        self.title_label = QPushButton(f"  {title}  ")
        self.title_label.setFlat(True)
        self.title_label.setEnabled(False)
        self.title_label.setStyleSheet("color: #444444; font-weight: bold; font-size: 12px;")

        left_widget = QWidget()
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        left_layout.addWidget(self.close_btn)
        left_layout.addWidget(self.min_btn)
        left_layout.addWidget(self.max_btn)
        left_widget.setFixedWidth(14 * 3 + 4 * 2)

        right_widget = QWidget()
        right_widget.setFixedWidth(left_widget.width())

        btn_layout = QHBoxLayout(self.title_bar)
        btn_layout.setContentsMargins(10, 0, 10, 0)
        btn_layout.setSpacing(0)
        btn_layout.addWidget(left_widget)
        btn_layout.addStretch()
        btn_layout.addWidget(self.title_label)
        btn_layout.addStretch()
        btn_layout.addWidget(right_widget)

        self._main_layout.addWidget(self.title_bar)

        self.body_widget = QWidget()
        self.body_widget.setMouseTracking(True)
        self.body_widget.setStyleSheet(self._main_bar_style())
        self.body_layout = QVBoxLayout(self.body_widget)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)

        self._main_layout.addWidget(self.body_widget)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self._on_animation_finished)

    def setContentLayout(self, layout):
        self.body_layout.addLayout(layout)

    def _create_circle_button(self, color):
        hover_color = self._darken_color(color, 0.85)
        btn = QPushButton()
        btn.setFixedSize(14, 14)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 7px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)
        return btn

    @staticmethod
    def _darken_color(color_str, factor):
        color = QColor(color_str)
        r = max(0, min(255, int(color.red() * factor)))
        g = max(0, min(255, int(color.green() * factor)))
        b = max(0, min(255, int(color.blue() * factor)))
        return f"rgb({r},{g},{b})"

    @staticmethod
    def _content_style():
        return "background-color: white; border-radius: 8px;"

    @staticmethod
    def _title_bar_style():
        return "background-color: #E9EBEC; border-top-left-radius: 10px; border-top-right-radius: 10px;"

    @staticmethod
    def _main_bar_style():
        return "background: transparent; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px;"

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