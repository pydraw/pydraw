"""
Objects Test: Exercises every callable signature on the Renderable API
(Rectangle, Oval, Triangle, Polygon) and their constructors.

Signatures that *should* work but currently raise due to the overload
dispatch gap (missing 8/9-arg forms) 
"""

import unittest
from pydraw.errors import InvalidArgumentError
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

    def test_xy_forms(self):
        # (x, y) constructor at every positional arity from 5 to 10. Rectangle,
        # Oval and Triangle share this exact signature, so one loop covers all
        # three. Each arity asserts both the supplied values and that the omitted
        # trailing arguments fall back to their defaults.
        for Shape in SIMPLE_SHAPES:
            self.screen.clear()

            # 5: (screen, x, y, w, h) -- everything after height defaults
            obj = Shape(self.screen, 10, 20, 50, 60)
            self.assertIsInstance(obj, Renderable)
            self.assertEqual(obj.location(), Location(10, 20))
            self.assertEqual(obj.width(), 50)
            self.assertEqual(obj.height(), 60)
            self.assertEqual(obj.color(), Color('black'))
            self.assertEqual(obj.fill(), True)
            self.assertEqual(obj.rotation(), 0)
            self.assertEqual(obj.visible(), True)

            # 6: + color
            obj = Shape(self.screen, 10, 20, 50, 60, Color('blue'))
            self.assertEqual(obj.color(), Color('blue'))

            # 7: + border
            obj = Shape(self.screen, 10, 20, 50, 60, Color('blue'), Color('green'))
            self.assertEqual(obj.border(), Color('green'))

            # 8: + fill (rotation, visible still default)
            obj = Shape(self.screen, 10, 20, 50, 60, Color('blue'), Color('green'), False)
            self.assertEqual(obj.fill(), False)
            self.assertEqual(obj.rotation(), 0)
            self.assertEqual(obj.visible(), True)

            # 9: + rotation (visible still default)
            obj = Shape(self.screen, 10, 20, 50, 60, Color('blue'), Color('green'), True, 30)
            self.assertEqual(obj.rotation(), 30)
            self.assertEqual(obj.visible(), True)

            # 10: + visible (full form)
            obj = Shape(self.screen, 10, 20, 50, 60, Color('blue'), Color('green'), False, 45, False)
            self.assertEqual(obj.fill(), False)
            self.assertEqual(obj.rotation(), 45)
            self.assertEqual(obj.visible(), False)

    def test_kwargs_forms(self):
        # Dispatch is on positional args only; keyword arguments bind to the
        # optional tail of the selected overload afterwards. This must hold for
        # every positional arity, including the ones the default-honoring
        # dispatcher newly unlocked.
        for Shape in SIMPLE_SHAPES:
            # 5 positional + color kwarg
            obj = Shape(self.screen, 43, 43, 50, 50, color=Color('blue'))
            self.assertEqual(obj.color(), Color('blue'))
            self.assertEqual(obj.location(), Location(43, 43))

            # 6 positional (color) + visible kwarg
            obj = Shape(self.screen, 150, 75, 50, 50, Color('red'), visible=False)
            self.assertEqual(obj.color(), Color('red'))
            self.assertEqual(obj.visible(), False)

            # 7 positional (color, border) + fill kwarg
            obj = Shape(self.screen, 10, 10, 50, 50, Color('red'), Color('green'), fill=False)
            self.assertEqual(obj.border(), Color('green'))
            self.assertEqual(obj.fill(), False)

            # 5 positional + entire tail as kwargs
            obj = Shape(self.screen, 10, 10, 50, 50, color=Color('blue'),
                        border=Color('red'), rotation=30, visible=False)
            self.assertEqual(obj.color(), Color('blue'))
            self.assertEqual(obj.rotation(), 30)
            self.assertEqual(obj.visible(), False)

            # 8 positional (a newly-unlocked gap arity) + visible kwarg
            obj = Shape(self.screen, 10, 10, 50, 50, Color('red'), Color('green'), True, visible=False)
            self.assertEqual(obj.fill(), True)
            self.assertEqual(obj.visible(), False)

            # Location form + color kwarg
            obj = Shape(self.screen, Location(30, 40), 50, 50, color=Color('blue'))
            self.assertEqual(obj.location(), Location(30, 40))
            self.assertEqual(obj.color(), Color('blue'))

            # Location form, 8 positional + visible kwarg
            obj = Shape(self.screen, Location(30, 40), 50, 50,
                        Color('red'), Color('green'), True, 30, visible=False)
            self.assertEqual(obj.rotation(), 30)
            self.assertEqual(obj.visible(), False)

    def test_required_args_must_be_positional(self):
        # Dispatch counts only positional args, so passing the required geometry
        # arguments as keywords leaves nothing to match on. (Pre-existing
        # behavior, unchanged by default-honoring.)
        self.assertRaises(NotImplementedError, Rectangle, self.screen,
                          x=43, y=43, width=50, height=50)

    def test_location_forms(self):
        # (location) constructor at every positional arity from 4 to 9, across
        # all three shapes. The 7/8/9-arg forms are only reachable once a shape
        # has a full Location overload (Phase 2 consolidation).
        for Shape in SIMPLE_SHAPES:
            self.screen.clear()
            loc = Location(10, 20)

            # 4: (screen, location, w, h)
            obj = Shape(self.screen, loc, 50, 60)
            self.assertIsInstance(obj, Renderable)
            self.assertEqual(obj.location(), loc)
            self.assertEqual(obj.width(), 50)
            self.assertEqual(obj.height(), 60)
            self.assertEqual(obj.color(), Color('black'))
            self.assertEqual(obj.rotation(), 0)
            self.assertEqual(obj.visible(), True)

            # 5: + color
            obj = Shape(self.screen, loc, 50, 60, Color('blue'))
            self.assertEqual(obj.color(), Color('blue'))

            # 6: + border
            obj = Shape(self.screen, loc, 50, 60, Color('blue'), Color('green'))
            self.assertEqual(obj.border(), Color('green'))

            # 7: + fill
            obj = Shape(self.screen, loc, 50, 60, Color('blue'), Color('green'), False)
            self.assertEqual(obj.fill(), False)

            # 8: + rotation
            obj = Shape(self.screen, loc, 50, 60, Color('blue'), Color('green'), True, 30)
            self.assertEqual(obj.rotation(), 30)

            # 9: + visible (full form)
            obj = Shape(self.screen, loc, 50, 60, Color('blue'), Color('green'), True, 30, False)
            self.assertEqual(obj.visible(), False)

    def test_polygon_numeric_forms(self):
        # Polygon's (num_sides, x, y) form at every positional arity from 6 to 11.
        # 6: (screen, sides, x, y, w, h)
        obj = Polygon(self.screen, 6, 10, 20, 50, 60)
        self.assertIsInstance(obj, Renderable)
        self.assertEqual(obj.location(), Location(10, 20))
        self.assertEqual(len(obj.vertices()), 6)
        self.assertEqual(obj.color(), Color('black'))
        self.assertEqual(obj.rotation(), 0)
        self.assertEqual(obj.visible(), True)

        # 7: + color
        obj = Polygon(self.screen, 5, 10, 20, 50, 60, Color('blue'))
        self.assertEqual(obj.color(), Color('blue'))
        self.assertEqual(len(obj.vertices()), 5)

        # 8: + border
        obj = Polygon(self.screen, 6, 10, 20, 50, 60, Color('blue'), Color('green'))
        self.assertEqual(obj.border(), Color('green'))

        # 9: + fill
        obj = Polygon(self.screen, 6, 10, 20, 50, 60, Color('blue'), Color('green'), False)
        self.assertEqual(obj.fill(), False)
        self.assertEqual(obj.rotation(), 0)

        # 10: + rotation
        obj = Polygon(self.screen, 6, 10, 20, 50, 60, Color('blue'), Color('green'), True, 30)
        self.assertEqual(obj.rotation(), 30)
        self.assertEqual(obj.visible(), True)

        # 11: + visible (full form)
        obj = Polygon(self.screen, 8, 10, 20, 50, 60, Color('blue'), Color('green'), False, 45, False)
        self.assertEqual(obj.fill(), False)
        self.assertEqual(obj.rotation(), 45)
        self.assertEqual(obj.visible(), False)
        self.assertEqual(len(obj.vertices()), 8)

    def test_polygon_location_forms(self):
        # Polygon's (num_sides, location) form at every positional arity 5 to 10.
        loc = Location(10, 20)

        # 5: (screen, sides, location, w, h)
        obj = Polygon(self.screen, 6, loc, 50, 60)
        self.assertEqual(obj.location(), loc)
        self.assertEqual(len(obj.vertices()), 6)

        # 6: + color
        obj = Polygon(self.screen, 6, loc, 50, 60, Color('blue'))
        self.assertEqual(obj.color(), Color('blue'))

        # 7: + border
        obj = Polygon(self.screen, 6, loc, 50, 60, Color('blue'), Color('green'))
        self.assertEqual(obj.border(), Color('green'))

        # 8: + fill
        obj = Polygon(self.screen, 6, loc, 50, 60, Color('blue'), Color('green'), False)
        self.assertEqual(obj.fill(), False)

        # 9: + rotation
        obj = Polygon(self.screen, 6, loc, 50, 60, Color('blue'), Color('green'), True, 30)
        self.assertEqual(obj.rotation(), 30)

        # 10: + visible (full form)
        obj = Polygon(self.screen, 6, loc, 50, 60, Color('blue'), Color('green'), True, 30, False)
        self.assertEqual(obj.visible(), False)

    def test_polygon_kwargs_forms(self):
        # num_sides is positional; the optional tail binds by keyword.
        obj = Polygon(self.screen, 6, 10, 20, 50, 60, color=Color('blue'))
        self.assertEqual(obj.color(), Color('blue'))
        self.assertEqual(len(obj.vertices()), 6)

        obj = Polygon(self.screen, 5, Location(10, 20), 50, 60, Color('red'), visible=False)
        self.assertEqual(obj.color(), Color('red'))
        self.assertEqual(obj.visible(), False)
        self.assertEqual(len(obj.vertices()), 5)

    def test_polygon_requires_at_least_three_sides(self):
        for num_sides in (0, 1, 2, -1):
            with self.subTest(num_sides=num_sides):
                with self.assertRaises(InvalidArgumentError):
                    Polygon(self.screen, num_sides, 0, 0, 100, 100)

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

    def test_center_rejects_unknown_keywords(self):
        for obj in self.each():
            with self.assertRaises(InvalidArgumentError):
                obj.center(horizontal=300)

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

        asymmetric = CustomPolygon(
            self.screen,
            [(100, 100), (200, 100), (100, 200)],
        )
        self.assertEqual(asymmetric.center(), Location(150, 150))
        self.assertEqual(
            asymmetric.center(centroid=True),
            Location(400 / 3, 400 / 3),
        )

    def test_center_setter_uses_selected_center(self):
        p = CustomPolygon(
            self.screen,
            [(100, 100), (200, 100), (100, 200)],
        )

        p.center(300, 400)
        self.assertEqual(p.center(), Location(300, 400))

        p.center(500, 600, centroid=True)
        centroid = p.center(centroid=True)
        self.assertAlmostEqual(centroid.x(), 500)
        self.assertAlmostEqual(centroid.y(), 600)

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

    def test_center_rejects_unknown_keywords(self):
        p = self.make()
        with self.assertRaises(InvalidArgumentError):
            p.center(horizontal=300)

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

    def assertVerticesAlmostEqual(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for actual_vertex, expected_vertex in zip(actual, expected):
            self.assertAlmostEqual(actual_vertex.x(), expected_vertex.x())
            self.assertAlmostEqual(actual_vertex.y(), expected_vertex.y())

    def test_constructor_rotation_is_applied_to_geometry(self):
        constructed_rotated = self.make(rotation=20)
        rotated_after_construction = self.make()
        rotated_after_construction.rotation(20)

        self.assertVerticesAlmostEqual(
            constructed_rotated.vertices(), rotated_after_construction.vertices()
        )

    def test_repeated_rotation_does_not_accumulate_absolute_angle(self):
        incremental = self.make()
        incremental.rotate(10)
        incremental.rotate(10)

        single = self.make()
        single.rotate(20)

        self.assertEqual(incremental.rotation(), 20)
        self.assertVerticesAlmostEqual(incremental.vertices(), single.vertices())

    def test_resizing_rotated_polygon_does_not_rotate_it_again(self):
        rotate_then_resize = self.make()
        rotate_then_resize.rotate(20)
        rotate_then_resize.width(200)

        resize_then_rotate = self.make()
        resize_then_rotate.width(200)
        resize_then_rotate.rotate(20)

        self.assertVerticesAlmostEqual(
            rotate_then_resize.vertices(), resize_then_rotate.vertices()
        )

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

    def test_clone_preserves_live_geometry(self):
        p = self.make(color=Color('purple'))
        p.move(75, 40)
        p.width(160)
        p.height(80)
        clone = p.clone()

        self.assertEqual(clone.location(), p.location())
        self.assertEqual(clone.width(), p.width())
        self.assertEqual(clone.height(), p.height())
        self.assertVerticesAlmostEqual(clone.vertices(), p.vertices())

    def test_transform_getter(self):
        p = self.make()
        self.assertEqual(p.transform(), (100, 100, 0))

    def test_transform_setter(self):
        p = self.make()
        original_ref = p._ref
        p.transform((50, 75, 45))

        self.assertEqual(p.transform(), (50, 75, 45))
        self.assertEqual(p.location(), Location(100, 100))
        self.assertEqual(p._ref, original_ref)

        expected = self.make()
        expected.width(50)
        expected.height(75)
        expected.rotation(45)
        self.assertVerticesAlmostEqual(p.vertices(), expected.vertices())


if __name__ == '__main__':
    unittest.main()
