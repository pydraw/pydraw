"""
Image Test: Tests methods in the Image class
"""

import unittest;
from pydraw import *;


class ImageTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600);

    def test_creation(self):
        image = Image(self.screen, '../cool_barry.jpg', screen.width() / 2, screen.height() / 2, 50, 50,
                      color=Color('magenta'), border=Color('green'), rotation=30);

        self.screen.clear();

    def test_rotation(self):
        image = Image(self.screen, '../cool_barry.jpg', screen.width() / 2, screen.height() / 2, 50, 50);
        image.rotation(30);


if __name__ == '__main__':
    unittest.main();
