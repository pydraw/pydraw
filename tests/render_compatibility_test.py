"""Temporary characterization tests for the rendering-backend rewrite.

These tests describe behavior at the boundary between pydraw and the visible
Tk widget. The raw Tk backend stores native top-left Canvas coordinates, which
must match public pydraw coordinates exactly.

Keep this module for the duration of the ``render-abstract`` work.  Once the
new backend is stable, its durable assertions can be folded into the normal
screen, object, and input suites.
"""

import os
import unittest

from pydraw import (
    Color,
    CustomPolygon,
    Image,
    Line,
    Location,
    Oval,
    Pen,
    Polygon,
    Rectangle,
    RoundedRectangle,
    Screen,
    Text,
    Triangle,
)


PNG = os.path.join(os.path.dirname(__file__), '..', 'images', 'earth.png')


class RenderCompatibilityTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.screen = Screen(320, 200, 'render compatibility')
        cls.screen.update()

    @classmethod
    def tearDownClass(cls):
        # Do not use Screen.exit(): it intentionally raises SystemExit.
        try:
            cls.screen._backend.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.screen.reset()
        self.screen.color(Color('white'))
        self.screen.update()

    def _widget_canvas(self):
        return self.screen._backend.canvas

    def _item_widget_coordinates(self, item):
        """Translate stored item coordinates into visible widget pixels."""

        canvas = self._widget_canvas()
        origin_x = canvas.canvasx(0)
        origin_y = canvas.canvasy(0)
        stored = self.screen._backend.canvas.coords(item)
        return [
            coordinate - (origin_x if index % 2 == 0 else origin_y)
            for index, coordinate in enumerate(stored)
        ]

    def _item_for(self, obj):
        render_id = getattr(obj, '_render_id', None)
        if render_id is not None:
            return self.screen._backend.item_for(render_id)
        return obj._ref

    def assertCoordinatesAlmostEqual(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for index, (actual_value, expected_value) in enumerate(zip(actual, expected)):
            self.assertAlmostEqual(
                actual_value,
                expected_value,
                places=7,
                msg=f'coordinate {index}: {actual_value} != {expected_value}',
            )

    @staticmethod
    def _flatten(locations):
        return [coordinate for location in locations for coordinate in location]

    def test_declared_screen_size_and_coordinate_extents(self):
        self.assertEqual(self.screen.width(), 320)
        self.assertEqual(self.screen.height(), 200)
        self.assertEqual(self.screen.center(), Location(160, 100))
        self.assertEqual(self.screen.top_left(), Location(0, 0))
        self.assertEqual(self.screen.bottom_right(), Location(320, 200))

        edge = Line(self.screen, 0, 0, 320, 200)
        self.screen.update()
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(
                self.screen._backend.item_for(edge._render_id)
            ),
            [0, 0, 320, 200],
        )

    def test_renderable_vertices_land_on_the_same_visible_pixels(self):
        shapes = (
            Rectangle(self.screen, 12, 18, 40, 30),
            RoundedRectangle(self.screen, 18, 62, 70, 38, radius=12),
            Oval(self.screen, 61, 22, 48, 36),
            Triangle(self.screen, 123, 27, 42, 39),
            Polygon(self.screen, 5, 177, 31, 44, 38),
            CustomPolygon(
                self.screen,
                [(235, 19), (301, 28), (286, 79), (247, 68)],
            ),
        )
        self.screen.update()

        for shape in shapes:
            with self.subTest(shape=type(shape).__name__):
                self.assertCoordinatesAlmostEqual(
                    self._item_widget_coordinates(self._item_for(shape)),
                    self._flatten(shape.vertices()),
                )

    def test_oval_wedges_preserve_polygon_rendering_intent(self):
        oval = Oval(self.screen, 20, 20, 80, 40)
        self.assertFalse(oval._render_node().render_as_polygon)

        oval.wedges(24)
        node = oval._render_node()

        self.assertTrue(node.render_as_polygon)
        self.assertEqual(len(node.points), 24)
        self.screen.update()
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(self._item_for(oval)),
            self._flatten(oval.vertices()),
        )

    def test_rounded_rectangle_uses_geometry_not_stroke_width(self):
        shape = RoundedRectangle(
            self.screen,
            20,
            20,
            100,
            50,
            Color('blue'),
            Color('red'),
            radius=16,
        )
        self.screen.update()

        item = self._item_for(shape)
        canvas = self._widget_canvas()
        self.assertGreater(len(shape.vertices()), 4)
        self.assertEqual(float(canvas.itemcget(item, 'width')), 1)
        self.assertEqual(
            canvas.winfo_rgb(canvas.itemcget(item, 'outline')),
            canvas.winfo_rgb('red'),
        )

    def test_movement_and_rotation_remain_pixel_exact(self):
        rectangle = Rectangle(self.screen, 20, 30, 40, 24)
        rectangle.move(17.5, 9.25)
        rectangle.rotate(90)
        self.screen.update()

        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(self._item_for(rectangle)),
            self._flatten(rectangle.vertices()),
        )

        line = Line(self.screen, 7.5, 11.25, 87.75, 91.5)
        line.move(13.25, 17.5)
        self.screen.update()
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(
                self.screen._backend.item_for(line._render_id)
            ),
            [20.75, 28.75, 101.0, 109.0],
        )

    def test_text_anchor_retains_its_current_pixel_placement(self):
        text = Text(self.screen, 'anchor', 12, 18)
        self.screen.update()

        # Text currently places its NW anchor one pixel left of its public x.
        # Preserve that visible behavior during the backend swap; changing it
        # should be an explicit API/rendering decision made after the rewrite.
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(self._item_for(text)),
            [11, 18],
        )

        text.moveto(101.5, 73.25)
        self.screen.update()
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(self._item_for(text)),
            [100.5, 73.25],
        )

    def test_image_and_pen_coordinates_land_on_visible_pixels(self):
        image = Image(self.screen, PNG, 23, 29, 40, 30)
        self.screen.update()
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(self._item_for(image)),
            [43, 44],
        )

        image.move(11.5, 7.25)
        self.screen.update()
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(self._item_for(image)),
            [54.5, 51.25],
        )

        pen = Pen(self.screen, 17.5, 21.25)
        pen.start()
        pen.moveto(88.75, 93.5)
        self.screen.update()
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(
                self.screen._backend.item_for(pen._ref)
            ),
            [17.5, 21.25, 88.75, 93.5],
        )

    def test_tk_rendering_options_match_public_state(self):
        self.screen.title('compatibility title')
        self.screen.color(Color('navy'))
        rectangle = Rectangle(
            self.screen,
            10,
            10,
            30,
            20,
            Color('red'),
            Color('yellow'),
        )
        line = Line(
            self.screen,
            10,
            40,
            100,
            40,
            Color('blue'),
            3,
            (4, 2),
        )
        self.screen.update()
        line_item = self.screen._backend.item_for(line._render_id)

        canvas = self._widget_canvas()
        self.assertEqual(self.screen._backend.root.title(), 'compatibility title')
        self.assertEqual(
            canvas.winfo_rgb(canvas.cget('background')),
            canvas.winfo_rgb('navy'),
        )
        rectangle_item = self._item_for(rectangle)
        self.assertEqual(
            canvas.winfo_rgb(canvas.itemcget(rectangle_item, 'fill')),
            canvas.winfo_rgb('red'),
        )
        self.assertEqual(
            canvas.winfo_rgb(canvas.itemcget(rectangle_item, 'outline')),
            canvas.winfo_rgb('yellow'),
        )
        self.assertEqual(
            canvas.winfo_rgb(canvas.itemcget(line_item, 'fill')),
            canvas.winfo_rgb('blue'),
        )
        self.assertEqual(float(canvas.itemcget(line_item, 'width')), 3)
        self.assertEqual(canvas.itemcget(line_item, 'dash'), '4 2')

        rectangle.visible(False)
        self.screen.update()
        self.assertEqual(canvas.itemcget(rectangle_item, 'state'), 'hidden')
        rectangle.visible(True)
        self.screen.update()
        self.assertEqual(canvas.itemcget(rectangle_item, 'state'), 'normal')

    def test_canvas_stacking_order_is_preserved(self):
        first = Rectangle(self.screen, 10, 10, 50, 50)
        second = Rectangle(self.screen, 20, 20, 50, 50)
        self.screen.update()
        canvas = self._widget_canvas()
        first_item = self._item_for(first)
        second_item = self._item_for(second)

        self.assertLess(canvas.find_all().index(first_item),
                        canvas.find_all().index(second_item))

        first.front()
        self.screen.update()
        self.assertGreater(canvas.find_all().index(first_item),
                           canvas.find_all().index(second_item))

        first.back()
        self.screen.update()
        self.assertLess(canvas.find_all().index(first_item),
                        canvas.find_all().index(second_item))

    def test_retained_line_lifecycle_and_legacy_stacking(self):
        rectangle = Rectangle(self.screen, 20, 20, 80, 60)
        line = Line(self.screen, 10, 10, 120, 90)
        self.screen.update()
        canvas = self._widget_canvas()
        line_item = self.screen._backend.item_for(line._render_id)
        rectangle_item = self._item_for(rectangle)

        line.back()
        self.screen.update()
        self.assertLess(canvas.find_all().index(line_item),
                        canvas.find_all().index(rectangle_item))

        line.front()
        self.screen.update()
        self.assertGreater(canvas.find_all().index(line_item),
                           canvas.find_all().index(rectangle_item))

        line.remove()
        self.screen.update()
        self.assertIsNone(self.screen._backend.item_for(line._render_id))

        self.screen.add(line)
        self.screen.update()
        self.assertIsNotNone(self.screen._backend.item_for(line._render_id))

    def test_pen_retains_and_clears_multiple_strokes(self):
        pen = Pen(self.screen, 10, 10)
        pen.start()
        pen.moveto(40, 40)
        pen.stop()
        first_id = pen._ref
        pen.start()
        pen.moveto(80, 30)
        second_id = pen._ref
        pen.color(Color('blue'))
        pen.width(5)
        self.screen.update()
        canvas = self._widget_canvas()

        for render_id in (first_id, second_id):
            item = self.screen._backend.item_for(render_id)
            self.assertIsNotNone(item)
            self.assertEqual(
                canvas.winfo_rgb(canvas.itemcget(item, 'fill')),
                canvas.winfo_rgb('blue'),
            )
            self.assertEqual(float(canvas.itemcget(item, 'width')), 5)

        pen.clear()
        self.screen.update()
        self.assertIsNone(self.screen._backend.item_for(first_id))
        self.assertIsNotNone(self.screen._backend.item_for(second_id))

    def test_widget_mouse_coordinates_round_trip_through_every_binding(self):
        received = []
        self.screen.registry.update({
            'mousemove': lambda location: received.append(('move', location)),
            'mousedown': lambda location, button: received.append(
                ('down', location, button)
            ),
            'mouseup': lambda location, button: received.append(
                ('up', location, button)
            ),
            'mousedrag': lambda location, button: received.append(
                ('drag', location, button)
            ),
        })
        self.screen._listen()
        canvas = self._widget_canvas()

        for x, y in ((1, 1), (25, 35), (160, 100), (300, 180)):
            received.clear()
            canvas.event_generate('<Motion>', x=x, y=y)
            canvas.event_generate('<Button-1>', x=x, y=y)
            canvas.event_generate('<Button1-ButtonRelease>', x=x, y=y)
            canvas.event_generate('<B1-Motion>', x=x, y=y)
            self.screen.update()

            expected = Location(x, y)
            self.assertEqual(received, [
                ('move', expected),
                ('down', expected, 1),
                ('up', expected, 1),
                ('drag', expected, 1),
            ])
            self.assertEqual(self.screen.mouse(), expected)

    def test_widget_key_events_reach_registered_handlers(self):
        received = []
        self.screen.registry.update({
            'keydown': lambda key: received.append(('down', str(key))),
            'keyup': lambda key: received.append(('up', str(key))),
        })
        self.screen._listen()
        canvas = self._widget_canvas()
        canvas.focus_force()
        self.screen.update()

        canvas.event_generate('<KeyPress-a>')
        canvas.event_generate('<KeyRelease-a>')
        self.screen.update()

        self.assertEqual(received, [('down', 'a'), ('up', 'a')])

    def test_update_processes_pending_tk_callbacks(self):
        callbacks = []
        self.screen._backend.root.after_idle(lambda: callbacks.append('idle'))

        self.assertEqual(callbacks, [])
        self.screen.update()
        self.assertEqual(callbacks, ['idle'])

    def test_loop_runs_tk_callbacks_until_quit(self):
        callbacks = []
        rectangle = Rectangle(self.screen, 10, 10, 20, 20)
        self.screen.update()

        def mutate():
            rectangle.move(13, 7)
            callbacks.append('mutated')
            self.screen._backend.root.after(5, finish_loop)

        def finish_loop():
            callbacks.append('finished')
            self.screen._backend.root.quit()

        self.screen._backend.root.after(1, mutate)
        self.screen.loop()

        self.assertEqual(callbacks, ['mutated', 'finished'])
        self.assertCoordinatesAlmostEqual(
            self._item_widget_coordinates(self._item_for(rectangle)),
            self._flatten(rectangle.vertices()),
        )


if __name__ == '__main__':
    unittest.main()
