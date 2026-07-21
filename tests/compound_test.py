"""
Compound Test: End-to-end coverage of CompoundObject - grouping objects and
moving, centering, coloring, adding/removing, z-ordering, and rotating them as a
unit.

(Rewritten from a manual sandbox script into real assertions.)
"""

import os
import unittest
from pydraw import Screen, Location, Color, Rectangle, Polygon, Triangle, Image
from pydraw.compound import CompoundObject
from pydraw.errors import *

IMAGES = os.path.join(os.path.dirname(__file__), '..', 'images')
PNG = os.path.join(IMAGES, 'earth.png')


class CompoundObjectTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def _pair(self):
        # Origins at (0,0) and (100,0) -> centroid at (50, 0).
        a = Rectangle(self.screen, 0, 0, 20, 20)
        b = Rectangle(self.screen, 100, 0, 20, 20)
        return a, b, CompoundObject(a, b)

    def test_construct_mixed_objects(self):
        poly = Polygon(self.screen, 5, 150, 50, 50, 50, Color('red'))
        tri = Triangle(self.screen, 50, 50, 50, 50)
        image = Image(self.screen, PNG, 100, 50, 50, 50)
        comp = CompoundObject(poly, tri, image)
        self.assertEqual(len(comp.objects()), 3)

    def test_requires_at_least_one_object(self):
        self.assertRaises(InvalidArgumentError, CompoundObject)

    def test_rejects_non_object(self):
        self.assertRaises(InvalidArgumentError, CompoundObject, 42)

    def test_move_translates_all_children(self):
        a, b, comp = self._pair()
        comp.move(5, 5)
        self.assertEqual(a.location(), Location(5, 5))
        self.assertEqual(b.location(), Location(105, 5))

    def test_move_updates_tracked_bounds(self):
        # Regression: bounds used to be shifted once per child, multiplying the
        # delta. The bounding-box center must move by exactly the delta.
        a, b, comp = self._pair()
        # Bounding box spans the children's full extent: (0,0)-(120,20), center (60,10).
        self.assertEqual(comp.center(centroid=False), Location(60, 10))
        comp.move(5, 5)
        self.assertEqual(comp.center(centroid=False), Location(65, 15))

    def test_center_centroid(self):
        a, b, comp = self._pair()
        # centroid averages child origins: ((0+100)/2, (0+0)/2)
        self.assertEqual(comp.center(centroid=True), Location(50, 0))

    def test_color_applies_to_all(self):
        a, b, comp = self._pair()
        comp.color(Color('blue'))
        self.assertEqual(a.color(), Color('blue'))
        self.assertEqual(b.color(), Color('blue'))

    def test_add_and_object_lookup(self):
        a, b, comp = self._pair()
        c = Rectangle(self.screen, 200, 200, 20, 20)
        comp.add(c, name='third')
        self.assertEqual(len(comp.objects()), 3)
        self.assertIs(comp.object('third'), c)

    def test_remove(self):
        a, b, comp = self._pair()
        removed = comp.remove(a)
        self.assertIs(removed, a)
        self.assertEqual(len(comp.objects()), 1)

    def test_front_and_back_do_not_crash(self):
        # Regression: front()/back() used to iterate the dict's keys (strings)
        # and call .front() on a str.
        a, b, comp = self._pair()
        comp.front()
        comp.back()

    def _assert_at(self, obj, x, y):
        self.assertAlmostEqual(obj.x(), x)
        self.assertAlmostEqual(obj.y(), y)

    def test_rotate_around_centroid(self):
        # Rotating a group revolves each child's origin around the pivot (the
        # centroid by default) AND spins each child in place by the same angle.
        # Pivot = (50, 0). A 90 deg turn sends:
        #   (0,0)   -> (50, -50)
        #   (100,0) -> (50,  50)
        a, b, comp = self._pair()
        comp.rotate(90)

        self._assert_at(a, 50, -50)
        self._assert_at(b, 50, 50)
        self.assertAlmostEqual(a.rotation(), 90)
        self.assertAlmostEqual(b.rotation(), 90)
        self.assertAlmostEqual(comp.rotation(), 90)

    def test_rotate_full_circle_restores_positions(self):
        # A full revolution returns every child to where it started, and the
        # accumulated angle reads 360 (it does not wrap).
        a, b, comp = self._pair()
        comp.rotate(360)

        self._assert_at(a, 0, 0)
        self._assert_at(b, 100, 0)
        self.assertAlmostEqual(comp.rotation(), 360)

    def test_rotate_around_explicit_pivot(self):
        # 180 deg about the origin flips each child through (0,0):
        #   (0,0)   -> (0, 0)
        #   (100,0) -> (-100, 0)
        a, b, comp = self._pair()
        comp.rotate(180, pivot=Location(0, 0))

        self._assert_at(a, 0, 0)
        self._assert_at(b, -100, 0)

    def test_rotation_setter(self):
        a, b, comp = self._pair()
        comp.rotation(45)
        self.assertAlmostEqual(comp.rotation(), 45)


if __name__ == '__main__':
    unittest.main()
