"""NOMIKO desktop browser (Windows 11), alpha / experimental build."""
import sys
from PySide6.QtWidgets import QApplication
from src.ui import BrowserWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('NOMIKO')
    app.setOrganizationName('NOMIKO')
    app.windows = []
    window = BrowserWindow()
    app.windows.append(window)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
