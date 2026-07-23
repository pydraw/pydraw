"""Regression tests for the standalone Pen movement API."""

import unittest

from pydraw import Color, Line, Location, Pen, Rectangle, Screen
from pydraw.compound import CompoundObject
from pydraw.errors import InvalidArgumentError, PydrawError, UnsupportedError


class PenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def test_move_and_moveto_return_current_location(self):
        pen = Pen(self.screen, 10, 20)
        self.assertIsNone(pen._ref)
        pen.start()

        self.assertEqual(pen.move(5, 6), Location(15, 26))
        self.assertEqual(pen.moveto(30, 40), Location(30, 40))

    def test_partial_moveto_uses_last_drawn_coordinate(self):
        pen = Pen(self.screen, 10, 20)
        pen.start()
        pen.moveto(30, 40)
        pen.moveto(x=50)

        self.assertEqual(pen.coordinates()[-1], Location(50, 40))

    def test_stopped_moves_advance_from_current_location(self):
        pen = Pen(self.screen, 10, 20)
        pen.start()
        pen.moveto(30, 40)
        pen.stop()

        self.assertEqual(pen.move(5, 6), Location(35, 46))
        self.assertEqual(pen.move(5, 6), Location(40, 52))

    def test_rejects_unknown_movement_keywords(self):
        pen = Pen(self.screen, 10, 20)
        pen.start()

        with self.assertRaises(InvalidArgumentError):
            pen.move(distance=10)
        with self.assertRaises(InvalidArgumentError):
            pen.moveto(horizontal=10)

    def test_object_pen_is_lazy_and_tracks_movement(self):
        obj = Rectangle(self.screen, 10, 20, 30, 40)
        self.assertIsNone(obj._pen)

        pen = obj.pen(Color('red'), 4, True)
        self.assertIs(obj._pen, pen)
        self.assertTrue(pen.drawing())
        self.assertEqual(pen.color(), Color('red'))
        self.assertEqual(pen.width(), 4)
        self.assertTrue(pen.top())

        obj.move(5, 6)
        obj.moveto(30, 40)
        self.assertEqual(
            pen.coordinates(),
            [Location(10, 20), Location(15, 26), Location(30, 40)]
        )

        self.assertFalse(obj.pen_stop())

    def test_object_pen_controls_require_started_pen(self):
        obj = Rectangle(self.screen, 10, 20, 30, 40)

        for method in (obj.pen_clear, obj.pen_stop, obj.pen_width, obj.pen_top):
            with self.subTest(method=method.__name__):
                with self.assertRaises(PydrawError):
                    method()

    def test_clear_while_drawing_can_continue_from_current_location(self):
        obj = Rectangle(self.screen, 10, 20, 30, 40)
        pen = obj.pen()
        obj.move(10, 10)
        obj.pen_clear()
        obj.move(5, 5)

        self.assertEqual(
            pen.coordinates(),
            [Location(20, 30), Location(25, 35)]
        )

    def test_line_and_compound_do_not_support_pens(self):
        line = Line(self.screen, 0, 0, 10, 10)
        shape = Rectangle(self.screen, 20, 20, 10, 10)
        compound = CompoundObject(shape)

        for obj in (line, compound):
            for method in (obj.pen, obj.pen_clear, obj.pen_stop, obj.pen_width, obj.pen_top):
                with self.subTest(obj=type(obj).__name__, method=method.__name__):
                    with self.assertRaises(UnsupportedError):
                        method()


if __name__ == '__main__':
    unittest.main()
