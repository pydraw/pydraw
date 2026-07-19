"""
Overload Test: End-to-end coverage of pydraw's multiple-dispatch constructors -
the same object built through positional numbers, a Location, and via keyword
arguments, across more than one class.

(Rewritten from an old manual smoke-test script into real assertions.)
"""

import unittest
from pydraw import Screen, Location, Color, Rectangle, Text


class OverloadTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def test_rectangle_xy_form(self):
        rect = Rectangle(self.screen, 100, 100, 50, 50)
        self.assertEqual(rect.location(), Location(100, 100))
        self.assertEqual(rect.width(), 50)
        self.assertEqual(rect.height(), 50)

    def test_rectangle_location_form(self):
        # The same constructor dispatched on a Location as the first coordinate.
        center = self.screen.center()
        rect = Rectangle(self.screen, center, 50, 50)
        self.assertEqual(rect.location(), center)

    def test_rectangle_keyword_arguments(self):
        rect = Rectangle(self.screen, 500, 400, 150, 50,
                         color=Color('green'), fill=True, border=Color('black'))
        self.assertEqual(rect.color(), Color('green'))
        self.assertEqual(rect.border(), Color('black'))
        self.assertTrue(rect.fill())

    def test_rectangle_mixed_positional_and_keyword(self):
        # A positional color plus a trailing keyword - both dispatch to the
        # same signature and forward the kwargs.
        a = Rectangle(self.screen, 43, 43, 50, 50, color=Color('blue'))
        self.assertEqual(a.color(), Color('blue'))

        b = Rectangle(self.screen, 150, 75, 50, 50, Color('red'), visible=False)
        self.assertEqual(b.color(), Color('red'))
        self.assertFalse(b.visible())

    def test_text_location_form(self):
        loc = Location(200, 100)
        text = Text(self.screen, 'Some text', loc)
        self.assertEqual(text.location(), loc)

    def test_text_computed_coordinate(self):
        # Values computed from another object's measured width still dispatch to
        # the (str, x, y) numeric form.
        first = Text(self.screen, 'Some text', 200, 100)
        second = Text(self.screen, 'More text', 210 + first.width(), 100)
        self.assertEqual(second.x(), 210 + first.width())


if __name__ == '__main__':
    unittest.main()
