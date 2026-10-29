"""NOMIKO v0.7.1 layout/defaults regressions (offline, without Qt)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from src import storage
from src.home import render_home
from src.widgets import DEFAULT_WIDGETS, render_widgets


class V071Tests(TestCase):
    def test_new_profiles_have_no_widgets(self):
        self.assertEqual(DEFAULT_WIDGETS, [])
        with TemporaryDirectory() as temp:
            p = Path(temp)
            with patch.object(storage, 'SETTINGS_FILE', p / 'settings.json'), \
                    patch.object(storage, 'BOOKMARKS_FILE', p / 'bookmarks.json'), \
                    patch.object(storage, 'HISTORY_FILE', p / 'history.json'), \
                    patch.object(storage, 'WIDGET_DATA_FILE', p / 'widgets.json'):
                store = storage.Store()
                self.assertEqual(store.settings['widget_enabled'], [])
                self.assertEqual(store.settings['theme'], 'dark')  # Graphite, not Midnight.
                store.settings['widget_enabled'] = ['notes', 'clock']
                store.save_settings()
                restored = storage.Store()
                self.assertEqual(restored.settings['widget_enabled'], ['notes', 'clock'])

    def test_clean_new_tab_no_empty_widget_notice_or_timers(self):
        html = render_home('#9A82FF', [], widget_enabled=[])
        self.assertIn('class="clean-home"', html)
        self.assertNotIn('widgets-empty', html)
        self.assertNotIn('widget-grid', html)
        self.assertNotIn('setInterval(', html)
        self.assertNotIn('w-clock', html)
        self.assertIn('nomikoSearchForm', html)

    def test_manual_widgets_still_work(self):
        html = render_home('#9A82FF', [], widget_enabled=['notes', 'clock'])
        self.assertIn('class="with-widgets"', html)
        self.assertIn('w-clock', html)
        self.assertIn('const byId=', html)
        self.assertIn('Your thoughts stay on this device', html)

    def test_sidebar_is_compact_right_and_searchable(self):
        settings = (Path(__file__).resolve().parents[1] / 'src' / 'settings_page.py').read_text('utf-8')
        self.assertIn('self.root.addWidget(self.rail, 0)', settings)
        self.assertIn('self.rail.setFixedWidth(168)', settings)
        self.assertIn('QSize(135, 27)', settings)
        self.assertIn('self.category_filter.textChanged.connect(self.filter_categories)', settings)
        self.assertIn('def hide_all_widgets(self)', settings)
        self.assertIn('self.set_preference(widget_enabled=[])', settings)
        self.assertNotIn('self.category_list.setFixedWidth(185)', settings)

    def test_quiet_theme_and_visible_tab_highlight(self):
        ui = (Path(__file__).resolve().parents[1] / 'src' / 'ui.py').read_text('utf-8')
        self.assertIn("fg = '#25313D' if light", ui)
        self.assertIn('QListWidget#settingsSidebar::item:selected', ui)
        self.assertIn('QScrollBar:vertical', ui)
        self.assertIn('self.tabs.bar.ink = fg', ui)
