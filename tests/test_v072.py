"""New v0.7.2 offline regressions: no Qt required."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from src import storage
from src.appearance import layered_hex

ROOT = Path(__file__).resolve().parents[1] / 'src'


class V072Tests(TestCase):
    def test_default_privacy_and_blend(self):
        d = storage.DEFAULT_SETTINGS
        self.assertTrue(d['privacy_webrtc_public_only'])
        self.assertFalse(d['privacy_dns_prefetch'])
        self.assertEqual(d['interface_transparency']['toolbar'], 0)
        self.assertEqual(layered_hex('#FFFFFF', '#000000', 0), '#FFFFFF')
        self.assertNotEqual(layered_hex('#FFFFFF', '#000000', 65), '#FFFFFF')

    def test_transparency_clamp_and_bookmark_width(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch.object(storage, 'SETTINGS_FILE', folder/'settings.json'), \
                    patch.object(storage, 'BOOKMARKS_FILE', folder/'bookmarks.json'), \
                    patch.object(storage, 'HISTORY_FILE', folder/'history.json'), \
                    patch.object(storage, 'WIDGET_DATA_FILE', folder/'widgets.json'), \
                    patch.object(storage, 'DOWNLOADS_FILE', folder/'downloads.json'):
                store = storage.Store()
                store.settings['interface_transparency'] = {'tabs': 99, 'settings': -7}
                store.settings['bookmark_sidebar_width'] = 900
                store.save_settings()
                restarted = storage.Store()
                self.assertEqual(restarted.settings['interface_transparency']['tabs'], 65)
                self.assertEqual(restarted.settings['interface_transparency']['settings'], 0)
                self.assertEqual(restarted.settings['bookmark_sidebar_width'], 360)

    def test_download_records_stay_on_device_and_can_be_removed(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            with patch.object(storage, 'SETTINGS_FILE', folder/'settings.json'), \
                    patch.object(storage, 'BOOKMARKS_FILE', folder/'bookmarks.json'), \
                    patch.object(storage, 'HISTORY_FILE', folder/'history.json'), \
                    patch.object(storage, 'WIDGET_DATA_FILE', folder/'widgets.json'), \
                    patch.object(storage, 'DOWNLOADS_FILE', folder/'downloads.json'):
                store = storage.Store()
                ident = store.record_download(str(folder/'test.zip'), 'https://example.org/file')
                self.assertEqual(len(storage.Store().download_history), 1)
                # The old active record becomes interrupted on restart.
                self.assertEqual(storage.Store().download_history[0]['status'], 'Interrupted')
                store.finish_download(ident, 'DownloadCompleted')
                self.assertEqual(storage.Store().download_history[0]['status'], 'DownloadCompleted')
                store.remove_downloads({ident})
                self.assertEqual(storage.Store().download_history, [])

    def test_tabs_downloads_privacy_and_settings_are_wired(self):
        ui = (ROOT/'ui.py').read_text()
        settings = (ROOT/'settings_page.py').read_text()
        managers = (ROOT/'managers.py').read_text()
        self.assertIn('return QSize(41, max(40, self.width()-10))', ui)
        self.assertIn('rows * 41 + 2', ui)
        self.assertIn('QToolButton#brand:hover, QToolButton#brand:pressed', ui)
        self.assertIn('def set_side_width(self, value)', ui)
        self.assertIn('def _save_bookmark_sidebar_width', ui)
        self.assertIn('searchPickerCombo', ui)
        self.assertIn('record_download', ui)
        self.assertIn("self.row(box, 'FMAIL (optional)', email)", settings)
        self.assertIn('def update_wallpaper_preview', settings)
        self.assertIn('privacy_webrtc_public_only', settings)
        self.assertIn('set_transparency', settings)
        self.assertIn('Delete file…', managers)
        self.assertIn('Remove entry', managers)
        self.assertIn('Clear download history', managers)
