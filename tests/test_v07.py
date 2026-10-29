"""v0.7 local widgets, escaping, defaults and tuning regression tests."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src import storage
from src.widgets import WIDGETS, DEFAULT_WIDGETS, render_widgets, normalize_widgets, WIDGET_SCRIPT
from src.home import render_home


class V07Tests(unittest.TestCase):
    def test_grey_default_and_new_options(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            with patch.object(storage, 'SETTINGS_FILE', r/'settings.json'), \
                 patch.object(storage, 'WIDGET_DATA_FILE', r/'widgets.json'), \
                 patch.object(storage, 'BOOKMARKS_FILE', r/'bookmarks.json'), \
                 patch.object(storage, 'HISTORY_FILE', r/'history.json'):
                s = storage.Store()
                self.assertEqual(s.settings['theme'], 'dark')  # Graphite
                self.assertEqual(s.settings['widget_enabled'], DEFAULT_WIDGETS)
                self.assertEqual(s.settings['cache_limit_mb'], 128)
                self.assertIn('weather', s.settings['widget_order'])
                self.assertIn('audio', s.settings['widget_order'])
                s.settings.update(theme='midnight', widget_density='compact', widget_columns='2', performance_mode='ultra')
                s.save_settings()
                restored = storage.Store()
                self.assertEqual(restored.settings['theme'], 'midnight')
                self.assertEqual(restored.settings['widget_density'], 'compact')
                self.assertEqual(restored.settings['widget_columns'], '2')
                self.assertEqual(restored.settings['performance_mode'], 'ultra')

    def test_widget_actions_persist_and_private_doesnt(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            with patch.object(storage, 'SETTINGS_FILE', r/'settings.json'), \
                 patch.object(storage, 'WIDGET_DATA_FILE', r/'widgets.json'), \
                 patch.object(storage, 'BOOKMARKS_FILE', r/'bookmarks.json'), \
                 patch.object(storage, 'HISTORY_FILE', r/'history.json'):
                s = storage.Store()
                self.assertTrue(s.apply_widget_action('note', {'text':'Hi <script>world</script>'}))
                self.assertTrue(s.apply_widget_action('task-add', {'text':'Read email'}))
                self.assertTrue(s.apply_widget_action('weather', {'city':'Kyiv'}))
                self.assertEqual(storage.Store().widget_data['tasks'], ['Read email'])
                self.assertEqual(storage.Store().widget_data['weather_city'], 'Kyiv')
                self.assertFalse(s.apply_widget_action('task-remove', {'idx':'banana'}))
                self.assertTrue(s.apply_widget_action('task-remove', {'idx':'0'}))
                self.assertEqual(storage.Store().widget_data['tasks'], [])
                private = storage.Store()
                private.apply_widget_action('note', {'text':'private message'}, persist=False)
                self.assertEqual(storage.Store().widget_data['note'], 'Hi <script>world</script>')

    def test_widget_order_and_escaping(self):
        order, enabled = normalize_widgets(['notes','notes','timer','bad'], ['notes','bad'])
        self.assertEqual(order[:2], ['notes','timer'])
        self.assertEqual(enabled, ['notes'])
        text = render_widgets(order, ['notes','tasks','links','audio','weather'], {
            'note':'<img src=x onerror=alert(1)>',
            'tasks':['<script>bad</script>'],
            'weather_city':'<bad>',
        }, [{'url':'https://example.com/?q="', 'title':'<b>evil</b>'}])
        self.assertNotIn('<script>bad</script>', text)
        self.assertNotIn('<img src=x onerror=alert(1)>', text)
        self.assertIn('&lt;script&gt;', text)
        self.assertIn('https://nomiko.invalid/widget', text)
        self.assertIn('w-record', text)
        self.assertIn('w-audiofile', text)

    def test_dashboard_html_script_and_no_external_scripts(self):
        html = render_home('#9A82FF', [], widget_enabled=list(WIDGETS),
                           widget_order=list(WIDGETS), theme='dark')
        self.assertIn('id="w-clock"', html)
        self.assertIn('id="w-calcrun"', html)
        self.assertIn('script-src', html)
        self.assertNotIn('src="https://', html)
        self.assertNotIn('Wikipedia', html)
        self.assertIn('#292C33', html)
        self.assertNotIn('Function(', WIDGET_SCRIPT)
        self.assertIn('25:00', html)

    def test_undo_close_shortcut_and_regressions(self):
        root = Path(__file__).resolve().parents[1]/'src'
        ui = (root/'ui.py').read_text('utf-8')
        self.assertIn("('Reopen closed tab', 'Ctrl+Shift+T'", ui)
        self.assertIn("'ultra': (10, 35)", ui)
        self.assertIn('def _request_weather', ui)
        self.assertIn("'widget_enabled'", ui)
        self.assertIn('setHttpCacheMaximumSize', ui)
        self.assertNotIn("home_order=self.store.settings.get('home_order'),\n            home_hidden=self.store.settings.get('home_hidden'),\n            home_colors=self.store.settings.get('home_colors'),\n        ), QUrl.fromLocalFile(str(APP_DIR / 'nomiko-newtab.html')))\n        if view is self.current_view():", ui) # old _render_search kwargs

if __name__ == '__main__': unittest.main()
