"""Pure-Python regression checks; no Qt required."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import storage
from src.home import render_home, render_search_results, INTERNAL_SEARCH_ACTION, _matches


class CoreTests(unittest.TestCase):
    def test_url_and_search_providers(self):
        self.assertEqual(storage.resolve_input('example.org/path'), 'https://example.org/path')
        self.assertEqual(storage.resolve_input('https://example.org/a'), 'https://example.org/a')
        self.assertEqual(storage.resolve_input('localhost:3000'), 'http://localhost:3000')
        self.assertEqual(storage.resolve_input('windows browser'), 'https://duckduckgo.com/?q=windows+browser')
        self.assertEqual(storage.resolve_input('windows browser', 'Google'),
                         'https://www.google.com/search?q=windows+browser')
        self.assertIn('q=a%2Bb', storage.resolve_input('a+b'))
        self.assertTrue(storage.resolve_input('javascript:alert(1)').startswith('https://'))
        self.assertTrue(storage.is_navigation_input('example.org/path'))
        self.assertFalse(storage.is_navigation_input('nomiko search'))

    def test_default_engine_and_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (patch.object(storage, 'SETTINGS_FILE', root / 'settings.json'),
                  patch.object(storage, 'BOOKMARKS_FILE', root / 'bookmarks.json'),
                  patch.object(storage, 'HISTORY_FILE', root / 'history.json')):
                store = storage.Store()
                self.assertEqual(store.settings['search_engine'], 'DuckDuckGo')
                self.assertFalse(store.toggle_bookmark('about:blank', 'Home'))
                self.assertTrue(store.toggle_bookmark('https://example.org', 'Example'))
                store.add_history('https://example.org', 'Example')
                self.assertEqual(len(storage.Store().bookmarks), 1)
                self.assertEqual(len(storage.Store().history), 1)
                self.assertFalse(store.toggle_bookmark('https://example.org', 'Example'))
                store.clear_history()
                self.assertEqual(storage.Store().history, [])

    def test_home_no_bridge_required_and_selection_works(self):
        html = render_home('#9A82FF', [])
        self.assertIn('action="' + INTERNAL_SEARCH_ACTION + '"', html)
        self.assertIn('method="GET"', html)
        self.assertIn('name="q"', html)
        self.assertIn('form="nomikoSearchForm"', html)
        self.assertIn('<option value="DuckDuckGo" selected>', html)
        self.assertIn('<option value="NOMIKO Search">', html)
        self.assertIn('<option value="Google">', html)
        self.assertNotIn('nomikoBridge', html)
        self.assertNotIn('Wikipedia', html)
        self.assertIn('user-select:none', html)

    def test_html_escapes_untrusted_bookmarks(self):
        html = render_home('#9A82FF', [{
            'url': 'https://example.org/?x="', 'title': '<script>alert(1)</script>',
        }])
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('&quot;', html)
        self.assertIn('Content-Security-Policy', html)

    def test_local_search_no_wikipedia_requests(self):
        html = render_search_results('alpha', '#9A82FF', [
            {'url': 'https://alpha.example.org', 'title': 'Alpha'},
            {'url': 'https://beta.example.org', 'title': 'Beta'},
        ], [])
        self.assertIn('https://alpha.example.org', html)
        self.assertNotIn('https://beta.example.org', html)
        self.assertNotIn('https://en.wikipedia.org', html)
        self.assertIn('Search on DuckDuckGo', html)
        self.assertIn('Search on Google', html)
        self.assertIn('No Wikipedia requests', html)

    def test_search_html_escapes_query_and_results(self):
        html = render_search_results('<script>alert(1)</script>', '#9A82FF', [], [])
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('user-select:none', html)

    def test_ranking_dedupes_history_and_bookmarks(self):
        rows = _matches('private browser', [
            {'url': 'https://example.com', 'title': 'Private Browser'},
        ], [
            {'url': 'https://example.com', 'title': 'Private Browser'},
        ])
        self.assertEqual(rows, [('BOOKMARK', 'Private Browser', 'https://example.com')])

    def test_session_restoration_validates_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (patch.object(storage, 'SETTINGS_FILE', root / 'settings.json'),
                  patch.object(storage, 'BOOKMARKS_FILE', root / 'bookmarks.json'),
                  patch.object(storage, 'HISTORY_FILE', root / 'history.json'),
                  patch.object(storage, 'SESSION_FILE', root / 'session.json')):
                store = storage.Store()
                self.assertFalse(store.settings['restore_tabs'])
                self.assertEqual(store.read_session(), {'tabs': [], 'active': 0})
                store.save_session([
                    {'kind': 'web', 'url': 'https://example.com/article?q=abc'},
                    {'kind': 'home'},
                    {'kind': 'search', 'query': 'browser privacy'},
                    {'kind': 'settings'},
                    {'kind': 'web', 'url': 'file:///C:/secrets.txt'},
                    {'kind': 'web', 'url': 'javascript:alert(1)'},
                    {'kind': 'web', 'url': 'https://user:secret@example.com'},
                    {'kind': 'web', 'url': 'https://nomiko.invalid/search?q=test'},
                    {'kind': 'web', 'url': 'http://['},
                ], 2)
                session = store.read_session()
                self.assertEqual(session['active'], 2)
                self.assertEqual([t['kind'] for t in session['tabs']],
                                 ['web', 'home', 'search', 'settings'])
                self.assertEqual(session['tabs'][0]['url'], 'https://example.com/article?q=abc')
                store.clear_session()
                self.assertEqual(store.read_session(), {'tabs': [], 'active': 0})

    def test_removed_search_engines_not_displayed_on_home(self):
        html = render_home('#9A82FF', [], engine='DuckDuckGo',
                           visible_engines=['DuckDuckGo'])
        self.assertIn('<option value="DuckDuckGo" selected>', html)
        self.assertNotIn('<option value="Google">', html)
        self.assertNotIn('<option value="NOMIKO Search">', html)

    def test_readable_accent_contrast(self):
        self.assertEqual(storage.readable_accent('#000000', 'light'), '#000000')
        self.assertNotEqual(storage.readable_accent('#FFFFFF', 'light'), '#FFFFFF')
        self.assertNotEqual(storage.readable_accent('#000000', 'dark'), '#000000')
        self.assertTrue(storage.readable_accent('#9A82FF', 'dark').startswith('#'))


if __name__ == '__main__':
    unittest.main()
