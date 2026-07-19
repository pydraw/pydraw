"""
Objects Test: Exercises every callable signature on the Renderable API
(Rectangle, Oval, Triangle, Polygon) and their constructors.

Signatures that *should* work but currently raise due to the overload
dispatch gap (missing 8/9-arg forms) 
"""

import unittest
from pydraw.errors import *
from pydraw import Screen, Location, Color, Rectangle, Oval, Triangle, Polygon, CustomPolygon, Renderable

# Shapes that share the standard (x, y, w, h, ...) Renderable constructor.
SIMPLE_SHAPES = (Rectangle, Oval, Triangle)


def build(screen, Shape, x=100, y=100, w=50, h=50,
          color=Color('black'), border=Color('red'), fill=True, rotation=0, visible=True):
    """Construct a shape with the full argument list, handling Polygon's extra num_sides."""
    if Shape is Polygon:
        return Polygon(screen, 6, x, y, w, h, color, border, fill, rotation, visible)
    return Shape(screen, x, y, w, h, color, border, fill, rotation, visible)


class ConstructorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def test_simple_numeric_forms(self):
        loc = Location(150, 150)
        for Shape in SIMPLE_SHAPES:
            # (screen, x, y, w, h)
            obj = Shape(self.screen, 150, 150, 50, 50)
            self.assertIsInstance(obj, Renderable)
            self.assertEqual(obj.location(), loc)
            self.assertEqual(obj.width(), 50)
            self.assertEqual(obj.height(), 50)

            # (screen, x, y, w, h, color)
            obj = Shape(self.screen, 150, 150, 50, 50, Color('blue'))
            self.assertEqual(obj.color(), Color('blue'))

            # (screen, x, y, w, h, color, border)
            obj = Shape(self.screen, 150, 150, 50, 50, Color('blue'), Color('green'))
            self.assertEqual(obj.border(), Color('green'))

            # (screen, x, y, w, h, color, border, fill, rotation, visible)
            obj = Shape(self.screen, 150, 150, 50, 50, Color('blue'), Color('green'), False, 45, False)
            self.assertEqual(obj.fill(), False)
            self.assertEqual(obj.rotation(), 45)
            self.assertEqual(obj.visible(), False)

    def test_simple_location_forms(self):
        loc = Location(150, 150)
        for Shape in SIMPLE_SHAPES:
            # (screen, location, w, h)
            obj = Shape(self.screen, loc, 50, 50)
            self.assertIsInstance(obj, Renderable)
            self.assertEqual(obj.location(), loc)

            # (screen, location, w, h, color)
            obj = Shape(self.screen, loc, 50, 50, Color('blue'))
            self.assertEqual(obj.color(), Color('blue'))

            # (screen, location, w, h, color, border)
            obj = Shape(self.screen, loc, 50, 50, Color('blue'), Color('green'))
            self.assertEqual(obj.border(), Color('green'))

    def test_polygon_numeric_forms(self):
        loc = Location(150, 150)

        obj = Polygon(self.screen, 6, 150, 150, 50, 50)
        self.assertIsInstance(obj, Renderable)
        self.assertEqual(obj.location(), loc)
        self.assertEqual(len(obj.vertices()), 6)

        obj = Polygon(self.screen, 5, 150, 150, 50, 50, Color('blue'))
        self.assertEqual(obj.color(), Color('blue'))
        self.assertEqual(len(obj.vertices()), 5)

        obj = Polygon(self.screen, 6, 150, 150, 50, 50, Color('blue'), Color('green'))
        self.assertEqual(obj.border(), Color('green'))

        # Full form (screen, sides, x, y, w, h, color, border, fill, rotation, visible)
        obj = Polygon(self.screen, 8, 150, 150, 50, 50, Color('blue'), Color('green'), False, 45, False)
        self.assertEqual(obj.fill(), False)
        self.assertEqual(obj.rotation(), 45)
        self.assertEqual(obj.visible(), False)
        self.assertEqual(len(obj.vertices()), 8)

    def test_polygon_location_forms(self):
        loc = Location(150, 150)

        obj = Polygon(self.screen, 6, loc, 50, 50)
        self.assertEqual(obj.location(), loc)

        obj = Polygon(self.screen, 6, loc, 50, 50, Color('blue'))
        self.assertEqual(obj.color(), Color('blue'))

        obj = Polygon(self.screen, 6, loc, 50, 50, Color('blue'), Color('green'))
        self.assertEqual(obj.border(), Color('green'))

    def test_invalid_constructor(self):
        # A bogus argument type finds no matching signature.
        self.assertRaises(NotImplementedError, Rectangle, self.screen, 'x', 'y', 50, 50)


class MethodTest(unittest.TestCase):
    """Runs every Renderable method, in each of its valid call forms, across all shapes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def each(self):
        """Yield a freshly-built object of each shape type."""
        for Shape in SIMPLE_SHAPES + (Polygon,):
            self.screen.clear()
            yield build(self.screen, Shape)

    def test_position_getters(self):
        for obj in self.each():
            self.assertEqual(obj.x(), 100)
            self.assertEqual(obj.y(), 100)
            self.assertEqual(obj.location(), Location(100, 100))

    def test_x_y_setters(self):
        for obj in self.each():
            obj.x(200)
            self.assertEqual(obj.x(), 200)
            obj.y(250)
            self.assertEqual(obj.y(), 250)
            self.assertEqual(obj.location(), Location(200, 250))

    def test_move_forms(self):
        for obj in self.each():
            obj.move(10, 5)                       # two numbers
            self.assertEqual(obj.location(), Location(110, 105))
            obj.move((10, 5))                     # tuple
            self.assertEqual(obj.location(), Location(120, 110))
            obj.move(Location(1, 1))              # Location
            self.assertEqual(obj.location(), Location(121, 111))

    def test_moveto_forms(self):
        for obj in self.each():
            obj.moveto(300, 300)                  # two numbers
            self.assertEqual(obj.location(), Location(300, 300))
            obj.moveto((200, 200))                # tuple
            self.assertEqual(obj.location(), Location(200, 200))
            obj.moveto(Location(150, 150))        # Location
            self.assertEqual(obj.location(), Location(150, 150))

    def test_width_height(self):
        for obj in self.each():
            self.assertEqual(obj.width(), 50)
            self.assertEqual(obj.height(), 50)
            obj.width(75)
            obj.height(80)
            self.assertEqual(obj.width(), 75)
            self.assertEqual(obj.height(), 80)

    def test_center_getter(self):
        for obj in self.each():
            self.assertEqual(obj.center(), Location(125, 125))
            # centroid=True is a pure getter and must not move the object.
            before = obj.location().clone()
            self.assertIsInstance(obj.center(centroid=True), Location)
            self.assertEqual(obj.location(), before)

    def test_center_setter_forms(self):
        for obj in self.each():
            obj.center(400, 400)                  # two numbers
            self.assertEqual(obj.center(), Location(400, 400))
            obj.center(Location(300, 300))        # Location
            self.assertEqual(obj.center(), Location(300, 300))
            obj.center((250, 250))                # tuple
            self.assertEqual(obj.center(), Location(250, 250))

    def test_center_keyword_forms(self):
        for obj in self.each():
            obj.center(move_to=Location(400, 400))   # move_to keyword
            self.assertEqual(obj.center(), Location(400, 400))
            obj.center(x=300)                        # x keyword
            self.assertEqual(obj.center(), Location(300, 400))
            obj.center(y=250)                        # y keyword
            self.assertEqual(obj.center(), Location(300, 250))

    def test_rotation_and_rotate(self):
        for obj in self.each():
            self.assertEqual(obj.rotation(), 0)
            obj.rotation(30)
            self.assertEqual(obj.rotation(), 30)
            obj.rotate(5)
            self.assertEqual(obj.rotation(), 35)
            obj.rotate()                          # default 0 -> no change
            self.assertEqual(obj.rotation(), 35)

    def test_angleto_forms(self):
        for obj in self.each():
            self.assertIsInstance(obj.angleto(Location(200, 200)), float)
            self.assertIsInstance(obj.angleto((200, 200)), float)
            other = build(self.screen, Rectangle, x=300, y=300)
            self.assertIsInstance(obj.angleto(other), float)

    def test_lookat(self):
        for obj in self.each():
            obj.rotation(0)
            obj.lookat(Location(obj.center().x() + 100, obj.center().y()))
            self.assertAlmostEqual(obj.rotation(), 90)

    def test_forward_backward(self):
        for obj in self.each():
            obj.rotation(0)
            start = obj.location().clone()
            obj.forward(10)
            self.assertAlmostEqual(obj.y(), start.y() - 10)
            obj.backward(10)
            self.assertAlmostEqual(obj.y(), start.y())

    def test_color(self):
        for obj in self.each():
            self.assertEqual(obj.color(), Color('black'))
            obj.color(Color('gray'))
            self.assertEqual(obj.color(), Color('gray'))
            self.assertRaises(InvalidArgumentError, obj.color, 'not_a_color')

    def test_border_forms(self):
        for obj in self.each():
            self.assertEqual(obj.border(), Color('red'))
            obj.border(Color('blue'))                          # color only
            self.assertEqual(obj.border(), Color('blue'))
            obj.border(Color('green'), 4)                      # color + width
            self.assertEqual(obj.border(), Color('green'))
            self.assertEqual(obj.border_width(), 4)
            obj.border(Color('black'), fill=False)             # color + fill kwarg
            self.assertEqual(obj.border(), Color('black'))
            self.assertEqual(obj.fill(), False)

    def test_border_width(self):
        for obj in self.each():
            self.assertEqual(obj.border_width(), 1)
            obj.border_width(6)
            self.assertEqual(obj.border_width(), 6)

    def test_fill(self):
        for obj in self.each():
            self.assertEqual(obj.fill(), True)
            obj.fill(False)
            self.assertEqual(obj.fill(), False)

    def test_distance_forms(self):
        for obj in self.each():
            self.assertEqual(obj.distance(obj.center()), 0)
            self.assertAlmostEqual(obj.distance(obj.center().move(75, 75)), 106.066017, 4)
            other = build(self.screen, Rectangle, x=100, y=100)
            self.assertIsInstance(obj.distance(other), float)
            self.assertRaises(InvalidArgumentError, obj.distance, 'nope')

    def test_visible(self):
        for obj in self.each():
            self.assertEqual(obj.visible(), True)
            obj.visible(False)
            self.assertEqual(obj.visible(), False)

    def test_transform(self):
        for obj in self.each():
            self.assertEqual(obj.transform(), (50, 50, 0))
            obj.transform((100, 120, 36))
            self.assertEqual(obj.transform(), (100, 120, 36))
            self.assertEqual(obj.width(), 100)
            self.assertEqual(obj.height(), 120)
            self.assertEqual(obj.rotation(), 36)
            # Bad-length tuple is rejected.
            self.assertRaises(InvalidArgumentError, obj.transform, (1, 2))

    def test_clone(self):
        for obj in self.each():
            obj.color(Color('purple'))
            obj.rotation(15)
            clone = obj.clone()
            self.assertIsInstance(clone, type(obj))
            self.assertEqual(clone.width(), obj.width())
            self.assertEqual(clone.height(), obj.height())
            self.assertEqual(clone.color(), obj.color())
            self.assertEqual(clone.rotation(), obj.rotation())
            self.assertEqual(len(clone.vertices()), len(obj.vertices()))

    def test_vertices(self):
        for obj in self.each():
            verts = obj.vertices()
            self.assertIsInstance(verts, list)
            self.assertTrue(all(isinstance(v, Location) for v in verts))
            self.assertGreaterEqual(len(verts), 3)

    def test_bounds(self):
        for obj in self.each():
            bounds = obj.bounds()
            self.assertEqual(len(bounds), 3)
            self.assertIsInstance(bounds[0], Location)

    def test_contains_forms(self):
        for obj in self.each():
            center = obj.center()
            self.assertTrue(obj.contains(center.x(), center.y()))   # two numbers
            self.assertTrue(obj.contains(center))                   # Location
            self.assertTrue(obj.contains((center.x(), center.y()))) # tuple
            self.assertFalse(obj.contains(0, 0))

    def test_overlaps(self):
        for Shape in SIMPLE_SHAPES + (Polygon,):
            self.screen.clear()
            a = build(self.screen, Shape, x=0, y=0, w=100, h=100)
            near = build(self.screen, Shape, x=50, y=50, w=100, h=100)
            far = build(self.screen, Shape, x=500, y=500, w=20, h=20)
            self.assertTrue(a.overlaps(near))
            self.assertFalse(a.overlaps(far))


class CustomPolygonTest(unittest.TestCase):
    """
    CustomPolygon has a different constructor (an explicit vertex list) and
    overrides several methods, so it is tested separately from the standard
    Renderables.
    """

    SQUARE = [(100, 100), (200, 100), (200, 200), (100, 200)]

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def make(self, **kwargs):
        return CustomPolygon(self.screen, list(self.SQUARE), **kwargs)

    def test_construction(self):
        p = CustomPolygon(self.screen, list(self.SQUARE),
                          Color('black'), Color('red'), True, 0, True)
        self.assertIsInstance(p, Renderable)
        self.assertEqual(p.location(), Location(100, 100))
        self.assertEqual(p.x(), 100)
        self.assertEqual(p.y(), 100)
        self.assertEqual(p.width(), 100)
        self.assertEqual(p.height(), 100)
        self.assertEqual(p.color(), Color('black'))
        self.assertEqual(p.border(), Color('red'))
        self.assertEqual(p.fill(), True)
        self.assertEqual(p.visible(), True)
        self.assertEqual(p.rotation(), 0)
        self.assertEqual(len(p.vertices()), 4)

    def test_too_few_vertices(self):
        self.assertRaises(InvalidArgumentError, CustomPolygon, self.screen, [(0, 0), (1, 1)])

    def test_move_forms(self):
        p = self.make()
        p.move(10, 20)                       # two numbers
        self.assertEqual(p.location(), Location(110, 120))
        p.move((10, 20))                     # tuple
        self.assertEqual(p.location(), Location(120, 140))
        p.move(Location(5, 5))               # Location
        self.assertEqual(p.location(), Location(125, 145))

    def test_moveto_forms(self):
        p = self.make()
        p.moveto(300, 300)
        self.assertEqual(p.location(), Location(300, 300))
        p.moveto((200, 200))
        self.assertEqual(p.location(), Location(200, 200))
        p.moveto(Location(150, 150))
        self.assertEqual(p.location(), Location(150, 150))

    def test_width_height(self):
        p = self.make()
        p.width(200)
        p.height(150)
        self.assertEqual(p.width(), 200)
        self.assertEqual(p.height(), 150)

    def test_rotation_and_rotate(self):
        p = self.make()
        self.assertEqual(p.rotation(), 0)
        p.rotation(90)
        self.assertEqual(p.rotation(), 90)
        p.rotate(5)
        self.assertEqual(p.rotation(), 95)

    def test_color(self):
        p = self.make()
        p.color(Color('blue'))
        self.assertEqual(p.color(), Color('blue'))
        self.assertRaises(InvalidArgumentError, p.color, 'not_a_color')

    def test_border_and_fill(self):
        p = self.make()
        p.border(Color('green'))
        self.assertEqual(p.border(), Color('green'))
        p.fill(False)
        self.assertEqual(p.fill(), False)

    def test_visible(self):
        p = self.make()
        p.visible(False)
        self.assertEqual(p.visible(), False)

    def test_center_getter(self):
        p = self.make()
        self.assertEqual(p.center(), Location(150, 150))

    def test_move_is_exact(self):
        # move() uses a relative canvas move, so vertices track the delta exactly
        # (no 1px bounding-box rounding from canvas.moveto()).
        p = self.make()
        p.move(50, 50)
        self.assertEqual([(v.x(), v.y()) for v in p.vertices()],
                         [(150, 150), (250, 150), (250, 250), (150, 250)])

    def test_center_after_move(self):
        p = self.make()
        self.assertEqual(p.center(), Location(150, 150))
        p.move(50, 50)
        # center() is derived from the live vertices, so it tracks the move
        # exactly and stays consistent with vertices().
        verts = p.vertices()
        cx = sum(v.x() for v in verts) / len(verts)
        cy = sum(v.y() for v in verts) / len(verts)
        self.assertEqual(p.center(), Location(cx, cy))
        self.assertEqual(p.center(), Location(200, 200))

    def test_rotate_after_move_pivots_on_current_center(self):
        p = self.make()
        p.move(100, 100)
        before = p.center()
        p.rotate(90)
        after = p.center()
        # Rotation pivots around the current center, so the centroid is preserved.
        self.assertAlmostEqual(after.x(), before.x())
        self.assertAlmostEqual(after.y(), before.y())

    def test_vertices(self):
        p = self.make()
        verts = p.vertices()
        self.assertIsInstance(verts, list)
        self.assertEqual(len(verts), 4)
        self.assertTrue(all(isinstance(v, Location) for v in verts))

    def test_contains_forms(self):
        p = self.make()
        self.assertTrue(p.contains(150, 150))
        self.assertTrue(p.contains(Location(150, 150)))
        self.assertTrue(p.contains((150, 150)))
        self.assertFalse(p.contains(0, 0))

    def test_distance(self):
        p = self.make()
        self.assertEqual(p.distance(p.center()), 0)
        self.assertIsInstance(p.distance(Location(0, 0)), float)

    def test_overlaps(self):
        a = CustomPolygon(self.screen, [(0, 0), (100, 0), (100, 100), (0, 100)])
        near = CustomPolygon(self.screen, [(50, 50), (150, 50), (150, 150), (50, 150)])
        far = CustomPolygon(self.screen, [(500, 500), (520, 500), (510, 520)])
        self.assertTrue(a.overlaps(near))
        self.assertFalse(a.overlaps(far))

    def test_clone(self):
        p = self.make(color=Color('purple'))
        p.rotation(20)
        clone = p.clone()
        self.assertIsInstance(clone, CustomPolygon)
        self.assertEqual(len(clone.vertices()), len(p.vertices()))
        self.assertEqual(clone.color(), Color('purple'))

    def test_transform_getter(self):
        p = self.make()
        self.assertEqual(p.transform(), (100, 100, 0))

    def test_transform_set_unsupported(self):
        p = self.make()
        self.assertRaises(UnsupportedError, p.transform, (50, 50, 45))


class KnownGapsTest(unittest.TestCase):
    """
    Signatures that are intended to work but currently do not.

    These are marked expectedFailure so they document the desired behavior
    without failing the suite; each should flip to an unexpected success
    (and can then be promoted to a normal test) once fixed:

      * 8/9-arg constructor forms -> requires the overload dispatcher to
        honor default arguments.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    @unittest.expectedFailure
    def test_numeric_8_arg_form(self):
        # (screen, x, y, w, h, color, border, fill, rotation) -- omits visible
        obj = Rectangle(self.screen, 150, 150, 50, 50, Color('blue'), Color('green'), True, 30)
        self.assertEqual(obj.rotation(), 30)

    @unittest.expectedFailure
    def test_location_full_form(self):
        # (screen, location, w, h, color, border, fill, rotation, visible)
        obj = Rectangle(self.screen, Location(150, 150), 50, 50,
                        Color('blue'), Color('green'), True, 30, True)
        self.assertEqual(obj.rotation(), 30)


if __name__ == '__main__':
    unittest.main()
