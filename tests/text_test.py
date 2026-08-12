"""
Text Test: Exercises the full Text surface - every constructor form and every
public method, with a focus on exact (relative) movement.

Text rendering is retained and uses the Tk backend without requiring Pillow.
"""

import unittest
from unittest.mock import patch
from pydraw.errors import InvalidArgumentError, PydrawError, UnsupportedError
from pydraw import Screen, Location, Color, Text, Rectangle, Renderable


class TextConstructorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()

    def test_numeric_form(self):
        text = Text(self.screen, 'hello', 100, 120)
        self.assertIsInstance(text, Renderable)
        self.assertEqual(text.location(), Location(100, 120))
        self.assertEqual(text.text(), 'hello')
        self.assertGreater(text.width(), 0)
        self.assertGreater(text.height(), 0)

    def test_numeric_form_with_color(self):
        text = Text(self.screen, 'hi', 10, 10, Color('red'))
        self.assertEqual(text.color(), Color('red'))

    def test_location_form(self):
        text = Text(self.screen, 'hello', Location(100, 120))
        self.assertEqual(text.location(), Location(100, 120))

    def test_location_form_with_color(self):
        text = Text(self.screen, 'hi', Location(10, 10), Color('blue'))
        self.assertEqual(text.color(), Color('blue'))

    def test_keyword_styling(self):
        text = Text(self.screen, 'hi', 0, 0, font='Courier', size=24, align='center',
                    bold=True, italic=True, underline=True, strikethrough=True, rotation=15, visible=False)
        self.assertEqual(text.font(), 'Courier')
        self.assertEqual(text.size(), 24)
        self.assertEqual(text.align(), 'center')
        self.assertTrue(text.bold())
        self.assertTrue(text.italic())
        self.assertTrue(text.underline())
        self.assertTrue(text.strikethrough())
        self.assertEqual(text.rotation(), 15)
        self.assertFalse(text.visible())


class TextMethodTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.clear()
        self.text = Text(self.screen, 'hello', 200, 200)
        self.screen.update()

    def _item_for(self, text):
        return self.screen._backend.item_for(text._render_id)

    def test_text_getter_setter(self):
        self.assertEqual(self.text.text(), 'hello')
        self.text.text('changed')
        self.assertEqual(self.text.text(), 'changed')
        self.assertRaises(InvalidArgumentError, self.text.text, 123)

    def test_unchanged_text_skips_canvas_and_measurement_work(self):
        canvas = self.text._screen._canvas
        with patch.object(canvas, 'itemconfigure') as itemconfigure, \
                patch.object(self.text, '_update_coords') as update_coords:
            self.assertEqual(self.text.text('hello'), 'hello')

        itemconfigure.assert_not_called()
        update_coords.assert_not_called()

    def test_move_is_exact(self):
        # A relative move must shift the location by exactly the delta and shift
        # the canvas item by the same amount (no bbox-induced 1px drift).
        before = self.screen._canvas.coords(self._item_for(self.text))
        self.text.move(15, 25)
        self.screen.update()
        after = self.screen._canvas.coords(self._item_for(self.text))
        self.assertEqual(self.text.location(), Location(215, 225))
        self.assertEqual([round(b - a, 4) for a, b in zip(before, after)], [15, 25])

    def test_moveto_is_exact(self):
        self.text.moveto(300, 400)
        self.assertEqual(self.text.location(), Location(300, 400))

    def test_move_zero_is_noop(self):
        before = self.screen._canvas.coords(self._item_for(self.text))
        self.text.move(0, 0)
        self.assertEqual(self.screen._canvas.coords(self._item_for(self.text)), before)

    def test_dimensions_are_read_only(self):
        w, h = self.text.width(), self.text.height()
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    def test_color(self):
        self.text.color(Color('green'))
        self.assertEqual(self.text.color(), Color('green'))
        self.assertRaises(InvalidArgumentError, self.text.color, 'green')

    def test_font_and_size(self):
        self.text.font('Times')
        self.assertEqual(self.text.font(), 'Times')
        self.text.size(30)
        self.assertEqual(self.text.size(), 30)

    def test_align_valid_and_invalid(self):
        self.text.align('right')
        self.assertEqual(self.text.align(), 'right')
        self.assertRaises(PydrawError, self.text.align, 'sideways')

    def test_style_toggles(self):
        for setter, getter in (('bold', self.text.bold), ('italic', self.text.italic),
                               ('underline', self.text.underline), ('strikethrough', self.text.strikethrough)):
            getattr(self.text, setter)(True)
            self.assertTrue(getter())
            getattr(self.text, setter)(False)
            self.assertFalse(getter())

    def test_mutations_emit_one_retained_text_node(self):
        render_id = self.text._render_id
        self.text.text('updated')
        self.text.color(Color('purple'))
        self.text.font('Courier')
        self.text.size(22)
        self.text.align('center')
        self.text.bold(True)
        self.text.rotation(30)

        node = self.text._render_node()
        self.assertEqual(node.id, render_id)
        self.assertEqual(node.text, 'updated')
        self.assertEqual(node.color, Color('purple').rgb())
        self.assertEqual(node.font, 'Courier')
        self.assertEqual(node.size, 22)
        self.assertEqual(node.align, 'center')
        self.assertTrue(node.bold)
        self.assertEqual(node.rotation, 30)

    def test_rotation_and_rotate(self):
        self.text.rotation(45)
        self.assertEqual(self.text.rotation(), 45)
        self.text.rotate(15)
        self.assertEqual(self.text.rotation(), 60)

    def test_rotation_matches_constructor_on_canvas(self):
        # Constructor and .rotation() must yield the same canvas angle (getter can't catch a wrong sign).
        cv = self.screen._screen.cv
        constructed = Text(self.screen, 'A', 50, 150, rotation=45)
        rotated = Text(self.screen, 'B', 250, 150)
        rotated.rotation(45)
        self.screen.update()
        self.assertEqual(
            float(cv.itemcget(self._item_for(constructed), 'angle')),
            float(cv.itemcget(self._item_for(rotated), 'angle')),
        )

    def test_lookat_location(self):
        self.text.lookat(Location(400, 200))
        self.assertIsInstance(self.text.rotation(), (int, float))

    def test_lookat_object(self):
        target = Rectangle(self.screen, 400, 400, 10, 10)
        self.text.lookat(target)
        self.assertIsInstance(self.text.rotation(), (int, float))

    def test_lookat_invalid(self):
        self.assertRaises(InvalidArgumentError, self.text.lookat, 42)

    def test_center_getter(self):
        center = self.text.center()
        self.assertEqual(center, Location(self.text.x() + self.text.width() / 2,
                                          self.text.y() + self.text.height() / 2))

    def test_center_move_to(self):
        self.text.center(move_to=Location(400, 300))
        self.assertEqual(self.text.center(), Location(400, 300))

    def test_center_rejects_unknown_keywords(self):
        with self.assertRaises(InvalidArgumentError):
            self.text.center(horizontal=400)

    def test_vertices(self):
        verts = self.text.vertices()
        self.assertEqual(len(verts), 4)
        self.assertEqual(verts[0], Location(200, 200))

    def test_visible(self):
        self.text.visible(False)
        self.assertFalse(self.text.visible())
        self.text.visible(True)
        self.assertTrue(self.text.visible())

    def test_transform_getter_and_unsupported_setter(self):
        self.assertEqual(self.text.transform(), (self.text.width(), self.text.height(), self.text.rotation()))
        self.assertRaises(UnsupportedError, self.text.transform, (1, 2, 3))

    def test_clone(self):
        self.text.color(Color('purple'))
        self.text.size(22)
        self.text.bold(True)
        clone = self.text.clone()
        self.assertEqual(clone.text(), self.text.text())
        self.assertEqual(clone.color(), self.text.color())
        self.assertEqual(clone.size(), self.text.size())
        self.assertEqual(clone.bold(), self.text.bold())
        self.assertEqual(clone.location(), self.text.location())


if __name__ == '__main__':
    unittest.main()
