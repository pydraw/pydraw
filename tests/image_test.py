"""
Image Test: Exercises the full Image surface - every constructor form (x/y and
location, every arity, plus kwargs) and every public method.

PNG assets are tkinter-native so most tests need no PIL/Pillow. Image mutation
(width/height/color/border/rotation/frames) routes through PIL, so those tests
are skipped when Pillow is not installed.
"""

import builtins
import os
import unittest
from unittest.mock import patch
from pydraw.errors import InvalidArgumentError, PydrawError, UnsupportedError
from pydraw import Screen, Location, Color, Image, Renderable

IMAGES = os.path.join(os.path.dirname(__file__), '..', 'images')
PNG = os.path.join(IMAGES, 'earth.png')        # tkinter-native (no PIL required)
JPG = os.path.join(IMAGES, 'cool_barry.jpg')   # requires PIL/Pillow

try:
    import PIL  # noqa: F401
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ImageConstructorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def test_xy_forms(self):
        # (x, y) form at every positional arity from 2 (just screen + path) to 10.
        # Only screen and the path are required; everything else defaults.
        img = Image(self.screen, PNG)                       # 2
        self.assertIsInstance(img, Renderable)
        self.assertGreater(img.width(), 0)
        self.assertGreater(img.height(), 0)

        img = Image(self.screen, PNG, 100, 120)             # 4: + x, y
        self.assertEqual(img.location(), Location(100, 120))

        img = Image(self.screen, PNG, 100, 120, 60, 40)     # 6: + width, height
        self.assertEqual(img.width(), 60)
        self.assertEqual(img.height(), 40)

        img = Image(self.screen, PNG, 100, 120, 60, 40, Color('magenta'))          # 7: + color
        self.assertEqual(img.color(), Color('magenta'))

        img = Image(self.screen, PNG, 100, 120, 60, 40,
                    Color('magenta'), Color('green'))                              # 8: + border
        self.assertEqual(img.border(), Color('green'))

        img = Image(self.screen, PNG, 100, 120, 60, 40,
                    Color('magenta'), Color('green'), 30)                          # 9: + rotation
        self.assertEqual(img.rotation(), 30)

        img = Image(self.screen, PNG, 100, 120, 60, 40,
                    Color('magenta'), Color('green'), 30, False)                   # 10: full
        self.assertEqual(img.visible(), False)

    def test_location_forms(self):
        # (location) form at every positional arity from 3 to 9.
        loc = Location(100, 120)

        img = Image(self.screen, PNG, loc)                  # 3
        self.assertEqual(img.location(), loc)

        img = Image(self.screen, PNG, loc, 60, 40)          # 5: + width, height
        self.assertEqual(img.width(), 60)
        self.assertEqual(img.height(), 40)

        img = Image(self.screen, PNG, loc, 60, 40, Color('magenta'))              # 6: + color
        self.assertEqual(img.color(), Color('magenta'))

        img = Image(self.screen, PNG, loc, 60, 40,
                    Color('magenta'), Color('green'), 30, False)                  # 9: full
        self.assertEqual(img.rotation(), 30)
        self.assertEqual(img.visible(), False)

    def test_kwargs_forms(self):
        img = Image(self.screen, PNG, 100, 100, 60, 40, rotation=45)
        self.assertEqual(img.rotation(), 45)

        img = Image(self.screen, PNG, Location(100, 100), visible=False)
        self.assertEqual(img.visible(), False)

        img = Image(self.screen, PNG, 100, 100, width=70, height=30)
        self.assertEqual(img.width(), 70)
        self.assertEqual(img.height(), 30)

    def test_natural_size(self):
        # Omitting width/height falls back to the image's own dimensions.
        img = Image(self.screen, PNG)
        self.assertGreater(img.width(), 1)
        self.assertGreater(img.height(), 1)

    def test_png_loads_without_pillow(self):
        """PNG is documented as a tkinter-native format and must not import PIL."""
        real_import = builtins.__import__

        def import_without_pillow(name, *args, **kwargs):
            if name == 'PIL' or name.startswith('PIL.'):
                raise ImportError('Pillow intentionally unavailable for this test')
            return real_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=import_without_pillow):
            img = Image(self.screen, PNG)

        self.assertGreater(img.width(), 0)
        self.assertGreater(img.height(), 0)

    def test_missing_file(self):
        self.assertRaises(InvalidArgumentError, Image, self.screen,
                          os.path.join(IMAGES, 'does_not_exist.png'))

    def test_no_extension(self):
        self.assertRaises(PydrawError, Image, self.screen, 'noextension')

    @unittest.skipUnless(HAS_PIL, 'PIL/Pillow not installed')
    def test_jpg_via_pil(self):
        # Non-tkinter formats (e.g. JPG) load through PIL/Pillow.
        img = Image(self.screen, JPG, 100, 100, 50, 50)
        self.assertEqual(img.width(), 50)
        self.assertEqual(img.height(), 50)


class ImageMethodTest(unittest.TestCase):
    """Exercises every public Image method that does not require PIL."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()
        self.img = Image(self.screen, PNG, 100, 100, 50, 50)
        self.screen.update()

    def _item_for(self, image):
        return self.screen._backend.item_for(image._render_id)

    def test_location_and_xy_getters(self):
        self.assertEqual(self.img.location(), Location(100, 100))
        self.assertEqual(self.img.x(), 100)
        self.assertEqual(self.img.y(), 100)

    def test_x_setter_moves(self):
        self.img.x(200)
        self.assertEqual(self.img.location(), Location(200, 100))

    def test_y_setter_moves(self):
        self.img.y(250)
        self.assertEqual(self.img.location(), Location(100, 250))

    def test_move_is_exact(self):
        # A relative move must shift the location by exactly the delta (no
        # doubling) and shift the canvas item by the same amount.
        before = self.screen._backend.canvas.coords(self._item_for(self.img))
        image_ref = self.screen._backend.image_refs[self.img._render_id]
        self.img.move(30, -20)
        self.screen.update()
        after = self.screen._backend.canvas.coords(self._item_for(self.img))
        self.assertEqual(self.img.location(), Location(130, 80))
        self.assertEqual([round(b - a, 4) for a, b in zip(before, after)], [30, -20])
        self.assertIs(
            self.screen._backend.image_refs[self.img._render_id],
            image_ref,
        )

    def test_moveto_is_exact(self):
        self.img.moveto(300, 250)
        self.assertEqual(self.img.location(), Location(300, 250))

    def test_move_zero_is_noop(self):
        before = self.screen._backend.canvas.coords(self._item_for(self.img))
        self.img.move(0, 0)
        self.assertEqual(
            self.screen._backend.canvas.coords(self._item_for(self.img)),
            before,
        )

    def test_vertices(self):
        verts = self.img.vertices()
        self.assertEqual(len(verts), 4)
        self.assertIn(Location(100, 100), verts)
        self.assertIn(Location(150, 150), verts)

    def test_vertices_not_aliased(self):
        # vertices() must not hand out the live internal location, otherwise a
        # move would shift it twice (once via _location, once via the vertex
        # cache) and double the displacement.
        self.assertIsNot(self.img.vertices()[0], self.img._location)
        self.img.vertices()[0].move(1000, 1000)
        self.assertEqual(self.img.location(), Location(100, 100))

    def test_center_getter(self):
        self.assertEqual(self.img.center(), Location(125, 125))

    def test_center_move_to(self):
        self.img.center(move_to=Location(400, 300))
        self.assertEqual(self.img.center(), Location(400, 300))
        self.assertEqual(self.img.location(), Location(375, 275))

    def test_center_rejects_unknown_keywords(self):
        with self.assertRaises(InvalidArgumentError):
            self.img.center(horizontal=400)

    def test_contains(self):
        self.assertTrue(self.img.contains(Location(120, 120)))
        self.assertFalse(self.img.contains(Location(500, 500)))

    def test_distance(self):
        other = Image(self.screen, PNG, 100, 100, 50, 50)
        other.moveto(103, 104)
        self.assertAlmostEqual(self.img.distance(other), 5.0)

    def test_transform_getter(self):
        self.assertEqual(self.img.transform(), (50, 50, 0))

    def test_visible_setter(self):
        self.assertTrue(self.img.visible())
        self.img.visible(False)
        self.assertFalse(self.img.visible())

    def test_fill_unsupported(self):
        self.assertRaises(UnsupportedError, self.img.fill, True)

    def test_frames_default(self):
        # A non-animated image reports -1 frames.
        self.assertEqual(self.img.frames(), -1)

    def test_remove(self):
        self.img.remove()
        self.assertNotIn(self.img, self.screen.objects())


@unittest.skipUnless(HAS_PIL, 'PIL/Pillow not installed')
class ImagePILMethodTest(unittest.TestCase):
    """Exercises Image methods that mutate the bitmap and therefore need PIL."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()
        self.img = Image(self.screen, PNG, 100, 100, 50, 50)

    def test_width_setter(self):
        self.img.width(80)
        self.assertEqual(self.img.width(), 80)

    def test_height_setter(self):
        self.img.height(30)
        self.assertEqual(self.img.height(), 30)

    def test_color_mask(self):
        self.img.color(Color('red'))
        self.assertEqual(self.img.color(), Color('red'))

    def test_border_setter(self):
        self.img.border(Color('blue'))
        self.assertEqual(self.img.border(), Color('blue'))

    def test_rotation_setter(self):
        self.img.rotation(30)
        self.assertEqual(self.img.rotation(), 30)

    def test_rotate(self):
        self.img.rotation(10)
        self.img.rotate(20)
        self.assertEqual(self.img.rotation(), 30)

    def test_transform_setter(self):
        self.img.transform((70, 40, 15))
        self.assertEqual(self.img.transform(), (70, 40, 15))

    def test_flip_toggles_and_persists_axis_state(self):
        self.assertIsNone(self.img.flip('x'))
        self.assertTrue(self.img._flip_x)
        self.assertFalse(self.img._flip_y)

        self.img.width(80)
        self.assertTrue(self.img._flip_x)

        self.img.flip('x')
        self.assertFalse(self.img._flip_x)

        self.img.flip('Y')
        self.assertTrue(self.img._flip_y)

    def test_flip_rejects_invalid_axis(self):
        self.assertRaises(InvalidArgumentError, self.img.flip, 'z')
        self.assertRaises(InvalidArgumentError, self.img.flip, 1)

    def test_clone_preserves_dimensions(self):
        # Regression: clone() used to swap width/height into the constructor.
        clone = self.img.clone()
        self.assertEqual(clone.width(), self.img.width())
        self.assertEqual(clone.height(), self.img.height())
        self.assertEqual(clone.location(), self.img.location())
        self.assertEqual(clone.visible(), self.img.visible())

    def test_clone_preserves_flip_state(self):
        self.img.flip('x')
        self.img.flip('y')
        clone = self.img.clone()

        self.assertTrue(clone._flip_x)
        self.assertTrue(clone._flip_y)

    def test_combined_transform_presents_through_backend(self):
        self.img.transform((80, 40, 25))
        self.img.color(Color('purple'), 100)
        self.img.border(Color('blue'))
        self.img.flip('y')
        self.img.smooth(False)
        self.screen.update()

        node = self.img._render_node()
        self.assertEqual(node.tint, Color('purple').rgb())
        self.assertEqual(node.tint_alpha, 100)
        self.assertEqual(node.border, Color('blue').rgb())
        self.assertTrue(node.flip_y)
        self.assertFalse(node.smooth)
        self.assertIsNotNone(
            self.screen._backend.item_for(self.img._render_id)
        )


if __name__ == '__main__':
    unittest.main()
