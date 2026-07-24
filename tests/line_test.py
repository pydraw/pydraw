"""
Line Test: Test methods in the Line class
"""


import unittest
from pydraw.errors import InvalidArgumentError, UnsupportedError
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

    def test_constructor_positional_extras(self):
        # Two Locations / tuples followed by positional color, thickness, etc.
        # (the tightened guard must still route these to the endpoint branch).
        line = Line(self.screen, Location(0, 0), Location(9, 0), Color('blue'), 2)
        self.assertEqual(line.pos1(), Location(0, 0))
        self.assertEqual(line.pos2(), Location(9, 0))
        self.assertEqual(line.color(), Color('blue'))
        self.assertEqual(line.thickness(), 2)

        line = Line(self.screen, (0, 0), (10, 0), Color('red'))
        self.assertEqual(line.color(), Color('red'))

    def test_constructor_rejects_bad_arity(self):
        # Two or three bare numbers is not a valid Line (needs four).
        self.assertRaises(InvalidArgumentError, Line, self.screen, 0, 0)
        self.assertRaises(InvalidArgumentError, Line, self.screen, 0, 0, 10)

    def test_constructor_kwargs(self):
        line = Line(self.screen, 0, 0, 10, 0, color=Color('red'), thickness=3,
                    dashes=(4, 2), visible=False)
        self.assertEqual(line.color(), Color('red'))
        self.assertEqual(line.thickness(), 3)
        self.assertEqual(line.dashes(), (4, 2))
        self.assertFalse(line.visible())

    def test_endpoints_tuple_form(self):
        line = Line(self.screen, 0, 0, 10, 0)
        line.pos1((5, 5))
        self.assertEqual(line.pos1(), Location(5, 5))
        line.pos2((20, 20))
        self.assertEqual(line.pos2(), Location(20, 20))

    def test_endpoints_reject_bad_input(self):
        line = Line(self.screen, 0, 0, 10, 0)
        # Non-numeric pair is rejected at the guard (previously slipped through).
        self.assertRaises(TypeError, line.pos1, 'a', 'b')
        self.assertRaises(TypeError, line.pos2, 'a', 'b')
        # Two tuples is not a valid endpoint form (previously the 2nd was
        # silently dropped due to an operator-precedence bug).
        self.assertRaises(TypeError, line.pos1, (1, 2), (3, 4))
        self.assertRaises(TypeError, line.pos2, (1, 2), (3, 4))

    def test_lookat_reject_bad_input(self):
        line = Line(self.screen, 0, 0, 10, 0)
        self.assertRaises(InvalidArgumentError, line.lookat, 'a', 'b')

    def test_move(self):
        line = Line(self.screen, 100, 100, 200, 100)

        # Move both endpoints
        line.move(10, 20)
        self.assertEqual(line.pos1(), Location(110, 120))
        self.assertEqual(line.pos2(), Location(210, 120))

        # Move only the first endpoint
        line.move(1, 1, point=1)
        self.assertEqual(line.pos1(), Location(111, 121))
        self.assertEqual(line.pos2(), Location(210, 120))

        # Move only the second endpoint
        line.move(5, 0, point=2)
        self.assertEqual(line.pos1(), Location(111, 121))
        self.assertEqual(line.pos2(), Location(215, 120))

        # An invalid point selector is rejected
        self.assertRaises(InvalidArgumentError, line.move, 1, 1, point=3)

    def test_move_point_zero_moves_both_endpoints(self):
        line = Line(self.screen, 100, 100, 200, 100)
        line.move(10, 20, point=0)

        self.assertEqual(line.pos1(), Location(110, 120))
        self.assertEqual(line.pos2(), Location(210, 120))

    def test_move_rejects_unknown_keywords(self):
        line = Line(self.screen, 100, 100, 200, 100)
        with self.assertRaises(InvalidArgumentError):
            line.move(10, 20, endpoint=1)

    def test_moveto(self):
        line = Line(self.screen, 0, 0, 10, 0)

        # Four numbers (x1, y1, x2, y2)
        line.moveto(50, 50, 100, 100)
        self.assertEqual(line.pos1(), Location(50, 50))
        self.assertEqual(line.pos2(), Location(100, 100))

        # Two tuples
        line.moveto((0, 0), (5, 5))
        self.assertEqual(line.pos1(), Location(0, 0))
        self.assertEqual(line.pos2(), Location(5, 5))

        # Keyword endpoints
        line.moveto(x1=1, y1=2, x2=3, y2=4)
        self.assertEqual(line.pos1(), Location(1, 2))
        self.assertEqual(line.pos2(), Location(3, 4))

    def test_moveto_rejects_unknown_keywords_without_moving(self):
        line = Line(self.screen, 0, 0, 10, 0)
        before = line.location()

        with self.assertRaises(InvalidArgumentError):
            line.moveto((20, 20), (30, 30), endpoint=1)

        self.assertEqual(line.location(), before)

    def test_lookat(self):
        # Line points along +x; look at a point directly above pos1.
        line = Line(self.screen, 0, 0, 10, 0)
        line.lookat(0, 10)
        # pos1 stays fixed and the length is preserved (lookat rotates pos2).
        self.assertEqual(line.pos1(), Location(0, 0))
        self.assertAlmostEqual(line.length(), 10.0)
        self.assertAlmostEqual(line.pos2().x(), 0)
        self.assertAlmostEqual(line.pos2().y(), 10)

    def test_lookat_rejects_unknown_keywords(self):
        line = Line(self.screen, 0, 0, 10, 0)
        with self.assertRaises(InvalidArgumentError):
            line.lookat(0, 10, endpoint=2)

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

    def test_rotate_about_pos2(self):
        # Rotate 90 degrees about pos2; pos2 stays put, pos1 swings around it.
        line = Line(self.screen, 0, 0, 10, 0)
        line.rotate(90, point=2)
        self.assertAlmostEqual(line.pos2().x(), 10)
        self.assertAlmostEqual(line.pos2().y(), 0)
        self.assertAlmostEqual(line.pos1().x(), 10)
        self.assertAlmostEqual(line.pos1().y(), -10)

    def test_endpoint_changes_keep_rotation_in_sync(self):
        line = Line(self.screen, 0, 0, 10, 0)
        line.pos2(0, 10)
        expected = Line(self.screen, line.pos1(), line.pos2()).rotation()
        self.assertAlmostEqual(line.rotation(), expected)

        line.moveto((0, 0), (-10, 0))
        expected = Line(self.screen, line.pos1(), line.pos2()).rotation()
        self.assertAlmostEqual(line.rotation(), expected)

    def test_rotate_rejects_invalid_origin_point(self):
        line = Line(self.screen, 0, 0, 10, 0)
        self.assertRaises(InvalidArgumentError, line.rotate, 45, point=0)
        self.assertRaises(InvalidArgumentError, line.rotate, 45, point=3)

    def test_transform(self):
        line = Line(self.screen, 0, 0, 3, 4)
        length, rotation = line.transform()
        self.assertAlmostEqual(length, 5.0)
        self.assertAlmostEqual(rotation, line.rotation())

        # Setting a transform is not yet supported
        self.assertRaises(UnsupportedError, line.transform, (1, 2))

    def test_clone(self):
        line = Line(self.screen, 0, 0, 10, 0, Color('green'), 3, (4, 2), False)
        clone = line.clone()

        self.assertAlmostEqual(clone.length(), line.length())
        self.assertAlmostEqual(clone.rotation(), line.rotation())
        self.assertEqual(clone.color(), line.color())
        self.assertEqual(clone.thickness(), line.thickness())
        self.assertEqual(clone.dashes(), line.dashes())
        self.assertEqual(clone.visible(), line.visible())
        self.assertEqual(clone.pos1(), line.pos1())
        self.assertEqual(clone.pos2(), line.pos2())

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
