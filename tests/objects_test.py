"""
Objects Test: Tests methods on the Object class.
"""

import unittest;
from pydraw.errors import *;
from pydraw import Screen, Location, Color, Rectangle, Oval, Triangle, Renderable, Polygon;


class ObjectsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600);

    def test_constructors(self):
        self.create_objects();

        start = Location(150, 150);
        for obj in self.objects:
            self.assertEqual(obj.location(), start);
            self.assertIsInstance(obj, Renderable);
            start.move(100, 100);

    def test_methods(self):
        self.create_objects();

        start = Location(150, 150);
        for obj in self.objects:
            self.assertEqual(obj.width(), 50);
            self.assertEqual(obj.height(), 50);

            obj.width(75);
            obj.height(75);

            self.assertEqual(obj.width(), 75);
            self.assertEqual(obj.height(), 75);

            # self.assertEqual(obj.center(), (obj.x() + 75 / 2, obj.y() + 75 / 2));

            self.assertEqual(obj.color(), Color('black'));
            obj.color(Color('gray'));
            self.assertEqual(obj.color(), Color('gray'));

            self.assertRaises(InvalidArgumentError, obj.color, 'not_a_color');

            self.assertEqual(obj.rotation(), 30);
            obj.rotate(5);
            self.assertEqual(obj.rotation(), 35);

            self.assertEqual(obj.border(), Color('red'));
            obj.border(Color('black'), False);
            self.assertEqual(obj.border(), Color('black'));
            self.assertEqual(obj.fill(), False);

            self.assertEqual(obj.distance(obj.center()), 0);
            self.assertAlmostEqual(obj.distance(obj.center().move(75, 75)), 106.066017, 4);

            self.assertEqual(obj.visible(), True);
            obj.visible(False);
            self.assertEqual(obj.visible(), False);

            self.assertEqual(obj.transform(), (75, 75, 35));
            obj.transform((100, 100, 36));
            self.assertEqual(obj.transform(), (100, 100, 36));

            self.assertEqual(obj.width(), 100);
            self.assertEqual(obj.height(), 100);
            self.assertEqual(obj.rotation(), 36);

            start.move(100, 100);

    def create_objects(self):
        self.screen.clear();

        rect = Rectangle(self.screen, 150, 150, 50, 50, Color('black'), Color('red'), True, 30);
        oval = Oval(self.screen, 250, 250, 50, 50, Color('black'), Color('red'), True, 30);
        triangle = Triangle(self.screen, 350, 350, 50, 50, Color('black'), Color('red'), True, 30);
        polygon = Polygon(self.screen, 6, 450, 450, 50, 50, Color('black'), Color('red'), True, 30);

        self.objects = [rect, oval, triangle, polygon];



