"""Split View navigation and wiring regression tests (do not require Qt)."""
from pathlib import Path
import unittest

from src.split_search import split_destination


ROOT = Path(__file__).resolve().parents[1]


class SplitSearchTests(unittest.TestCase):
    def test_independent_search_providers(self):
        self.assertEqual(split_destination('hello world', 'DuckDuckGo'),
                         ('web', 'https://duckduckgo.com/?q=hello+world'))
        self.assertEqual(split_destination('hello world', 'Google'),
                         ('web', 'https://www.google.com/search?q=hello+world'))
        self.assertEqual(split_destination('hello world', 'NOMIKO Search'),
                         ('local', 'hello world'))

    def test_direct_urls_override_search_engines(self):
        for engine in ('NOMIKO Search', 'Google', 'DuckDuckGo'):
            self.assertEqual(split_destination('example.com/docs', engine),
                             ('web', 'https://example.com/docs'))
            self.assertEqual(split_destination('https://example.com', engine),
                             ('web', 'https://example.com'))
        self.assertEqual(split_destination('   ', 'DuckDuckGo'), None)

    def test_reserved_schemes_never_execute(self):
        result = split_destination('javascript:alert(1)', 'Google')
        self.assertEqual(result[0], 'web')
        self.assertTrue(result[1].startswith('https://www.google.com/search?'))
        self.assertNotIn('https://nomiko.invalid', result[1])

    def test_split_controls_are_independent(self):
        source = (ROOT / 'src' / 'advanced_ui.py').read_text(encoding='utf-8')
        for needle in ('class SplitPane(', 'self.address.returnPressed.connect(self.search)',
                       "self.search_btn = button('⌕'", 'self.engine = QComboBox',
                       'split_destination(query, provider)', 'self.left_pane = SplitPane',
                       'self.right_pane = SplitPane', 'self.view.setHtml(html',
                       'self.view.setPage(self.browser._make_split_page(self.view))'):
            self.assertIn(needle, source)

    def test_split_search_is_dispatched_to_own_pane(self):
        source = (ROOT / 'src' / 'ui.py').read_text(encoding='utf-8')
        self.assertIn("pane = getattr(self.view, 'nomiko_split_pane', None)", source)
        self.assertIn('p.search(q, e)', source)
        self.assertIn('NomikoPage(self, view)', source)
        self.assertIn('view.active_pane.search(text)', source)


if __name__ == '__main__':
    unittest.main()
