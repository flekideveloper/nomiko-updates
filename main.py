"""NOMIKO desktop browser (Windows 11)."""
from pathlib import Path
import os
import sys
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from src.ui import BrowserWindow

def icon_path() -> Path:
    bundle = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return bundle / 'assets' / 'NOMIKO.ico'

def main():
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('NOMIKO.Browser')
        except (AttributeError, OSError):
            pass
    app = QApplication(sys.argv)
    app.setApplicationName('NOMIKO')
    app.setOrganizationName('NOMIKO')
    app.setWindowIcon(QIcon(str(icon_path())))
    app.windows = []
    window = BrowserWindow()
    window.setWindowIcon(app.windowIcon())
    app.windows.append(window)
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
