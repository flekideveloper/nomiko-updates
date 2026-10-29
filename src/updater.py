"""NOMIKO signed update discovery and verified installer downloads.

Trust is anchored in a built-in Ed25519 public key, not GitHub JSON or TLS alone.
No downloaded code runs during checking/downloading.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .update_trust import CURRENT_VERSION, PUBLIC_ED25519_KEY_B64, RELEASE_OWNER, RELEASE_REPO

RELEASE_ROOT = f'https://github.com/{RELEASE_OWNER}/{RELEASE_REPO}/releases/download'
API_URL = f'https://api.github.com/repos/{RELEASE_OWNER}/{RELEASE_REPO}/releases?per_page=30'
MAX_METADATA = 64 * 1024
MAX_INSTALLER = 650 * 1024 * 1024
VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+$')
TAG_PATTERN = re.compile(r'^v\d+\.\d+\.\d+(?:-(?:alpha|beta|rc))?$')
INSTALLER_PATTERN = re.compile(r'^NOMIKO-Setup-\d+\.\d+\.\d+(?:-alpha|-beta|-rc)?\.exe$')


class UpdateError(Exception):
    pass


@dataclass(frozen=True)
class Release:
    version: str
    channel: str
    tag: str
    asset: str
    size: int
    sha256: str
    notes: str = ''

    @property
    def download_url(self) -> str:
        # All URL components have strict patterns; arbitrary download URLs are forbidden.
        return f'{RELEASE_ROOT}/{self.tag}/{self.asset}'


def parse_version(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not VERSION_PATTERN.fullmatch(value):
        raise UpdateError('Invalid update version')
    return tuple(int(x) for x in value.split('.'))


def fetch_bytes(url: str, limit: int = MAX_METADATA) -> bytes:
    if not isinstance(url, str) or not url.startswith('https://'):
        raise UpdateError('Update metadata must use HTTPS')
    req = urllib.request.Request(url, headers={
        'User-Agent': f'NOMIKO-Updater/{CURRENT_VERSION}',
        'Accept': 'application/vnd.github+json' if url.startswith('https://api.github.com/') else 'application/octet-stream',
        'Cache-Control': 'no-cache',
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.geturl().split(':', 1)[0] != 'https':
                raise UpdateError('Insecure redirect blocked')
            raw = resp.read(limit + 1)
    except (OSError, ValueError) as exc:
        raise UpdateError(f'Network error: {exc}') from exc
    if len(raw) > limit:
        raise UpdateError('Update metadata too large')
    return raw


def verify_manifest(raw: bytes, signature_b64: bytes, *, expected_tag: str) -> Release:
    if len(raw) > MAX_METADATA or not TAG_PATTERN.fullmatch(expected_tag):
        raise UpdateError('Invalid update manifest')
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_ED25519_KEY_B64, validate=True))
        sig = base64.b64decode(signature_b64.strip(), validate=True)
        pub.verify(sig, raw)
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise UpdateError('Update signature is invalid — refusing installation') from exc
    try:
        info = json.loads(raw)
        if not isinstance(info, dict) or info.get('schema') != 1:
            raise ValueError('Unsupported manifest schema')
        tag, version, channel, asset = (info[x] for x in ('tag', 'version', 'channel', 'asset'))
        sha, size = info['sha256'], info['size']
        notes = info.get('notes', '')
        parse_version(version)
        if not TAG_PATTERN.fullmatch(tag) or tag != expected_tag:
            raise ValueError('Manifest tag mismatch')
        if channel not in ('alpha', 'stable'):
            raise ValueError('Invalid channel')
        if not INSTALLER_PATTERN.fullmatch(asset) or not asset.startswith(f'NOMIKO-Setup-{version}'):
            raise ValueError('Invalid installer name')
        if (not isinstance(sha, str) or re.fullmatch('[a-f0-9]{64}', sha) is None
                or type(size) is not int or not (0 < size <= MAX_INSTALLER)):
            raise ValueError('Invalid installer checksum/size')
        if not isinstance(notes, str) or len(notes) > 4000:
            raise ValueError('Invalid release notes')
        return Release(version, channel, tag, asset, size, sha, notes)
    except (KeyError, TypeError, ValueError) as exc:
        raise UpdateError(f'Invalid signed update metadata: {exc}') from exc


def find_update(channel: str = 'alpha', *, local_version: str = CURRENT_VERSION) -> Release | None:
    if channel not in ('alpha', 'stable'):
        raise UpdateError('Unknown update channel')
    releases = json.loads(fetch_bytes(API_URL, limit=512 * 1024))
    if not isinstance(releases, list):
        raise UpdateError('Unexpected release catalog')
    candidates = []
    for item in releases:
        if not isinstance(item, dict) or item.get('draft'):
            continue
        if channel == 'stable' and item.get('prerelease'):
            continue
        tag = item.get('tag_name')
        if not isinstance(tag, str) or not TAG_PATTERN.fullmatch(tag):
            continue
        try:
            version = tag.removeprefix('v').split('-', 1)[0]
            if parse_version(version) <= parse_version(local_version):
                continue
        except UpdateError:
            continue
        available = {x.get('name') for x in item.get('assets', []) if isinstance(x, dict)}
        if 'update.json' not in available or 'update.sig' not in available:
            continue
        candidates.append((parse_version(version), tag))

    # Never trust API version alone — release manifest is independently signed.
    for _, tag in sorted(candidates, reverse=True):
        raw = fetch_bytes(f'{RELEASE_ROOT}/{tag}/update.json')
        sig = fetch_bytes(f'{RELEASE_ROOT}/{tag}/update.sig', 2048)
        release = verify_manifest(raw, sig, expected_tag=tag)
        if (parse_version(release.version) > parse_version(local_version)
                and (channel == 'alpha' or release.channel == 'stable')):
            return release
    return None


def update_cache_dir() -> Path:
    root = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    return Path(root) / 'NOMIKO' / 'updates'


def verify_file(path: Path, release: Release) -> bool:
    if not path.is_file() or path.stat().st_size != release.size:
        return False
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest() == release.sha256


def download_installer(release: Release, progress=None) -> Path:
    folder = update_cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / release.asset
    if verify_file(target, release):
        if progress:
            progress(100)
        return target
    part = folder / f'{release.asset}.part'
    req = urllib.request.Request(release.download_url, headers={'User-Agent':f'NOMIKO-Updater/{CURRENT_VERSION}'})
    digest = hashlib.sha256()
    received = 0
    try:
        with urllib.request.urlopen(req, timeout=30) as r, part.open('wb') as file:
            if r.geturl().split(':', 1)[0] != 'https':
                raise UpdateError('Insecure installer download redirected')
            while True:
                block = r.read(256 * 1024)
                if not block:
                    break
                received += len(block)
                if received > release.size or received > MAX_INSTALLER:
                    raise UpdateError('Downloaded installer exceeds signed size')
                digest.update(block)
                file.write(block)
                if progress:
                    progress(min(99, int(received * 100 / release.size)))
        if received != release.size or digest.hexdigest() != release.sha256:
            raise UpdateError('Installer checksum/size mismatch — download rejected')
        os.replace(part, target)
        if progress:
            progress(100)
        return target
    except (OSError, ValueError) as exc:
        raise UpdateError(f'Download failed: {exc}') from exc
    finally:
        part.unlink(missing_ok=True)
