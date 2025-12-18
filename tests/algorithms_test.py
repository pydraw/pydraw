"""
Algorithms Test: Tests all algorithms (IE: overlaps(), contains(), etc).
"""

import unittest
from pydraw import Screen, Color, Location, Rectangle, Triangle, Oval, Line, CustomPolygon, Image


class AlgorithmsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def test_overlaps(self):
        shape_types = [Rectangle, Triangle, Oval]

        for Shape in shape_types:
            shape1 = Shape(self.screen, 0, 0, 150, 150, Color('black'), Color('red'))
            shape2 = Shape(self.screen, 50, 50, 150, 150, Color('black'), Color('red2'))
            shape2.rotation(45)

            shape3 = Shape(self.screen, 400, 450, 150, 150, Color('black'), Color('red3'))
            shape3.rotation(-32)

            self.assertTrue(shape1.overlaps(shape2) and shape2.overlaps(shape1), f'{Shape}')
            self.assertFalse(shape3.overlaps(shape1) and shape3.overlaps(shape2), f'{Shape}')

            custom_shape = CustomPolygon(self.screen,
                                         [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)],
                                         Color('black'), Color('red'))

            image = Image(self.screen, '../images/cool_barry.jpg', 250, 250, 150, 150)
            self.assertTrue(image.overlaps(custom_shape))
            self.assertTrue(custom_shape.overlaps(shape2))
            self.screen.clear()

    def test_contains(self):
        shape_types = [Rectangle, Triangle, Oval]

        for Shape in shape_types:
            shape1 = Shape(self.screen, 0, 0, 150, 150, Color('black'), Color('red'))
            shape2 = Shape(self.screen, 50, 50, 150, 150, Color('black'), Color('red2'))
            shape2.rotation(45)

            shape3 = Shape(self.screen, 400, 450, 150, 150, Color('black'), Color('red3'))
            shape3.rotation(-32)

            location1 = Location(100, 100)
            location2 = Location(shape3.center())

            self.assertTrue(shape1.contains(location1) and shape2.contains(location1))
            self.assertFalse(shape1.contains(location2) and shape2.contains(location2))
            self.assertTrue(shape3.contains(location2))

            custom_shape = CustomPolygon(self.screen,
                                         [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)],
                                         Color('black'), Color('red'))
            self.assertTrue(custom_shape.contains(200, 200))

            self.screen.clear()

    def test_intersects(self):
        """
        Verify that a Line correctly reports whether it intersects various shapes.
        """
        shape_types = [Rectangle, Triangle, Oval]

        # Helper to create a Line instance
        def make_line(p1, p2):
            loc1 = Location(*p1) if not isinstance(p1, Location) else p1
            loc2 = Location(*p2) if not isinstance(p2, Location) else p2
            return Line(self.screen, loc1, loc2)

        for Shape in shape_types:
            # Base shape at the origin
            shape = Shape(self.screen, 0, 0, 150, 150,
                          Color('black'), Color('red'))

            # A line that crosses the shape
            cross_line = make_line((-10, -10), (160, 160))
            self.assertTrue(cross_line.intersects(shape),
                            f"{Shape.__name__} should intersect the crossing line")

            # A line that stays far away
            miss_line = make_line((400, 400), (500, 500))
            self.assertFalse(miss_line.intersects(shape),
                             f"{Shape.__name__} should not intersect the distant line")

            # Rotated shape test
            rot_shape = Shape(self.screen, 50, 50, 150, 150,
                              Color('black'), Color('red2'))
            rot_shape.rotation(45)
            graze_line = make_line((50, 200), (200, 50))
            self.assertTrue(graze_line.intersects(rot_shape),
                            f"{Shape.__name__} (rotated) should intersect the grazing line")

            # Shape far away – no intersection
            far_shape = Shape(self.screen, 400, 450, 150, 150,
                              Color('black'), Color('red3'))
            far_shape.rotation(-32)
            self.assertFalse(cross_line.intersects(far_shape),
                             f"{Shape.__name__} (far) should not intersect the crossing line")

        # Optional: test against a CustomPolygon
        poly = CustomPolygon(
            self.screen,
            [(150, 150), (250, 150), (300, 200),
             (300, 250), (250, 230), (150, 300)],
            Color('black'), Color('red')
        )
        self.assertTrue(cross_line.intersects(poly),
                        "CustomPolygon should intersect the diagonal line")

        # Truly distant line – no intersection
        far_line = make_line((400, 400), (500, 500))
        self.assertFalse(far_line.intersects(poly),
                         "CustomPolygon should not intersect the distant line")

        self.screen.clear()


if __name__ == '__main__':
    unittest.main()
