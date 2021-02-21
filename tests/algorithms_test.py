"""
Algorithms Test: Tests all algorithms (IE: overlaps(), contains(), etc).
"""

import unittest;
from pydraw import Screen, Color, Location, Rectangle, Triangle, Oval, Polygon, CustomPolygon, Image;


class AlgorithmsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600);

    def test_overlaps(self):
        shape_types = [Rectangle, Triangle, Oval];

        for Shape in shape_types:
            shape1 = Shape(self.screen, 0, 0, 150, 150, Color('black'), Color('red'));
            shape2 = Shape(self.screen, 50, 50, 150, 150, Color('black'), Color('red2'));
            shape2.rotation(45);

            shape3 = Shape(self.screen, 400, 450, 150, 150, Color('black'), Color('red3'));
            shape3.rotation(-32);

            self.assertTrue(shape1.overlaps(shape2) and shape2.overlaps(shape1), f'{Shape}');
            self.assertFalse(shape3.overlaps(shape1) and shape3.overlaps(shape2), f'{Shape}');

            custom_shape = CustomPolygon(self.screen,
                                         [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)],
                                         Color('black'), Color('red'));

            image = Image(self.screen, '../images/cool_barry.jpg', 250, 250, 150, 150);
            self.assertTrue(image.overlaps(custom_shape));
            self.assertTrue(custom_shape.overlaps(shape2));
            self.screen.clear();

    def test_contains(self):
        shape_types = [Rectangle, Triangle, Oval];

        for Shape in shape_types:
            shape1 = Shape(self.screen, 0, 0, 150, 150, Color('black'), Color('red'));
            shape2 = Shape(self.screen, 50, 50, 150, 150, Color('black'), Color('red2'));
            shape2.rotation(45);

            shape3 = Shape(self.screen, 400, 450, 150, 150, Color('black'), Color('red3'));
            shape3.rotation(-32);

            location1 = Location(100, 100);
            location2 = Location(shape3.center());

            self.assertTrue(shape1.contains(location1) and shape2.contains(location1));
            self.assertFalse(shape1.contains(location2) and shape2.contains(location2));
            self.assertTrue(shape3.contains(location2));

            custom_shape = CustomPolygon(self.screen,
                                         [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)],
                                         Color('black'), Color('red'));
            self.assertTrue(custom_shape.contains(200, 200));

            self.screen.clear();


if __name__ == '__main__':
    unittest.main();
