"""
Image Test: Tests methods in the Image class
"""

import os
import unittest
from pydraw import *

IMAGE_PATH = os.path.join(os.path.dirname(__file__), '..', 'images', 'cool_barry.jpg')


class ImageTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def test_creation(self):
        image = Image(self.screen, IMAGE_PATH, self.screen.width() / 2, self.screen.height() / 2, 50, 50,
                      color=Color('magenta'), border=Color('green'), rotation=30)

        self.assertEqual(image.width(), 50)
        self.assertEqual(image.height(), 50)

        self.screen.clear()

    def test_rotation(self):
        image = Image(self.screen, IMAGE_PATH, self.screen.width() / 2, self.screen.height() / 2, 50, 50)
        image.rotation(30)

        self.assertEqual(image.rotation(), 30)

        self.screen.clear()


if __name__ == '__main__':
    unittest.main()
