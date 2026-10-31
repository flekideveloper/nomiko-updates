"""Windows release smoke assertions; no GUI needed."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class TestNomikoWindowsBrand(unittest.TestCase):
    def test_shortcuts(self):
        nsi = (ROOT / 'installer/NOMIKO.nsi').read_text()
        self.assertIn('CreateShortCut "$DESKTOP\\NOMIKO.lnk"', nsi)
        self.assertIn('Delete "$DESKTOP\\NOMIKO.lnk"', nsi)
        self.assertIn('File /oname=NOMIKO.ico', nsi)
    def test_taskbar_icon(self):
        main = (ROOT / 'main.py').read_text()
        workflow = (ROOT / '.github/workflows/windows.yml').read_text()
        self.assertIn('SetCurrentProcessExplicitAppUserModelID', main)
        self.assertIn('app.setWindowIcon', main)
        self.assertIn('--icon assets/NOMIKO.ico', workflow)
        self.assertIn('--add-data', workflow)
    def test_release_version(self):
        from src.update_trust import CURRENT_VERSION
        self.assertEqual(CURRENT_VERSION, '0.9.1')
        self.assertIn('NOMIKO-Setup-0.9.1-alpha.exe', (ROOT / 'installer/NOMIKO.nsi').read_text())
        self.assertEqual((ROOT / '.github/release-request.txt').read_text().strip(), 'PUBLISH v0.9.1-alpha')
