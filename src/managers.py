"""On-device managers for history, bookmarks and download requests."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget, QComboBox,
)


def _row_layout(*widgets):
    row = QHBoxLayout()
    for widget in widgets:
        widget.setMaximumWidth(160)
        row.addWidget(widget, 0)
    row.addStretch(1)
    return row


class HistoryDialog(QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setWindowTitle('NOMIKO · History')
        self.resize(770, 510)
        root = QVBoxLayout(self)
        root.addWidget(QLabel('History is stored locally. You can disable it under Settings → Privacy.'))
        self.search = QLineEdit()
        self.search.setMaximumWidth(490)
        self.search.setPlaceholderText('Filter by title, URL or date…')
        self.search.textChanged.connect(self.reload)
        root.addWidget(self.search)
        self.list = QTreeWidget()
        self.list.setHeaderLabels(['Visited (local time)', 'Page', 'Address'])
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setColumnWidth(0, 180)
        self.list.setColumnWidth(1, 270)
        self.list.itemDoubleClicked.connect(self.open_selected)
        root.addWidget(self.list, 1)
        open_btn = QPushButton('Open')
        open_btn.clicked.connect(self.open_selected)
        remove_btn = QPushButton('Delete selected')
        remove_btn.clicked.connect(self.remove_selected)
        clear_btn = QPushButton('Clear all history')
        clear_btn.clicked.connect(self.clear_all)
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        root.addLayout(_row_layout(open_btn, remove_btn, clear_btn, close_btn))
        self.reload()

    def reload(self, *_):
        self.list.clear()
        term = self.search.text().casefold()
        for index in reversed(range(len(self.browser.store.history))):
            record = self.browser.store.history[index]
            ts = str(record.get('time') or '')
            try: local_date = datetime.fromisoformat(ts).astimezone().strftime('%Y-%m-%d %H:%M')
            except ValueError: local_date = ts
            title = str(record.get('title') or '')
            url = str(record.get('url') or '')
            if term and term not in (title + url + local_date).casefold():
                continue
            item = QTreeWidgetItem([local_date, title, url])
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            self.list.addTopLevelItem(item)

    def open_selected(self, *_):
        items = self.list.selectedItems()
        if items:
            url = items[0].text(2)
            if url.startswith(('http://', 'https://')):
                self.browser.open_url(url, new_tab=True)

    def remove_selected(self):
        indexes = {item.data(0, Qt.ItemDataRole.UserRole) for item in self.list.selectedItems()}
        if not indexes: return
        self.browser.store.remove_history_indexes(indexes)
        self.reload()

    def clear_all(self):
        if QMessageBox.question(self, 'Clear history', 'Delete your locally stored visit history?') == QMessageBox.StandardButton.Yes:
            self.browser.store.clear_history()
            self.reload()


class BookmarksDialog(QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setWindowTitle('NOMIKO · Bookmarks')
        self.resize(770, 510)
        root = QVBoxLayout(self)
        root.addWidget(QLabel('Manage bookmarks and folders · double-click to open'))
        self.filter = QLineEdit()
        self.filter.setMaximumWidth(490)
        self.filter.setPlaceholderText('Find a bookmark…')
        self.filter.textChanged.connect(self.reload)
        root.addWidget(self.filter)
        self.list = QTreeWidget()
        self.list.setHeaderLabels(['Name', 'Folder', 'Address'])
        self.list.setColumnWidth(0, 230)
        self.list.setColumnWidth(1, 145)
        self.list.itemDoubleClicked.connect(self.open_selected)
        root.addWidget(self.list, 1)
        actions = [('Add', self.add), ('Edit', self.edit), ('Delete', self.remove),
                   ('Open', self.open_selected), ('Close', self.accept)]
        root.addLayout(_row_layout(*(self._button(name, cb) for name, cb in actions)))
        self.reload()

    def _button(self, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def reload(self, *_):
        self.list.clear()
        term = self.filter.text().casefold()
        for i, row in enumerate(self.browser.store.bookmarks):
            title = str(row.get('title') or row.get('url') or '')
            folder = str(row.get('folder', 'toolbar'))
            url = str(row.get('url') or '')
            if term and term not in (title + folder + url).casefold(): continue
            item = QTreeWidgetItem([title, folder, url])
            item.setData(0, Qt.ItemDataRole.UserRole, i)
            self.list.addTopLevelItem(item)

    def selected_index(self):
        items = self.list.selectedItems()
        return items[0].data(0, Qt.ItemDataRole.UserRole) if items else None

    def _editor(self, record=None):
        record = record or {}
        dialog = QDialog(self)
        dialog.setWindowTitle('Bookmark')
        form = QFormLayout(dialog)
        name = QLineEdit(str(record.get('title', '')))
        url = QLineEdit(str(record.get('url', 'https://')))
        folder = QLineEdit(str(record.get('folder', 'toolbar')))
        form.addRow('Name:', name)
        form.addRow('Address:', url)
        form.addRow('Folder (toolbar to pin):', folder)
        actions = QWidget()
        row = QHBoxLayout(actions)
        okay = QPushButton('Save')
        cancel = QPushButton('Cancel')
        okay.clicked.connect(dialog.accept)
        cancel.clicked.connect(dialog.reject)
        row.addWidget(okay)
        row.addWidget(cancel)
        form.addRow(actions)
        if dialog.exec() != QDialog.DialogCode.Accepted: return None
        result = (name.text().strip(), url.text().strip(), folder.text().strip() or 'toolbar')
        if not result[1].startswith(('http://', 'https://')):
            QMessageBox.warning(self, 'Invalid URL', 'Only HTTP and HTTPS bookmarks can be saved.')
            return None
        return result

    def add(self):
        fields = self._editor()
        if fields:
            self.browser.store.add_bookmark(fields[1], fields[0], fields[2])
            self._changed()

    def edit(self):
        idx = self.selected_index()
        if idx is None: return
        fields = self._editor(self.browser.store.bookmarks[idx])
        if fields:
            self.browser.store.update_bookmark(idx, fields[0], fields[1], fields[2])
            self._changed()

    def remove(self):
        idx = self.selected_index()
        if idx is not None:
            self.browser.store.delete_bookmark(idx)
            self._changed()

    def open_selected(self, *_):
        idx = self.selected_index()
        if idx is not None:
            self.browser.open_url(self.browser.store.bookmarks[idx]['url'], new_tab=True)

    def _changed(self):
        self.reload()
        self.browser.update_bookmark_button()
        self.browser.refresh_bookmarks()
        self.browser._refresh_internal_pages()


class DownloadsDialog(QDialog):
    """Persistent, local download history with explicit file deletion."""
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.setWindowTitle('NOMIKO · Downloads')
        self.resize(890, 550)
        root = QVBoxLayout(self)
        caption = QLabel('All download records stay on this PC. Removing a record does not delete its file.')
        caption.setWordWrap(True)
        root.addWidget(caption)
        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText('Search downloads by name, date, source or path…')
        self.filter.setMaximumWidth(530)
        self.filter.textChanged.connect(self.reload)
        root.addWidget(self.filter)
        self.list = QTreeWidget(self)
        self.list.setColumnCount(4)
        self.list.setHeaderLabels(['Date', 'File name', 'Status', 'Folder'])
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setColumnWidth(0, 140)
        self.list.setColumnWidth(1, 230)
        self.list.setColumnWidth(2, 120)
        self.list.itemDoubleClicked.connect(self.open_selected)
        root.addWidget(self.list, 1)
        buttons = [
            ('Open file', self.open_selected),
            ('Open folder', self.open_folder),
            ('Pause / Resume', self.toggle_pause),
            ('Cancel', self.cancel_selected),
            ('Remove entry', self.remove_selected),
            ('Delete file…', self.delete_file),
            ('Clear history', self.clear),
        ]
        action_row = QHBoxLayout()
        for title, callback in buttons:
            button = QPushButton(title)
            button.clicked.connect(callback)
            action_row.addWidget(button)
        root.addLayout(action_row)
        close_row = QHBoxLayout()
        close_row.addStretch()
        done = QPushButton('Close')
        done.clicked.connect(self.accept)
        close_row.addWidget(done)
        root.addLayout(close_row)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.reload)
        self.timer.start(1500)
        self.reload()

    def _records(self):
        if not self.browser.private:
            return list(self.browser.store.download_history)
        # Incognito never reads or writes the persistent download history.
        records = []
        for index, request in enumerate(self.browser.downloads):
            path = Path(request.downloadDirectory()) / request.downloadFileName()
            records.append({'id': f'private:{index}', 'path': str(path), 'time': '',
                            'url': request.url().toString(), 'status': request.state().name})
        return records

    def reload(self, *_):
        selected = {item.data(0, Qt.ItemDataRole.UserRole) for item in self.list.selectedItems()}
        self.list.clear()
        term = self.filter.text().casefold().strip()
        for record in reversed(self._records()):
            ident = str(record.get('id', ''))
            path = Path(str(record.get('path', '')))
            state = str(record.get('status', 'Unknown'))
            live = self.browser._active_downloads.get(ident)
            if live is not None and not live.isFinished():
                total = live.totalBytes()
                state = f'{100 * live.receivedBytes() // total}%' if total > 0 else 'Downloading'
            timestamp = str(record.get('time') or '')
            try: display_time = datetime.fromisoformat(timestamp).astimezone().strftime('%d.%m.%Y %H:%M')
            except ValueError: display_time = timestamp or 'This session'
            hay = ' '.join([display_time, str(path), state, str(record.get('url', ''))])
            if term and term not in hay.casefold(): continue
            row = QTreeWidgetItem([display_time, path.name, state, str(path.parent)])
            row.setToolTip(1, str(path))
            row.setData(0, Qt.ItemDataRole.UserRole, ident)
            self.list.addTopLevelItem(row)
            if ident in selected: row.setSelected(True)

    def selected_ids(self):
        return [item.data(0, Qt.ItemDataRole.UserRole) for item in self.list.selectedItems()]

    def selected_records(self):
        ids = set(self.selected_ids())
        return [r for r in self._records() if r.get('id') in ids]

    def open_selected(self, *_):
        rec = self.selected_records()
        if rec:
            file = Path(str(rec[0].get('path', '')))
            if file.is_file(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(file)))
            else: QMessageBox.information(self, 'File unavailable', 'The file was moved or deleted.')

    def open_folder(self):
        rec = self.selected_records()
        folder = Path(str(rec[0].get('path', ''))).parent if rec else Path(
            self.browser.store.settings.get('downloads_dir') or (Path.home()/'Downloads'))
        if folder.is_dir(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        else: QMessageBox.information(self, 'Folder unavailable', 'This folder no longer exists.')

    def toggle_pause(self):
        for ident in self.selected_ids():
            req = self.browser._active_downloads.get(ident)
            if req is not None and not req.isFinished():
                if req.isPaused(): req.resume()
                else: req.pause()
        self.reload()

    def cancel_selected(self):
        for ident in self.selected_ids():
            req = self.browser._active_downloads.get(ident)
            if req is not None and not req.isFinished(): req.cancel()
        self.reload()

    def remove_selected(self):
        if self.browser.private: return
        ids = self.selected_ids()
        if not ids: return
        self.browser.store.remove_downloads(ids)
        self.reload()

    def delete_file(self):
        records = self.selected_records()
        if not records: return
        paths = [Path(str(record.get('path',''))) for record in records]
        if QMessageBox.question(self, 'Delete downloaded files?',
            f'Delete {len(paths)} selected file(s) from disk? This cannot be undone.\n\n'
            + '\n'.join(str(path) for path in paths[:4]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        failures = []
        for path in paths:
            try:
                if path.is_file(): path.unlink()
            except OSError:
                failures.append(str(path))
        if failures: QMessageBox.warning(self, 'Could not delete', '\n'.join(failures[:5]))
        self.reload()

    def clear(self):
        if self.browser.private: return
        if QMessageBox.question(self, 'Clear download history',
            'Remove all saved download records? Actual files will NOT be deleted.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.browser.store.clear_downloads()
            self.reload()
