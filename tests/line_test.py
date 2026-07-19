"""
Line Test: Test methods in the Line class
"""


import unittest
from pydraw.errors import *
from pydraw import Screen, Location, Color, Line


class LineTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def test_constructors(self):
        # Four numbers (x1, y1, x2, y2)
        line = Line(self.screen, 100, 100, 200, 100)
        self.assertEqual(line.pos1(), Location(100, 100))
        self.assertEqual(line.pos2(), Location(200, 100))

        # Two tuples
        line = Line(self.screen, (0, 0), (3, 4))
        self.assertEqual(line.pos1(), Location(0, 0))
        self.assertEqual(line.pos2(), Location(3, 4))
        self.assertAlmostEqual(line.length(), 5.0)

        # Two Locations
        line = Line(self.screen, Location(10, 10), Location(10, 40))
        self.assertEqual(line.pos1(), Location(10, 10))
        self.assertEqual(line.pos2(), Location(10, 40))
        self.assertAlmostEqual(line.length(), 30.0)

        # Too few arguments
        self.assertRaises(InvalidArgumentError, Line, self.screen, 5)

    def test_defaults(self):
        line = Line(self.screen, 0, 0, 10, 0)
        self.assertEqual(line.color(), Color('black'))
        self.assertEqual(line.thickness(), 1)
        self.assertEqual(line.dashes(), None)
        self.assertEqual(line.visible(), True)

    def test_location(self):
        line = Line(self.screen, 100, 100, 200, 150)
        self.assertEqual(line.location(), (Location(100, 100), Location(200, 150)))

    def test_length(self):
        line = Line(self.screen, 0, 0, 3, 4)
        self.assertAlmostEqual(line.length(), 5.0)

        line.pos2(0, 10)
        self.assertAlmostEqual(line.length(), 10.0)

    def test_color(self):
        line = Line(self.screen, 0, 0, 10, 10)
        self.assertEqual(line.color(), Color('black'))

        line.color(Color('blue'))
        self.assertEqual(line.color(), Color('blue'))

        self.assertRaises(InvalidArgumentError, line.color, 'not_a_color')

    def test_thickness(self):
        line = Line(self.screen, 0, 0, 10, 10)
        self.assertEqual(line.thickness(), 1)

        line.thickness(5)
        self.assertEqual(line.thickness(), 5)

        self.assertRaises(InvalidArgumentError, line.thickness, 'thick')

    def test_dashes(self):
        line = Line(self.screen, 0, 0, 10, 10)
        self.assertEqual(line.dashes(), None)

        line.dashes(4)
        self.assertEqual(line.dashes(), 4)

        line.dashes((4, 2))
        self.assertEqual(line.dashes(), (4, 2))

        self.assertRaises(InvalidArgumentError, line.dashes, 'dash')

    def test_visible(self):
        line = Line(self.screen, 0, 0, 10, 10)
        self.assertEqual(line.visible(), True)

        line.visible(False)
        self.assertEqual(line.visible(), False)

    def test_endpoints(self):
        line = Line(self.screen, 0, 0, 10, 0)

        line.pos1(5, 5)
        self.assertEqual(line.pos1(), Location(5, 5))

        line.pos2(Location(20, 20))
        self.assertEqual(line.pos2(), Location(20, 20))

    def test_move(self):
        line = Line(self.screen, 100, 100, 200, 100)

        # Move both endpoints
        line.move(10, 20)
        self.assertEqual(line.pos1(), Location(110, 120))
        self.assertEqual(line.pos2(), Location(210, 120))

        # Move only the second endpoint
        line.move(5, 0, point=2)
        self.assertEqual(line.pos1(), Location(110, 120))
        self.assertEqual(line.pos2(), Location(215, 120))

    def test_rotation(self):
        line = Line(self.screen, 0, 0, 10, 0)
        self.assertAlmostEqual(line.rotation(), 180.0)

        # Rotate 90 degrees about pos1
        line.rotate(90)
        self.assertAlmostEqual(line.rotation(), 270.0)
        self.assertAlmostEqual(line.pos1().x(), 0)
        self.assertAlmostEqual(line.pos1().y(), 0)
        self.assertAlmostEqual(line.pos2().x(), 0)
        self.assertAlmostEqual(line.pos2().y(), 10)

        # Absolute set via rotation()
        line.rotation(45)
        self.assertAlmostEqual(line.rotation(), 45.0)

    def test_transform(self):
        line = Line(self.screen, 0, 0, 3, 4)
        length, rotation = line.transform()
        self.assertAlmostEqual(length, 5.0)
        self.assertAlmostEqual(rotation, line.rotation())

        # Setting a transform is not yet supported
        self.assertRaises(UnsupportedError, line.transform, (1, 2))

    def test_clone(self):
        line = Line(self.screen, 0, 0, 10, 0, Color('green'), 3)
        clone = line.clone()

        self.assertAlmostEqual(clone.length(), line.length())
        self.assertAlmostEqual(clone.rotation(), line.rotation())
        self.assertEqual(clone.color(), line.color())
        self.assertEqual(clone.thickness(), line.thickness())

    def test_intersects(self):
        a = Line(self.screen, 0, 0, 10, 10)

        # Crossing line
        crossing = Line(self.screen, 0, 10, 10, 0)
        self.assertTrue(a.intersects(crossing))

        # Non-crossing line
        apart = Line(self.screen, 0, 5, 1, 5)
        self.assertFalse(a.intersects(apart))

        # Invalid argument
        self.assertRaises(InvalidArgumentError, a.intersects, 42)


if __name__ == '__main__':
    unittest.main()
