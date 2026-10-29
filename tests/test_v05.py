"""Behavioral regression checks that run without Qt or a network connection."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import storage
from src.home import render_home


class NomikoV05Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patcher = patch.multiple(storage, APP_DIR=self.root,
                                      SETTINGS_FILE=self.root/'settings.json',
                                      BOOKMARKS_FILE=self.root/'bookmarks.json',
                                      HISTORY_FILE=self.root/'history.json',
                                      SESSION_FILE=self.root/'session.json')
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.store = storage.Store()

    def test_history_can_be_disabled_without_erasing_records(self):
        self.store.add_history('https://example.org/1','One')
        self.store.settings['save_history'] = False
        self.store.save_settings()
        self.store.add_history('https://example.org/2','Two')
        self.assertEqual(len(storage.Store().history),1)
        self.store.remove_history_indexes({0})
        self.assertFalse(storage.Store().history)

    def test_bookmark_management_and_folder(self):
        self.assertTrue(self.store.add_bookmark('https://example.org','Hi','toolbar'))
        self.assertFalse(self.store.add_bookmark('https://example.org','Duplicate','toolbar'))
        self.assertTrue(self.store.update_bookmark(0,'New','https://example.net','Personal'))
        self.assertEqual(storage.Store().bookmarks[0]['folder'], 'Personal')
        self.assertTrue(self.store.delete_bookmark(0))
        self.assertFalse(storage.Store().bookmarks)

    def test_wallpaper_copied_locally_and_size_checked(self):
        src = self.root / 'photo.gif'
        src.write_bytes(b'GIF89a' + b'0' * 80)
        self.assertTrue(self.store.save_wallpaper(src))
        self.assertEqual(self.store.wallpaper().name, 'wallpaper.gif')
        self.assertFalse(self.store.save_wallpaper(self.root / 'missing.gif'))
        self.store.remove_wallpaper()
        self.assertIsNone(self.store.wallpaper())

    def test_custom_home_sections_and_safe_color(self):
        html = render_home('#9A82FF', [], home_order=['search','title','logo'],
                           home_hidden=['logo'], home_colors={'title':'#FF0000'},
                           wallpaper='wallpaper.gif')
        self.assertLess(html.index('<section class="home-part" data-name="search"'), html.index('<section class="home-part" data-name="title"'))
        self.assertNotIn('<section class="home-part" data-name="logo"', html)
        self.assertIn('url("wallpaper.gif")', html)
        self.assertIn('#FF0000', html)
        evil = render_home('#9A82FF', [], home_colors={'title':'red;}</style><script>'},
                           wallpaper='javascript:alert(1)')
        self.assertNotIn('red;}</style><script>', evil)
        self.assertNotIn('url("javascript:', evil)

    def test_local_ui_preferences_survive_reload(self):
        self.store.settings.update({
            'bookmark_position':'right', 'bookmark_bar_visible':True,
            'toolbar_order':list(reversed(storage.TOOLBAR_ITEMS)),
            'toolbar_hidden':['brand','private'],
            'home_hidden':['kicker'],
            'sidebar_width':283,
            'account_nickname':'Test user',
            'account_email':'',
        })
        self.store.save_settings()
        loaded = storage.Store().settings
        self.assertEqual(loaded['bookmark_position'],'right')
        self.assertEqual(loaded['sidebar_width'],283)
        self.assertEqual(loaded['toolbar_order'][0],'menu')
        self.assertEqual(loaded['toolbar_hidden'],['brand','private'])
        self.assertEqual(loaded['account_nickname'],'Test user')


if __name__ == '__main__':
    unittest.main()
