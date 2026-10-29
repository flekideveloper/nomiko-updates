"""Local-first productivity and portable data tools, independent from Qt."""
from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
import json
import os
import re
import shutil
import tempfile
import zipfile


MAX_IMPORT_BYTES = 8 * 1024 * 1024
MAX_BACKUP_BYTES = 40 * 1024 * 1024
SAFE_FILES = ('bookmarks.json', 'history.json', 'settings.json', 'widgets.json', 'session.json', 'workspaces.json', 'downloads.json')


def safe_web_url(value: str) -> bool:
    if not isinstance(value, str) or len(value) > 4096 or any(ord(c) < 32 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ('https', 'http') and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


class BookmarksHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.href = ''
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            link = dict(attrs).get('href', '')
            self.href = link if safe_web_url(link) else ''
            self.text_parts = []

    def handle_data(self, data):
        if self.href:
            self.text_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == 'a':
            if self.href and len(self.rows) < 15000:
                name = ''.join(self.text_parts).strip()[:200]
                self.rows.append({'title': name or self.href, 'url': self.href, 'folder': 'imported'})
            self.href = ''
            self.text_parts = []


def parse_bookmarks_html(source: str) -> list[dict]:
    if len(source.encode('utf-8')) > MAX_IMPORT_BYTES:
        raise ValueError('The bookmark HTML file is too large.')
    parser = BookmarksHTMLParser()
    parser.feed(source)
    return parser.rows


def bookmarks_to_html(rows: list[dict]) -> str:
    lines = ['<!DOCTYPE NETSCAPE-Bookmark-file-1>', '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">', '<TITLE>NOMIKO Bookmarks</TITLE>', '<H1>NOMIKO Bookmarks</H1>', '<DL><p>']
    for item in rows:
        url = item.get('url', '')
        if safe_web_url(url):
            lines.append(f'    <DT><A HREF="{escape(url, quote=True)}">{escape(str(item.get("title") or url))}</A>')
    return '\n'.join(lines + ['</DL><p>'])


def export_backup(directory: Path, destination: Path) -> int:
    """Portable non-secret JSON backup. Never bundle cache, cookies, passwords or raw profiles."""
    count = 0
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for basename in SAFE_FILES:
            path = directory / basename
            if path.is_file() and path.stat().st_size <= MAX_BACKUP_BYTES:
                try:
                    # Ensure corrupted JSON does not make the export fail mysteriously.
                    json.loads(path.read_text(encoding='utf-8'))
                    archive.write(path, arcname=basename)
                    count += 1
                except (UnicodeError, ValueError, OSError):
                    pass
    return count


def validate_backup(source: Path) -> dict[str, bytes]:
    """Read only allowlisted small JSON members; no ZIP extraction or traversal."""
    result = {}
    with zipfile.ZipFile(source) as archive:
        if len(archive.infolist()) > 20:
            raise ValueError('Backup contains too many files')
        for info in archive.infolist():
            if info.filename not in SAFE_FILES or info.is_dir() or info.file_size > MAX_BACKUP_BYTES:
                raise ValueError('Backup has an unsupported entry')
            if info.filename in result:
                raise ValueError('Backup has duplicate entries')
            data = archive.read(info)
            if len(data) > MAX_BACKUP_BYTES:
                raise ValueError('Backup is too large')
            parsed = json.loads(data.decode('utf-8'))
            if not isinstance(parsed, (dict, list)):
                raise ValueError('Backup has invalid data')
            result[info.filename] = data
    if not result:
        raise ValueError('No portable data found')
    return result


def import_backup(source: Path, target: Path) -> int:
    records = validate_backup(source)
    target.mkdir(parents=True, exist_ok=True)
    # Save each existing file to a dated snapshot before overwriting.
    snapshot = target / ('backup-before-restore-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    snapshot.mkdir(exist_ok=True)
    for name in records:
        if (target / name).is_file():
            shutil.copy2(target / name, snapshot / name)
    for name, data in records.items():
        with tempfile.NamedTemporaryFile(dir=target, suffix='.tmp', delete=False) as temp:
            temp.write(data)
            path = Path(temp.name)
        os.replace(path, target / name)
    return len(records)


def normalized_workspaces(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {}
    result = {}
    for name, urls in list(raw.items())[:30]:
        if isinstance(name, str) and 0 < len(name.strip()) <= 45 and isinstance(urls, list):
            result[name] = [url for url in urls[:40] if safe_web_url(url)]
    return result


class ArticleExtractor(HTMLParser):
    """Simple offline reader fallback (not a full Readability implementation)."""
    IGNORE = {'script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'svg', 'form'}
    BLOCKS = {'p', 'h1', 'h2', 'h3', 'h4', 'li', 'blockquote'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.current = None
        self.parts = []
        self.blocks = []
        self.in_title = False
        self.title = ''

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.IGNORE:
            self.skip_depth += 1
        if tag == 'title':
            self.in_title = True
        if self.skip_depth == 0 and tag in self.BLOCKS and self.current is None:
            self.current = tag
            self.parts = []

    def handle_data(self, data):
        if self.skip_depth:
            return
        if self.in_title:
            self.title += data
        if self.current:
            self.parts.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == 'title':
            self.in_title = False
        if tag in self.IGNORE:
            self.skip_depth = max(0, self.skip_depth - 1)
        if tag == self.current:
            paragraph = re.sub(r'\s+', ' ', ' '.join(self.parts)).strip()
            if len(paragraph) > 12 and len(self.blocks) < 250:
                self.blocks.append((tag, paragraph[:6000]))
            self.current = None
            self.parts = []


def render_reader(html: str, original_url: str, accent: str = '#9A82FF') -> str:
    if not isinstance(accent, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
        accent = '#9A82FF'
    parser = ArticleExtractor()
    parser.feed(html[:3_000_000])
    safe_title = escape(parser.title.strip()[:160] or 'Reader')
    content = ''.join(f'<{tag}>{escape(t)}</{tag}>' for tag, t in parser.blocks)
    if not content:
        content = '<p>No readable article text was found on this page.</p>'
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{safe_title} — NOMIKO Reader</title><style>
body{{background:#22242b;color:#eeeeef;font:19px/1.75 Georgia,serif;max-width:780px;margin:52px auto;padding:0 25px}}
h1,h2,h3,h4{{font-family:Segoe UI,Arial,sans-serif;line-height:1.3;color:{escape(accent,quote=True)}}}
small{{font:12px Segoe UI;color:#a5a9b6}} blockquote{{border-left:3px solid {escape(accent,quote=True)};padding-left:18px}}
</style></head><body><small>NOMIKO READER · {escape(original_url)}</small><h1>{safe_title}</h1>{content}</body></html>'''
