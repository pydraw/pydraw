"""
CustomPolygon Test: Tests methods in the CustomPolygon class.
"""

import unittest;
from pydraw import Screen, Color, Location, Renderable, CustomRenderable, CustomPolygon;


class PolygonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600);

    def test_creation(self):
        polygon = CustomPolygon(self.screen,
                                     [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)],
                                     Color('red'), Color('black'), True);

        self.assertEqual(polygon.vertices(), [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)]);

    def test_methods(self):
        polygon = CustomPolygon(self.screen,
                                [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)]);

        self.assertEqual(polygon.location(), (150, 150));
        polygon.move(-50, 200);
        self.assertEqual(polygon.location(), (100, 350));
        polygon.moveto(x=550);
        self.assertEqual(polygon.location(), (550, 350));

        self.assertEqual(polygon.width(), 150);
        self.assertEqual(polygon.height(), 150);

        self.assertEqual(polygon.rotation(), 0);
        polygon.rotate(25);
        self.assertEqual(polygon.rotation(), 25);
        polygon.rotation(-25);
        self.assertEqual(polygon.rotation(), -25);

        self.assertEqual(polygon.color(), Color('black'));
        self.assertEqual(polygon.border(), Color.NONE);

        # self.assertEqual(polygon.transform(), (150, 150, -25));
        # TODO: Polygon keeps original vertices and modifies shape upon update (width/height transform + rotation)


if __name__ == '__main__':
    unittest.main();
