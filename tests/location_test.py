"""
Location Test: Tests methods in the Location class
"""

import unittest
from pydraw import Location
from pydraw.errors import InvalidArgumentError


class LocationTest(unittest.TestCase):

    def test_creation(self):
        location1 = Location(150, 300)
        location2 = Location((150, 300))
        location3 = Location(location2)

        location4 = Location(x=150, y=300)
        location5 = Location(x=150)

        self.assertEqual(location1, location2)
        self.assertEqual(location2, location3)
        self.assertEqual(location3, location4)
        self.assertEqual(location5.x(), 150)
        self.assertEqual(location5.y(), 0)

    def test_methods(self):
        location1 = Location(150, 300)
        self.assertEqual(location1, (150, 300))

        location1.move(dx=100, dy=50)
        self.assertEqual(location1, (250, 350))

        self.assertRaises(InvalidArgumentError, location1.move, '')

        location1.moveto((300, 300))
        self.assertEqual(location1, (300, 300))
        location1.moveto(x=500)
        self.assertEqual(location1, (500, 300))

    def test_value_and_sequence_protocols(self):
        location = Location(3, 4)
        clone = location.clone()

        self.assertEqual(location.distance(Location(0, 0)), 5)
        self.assertEqual(tuple(location), (3, 4))
        self.assertEqual(location[0], 3)
        self.assertEqual(location[1], 4)
        self.assertEqual(len(location), 2)
        self.assertEqual(hash(location), hash(clone))
        self.assertIsNot(location, clone)
        with self.assertRaises(IndexError):
            _ = location[2]

    def test_coordinate_setters(self):
        location = Location(1, 2)
        self.assertEqual(location.x(10), 10)
        self.assertEqual(location.y(20), 20)
        self.assertEqual(location, Location(10, 20))

    def test_move_forms(self):
        # move()/moveto() accept two numbers, a tuple, or a Location.
        loc = Location(0, 0)
        loc.move(2, 3)
        self.assertEqual(loc, (2, 3))
        loc.move((1, 1))
        self.assertEqual(loc, (3, 4))
        loc.move(Location(-3, -4))
        self.assertEqual(loc, (0, 0))

        loc.moveto(5, 6)
        self.assertEqual(loc, (5, 6))
        loc.moveto(Location(7, 8))
        self.assertEqual(loc, (7, 8))

    def test_rejects_bad_types(self):
        # Regression: the two-number branch guard used to be a dead
        # list-wrapped generator, so non-numeric pairs slipped through.
        self.assertRaises(InvalidArgumentError, Location, 'a', 'b')
        loc = Location(0, 0)
        self.assertRaises(InvalidArgumentError, loc.move, 'a', 'b')
        self.assertRaises(InvalidArgumentError, loc.moveto, 'a', 'b')

    def test_rejects_unknown_keywords(self):
        with self.assertRaises(InvalidArgumentError):
            Location(horizontal=10)

        loc = Location(0, 0)
        with self.assertRaises(InvalidArgumentError):
            loc.move(distance=10)
        with self.assertRaises(InvalidArgumentError):
            loc.moveto(horizontal=10)


if __name__ == '__main__':
    unittest.main()
