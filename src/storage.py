"""Small, local-only settings/bookmarks/history store."""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlsplit

from .productivity import normalized_workspaces
from .widgets import WIDGETS, DEFAULT_WIDGETS, normalize_widgets

APP_DIR = Path(os.environ.get('APPDATA', Path.home() / '.config')) / 'NOMIKO'
SETTINGS_FILE = APP_DIR / 'settings.json'
BOOKMARKS_FILE = APP_DIR / 'bookmarks.json'
HISTORY_FILE = APP_DIR / 'history.json'
SESSION_FILE = APP_DIR / 'session.json'
WALLPAPER_PREFIX = 'wallpaper.'
WIDGET_DATA_FILE = APP_DIR / 'widgets.json'
DOWNLOADS_FILE = APP_DIR / 'downloads.json'
WORKSPACES_FILE = APP_DIR / 'workspaces.json'

TOOLBAR_ITEMS = ['brand', 'back', 'forward', 'reload', 'home', 'address', 'download', 'bookmark', 'private', 'menu']
HOME_ITEMS = ['logo', 'kicker', 'title', 'subtitle', 'search', 'bookmarks']
MENU_ITEMS = ['new_tab', 'private_window', 'bookmarks', 'history', 'downloads', 'settings', 'modules', 'clear_data', 'about']

DEFAULT_SETTINGS = {
    'theme': 'dark',  # Graphite grey default. 'midnight' is darker.
    'accent': '#9A82FF',
    'search_engine': 'DuckDuckGo',
    'tracker_blocking': True,
    'ad_blocking': True,
    'block_popups': True,
    'autoplay_guard': True,
    'clean_tracking_links': True,
    'block_exceptions': [],
    'performance_mode': 'balanced',
    'pause_background_media': False,
    'cache_limit_mb': 128,
    'homepage': '',
    'language': 'en',
    'visible_engines': ['DuckDuckGo', 'NOMIKO Search', 'Google'],
    'downloads_dir': str(Path.home() / 'Downloads'),
    'tab_position': 'top',
    'tab_style': 'icon-and-title',
    'sidebar_style': 'expanded',
    'restore_tabs': False,
    'save_history': True,
    'bookmark_position': 'top',
    'bookmark_bar_visible': True,
    'sidebar_width': 196,
    'toolbar_order': TOOLBAR_ITEMS.copy(),
    'toolbar_hidden': [],
    'toolbar_colors': {},
    'menu_order': MENU_ITEMS.copy(),
    'menu_hidden': [],
    'menu_colors': {},
    'home_order': HOME_ITEMS.copy(),
    'home_hidden': [],
    'home_colors': {},
    'widget_order': list(WIDGETS),
    'widget_enabled': DEFAULT_WIDGETS.copy(),
    'widget_density': 'comfortable',
    'widget_columns': 'auto',
    'account_nickname': '',
    'account_email': '',
    'bookmark_sidebar_width': 154,
    'privacy_webrtc_public_only': True,
    'privacy_dns_prefetch': False,
    'privacy_persistent_cookies': True,
    'privacy_referrer_policy': 'normal',
    'interface_transparency': {'toolbar': 0, 'tabs': 0, 'bookmarks': 0, 'settings': 0},
    'account_avatar': '',
    'reader_font_size': 19,
    'warn_insecure_websites': True,
    'warn_suspicious_domains': True,
    'pinned_tabs': [],
    'theme_font_size': 12,
}
SEARCH_ENGINES = {
    'DuckDuckGo': 'https://duckduckgo.com/?q={query}',
    'Google': 'https://www.google.com/search?q={query}',
}


def readable_accent(hex_color: str, theme: str) -> str:
    """Adjust the user accent enough to stay legible on light/dark surfaces."""
    color = str(hex_color).lstrip('#')
    if len(color) != 6 or any(c not in '0123456789abcdefABCDEF' for c in color):
        color = '9A82FF'
    channels = [int(color[i:i + 2], 16) for i in (0, 2, 4)]
    light = theme == 'light'
    # Blend toward black/white when necessary, preserving the accent hue.
    def luminance(vals):
        lin = []
        for v in vals:
            c = v / 255
            lin.append(c / 12.92 if c <= 0.04045 else ((c + .055) / 1.055) ** 2.4)
        return .2126 * lin[0] + .7152 * lin[1] + .0722 * lin[2]
    background = .95 if light else .01
    for _ in range(11):
        x = luminance(channels)
        ratio = (max(x, background) + .05) / (min(x, background) + .05)
        if ratio >= 4.5:
            break
        channels = [round(v * .85) if light else round(v + (255 - v) * .2) for v in channels]
    return '#' + ''.join(f'{max(0, min(255, c)):02X}' for c in channels)



def _load(path: Path, default):
    try:
        with path.open('r', encoding='utf-8') as f:
            result = json.load(f)
        if isinstance(result, type(default)):
            return result
    except (OSError, ValueError):
        pass
    return default.copy()


def _save(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class Store:
    def __init__(self):
        self.settings = {**DEFAULT_SETTINGS, **_load(SETTINGS_FILE, {})}
        # Preserve the user's explicit search choice. Do not silently migrate
        # DuckDuckGo to NOMIKO Search (older alpha did that by mistake).
        if self.settings.get('search_engine') not in ('DuckDuckGo', 'NOMIKO Search', 'Google'):
            self.settings['search_engine'] = 'DuckDuckGo'
            self.save_settings()
        # v0.2 changed DuckDuckGo to NOMIKO Search without permission.
        # Undo that one-time migration on upgrade; users may select NOMIKO
        # again explicitly afterwards.
        if self.settings.get('v02_search_migrated') and not self.settings.get('v03_search_migrated'):
            if self.settings.get('search_engine') == 'NOMIKO Search':
                self.settings['search_engine'] = 'DuckDuckGo'
            self.settings['v03_search_migrated'] = True
            self.save_settings()
        available = ('DuckDuckGo', 'NOMIKO Search', 'Google')
        shown = self.settings.get('visible_engines')
        if not isinstance(shown, list):
            shown = list(available)
        shown = [e for e in available if e in shown]
        if not shown:
            shown = ['DuckDuckGo']
        self.settings['visible_engines'] = shown
        if self.settings['search_engine'] not in shown:
            self.settings['search_engine'] = shown[0]
        if self.settings.get('tab_position') not in ('top', 'bottom', 'left', 'right'):
            self.settings['tab_position'] = 'top'
        if self.settings.get('tab_style') not in ('icon', 'title', 'icon-and-title'):
            self.settings['tab_style'] = 'icon-and-title'
        if self.settings.get('sidebar_style') not in ('icon', 'expanded'):
            self.settings['sidebar_style'] = 'expanded'
        self.settings['save_history'] = self.settings.get('save_history', True) is True
        for key in ('tracker_blocking', 'ad_blocking', 'block_popups', 'autoplay_guard', 'clean_tracking_links'):
            self.settings[key] = self.settings.get(key, DEFAULT_SETTINGS[key]) is True
        if self.settings.get('performance_mode') not in ('off', 'balanced', 'gaming', 'ultra'):
            self.settings['performance_mode'] = 'balanced'
        exceptions = self.settings.get('block_exceptions', [])
        if not isinstance(exceptions, list): exceptions = []
        self.settings['block_exceptions'] = [str(x).lower().strip() for x in exceptions[:30]
                                             if isinstance(x, str) and x.strip() and len(x) < 256]

        if self.settings.get('bookmark_position') not in ('top', 'bottom', 'left', 'right'):
            self.settings['bookmark_position'] = 'top'
        self.settings['bookmark_bar_visible'] = self.settings.get('bookmark_bar_visible', True) is True
        try:
            side_width = int(self.settings.get('sidebar_width', 196))
        except (ValueError, TypeError):
            side_width = 196
        self.settings['sidebar_width'] = min(340, max(58, side_width))
        for key, allowed in (('toolbar_order', TOOLBAR_ITEMS), ('home_order', HOME_ITEMS), ('menu_order', MENU_ITEMS)):
            order = self.settings.get(key, [])
            if not isinstance(order, list): order = []
            listed = list(dict.fromkeys(x for x in order if x in allowed))
            self.settings[key] = listed + [x for x in allowed if x not in listed]
        for key, allowed in (('toolbar_hidden', TOOLBAR_ITEMS), ('home_hidden', HOME_ITEMS), ('menu_hidden', MENU_ITEMS)):
            values = self.settings.get(key, [])
            self.settings[key] = [x for x in values if x in allowed] if isinstance(values, list) else []
        if not isinstance(self.settings.get('menu_colors'), dict):
            self.settings['menu_colors'] = {}
        if not isinstance(self.settings.get('home_colors'), dict):
            self.settings['home_colors'] = {}
        if not isinstance(self.settings.get('toolbar_colors'), dict):
            self.settings['toolbar_colors'] = {}
        self.settings['widget_order'], self.settings['widget_enabled'] = normalize_widgets(
            self.settings.get('widget_order'), self.settings.get('widget_enabled'))
        if self.settings.get('widget_density') not in ('comfortable', 'compact'):
            self.settings['widget_density'] = 'comfortable'
        if self.settings.get('widget_columns') not in ('auto', '2', '3'):
            self.settings['widget_columns'] = 'auto'
        self.settings['pause_background_media'] = self.settings.get('pause_background_media', False) is True
        try: self.settings['cache_limit_mb'] = min(512, max(32, int(self.settings.get('cache_limit_mb', 128))))
        except (ValueError, TypeError): self.settings['cache_limit_mb'] = 128
        self.widget_data = _load(WIDGET_DATA_FILE, {})
        if not isinstance(self.widget_data.get('tasks'), list): self.widget_data['tasks'] = []
        self.bookmarks = _load(BOOKMARKS_FILE, [])
        self.history = _load(HISTORY_FILE, [])
        self.settings['restore_tabs'] = self.settings.get('restore_tabs') is True
        self.settings['privacy_webrtc_public_only'] = self.settings.get('privacy_webrtc_public_only', True) is True
        self.settings['privacy_dns_prefetch'] = self.settings.get('privacy_dns_prefetch', False) is True
        self.settings['privacy_persistent_cookies'] = self.settings.get('privacy_persistent_cookies', True) is True
        if self.settings.get('privacy_referrer_policy') not in ('normal', 'no-referrer'):
            self.settings['privacy_referrer_policy'] = 'normal'
        try:
            self.settings['bookmark_sidebar_width'] = min(360, max(72, int(self.settings.get('bookmark_sidebar_width', 154))))
        except (ValueError, TypeError):
            self.settings['bookmark_sidebar_width'] = 154
        choices = self.settings.get('interface_transparency', {})
        if not isinstance(choices, dict): choices = {}
        self.settings['interface_transparency'] = {}
        for key in ('toolbar', 'tabs', 'bookmarks', 'settings'):
            try: level = int(choices.get(key, 0))
            except (ValueError, TypeError): level = 0
            self.settings['interface_transparency'][key] = min(65, max(0, level))
        self.workspaces = normalized_workspaces(_load(WORKSPACES_FILE, {}))
        self.download_history = _load(DOWNLOADS_FILE, [])
        if not isinstance(self.download_history, list): self.download_history = []
        self.download_history = [x for x in self.download_history[-700:] if isinstance(x, dict)]
        # A download marked active after a restart was interrupted.
        for record in self.download_history:
            if record.get('status') == 'Downloading':
                record['status'] = 'Interrupted'


    def save_workspaces(self):
        _save(WORKSPACES_FILE, normalized_workspaces(self.workspaces))

    def record_download(self, path: str, source: str = '') -> str:
        """Persist safe download metadata only, never the downloaded contents."""
        from uuid import uuid4
        identifier = uuid4().hex
        record = {'id': identifier, 'path': str(path), 'url': str(source)[:2048],
                  'time': datetime.now(timezone.utc).isoformat(), 'status': 'Downloading'}
        self.download_history.append(record)
        self.download_history = self.download_history[-700:]
        _save(DOWNLOADS_FILE, self.download_history)
        return identifier

    def finish_download(self, identifier: str, status: str):
        for record in self.download_history:
            if record.get('id') == identifier:
                record['status'] = str(status)[:80]
                _save(DOWNLOADS_FILE, self.download_history)
                break

    def remove_downloads(self, identifiers):
        selected = set(identifiers)
        self.download_history = [r for r in self.download_history if r.get('id') not in selected]
        _save(DOWNLOADS_FILE, self.download_history)

    def clear_downloads(self):
        self.download_history = []
        _save(DOWNLOADS_FILE, self.download_history)

    def save_widget_data(self):
        # Notes and tasks never leave the local Windows profile.
        _save(WIDGET_DATA_FILE, self.widget_data)

    def apply_widget_action(self, action: str, values: dict, persist: bool = True) -> bool:
        if action == 'note':
            self.widget_data['note'] = str(values.get('text', ''))[:4000]
        elif action == 'task-add':
            task = str(values.get('text', '')).strip()[:120]
            if not task: return False
            self.widget_data['tasks'] = self.widget_data.get('tasks', [])[:39] + [task]
        elif action == 'task-remove':
            try: index = int(values.get('idx', -1))
            except (ValueError, TypeError): return False
            tasks = self.widget_data.get('tasks', [])
            if not (0 <= index < len(tasks)): return False
            del tasks[index]
        elif action == 'weather':
            self.widget_data['weather_city'] = str(values.get('city', '')).strip()[:80]
        else:
            return False
        if persist: self.save_widget_data()
        return True

    def save_settings(self):
        _save(SETTINGS_FILE, self.settings)

    def read_session(self):
        """Return only safe, normal-window tabs from the last session."""
        raw = _load(SESSION_FILE, {})
        if not isinstance(raw, dict):
            return {'tabs': [], 'active': 0}
        tabs = [item for item in (normalize_session_tab(x) for x in raw.get('tabs', [])[:60])
                if item is not None] if isinstance(raw.get('tabs'), list) else []
        active = raw.get('active', 0)
        if not isinstance(active, int):
            active = 0
        return {'tabs': tabs, 'active': min(max(0, active), max(0, len(tabs) - 1))}

    def save_session(self, tabs, active=0):
        """Atomically save the ordinary tab addresses; never use for private windows."""
        safe = [item for item in (normalize_session_tab(t) for t in tabs[:60]) if item is not None]
        index = active if isinstance(active, int) else 0
        _save(SESSION_FILE, {'tabs': safe, 'active': min(max(0, index), max(0, len(safe) - 1))})

    def clear_session(self):
        self.save_session([], 0)

    def save_bookmarks(self):
        _save(BOOKMARKS_FILE, self.bookmarks)

    def add_history(self, url, title):
        if not self.settings.get('save_history', True):
            return
        if not url.startswith(('https://', 'http://')):
            return
        self.history.append({'url': url, 'title': title or url, 'time': datetime.now(timezone.utc).isoformat()})
        self.history = self.history[-1000:]
        _save(HISTORY_FILE, self.history)

    def clear_history(self):
        self.history = []
        _save(HISTORY_FILE, self.history)

    def remove_history_indexes(self, indexes):
        self.history = [row for i, row in enumerate(self.history) if i not in set(indexes)]
        _save(HISTORY_FILE, self.history)

    def add_bookmark(self, url, title, folder='toolbar'):
        if not str(url).startswith(('https://','http://')): return False
        for item in self.bookmarks:
            if item.get('url') == url: return False
        self.bookmarks.append({'url': url, 'title': title or url, 'folder': folder})
        self.save_bookmarks()
        return True

    def update_bookmark(self, index, title, url, folder):
        if not 0 <= index < len(self.bookmarks) or not str(url).startswith(('https://','http://')):
            return False
        self.bookmarks[index] = {'url': url, 'title': title or url, 'folder': folder}
        self.save_bookmarks()
        return True

    def delete_bookmark(self, index):
        if not 0 <= index < len(self.bookmarks): return False
        del self.bookmarks[index]
        self.save_bookmarks()
        return True

    def save_wallpaper(self, source):
        """Keep wallpaper on-device; reject files over 10 MiB. The UI validates image content."""
        source = Path(source)
        if not source.is_file() or source.stat().st_size > 10 * 1024 * 1024:
            return False
        if source.suffix.lower() not in ('.gif','.png','.jpg','.jpeg','.webp'):
            return False
        APP_DIR.mkdir(parents=True, exist_ok=True)
        dest = APP_DIR / ('wallpaper' + source.suffix.lower())
        try:
            tmp = dest.with_suffix(dest.suffix + '.tmp')
            shutil.copyfile(source, tmp)
            os.replace(tmp, dest)
            self.remove_wallpaper(except_path=dest)
            return True
        except OSError:
            return False

    def remove_wallpaper(self, except_path=None):
        for path in APP_DIR.glob('wallpaper.*'):
            if path != except_path and path.is_file():
                try: path.unlink()
                except OSError: pass

    def wallpaper(self):
        for ext in ('.gif','.png','.jpg','.jpeg','.webp'):
            path = APP_DIR / ('wallpaper' + ext)
            if path.is_file() and path.stat().st_size <= 10 * 1024 * 1024:
                return path
        return None

    def toggle_bookmark(self, url, title):
        if not url.startswith(('https://', 'http://')):
            return False
        exists = any(x.get('url') == url for x in self.bookmarks)
        if exists:
            self.bookmarks = [x for x in self.bookmarks if x.get('url') != url]
        else:
            self.bookmarks.append({'url': url, 'title': title or url, 'folder': 'toolbar'})
        _save(BOOKMARKS_FILE, self.bookmarks)
        return not exists


def resolve_input(text: str, engine: str = 'DuckDuckGo') -> str:
    """Take a URL, localhost, or phrase to a real navigable URL."""
    text = text.strip()
    if not text:
        return ''
    parts = urlsplit(text)
    if parts.scheme in ('http', 'https') and parts.netloc:
        return text
    if not any(c.isspace() for c in text) and not text.startswith(('javascript:', 'data:', 'file:', 'chrome:', 'about:')):
        host = text.split('/', 1)[0]
        if '.' in host or host.startswith('localhost') or host.startswith('127.0.0.1'):
            return 'https://' + text if not host.startswith(('localhost', '127.0.0.1')) else 'http://' + text
    template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES['DuckDuckGo'])
    return template.format(query=quote_plus(text))


def is_navigation_input(text: str) -> bool:
    """Recognize web URLs without interpreting normal search phrases as URLs."""
    text = text.strip()
    if not text or any(ch.isspace() for ch in text):
        return False
    parts = urlsplit(text)
    if parts.scheme in ('http', 'https') and bool(parts.netloc):
        return True
    if ':' in text and not text.startswith(('localhost:', '127.0.0.1:')):
        return False
    if text.startswith(('javascript:', 'data:', 'file:', 'chrome:', 'about:')):
        return False
    host = text.split('/', 1)[0].split(':', 1)[0]
    return '.' in host or host in ('localhost', '127.0.0.1')


def normalize_session_tab(tab):
    """Restore only ordinary HTTPS/HTTP pages and NOMIKO's own internal tabs.

    Do not restore arbitrary schemes (file:, javascript:, data:, custom protocols)
    or store embedded credentials in a URL. Each record contains only minimal
    information needed to reconstruct a tab, never cookies or form fields.
    """
    if not isinstance(tab, dict):
        return None
    kind = tab.get('kind')
    if kind in ('home', 'settings'):
        return {'kind': kind}
    if kind == 'search':
        query = tab.get('query', '')
        if isinstance(query, str) and query.strip():
            return {'kind': kind, 'query': query.strip()[:250]}
        return None
    if kind == 'web':
        url = tab.get('url')
        if not isinstance(url, str) or len(url) > 2048:
            return None
        try:
            parts = urlsplit(url)
            if (parts.scheme in ('http', 'https') and parts.hostname
                    and not (parts.username or parts.password)
                    and parts.hostname.lower() != 'nomiko.invalid'):
                record = {'kind': kind, 'url': url}
                if tab.get('pinned') is True: record['pinned'] = True
                group = tab.get('group')
                if isinstance(group,str) and group in ('Work','Study','Games','Personal'):
                    record['group'] = group
                return record
        except ValueError:
            pass
    return None
