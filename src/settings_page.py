"""NOMIKO settings. Every change is persisted immediately; sections stay in place."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QSize
from PySide6.QtGui import QColor, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QScrollArea, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

from .i18n import LANGUAGES
from .storage import APP_DIR, HOME_ITEMS, TOOLBAR_ITEMS, MENU_ITEMS
from .widgets import WIDGETS


class SettingsPane(QWidget):
    CATEGORIES = ['General', 'Updates', 'Appearance', 'Home', 'Toolbar', 'Menu', 'Tabs', 'Bookmarks',
                  'Search', 'Downloads', 'Privacy', 'Modules', 'Performance', 'Widgets', 'Account', 'Workspaces', 'Data & backup', 'Support', 'About']

    def __init__(self, browser, parent=None):
        super().__init__(parent)
        self.browser = browser
        self._rebuild = False
        self.root = QHBoxLayout(self)
        self.root.setContentsMargins(12, 10, 10, 10)
        self.root.setSpacing(8)
        self.pages = QStackedWidget(self)
        self.pages.setObjectName('settingsPages')
        self.root.addWidget(self.pages, 1)

        # Compact Firefox-inspired section rail, always on the RIGHT.
        # 16 sections fit much more comfortably without a giant button per row.
        self.rail = QWidget(self)
        self.rail.setObjectName('settingsRail')
        self.rail.setFixedWidth(168)
        rail_layout = QVBoxLayout(self.rail)
        rail_layout.setContentsMargins(7, 10, 5, 6)
        rail_layout.setSpacing(5)
        rail_title = QLabel('NOMIKO  /  SETTINGS', self.rail)
        rail_title.setObjectName('railTitle')
        rail_title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        rail_layout.addWidget(rail_title)
        self.category_filter = QLineEdit(self.rail)
        self.category_filter.setObjectName('settingsFilter')
        self.category_filter.setPlaceholderText('Find a section…')
        self.category_filter.setClearButtonEnabled(True)
        self.category_filter.setFixedHeight(29)
        self.category_filter.setToolTip('Filter settings sections by name')
        rail_layout.addWidget(self.category_filter)
        self.category_list = QListWidget(self.rail)
        self.category_list.setObjectName('settingsSidebar')
        self.category_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.category_list.setUniformItemSizes(True)
        self.category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.category_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        rail_layout.addWidget(self.category_list, 1)
        self.root.addWidget(self.rail, 0)
        self.category_filter.textChanged.connect(self.filter_categories)
        self.category_list.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.rebuild()

    def filter_categories(self, query):
        """Filter sections without rebuilding pages or losing settings edits."""
        needle = query.casefold().strip()
        selected = self.category_list.currentRow()
        first_visible = -1
        for i in range(self.category_list.count()):
            item = self.category_list.item(i)
            # Match both localized and English names (e.g. 'Privacy').
            visible = not needle or needle in item.text().casefold() or needle in self.CATEGORIES[i].casefold()
            item.setHidden(not visible)
            if visible and first_visible < 0:
                first_visible = i
        if first_visible >= 0 and (selected < 0 or self.category_list.item(selected).isHidden()):
            self.category_list.setCurrentRow(first_visible)

    def t(self, key): return self.browser.t(key)

    def set_preference(self, **changes):
        self.browser.update_preference(**changes)

    def section(self, name):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget(scroll)
        content.setMaximumWidth(760)
        content.setMinimumWidth(0)
        box = QVBoxLayout(content)
        box.setContentsMargins(18, 14, 14, 24)
        box.setSpacing(8)
        box.setAlignment(Qt.AlignmentFlag.AlignTop)
        heading = QLabel(self.t(name))
        heading.setObjectName('sectionHeading')
        heading.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        box.addWidget(heading)
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        return box

    def row(self, box, text, widget, max_width=280):
        line = QWidget(self)
        line.setObjectName('settingRow')
        lay = QHBoxLayout(line)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(10)
        label = QLabel(self.t(text))
        label.setToolTip(self.t(text))
        label.setMinimumWidth(110)
        label.setMaximumWidth(190)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        lay.addWidget(label)
        widget.setMaximumWidth(max_width)
        lay.addWidget(widget, 0)
        lay.addStretch(1)
        line.setMaximumWidth(730)
        box.addWidget(line, alignment=Qt.AlignmentFlag.AlignLeft)
        return widget

    def note(self, box, message):
        label = QLabel(self.t(message))
        label.setWordWrap(True)
        label.setObjectName('settingsNote')
        label.setMaximumWidth(545)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        box.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
        return label

    def combo(self, options, current):
        w = QComboBox(self)
        w.setFixedWidth(200)
        for value, title in options:
            w.addItem(self.t(title), value)
        idx = w.findData(current)
        w.setCurrentIndex(max(0, idx))
        return w

    def button(self, title, click):
        w = QPushButton(self.t(title))
        w.setMaximumWidth(200)
        w.setMinimumHeight(28)
        w.setCursor(Qt.CursorShape.PointingHandCursor)
        w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        w.clicked.connect(click)
        return w

    def rebuild(self, preserve=True):
        selected = self.category_list.currentRow() if preserve else 0
        self._rebuild = True
        self.category_list.blockSignals(True)
        self.category_list.clear()
        while self.pages.count():
            old = self.pages.widget(0)
            self.pages.removeWidget(old)
            old.deleteLater()
        for cat in self.CATEGORIES:
            item = QListWidgetItem(self.t(cat))
            item.setSizeHint(QSize(135, 27))
            item.setToolTip(self.t(cat))
            self.category_list.addItem(item)
        s = self.browser.store.settings

        # GENERAL
        box = self.section('General')
        restore = QCheckBox(self.t('Restore previous tabs on startup'))
        restore.setChecked(s.get('restore_tabs', False))
        restore.toggled.connect(lambda v: self.set_preference(restore_tabs=v))
        box.addWidget(restore)
        self.note(box, 'Only ordinary tabs are restored. Private sessions never return.')
        self.note(box, 'Tip: Ctrl+T opens a new tab · Ctrl+L selects the address · Ctrl+Shift+M opens Protection · Ctrl+Shift+G toggles Gaming mode · Ctrl+M mutes a tab.')
        lang = self.combo(list(LANGUAGES.items()), s.get('language', 'en'))
        self.row(box, 'Language', lang)
        def change_lang(_):
            self.set_preference(language=lang.currentData())
            self.rebuild()
        lang.currentIndexChanged.connect(change_lang)
        self.note(box, 'Translations are incomplete. Untranslated phrases appear in English.')

        # UPDATES — locally stored preferences, verified GitHub releases.
        box = self.section('Updates')
        box.addWidget(self.button('Open Update Center', self.browser.show_update_center))
        enabled = QCheckBox('Check for new versions automatically at startup')
        enabled.setChecked(s.get('updates_auto_check', True))
        enabled.toggled.connect(lambda state: self.set_preference(updates_auto_check=state))
        box.addWidget(enabled)
        channel = self.combo([('alpha', 'Alpha and Stable'), ('stable', 'Stable only')], s.get('updates_channel', 'alpha'))
        channel.currentIndexChanged.connect(lambda _: self.set_preference(updates_channel=channel.currentData()))
        self.row(box, 'Release channel', channel)
        self.note(box, 'Checks contact GitHub and disclose your network IP to GitHub. No browsing history or bookmarks are sent.')
        self.note(box, 'Every installer must match the Ed25519-signed release manifest and SHA-256 checksum. Installation requires your confirmation.')

        # APPEARANCE
        box = self.section('Appearance')
        theme = self.combo([('dark','Graphite grey · Default'), ('midnight','Midnight black'), ('light','Light')], s.get('theme', 'dark'))
        theme.currentIndexChanged.connect(lambda _: self.set_preference(theme=theme.currentData()))
        self.row(box, 'Theme', theme)
        choose_accent = self.button('Change accent', lambda: self.pick_accent())
        reset_accent = self.button('Reset accent', lambda: self.set_preference(accent='#9A82FF'))
        accent_row = QWidget()
        ar = QHBoxLayout(accent_row)
        ar.setContentsMargins(0,0,0,0)
        choose_accent.setFixedWidth(132)
        reset_accent.setFixedWidth(125)
        ar.setSpacing(7)
        ar.addWidget(choose_accent)
        ar.addWidget(reset_accent)
        self.row(box, 'Accent', accent_row)
        box.addWidget(self.button('Open Theme Studio 2.0', self.browser.show_theme_studio))
        self.note(box, 'Changes are applied and saved immediately. No Save button needed.')
        self.note(box, 'Surface transparency blends panels toward the NOMIKO background. It does not make the Windows desktop visible.')
        for key, title in [('toolbar', 'Toolbar transparency'), ('tabs', 'Tabs transparency'),
                           ('bookmarks', 'Bookmarks transparency'), ('settings', 'Settings transparency')]:
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 65)
            slider.setFixedWidth(195)
            slider.setValue(s.get('interface_transparency', {}).get(key, 0))
            slider.setToolTip('0 = solid · 65 = most transparent-looking')
            slider.valueChanged.connect(lambda value, k=key: self.set_transparency(k, value))
            self.row(box, title, slider)

        # NEW TAB
        box = self.section('Home')
        self.note(box, 'Personalize the new tab. Images and animated GIFs are stored only on this computer (maximum 10 MB).')
        box.addWidget(self.button('Choose picture or GIF', self.pick_wallpaper))
        box.addWidget(self.button('Remove background picture', self.remove_wallpaper))
        self.wallpaper_preview = QLabel(self)
        self.wallpaper_preview.setObjectName('wallpaperPreview')
        self.wallpaper_preview.setFixedSize(292, 150)
        self.wallpaper_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.wallpaper_preview.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        box.addWidget(self.wallpaper_preview)
        self.update_wallpaper_preview()
        self.home_list = self._organizer(box, HOME_ITEMS, s.get('home_order', HOME_ITEMS),
                                         s.get('home_hidden', []), 'home')
        self.note(box, 'Drag to reorder; untick to hide. The search box can also be hidden.')
        box.addWidget(self.button('Set element color', self.pick_home_color))
        box.addWidget(self.button('Reset element color', self.reset_home_color))

        # TOOLBAR
        box = self.section('Toolbar')
        self.note(box, 'Drag items to rearrange; untick to hide. Windows controls stay accessible. Press Ctrl+, for Settings.')
        self.toolbar_list = self._organizer(box, TOOLBAR_ITEMS, s.get('toolbar_order', TOOLBAR_ITEMS),
                                            s.get('toolbar_hidden', []), 'toolbar')
        box.addWidget(self.button('Set selected button color', self.pick_toolbar_color))
        box.addWidget(self.button('Reset selected button color', self.reset_toolbar_color))

        # MAIN MENU
        box = self.section('Menu')
        self.note(box, 'Reorder, hide or recolor entries in the NOMIKO menu. Ctrl+, always opens settings even if that entry is hidden.')
        self.menu_list = self._organizer(box, MENU_ITEMS, s.get('menu_order', MENU_ITEMS),
                                         s.get('menu_hidden', []), 'menu')
        box.addWidget(self.button('Set selected menu item color', self.pick_menu_color))
        box.addWidget(self.button('Reset selected menu item color', self.reset_menu_color))

        # TABS
        box = self.section('Tabs')
        tab_box = box
        # BOOKMARKS
        bookmarks_box = self.section('Bookmarks')
        display = QCheckBox(self.t('Show bookmarks bar'))
        display.setChecked(s.get('bookmark_bar_visible', True))
        display.toggled.connect(lambda v: self.set_preference(bookmark_bar_visible=v))
        bookmarks_box.addWidget(display)
        placement = self.combo([('top','Top'),('bottom','Bottom'),('left','Left'),('right','Right')],
                               s.get('bookmark_position', 'top'))
        placement.currentIndexChanged.connect(lambda _: self.set_preference(bookmark_position=placement.currentData()))
        self.row(bookmarks_box, 'Bookmarks bar position', placement)
        bookmarks_box.addWidget(self.button('Manage bookmarks and folders', self.browser.show_bookmarks))
        self.note(bookmarks_box, 'Bookmarks assigned to the “toolbar” folder appear on the bookmarks bar.')

        # TABS OPTIONS
        position = self.combo([('top','Top'),('bottom','Bottom'),('left','Left'),('right','Right')],
                              s.get('tab_position','top'))
        position.currentIndexChanged.connect(lambda _: self.set_preference(tab_position=position.currentData()))
        self.row(tab_box, 'Tab position', position)
        labels = self.combo([('icon','Icon only'),('title','Title only'),('icon-and-title','Icon and title')],
                            s.get('tab_style','icon-and-title'))
        labels.currentIndexChanged.connect(lambda _: self.set_preference(tab_style=labels.currentData()))
        self.row(tab_box, 'Horizontal tab labels', labels)
        sidebar = self.combo([('expanded','Icon and title'),('icon','Icon only')],
                             s.get('sidebar_style', 'expanded'))
        sidebar.currentIndexChanged.connect(lambda _: self.set_preference(sidebar_style=sidebar.currentData()))
        self.row(tab_box, 'Side tab labels', sidebar)
        self.note(tab_box, 'When tabs are on the sides, drag the thin divider to resize the panel. Tabs can be dragged to reorder.')

        # SEARCH
        box = self.section('Search')
        allowed = s.get('visible_engines', ['DuckDuckGo','NOMIKO Search','Google'])
        checks = {}
        for engine in ('DuckDuckGo','NOMIKO Search','Google'):
            c = QCheckBox(engine)
            c.setChecked(engine in allowed)
            box.addWidget(c)
            checks[engine] = c
        current_engine = self.combo([(n,n) for n in allowed], s.get('search_engine','DuckDuckGo'))
        self.row(box, 'Default search engine', current_engine)
        def update_search(changed):
            visible = [n for n,v in checks.items() if v.isChecked()]
            if not visible:
                changed.blockSignals(True)
                changed.setChecked(True)
                changed.blockSignals(False)
                return
            old = current_engine.currentData()
            current_engine.blockSignals(True)
            current_engine.clear()
            for n in visible: current_engine.addItem(n,n)
            current_engine.setCurrentIndex(max(0,current_engine.findData(old)))
            current_engine.blockSignals(False)
            self.set_preference(visible_engines=visible, search_engine=current_engine.currentData())
        for cb in checks.values(): cb.toggled.connect(lambda _, c=cb: update_search(c))
        current_engine.currentIndexChanged.connect(lambda _: self.set_preference(search_engine=current_engine.currentData()))
        homepage = QLineEdit(s.get('homepage', ''))
        homepage.setPlaceholderText('Blank = NOMIKO new tab')
        homepage.editingFinished.connect(lambda: self.set_preference(homepage=homepage.text().strip()))
        self.row(box, 'Custom home URL', homepage)
        self.note(box, 'NOMIKO Search searches your local bookmarks/history, not the public web.')

        # DOWNLOADS
        box = self.section('Downloads')
        path = QLineEdit(s.get('downloads_dir',str(Path.home()/'Downloads')))
        path.setMinimumWidth(300)
        path.setToolTip(path.text())
        path.textChanged.connect(path.setToolTip)
        path.editingFinished.connect(lambda: self._download_path_changed(path))
        self.row(box, 'Download folder', path, max_width=530)
        def browse_folder():
            folder = QFileDialog.getExistingDirectory(self,'Download folder',path.text())
            if folder:
                path.setText(folder)
                self._download_path_changed(path)
        box.addWidget(self.button('Choose folder', browse_folder))
        box.addWidget(self.button('Show downloads & history', self.browser.show_downloads))
        self.note(box, 'The downloads list is stored locally across restarts. Clearing the list will not delete files.')

        # PRIVACY
        box = self.section('Privacy')
        blocker = QCheckBox(self.t('Block basic tracker/ad-host list'))
        blocker.setChecked(s.get('tracker_blocking',True))
        blocker.toggled.connect(lambda v: self.set_preference(tracker_blocking=v))
        box.addWidget(blocker)
        history = QCheckBox(self.t('Save browsing history on this device'))
        history.setChecked(s.get('save_history', True))
        history.toggled.connect(lambda v: self.set_preference(save_history=v))
        box.addWidget(history)
        box.addWidget(self.button('View / delete history', self.browser.show_history))
        box.addWidget(self.button('Clear browsing data', self.browser.clear_browsing_data))
        for key, title in [
            ('privacy_webrtc_public_only', 'Limit WebRTC to public network interfaces'),
            ('privacy_persistent_cookies', 'Keep persistent site cookies after closing'),
            ('privacy_dns_prefetch', 'Allow DNS prefetching')]:
            option = QCheckBox(self.t(title))
            option.setChecked(s.get(key, key != 'privacy_dns_prefetch'))
            option.toggled.connect(lambda on, k=key: self.set_preference(**{k:on}))
            box.addWidget(option)
        for key, title in [
            ('warn_insecure_websites', 'Warn when entering unencrypted HTTP websites'),
            ('warn_suspicious_domains', 'Warn about Punycode / internationalized domains'),
        ]:
            control = QCheckBox(title)
            control.setChecked(s.get(key, True))
            control.toggled.connect(lambda value, k=key: self.set_preference(**{k:value}))
            box.addWidget(control)
        self.note(box, 'These warnings are not a phishing-detection service. File warnings do not scan downloads for malware.')
        box.addWidget(self.button('Site permissions', self.browser.show_permissions_center))
        self.row(box, 'Referrer header', self._referrer_combo(s))
        self.note(box, 'Changing the cookie policy does not erase existing cookies. Disabling referrers can break some site navigation and sign-in flows.')
        self.note(box, 'Qt WebEngine still exposes your public IP address. These settings cannot guarantee anonymity, defeat all fingerprinting, or control DNS at the operating-system level.')
        self.note(box, 'Disabling history prevents NOMIKO from saving new entries; it does not remove old entries or all Chromium site data.')

        # BUILT-IN NATIVE MODULES (not Chrome/Firefox WebExtensions).
        box = self.section('Modules')
        self.note(box, 'Five built-in protection modules. No extension store, no NOMIKO server, no external downloads. They are not Chrome/Firefox extensions and cannot replace uBlock Origin.')
        options = (
            ('ad_blocking', 'Ad Block · block known advertising hosts', 'May leave empty ad spaces. Some sites require disabling it.'),
            ('tracker_blocking', 'Tracker Guard · stop known tracking hosts', 'Works on third-party network requests. It does not prevent all tracking or fingerprinting.'),
            ('clean_tracking_links', 'Link Cleaner · remove tracking parameters', 'Removes known URL parameters such as utm_source and fbclid from navigated links.'),
            ('block_popups', 'Popup Shield · block site-created windows', 'Blocks popups that sites attempt to open; some sign-in flows may need it disabled.'),
            ('autoplay_guard', 'Autoplay Guard · require user gesture', 'Asks sites to wait for a click before playing audio/video.'),
        )
        for key, title, explanation in options:
            option = QCheckBox(title)
            option.setChecked(s.get(key, True))
            option.toggled.connect(lambda value, k=key: self.set_preference(**{k:value}))
            box.addWidget(option)
            self.note(box, explanation)
        box.addWidget(self.button('Import domain blocklist (local)', self.browser.import_local_blocklist))
        box.addWidget(self.button('Remove custom blocklist', self.browser.remove_local_blocklist))
        self.note(box, 'Local list imports support hosts-style domains, not Chrome extensions, custom JavaScript or complex uBlock rules.')
        domain_field = QLineEdit(', '.join(s.get('block_exceptions', [])))
        domain_field.setPlaceholderText('example.com, another.example')
        domain_field.setMaximumWidth(430)
        def save_exceptions():
            from urllib.parse import urlsplit
            raw = [v.strip().lower() for v in domain_field.text().split(',')]
            safe = [host for host in raw if host and len(host)<256 and ' ' not in host
                    and '://' not in host and '/' not in host]
            self.set_preference(block_exceptions=safe[:30])
        domain_field.editingFinished.connect(save_exceptions)
        self.row(box, 'Allowlist (domains)', domain_field)
        self.note(box, 'Allowlisted websites are exempt from the ad/tracker network filters. A reload may be needed to see changes.')

        # RESOURCE SAVER
        box = self.section('Performance')
        perf = self.combo([('off', 'Off · never suspend tabs'),
                           ('balanced', 'Balanced · protect background tabs'),
                           ('gaming', 'Gaming · more aggressive saving'),
                           ('ultra', 'Ultra · strongest background saving')],
                          s.get('performance_mode', 'balanced'))
        perf.currentIndexChanged.connect(lambda _: self.set_preference(performance_mode=perf.currentData()))
        self.row(box, 'Background tab saving', perf)
        self.note(box, 'Balanced: freeze 2 min / discard 8 min. Gaming: 25 sec / 90 sec. Ultra: 10 sec / 35 sec. Qt decides whether it is safe to suspend a tab.')
        cache = self.combo([('64', '64 MB'), ('128', '128 MB'), ('256', '256 MB'), ('512', '512 MB')], str(s.get('cache_limit_mb', 128)))
        cache.currentIndexChanged.connect(lambda _: self.set_preference(cache_limit_mb=int(cache.currentData())))
        self.row(box, 'HTTP disk cache limit', cache)
        self.note(box, 'Cache limit reduces disk usage, not guaranteed RAM use. Audio/video tabs can remain active by design.')
        self.note(box, 'Discarded tabs reload when opened. Resource use never reaches zero, and no setting can guarantee Fortnite FPS.')

        # LOCAL HOME WIDGETS
        box = self.section('Widgets')
        self.note(box, 'Widgets are OFF by default. Tick only the tools you want on your new tab. Changes apply immediately.')
        self.note(box, 'Future community widget gallery: reserved for a future opt-in service. There is no upload or account integration today.')
        density = self.combo([('comfortable', 'Comfortable'), ('compact', 'Compact')],
                             s.get('widget_density', 'comfortable'))
        density.currentIndexChanged.connect(lambda _: self.set_preference(widget_density=density.currentData()))
        self.row(box, 'Widget spacing', density)
        columns = self.combo([('auto','Automatic'),('2','2 columns'),('3','3 columns')],
                             s.get('widget_columns', 'auto'))
        columns.currentIndexChanged.connect(lambda _: self.set_preference(widget_columns=columns.currentData()))
        self.row(box, 'Widget columns', columns)
        self.widget_list = QListWidget(self)
        self.widget_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.widget_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.widget_list.setFixedHeight(400)
        self.widget_list.setMinimumWidth(460)
        self.widget_list.setMaximumWidth(620)
        self.widget_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for key in s.get('widget_order', list(WIDGETS)):
            if key not in WIDGETS: continue
            item = QListWidgetItem(WIDGETS[key][0] + '  ·  ' + WIDGETS[key][1])
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled)
            item.setCheckState(Qt.CheckState.Checked if key in s.get('widget_enabled', []) else Qt.CheckState.Unchecked)
            self.widget_list.addItem(item)
        box.addWidget(self.widget_list, alignment=Qt.AlignmentFlag.AlignLeft)
        box.addWidget(self.button('Hide all widgets', self.hide_all_widgets))
        def save_widgets():
            items = [self.widget_list.item(i) for i in range(self.widget_list.count())]
            self.set_preference(widget_order=[item.data(Qt.ItemDataRole.UserRole) for item in items],
                                widget_enabled=[item.data(Qt.ItemDataRole.UserRole) for item in items
                                                if item.checkState() == Qt.CheckState.Checked])
        self.widget_list.itemChanged.connect(lambda _: save_widgets())
        self.widget_list.model().rowsMoved.connect(lambda *_: QTimer.singleShot(0, save_widgets))
        self.note(box, 'Weather calls Open-Meteo only when you press Check. Audio recording needs a microphone permission and is experimental.')

        # ACCOUNT PLACEHOLDER
        box = self.section('Account')
        self.note(box, 'Account integration is NOT active. These optional fields stay on this device; no emails are sent and no registration occurs.')
        nickname = QLineEdit(str(s.get('account_nickname', '')))
        nickname.setMaxLength(48)
        nickname.editingFinished.connect(lambda: self.set_preference(account_nickname=nickname.text().strip()))
        self.row(box, 'Nickname', nickname)
        email = QLineEdit(str(s.get('account_email', '')))
        email.setMaxLength(200)
        email.editingFinished.connect(lambda: self.set_preference(account_email=email.text().strip()))
        self.row(box, 'FMAIL (optional)', email)
        box.addWidget(self.button('Choose avatar (local only)', self.choose_avatar))
        box.addWidget(self.button('Remove avatar', lambda: self.set_preference(account_avatar='')))
        avatar = QLabel(s.get('account_avatar','') or 'No avatar selected')
        avatar.setWordWrap(True)
        box.addWidget(avatar)

        # WORKSPACES / PRODUCTIVITY
        box = self.section('Workspaces')
        self.note(box, 'Save groups of ordinary web URLs to reopen them later. Workspaces are local. Private tabs are excluded.')
        box.addWidget(self.button('Manage workspaces', self.browser.show_workspaces))
        box.addWidget(self.button('Find an open tab', self.browser.find_open_tab))
        box.addWidget(self.button('Open Split View', self.browser.open_split_view))
        box.addWidget(self.button('Open Reader mode', self.browser.open_reader_mode))
        box.addWidget(self.button('Performance monitor', self.browser.show_performance_monitor))

        # PORTABLE DATA
        box = self.section('Data & backup')
        self.note(box, 'Import / export Firefox-compatible bookmarks and back up local preferences. Passwords and cookies are intentionally excluded.')
        box.addWidget(self.button('Transfer bookmarks & backup', self.browser.show_transfer))
        box.addWidget(self.button('Windows password vault', self.browser.show_password_vault))
        box.addWidget(self.button('Website permissions', self.browser.show_permissions_center))
        self.note(box, 'Signed updates are checked against NOMIKO’s built-in public key. Downloading updates sends a request to GitHub.')

        # SUPPORT
        box = self.section('Support')
        box.addWidget(self.button('Support development ↗', self.browser.open_donation))
        self.note(box, 'Support goes to the NOMIKO developer. The link opens in your browser.')

        # ABOUT
        box = self.section('About')
        self.note(box, 'NOMIKO v0.9.0 Alpha · independent Windows 11 browser. Its interface is created for NOMIKO; website rendering is powered by Qt WebEngine / Chromium.')
        box.addWidget(self.button('Detailed information', self.browser.show_about))

        self.category_list.blockSignals(False)
        selected = max(0, min(selected, self.category_list.count() - 1))
        self.category_list.setCurrentRow(selected)
        self.pages.setCurrentIndex(selected)
        self.filter_categories(self.category_filter.text())
        self._rebuild = False

    def set_transparency(self, name, value):
        values = dict(self.browser.store.settings.get('interface_transparency', {}))
        values[name] = max(0, min(65, int(value)))
        self.set_preference(interface_transparency=values)

    def _referrer_combo(self, settings):
        combo = self.combo([('normal', 'Standard'), ('no-referrer', 'Do not send referrer')],
                           settings.get('privacy_referrer_policy', 'normal'))
        combo.currentIndexChanged.connect(
            lambda _: self.set_preference(privacy_referrer_policy=combo.currentData()))
        return combo

    def update_wallpaper_preview(self):
        image = self.browser.store.wallpaper()
        if image is None:
            self.wallpaper_preview.setPixmap(QPixmap())
            self.wallpaper_preview.setText('No background selected')
            return
        reader = QImageReader(str(image))
        reader.setAutoTransform(True)
        # Decode only one scaled frame, including GIFs; no animation timer or CPU drain.
        size = reader.size()
        if size.isValid():
            reader.setScaledSize(size.scaled(QSize(280, 140), Qt.AspectRatioMode.KeepAspectRatio))
        preview = reader.read()
        if preview.isNull():
            self.wallpaper_preview.setText('Could not preview image')
            return
        self.wallpaper_preview.setPixmap(QPixmap.fromImage(preview))
        self.wallpaper_preview.setToolTip(str(image))

    def hide_all_widgets(self):
        self.widget_list.blockSignals(True)
        for i in range(self.widget_list.count()):
            self.widget_list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.widget_list.blockSignals(False)
        self.set_preference(widget_enabled=[])

    def _organizer(self, box, known, order, hidden, kind):
        lst = QListWidget(self)
        lst.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        lst.setDefaultDropAction(Qt.DropAction.MoveAction)
        lst.setFixedHeight(min(260, max(145, len(known)*28)))
        lst.setMaximumWidth(480)
        lst.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for key in order:
            if key not in known: continue
            item = QListWidgetItem(key.replace('_',' ').title())
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled)
            item.setCheckState(Qt.CheckState.Unchecked if key in hidden else Qt.CheckState.Checked)
            lst.addItem(item)
        box.addWidget(lst)
        def save():
            new_order = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())]
            new_hidden = [lst.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lst.count())
                          if lst.item(i).checkState() == Qt.CheckState.Unchecked]
            self.set_preference(**{f'{kind}_order':new_order, f'{kind}_hidden':new_hidden})
        lst.itemChanged.connect(lambda _: save())
        model = lst.model()
        model.rowsMoved.connect(lambda *_: QTimer.singleShot(0, save))
        return lst

    def _selected_menu_key(self):
        item = self.menu_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def pick_menu_color(self):
        key = self._selected_menu_key()
        if not key: return
        colors = dict(self.browser.store.settings.get('menu_colors', {}))
        chosen = QColorDialog.getColor(QColor(colors.get(key, self.browser.store.settings.get('accent', '#9A82FF'))),
                                       self, 'Menu item color')
        if chosen.isValid():
            colors[key] = chosen.name()
            self.set_preference(menu_colors=colors)

    def reset_menu_color(self):
        key = self._selected_menu_key()
        if not key: return
        colors = dict(self.browser.store.settings.get('menu_colors', {}))
        colors.pop(key, None)
        self.set_preference(menu_colors=colors)

    def _selected_home_key(self):
        item = self.home_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def pick_home_color(self):
        key = self._selected_home_key()
        if not key: return
        colors = dict(self.browser.store.settings.get('home_colors', {}))
        chosen = QColorDialog.getColor(QColor(colors.get(key, self.browser.store.settings.get('accent', '#9A82FF'))),
                                       self, 'Home element color')
        if chosen.isValid():
            colors[key] = chosen.name()
            self.set_preference(home_colors=colors)

    def reset_home_color(self):
        key = self._selected_home_key()
        if not key: return
        colors = dict(self.browser.store.settings.get('home_colors', {}))
        colors.pop(key, None)
        self.set_preference(home_colors=colors)

    def _selected_toolbar_key(self):
        item = self.toolbar_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def pick_toolbar_color(self):
        key = self._selected_toolbar_key()
        if not key: return
        colors = dict(self.browser.store.settings.get('toolbar_colors', {}))
        chosen = QColorDialog.getColor(QColor(colors.get(key, self.browser.store.settings.get('accent', '#9A82FF'))),
                                       self, 'Button icon color')
        if chosen.isValid():
            colors[key] = chosen.name()
            self.set_preference(toolbar_colors=colors)

    def reset_toolbar_color(self):
        key = self._selected_toolbar_key()
        if not key: return
        colors = dict(self.browser.store.settings.get('toolbar_colors', {}))
        colors.pop(key, None)
        self.set_preference(toolbar_colors=colors)

    def pick_accent(self):
        chosen = QColorDialog.getColor(QColor(self.browser.store.settings.get('accent','#9A82FF')),
                                       self, 'NOMIKO accent')
        if chosen.isValid(): self.set_preference(accent=chosen.name())

    def pick_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose a background picture', '',
                                             'Images (*.png *.jpg *.jpeg *.webp *.gif)')
        if not path: return
        if Path(path).stat().st_size > 10 * 1024 * 1024:
            QMessageBox.warning(self, 'Image too large', 'Maximum file size: 10 MB.')
            return
        reader = QImageReader(path)
        if not reader.canRead():
            QMessageBox.warning(self, 'Invalid image', 'NOMIKO cannot read this image.')
            return
        if self.browser.store.save_wallpaper(path):
            self.browser._refresh_internal_pages()
            self.update_wallpaper_preview()
        else:
            QMessageBox.warning(self, 'Wallpaper', 'Unable to save this picture locally.')

    def remove_wallpaper(self):
        self.browser.store.remove_wallpaper()
        self.browser._refresh_internal_pages()
        self.update_wallpaper_preview()

    def choose_avatar(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose profile avatar', '',
                                             'Images (*.png *.jpg *.jpeg *.webp)')
        if not path: return
        if Path(path).stat().st_size > 2 * 1024 * 1024 or not QImageReader(path).canRead():
            QMessageBox.warning(self, 'Avatar', 'Choose a valid image under 2 MB.')
            return
        APP_DIR.mkdir(parents=True, exist_ok=True)
        from shutil import copyfile
        avatar_path = APP_DIR / ('avatar' + Path(path).suffix.lower())
        if Path(path).resolve() != avatar_path.resolve():
            copyfile(path, avatar_path)
        self.set_preference(account_avatar=str(avatar_path))
        self.rebuild()

    def _download_path_changed(self, field):
        path = Path(field.text()).expanduser()
        if not path.is_dir():
            QMessageBox.warning(self, 'Downloads', 'Please select an existing folder.')
            field.setText(self.browser.store.settings.get('downloads_dir', ''))
            return
        self.set_preference(downloads_dir=str(path))
