"""Additional NOMIKO 0.8 dialogs and split reader tools."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
import json
import os

from PySide6.QtCore import QEvent, QTimer, Qt, QUrl
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QInputDialog,
    QFileDialog, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QComboBox, QPlainTextEdit, QSplitter, QTabWidget, QToolButton, QVBoxLayout, QWidget,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from .productivity import (
    parse_bookmarks_html, bookmarks_to_html, safe_web_url,
    export_backup, import_backup, normalized_workspaces,
)
from .storage import APP_DIR
from .split_search import split_destination
from .vault import PasswordVault


def _simple_button(title, callback):
    b = QPushButton(title)
    b.clicked.connect(callback)
    return b


def import_export_dialog(browser):
    dialog = QDialog(browser)
    dialog.setWindowTitle('NOMIKO · Transfer & backups')
    dialog.resize(520, 310)
    lay = QVBoxLayout(dialog)
    lay.addWidget(QLabel('Transfer bookmarks with Firefox / Chrome HTML files, or back up NOMIKO data.'))
    lay.addWidget(QLabel('Backups contain settings, bookmarks, history, sessions, widgets and workspaces.\nThey DO NOT contain cookies, saved logins, passwords or the web cache.'))

    def import_html():
        filename, _ = QFileDialog.getOpenFileName(dialog, 'Import bookmarks', '', 'Bookmark HTML (*.html *.htm)')
        if not filename: return
        try:
            source = Path(filename)
            if source.stat().st_size > 8 * 1024 * 1024: raise ValueError('HTML exceeds 8 MB')
            rows = parse_bookmarks_html(source.read_text(encoding='utf-8-sig', errors='replace'))
            known = {i.get('url') for i in browser.store.bookmarks}
            added = 0
            for row in rows:
                if row['url'] not in known:
                    browser.store.bookmarks.append(row)
                    known.add(row['url'])
                    added += 1
            browser.store.save_bookmarks()
            browser.refresh_bookmarks()
            QMessageBox.information(dialog, 'Imported', f'Added {added} bookmarks.')
        except (OSError, ValueError) as exc:
            QMessageBox.warning(dialog, 'Import failed', str(exc))

    def export_html():
        filename, _ = QFileDialog.getSaveFileName(dialog, 'Export bookmarks', 'nomiko-bookmarks.html', 'Bookmark HTML (*.html)')
        if filename:
            try:
                Path(filename).write_text(bookmarks_to_html(browser.store.bookmarks), encoding='utf-8')
            except OSError as exc:
                QMessageBox.warning(dialog, 'Export failed', str(exc))

    def backup():
        filename, _ = QFileDialog.getSaveFileName(dialog, 'NOMIKO backup', 'nomiko-backup.zip', 'ZIP (*.zip)')
        if filename:
            try:
                count = export_backup(APP_DIR, Path(filename))
                QMessageBox.information(dialog, 'Export complete', f'Backed up {count} local files. Keep this backup private.')
            except (OSError, ValueError) as exc:
                QMessageBox.warning(dialog, 'Backup failed', str(exc))

    def restore():
        filename, _ = QFileDialog.getOpenFileName(dialog, 'Restore NOMIKO backup', '', 'ZIP (*.zip)')
        if not filename: return
        if QMessageBox.question(dialog, 'Restore backup', 'This will replace local settings/bookmarks/history. A snapshot of replaced files will be kept. Restart NOMIKO immediately after restore?') != QMessageBox.StandardButton.Yes:
            return
        try:
            number = import_backup(Path(filename), APP_DIR)
            # Avoid overwriting just-restored session.json as the old app closes.
            for win in list(getattr(QApplication.instance(), 'windows', [])):
                if getattr(win, 'store', None) is not None:
                    win._skip_final_session_save = True
                    if hasattr(win, '_session_timer'): win._session_timer.stop()
            QMessageBox.information(dialog, 'Backup restored', f'Restored {number} files. Close and restart NOMIKO now to load them. Do not change settings until restarting.')
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(dialog, 'Restore failed', str(exc))

    for name, cb in [('Import bookmarks from HTML', import_html), ('Export bookmarks to HTML', export_html),
                     ('Create local backup', backup), ('Restore local backup', restore)]:
        lay.addWidget(_simple_button(name, cb))
    lay.addStretch(1)
    dialog.exec()


class WorkspaceDialog(QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setWindowTitle('NOMIKO · Workspaces')
        self.resize(540, 420)
        root = QVBoxLayout(self)
        root.addWidget(QLabel('Save a set of ordinary tabs and open it later. Private tabs are never stored.'))
        self.list = QListWidget()
        root.addWidget(self.list)
        actions = QHBoxLayout()
        for name, cb in [('Save current tabs', self.save_current), ('Open', self.open_workspace), ('Delete', self.delete)]:
            actions.addWidget(_simple_button(name, cb))
        root.addLayout(actions)
        self.refresh()

    def refresh(self):
        self.list.clear()
        for name, urls in self.browser.store.workspaces.items():
            self.list.addItem(f'{name}  ·  {len(urls)} sites')
            self.list.item(self.list.count()-1).setData(Qt.ItemDataRole.UserRole, name)

    def current_name(self):
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def save_current(self):
        if self.browser.private:
            QMessageBox.warning(self, 'Unavailable', 'Workspaces are not saved from private windows.')
            return
        name, ok = QInputDialog.getText(self, 'Save workspace', 'Name:')
        name = name.strip()[:45]
        if not ok or not name: return
        urls = []
        from .ui import BrowserView
        for i in range(self.browser.tabs.count()):
            view = self.browser.tabs.widget(i)
            if isinstance(view, BrowserView):
                url = view.url().toString()
                if safe_web_url(url): urls.append(url)
        if not urls:
            QMessageBox.information(self, 'Empty workspace', 'Open a website before saving a workspace.')
            return
        self.browser.store.workspaces[name] = urls[:40]
        self.browser.store.save_workspaces()
        self.refresh()

    def open_workspace(self):
        name = self.current_name()
        if not name: return
        urls = self.browser.store.workspaces.get(name, [])
        if len(urls) > 15 and QMessageBox.question(self, 'Open many tabs?', f'Open {len(urls)} tabs?') != QMessageBox.StandardButton.Yes:
            return
        for url in urls:
            self.browser.new_tab(url)
        self.accept()

    def delete(self):
        name = self.current_name()
        if name and QMessageBox.question(self, 'Delete workspace?', f'Delete {name}?') == QMessageBox.StandardButton.Yes:
            self.browser.store.workspaces.pop(name, None)
            self.browser.store.save_workspaces()
            self.refresh()


class VaultDialog(QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.setWindowTitle('NOMIKO · Windows password vault')
        self.resize(510, 425)
        self.vault = PasswordVault(APP_DIR / 'passwords.dpapi')
        root = QVBoxLayout(self)
        root.addWidget(QLabel('Passwords encrypted with Windows DPAPI for your Windows account.\nNo cloud, no automatic form filling. Do not store them in a shared Windows account.'))
        self.list = QListWidget()
        root.addWidget(self.list)
        row = QHBoxLayout()
        for title, cb in [('Add', self.add), ('Copy password', self.copy_password), ('Delete', self.delete)]:
            row.addWidget(_simple_button(title, cb))
        root.addLayout(row)
        try:
            self.entries = self.vault.read()
        except Exception as exc:
            QMessageBox.warning(self, 'Vault unavailable', 'Windows could not decrypt this vault. No entries were changed.\n' + str(exc))
            self.entries = []
            self.setEnabled(False)
            return
        self.refresh()

    def refresh(self):
        self.list.clear()
        for e in self.entries:
            self.list.addItem(f'{e.get("site", "")}  ·  {e.get("username", "")}')

    def add(self):
        site, ok = QInputDialog.getText(self, 'Save login', 'Site (e.g. example.org):')
        if not ok or not site.strip(): return
        username, ok = QInputDialog.getText(self, 'Save login', 'Username:')
        if not ok: return
        password, ok = QInputDialog.getText(self, 'Save login', 'Password:', QLineEdit.EchoMode.Password)
        if not ok or not password: return
        self.entries.append({'site': site.strip()[:250], 'username':username[:250], 'password':password})
        self.vault.write(self.entries)
        self.refresh()

    def copy_password(self):
        idx = self.list.currentRow()
        if idx < 0 or idx >= len(self.entries): return
        password = self.entries[idx]['password']
        QApplication.clipboard().setText(password)
        QTimer.singleShot(20000, lambda: QApplication.clipboard().clear() if QApplication.clipboard().text()==password else None)
        QMessageBox.information(self, 'Copied', 'Password copied. NOMIKO will clear it from the clipboard after 20 seconds if unchanged.')

    def delete(self):
        idx = self.list.currentRow()
        if idx >= 0 and QMessageBox.question(self, 'Delete login', 'Delete the selected login from this device?') == QMessageBox.StandardButton.Yes:
            self.entries.pop(idx)
            self.vault.write(self.entries)
            self.refresh()


class SplitWebView(QWebEngineView):
    """Keep focus/navigation in the pane the user is interacting with."""

    def createWindow(self, window_type):  # noqa: N802
        return self.nomiko_split_pane.browser.new_tab()

    def focusInEvent(self, event):  # noqa: N802
        self.nomiko_split_pane.split.set_active(self.nomiko_split_pane)
        super().focusInEvent(event)

    def mousePressEvent(self, event):  # noqa: N802
        self.nomiko_split_pane.split.set_active(self.nomiko_split_pane)
        super().mousePressEvent(event)


class SplitPane(QWidget):
    """A standalone, navigable web view with its *own* address/search bar."""

    def __init__(self, split, title: str, initial_url: str = ''):
        super().__init__(split)
        self.split = split
        self.browser = split.browser
        self._local_query = ''
        self.setObjectName('splitPane')
        self.setMinimumWidth(245)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 4, 5, 5)
        layout.setSpacing(4)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(3)
        toolbar.setContentsMargins(1, 0, 1, 0)
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName('splitPaneLabel')
        self.title_label.setFixedWidth(42)
        toolbar.addWidget(self.title_label)

        def button(text, tip, callback):
            b = QToolButton(self)
            b.setText(text)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setObjectName('splitNav')
            b.setFixedSize(29, 31)
            b.clicked.connect(callback)
            toolbar.addWidget(b)
            return b

        self.back_btn = button('←', 'Back in ' + title, self.go_back)
        self.forward_btn = button('→', 'Forward in ' + title, self.go_forward)
        self.reload_btn = button('↻', 'Reload ' + title, self.reload)
        self.home_btn = button('⌂', 'New tab page in ' + title, self.show_home)
        self.address = QLineEdit(self)
        self.address.setObjectName('splitAddress')
        self.address.setPlaceholderText(f'Search or enter a URL · {title}')
        self.address.setClearButtonEnabled(True)
        self.address.setMinimumWidth(60)
        self.address.setToolTip(f'Search or open a website in the {title.lower()} pane')
        self.address.returnPressed.connect(self.search)
        self.address.installEventFilter(self)
        toolbar.addWidget(self.address, 1)
        self.search_btn = button('⌕', f'Search in {title}', self.search)
        self.search_btn.setObjectName('splitSearchBtn')
        layout.addLayout(toolbar)

        subbar = QHBoxLayout()
        subbar.setSpacing(6)
        subbar.setContentsMargins(3, 0, 3, 2)
        label = QLabel('Search engine:')
        label.setObjectName('splitPaneLabel')
        subbar.addWidget(label)
        self.engine = QComboBox(self)
        self.engine.setObjectName('splitEngine')
        engines = self.browser.store.settings.get('visible_engines', ['DuckDuckGo', 'NOMIKO Search', 'Google'])
        for name in engines:
            if name in ('DuckDuckGo', 'NOMIKO Search', 'Google'):
                self.engine.addItem(name)
        if not self.engine.count():
            self.engine.addItem('DuckDuckGo')
        preferred = self.browser.store.settings.get('search_engine', 'DuckDuckGo')
        if preferred in engines:
            self.engine.setCurrentText(preferred)
        self.engine.currentTextChanged.connect(lambda _=None: self.split.set_active(self))
        subbar.addWidget(self.engine)
        subbar.addStretch(1)
        layout.addLayout(subbar)

        self.view = SplitWebView(self)
        self.view.nomiko_split_pane = self  # handled by NOMIKO's existing QWebEnginePage
        self.view.setProperty('nomiko_page', 'home')
        self.view.setPage(self.browser._make_split_page(self.view))
        self.view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            not self.browser.store.settings.get('block_popups', True))
        self.view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        self.view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,
            self.browser.store.settings.get('autoplay_guard', True))
        self.view.urlChanged.connect(self.on_url_changed)
        self.view.loadFinished.connect(self.on_load_finished)
        self.view.titleChanged.connect(lambda _title: self.split.update_tab_title())
        layout.addWidget(self.view, 1)
        self.update_navigation()
        if safe_web_url(initial_url):
            self.navigate_url(initial_url)
        else:
            self.show_home()

    def eventFilter(self, watched, event):  # noqa: N802
        if watched is self.address and event.type() == QEvent.Type.FocusIn:
            self.split.set_active(self)
        return super().eventFilter(watched, event)

    def selected_url(self):
        if self.view.property('nomiko_page') == 'search':
            return 'nomiko://search?q=' + self._local_query
        if self.view.property('nomiko_page') == 'home':
            return ''
        return self.view.url().toString()

    def navigate_url(self, url: str):
        if safe_web_url(url):
            self.view.setProperty('nomiko_page', '')
            self._local_query = ''
            self.view.load(QUrl(url))
            self.address.setText(url)
            self.update_navigation()

    def search(self, text=None, engine=None):
        self.split.set_active(self)
        query = self.address.text() if text is None or isinstance(text, bool) else str(text)
        available = [self.engine.itemText(i) for i in range(self.engine.count())]
        provider = engine if engine in available else self.engine.currentText()
        if provider != self.engine.currentText():
            self.engine.setCurrentText(provider)
        destination = split_destination(query, provider)
        if destination is None:
            return
        kind, value = destination
        if kind == 'web':
            self.navigate_url(value)
        else:
            from .home import render_search_results
            self.view.setProperty('nomiko_page', 'search')
            self._local_query = value
            html = render_search_results(
                value, self.browser.store.settings.get('accent', '#9A82FF'),
                [] if self.browser.private else self.browser.store.bookmarks,
                [] if self.browser.private else self.browser.store.history,
                private=self.browser.private,
                theme=self.browser.store.settings.get('theme', 'dark'),
                visible_engines=self.browser.store.settings.get('visible_engines'),
                language=self.browser.store.settings.get('language', 'en'),
            )
            self.view.setHtml(html, QUrl.fromLocalFile(str(APP_DIR / 'nomiko-newtab.html')))
            self.address.setText(self.selected_url())
            self.update_navigation()

    def show_home(self):
        self.split.set_active(self)
        from .home import render_home
        s = self.browser.store.settings
        self.view.setProperty('nomiko_page', 'home')
        self._local_query = ''
        html = render_home(
            s.get('accent', '#9A82FF'),
            [] if self.browser.private else self.browser.store.bookmarks,
            private=self.browser.private, theme=s.get('theme', 'dark'),
            engine=self.engine.currentText(), visible_engines=s.get('visible_engines'),
            language=s.get('language', 'en'), widget_enabled=[],
        )
        self.view.setHtml(html, QUrl.fromLocalFile(str(APP_DIR / 'nomiko-newtab.html')))
        self.address.clear()
        self.update_navigation()

    def on_url_changed(self, url):
        if url.scheme() in ('http', 'https'):
            self.view.setProperty('nomiko_page', '')
            self._local_query = ''
        if not self.address.hasFocus():
            self.address.setText(self.selected_url())
        self.update_navigation()
        self.split.update_tab_title()

    def on_load_finished(self, ok):
        if ok and not self.browser.private and self.browser.store.settings.get('save_history', True):
            url = self.view.url().toString()
            if safe_web_url(url) and self.view.property('nomiko_page') not in ('home', 'search'):
                self.browser.store.add_history(url, self.view.title())
        self.update_navigation()

    def update_navigation(self):
        history = self.view.history()
        self.back_btn.setEnabled(history.canGoBack())
        self.forward_btn.setEnabled(history.canGoForward())
        if self.split.active_pane is self and self.split is self.browser.current_view():
            self.browser.update_address(self.split)

    def go_back(self):
        self.split.set_active(self)
        if self.view.history().canGoBack():
            self.view.back()

    def go_forward(self):
        self.split.set_active(self)
        if self.view.history().canGoForward():
            self.view.forward()

    def reload(self):
        self.split.set_active(self)
        kind = self.view.property('nomiko_page')
        if kind == 'home':
            self.show_home()
        elif kind == 'search':
            self.search(self._local_query, 'NOMIKO Search')
        else:
            self.view.reload()


class SplitViewTab(QWidget):
    """Two fully independent panes; each has its own URL/search and provider."""

    def __init__(self, browser, left_url='', right_url=''):
        super().__init__(browser)
        self.browser = browser
        self.setProperty('nomiko_page', 'split')
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.split = QSplitter(Qt.Orientation.Horizontal, self)
        self.split.setObjectName('splitSplitter')
        root.addWidget(self.split, 1)
        self.active_pane = None
        self.left_pane = SplitPane(self, 'Left', left_url)
        self.right_pane = SplitPane(self, 'Right', right_url)
        self.left = self.left_pane.view  # compatibility with existing code
        self.right = self.right_pane.view
        self.left_address = self.left_pane.address
        self.right_address = self.right_pane.address
        self.split.addWidget(self.left_pane)
        self.split.addWidget(self.right_pane)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 1)
        self.split.setChildrenCollapsible(False)
        self.set_active(self.right_pane)
        self.right_pane.address.setFocus()

    def set_active(self, pane):
        if pane is self.active_pane:
            return
        self.active_pane = pane
        for p in (getattr(self, 'left_pane', None), getattr(self, 'right_pane', None)):
            if p is not None:
                p.setProperty('splitActive', p is pane)
                p.style().unpolish(p)
                p.style().polish(p)
        if self.browser.current_view() is self:
            self.browser.update_address(self)
            self.browser.update_bookmark_button()

    def update_tab_title(self):
        if not hasattr(self, 'right_pane'):
            return
        idx = self.browser.tabs.indexOf(self)
        if idx >= 0:
            left_title = (self.left.title() or 'Left')[:30]
            right_title = (self.right.title() or 'Right')[:30]
            self.browser.tabs.setTabToolTip(idx, f'Left: {left_title}\nRight: {right_title}')
