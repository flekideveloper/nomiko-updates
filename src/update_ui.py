"""NOMIKO update center. All network I/O runs outside the GUI thread."""
from __future__ import annotations

import os
from pathlib import Path
import sys

from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout

from .update_trust import CURRENT_VERSION
from .updater import find_update, download_installer, UpdateError


class UpdateWorker(QThread):
    result = Signal(object)
    failed = Signal(str)
    progress_changed = Signal(int)

    def __init__(self, job, *, channel='alpha', release=None, parent=None):
        super().__init__(parent)
        self.job, self.channel, self.release = job, channel, release

    def run(self):
        try:
            if self.job == 'check':
                self.result.emit(find_update(self.channel))
            else:
                def progress(value):
                    if self.isInterruptionRequested():
                        raise UpdateError('Update download cancelled')
                    self.progress_changed.emit(value)
                self.result.emit(download_installer(self.release, progress))
        except (UpdateError, ValueError, OSError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f'Unexpected update error: {type(exc).__name__}')


class UpdateCenter(QDialog):
    def __init__(self, browser):
        super().__init__(browser)
        self.browser = browser
        self.release = None
        self.installer = None
        self.workers = []
        self.setWindowTitle('NOMIKO · Updates')
        self.resize(485, 330)
        self.setMinimumWidth(420)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.addWidget(QLabel(f'NOMIKO {CURRENT_VERSION} Alpha'))
        description = QLabel('Official releases: flekideveloper/nomiko-updates.\nEvery update must pass Ed25519 signature and SHA-256 checks. Your browsing data stays local.')
        description.setWordWrap(True)
        root.addWidget(description)
        row = QHBoxLayout()
        row.addWidget(QLabel('Channel'))
        self.channel = QComboBox()
        self.channel.addItems(['alpha', 'stable'])
        self.channel.setCurrentText(browser.store.settings.get('updates_channel', 'alpha'))
        self.channel.currentTextChanged.connect(lambda value: browser.update_preference(updates_channel=value))
        row.addWidget(self.channel)
        row.addStretch()
        root.addLayout(row)
        self.auto_check = QCheckBox('Check for updates at startup')
        self.auto_check.setChecked(browser.store.settings.get('updates_auto_check', True))
        self.auto_check.toggled.connect(lambda v: browser.update_preference(updates_auto_check=v))
        root.addWidget(self.auto_check)
        self.status = QLabel('Ready to check. Checking contacts GitHub, which may see your IP address.')
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.hide()
        root.addWidget(self.progress)
        row2 = QHBoxLayout()
        self.check_button = QPushButton('Check now')
        self.check_button.clicked.connect(self.check)
        self.download_button = QPushButton('Download verified update')
        self.download_button.setEnabled(False)
        self.download_button.clicked.connect(self.download)
        self.install_button = QPushButton('Install after closing')
        self.install_button.setEnabled(False)
        self.install_button.clicked.connect(self.install)
        row2.addWidget(self.check_button)
        row2.addWidget(self.download_button)
        root.addLayout(row2)
        root.addWidget(self.install_button)
        root.addStretch()

    def _run_worker(self, kind, *, release=None):
        worker = UpdateWorker(kind, channel=self.channel.currentText(), release=release, parent=self.browser)
        self.workers.append(worker)
        worker.result.connect(lambda value, k=kind: self._success(k, value))
        worker.failed.connect(self._error)
        worker.progress_changed.connect(self.progress.setValue)
        worker.finished.connect(lambda w=worker: self._cleanup(w))
        worker.start()

    def _cleanup(self, worker):
        if worker in self.workers:
            self.workers.remove(worker)
        worker.deleteLater()

    def _busy(self, value):
        self.check_button.setEnabled(not value)
        self.download_button.setEnabled(bool(self.release) and not value)
        self.channel.setEnabled(not value)

    def check(self):
        self.release = None
        self.installer = None
        self.install_button.setEnabled(False)
        self._busy(True)
        self.status.setText('Checking official releases and signatures…')
        self.progress.hide()
        self._run_worker('check')

    def download(self):
        if not self.release:
            return
        self._busy(True)
        self.progress.setValue(0)
        self.progress.show()
        self.status.setText(f'Downloading and verifying {self.release.asset}…')
        self._run_worker('download', release=self.release)

    def _success(self, kind, value):
        self._busy(False)
        if kind == 'check':
            self.release = value
            self.download_button.setEnabled(bool(value))
            self.status.setText(
                f'Available: NOMIKO {value.version} ({value.channel})\n{value.notes[:220]}'
                if value else 'NOMIKO is up to date on this channel.'
            )
        elif kind == 'download':
            self.installer = Path(value)
            self.progress.setValue(100)
            self.status.setText('Installer downloaded. Signature and hash were verified. You can install after closing NOMIKO.')
            self.install_button.setEnabled(True)

    def _error(self, detail):
        self._busy(False)
        self.status.setText(f'Update not installed. {detail}')

    def install(self):
        if not self.release or not self.installer:
            return
        frozen = getattr(sys, 'frozen', False)
        helper = Path(sys.executable).resolve().parent / 'NOMIKO-UpdateHelper.exe'
        if not frozen or not helper.is_file():
            QMessageBox.information(self, 'NOMIKO · Portable/developer mode',
                'Automatic installation is available in the packaged NOMIKO EXE.\n'
                'For this Python development build, close NOMIKO and manually run the verified installer located at:\n\n'
                + str(self.installer))
            return
        choice = QMessageBox.question(self, 'Install NOMIKO update',
            'Close NOMIKO now? The verified installer will run automatically once the browser exits.\n'
            'Open tabs are preserved only if tab restoration is enabled.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if choice != QMessageBox.StandardButton.Yes:
            return
        self.browser._pending_update = (self.installer, self.release.sha256)
        from PySide6.QtWidgets import QApplication
        QApplication.instance().closeAllWindows()
