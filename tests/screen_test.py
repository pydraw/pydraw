"""
Screen Test: Tests the methods in the Screen class
"""

import unittest;
from pydraw import Screen, Color, Rectangle;


class ScreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600, 'Custom Name');

    def test_color(self):
        self.screen.color(Color('red'))
        self.assertEqual(self.screen.color(), Color('red'));

    def test_helpers(self):
        self.screen.toggle_grid();
        self.screen.clear();
        self.screen.grid(helpers=True);
        self.assertNotEqual(len(self.screen.gridlines()), len(self.screen.objects()));

    def test_objects(self):
        rect = Rectangle(self.screen, self.screen.width() / 2 - 25, self.screen.height() / 2 - 25, 50, 50);
        self.assertEqual(self.screen.width(), 800);
        self.assertEqual(self.screen.height(), 600);

        self.assertEqual(rect.x(), 375);
        self.assertEqual(rect.y(), 275);

        self.assertEqual(len(self.screen.objects()), 1);
        self.assertEqual(self.screen.objects()[0].color(), rect.color());
        self.assertEqual(self.screen.objects()[0], rect);
        self.assertEqual(len(self.screen.gridlines()), 26);

        self.screen.remove(rect);


if __name__ == '__main__':
    unittest.main();
