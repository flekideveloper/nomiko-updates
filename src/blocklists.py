"""Built-in offline request-filter modules. No network-based list downloads.

These lists deliberately remain conservative. They are *not* equivalents of
uBlock Origin or its filter grammar, cosmetic filtering, scriptlets, etc.
"""
from __future__ import annotations
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

AD_DOMAINS = frozenset({
    'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
    'adnxs.com', 'adsrvr.org', 'advertising.com', 'adform.net', 'bidswitch.net',
    'criteo.com', 'criteo.net', 'pubmatic.com', 'rubiconproject.com',
    'openx.net', 'smartadserver.com', 'taboola.com', 'outbrain.com',
    'casalemedia.com', 'yieldmo.com', 'lijit.com', 'moatads.com',
    'contextweb.com', '3lift.com', 'triplelift.com', 'media.net',
    'teads.tv', 'smaato.net', 'spotxchange.com', 'inmobi.com',
    'adcolony.com', 'unityads.unity3d.com', 'amazon-adsystem.com',
    'adsafeprotected.com', 'adservice.google.com', 'revcontent.com',
})
TRACKER_DOMAINS = frozenset({
    'google-analytics.com', 'googletagmanager.com', 'analytics.google.com',
    'facebook.net', 'connect.facebook.net', 'analytics.tiktok.com',
    'scorecardresearch.com', 'quantserve.com', 'hotjar.com', 'clarity.ms',
    'mixpanel.com', 'amplitude.com', 'segment.io', 'branch.io',
    'chartbeat.com', 'newrelic.com', 'pixel.wp.com', 'fullstory.com',
    'mouseflow.com', 'crazyegg.com', 'luckyorange.com', 'heapanalytics.com',
    'kissmetrics.io', 'optimizely.com', 'demdex.net', 'bluekai.com',
    'krxd.net', 'mathtag.com', 'everesttech.net', 'analytics.twitter.com',
    'px.ads.linkedin.com', 'bat.bing.com', 'appsflyer.com',
    'adjust.com', 'kochava.com', 'app-measurement.com', 'mparticle.com',
    'sentry.io', 'datadoghq-browser-agent.com',
})
TRACKING_PARAMS = frozenset({
    'fbclid', 'gclid', 'dclid', 'gbraid', 'wbraid', 'msclkid', 'twclid',
    'igshid', 'mc_cid', 'mc_eid', 'vero_id', 'yclid', '_hsenc', '_hsmi',
    'ref_src', 'spm', 'mkt_tok', 'oly_anon_id', 'oly_enc_id',
})


def matches_domain(host: str, domain_list) -> bool:
    host = str(host).strip('.').lower()
    return any(host == d or host.endswith('.' + d) for d in domain_list)


def blocked_by(host: str, first_party: str = '', ads: bool = True,
               trackers: bool = True, exclusions=()) -> str | None:
    host = str(host).strip('.').lower()
    first_party = str(first_party).strip('.').lower()
    if not host or host == first_party or any(matches_domain(first_party, (e,)) for e in exclusions):
        return None
    if ads and matches_domain(host, AD_DOMAINS):
        return 'ads'
    if trackers and matches_domain(host, TRACKER_DOMAINS):
        return 'trackers'
    return None


def clean_tracking_url(url: str) -> str:
    """Only scrub well-known attribution params; never touch URL fragments or values of other params."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in ('https', 'http') or not parts.netloc or not parts.query:
            return url
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        cleaned = [(key, value) for key, value in pairs
                   if not (key.lower().startswith('utm_') or key.lower() in TRACKING_PARAMS)]
        if len(cleaned) == len(pairs):
            return url
        return urlunsplit((parts.scheme, parts.netloc, parts.path,
                           urlencode(cleaned, doseq=True), parts.fragment))
    except ValueError:
        return url
