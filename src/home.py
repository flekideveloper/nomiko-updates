"""Self-contained, private NOMIKO pages. No JS bridge or third-party assets."""
from __future__ import annotations

from html import escape
from urllib.parse import quote_plus

from .storage import SEARCH_ENGINES, HOME_ITEMS
from .i18n import tr
from .widgets import WIDGET_STYLE, WIDGET_SCRIPT, render_widgets

INTERNAL_SEARCH_ACTION = 'https://nomiko.invalid/search'
ENGINE_OPTIONS = ('DuckDuckGo', 'NOMIKO Search', 'Google')
MAGNIFIER = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10.7" cy="10.7" r="6.3"/><path d="m15.3 15.3 5 5"/></svg>'


def _palette(accent: str, theme: str) -> dict[str, str]:
    # Accent is saved as a QColor-validated hex string in settings. Use a
    # contrasting text tint for legibility with both dark and light themes.
    from .storage import readable_accent
    bright = theme == 'light'
    midnight = theme == 'midnight'
    return {
        'a': accent,
        'ink': '#26303D' if bright else '#EEF0F6',
        'bg': '#F6F7FA' if bright else ('#11131A' if midnight else '#292C33'),
        'surface': '#FFFFFF' if bright else ('#191B25' if midnight else '#343740'),
        'surface2': '#F1F3F7' if bright else ('#242736' if midnight else '#3D414B'),
        'line': '#DDE1E9' if bright else ('#343747' if midnight else '#4B4F5A'),
        'quiet': '#687483' if bright else ('#9DA5B5' if midnight else '#B3BAC7'),
    }


def _common_style(p: dict[str, str]) -> str:
    return f'''<style>
*{{box-sizing:border-box}}html,body{{height:100%;margin:0}}
body{{font-family:"Segoe UI Variable",Segoe UI,Arial,sans-serif;background:{p['bg']};color:{p['ink']};-webkit-user-select:none;user-select:none}}
a,button,select,input{{font-family:inherit}}
input{{user-select:text;-webkit-user-select:text;min-width:0;outline:0;border:0;background:transparent;color:{p['ink']};font-size:14px}}
input::placeholder{{color:{p['quiet']}}}
form.search{{display:flex;gap:8px;align-items:center;background:{p['surface']};border:1px solid {p['line']};border-radius:13px;padding:5px 6px;box-shadow:0 9px 35px #0000001a}}
form.search:focus-within{{border-color:{p['ink']}}}
form.search input{{flex:1;padding:11px 9px}}
form.search button{{width:37px;height:37px;flex:none;display:grid;place-items:center;border:0;border-radius:10px;background:{p['a']};color:#10121B;cursor:pointer}}
form.search button:hover{{filter:brightness(1.12)}}
.engine{{margin-top:13px;display:flex;justify-content:center;align-items:center;gap:8px;color:{p['quiet']};font-size:12px}}
.engine select{{background:{p['surface']};border:1px solid {p['line']};border-radius:8px;padding:6px;color:{p['ink']};font-size:12px}}
a{{color:{p['ink']}}}a:hover{{color:{p['a']}}}
</style>'''


def _engine_select(engine: str, visible_engines=None, language: str = 'en') -> str:
    allowed = [name for name in ENGINE_OPTIONS if visible_engines is None or name in visible_engines]
    if not allowed:
        allowed = ['DuckDuckGo']
    if engine not in allowed:
        engine = allowed[0]
    opts = ''.join(
        f'<option value="{escape(name, quote=True)}"{" selected" if name == engine else ""}>{escape(name)}</option>'
        for name in allowed
    )
    return f'<label class="engine">Search with <select name="engine" form="nomikoSearchForm" aria-label="Search engine">{opts}</select></label>'


def _form(engine: str, query: str = '', placeholder: str = 'Search or enter a website…', visible_engines=None, language: str = 'en') -> str:
    return (
        f'<form id="nomikoSearchForm" class="search" action="{INTERNAL_SEARCH_ACTION}" method="GET">'
        f'<input name="q" maxlength="250" value="{escape(query, quote=True)}" '
        f'aria-label="{escape(tr("Search", language), quote=True)}" placeholder="{escape(tr(placeholder, language), quote=True)}" autocomplete="off" autofocus/>'
        f'<button type="submit" aria-label="{escape(tr("Search", language), quote=True)}">{MAGNIFIER}</button>'
        f'{""}</form>' + _engine_select(engine, visible_engines, language)
    )


def render_home(accent: str, bookmarks: list, private: bool = False,
                theme: str = 'dark', engine: str = 'DuckDuckGo',
                visible_engines=None, language: str = 'en', wallpaper: str = '',
                home_order=None, home_hidden=None, home_colors=None,
                widget_order=None, widget_enabled=None, widget_data=None,
                widget_density='comfortable', widget_columns='auto', weather=None) -> str:
    p = _palette(accent, theme)
    label = tr('PRIVATE SESSION' if private else 'YOUR INTERNET, YOUR RULES', language)
    sub = tr('Temporary data. Private mode does not hide your IP address.' if private
           else 'Explore freely. Customize everything.', language)
    links = []
    if not private:
        for item in reversed(bookmarks[-8:]):
            url = str(item.get('url', ''))
            if not url.startswith(('https://', 'http://')):
                continue
            title = escape(str(item.get('title', url))[:38])
            links.append(f'<a class="shortcut" href="{escape(url, quote=True)}">★ {title}</a>')
    bookmarks_html = '<div class="shortcuts">' + ''.join(links) + '</div>' if links else ''
    order = home_order if isinstance(home_order, list) else HOME_ITEMS
    hidden = home_hidden if isinstance(home_hidden, list) else []
    blocks = {
        'logo': '<div class="logo">N</div>',
        'kicker': f'<p class="kicker">{escape(label)}</p>',
        'title': '<h1>nomiko.</h1>',
        'subtitle': f'<p class="sub">{escape(sub)}</p>',
        'search': f'<div class="searchwrap">{_form(engine, visible_engines=visible_engines, language=language)}</div>',
        'bookmarks': bookmarks_html,
    }
    overrides = home_colors if isinstance(home_colors, dict) else {}
    valid_colors = {key: value for key, value in overrides.items()
                    if key in HOME_ITEMS and isinstance(value, str) and len(value) == 7
                    and value.startswith('#') and all(c in '0123456789abcdefABCDEF' for c in value[1:])}
    content = ''.join(f'<section class="home-part" data-name="{key}">{blocks[key]}</section>'
                      for key in order if key in blocks and key not in hidden)
    dashboard = render_widgets(widget_order, widget_enabled, widget_data,
                               [] if private else bookmarks, weather, widget_density, widget_columns)
    color_css = ''.join(f'.home-part[data-name="{key}"] *{{color:{value} !important}}'
                        for key, value in valid_colors.items())
    # Only a trusted, fixed, locally-generated filename may be injected into CSS.
    wallpaper_css = ('background-image:linear-gradient(#0000006e,#0000006e),'
                     f'url("{wallpaper}");background-size:cover;background-position:center;'
                     if wallpaper in ('wallpaper.png','wallpaper.jpg','wallpaper.jpeg',
                                      'wallpaper.webp','wallpaper.gif') else '')
    has_widgets = bool(dashboard)
    # Widget JS (clock, timers and audio) is not parsed when widgets are off.
    scripts = WIDGET_SCRIPT if has_widgets else ''
    widget_style = WIDGET_STYLE if has_widgets else ''
    home_class = 'with-widgets' if has_widgets else 'clean-home'
    glow = '' if wallpaper_css else f'background:radial-gradient(ellipse at 50% 37%,{p["a"]}14,transparent 53%),{p["bg"]};'
    return f'''<!doctype html><html lang="{escape(language, quote=True)}"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline';script-src 'unsafe-inline';img-src file: data:;media-src blob: file: data:;form-action https://nomiko.invalid;base-uri 'none'"/>
<title>New Tab — NOMIKO</title>{_common_style(p)}
<style>
body{{min-height:100%;height:auto;padding:44px 24px 90px;{wallpaper_css}}}
body.clean-home{{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:32px 22px;{glow}}}
body.clean-home .wrap{{width:min(720px,100%);transform:translateY(-4vh)}}
body.clean-home .logo{{box-shadow:0 12px 32px #00000014}}
body.clean-home .sub{{margin-bottom:31px}}
body.with-widgets .wrap{{padding-bottom:20px}}
@media(max-height:590px){{body.clean-home{{display:block;padding-top:35px}}body.clean-home .wrap{{transform:none}}}}
.wrap{{width:min(1020px,100%);margin:0 auto;text-align:center;display:flex;flex-direction:column;align-items:stretch;gap:0}}
.logo{{margin:auto;width:57px;height:57px;border:1px solid {p['a']}88;border-radius:17px;background:{p['surface']};display:grid;place-items:center;font-weight:900;color:{p['ink']};font-size:29px}}
.kicker{{margin:19px 0 4px;color:{p['a']};font-weight:700;letter-spacing:2.7px;font-size:10px}}
h1{{font-size:52px;letter-spacing:-2.8px;margin:0 0 7px;font-weight:800}}
.sub{{font-size:13px;color:{p['quiet']};margin:0 0 27px}}
.searchwrap{{width:min(490px,100%);margin:auto}}
.shortcuts{{margin:20px auto 0;display:flex;flex-wrap:wrap;justify-content:center;gap:9px}}
.shortcut{{text-decoration:none;font-size:12px;display:block;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid {p['line']};border-radius:10px;background:{p['surface']};padding:9px 13px}}
.home-part{{min-width:0}}
:root{{--bg:{p["bg"]};--ink:{p["ink"]};--card:{p["surface"]};--line:{p["line"]};--quiet:{p["quiet"]};--surface:{p["surface"]};--surface2:{p["surface2"]};--accent:{p["a"]}}}
{widget_style}
{color_css}
</style></head><body class="{home_class}"><main class="wrap">{content}{dashboard}</main><script>{scripts}</script></body></html>''' 



def _matches(query: str, bookmarks: list, history: list) -> list[tuple[str, str, str]]:
    terms = query.casefold().split()
    found: dict[str, tuple[int, str, str, str]] = {}
    for source, rows, bonus in (('BOOKMARK', bookmarks, 100), ('HISTORY', history, 0)):
        for row in rows:
            url = str(row.get('url', ''))
            if not url.startswith(('http://', 'https://')):
                continue
            title = str(row.get('title') or url)
            target = (title + ' ' + url).casefold()
            if terms and not all(t in target for t in terms):
                continue
            score = bonus + sum(12 if t in title.casefold() else 1 for t in terms)
            if url not in found or score > found[url][0]:
                found[url] = (score, source, title, url)
    return [(src, title, url) for _, src, title, url in sorted(found.values(), key=lambda x: -x[0])[:30]]


def render_search_results(query: str, accent: str, bookmarks: list, history: list,
                          private: bool = False, theme: str = 'dark',
                          engine: str = 'NOMIKO Search', visible_engines=None, language: str = 'en') -> str:
    p = _palette(accent, theme)
    items = _matches(query, [] if private else bookmarks, [] if private else history)
    cards = ''.join(
        f'<a class="result" href="{escape(url, quote=True)}"><small>{src}</small>'
        f'<strong>{escape(title[:100])}</strong><span>{escape(url[:150])}</span></a>'
        for src, title, url in items
    )
    if not cards:
        cards = '<div class="empty">' + escape(tr('Nothing in your bookmarks or history matches yet.', language)) + '</div>'
    provider_links = ''.join(
        f'<a class="web" href="{escape(SEARCH_ENGINES[name].format(query=quote_plus(query)), quote=True)}">'
        f'{escape(tr("Search on", language))} {escape(name)} ↗</a>' for name in ('DuckDuckGo', 'Google') if visible_engines is None or name in visible_engines
    )
    return f'''<!doctype html><html lang="{escape(language, quote=True)}"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline';form-action https://nomiko.invalid; base-uri 'none'"/>
<title>{escape(query)} — NOMIKO Search</title>{_common_style(p)}
<style>
body{{padding:35px 24px}}.wrap{{max-width:810px;margin:0 auto}}
.head{{display:flex;align-items:center;gap:12px;margin-bottom:20px}}
.mark{{width:41px;height:41px;background:{p['surface']};border:1px solid {p['line']};border-radius:12px;display:grid;place-items:center;font-size:21px;font-weight:800}}
.head strong{{font-size:23px}}.subtitle{{font-size:12px;color:{p['quiet']}}}
.searchwrap{{max-width:570px;margin-bottom:25px}}
.section{{margin-top:26px;margin-bottom:10px;font-size:12px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:11px}}
.result{{display:flex;flex-direction:column;gap:6px;overflow-wrap:anywhere;text-decoration:none;padding:16px;background:{p['surface']};border:1px solid {p['line']};border-radius:13px}}
.result:hover{{border-color:{p['a']}}}.result small{{font-size:10px;color:{p['quiet']}}}
.result strong{{font-size:14px}}.result span,.empty{{font-size:12px;color:{p['quiet']}}}
.empty{{padding:20px;border:1px dashed {p['line']};border-radius:12px}}
.provider{{display:flex;gap:12px;flex-wrap:wrap}}
.web{{padding:11px 15px;text-decoration:none;border:1px solid {p['line']};border-radius:10px;background:{p['surface']};font-size:13px}}
.note{{font-size:12px;color:{p['quiet']};line-height:1.6;margin-top:17px}}
</style></head><body><main class="wrap"><div class="head"><div class="mark">N</div><div>
<strong>nomiko search</strong><div class="subtitle">{escape(tr('Your local index · No Wikipedia requests', language))}</div></div></div>
<div class="searchwrap">{_form('NOMIKO Search', query, visible_engines=visible_engines, language=language)}</div>
<h2 class="section">{escape(tr('Local results', language))} ({len(items)})</h2><div class="grid">{cards}</div>
<h2 class="section">{escape(tr('Search the wider web', language))}</h2><div class="provider">{provider_links}</div>
<p class="note">{escape(tr('NOMIKO Search currently searches your saved bookmarks and visited-page titles and addresses locally. It is not yet a search engine that indexes the entire public web. External search happens only when you choose a provider.', language))}</p>
</main></body></html>'''
