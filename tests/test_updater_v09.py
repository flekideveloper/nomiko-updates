"""NOMIKO update security checks (offline, no real GitHub access)."""
import base64
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from src import updater


class SignedUpdateTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.patcher = patch.object(updater, 'PUBLIC_ED25519_KEY_B64', base64.b64encode(public).decode())
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def signed(self, **changes):
        info = {
            'schema': 1,
            'version': '0.9.1',
            'channel': 'alpha',
            'tag': 'v0.9.1-alpha',
            'asset': 'NOMIKO-Setup-0.9.1-alpha.exe',
            'sha256': 'a'*64,
            'size': 1024,
            'notes': 'Bug fixes',
        }
        info.update(changes)
        raw = json.dumps(info, separators=(',', ':')).encode()
        sig = base64.b64encode(self.key.sign(raw))
        return raw, sig

    def test_valid_release(self):
        raw, sig = self.signed()
        release = updater.verify_manifest(raw, sig, expected_tag='v0.9.1-alpha')
        self.assertEqual(release.version, '0.9.1')
        self.assertEqual(release.download_url, 'https://github.com/flekideveloper/nomiko-updates/releases/download/v0.9.1-alpha/NOMIKO-Setup-0.9.1-alpha.exe')

    def test_tampering_rejected(self):
        raw, sig = self.signed()
        with self.assertRaises(updater.UpdateError):
            updater.verify_manifest(raw + b' ', sig, expected_tag='v0.9.1-alpha')

    def test_wrong_key_rejected(self):
        raw, _ = self.signed()
        badsig = base64.b64encode(Ed25519PrivateKey.generate().sign(raw))
        with self.assertRaises(updater.UpdateError):
            updater.verify_manifest(raw, badsig, expected_tag='v0.9.1-alpha')

    def test_wrong_release_tag_rejected(self):
        raw, sig = self.signed()
        with self.assertRaises(updater.UpdateError):
            updater.verify_manifest(raw, sig, expected_tag='v0.9.2-alpha')

    def test_signed_bad_asset_rejected(self):
        raw, sig = self.signed(asset='../../evil.exe')
        with self.assertRaises(updater.UpdateError):
            updater.verify_manifest(raw, sig, expected_tag='v0.9.1-alpha')

    def test_signed_huge_file_rejected(self):
        raw, sig = self.signed(size=updater.MAX_INSTALLER + 1)
        with self.assertRaises(updater.UpdateError):
            updater.verify_manifest(raw, sig, expected_tag='v0.9.1-alpha')

    def test_signed_wrong_channel_rejected(self):
        raw, sig = self.signed(channel='unstable')
        with self.assertRaises(updater.UpdateError):
            updater.verify_manifest(raw, sig, expected_tag='v0.9.1-alpha')

    def test_version_order(self):
        self.assertTrue(updater.parse_version('0.10.0') > updater.parse_version('0.9.9'))
        with self.assertRaises(updater.UpdateError):
            updater.parse_version('v0.9.0')

    def test_installer_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'NOMIKO-Setup-0.9.1-alpha.exe'
            p.write_bytes(b'test installer')
            rel = updater.Release('0.9.1', 'alpha', 'v0.9.1-alpha', p.name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertTrue(updater.verify_file(p, rel))
            p.write_bytes(b'test installer modified')
            self.assertFalse(updater.verify_file(p, rel))

    def test_new_version_scan(self):
        item = {'tag_name': 'v0.9.1-alpha', 'prerelease': True, 'draft': False,
                'assets': [{'name': 'update.json'}, {'name': 'update.sig'}]}
        raw, sig = self.signed()
        def fetch(url, limit=updater.MAX_METADATA):
            if url.startswith('https://api.github.com'):
                return json.dumps([item]).encode()
            return sig if url.endswith('update.sig') else raw
        with patch.object(updater, 'fetch_bytes', side_effect=fetch):
            self.assertIsNotNone(updater.find_update('alpha', local_version='0.9.0'))
            self.assertIsNone(updater.find_update('stable', local_version='0.9.0'))
            self.assertIsNone(updater.find_update('alpha', local_version='0.9.1'))


if __name__ == '__main__':
    unittest.main()
