"""
Color Test: Tests methods in the Color class
"""

import unittest;
from pydraw import Color;


class ColorTest(unittest.TestCase):
    def test_colors(self):
        color = Color('red');
        self.assertEqual(color.red(), 255);
        self.assertEqual(color.green(), 0);
        self.assertEqual(color.blue(), 0);

        self.assertEqual(color.rgb(), (255, 0, 0));
        self.assertEqual(color.__value__(), 'red');

        color2 = Color('#f6f');
        self.assertEqual(color2, Color('#ff66ff'));
        self.assertEqual(color2.rgb(), (255, 102, 255));


if __name__ == '__main__':
    unittest.main()