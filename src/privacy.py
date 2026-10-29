"""Offline, first-party-aware network modules. No telemetry, no remote list download.

Qt calls interceptRequest on an I/O thread: never touch Qt UI objects there.
"""
from __future__ import annotations
from threading import Lock
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from .blocklists import blocked_by, matches_domain, AD_DOMAINS, TRACKER_DOMAINS
from .module_packs import match_host

TRACKER_HOSTS = TRACKER_DOMAINS  # compatibility with older tests


def match_blocked(host):
    return matches_domain(host, TRACKER_DOMAINS | AD_DOMAINS)


class TrackerInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, enabled=True, parent=None, adblock=True, exceptions=None):
        super().__init__(parent)
        self.enabled = enabled
        self.adblock = adblock
        self.exceptions = tuple(exceptions or ())
        self._custom_hosts = frozenset()
        self._count = {'ads': 0, 'trackers': 0}
        self._guard = Lock()

    def configure(self, tracker_enabled, adblock_enabled, exceptions=(), referrer_policy='normal'):
        # Atomic swap of a single immutable policy object read on I/O thread.
        self._policy = (bool(tracker_enabled), bool(adblock_enabled),
                        tuple(str(x).strip().lower() for x in exceptions if isinstance(x, str)),
                        referrer_policy == 'no-referrer')
        self.enabled = bool(tracker_enabled)
        self.adblock = bool(adblock_enabled)

    def set_custom_hosts(self, hosts):
        # Immutable copy: safe to swap on the GUI thread while network requests run.
        self._custom_hosts = frozenset(hosts)

    def counts(self):
        with self._guard:
            return dict(self._count)

    def interceptRequest(self, info):
        policy = getattr(self, '_policy', (self.enabled, self.adblock, self.exceptions))
        trackers, ads, exceptions, no_referrer = (policy if len(policy) == 4 else (*policy, False))
        if no_referrer:
            info.setHttpHeader(b'Referer', b'')
        # Main-frame navigation is never blocked, preserving manual site access.
        if info.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            return
        url = info.requestUrl()
        host = url.host().lower()
        first_party = info.firstPartyUrl().host().lower()
        reason = blocked_by(host, first_party, ads, trackers, exceptions)
        if not reason and (ads or trackers) and host != first_party and match_host(host, self._custom_hosts):
            if not any(matches_domain(first_party, (e,)) for e in exceptions):
                reason = 'trackers'
        if reason:
            info.block(True)
            with self._guard:
                self._count[reason] += 1
