"""
Integration coverage of CompoundObject - grouping objects and
moving, centering, coloring, adding/removing, z-ordering, and rotating them as a
unit.

(Rewritten from a manual sandbox script into real assertions.)
"""

import os
import unittest
from pydraw import Screen, Location, Color, Rectangle, Polygon, Triangle, Image
from pydraw.compound import CompoundObject
from pydraw.errors import InvalidArgumentError

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

    def test_moveto_translates_children_and_bounds_once(self):
        a, b, comp = self._pair()
        comp.moveto(50, 75)
        self.assertEqual(a.location(), Location(50, 75))
        self.assertEqual(b.location(), Location(150, 75))
        self.assertEqual(comp.x(), 50)
        self.assertEqual(comp.y(), 75)

    def test_center_centroid(self):
        a, b, comp = self._pair()
        # The compound centroid averages the centers around which its children
        # rotate: ((10+110)/2, (10+10)/2).
        self.assertEqual(comp.center(centroid=True), Location(60, 10))

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

    def test_remove_unknown_entry_returns_none(self):
        a, b, comp = self._pair()

        self.assertIs(comp.remove(a), a)
        self.assertIsNone(comp.remove(a))
        self.assertIsNone(comp.remove(name='missing'))
        self.assertEqual(comp.objects(), (b,))

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
        # Rotating a group revolves each child's center around the pivot AND
        # spins each child in place by the same angle. Pivot = (60, 10). Since
        # both children have the same dimensions, their anchors land at:
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
        # 180 deg about the origin flips all of each child's geometry through
        # (0,0), so their top-left anchors account for their dimensions:
        #   (0,0)   -> (-20, -20)
        #   (100,0) -> (-120, -20)
        a, b, comp = self._pair()
        comp.rotate(180, pivot=Location(0, 0))

        self._assert_at(a, -20, -20)
        self._assert_at(b, -120, -20)

    def test_rotate_unequal_children_as_rigid_body(self):
        # Regression: rotating top-left anchors while spinning each child about
        # its center deformed compounds containing differently sized objects.
        a = Rectangle(self.screen, 0, 0, 20, 40)
        b = Rectangle(self.screen, 100, 0, 60, 20)
        comp = CompoundObject(a, b)

        # Child centers are (10,20) and (130,10), so the compound pivot is
        # (70,15). A 90 degree rotation moves those centers to (65,-45) and
        # (75,75), respectively.
        pivot = comp.center()
        comp.rotate(90)

        self.assertEqual(pivot, Location(70, 15))
        self._assert_at(a, 55, -65)
        self._assert_at(b, 45, 65)
        self._assert_at(comp.center(), pivot.x(), pivot.y())
        self.assertAlmostEqual(comp.width(), 40)
        self.assertAlmostEqual(comp.height(), 160)

    def test_rotate_then_inverse_restores_unequal_children(self):
        a = Rectangle(self.screen, 5, 15, 20, 40, rotation=17)
        b = Rectangle(self.screen, 100, 30, 60, 20, rotation=-23)
        comp = CompoundObject(a, b)
        originals = [(obj.location().clone(), obj.rotation()) for obj in (a, b)]

        comp.rotate(37)
        comp.rotate(-37)

        for obj, (location, rotation) in zip((a, b), originals):
            self._assert_at(obj, location.x(), location.y())
            self.assertAlmostEqual(obj.rotation(), rotation)

    def test_rotation_setter(self):
        a, b, comp = self._pair()
        comp.rotation(45)
        self.assertAlmostEqual(comp.rotation(), 45)


if __name__ == '__main__':
    unittest.main()
