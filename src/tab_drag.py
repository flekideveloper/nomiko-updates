"""Pure geometry used for smooth, vertical side-tab reordering.

Qt's standard QTabBar animated drag works for ordinary horizontal tabs.  The
NOMIKO sidebar uses its own non-rotated painting over a vertical QTabBar, so
it needs a matching vertical drag model instead.
"""


def drop_index(source: int, center_y: float, tab_centers: list[float]) -> int:
    """Return the new index of source at the dragged center, excluding itself."""
    if not 0 <= source < len(tab_centers):
        return source
    return sum(center_y > y for i, y in enumerate(tab_centers) if i != source)


def neighbor_shift(index: int, source: int, target: int, height: float) -> float:
    """Where an adjacent tab glides when the dragged tab leaves a gap."""
    if source < target and source < index <= target:
        return -height
    if target < source and target <= index < source:
        return height
    return 0.0
