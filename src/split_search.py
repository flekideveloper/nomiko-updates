"""Pure search routing shared by the two independent Split View panes."""
from __future__ import annotations

from .storage import SEARCH_ENGINES, is_navigation_input, resolve_input


def split_destination(text: str, engine: str) -> tuple[str, str] | None:
    """Return ('web', URL) or ('local', text); never use the wrong provider.

    Each Split View pane owns its search engine independently of the app's
    default. Explicit URLs always navigate directly instead of searching.
    """
    query = str(text).strip()[:250]
    if not query:
        return None
    if is_navigation_input(query):
        return ('web', resolve_input(query))
    if engine == 'NOMIKO Search':
        return ('local', query)
    if engine not in SEARCH_ENGINES:
        engine = 'DuckDuckGo'
    return ('web', resolve_input(query, engine))
