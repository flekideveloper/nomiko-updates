"""Pure helpers for NOMIKO interface surface transparency (does not expose the desktop)."""

def layered_hex(surface: str, background: str, percent: int) -> str:
    """Blend a surface toward the page background without changing hit targets.

    No true OS-level transparency: this is safer and works reliably with Qt WebEngine.
    """
    strength = max(0, min(65, int(percent))) / 100
    try:
        a = [int(surface[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(background[i:i + 2], 16) for i in (1, 3, 5)]
    except (TypeError, ValueError, IndexError):
        return surface
    return '#'+''.join(f'{round(x*(1-strength)+y*strength):02X}' for x,y in zip(a,b))
