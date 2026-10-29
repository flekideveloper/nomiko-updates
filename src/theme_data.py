"""Pure theme validation and presets."""
from __future__ import annotations
import re

THEME_KEYS = {'theme','accent','theme_font_size','interface_transparency'}
THEME_PRESETS = {
    'Graphite': ('dark', '#9A82FF'),
    'Slate Blue': ('dark', '#74A5FF'),
    'Forest': ('dark', '#78BA93'),
    'Warm Sand': ('light', '#8C6849'),
    'Pearl': ('light', '#5268B6'),
    'Midnight': ('midnight', '#A78BFA'),
}


def sanitize_theme(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError('Theme must be a JSON object')
    result = {}
    if data.get('theme') in ('dark','midnight','light'):
        result['theme'] = data['theme']
    accent = data.get('accent')
    if isinstance(accent, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
        result['accent'] = accent.upper()
    size = data.get('theme_font_size')
    if isinstance(size, int) and not isinstance(size, bool):
        result['theme_font_size'] = min(16, max(10, size))
    trans = data.get('interface_transparency')
    if isinstance(trans, dict):
        result['interface_transparency'] = {
            k:min(65,max(0,int(v))) for k,v in trans.items()
            if k in ('toolbar','tabs','bookmarks','settings') and isinstance(v,int) and not isinstance(v,bool)
        }
    if not result: raise ValueError('No valid NOMIKO theme settings found')
    return result

