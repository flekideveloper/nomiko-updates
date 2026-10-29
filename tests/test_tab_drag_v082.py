"""Side-tab drag regression tests independent of Qt installation."""
import unittest
from pathlib import Path

from src.tab_drag import drop_index, neighbor_shift


ROOT = Path(__file__).resolve().parents[1]


class VerticalDragGeometryTests(unittest.TestCase):
    def setUp(self):
        self.centers = [20, 61, 102, 143, 184]

    def test_drag_first_to_last(self):
        self.assertEqual(drop_index(0, 202, self.centers), 4)
        self.assertEqual(drop_index(0, 85, self.centers), 1)

    def test_sidebar_mode_is_geometry_independent(self):
        # Both favicon-only and expanded sidebar tabs use the same vertical
        # hit geometry; resizing the bar changes width, not drag placement.
        for label_mode in ('icon', 'expanded'):
            with self.subTest(label_mode=label_mode):
                self.assertEqual(drop_index(1, 159, self.centers), 3)
                self.assertEqual(drop_index(3, 46, self.centers), 1)

    def test_drag_last_to_first(self):
        self.assertEqual(drop_index(4, 3, self.centers), 0)
        self.assertEqual(drop_index(4, 90, self.centers), 2)

    def test_drag_in_place_and_one_tab(self):
        self.assertEqual(drop_index(2, 102, self.centers), 2)
        self.assertEqual(drop_index(0, 100, [20]), 0)
        self.assertEqual(drop_index(-1, 100, self.centers), -1)

    def test_gap_moves_neighbors_but_not_source(self):
        self.assertEqual([neighbor_shift(i, 0, 3, 41) for i in range(5)],
                         [0, -41, -41, -41, 0])
        self.assertEqual([neighbor_shift(i, 3, 0, 41) for i in range(5)],
                         [41, 41, 41, 0, 0])
        self.assertTrue(all(neighbor_shift(i, 2, 2, 41) == 0 for i in range(5)))

    def test_vertical_mouse_drag_wired_to_tab_move(self):
        source = (ROOT / 'src' / 'ui.py').read_text(encoding='utf-8')
        self.assertIn('self.bar.setMovable(not side)', source)
        self.assertIn('self._drag_target = drop_index(', source)
        self.assertIn('self.moveTab(source, target)', source)
        self.assertIn('self.bar.tabMoved.connect(self._tab_moved)', source)
        self.assertIn('self._animation.setInterval(16)', source)
        self.assertIn('self._dragging and index == self._drag_index', source)
        self.assertIn('self._close_pressed', source)


if __name__ == '__main__':
    unittest.main()
