"""Offline regression tests for NOMIKO built-in modules and preferences."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import storage
from src.blocklists import (
    AD_DOMAINS, TRACKER_DOMAINS, blocked_by, clean_tracking_url, matches_domain,
)


class V06Tests(unittest.TestCase):
    def test_default_modules_are_local_and_on(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(storage, 'SETTINGS_FILE', root / 'settings.json'), \
                 patch.object(storage, 'BOOKMARKS_FILE', root / 'bookmarks.json'), \
                 patch.object(storage, 'HISTORY_FILE', root / 'history.json'):
                s = storage.Store()
                for name in ('ad_blocking', 'tracker_blocking', 'block_popups',
                             'autoplay_guard', 'clean_tracking_links'):
                    self.assertTrue(s.settings[name], name)
                self.assertEqual(s.settings['performance_mode'], 'balanced')
                s.settings.update(ad_blocking=False, performance_mode='gaming',
                                  block_exceptions=['example.org'])
                s.save_settings()
                new = storage.Store()
                self.assertFalse(new.settings['ad_blocking'])
                self.assertEqual(new.settings['performance_mode'], 'gaming')
                self.assertEqual(new.settings['block_exceptions'], ['example.org'])

    def test_suffix_matching_without_confusing_unrelated_hosts(self):
        self.assertTrue(matches_domain('images.doubleclick.net', AD_DOMAINS))
        self.assertFalse(matches_domain('notdoubleclick.net', AD_DOMAINS))
        self.assertFalse(matches_domain('doubleclick.net.evil.example', AD_DOMAINS))
        self.assertTrue(matches_domain('connect.facebook.net', TRACKER_DOMAINS))

    def test_first_party_and_allowlist_respected(self):
        self.assertEqual(blocked_by('doubleclick.net', 'example.com'), 'ads')
        self.assertEqual(blocked_by('analytics.google.com', 'example.com'), 'trackers')
        self.assertIsNone(blocked_by('analytics.google.com', 'example.com', trackers=False))
        self.assertIsNone(blocked_by('doubleclick.net', 'example.com', ads=False))
        self.assertIsNone(blocked_by('doubleclick.net', 'example.com', exclusions=['example.com']))
        self.assertIsNone(blocked_by('google-analytics.com', 'google-analytics.com'))
        self.assertEqual(blocked_by('doubleclick.net', 'notexample.com', exclusions=['example.com']), 'ads')

    def test_link_cleaner_preserves_required_params_and_fragment(self):
        original = 'https://example.org/a?utm_source=x&id=12&fbclid=abc&empty=#section'
        self.assertEqual(clean_tracking_url(original), 'https://example.org/a?id=12&empty=#section')
        self.assertEqual(clean_tracking_url('https://example.org/search?q=music'), 'https://example.org/search?q=music')
        self.assertEqual(clean_tracking_url('about:blank?utm_source=x'), 'about:blank?utm_source=x')

    def test_settings_page_describes_modules_without_webextension_promise(self):
        page = (Path(__file__).resolve().parents[1] / 'src' / 'settings_page.py').read_text('utf-8')
        self.assertIn("self.section('Modules')", page)
        self.assertIn("self.section('Performance')", page)
        self.assertIn('Ad Block', page)
        self.assertIn('Tracker Guard', page)
        self.assertIn('Link Cleaner', page)


if __name__ == '__main__':
    unittest.main()
