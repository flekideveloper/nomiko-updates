"""NOMIKO 0.8 offline regression and portable data safety tests."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from src.productivity import (
    safe_web_url, bookmarks_to_html, parse_bookmarks_html,
    export_backup, import_backup, validate_backup, normalized_workspaces,
    render_reader,
)
from src.module_packs import parse_hosts_file, match_host
from src.theme_data import sanitize_theme
from src.storage import Store


class V08Tests(unittest.TestCase):
    def test_safe_urls_and_workspaces(self):
        self.assertTrue(safe_web_url('https://example.com/test?a=b'))
        self.assertFalse(safe_web_url('javascript:alert(1)'))
        self.assertFalse(safe_web_url('https://me:pass@example.com'))
        self.assertFalse(safe_web_url('https://example.com\nfoo'))
        raw = {'gaming':['https://example.com','file:///etc/passwd','https://me:pass@other.com']}
        self.assertEqual(normalized_workspaces(raw), {'gaming':['https://example.com']})
        self.assertEqual(normalized_workspaces([]), {})

    def test_bookmark_html_is_escaped_and_filtered(self):
        html = bookmarks_to_html([
            {'url':'https://example.org/?a="xyz"','title':'<script>alert(1)</script>'},
            {'url':'javascript:evil()','title':'unsafe'},
        ])
        self.assertNotIn('<script>', html)
        self.assertNotIn('javascript:evil()', html)
        rows = parse_bookmarks_html(html)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['title'], '<script>alert(1)</script>')
        self.assertEqual(rows[0]['url'], 'https://example.org/?a="xyz"')

    def test_reader_is_static_and_escaped(self):
        html = '<title>Test Reader</title><script>alert(1)</script><p>Hello &lt;script&gt;world&lt;/script&gt;. Article paragraph works!</p><p>Another paragraph of sufficient length.</p>'
        rendered = render_reader(html, 'https://example.com')
        self.assertNotIn('alert(1)', rendered)
        self.assertNotIn('<script>', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('Content-Security-Policy', rendered)

    def test_backup_only_allowlist_no_cache_or_passwords(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, value in [('settings.json',{'theme':'light'}),('bookmarks.json',[{'url':'https://example.com'}])]:
                (root/name).write_text(json.dumps(value))
            (root/'passwords.dpapi').write_bytes(b'SECRET DATA')
            (root/'cookies.sqlite').write_text('cookies')
            backup = root/'export.zip'
            count = export_backup(root,backup)
            self.assertEqual(count,2)
            with zipfile.ZipFile(backup) as archive:
                self.assertEqual(set(archive.namelist()), {'settings.json','bookmarks.json'})
            other=root/'other'
            count=import_backup(backup,other)
            self.assertEqual(count,2)
            self.assertEqual(json.loads((other/'settings.json').read_text()), {'theme':'light'})
            self.assertFalse((other/'passwords.dpapi').exists())

    def test_backup_cannot_extract_path_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            malicious=root/'malicious.zip'
            with zipfile.ZipFile(malicious,'w') as z:
                z.writestr('../evil.txt','bad')
            with self.assertRaises(ValueError):validate_backup(malicious)

    def test_backup_restoration_creates_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'settings.json').write_text('{"theme":"light"}')
            saved=root/'saved.zip'
            export_backup(root,saved)
            (root/'settings.json').write_text('{"theme":"midnight"}')
            import_backup(saved,root)
            self.assertEqual(json.loads((root/'settings.json').read_text())['theme'],'light')
            snapshots=list(root.glob('backup-before-restore-*'))
            self.assertEqual(len(snapshots),1)
            self.assertEqual(json.loads((snapshots[0]/'settings.json').read_text())['theme'],'midnight')

    def test_local_blocklist_hosts_and_suffix(self):
        lines='127.0.0.1 tracking.example.org\n0.0.0.0 annoying.ads.net\n# comment\nhttps://not-valid.example\n'
        hosts=parse_hosts_file(lines)
        self.assertEqual(hosts, frozenset({'tracking.example.org','annoying.ads.net'}))
        self.assertTrue(match_host('sub.tracking.example.org',hosts))
        self.assertFalse(match_host('eviltracking.example.org',hosts))
        self.assertFalse(match_host('tracking.example.org.evil.test',hosts))

    def test_theme_sanitizer(self):
        result=sanitize_theme({'theme':'midnight','accent':'#50AAee','theme_font_size':99, 'foo':'javascript:evil()','interface_transparency':{'toolbar':25,'other':-4}})
        self.assertEqual(result['theme'],'midnight')
        self.assertEqual(result['accent'],'#50AAEE')
        self.assertEqual(result['theme_font_size'],16)
        self.assertEqual(result['interface_transparency'],{'toolbar':25})
        with self.assertRaises(ValueError):sanitize_theme({'script':'bad'})

    def test_workspace_local_persistence(self):
        from src import storage
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'workspaces.json'
            with patch.object(storage,'WORKSPACES_FILE',target):
                store=Store()
                store.workspaces={'Work':['https://example.org']}
                store.save_workspaces()
                newer=Store()
                self.assertEqual(newer.workspaces['Work'],['https://example.org'])

    def test_ui_wiring_regression(self):
        source = (Path(__file__).parents[1]/'src'/'ui.py').read_text()
        for name in ('open_split_view', 'show_password_vault','show_workspaces', 'find_open_tab', 'request_picture_in_picture','open_reader_mode','show_theme_studio'):
            self.assertIn('def '+name+'(',source)
        self.assertIn('NomikoPage(self, view)',source)  # split panes use full browser safeguards
        self.assertIn('tabPinRequested.connect(self.toggle_pin_tab)',source)


if __name__ == '__main__': unittest.main()
