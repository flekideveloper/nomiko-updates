"""NOMIKO desktop browser. Custom chrome; Qt WebEngine handles web rendering."""
from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys
import subprocess
import time

from math import cos, pi, sin
from urllib.parse import parse_qs, quote_plus
import json

from PySide6.QtCore import QEvent, QPoint, QPointF, QTimer, QUrl, Qt, QSize, Signal, QRect, QRectF
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon, QKeySequence, QPainter, QPainterPath, QPen, QPolygonF, QPixmap, QImageReader
from PySide6.QtWidgets import (
    QSizePolicy,
    QApplication, QBoxLayout, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QSplitter, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea, QTabWidget,
    QStackedWidget, QTabBar, QToolButton, QToolTip, QVBoxLayout, QWidget, QWidgetAction,
)
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWebEngineWidgets import QWebEngineView

from .home import render_home, render_search_results
from .tab_drag import drop_index, neighbor_shift
from .update_trust import CURRENT_VERSION
from .update_ui import UpdateCenter, UpdateWorker
from .productivity import safe_web_url, render_reader
from .advanced_ui import import_export_dialog, WorkspaceDialog, VaultDialog, SplitViewTab
from .theme_studio import ThemeStudioDialog
from .module_packs import load_hosts
from .settings_page import SettingsPane
from .managers import HistoryDialog, BookmarksDialog, DownloadsDialog
from .i18n import LANGUAGES, tr

from .privacy import TrackerInterceptor
from .blocklists import clean_tracking_url
from .storage import APP_DIR, SEARCH_ENGINES, Store, is_navigation_input, resolve_input, readable_accent, TOOLBAR_ITEMS, MENU_ITEMS, APP_DIR


class IconButton(QToolButton):
    """Consistent vector buttons. Glyph artwork can change without changing hitboxes."""
    def __init__(self, glyph: str, tip: str, callback, size=(36, 36), parent=None):
        super().__init__(parent)
        self.glyph = glyph
        self.glyph_color = '#9A82FF'
        self.custom_color = None
        self.setToolTip(tip)
        self.setFixedSize(*size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(callback)
        self._tip_timer = QTimer(self)
        self._tip_timer.setSingleShot(True)
        self._tip_timer.setInterval(1000)
        self._tip_timer.timeout.connect(self._show_tip)

    def enterEvent(self, event):  # noqa: N802
        self._tip_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self._tip_timer.stop()
        QToolTip.hideText()
        super().leaveEvent(event)

    def event(self, event):
        if event.type() == QEvent.Type.ToolTip:
            return True  # Only show our tooltip after the full 1000 ms delay.
        return super().event(event)

    def _show_tip(self):
        if self.isVisible() and self.isEnabled() and self.underMouse():
            # Top row has no space above: show below, otherwise above.
            local_y = self.height() + 7 if self.mapToGlobal(QPoint(0, 0)).y() < 42 else -9
            QToolTip.showText(self.mapToGlobal(QPoint(self.width() // 2, local_y)),
                              self.toolTip(), self, self.rect(), 3500)

    def paintEvent(self, event):  # noqa: N802
        super().paintEvent(event)  # Draw Qt hover/pressed state, not a text glyph.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor((self.custom_color or self.glyph_color) if self.isEnabled() else '#727685')
        painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        x, y = self.width() / 2, self.height() / 2
        g = self.glyph
        if g in ('back', 'forward'):
            y -= 3
            sign = -1 if g == 'back' else 1
            tip = x + 9 * sign
            tail = x - 8 * sign
            painter.drawLine(QPointF(tip, y), QPointF(tail, y))
            painter.drawLine(QPointF(tip, y), QPointF(tip - 7 * sign, y - 7))
            painter.drawLine(QPointF(tip, y), QPointF(tip - 7 * sign, y + 7))
        elif g == 'reload':
            y -= 1
            painter.drawArc(int(x-8), int(y-8), 16, 16, 35*16, 290*16)
            painter.drawLine(QPointF(x + 7, y - 2), QPointF(x + 8, y - 8))
            painter.drawLine(QPointF(x + 8, y - 8), QPointF(x + 2, y - 7))
        elif g == 'home':
            y -= 3
            painter.drawLine(QPointF(x-9, y), QPointF(x, y-8))
            painter.drawLine(QPointF(x, y-8), QPointF(x+9, y))
            painter.drawLine(QPointF(x-6, y-2), QPointF(x-6, y+8))
            painter.drawLine(QPointF(x+6, y-2), QPointF(x+6, y+8))
            painter.drawLine(QPointF(x-6, y+8), QPointF(x+6, y+8))
        elif g in ('star', 'star-filled'):
            # Slightly smaller than navigation buttons.
            pts = []
            for i in range(10):
                r = 7.8 if i % 2 == 0 else 3.6
                a = -pi / 2 + i * pi / 5
                pts.append(QPointF(x + cos(a)*r, y + sin(a)*r))
            path = QPainterPath()
            path.addPolygon(QPolygonF(pts))
            path.closeSubpath()
            if g == 'star-filled':
                painter.setBrush(color)
            painter.drawPath(path)
        elif g == 'private':
            # A shield rather than the confusing old diamond symbol.
            path = QPainterPath(QPointF(x, y-9))
            path.lineTo(x+7, y-6)
            path.lineTo(x+6, y+2)
            path.quadTo(x+4, y+7, x, y+9)
            path.quadTo(x-4, y+7, x-6, y+2)
            path.lineTo(x-7, y-6)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(QPointF(x-2, y), QPointF(x, y+2))
            painter.drawLine(QPointF(x, y+2), QPointF(x+4, y-3))
        elif g == 'menu':
            for yy in (-5, 0, 5):
                painter.drawLine(QPointF(x-7,y+yy),QPointF(x+7,y+yy))
        elif g == 'download':
            painter.drawLine(QPointF(x, y-8), QPointF(x, y+4))
            painter.drawLine(QPointF(x-5, y), QPointF(x, y+5))
            painter.drawLine(QPointF(x+5, y), QPointF(x, y+5))
            painter.drawLine(QPointF(x-8,y+8), QPointF(x+8,y+8))
        elif g == 'plus':
            painter.drawLine(QPointF(x-6,y),QPointF(x+6,y))
            painter.drawLine(QPointF(x,y-6),QPointF(x,y+6))
        elif g == 'min':
            # Narrow artwork, full original clickable region retained.
            painter.drawLine(QPointF(x-6, y+1), QPointF(x+6, y+1))
        elif g in ('max', 'restore'):
            if g == 'max':
                painter.drawRect(int(x-6), int(y-5), 12, 10)
            else:
                painter.drawRect(int(x-5), int(y-3), 10, 9)
                painter.drawLine(QPointF(x-3, y-6), QPointF(x+7, y-6))
                painter.drawLine(QPointF(x+7, y-6), QPointF(x+7, y+2))
        elif g in ('close', 'close-tab'):
            # Glyph moves up, hit target stays the same.
            offset = 1.5 if g == 'close' else 0
            r = 5.4 if g == 'close' else 4.5
            painter.drawLine(QPointF(x-r,y-r-offset),QPointF(x+r,y+r-offset))
            painter.drawLine(QPointF(x+r,y-r-offset),QPointF(x-r,y+r-offset))
        elif g == 'brand':
            painter.translate(0, -2)
            painter.setPen(QPen(color))
            font = self.font()
            font.setPointSize(19)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 'N')
        painter.end()


class NomikoTabBar(QTabBar):
    """Native tabs horizontally, horizontal-reading tabs in both sidebars."""
    pinRequested = Signal(int)
    groupRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.side = False
        self.side_compact = False
        self.accent = '#9A82FF'
        self.ink = '#EDEBF9'
        self.surface = '#151721'
        self.selected_surface = '#222433'
        self.hover_index = -1
        # Vertical tabs have their own drag lifecycle, independent of the
        # native QTabBar drag animation (which uses rotated tab geometry).
        self._press_index = -1
        self._press_point = None
        self._close_pressed = False
        self._dragging = False
        self._drag_index = -1
        self._drag_target = -1
        self._drag_offset = 0.0
        self._neighbor_offsets = {}
        self._settle_index = -1
        self._settle_offset = 0.0
        self._animation = QTimer(self)
        self._animation.setInterval(16)  # about 60 fps when dragging
        self._animation.timeout.connect(self._animate_drag)

    def _close_hit(self, index, point):
        if index < 0 or not self.side:
            return False
        rect = self.tabRect(index)
        if self.side_compact:
            return self.hover_index == index and QRect(rect.left()+2, rect.top()+2, 21, 20).contains(point)
        return QRect(rect.right()-28, rect.top(), 28, rect.height()).contains(point)

    def _clear_drag(self):
        self._press_index = -1
        self._press_point = None
        self._close_pressed = False
        self._dragging = False
        self._drag_index = -1
        self._drag_target = -1
        self._drag_offset = 0.0

    def mousePressEvent(self, event):  # noqa: N802
        if not self.side or event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        point = event.position().toPoint()
        index = self.tabAt(point)
        self._animation.stop()
        self._neighbor_offsets.clear()
        self._settle_index = -1
        self._settle_offset = 0.0
        self._clear_drag()
        if index >= 0:
            self._press_index = index
            self._press_point = point
            self._close_pressed = self._close_hit(index, point)
            # Keep the current page active while moving a background tab;
            # a normal click (without drag) will activate it on release.
        event.accept()

    def _animate_drag(self):
        running = False
        current_indices = range(self.count())
        for index in current_indices:
            desired = 0.0
            if self._dragging and index != self._drag_index:
                desired = neighbor_shift(index, self._drag_index, self._drag_target,
                                         self.tabRect(self._drag_index).height())
            previous = self._neighbor_offsets.get(index, 0.0)
            next_value = previous + (desired - previous) * 0.36
            if abs(next_value - desired) < 0.45:
                next_value = desired
            if abs(next_value) > 0.45:
                self._neighbor_offsets[index] = next_value
            else:
                self._neighbor_offsets.pop(index, None)
            if abs(next_value - desired) >= 0.45:
                running = True
        if self._settle_index >= 0:
            self._settle_offset *= 0.72
            if abs(self._settle_offset) < 0.5:
                self._settle_index = -1
                self._settle_offset = 0.0
            else:
                running = True
        self.update()
        if not running:
            self._animation.stop()

    def tabSizeHint(self, index):  # noqa: N802
        if self.side:
            # RoundedWest/East rotate Qt's logical tab size: return the
            # *unrotated* 41px height first, then the intended sidebar width.
            return QSize(41, max(40, self.width()-10))
        return super().tabSizeHint(index)

    def mouseMoveEvent(self, event):  # noqa: N802
        point = event.position().toPoint()
        self.hover_index = self.tabAt(point)
        if not self.side:
            self.update()
            return super().mouseMoveEvent(event)
        if self._press_index >= 0 and self._press_point is not None and not self._close_pressed:
            delta = point.y() - self._press_point.y()
            if not self._dragging and abs(delta) >= QApplication.startDragDistance() and self.count() > 1:
                self._dragging = True
                self._drag_index = self._press_index
                self._drag_target = self._drag_index
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            if self._dragging:
                src = self.tabRect(self._drag_index)
                # Don't draw a dragged tab outside the visible tab strip.
                self._drag_offset = float(max(-src.top(), min(self.height()-src.bottom(), delta)))
                centers = [self.tabRect(i).center().y() for i in range(self.count())]
                self._drag_target = drop_index(self._drag_index,
                                               src.center().y() + self._drag_offset, centers)
                if not self._animation.isActive():
                    self._animation.start()
        self.update()
        event.accept()

    def leaveEvent(self, event):  # noqa: N802
        if not self._dragging:
            self.hover_index = -1
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.MiddleButton:
            index = self.tabAt(event.position().toPoint())
            if index >= 0:
                self.tabCloseRequested.emit(index)
                event.accept()
                return
        if not self.side or event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        point = event.position().toPoint()
        was_dragging = self._dragging
        pressed_index = self._press_index
        source = self._drag_index
        target = self._drag_target
        before_center = (self.tabRect(source).center().y() + self._drag_offset
                         if was_dragging and source >= 0 else 0.0)
        close_clicked = (not was_dragging and self._close_pressed
                         and self.tabAt(point) == pressed_index
                         and self._close_hit(pressed_index, point))
        self._clear_drag()
        self.unsetCursor()
        if was_dragging and 0 <= source < self.count() and 0 <= target < self.count():
            # Neighbor previews belong to pre-drop indices; never carry them
            # across Qt's real tab order change.
            self._neighbor_offsets.clear()
            if source != target:
                # moveTab emits tabMoved; BrowserTabs updates its page stack in
                # exactly the same transaction, preserving selected page/data.
                self.moveTab(source, target)
                self._settle_index = target
                self._settle_offset = before_center - self.tabRect(target).center().y()
                self._animation.start()
            else:
                self._neighbor_offsets.clear()
        else:
            if close_clicked:
                self.tabCloseRequested.emit(self.tabAt(point))
            elif self.tabAt(point) == pressed_index and pressed_index >= 0:
                self.setCurrentIndex(pressed_index)
            self._neighbor_offsets.clear()
        self.update()
        event.accept()

    def contextMenuEvent(self, event):  # noqa: N802
        index = self.tabAt(event.pos())
        if index < 0:
            return super().contextMenuEvent(event)
        menu = QMenu(self)
        tab_data = self.tabData(index) or {}
        pin_action = menu.addAction('Unpin tab' if tab_data.get('pinned') else 'Pin tab')
        group_action = menu.addAction('Assign tab group…')
        close_action = menu.addAction('Close tab')
        picked = menu.exec(event.globalPos())
        if picked is pin_action: self.pinRequested.emit(index)
        if picked is group_action: self.groupRequested.emit(index)
        if picked is close_action: self.tabCloseRequested.emit(index)
        event.accept()

    def paintEvent(self, event):  # noqa: N802
        if not self.side:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        indices = [i for i in range(self.count()) if i != self._drag_index]
        if self._dragging and self._drag_index >= 0:
            indices.append(self._drag_index)  # Lift dragged tab above the others.
        for index in indices:
            painter.save()
            offset = self._neighbor_offsets.get(index, 0.0)
            if self._dragging and index == self._drag_index:
                offset = self._drag_offset
                painter.setOpacity(0.94)
            elif self._settle_index == index:
                offset = self._settle_offset
            painter.translate(0, offset)
            rect = self.tabRect(index).adjusted(3, 2, -3, -2)
            if self.currentIndex() == index:
                painter.setBrush(QColor(self.selected_surface))
                painter.setPen(QPen(QColor(self.accent), 1.8 if self._dragging and index == self._drag_index else 1))
            else:
                painter.setBrush(QColor(self.surface))
                painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(rect), 8, 8)
            data = self.tabData(index) or {}
            if data.get('group'):
                painter.setBrush(QColor(self.accent))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QRectF(rect.left()+3, rect.top()+4, 4, 4))
            if data.get('pinned'):
                painter.setPen(QPen(QColor(self.accent), 1.5))
                painter.drawLine(QPointF(rect.right()-7,rect.top()+5), QPointF(rect.right()-7,rect.top()+14))
            icon = self.tabIcon(index)
            if not icon.isNull():
                icon.paint(painter, QRect(rect.left()+9, rect.center().y()-9, 18, 18))
            if self.side_compact and self.hover_index == index and not self._dragging:
                # A close affordance sits at the upper-left of the favicon tab.
                r = self.tabRect(index)
                close_rect = QRectF(r.left()+2, r.top()+2, 17, 17)
                painter.setBrush(QColor(self.selected_surface))
                painter.setPen(QPen(QColor(self.accent),1))
                painter.drawRoundedRect(close_rect, 5, 5)
                painter.drawLine(close_rect.center()+QPointF(-3,-3),close_rect.center()+QPointF(3,3))
                painter.drawLine(close_rect.center()+QPointF(3,-3),close_rect.center()+QPointF(-3,3))
            if not self.side_compact:
                painter.setPen(QColor(self.ink))
                text_rect = rect.adjusted(34, 0, -26, 0)
                txt = painter.fontMetrics().elidedText(self.tabText(index), Qt.TextElideMode.ElideRight, text_rect.width())
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, txt)
                center = QPointF(rect.right()-14, rect.center().y())
                painter.drawLine(center+QPointF(-4,-4), center+QPointF(4,4))
                painter.drawLine(center+QPointF(4,-4), center+QPointF(-4,4))
            painter.restore()
        painter.end()


class TabResizeHandle(QWidget):
    """Drag between sidebar tabs and web content to resize the sidebar."""
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setFixedWidth(7)
        self.setCursor(Qt.CursorShape.SizeHorCursor)
        self.setToolTip('Drag to resize side tabs')
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):  # noqa: N802
        if event.buttons() & Qt.MouseButton.LeftButton:
            global_x = event.globalPosition().x()
            left_x = self.owner.mapToGlobal(QPoint(0, 0)).x()
            if self.owner._position == 'left':
                width = int(global_x - left_x)
            else:
                width = int(left_x + self.owner.width() - global_x)
            self.owner.set_side_width(width)
            event.accept()


class BrowserTabs(QWidget):
    """Repositionable tab strip; plus always follows last tab."""
    tabCloseRequested = Signal(int)
    currentChanged = Signal(int)
    tabMoved = Signal(int, int)
    side_width_changed = Signal(int)
    tabPinRequested = Signal(int)
    tabGroupRequested = Signal(int)

    def __init__(self, create_tab, parent=None):
        super().__init__(parent)
        self.outer = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(0)
        self.strip = QWidget(self)
        self.strip.setObjectName('tabStrip')
        self.line = QBoxLayout(QBoxLayout.Direction.LeftToRight, self.strip)
        self.line.setContentsMargins(7, 2, 7, 2)
        self.line.setSpacing(4)
        self.bar = NomikoTabBar(self.strip)
        self.bar.setDocumentMode(True)
        self.bar.setExpanding(False)
        self.bar.setMovable(True)
        self.bar.setUsesScrollButtons(True)
        self.bar.setTabsClosable(True)  # Native Qt closes, not tiny manual overlays.
        self.bar.tabCloseRequested.connect(self.tabCloseRequested.emit)
        self.bar.tabMoved.connect(self._tab_moved)
        self.bar.pinRequested.connect(lambda i: self.tabPinRequested.emit(i))
        self.bar.groupRequested.connect(lambda i: self.tabGroupRequested.emit(i))
        self.bar.currentChanged.connect(self._current_changed)
        self.line.addWidget(self.bar)
        self.plus = IconButton('plus', 'Open new tab (Ctrl+T)', create_tab, (30, 29), self.strip)
        self.plus.setObjectName('newTab')
        self.line.addWidget(self.plus)
        self.line.addStretch(1)
        self.stack = QStackedWidget(self)
        self.resizer = TabResizeHandle(self)
        self.outer.addWidget(self.strip)
        self.outer.addWidget(self.resizer)
        self.outer.addWidget(self.stack, 1)
        self.resizer.hide()
        self.sidebar_width = 196
        self._tab_width_timer = QTimer(self)
        self._tab_width_timer.setSingleShot(True)
        self._tab_width_timer.timeout.connect(self._update_tab_width)
        self._position = 'top'
        self._label_mode = 'icon-and-title'
        self._sidebar_style = 'expanded'
        self._titles = {}
        self._icons = {}

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._tab_width_timer.start(0)

    def _update_tab_width(self):
        if self._position in ('left', 'right'):
            # Keep the + directly after the last real tab. A vertical
            # QTabBar otherwise reserves Qt's sizeHint for several tabs.
            available = max(42, self.height() - 72)
            rows = max(1, self.bar.count())
            wanted = max(41, min(rows * 41 + 2, available))
            if self.bar.height() != wanted:
                self.bar.setFixedHeight(wanted)
            return
        self.bar.setMinimumHeight(0)
        widths = sum(max(54, self.bar.tabRect(i).width()) for i in range(self.bar.count()))
        target = max(1, min(widths + 8, max(1, self.width()-61)))
        if self.bar.width() != target:
            self.bar.setFixedWidth(target)

    def addTab(self, widget, title):
        self.stack.addWidget(widget)
        index = self.bar.addTab(title)
        self._titles[widget] = title
        self._tab_width_timer.start(0)
        self.setCurrentIndex(index)
        return index

    def removeTab(self, index):
        widget = self.stack.widget(index)
        if widget is None:
            return
        self._titles.pop(widget, None)
        self._icons.pop(widget, None)
        self.stack.removeWidget(widget)
        self.bar.removeTab(index)
        self._tab_width_timer.start(0)

    def _tab_moved(self, src, dst):
        widget = self.stack.widget(src)
        if widget:
            self.stack.removeWidget(widget)
            self.stack.insertWidget(dst, widget)
            self.stack.setCurrentIndex(self.bar.currentIndex())
        self.tabMoved.emit(src, dst)

    def _current_changed(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
        self.currentChanged.emit(index)

    def configure(self, position: str, label_mode: str, sidebar_style: str = 'expanded'):
        self._position = position
        self._label_mode = label_mode
        self._sidebar_style = sidebar_style
        side = position in ('left', 'right')
        # Qt's visual tab labels are overridden for sidebars to stay horizontal.
        self.bar.side = side
        self.bar.side_compact = sidebar_style == 'icon'
        self.bar.setTabsClosable(not side)
        self.bar.setStyleSheet('QTabBar { border: 0; } QTabBar::tab { border:0; background:transparent; padding:0; margin:0; min-width:0; max-width:400px; }' if side else '')
        # Sidebars use our vertical drag animation; keep Qt's native drag for
        # horizontal tabs only. The sidebar still calls moveTab on drop.
        self.bar.setMovable(not side)
        self.bar._clear_drag()
        self.bar._animation.stop()
        self.bar._neighbor_offsets.clear()
        self.bar._settle_index = -1
        self.bar.unsetCursor()
        self.bar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.bar.setShape(QTabBar.Shape.RoundedWest if side else (
            QTabBar.Shape.RoundedSouth if position == 'bottom' else QTabBar.Shape.RoundedNorth))
        self.bar.setMinimumWidth(0)
        self.bar.setMaximumWidth(16777215)
        self.line.setDirection(QBoxLayout.Direction.TopToBottom if side else QBoxLayout.Direction.LeftToRight)
        self.outer.setDirection({
            'top':QBoxLayout.Direction.TopToBottom, 'bottom':QBoxLayout.Direction.BottomToTop,
            'left':QBoxLayout.Direction.LeftToRight, 'right':QBoxLayout.Direction.RightToLeft
        }.get(position, QBoxLayout.Direction.TopToBottom))
        self.bar.setFixedWidth((self.sidebar_width-12) if side else 100)
        if not side:
            self.bar.setMinimumHeight(0)
            self.bar.setMaximumHeight(16777215)
        self.resizer.setVisible(side)
        if side:
            self.strip.setFixedWidth(self.sidebar_width)
        else:
            self.strip.setMinimumWidth(0)
            self.strip.setMaximumWidth(16777215)
        self.strip.setMaximumHeight(16777215 if side else 38)
        self.strip.setMinimumHeight(0)
        self.plus.setFixedSize(36 if side else 30, 32 if side else 29)
        for widget in list(self._titles):
            self._update_label(widget)
        self.bar.updateGeometry()
        self.bar.update()
        self._tab_width_timer.start(0)

    def set_side_width(self, width):
        self.sidebar_width = min(340, max(58, int(width)))
        if self._position in ('left', 'right'):
            self.strip.setFixedWidth(self.sidebar_width)
            self.bar.setFixedWidth(self.sidebar_width - 12)
            self.bar.updateGeometry()
        self.side_width_changed.emit(self.sidebar_width)

    def _update_label(self, widget):
        idx = self.indexOf(widget)
        if idx < 0: return
        title = self._titles.get(widget, 'New tab')
        if self._position in ('top','bottom'):
            text = '' if self._label_mode == 'icon' else title
            icon = QIcon() if self._label_mode == 'title' else self._icons.get(widget, QIcon())
        else:
            text = title
            icon = self._icons.get(widget, QIcon())
        self.bar.setTabText(idx, text)
        self.bar.setTabIcon(idx, icon)
        self.bar.setTabToolTip(idx, title)

    def setCurrentIndex(self, index):
        self.bar.setCurrentIndex(index)
        self.stack.setCurrentIndex(index)

    def currentIndex(self): return self.bar.currentIndex()
    def currentWidget(self): return self.stack.currentWidget()
    def widget(self, index): return self.stack.widget(index)
    def indexOf(self, view): return self.stack.indexOf(view)
    def count(self): return self.bar.count()
    def setTabText(self, index, text):
        view = self.widget(index)
        if view is not None:
            self._titles[view] = text
            self._update_label(view)
        self._tab_width_timer.start(0)
    def setTabIcon(self, index, icon):
        view = self.widget(index)
        if view is not None:
            self._icons[view] = icon
            self._update_label(view)
    def setTabToolTip(self, index, text): self.bar.setTabToolTip(index, text)


class BookmarksRail(QWidget):
    """Independent, movable bar for links in the 'toolbar' bookmarks folder."""
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setObjectName('bookmarkRail')
        self.line = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self.line.setContentsMargins(6, 3, 6, 3)
        self.line.setSpacing(4)
        self.sidebar_width = int(browser.store.settings.get('bookmark_sidebar_width', 154))
        self._side = False
        self._position = 'top'
        self._grip = QWidget(self)
        self._grip.setObjectName('bookmarkResizeGrip')
        self._grip.setCursor(Qt.CursorShape.SizeHorCursor)
        self._grip.setToolTip('Drag to resize bookmarks sidebar')
        self._grip.installEventFilter(self)
        self._grip.hide()
        self.refresh()

    def configure(self, position):
        side = position in ('left','right')
        self._side = side
        self._position = position
        self.line.setDirection(QBoxLayout.Direction.TopToBottom if side else QBoxLayout.Direction.LeftToRight)
        self.setMinimumWidth(0)
        self.setMaximumWidth(self.sidebar_width if side else 16777215)
        if side:
            self.setFixedWidth(self.sidebar_width)
        else:
            self.setMinimumWidth(0)
        self._grip.setVisible(side)
        self._position_grip()
        self.setMaximumHeight(16777215 if side else 39)
        self.setMinimumHeight(0)
        self.refresh()

    def refresh(self):
        while self.line.count():
            child = self.line.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        records = [x for x in self.browser.store.bookmarks if x.get('folder','toolbar') == 'toolbar']
        side = self.browser.store.settings.get('bookmark_position','top') in ('left','right')
        for row in records[:9 if side else 4]:
            title = str(row.get('title') or row.get('url') or '')
            url = str(row.get('url',''))
            if not url.startswith(('https://','http://')): continue
            btn = QToolButton(self)
            btn.setObjectName('bookmarkLink')
            btn.setText(('★ ' + title[:max(8, (self.sidebar_width-44)//8)]) if side else ('★ ' + title[:20]))
            btn.setToolTip(url)
            btn.setFixedHeight(29)
            btn.setMaximumWidth(max(70,self.sidebar_width-16) if side else 180)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, u=url: self.browser.open_url(u))
            self.line.addWidget(btn)
        more = QToolButton(self)
        more.setObjectName('bookmarkMore')
        more.setText('⋯')
        more.setToolTip('Manage bookmarks')
        more.setFixedSize(30,29)
        def show_more():
            menu = QMenu(more)
            for saved in records:
                url = str(saved.get('url',''))
                if url.startswith(('https://','http://')):
                    menu.addAction(str(saved.get('title') or url)[:48],
                                   lambda checked=False, u=url: self.browser.open_url(u))
            menu.addSeparator()
            menu.addAction('Manage bookmarks…', self.browser.show_bookmarks)
            menu.exec(more.mapToGlobal(more.rect().bottomLeft()))
        more.clicked.connect(show_more)
        self.line.addWidget(more)
        self.line.addStretch(1)
        self.setVisible(self.browser.store.settings.get('bookmark_bar_visible', True))
        self._position_grip()

    def _position_grip(self):
        if self._side:
            self._grip.setGeometry(self.width()-7 if self._position == 'left' else 0,
                                   0, 7, max(10, self.height()))
            self._grip.raise_()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._position_grip()

    def set_side_width(self, value):
        self.sidebar_width = max(72, min(360, int(value)))
        if self._side:
            self.setFixedWidth(self.sidebar_width)
            self.setMaximumWidth(self.sidebar_width)
            self.refresh()
        if hasattr(self.browser, '_bookmark_resize_timer'):
            self.browser._bookmark_resize_timer.start(500)

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self._grip and self._side:
            if event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
                pos = event.globalPosition().x()
                work = self.parentWidget()
                if work is not None:
                    left = work.mapToGlobal(QPoint(0, 0)).x()
                    new_width = pos - left if self._position == 'left' else left + work.width() - pos
                    self.set_side_width(new_width)
                return True
        return super().eventFilter(watched, event)


class NomikoPage(QWebEnginePage):
    """Intercept reserved .invalid form targets, never contact a search server."""
    def __init__(self, browser, view):
        super().__init__(browser.profile, view)
        self.browser, self.view = browser, view

    def acceptNavigationRequest(self, url, navigation_type, is_main_frame):  # noqa: N802
        if url.host() == 'nomiko.invalid':
            if (is_main_frame and url.scheme() == 'https' and url.path() == '/search'
                    and self.view.property('nomiko_page') in ('home', 'search')):
                args = parse_qs(url.query(QUrl.ComponentFormattingOption.FullyEncoded), keep_blank_values=True)
                query = args.get('q', [''])[0]
                engine = args.get('engine', [''])[0]
                pane = getattr(self.view, 'nomiko_split_pane', None)
                if pane is not None:
                    QTimer.singleShot(0, lambda q=query, e=engine, p=pane: p.search(q, e))
                else:
                    QTimer.singleShot(0, lambda q=query, e=engine: self.browser.search_query(q, self.view, e))
            if (is_main_frame and url.scheme() == 'https' and url.path() == '/widget'
                    and self.view.property('nomiko_page') == 'home'):
                args = parse_qs(url.query(QUrl.ComponentFormattingOption.FullyEncoded), keep_blank_values=True)
                values = {key: val[0] if val else '' for key, val in args.items()}
                QTimer.singleShot(0, lambda v=values: self.browser.on_widget_action(self.view, v))
            return False
        if is_main_frame and url.scheme() == 'http' and self.browser.store.settings.get('warn_insecure_websites', True):
            host = url.host().lower()
            if host not in ('localhost', '127.0.0.1') and host not in self.browser._allowed_http_hosts:
                choice = QMessageBox.question(
                    self.browser, 'Unencrypted website',
                    f'{host} uses HTTP, not HTTPS. Your traffic could be inspected or modified.\n\nContinue to this website?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if choice != QMessageBox.StandardButton.Yes:
                    return False
                self.browser._allowed_http_hosts.add(host)
        if (is_main_frame and self.browser.store.settings.get('warn_suspicious_domains', True)
                and url.scheme() in ('http', 'https') and 'xn--' in url.host().lower()):
            host = url.host().lower()
            if host not in self.browser._allowed_idn_hosts:
                choice = QMessageBox.question(
                    self.browser, 'Review website address',
                    f'This address contains a Punycode/IDN domain: {host}\nInternationalized domains can be legitimate, but can also resemble familiar websites.\n\nContinue?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if choice != QMessageBox.StandardButton.Yes: return False
                self.browser._allowed_idn_hosts.add(host)
        if (is_main_frame and self.browser.store.settings.get('clean_tracking_links', True)
                and url.scheme() in ('http', 'https')):
            cleaned = clean_tracking_url(url.toString())
            if cleaned != url.toString():
                QTimer.singleShot(0, lambda u=cleaned: self.view.load(QUrl(u)))
                return False
        return super().acceptNavigationRequest(url, navigation_type, is_main_frame)


class DragArea(QWidget):
    """Small unobstructed drag zone next to the native-style window controls."""
    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window().windowHandle()
            if handle and handle.startSystemMove():
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.window().toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class BrowserView(QWebEngineView):
    def __init__(self, browser: 'BrowserWindow'):
        super().__init__(browser)
        self.browser = browser
        self.setProperty('nomiko_page', '')
        self.setProperty('nomiko_search_query', '')
        self.setPage(NomikoPage(browser, self))
        self.page().permissionRequested.connect(browser.on_permission_requested)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            not browser.store.settings.get('block_popups', True))
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,
                                     browser.store.settings.get('autoplay_guard', True))

    def createWindow(self, window_type):  # noqa: N802
        return self.browser.new_tab()


class BrowserWindow(QMainWindow):
    def __init__(self, private: bool = False):
        super().__init__()
        self.private = private
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.store = Store()
        self.downloads = []
        self._pending_update = None
        self._update_center = None
        self._update_workers = []
        self._active_downloads = {}
        self._recently_closed = []
        self._weather_data = {}
        self._weather_manager = QNetworkAccessManager(self)
        self._weather_request_id = 0
        self._allowed_http_hosts = set()
        self._allowed_idn_hosts = set()
        self._restoring_session = True
        self._skip_final_session_save = False
        self._settings_panes = []
        self._idle_since = {}
        self._session_timer = QTimer(self)
        self._session_timer.setSingleShot(True)
        self._session_timer.setInterval(900)
        self._session_timer.timeout.connect(self._save_open_tabs)
        self.setWindowTitle('NOMIKO — Private' if private else 'NOMIKO')
        self.setMinimumSize(850, 560)
        self.resize(1320, 850)

        if private:
            self.profile = QWebEngineProfile(self)
        else:
            self.profile = QWebEngineProfile('NOMIKO-Default', self)
            storage_dir = APP_DIR / 'WebProfile'
            self.profile.setPersistentStoragePath(str(storage_dir / 'storage'))
            self.profile.setCachePath(str(storage_dir / 'cache'))
            self.profile.setHttpCacheMaximumSize(int(self.store.settings.get('cache_limit_mb', 128)) * 1024 * 1024)

        self.profile.setPersistentPermissionsPolicy(
            QWebEngineProfile.PersistentPermissionsPolicy.AskEveryTime
        )
        self.interceptor = TrackerInterceptor(
            enabled=self.store.settings.get('tracker_blocking', True),
            adblock=self.store.settings.get('ad_blocking', True), parent=self
        )
        self.interceptor.configure(self.store.settings.get('tracker_blocking', True),
                                   self.store.settings.get('ad_blocking', True),
                                   self.store.settings.get('block_exceptions', []),
                                   self.store.settings.get('privacy_referrer_policy', 'normal'))
        try:
            self.interceptor.set_custom_hosts(load_hosts(APP_DIR / 'custom-blocklist.txt'))
        except (OSError, ValueError) as exc:
            print('NOMIKO custom blocklist ignored:', exc)
        self.profile.setUrlRequestInterceptor(self.interceptor)
        self.profile.downloadRequested.connect(self.on_download)
        # User controls: limit local WebRTC address exposure and DNS prefetching.
        self._configure_privacy(self.store.settings)


        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(10000 if self.store.settings.get('performance_mode') == 'ultra' else 15000)
        self._idle_timer.timeout.connect(self._maintain_background_tabs)
        self._idle_timer.start()
        self._setup_ui()
        self._setup_shortcuts()
        self.apply_theme()
        if not private and self.store.settings.get('restore_tabs'):
            self._restore_open_tabs()
        if self.tabs.count() == 0:
            self.new_tab()
        self._restoring_session = False
        self._queue_session_save()
        self._translate_chrome()
        # Installed after initialization so eventFilter can safely inspect state.
        QApplication.instance().installEventFilter(self)
        if not self.private and self.store.settings.get("updates_auto_check", True):
            QTimer.singleShot(4000, self._check_updates_at_startup)

    def _configure_privacy(self, settings):
        self.profile.settings().setAttribute(
            QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly,
            bool(settings.get('privacy_webrtc_public_only', True)))
        self.profile.settings().setAttribute(
            QWebEngineSettings.WebAttribute.DnsPrefetchEnabled,
            bool(settings.get('privacy_dns_prefetch', False)))
        if not self.private:
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
                if settings.get('privacy_persistent_cookies', True)
                else QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

    def _setup_ui(self):
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget(self)
        toolbar.setObjectName('toolbar')
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(8, 2, 6, 2)
        bar.setSpacing(4)
        self._toolbar_layout = bar

        self.brand_btn = self._btn('brand', 'NOMIKO — New Tab', lambda: self.new_tab(), size=(36, 36))
        self.brand_btn.setObjectName('brand')
        self.back_btn = self._btn('back', 'Back (Alt+Left)', self.go_back, size=(38, 36))
        self.next_btn = self._btn('forward', 'Forward (Alt+Right)', self.go_forward, size=(38, 36))
        self.reload_btn = self._btn('reload', 'Reload (Ctrl+R)', self.reload_page, size=(38, 36))
        self.home_btn = self._btn('home', 'Home', self.go_home, size=(35, 36))
        for button in (self.brand_btn, self.back_btn, self.next_btn, self.reload_btn, self.home_btn):
            bar.addWidget(button)

        self.address = QLineEdit()
        self.address.setObjectName('address')
        self.address.setPlaceholderText('Search or enter a website...')
        self.address.setFixedHeight(34)
        self.address.returnPressed.connect(self.navigate)
        bar.addWidget(self.address, stretch=1)

        # The former stray ◈ security label after the address field is gone.
        self.bookmark_btn = self._btn('star', 'Save / remove bookmark (Ctrl+D)', self.toggle_bookmark, size=(34, 36))
        self.private_btn = self._btn('private', 'Open private window (Ctrl+Shift+N)', self.open_private, size=(34, 36))
        self.menu_btn = self._btn('menu', 'NOMIKO menu', self.show_main_menu, size=(34, 36))
        for button in (self.bookmark_btn, self.private_btn, self.menu_btn):
            bar.addWidget(button)

        drag = DragArea(toolbar)
        drag.setObjectName('dragArea')
        drag.setFixedSize(46, 34)
        drag.setToolTip('Drag window · Double-click to maximize')
        bar.addWidget(drag)

        self.minimize_btn = self._btn('min', 'Minimize', self.showMinimized, size=(40, 34))
        self.maximize_btn = self._btn('max', 'Maximize', self.toggle_maximize, size=(40, 34))
        self.close_btn = self._btn('close', 'Close NOMIKO', self.close, size=(40, 34))
        for button, name in (
            (self.minimize_btn, 'windowMin'),
            (self.maximize_btn, 'windowMax'),
            (self.close_btn, 'windowClose'),
        ):
            button.setObjectName(name)
            bar.addWidget(button)
        layout.addWidget(toolbar)

        self.download_btn = self._btn('download', 'Show downloads (Ctrl+J)', self.show_downloads_menu, size=(34, 36))
        self.download_btn.setObjectName('downloadMenu')
        # Place directly after the address field, before bookmark and private controls.
        bar.insertWidget(bar.indexOf(self.bookmark_btn), self.download_btn)
        self._toolbar_widgets = dict(zip(TOOLBAR_ITEMS,
            [self.brand_btn, self.back_btn, self.next_btn, self.reload_btn, self.home_btn,
             self.address, self.download_btn, self.bookmark_btn, self.private_btn, self.menu_btn]))

        self.tabs = BrowserTabs(lambda: self.new_tab())
        self.tabs.setObjectName('tabs')
        self.tabs.sidebar_width = self.store.settings.get('sidebar_width', 196)
        self.tabs.currentChanged.connect(self.on_current_tab_changed)
        self.tabs.tabMoved.connect(lambda src, dst: self._queue_session_save())
        self.tabs.configure(self.store.settings.get('tab_position','top'),
                            self.store.settings.get('tab_style','icon-and-title'),
                            self.store.settings.get('sidebar_style','expanded'))
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.tabPinRequested.connect(self.toggle_pin_tab)
        self.tabs.tabGroupRequested.connect(self.group_tab)
        self.tabs.side_width_changed.connect(self._on_sidebar_resized)
        self.bookmarks_rail = BookmarksRail(self)
        self._bookmark_resize_timer = QTimer(self)
        self._bookmark_resize_timer.setSingleShot(True)
        self._bookmark_resize_timer.timeout.connect(self._save_bookmark_sidebar_width)
        self.workspace = QWidget(self)
        self.workspace.setObjectName('workspace')
        self.workspace_layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self.workspace)
        self.workspace_layout.setContentsMargins(0,0,0,0)
        self.workspace_layout.setSpacing(0)
        self.workspace_layout.addWidget(self.bookmarks_rail)
        self.workspace_layout.addWidget(self.tabs, 1)
        layout.addWidget(self.workspace, stretch=1)
        self._apply_bookmark_position()
        self._apply_toolbar()

        footer = QWidget()
        footer.setObjectName('footer')
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 3, 12, 3)
        self.status = QLabel('Ready')
        self.status.setObjectName('status')
        footer_layout.addWidget(self.status)
        footer_layout.addStretch()
        self.mode_label = QLabel('')
        self.mode_label.setObjectName('mode')
        footer_layout.addWidget(self.mode_label)
        layout.addWidget(footer)
        self.setCentralWidget(container)

    def _btn(self, label, tooltip, callback, size=(35, 35)):
        return IconButton(label, tooltip, callback, size, self)

    def _action(self, title, shortcut, callback):
        action = QAction(title, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.triggered.connect(callback)
        self.addAction(action)
        return action

    def _setup_shortcuts(self):
        for title, hotkey, callback in (
            ('New tab', 'Ctrl+T', lambda: self.new_tab()),
            ('Close tab', 'Ctrl+W', lambda: self.close_tab(self.tabs.currentIndex())),
            ('Reopen closed tab', 'Ctrl+Shift+T', self.reopen_closed_tab),
            ('New private window', 'Ctrl+Shift+N', self.open_private),
            ('Focus address', 'Ctrl+L', self.focus_address),
            ('Bookmark', 'Ctrl+D', self.toggle_bookmark),
            ('History', 'Ctrl+H', self.show_history),
            ('Downloads', 'Ctrl+J', self.show_downloads),
            ('Reload', 'Ctrl+R', self.reload_page),
            ('Back', 'Alt+Left', self.go_back),
            ('Forward', 'Alt+Right', self.go_forward),
            ('Find on page', 'Ctrl+F', self.find_on_page),
            ('Settings', 'Ctrl+,', self.show_settings),
            ('Protection modules', 'Ctrl+Shift+M', self.show_modules),
            ('Mute tab', 'Ctrl+M', self.toggle_current_tab_audio),
            ('Gaming performance', 'Ctrl+Shift+G', self.toggle_gaming_mode),
            ('Search', 'Ctrl+K', self.focus_search),
            ('Find open tabs', 'Ctrl+Shift+A', self.find_open_tab),
            ('Reader mode', 'Ctrl+Shift+R', self.open_reader_mode),
            ('Split View', 'Ctrl+Shift+S', self.open_split_view),
            ('Workspaces', 'Ctrl+Alt+W', self.show_workspaces),
            ('Zoom in', 'Ctrl++', lambda: self.adjust_zoom(0.1)),
            ('Zoom out', 'Ctrl+-', lambda: self.adjust_zoom(-0.1)),
            ('Reset zoom', 'Ctrl+0', lambda: self.adjust_zoom(0)),
        ):
            self._action(title, hotkey, callback)

    def current_view(self):
        return self.tabs.currentWidget()

    def new_tab(self, url: str | None = None):
        view = BrowserView(self)
        self._idle_since[view] = time.monotonic()
        index = self.tabs.addTab(view, self.t('New tab'))
        view.iconChanged.connect(lambda icon, v=view: self.on_tab_icon(v, icon))
        self.tabs.setCurrentIndex(index)
        self.tabs.setTabIcon(index, self._nomiko_icon())
        view.titleChanged.connect(lambda title, v=view: self.on_tab_title(v, title))
        view.urlChanged.connect(lambda new_url, v=view: self.on_url_changed(v, new_url))
        view.loadFinished.connect(lambda ok, v=view: self.on_page_loaded(v, ok))
        view.loadStarted.connect(lambda v=view: self.on_load_started(v))
        if url:
            view.load(QUrl(url))
        else:
            self.load_home(view)
        self._queue_session_save()
        return view

    def load_home(self, view):
        homepage = str(self.store.settings.get('homepage', '')).strip()
        if homepage:
            url = resolve_input(homepage, self.store.settings.get('search_engine', 'DuckDuckGo'))
            if url:
                view.setProperty('nomiko_page', '')
                view.setProperty('nomiko_search_query', '')
                view.load(QUrl(url))
                return
        self._render_default_home(view)

    def close_tab(self, index):
        if index < 0:
            return
        if (self.tabs.bar.tabData(index) or {}).get('pinned'):
            self.status.setText('This tab is pinned. Right-click and unpin it before closing.')
            return
        if self.tabs.count() == 1:
            # A deliberately closed final tab must not reappear on the next start.
            self._skip_final_session_save = True
            if not self.private:
                self.store.clear_session()
            self.close()
            return
        view = self.tabs.widget(index)
        if view is None:
            return
        if isinstance(view, BrowserView):
            kind = view.property('nomiko_page')
            url = view.url().toString()
            entry = ('home', '') if kind == 'home' else (('web', url) if url.startswith(('http://', 'https://')) else None)
            if entry:
                self._recently_closed.append(entry)
                self._recently_closed = self._recently_closed[-15:]
        self.tabs.removeTab(index)
        self._idle_since.pop(view, None)
        view.deleteLater()
        self.status.setText(self.t('Ready'))
        self._queue_session_save()

    def reopen_closed_tab(self):
        if not self._recently_closed: return
        kind, url = self._recently_closed.pop()
        self.new_tab(url if kind == 'web' else None)

    def on_current_tab_changed(self, index):
        view = self.current_view()
        if isinstance(view, BrowserView):
            self._idle_since[view] = time.monotonic()
            try:
                view.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
            except RuntimeError:
                pass
        if view is not None:
            self.update_address(view)
            self.update_bookmark_button()
        self._queue_session_save()

    def _nomiko_icon(self, letter='N'):
        """Visible fallback icon for internal pages and favicon-only tabs."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bg = QColor(self.store.settings.get('accent', '#9A82FF'))
        if not bg.isValid():
            bg = QColor('#9A82FF')
        painter.setBrush(bg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRect(1, 1, 30, 30), 8, 8)
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(20)
        painter.setFont(font)
        painter.setPen(QColor('#10111A'))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, letter)
        painter.end()
        return QIcon(pixmap)

    def on_tab_icon(self, view, icon):
        idx = self.tabs.indexOf(view)
        if idx >= 0:
            fallback = self._nomiko_icon('N')
            self.tabs.setTabIcon(idx, fallback if view.property('nomiko_page') in ('home', 'search') or icon.isNull() else icon)

    def t(self, phrase):
        return tr(phrase, self.store.settings.get('language', 'en'))

    def on_tab_title(self, view, title):
        idx = self.tabs.indexOf(view)
        page_kind = view.property('nomiko_page')
        if idx >= 0:
            if page_kind == 'home':
                title = self.t('New tab')
            elif page_kind == 'search' and not title:
                title = 'NOMIKO Search'
            short = (title or 'New Tab')
            if len(short) > 25:
                short = short[:25] + '…'
            self.tabs.setTabText(idx, short)
            self.tabs.setTabToolTip(idx, title or 'New Tab')
        if view is self.current_view():
            self.setWindowTitle(f'{title or "NOMIKO"} — NOMIKO')

    def on_load_started(self, view):
        if view is self.current_view():
            self.status.setText('Loading...')

    def on_url_changed(self, view, url):
        if url.scheme() in ('https', 'http') and url.toString() not in ('about:blank', ''):
            if view.property('nomiko_page') not in ('home', 'search') or url.host() != '':
                view.setProperty('nomiko_page', '')
                view.setProperty('nomiko_search_query', '')
        if view is self.current_view():
            self.update_address(view)
            self.update_bookmark_button()
        self._queue_session_save()

    def on_page_loaded(self, view, ok):
        if view is self.current_view():
            self.status.setText('Ready' if ok else 'Page failed to load')
        url = view.url().toString()
        if ok and not self.private and url.startswith(('https://', 'http://')):
            self.store.add_history(url, view.title())
        self._queue_session_save()

    def update_address(self, view):
        if isinstance(view, SplitViewTab):
            pane = view.active_pane or view.left_pane
            self.address.setPlaceholderText('Split View · Use either search bar')
            self.address.setText(pane.selected_url())
            self.address.setToolTip('Active Split View pane; each side has an independent search bar')
            self.back_btn.setEnabled(pane.view.history().canGoBack())
            self.next_btn.setEnabled(pane.view.history().canGoForward())
            self.reload_btn.setEnabled(True)
            self.home_btn.setEnabled(True)
            return
        self.address.setPlaceholderText('Search or enter a website...')
        if not isinstance(view, BrowserView):
            kind = view.property('nomiko_page') or 'settings'
            self.address.setText('nomiko://' + str(kind))
            self.address.setToolTip(str(kind).title())
            self.back_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.reload_btn.setEnabled(False)
            self.home_btn.setEnabled(True)
            return
        self.reload_btn.setEnabled(True)
        url = view.url()
        page_type = view.property('nomiko_page')
        if page_type == 'home' and url.scheme() not in ('https', 'http'):
            self.address.setText('')
            self.address.setToolTip('NOMIKO new tab')
        elif page_type == 'search' and url.scheme() not in ('https', 'http'):
            self.address.setText('nomiko://search?q=' + str(view.property('nomiko_search_query') or ''))
            self.address.setToolTip('NOMIKO Search: your local bookmarks and history')
        else:
            self.address.setText(url.toString())
            self.address.setToolTip('HTTPS encrypts transport, but does not provide anonymity.'
                                    if url.scheme() == 'https' else 'Check website security before sharing data.')
        self.back_btn.setEnabled(view.history().canGoBack())
        self.next_btn.setEnabled(view.history().canGoForward())

    def focus_address(self):
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            field = view.active_pane.address
            field.setFocus()
            field.selectAll()
            return
        self.address.setFocus()
        self.address.selectAll()

    def focus_search(self):
        if self.address.isVisible():
            self.focus_address()
        else:
            text, ok = QInputDialog.getText(self, 'NOMIKO Search', 'Search or enter an address:')
            if ok and text.strip():
                if not isinstance(self.current_view(), BrowserView):
                    self.new_tab()
                self.search_query(text)

    def navigate(self):
        text = self.address.text().strip()
        view = self.current_view()
        if not text:
            return
        if isinstance(view, SplitViewTab):
            view.active_pane.search(text)
            return
        if not isinstance(view, BrowserView):
            view = self.new_tab()
        if text.startswith('nomiko://search?q='):
            self.search_query(text[len('nomiko://search?q='):], view, 'NOMIKO Search')
        else:
            self.search_query(text, view, self.store.settings.get('search_engine', 'DuckDuckGo'))

    def search_query(self, text: str, view=None, engine: str = ''):
        """Run chosen provider; NOMIKO mode only searches local page metadata."""
        query = str(text).strip()[:250]
        view = view or self.current_view()
        if not isinstance(view, BrowserView) or not query or self.tabs.indexOf(view) < 0:
            return
        if is_navigation_input(query):
            url = resolve_input(query)
            view.setProperty('nomiko_page', '')
            view.setProperty('nomiko_search_query', '')
            view.load(QUrl(url))
            return
        enabled = self.store.settings.get('visible_engines', ['DuckDuckGo','NOMIKO Search','Google'])
        if engine not in enabled:
            engine = self.store.settings.get('search_engine', enabled[0] if enabled else 'DuckDuckGo')
        if engine in SEARCH_ENGINES:
            url = resolve_input(query, engine)
            view.setProperty('nomiko_page', '')
            view.setProperty('nomiko_search_query', '')
            view.load(QUrl(url))
        else:
            view.setProperty('nomiko_page', 'search')
            view.setProperty('nomiko_search_query', query)
            self._render_search(view, query)

    def _render_search(self, view, query):
        if self.tabs.indexOf(view) >= 0:
            self.tabs.setTabIcon(self.tabs.indexOf(view), self._nomiko_icon())
        view.setHtml(render_search_results(
            query, self.store.settings.get('accent', '#9A82FF'),
            [] if self.private else self.store.bookmarks,
            [] if self.private else self.store.history,
            private=self.private, theme=self.store.settings.get('theme', 'dark'),
            visible_engines=self.store.settings.get('visible_engines'),
            language=self.store.settings.get('language', 'en'),
        ), QUrl.fromLocalFile(str(APP_DIR / 'nomiko-newtab.html')))
        if view is self.current_view():
            self.update_address(view)

    def open_url(self, url: str, new_tab: bool = False):
        if new_tab:
            self.new_tab(url)
        elif isinstance(self.current_view(), BrowserView):
            self.current_view().setProperty('nomiko_page', '')
            self.current_view().setProperty('nomiko_search_query', '')
            self.current_view().load(QUrl(url))
        else:
            self.new_tab(url)

    def go_back(self):
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            view.active_pane.go_back()
        elif isinstance(view, BrowserView):
            view.back()

    def go_forward(self):
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            view.active_pane.go_forward()
        elif isinstance(view, BrowserView):
            view.forward()

    def reload_page(self):
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            view.active_pane.reload()
            return
        if not isinstance(view, BrowserView):
            return
        if view.property('nomiko_page') == 'home':
            self.load_home(view)
        elif view.property('nomiko_page') == 'search':
            self._render_search(view, str(view.property('nomiko_search_query') or ''))
        else:
            view.reload()

    def go_home(self):
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            view.active_pane.show_home()
        elif isinstance(view, BrowserView):
            self.load_home(view)
        else:
            self.new_tab()


    def update_bookmark_button(self):
        view = self.current_view()
        url = (view.active_pane.view.url().toString() if isinstance(view, SplitViewTab)
               else view.url().toString() if isinstance(view, BrowserView) else '')
        is_saved = any(b.get('url') == url for b in self.store.bookmarks)
        self.bookmark_btn.glyph = 'star-filled' if is_saved else 'star'
        self.bookmark_btn.update()

    def toggle_bookmark(self):
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            view = view.active_pane.view
        if not isinstance(view, QWebEngineView):
            return
        url = view.url().toString()
        if not url.startswith(('http://', 'https://')):
            self.status.setText('Only websites can be bookmarked')
            return
        saved = self.store.toggle_bookmark(url, view.title())
        self.status.setText('Bookmark added' if saved else 'Bookmark removed')
        self.update_bookmark_button()
        self.refresh_bookmarks()
        self._refresh_internal_pages()  # Newly pinned link appears on existing start pages.

    def open_private(self):
        window = BrowserWindow(private=True)
        QApplication.instance().windows.append(window)
        window.show()

    def _list_dialog(self, title, rows):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(680, 480)
        layout = QVBoxLayout(dlg)
        lbl = QLabel('Double-click an item to open it in the browser.')
        layout.addWidget(lbl)
        listing = QListWidget()
        layout.addWidget(listing)
        for row in rows:
            url = row.get('url', '')
            item = QListWidgetItem(f"{row.get('title') or url}\n{url}")
            item.setData(Qt.ItemDataRole.UserRole, url)
            listing.addItem(item)

        def go(item):
            url = item.data(Qt.ItemDataRole.UserRole)
            if url and url.startswith(('http://', 'https://')):
                self.open_url(url, new_tab=True)
                dlg.accept()

        listing.itemDoubleClicked.connect(go)
        dlg.exec()

    def show_history(self):
        if self.private:
            QMessageBox.information(self, 'Private session', 'Private history is not recorded by NOMIKO.')
        else:
            HistoryDialog(self).exec()

    def show_bookmarks(self):
        BookmarksDialog(self).exec()

    def refresh_bookmarks(self):
        self.bookmarks_rail.refresh()

    def show_downloads_menu(self):
        menu = QMenu(self)
        menu.addAction(self.t('Downloads')).setEnabled(False)
        menu.addSeparator()
        for request in self.downloads[-9:][::-1]:
            filename = request.downloadFileName() or 'download'
            state = self.t('Ready') if request.isFinished() else '↓  In progress'
            action = menu.addAction(f'{filename[:37]}   ·   {state}')
            folder = request.downloadDirectory()
            full_path = Path(folder) / filename
            action.setEnabled(request.isFinished() and full_path.is_file())
            action.triggered.connect(lambda checked=False, f=full_path:
                                     QDesktopServices.openUrl(QUrl.fromLocalFile(str(f))))
        if not self.downloads:
            action = menu.addAction('No downloads this session')
            action.setEnabled(False)
        menu.addSeparator()
        menu.addAction(self.t('Show downloads'), self.show_downloads)
        menu.addAction(self.t('Choose folder'), self.show_settings)
        menu.exec(self.download_btn.mapToGlobal(self.download_btn.rect().bottomLeft()))

    def show_downloads(self):
        DownloadsDialog(self).exec()

    def on_download(self, request):
        downloads_folder = Path(self.store.settings.get('downloads_dir', str(Path.home() / 'Downloads'))).expanduser()
        if not downloads_folder.is_dir():
            downloads_folder = Path.home() / 'Downloads'

        downloads_folder.mkdir(parents=True, exist_ok=True)
        suggested = request.downloadFileName() or request.suggestedFileName() or 'download'
        if Path(suggested).suffix.lower() in ('.exe','.msi','.scr','.bat','.cmd','.vbs','.ps1','.jar','.reg','.lnk'):
            confirm = QMessageBox.question(self, 'Potentially dangerous download',
                f'This file can run code on your computer: {suggested}\n\nOnly download files you trust. Continue?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                request.cancel()
                return
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Save download', str(downloads_folder / suggested)
        )
        if not filename:
            request.cancel()
            return
        path = Path(filename)
        request.setDownloadDirectory(str(path.parent))
        request.setDownloadFileName(path.name)
        request.accept()
        self.downloads.append(request)
        history_id = None if self.private else self.store.record_download(
            str(path), request.url().toString())
        if history_id:
            self._active_downloads[history_id] = request
        self.status.setText(f'Downloading: {path.name}')
        def completed(d=request, identifier=history_id):
            if not d.isFinished(): return
            label = d.state().name
            if identifier is not None:
                self.store.finish_download(identifier, label)
                self._active_downloads.pop(identifier, None)
            self.status.setText(f'Download {label}: {d.downloadFileName()}')
        request.isFinishedChanged.connect(completed)

    def on_permission_requested(self, permission):
        origin = permission.origin().toString()
        category = permission.permissionType().name
        choice = QMessageBox.question(
            self, 'NOMIKO — Website permission',
            f'{origin}\n\nAllow access to: {category}?\n\nOnly allow websites you trust.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if choice == QMessageBox.StandardButton.Yes:
            permission.grant()
        else:
            permission.deny()

    def find_on_page(self):
        text, ok = QInputDialog.getText(self, 'Find on page', 'Text to find:')
        if not ok:
            return
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            view.active_pane.view.findText(text)
        elif isinstance(view, BrowserView):
            view.findText(text)

    def adjust_zoom(self, delta):
        view = self.current_view()
        if isinstance(view, SplitViewTab):
            view = view.active_pane.view
        if not isinstance(view, QWebEngineView):
            return
        if delta == 0:
            view.setZoomFactor(1)
        else:
            view.setZoomFactor(min(3, max(0.4, view.zoomFactor() + delta)))

    def show_main_menu(self):
        menu = QMenu(self)
        picker = QWidget(menu)
        picker.setObjectName('searchPicker')
        picker_row = QHBoxLayout(picker)
        picker_row.setContentsMargins(10, 8, 10, 8)
        picker_row.setSpacing(8)
        search_icon = QLabel('⌕', picker)
        search_icon.setObjectName('searchPickerIcon')
        picker_row.addWidget(search_icon)
        engine_picker = QComboBox(picker)
        engine_picker.setObjectName('searchPickerCombo')
        engine_picker.setToolTip('Default search engine for the address bar and new tab')
        enabled = self.store.settings.get('visible_engines', ['DuckDuckGo','NOMIKO Search','Google'])
        for engine in enabled: engine_picker.addItem(engine)
        engine_picker.setCurrentText(self.store.settings.get('search_engine', 'DuckDuckGo'))
        picker_row.addWidget(engine_picker, 1)
        engine_picker.currentTextChanged.connect(
            lambda engine: self.update_preference(search_engine=engine))
        picker_action = QWidgetAction(menu)
        picker_action.setDefaultWidget(picker)
        menu.addAction(picker_action)
        menu.addSeparator()
        handlers = {
            'new_tab': (self.t('New tab'), lambda: self.new_tab()),
            'private_window': (self.t('New private window'), self.open_private),
            'bookmarks': (self.t('Bookmarks'), self.show_bookmarks),
            'history': (self.t('History'), self.show_history),
            'downloads': (self.t('Downloads'), self.show_downloads),
            'settings': (self.t('Settings'), self.show_settings),
            'modules': ('Protection modules', self.show_modules),
            'clear_data': (self.t('Clear browsing data'), self.clear_browsing_data),
            'about': (self.t('About NOMIKO'), self.show_about),
        }
        hidden = self.store.settings.get('menu_hidden', [])
        colors = self.store.settings.get('menu_colors', {})
        for key in self.store.settings.get('menu_order', MENU_ITEMS):
            if key not in handlers or key in hidden: continue
            title, callback = handlers[key]
            action = QWidgetAction(menu)
            btn = QPushButton(title, menu)
            btn.setFixedSize(225, 32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setObjectName('nomikoMenuItem')
            tint = colors.get(key)
            if tint and QColor(tint).isValid():
                btn.setStyleSheet(f'QPushButton#nomikoMenuItem {{ color:{tint};text-align:left;padding-left:12px; }}')
            else:
                btn.setStyleSheet('QPushButton#nomikoMenuItem { text-align:left;padding-left:12px; }')
            def run(checked=False, cb=callback):
                menu.close()
                cb()
            btn.clicked.connect(run)
            action.setDefaultWidget(btn)
            menu.addAction(action)
        menu.addSeparator()
        tools = menu.addMenu('NOMIKO tools')
        for name, cb in [
            ('Find open tab…', self.find_open_tab),
            ('Workspaces…', self.show_workspaces),
            ('Split View…', self.open_split_view),
            ('Reading mode', self.open_reader_mode),
            ('Picture-in-Picture (experimental)', self.request_picture_in_picture),
            ('Transfer & backups…', self.show_transfer),
            ('Windows password vault…', self.show_password_vault),
            ('Privacy / site permissions…', self.show_permissions_center),
            ('Performance monitor', self.show_performance_monitor),
            ('Theme Studio', self.show_theme_studio),
            ('NOMIKO Updates…', self.show_update_center),
            ('Import local blocklist…', self.import_local_blocklist),
        ]:
            tools.addAction(name, cb)
        menu.exec(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))

    def toggle_pin_tab(self, index):
        if index < 0 or index >= self.tabs.count(): return
        bar = self.tabs.bar
        data = dict(bar.tabData(index) or {})
        data['pinned'] = not data.get('pinned', False)
        bar.setTabData(index, data)
        bar.setTabToolTip(index, ('Pinned · ' if data['pinned'] else '') + (self.tabs.bar.tabText(index) or 'Tab'))
        self.status.setText('Tab pinned — right-click to unpin' if data['pinned'] else 'Tab unpinned')
        bar.update()
        self._queue_session_save()

    def group_tab(self, index):
        if index < 0 or index >= self.tabs.count(): return
        choices = ['None', 'Work', 'Study', 'Games', 'Personal']
        group, ok = QInputDialog.getItem(self, 'Organize tab', 'Group:', choices, 0, False)
        if not ok: return
        data = dict(self.tabs.bar.tabData(index) or {})
        data['group'] = '' if group == 'None' else group
        self.tabs.bar.setTabData(index, data)
        self.tabs.bar.setTabTextColor(index, QColor('#79C3AD' if data['group'] else self.store.settings.get('accent','#9A82FF')))
        widget = self.tabs.widget(index)
        if widget:
            # Group metadata is carried with the widget after dragging.
            widget.setProperty('nomiko_group', data['group'])
        self.tabs.bar.update()
        self.status.setText('Group: ' + (data['group'] or 'None'))
        self._queue_session_save()

    def find_open_tab(self):
        options = []
        for idx in range(self.tabs.count()):
            widget = self.tabs.widget(idx)
            title = self.tabs.bar.tabText(idx) or str(widget.property('nomiko_page') or 'Tab')
            link = widget.url().toString() if isinstance(widget, BrowserView) else ''
            options.append((idx, title + ('  ·  ' + link[:65] if link else '')))
        if not options: return
        labels = [x[1] for x in options]
        item, ok = QInputDialog.getItem(self, 'Find a tab', 'Open tabs:', labels, self.tabs.currentIndex(), False)
        if ok and item in labels:
            self.tabs.setCurrentIndex(options[labels.index(item)][0])

    def show_workspaces(self):
        if self.private:
            QMessageBox.information(self, 'Private browsing', 'Workspaces are not saved in private sessions.')
        else:
            WorkspaceDialog(self).exec()

    def show_transfer(self):
        if self.private:
            QMessageBox.information(self, 'Private browsing', 'Use a normal window for imports, exports and backups.')
        else:
            import_export_dialog(self)

    def show_password_vault(self):
        if self.private:
            QMessageBox.information(self, 'Private browsing', 'The persistent password vault is available only in normal windows.')
        elif os.name != 'nt':
            QMessageBox.information(self, 'Windows only', 'This vault uses the Windows DPAPI and is available on Windows.')
        else:
            VaultDialog(self).exec()

    def _make_split_page(self, view):
        # Reuse the security, request-cleaning and internal-search interceptors
        # from ordinary NOMIKO tabs for BOTH split panes.
        page = NomikoPage(self, view)
        page.permissionRequested.connect(self.on_permission_requested)
        return page

    def open_split_view(self):
        current = self.current_view()
        if isinstance(current, SplitViewTab):
            current.right_pane.address.setFocus()
            current.right_pane.address.selectAll()
            return
        left_url = current.url().toString() if isinstance(current, BrowserView) else ''
        if not safe_web_url(left_url):
            left_url = ''
        # No dialog: the right-hand side starts on NOMIKO's home page with its
        # own immediately usable search/address field and search-engine picker.
        split = SplitViewTab(self, left_url, '')
        idx = self.tabs.addTab(split, 'Split View')
        self.tabs.setTabIcon(idx, self._nomiko_icon())
        self.tabs.setCurrentIndex(idx)
        split.right_pane.address.setFocus()
        self._queue_session_save()

    def open_reader_mode(self):
        source = self.current_view()
        if not isinstance(source, BrowserView) or not safe_web_url(source.url().toString()):
            QMessageBox.information(self, 'Reading mode', 'Open an article website first.')
            return
        original = source.url().toString()
        title = source.title()[:60]
        def complete(html):
            if not html: return
            text = render_reader(html, original, self.store.settings.get('accent', '#9A82FF'))
            target = self.new_tab()
            target.setProperty('nomiko_page','reader')
            target.setHtml(text, QUrl('about:blank'))
            self.tabs.setTabText(self.tabs.indexOf(target), 'Reader · ' + title[:25])
        source.page().toHtml(complete)

    def request_picture_in_picture(self):
        view = self.current_view()
        if not isinstance(view, BrowserView): return
        js = """(async()=>{const video=document.querySelector('video');
            if (!video || !document.pictureInPictureEnabled) return 'Unavailable on this site / Qt build';
            try { await video.requestPictureInPicture(); return 'Picture-in-picture requested'; }
            catch(e){ return 'Could not start: '+ e.name; } })()"""
        view.page().runJavaScript(js, lambda result: self.status.setText(str(result or 'Not supported')))

    def show_permissions_center(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('NOMIKO · Website permissions')
        dlg.resize(540, 350)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel('NOMIKO asks each time a site requests camera, microphone or other sensitive permissions.'))
        lay.addWidget(QLabel('Current profile policy: Ask Every Time. Grants are not stored across launches.'))
        lay.addWidget(QLabel('To revoke active permissions, close the relevant site tab or restart NOMIKO.'))
        link = self.current_view().url().toString() if isinstance(self.current_view(), BrowserView) else '(internal tab)'
        lay.addWidget(QLabel('Current page: ' + link[:180]))
        lay.addWidget(QLabel('IP addresses are visible to websites. NOMIKO has not passed an anonymity audit.'))
        lay.addStretch()
        dlg.exec()

    def import_local_blocklist(self):
        filename, _ = QFileDialog.getOpenFileName(self, 'Import local domain blocklist', '', 'Text lists (*.txt *.hosts)')
        if not filename: return
        try:
            from .module_packs import MAX_LIST_BYTES
            source = Path(filename)
            if source.stat().st_size > MAX_LIST_BYTES: raise ValueError('Maximum 2 MB text file')
            hosts = load_hosts(source)
            if not hosts: raise ValueError('No supported domain entries found')
            target = APP_DIR / 'custom-blocklist.txt'
            APP_DIR.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copyfile(source, target)
            for win in list(getattr(QApplication.instance(), 'windows', [])):
                if isinstance(win, BrowserWindow): win.interceptor.set_custom_hosts(hosts)
            QMessageBox.information(self, 'Module list imported', f'Loaded {len(hosts)} domains. This list is local and never auto-updated.')
        except (OSError,ValueError) as exc:
            QMessageBox.warning(self, 'Import failed', str(exc))

    def remove_local_blocklist(self):
        target = APP_DIR / 'custom-blocklist.txt'
        try: target.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, 'Cannot remove list', str(exc))
            return
        for win in list(getattr(QApplication.instance(), 'windows', [])):
            if isinstance(win, BrowserWindow): win.interceptor.set_custom_hosts(frozenset())
        self.status.setText('Custom domain list removed')

    def show_theme_studio(self):
        ThemeStudioDialog(self).exec()

    def show_performance_monitor(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('NOMIKO · Performance')
        dlg.resize(465, 290)
        lay = QVBoxLayout(dlg)
        status = QLabel()
        status.setWordWrap(True)
        lay.addWidget(status)
        lay.addWidget(QLabel('Background tabs may be frozen/discarded by Qt.\nMemory of separate Chromium subprocesses is not included in the value below.'))
        def refresh():
            memory = 'Unavailable'
            if os.name == 'nt':
                try:
                    import ctypes
                    from ctypes import wintypes
                    class Pm(ctypes.Structure):
                        _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                          ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                          ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                          ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                          ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
                    proc = Pm(); proc.cb = ctypes.sizeof(proc)
                    ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(proc), proc.cb)
                    memory = f'{proc.WorkingSetSize // (1024*1024)} MB (UI process only)'
                except (OSError, AttributeError): pass
            status.setText(f'Browser tabs: {self.tabs.count()}\nMode: {self.store.settings.get("performance_mode", "balanced")}\nNOMIKO UI memory: {memory}')
        refresh()
        timer = QTimer(dlg)
        timer.setInterval(2000)
        timer.timeout.connect(refresh)
        timer.start()
        lay.addStretch(1)
        dlg.exec()

    def toggle_current_tab_audio(self):
        view = self.current_view()
        if isinstance(view, BrowserView):
            page = view.page()
            page.setAudioMuted(not page.isAudioMuted())
            self.status.setText('Tab muted' if page.isAudioMuted() else 'Tab audio restored')

    def toggle_gaming_mode(self):
        enabled = self.store.settings.get('performance_mode') == 'gaming'
        self.update_preference(performance_mode='balanced' if enabled else 'gaming')
        self.status.setText('Gaming mode OFF' if enabled else 'Gaming mode ON · background tabs may reload')

    def show_modules(self):
        self.show_settings()
        view = self.current_view()
        for pane in view.findChildren(SettingsPane):
            idx = pane.CATEGORIES.index('Modules')
            pane.category_list.setCurrentRow(idx)
            break

    def _maintain_background_tabs(self):
        mode = self.store.settings.get('performance_mode', 'balanced')
        if not self.private:
            c = self.interceptor.counts()
            text = f'PROTECTION  ·  ADS {c["ads"]}  /  TRACKERS {c["trackers"]}'
            if self.mode_label.text() != text:
                self.mode_label.setText(text)
        if mode == 'off':
            return
        freeze_after, discard_after = ({'ultra': (10, 35), 'gaming': (25, 90),
                                       'balanced': (120, 480)}.get(mode, (120, 480)))
        now = time.monotonic()
        # Only act on hidden, loaded, ordinary web pages and only as Qt recommends.
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)
            if not isinstance(view, BrowserView):
                continue
            page = view.page()
            if view is self.current_view() and not self.isMinimized():
                self._idle_since[view] = now
                continue
            idle = now - self._idle_since.setdefault(view, now)
            if (view.isVisible() and not self.isMinimized()) or page.isLoading() or view.property('nomiko_page'):
                continue
            suggested = page.recommendedState()
            if idle >= discard_after and suggested == QWebEnginePage.LifecycleState.Discarded:
                page.setLifecycleState(QWebEnginePage.LifecycleState.Discarded)
            elif idle >= freeze_after and suggested in (QWebEnginePage.LifecycleState.Frozen,
                                                         QWebEnginePage.LifecycleState.Discarded):
                if page.lifecycleState() == QWebEnginePage.LifecycleState.Active:
                    page.setLifecycleState(QWebEnginePage.LifecycleState.Frozen)

    def on_widget_action(self, view, values):
        """Handle local home widget forms without contacting nomiko.invalid."""
        if self.tabs.indexOf(view) < 0 or view.property('nomiko_page') != 'home':
            return
        action = str(values.get('action', ''))
        if action not in ('note', 'task-add', 'task-remove', 'weather'):
            return
        # A private window must never persist widget notes/city/tasks to disk.
        if self.store.apply_widget_action(action, values, persist=not self.private):
            if action == 'weather':
                self._request_weather(str(values.get('city', '')).strip()[:80])
            else:
                self._render_default_home(view)

    def _request_weather(self, city):
        """Opt-in requests to Open-Meteo; no NOMIKO server or location tracking."""
        if not city:
            return
        self._weather_request_id += 1
        request_id = self._weather_request_id
        self._weather_data = {'error': 'Loading weather…'}
        self._refresh_home_only()
        url = QUrl('https://geocoding-api.open-meteo.com/v1/search?name=' + quote_plus(city)
                   + '&count=1&language=en&format=json')
        request = QNetworkRequest(url)
        request.setTransferTimeout(8000)
        reply = self._weather_manager.get(request)
        def got_city():
            try:
                if request_id != self._weather_request_id: return
                if reply.error() != QNetworkReply.NetworkError.NoError:
                    raise ValueError('Weather service unavailable.')
                results = json.loads(bytes(reply.readAll()).decode('utf-8')).get('results') or []
                if not results: raise ValueError('City not found. Try another city name.')
                location = results[0]
                latitude, longitude = float(location['latitude']), float(location['longitude'])
                name = str(location['name'])[:80]
                forecast = QUrl('https://api.open-meteo.com/v1/forecast?latitude=' + str(latitude)
                                + '&longitude=' + str(longitude)
                                + '&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto')
                request2 = QNetworkRequest(forecast)
                request2.setTransferTimeout(8000)
                reply2 = self._weather_manager.get(request2)
                def got_forecast():
                    try:
                        if request_id != self._weather_request_id: return
                        if reply2.error() != QNetworkReply.NetworkError.NoError:
                            raise ValueError('Forecast currently unavailable.')
                        cur = json.loads(bytes(reply2.readAll()).decode('utf-8')).get('current') or {}
                        code = int(cur.get('weather_code', -1))
                        summary = ('Clear' if code == 0 else 'Cloudy' if code <= 3 else
                                   'Fog' if code <= 48 else 'Rain' if code <= 67 else
                                   'Snow' if code <= 77 else 'Showers' if code <= 86 else
                                   'Thunderstorm' if code >= 95 else 'Mixed')
                        self._weather_data = {
                            'temp': round(float(cur['temperature_2m'])),
                            'wind': round(float(cur['wind_speed_10m'])),
                            'city': name, 'summary': summary,
                        }
                    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                        self._weather_data = {'error': str(exc)[:140]}
                    finally:
                        reply2.deleteLater()
                        if request_id == self._weather_request_id: self._refresh_home_only()
                reply2.finished.connect(got_forecast)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                self._weather_data = {'error': str(exc)[:140]}
                self._refresh_home_only()
            finally:
                reply.deleteLater()
        reply.finished.connect(got_city)

    def _refresh_home_only(self):
        for i in range(self.tabs.count()):
            view = self.tabs.widget(i)
            if view.property('nomiko_page') == 'home' and isinstance(view, BrowserView):
                self._render_default_home(view)

    def show_settings(self):
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if widget.property('nomiko_page') == 'settings':
                self.tabs.setCurrentIndex(i)
                return
        page = QWidget(self)
        page.setProperty('nomiko_page', 'settings')
        index = self.tabs.addTab(page, self.t('Settings'))
        self.tabs.setTabIcon(index, self._nomiko_icon('⚙'))
        self._build_settings_page(page)
        self.tabs.setCurrentIndex(self.tabs.indexOf(page))

    def _queue_session_save(self):
        if (not self.private and not self._restoring_session
                and self.store.settings.get('restore_tabs')):
            self._session_timer.start()

    def _save_open_tabs(self):
        if self.private or self._restoring_session or not self.store.settings.get('restore_tabs'):
            return
        tabs = []
        original_index = self.tabs.currentIndex()
        restored_active = 0
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            kind = widget.property('nomiko_page')
            record = None
            if kind == 'settings':
                record = {'kind': 'settings'}
            elif kind == 'home':
                record = {'kind': 'home'}
            elif kind == 'search':
                record = {'kind': 'search', 'query': widget.property('nomiko_search_query') or ''}
            elif isinstance(widget, BrowserView):
                address = widget.url().toString()
                if address.startswith(('http://', 'https://')):
                    record = {'kind': 'web', 'url': address}
            if record:
                tabs.append(record)
                if isinstance(widget, BrowserView) and record.get('kind') == 'web':
                    data = self.tabs.bar.tabData(i) or {}
                    if data.get('pinned'): record['pinned'] = True
                    if data.get('group'): record['group'] = data['group']
                if i <= original_index:
                    restored_active = len(tabs) - 1
        self.store.save_session(tabs, restored_active)

    def _restore_open_tabs(self):
        saved = self.store.read_session()
        for tab in saved['tabs']:
            kind = tab['kind']
            if kind == 'web':
                view = self.new_tab(tab['url'])
                idx = self.tabs.indexOf(view)
                data = {}
                if tab.get('pinned'): data['pinned'] = True
                if tab.get('group'): data['group'] = tab['group']
                if data: self.tabs.bar.setTabData(idx, data)
            elif kind == 'home':
                self.new_tab()
            elif kind == 'search':
                view = self.new_tab()
                view.setProperty('nomiko_page', 'search')
                view.setProperty('nomiko_search_query', tab['query'])
                self._render_search(view, tab['query'])
            elif kind == 'settings':
                self.show_settings()
        if self.tabs.count():
            self.tabs.setCurrentIndex(min(saved['active'], self.tabs.count()-1))

    def _build_settings_page(self, page):
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        pane = SettingsPane(self, page)
        root.addWidget(pane)
        self._settings_panes.append(pane)

    def update_preference(self, **changes):
        """One-step persistence, no settings-tab rebuild or navigation."""
        if not changes: return
        self.store.settings.update(changes)
        self.store.save_settings()
        if changes.get('restore_tabs') is False:
            self._session_timer.stop()
            self.store.clear_session()
        for win in list(getattr(QApplication.instance(), 'windows', [])):
            if not isinstance(win, BrowserWindow): continue
            if win is not self:
                win.store.settings.update(changes)
            if 'cache_limit_mb' in changes and not win.private:
                win.profile.setHttpCacheMaximumSize(int(win.store.settings['cache_limit_mb']) * 1024 * 1024)
            if 'performance_mode' in changes:
                win._idle_timer.setInterval(10000 if win.store.settings['performance_mode'] == 'ultra' else 15000)
            changed = set(changes)
            if changed & {'tracker_blocking', 'ad_blocking', 'block_exceptions', 'privacy_referrer_policy'}:
                win.interceptor.configure(
                    win.store.settings.get('tracker_blocking', True),
                    win.store.settings.get('ad_blocking', True),
                    win.store.settings.get('block_exceptions', []),
                    win.store.settings.get('privacy_referrer_policy', 'normal'))
            if changed & {'privacy_webrtc_public_only', 'privacy_dns_prefetch', 'privacy_persistent_cookies'}:
                win._configure_privacy(win.store.settings)
            if changed & {'block_popups', 'autoplay_guard'}:
                for i in range(win.tabs.count()):
                    view = win.tabs.widget(i)
                    if isinstance(view, BrowserView):
                        view.settings().setAttribute(
                            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
                            not win.store.settings.get('block_popups', True))
                        view.settings().setAttribute(
                            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,
                            win.store.settings.get('autoplay_guard', True))
            if changes.get('performance_mode') == 'off':
                for i in range(win.tabs.count()):
                    view = win.tabs.widget(i)
                    if isinstance(view, BrowserView):
                        view.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
            if changed & {'tab_position', 'tab_style', 'sidebar_style'}:
                win.tabs.configure(win.store.settings.get('tab_position','top'),
                                   win.store.settings.get('tab_style','icon-and-title'),
                                   win.store.settings.get('sidebar_style','expanded'))
            if changed & {'toolbar_order', 'toolbar_hidden'}:
                win._apply_toolbar()
            if changed & {'bookmark_bar_visible', 'bookmark_position'}:
                win._apply_bookmark_position()
            if changed & {'theme', 'accent', 'toolbar_colors', 'tab_position', 'tab_style',
                          'sidebar_style', 'bookmark_bar_visible', 'bookmark_position',
                          'interface_transparency', 'theme_font_size'}:
                win.apply_theme()
            if 'language' in changed:
                win._translate_chrome()
            # Home reload is intentionally limited to changes that actually affect it.
            # Timer/audio widgets are left untouched by unrelated preference changes.
            if changed & {'theme', 'accent', 'language', 'home_order', 'home_hidden',
                          'home_colors', 'widget_order', 'widget_enabled', 'widget_density',
                          'widget_columns', 'search_engine', 'visible_engines', 'homepage'}:
                win._refresh_internal_pages()
        self.status.setText('Settings saved automatically')

    def _save_bookmark_sidebar_width(self):
        value = self.bookmarks_rail.sidebar_width
        self.store.settings['bookmark_sidebar_width'] = value
        self.store.save_settings()

    def _on_sidebar_resized(self, width):
        # Writing this cheap preference only after resize has settled avoids I/O on each pixel.
        if not hasattr(self, '_resize_timer'):
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._persist_sidebar_width)
        self._resize_timer.start(450)

    def _persist_sidebar_width(self):
        self.store.settings['sidebar_width'] = self.tabs.sidebar_width
        self.store.save_settings()

    def _apply_toolbar(self):
        if not hasattr(self, '_toolbar_widgets'): return
        layout = self._toolbar_layout
        order = self.store.settings.get('toolbar_order', TOOLBAR_ITEMS)
        hidden = self.store.settings.get('toolbar_hidden', [])
        for key in TOOLBAR_ITEMS:
            widget = self._toolbar_widgets[key]
            layout.removeWidget(widget)
        for index, key in enumerate(order):
            if key not in self._toolbar_widgets: continue
            widget = self._toolbar_widgets[key]
            layout.insertWidget(index, widget, 1 if key == 'address' else 0)
            widget.setVisible(key not in hidden)

    def _apply_bookmark_position(self):
        if not hasattr(self, 'bookmarks_rail'): return
        place = self.store.settings.get('bookmark_position', 'top')
        layout = self.workspace_layout
        layout.removeWidget(self.bookmarks_rail)
        layout.removeWidget(self.tabs)
        layout.setDirection({
            'top': QBoxLayout.Direction.TopToBottom,
            'bottom': QBoxLayout.Direction.BottomToTop,
            'left': QBoxLayout.Direction.LeftToRight,
            'right': QBoxLayout.Direction.RightToLeft,
        }.get(place, QBoxLayout.Direction.TopToBottom))
        layout.addWidget(self.bookmarks_rail)
        layout.addWidget(self.tabs, 1)
        self.bookmarks_rail.configure(place)
        self.bookmarks_rail.setVisible(self.store.settings.get('bookmark_bar_visible',True))

    def open_donation(self):
        QDesktopServices.openUrl(QUrl('https://send.monobank.ua/jar/91HH8iY31q'))

    def _translate_chrome(self):
        controls = [
            (self.brand_btn,'New tab'),(self.back_btn,'Back'),
            (self.next_btn,'Forward'),(self.reload_btn,'Reload'),
            (self.home_btn,'Home'),(self.bookmark_btn,'Bookmark'),
            (self.download_btn,'Downloads'),(self.private_btn,'Private window'),
            (self.menu_btn,'Menu'),(self.minimize_btn,'Minimize'),
            (self.maximize_btn,'Maximize'),(self.close_btn,'Close'),
            (self.tabs.plus,'New tab'),
        ]
        for btn,key in controls:
            btn.setToolTip(self.t(key))
        self.address.setPlaceholderText(self.t('Search or enter a website'))
        self.tabs.setTabToolTip(self.tabs.currentIndex(),self.t('New tab')) if self.tabs.count()==1 and self.current_view().property('nomiko_page')=='home' else None

    def _refresh_internal_pages(self):
        """Restyle currently open home/search tabs after Save, not just new tabs."""
        for index in range(self.tabs.count()):
            view = self.tabs.widget(index)
            page_kind = view.property('nomiko_page')
            if page_kind == 'home':
                # Refresh *our* new tab, not an external custom homepage.
                self._render_default_home(view)
            elif page_kind == 'search':
                self._render_search(view, str(view.property('nomiko_search_query') or ''))
        self.update_bookmark_button()

    def _render_default_home(self, view):
        view.setProperty('nomiko_page', 'home')
        view.setProperty('nomiko_search_query', '')
        if self.tabs.indexOf(view) >= 0:
            self.tabs.setTabIcon(self.tabs.indexOf(view), self._nomiko_icon())
        view.setHtml(render_home(
            self.store.settings.get('accent', '#9A82FF'),
            self.store.bookmarks, private=self.private,
            theme=self.store.settings.get('theme', 'dark'),
            engine=self.store.settings.get('search_engine', 'DuckDuckGo'),
            visible_engines=self.store.settings.get('visible_engines'),
            language=self.store.settings.get('language', 'en'),
            wallpaper=(self.store.wallpaper().name if self.store.wallpaper() else ''),
            home_order=self.store.settings.get('home_order'),
            home_hidden=self.store.settings.get('home_hidden'),
            home_colors=self.store.settings.get('home_colors'),
            widget_order=self.store.settings.get('widget_order'),
            widget_enabled=self.store.settings.get('widget_enabled'),
            widget_data=({} if self.private else self.store.widget_data),
            widget_density=self.store.settings.get('widget_density', 'comfortable'),
            widget_columns=self.store.settings.get('widget_columns', 'auto'),
            weather=self._weather_data,
        ), QUrl.fromLocalFile(str(APP_DIR / 'nomiko-newtab.html')))
        if view is self.current_view():
            self.update_address(view)

    def clear_browsing_data(self):
        if QMessageBox.question(
            self, 'Clear browsing data',
            'Delete NOMIKO app history, cookies and network cache for this profile?\n'
            'Bookmarks, downloads and some other website storage remain.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        if not self.private:
            self.store.clear_history()
        self.profile.cookieStore().deleteAllCookies()
        self.profile.clearHttpCache()
        self.profile.clearAllVisitedLinks()
        self.status.setText('History, cookies and cache cleared (some site storage remains).')

    def show_about(self):
        from PySide6.QtCore import qVersion
        dialog = QDialog(self)
        dialog.setWindowTitle('About NOMIKO')
        dialog.resize(670, 520)
        root = QVBoxLayout(dialog)
        heading = QLabel(f'NOMIKO   /   v{CURRENT_VERSION} Alpha')
        heading.setObjectName('sectionHeading')
        root.addWidget(heading)
        copy = (
            'Independent browser for Windows 11. NOMIKO is a personal project, not an AURVEX product.\n\n'
            'OUR PRINCIPLES\n'
            '• User-controlled interface: rearrange buttons, tabs, bookmark rails, accents and wallpaper.\n'
            '• Local-first: settings, history, bookmarks and wallpapers stay on your device by default.\n'
            '• No mandatory account. The Account screen is a local-only placeholder.\n'
            '• Search: DuckDuckGo / Google, or NOMIKO local bookmarks/history search.\n'
            '• Home widgets: clocks, timers, notes, tasks, calendar, opt-in weather and audio beta.\n'
            '• Widget order, visibility and density are customizable on-device.\n\n'
            'TECHNICAL FOUNDATION\n'
            f'• Application: Python + PySide6 / Qt {qVersion()}.\n'
            '• Web rendering: Qt WebEngine, based on Chromium.\n'
            '• Website code and content are not NOMIKO’s own engine.\n'
            f'• Local profile path: {APP_DIR}\n\n'
            'PRIVACY LIMITATIONS\n'
            '• This is experimental software. No independently audited anonymity protection.\n'
            '• Sites can see your IP address; browser fingerprinting and network leaks are not fully mitigated.\n'
            '• Weather sends the entered city to Open-Meteo ONLY on request.\n'
            '• Audio recording requires explicit microphone permission and may not work in every Qt WebEngine build.\n'
            '• Downloads, stored cookies and site data may remain after clearing visit history.\n'
            '• Updates: GitHub Releases with Ed25519 signature and SHA-256 verification.\n'
            '• Update checks reveal your IP address to GitHub; you can disable automatic checks.\n'
            '• Unverified downloads never execute. This alpha is not suitable for high-risk private browsing.'
        )
        area = QScrollArea(dialog)
        area.setWidgetResizable(True)
        text_widget = QLabel(copy)
        text_widget.setWordWrap(True)
        text_widget.setContentsMargins(16,16,16,16)
        area.setWidget(text_widget)
        root.addWidget(area,1)
        close = QPushButton('Close')
        close.clicked.connect(dialog.accept)
        root.addWidget(close)
        dialog.exec()

    def show_update_center(self):
        if self.private:
            QMessageBox.information(self, 'NOMIKO · Updates', 'Open an ordinary window to manage browser updates.')
            return
        if self._update_center is None:
            self._update_center = UpdateCenter(self)
        self._update_center.show()
        self._update_center.raise_()
        self._update_center.activateWindow()

    def _check_updates_at_startup(self):
        # Asynchronous and non-blocking; never initiate an installation silently.
        if not self.isVisible() or self.private:
            return
        worker = UpdateWorker('check', channel=self.store.settings.get('updates_channel', 'alpha'), parent=self)
        self._update_workers.append(worker)
        worker.result.connect(self._on_startup_update_result)
        worker.finished.connect(lambda w=worker: self._on_update_worker_finished(w))
        worker.start()

    def _on_update_worker_finished(self, worker):
        if worker in self._update_workers:
            self._update_workers.remove(worker)
        worker.deleteLater()

    def _on_startup_update_result(self, release):
        if release is None or not self.isVisible():
            return
        answer = QMessageBox.question(self, 'NOMIKO · Update available',
            f'NOMIKO {release.version} is available.\n\nOpen Update Center to download and verify it?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.show_update_center()

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_max_button()

    def _sync_max_button(self):
        if hasattr(self, 'maximize_btn'):
            self.maximize_btn.glyph = 'restore' if self.isMaximized() else 'max'
            self.maximize_btn.update()
            self.maximize_btn.setToolTip('Restore' if self.isMaximized() else 'Maximize')

    def changeEvent(self, event):  # noqa: N802
        if event.type() == QEvent.Type.WindowStateChange:
            self._sync_max_button()
            if not self.isMinimized() and hasattr(self, 'tabs'):
                current = self.current_view()
                if isinstance(current, BrowserView):
                    current.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
                    self._idle_since[current] = time.monotonic()
        super().changeEvent(event)

    def eventFilter(self, obj, event):  # noqa: N802
        # A 6px resize border replaces the native border lost to FramelessWindowHint.
        if (event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseMove)
                and isinstance(obj, QWidget) and obj.window() is self and not self.isMaximized()):
            point = self.mapFromGlobal(event.globalPosition().toPoint())
            margin = 6
            edges = Qt.Edge(0)
            if point.x() < margin:
                edges |= Qt.Edge.LeftEdge
            elif point.x() >= self.width() - margin:
                edges |= Qt.Edge.RightEdge
            if point.y() < margin:
                edges |= Qt.Edge.TopEdge
            elif point.y() >= self.height() - margin:
                edges |= Qt.Edge.BottomEdge
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton and edges:
                if self.windowHandle() and self.windowHandle().startSystemResize(edges):
                    return True
        return super().eventFilter(obj, event)

    def apply_theme(self):
        settings = self.store.settings
        light = settings.get('theme') == 'light'
        midnight = settings.get('theme') == 'midnight'
        accent = QColor(settings.get('accent', '#9A82FF'))
        if not accent.isValid():
            accent = QColor('#9A82FF')
        a = accent.name()
        ink = readable_accent(a, settings.get('theme', 'dark'))
        bg = '#F7F8FC' if light else ('#0C0E16' if midnight else '#24262D')
        surface = '#FFFFFF' if light else ('#151721' if midnight else '#30333C')
        surface2 = '#E9EBF3' if light else ('#222433' if midnight else '#414550')
        border = '#D3D6E3' if light else ('#303344' if midnight else '#525663')
        # Firefox-inspired density and hierarchy: neutral copy, restrained surfaces,
        # user accent on actionable icons, selections and active tabs only.
        fg = '#25313D' if light else ('#DFE3EE' if midnight else '#EEF0F5')
        muted = '#687483' if light else ('#9DA5B5' if midnight else '#B3BAC7')
        hover = '#E3E8F0' if light else ('#252937' if midnight else '#454953')
        selected = '#E5E8F2' if light else ('#303344' if midnight else '#484C58')
        bg = '#F6F7FA' if light else ('#11131A' if midnight else '#292C33')
        surface = '#FFFFFF' if light else ('#191B25' if midnight else '#343740')
        surface2 = '#F1F3F7' if light else ('#242736' if midnight else '#3D414B')
        border = '#DDE1E9' if light else ('#343747' if midnight else '#4B4F5A')
        from .appearance import layered_hex
        opacity = settings.get('interface_transparency', {})
        trans_toolbar = layered_hex(surface, bg, opacity.get('toolbar', 0))
        trans_tabs = layered_hex(surface, bg, opacity.get('tabs', 0))
        trans_bookmarks = layered_hex(surface, bg, opacity.get('bookmarks', 0))
        trans_settings = layered_hex(surface, bg, opacity.get('settings', 0))
        font_size = min(16, max(10, int(settings.get('theme_font_size', 12))))
        self.setStyleSheet(f'''
            QMainWindow, QWidget {{background:{bg};color:{fg};font-family:"Segoe UI",Arial;font-size:{font_size}px}}
            QWidget#toolbar {{background:{trans_toolbar};border-bottom:1px solid {border}}}
            QWidget#tabStrip {{background:{trans_tabs};border-bottom:1px solid {border}}}
            QWidget#dragArea {{background:{surface};border:0}}
            QToolButton {{color:{fg};background:transparent;border:0;border-radius:7px;padding:0;min-width:0;min-height:0}}
            QToolButton:hover {{background:{hover}}}
            QToolButton:disabled {{background:transparent;color:{muted}}}
            QToolButton#brand, QToolButton#brand:hover, QToolButton#brand:pressed {{background:transparent;border:0;border-radius:8px}}
            QToolButton#windowMin, QToolButton#windowMax, QToolButton#windowClose {{border-radius:4px}}
            QToolButton#windowClose:hover {{background:#C42B39}}
            QToolButton#tabClose {{background:transparent;border-radius:5px}}
            QToolButton#tabClose:hover {{background:{hover}}}
            QToolButton:pressed {{background:{selected}}}
            QToolButton#brand:hover, QToolButton#brand:pressed {{background:transparent;border:0}}
            QAbstractButton {{selection-color:{fg};selection-background-color:transparent}}
            QLineEdit#address {{background:{surface2};color:{fg};border:1px solid {border};border-radius:9px;padding:5px 12px;font-size:13px;selection-background-color:{a}}}
            QLineEdit#address:focus {{border:1px solid {a}}}
            QTabBar {{background:{trans_tabs};border:0}}
            QTabBar::tab {{background:{surface};border:0;color:{fg};padding:6px 10px;min-width:62px;max-width:200px;border-radius:7px;margin:2px}}
            QTabBar::close-button {{subcontrol-position:right;margin-left:0px;margin-right:6px}}
            QTabBar::tab:selected {{background:{selected};border-bottom:2px solid {a}}}
            QTabBar::tab:!selected {{border:0}}
            QTabBar::tab:hover {{background:{hover}}}
            QTabBar::scroller {{width:19px}}
            QStackedWidget {{background:{bg};border:0}}
            QWidget#workspace {{background:{bg}}}
            QWidget#bookmarkRail {{background:{trans_bookmarks};border:0}}
            QWidget#bookmarkResizeGrip {{background:transparent;border:0}}
            QToolButton#bookmarkLink, QToolButton#bookmarkMore {{color:{fg};background:{surface2};border:0;border-radius:7px;padding:3px 6px}}
            QWidget#settingRow {{background:{trans_settings};border:1px solid {border};border-radius:9px}}
            QWidget#settingRow:hover {{border-color:{a}}}
            QWidget#settingsRail {{background:{trans_settings};border:1px solid {border};border-radius:11px}}
            QLabel#railTitle {{color:{muted};font-size:10px;font-weight:700;letter-spacing:1px;padding:6px 3px 7px 3px}}
            QLineEdit#settingsFilter {{background:{surface2};color:{fg};border:1px solid {border};border-radius:7px;padding:3px 7px;font-size:11px}}
            QLineEdit#settingsFilter:focus {{border-color:{a}}}
            QListWidget#settingsSidebar {{background:transparent;border:0;font-size:12px;padding:0;outline:0}}
            QListWidget#settingsSidebar::item {{background:transparent;color:{fg};padding:3px 9px;border:0;border-left:2px solid transparent;border-radius:5px;margin:0px 0px 1px 0px}}
            QListWidget#settingsSidebar::item:hover {{background:{hover};color:{fg}}}
            QListWidget#settingsSidebar::item:selected {{background:{selected};color:{fg};border:0;border-left:2px solid {a}}}
            QListWidget#settingsSidebar::item:selected:active {{background:{selected};color:{fg}}}
            QListWidget#settingsSidebar::item:focus {{outline:0;border:0;border-left:2px solid {a};color:{fg}}}
            QLabel#sectionHeading {{font-size:19px;font-weight:700;color:{fg};margin-bottom:8px}}
            QLabel#settingsNote {{color:{muted};font-size:11px;line-height:1.35;padding:2px 3px 6px 3px}}
            QWidget#footer {{background:{surface};border-top:1px solid {border}}}
            QLabel#status, QLabel#mode {{font-size:10px;color:{muted};letter-spacing:.5px}}
            QPushButton {{background:{surface2};color:{fg};border:1px solid {border};padding:5px 10px;border-radius:7px;min-height:20px}}
            QPushButton:pressed {{background:{selected};color:{fg};border-color:{a}}}
            QPushButton:hover {{background:{hover};border-color:{a}}}
            QPushButton:disabled {{color:{muted};border-color:{border}}}
            QCheckBox {{color:{fg};spacing:7px;padding:3px 4px;min-height:22px}}
            QCheckBox::indicator {{width:15px;height:15px}}
            QComboBox {{min-height:23px}}
            QLineEdit, QComboBox, QListWidget {{background:{surface2};color:{fg};border:1px solid {border};border-radius:7px;padding:5px}}
            QLineEdit:focus, QComboBox:focus {{border:1px solid {a}}}
            QDialog, QMenu {{background:{surface};color:{fg}}}
            QMenu::item:selected {{background:{selected};color:{fg}}}
            QListWidget::item:selected {{background:{selected};color:{fg}}}
            QWidget#searchPicker {{background:{surface};border-radius:8px}}
            QLabel#searchPickerIcon {{font-size:22px;color:{ink}}}
            QComboBox#searchPickerCombo {{min-width:180px}}
            QTreeWidget::item:selected {{background:{selected};color:{fg}}}
            QAbstractItemView {{selection-color:{fg};selection-background-color:{selected};outline:0}}
            QAbstractItemView::item:focus {{border:0;outline:0}}
            QLabel {{border:0;background:transparent}}
            QCheckBox:focus, QPushButton:focus {{outline:0}}
            QScrollArea {{border:0;background:{bg}}}
            QScrollBar:vertical {{background:transparent;width:8px;margin:2px 0}}
            QScrollBar::handle:vertical {{background:{border};border-radius:4px;min-height:24px}}
            QScrollBar::handle:vertical:hover {{background:{muted}}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{height:0;border:0}}
            QWidget#settingRow QLabel {{background:transparent}}
            QToolTip {{background:{surface2};color:{fg};border:1px solid {border};padding:5px;border-radius:5px}}
        ''')
        for button in self.findChildren(IconButton):
            button.glyph_color = ink
            button.custom_color = next((self.store.settings.get('toolbar_colors', {}).get(k)
                                        for k, b in self._toolbar_widgets.items() if b is button), None)
            button.update()
        self.tabs.bar.accent = a
        self.tabs.bar.ink = fg
        self.tabs.bar.surface = surface
        self.tabs.bar.selected_surface = surface2
        self.tabs.bar.update()
        font_size = min(16, max(10, int(settings.get('theme_font_size', 12))))
        # Font size is applied through the root QSS style.
        if hasattr(self, '_toolbar_widgets'):
            address_color = self.store.settings.get('toolbar_colors', {}).get('address')
            self.address.setStyleSheet(f'color:{address_color};' if address_color else '')
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            kind = tab.property('nomiko_page')
            if kind in ('home', 'search', 'settings'):
                self.tabs.setTabIcon(i, self._nomiko_icon('⚙' if kind == 'settings' else 'N'))
        counts = self.interceptor.counts()
        self.mode_label.setText('PRIVATE  •  NOT ANONYMOUS' if self.private else
                                f'PROTECTION  •  ADS {counts["ads"]} / TRACKERS {counts["trackers"]}')

    def closeEvent(self, event):  # noqa: N802
        # Do not delete live QThread objects. Ask active downloads to cancel and
        # retry after worker termination; keep the GUI responsive meanwhile.
        all_jobs = list(self._update_workers)
        if self._update_center is not None:
            all_jobs += list(self._update_center.workers)
        running = [job for job in all_jobs if job.isRunning()]
        if running:
            for job in running:
                job.requestInterruption()
            QTimer.singleShot(700, self.close)
            event.ignore()
            return
        # A separate helper waits for this PID to exit and rechecks the SHA-256
        # before invoking the per-user NSIS installer. Not executed in Python mode.
        if self._pending_update:
            from pathlib import Path
            installer, expected_sha = self._pending_update
            helper = Path(sys.executable).resolve().parent / 'NOMIKO-UpdateHelper.exe'
            if getattr(sys, 'frozen', False) and helper.is_file():
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                try:
                    # Run a COPY outside the installation directory so NSIS
                    # can safely replace the app's own update helper executable.
                    from .updater import update_cache_dir
                    temp_helper = update_cache_dir() / 'NOMIKO-UpdateHelper.exe'
                    temp_helper.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(helper, temp_helper)
                    subprocess.Popen([str(temp_helper), '--pid', str(os.getpid()),
                        '--installer', str(installer), '--sha256', expected_sha],
                        close_fds=True, creationflags=flags)
                except OSError as exc:
                    QMessageBox.warning(self, 'NOMIKO update',
                        f'The update helper could not start: {exc}. Installer remains in your update cache.')
        app = QApplication.instance()
        if app and hasattr(app, 'windows') and self in app.windows:
            app.windows.remove(self)
        self._session_timer.stop()
        self._idle_timer.stop()
        if not self.private and not self._skip_final_session_save:
            self._save_open_tabs()
        if app:
            app.removeEventFilter(self)
        super().closeEvent(event)
