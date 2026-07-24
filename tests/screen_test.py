"""Integration tests for Screen state and its real Tk canvas."""

import unittest
from pydraw import Screen, Color, Location, Rectangle
from pydraw.errors import PydrawError


class ScreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600, 'Custom Name')

    def setUp(self) -> None:
        self.screen.reset()
        self.screen.color(Color('white'))
        self.screen.title('Custom Name')

    def test_title_and_color_round_trip_to_tk(self):
        self.screen.title('Updated Name')
        self.screen.color(Color('red'))

        self.assertEqual(self.screen.title(), 'Updated Name')
        self.assertEqual(self.screen.color(), Color('red'))
        self.assertEqual(self.screen._root.title(), 'Updated Name')
        self.assertEqual(self.screen._screen.bgcolor(), 'red')

    def test_geometry_helpers(self):
        self.assertEqual(self.screen.width(), 800)
        self.assertEqual(self.screen.height(), 600)
        self.assertEqual(self.screen.center(), Location(400, 300))
        self.assertEqual(self.screen.top_left(), Location(0, 0))
        self.assertEqual(self.screen.top_right(), Location(800, 0))
        self.assertEqual(self.screen.bottom_left(), Location(0, 600))
        self.assertEqual(self.screen.bottom_right(), Location(800, 600))

        self.assertEqual(self.screen.create_location(0, 0), Location(400, 300))
        self.assertEqual(self.screen.canvas_location(400, 300), Location(0, 0))

    def test_grid_is_screen_decoration_not_user_object(self):
        rect = Rectangle(self.screen, 10, 10, 20, 20)
        self.screen.grid(rows=3, cols=4, helpers=False)

        self.assertGreater(len(self.screen.gridlines()), 0)
        self.assertEqual(self.screen.objects(), (rect,))

        self.screen.toggle_grid(False)
        self.assertTrue(all(not line.visible() for line in self.screen.gridlines()))
        self.screen.toggle_grid(True)
        self.assertTrue(all(line.visible() for line in self.screen.gridlines()))

        self.screen.reset()
        self.assertEqual(self.screen.gridlines(), ())
        self.assertEqual(self.screen.objects(), ())

    def test_object_lifecycle_updates_registry_and_canvas(self):
        rect = Rectangle(self.screen, self.screen.width() / 2 - 25, self.screen.height() / 2 - 25, 50, 50)

        self.assertEqual(rect.x(), 375)
        self.assertEqual(rect.y(), 275)
        self.assertIn(rect, self.screen)
        self.assertEqual(self.screen.objects(), (rect,))
        self.assertNotEqual(self.screen._canvas.type(rect._ref), '')

        self.screen.remove(rect)
        self.assertNotIn(rect, self.screen)
        self.assertIsNone(self.screen._canvas.type(rect._ref))

        self.screen.add(rect)
        self.assertIn(rect, self.screen)
        with self.assertRaises(PydrawError):
            self.screen.add(rect)

    def test_update_flushes_object_changes_to_canvas(self):
        rect = Rectangle(self.screen, 20, 30, 40, 50, Color('blue'))
        rect.move(15, 25)

        self.screen.update()

        self.assertEqual(rect.location(), Location(35, 55))
        self.assertEqual(self.screen._canvas.itemcget(rect._ref, 'fill'), 'blue')


if __name__ == '__main__':
    unittest.main()
