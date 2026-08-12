"""Integration tests for Screen state and its real Tk canvas."""

import unittest
from unittest import mock

from pydraw import Screen, Color, Location, Rectangle
from pydraw.backends.tk import TkBackend
from pydraw.errors import PydrawError
from pydraw.render import RenderBatch


class ScreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600, 'Custom Name')

    def setUp(self) -> None:
        self.screen.reset()
        self.screen.color(Color('white'))
        self.screen.title('Custom Name')

    def test_title_and_color_round_trip_to_tk(self):
        self.screen.title('Updated Name')
        self.screen.color(Color('red'))

        self.assertEqual(self.screen.title(), 'Updated Name')
        self.assertEqual(self.screen.color(), Color('red'))
        self.assertEqual(self.screen._backend.root.title(), 'Updated Name')
        self.assertEqual(
            self.screen._backend.canvas.winfo_rgb(
                self.screen._backend.canvas.cget('background')
            ),
            self.screen._backend.canvas.winfo_rgb('red'),
        )

    def test_platform_services_route_through_backend(self):
        with mock.patch.object(
                self.screen._backend, 'set_background_image') as picture, \
                mock.patch.object(self.screen._backend, 'resize') as resize, \
                mock.patch.object(
                    self.screen._backend, 'window_size', return_value=(810, 610)
                ) as window_size, \
                mock.patch.object(
                    self.screen._backend, 'canvas_size', return_value=(800, 600)
                ) as canvas_size, \
                mock.patch.object(
                    self.screen._backend, 'set_fullscreen'
                ) as set_fullscreen:
            self.screen.picture('background.gif')
            self.screen.resize(640, 480)
            self.assertEqual(self.screen.size(), (810, 610))
            self.assertEqual(
                (self.screen.width(), self.screen.height()),
                (800, 600),
            )
            self.screen.fullscreen(True)

        picture.assert_called_once_with('background.gif')
        resize.assert_called_once_with(640, 480)
        window_size.assert_called_once_with()
        self.assertEqual(canvas_size.call_count, 2)
        set_fullscreen.assert_called_once_with(True)

    def test_dialogs_and_screenshot_route_through_backend(self):
        with mock.patch.object(
                self.screen._backend, 'alert', return_value=True) as alert, \
                mock.patch.object(
                    self.screen._backend, 'prompt', return_value='Ada'
                ) as prompt, \
                mock.patch.object(self.screen._backend, 'listen') as listen, \
                mock.patch.object(
                    self.screen._backend, 'grab', return_value='frame.png'
                ) as grab:
            self.assertTrue(
                self.screen.alert('Continue?', 'Question', 'Yes', 'No')
            )
            self.assertEqual(self.screen.prompt('Name?', 'Student'), 'Ada')
            self.assertEqual(self.screen.grab('frame'), 'frame.png')

        alert.assert_called_once_with('Continue?', 'Question', 'Yes', 'No')
        prompt.assert_called_once_with('Name?', 'Student')
        listen.assert_called_once_with()
        grab.assert_called_once_with('frame.png')

    def test_uses_raw_tk_backend(self):
        self.assertIsInstance(self.screen._backend, TkBackend)

    def test_update_routes_through_backend(self):
        with mock.patch.object(
                self.screen._backend,
                'poll_events',
                wraps=self.screen._backend.poll_events) as poll_events, \
                mock.patch.object(
                    self.screen._backend,
                    'present',
                    wraps=self.screen._backend.present) as present:
            self.screen.update()

        poll_events.assert_called_once_with()
        self.assertIsInstance(present.call_args[0][0], RenderBatch)

    def test_geometry_helpers(self):
        self.assertEqual(self.screen.width(), 800)
        self.assertEqual(self.screen.height(), 600)
        self.assertEqual(self.screen.center(), Location(400, 300))
        self.assertEqual(self.screen.top_left(), Location(0, 0))
        self.assertEqual(self.screen.top_right(), Location(800, 0))
        self.assertEqual(self.screen.bottom_left(), Location(0, 600))
        self.assertEqual(self.screen.bottom_right(), Location(800, 600))

    def test_grid_is_screen_decoration_not_user_object(self):
        rect = Rectangle(self.screen, 10, 10, 20, 20)
        self.screen.grid(rows=3, cols=4, helpers=False)

        self.assertGreater(len(self.screen.gridlines()), 0)
        self.assertEqual(self.screen.objects(), (rect,))

        self.screen.toggle_grid(False)
        self.assertTrue(all(not line.visible() for line in self.screen.gridlines()))
        self.screen.toggle_grid(True)
        self.assertTrue(all(line.visible() for line in self.screen.gridlines()))

        self.screen.reset()
        self.assertEqual(self.screen.gridlines(), ())
        self.assertEqual(self.screen.objects(), ())

    def test_object_lifecycle_updates_registry_and_canvas(self):
        rect = Rectangle(self.screen, self.screen.width() / 2 - 25, self.screen.height() / 2 - 25, 50, 50)

        self.assertEqual(rect.x(), 375)
        self.assertEqual(rect.y(), 275)
        self.assertIn(rect, self.screen)
        self.assertEqual(self.screen.objects(), (rect,))
        self.screen.update()
        self.assertNotEqual(
            self.screen._backend.canvas.type(
                self.screen._backend.item_for(rect._render_id)
            ),
            '',
        )

        self.screen.remove(rect)
        self.screen.update()
        self.assertNotIn(rect, self.screen)
        self.assertIsNone(self.screen._backend.item_for(rect._render_id))

        self.screen.add(rect)
        self.screen.update()
        self.assertIn(rect, self.screen)
        with self.assertRaises(PydrawError):
            self.screen.add(rect)

    def test_update_flushes_object_changes_to_canvas(self):
        rect = Rectangle(self.screen, 20, 30, 40, 50, Color('blue'))
        rect.move(15, 25)

        self.screen.update()

        self.assertEqual(rect.location(), Location(35, 55))
        item = self.screen._backend.item_for(rect._render_id)
        self.assertEqual(
            self.screen._backend.canvas.winfo_rgb(
                self.screen._backend.canvas.itemcget(item, 'fill')
            ),
            self.screen._backend.canvas.winfo_rgb('blue'),
        )

    def test_reset_disables_input_before_removing_objects(self):
        rect = Rectangle(self.screen, 10, 10, 20, 20)
        events = []
        self.screen.registry['keydown'] = lambda key: events.append(key)
        original_remove = rect.remove

        def remove_during_queued_input():
            self.screen._keydown('q')
            original_remove()

        rect.remove = remove_during_queued_input
        self.screen.reset()

        self.assertEqual(events, [])
        self.assertEqual(self.screen.registry, {})
        self.assertEqual(self.screen.objects(), ())

    def test_exit_disables_input_before_destroying_screen(self):
        events = []
        self.screen.registry['keydown'] = lambda key: events.append(key)

        def clear_during_queued_input():
            self.screen._keydown('q')

        with mock.patch.object(
                self.screen._backend, 'close',
                side_effect=clear_during_queued_input), \
                self.assertRaises(SystemExit):
            self.screen.exit()

        self.assertEqual(events, [])
        self.assertEqual(self.screen.registry, {})


if __name__ == '__main__':
    unittest.main()
