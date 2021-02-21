"""
Location Test: Tests methods in the Location class
"""

import unittest;
from pydraw import Screen, Location, Rectangle;
from pydraw.errors import *;


class LocationTest(unittest.TestCase):

    def test_creation(self):
        location1 = Location(150, 300);
        location2 = Location((150, 300));
        location3 = Location(location2);

        location4 = Location(x=150, y=300);
        location5 = Location(x=150);

        self.assertEqual(location1, location2);
        self.assertEqual(location2, location3);
        self.assertEqual(location3, location4);
        self.assertEqual(location5.x(), 150);
        self.assertEqual(location5.y(), 0);

    def test_methods(self):
        location1 = Location(150, 300);
        self.assertEqual(location1, (150, 300));

        location1.move(dx=100, dy=50);
        self.assertEqual(location1, (250, 350));

        self.assertRaises(InvalidArgumentError, location1.move, '');

        location1.moveto((300, 300));
        self.assertEqual(location1, (300, 300));
        location1.moveto(x=500);
        self.assertEqual(location1, (500, 300));


if __name__ == '__main__':
    unittest.main();
