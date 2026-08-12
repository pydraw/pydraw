"""Characterize public input and event-loop behavior during backend migration."""

import contextlib
import io
import unittest
from unittest import mock

from pydraw import Location, Rectangle, Screen
from pydraw.errors import PydrawError


class InputCompatibilityTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.screen = Screen(320, 200, 'input compatibility')
        cls.screen.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.screen._backend.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.screen.reset()
        self.screen.update()

    def _canvas(self):
        return self.screen._backend.canvas

    def test_pointer_event_order_coordinates_and_buttons(self):
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
        canvas = self._canvas()

        for button in (1, 2, 3):
            x = 20 + button * 30
            y = 15 + button * 20
            canvas.event_generate('<Motion>', x=x, y=y)
            canvas.event_generate(f'<Button-{button}>', x=x, y=y)
            canvas.event_generate(
                f'<Button{button}-ButtonRelease>', x=x, y=y
            )
            canvas.event_generate(f'<B{button}-Motion>', x=x, y=y)

        self.screen.update()

        expected = []
        for button in (1, 2, 3):
            location = Location(20 + button * 30, 15 + button * 20)
            expected.extend((
                ('move', location),
                ('down', location, button),
                ('up', location, button),
                ('drag', location, button),
            ))
        self.assertEqual(received, expected)
        self.assertEqual(self.screen.mouse(), Location(110, 75))

    def test_printable_and_special_keys_are_normalized_in_order(self):
        received = []
        self.screen.registry.update({
            'keydown': lambda key: received.append(('down', str(key))),
            'keyup': lambda key: received.append(('up', str(key))),
        })
        self.screen._listen()
        canvas = self._canvas()
        canvas.focus_force()
        self.screen.update()

        for key in ('A', 'Left', 'Return', 'space'):
            canvas.event_generate(f'<KeyPress-{key}>')
            canvas.event_generate(f'<KeyRelease-{key}>')
        self.screen.update()

        self.assertEqual(received, [
            ('down', 'a'),
            ('up', 'a'),
            ('down', 'left'),
            ('up', 'left'),
            ('down', 'return'),
            ('up', 'return'),
            ('down', 'space'),
            ('up', 'space'),
        ])

    def test_input_callback_mutation_is_presented_by_the_same_update(self):
        rectangle = Rectangle(self.screen, 10, 10, 20, 20)
        self.screen.update()
        order = []
        frames = []

        def mousedown(location, button):
            order.append('callback')
            rectangle.moveto(location)

        self.screen.registry['mousedown'] = mousedown
        self.screen._listen()
        canvas = self._canvas()
        poll_events = self.screen._backend.poll_events
        present = self.screen._backend.present

        def recording_poll():
            order.append('poll')
            return poll_events()

        def recording_present(frame):
            order.append('present')
            frames.append(frame)
            return present(frame)

        with mock.patch.object(
                self.screen._backend, 'poll_events', recording_poll), \
                mock.patch.object(
                    self.screen._backend, 'present', recording_present):
            self.screen._backend.root.after_idle(
                lambda: canvas.event_generate('<Button-1>', x=70, y=80)
            )
            self.screen.update()

        self.assertEqual(order, ['poll', 'callback', 'present'])
        self.assertEqual(rectangle.location(), Location(70, 80))
        self.assertEqual(len(frames), 1)
        self.assertEqual(
            frames[0].upserts[0].points[0],
            (70, 80),
        )

    def test_handler_exception_identity_and_traceback_are_preserved(self):
        error = AttributeError('user callback failed')

        def mousedown(location, button):
            raise error

        self.screen.registry['mousedown'] = mousedown
        self.screen._listen()
        canvas = self._canvas()
        self.screen._backend.root.after_idle(
            lambda: canvas.event_generate('<Button-1>', x=50, y=60)
        )
        try:
            self.screen.update()
        except AttributeError as raised:
            self.assertIs(raised, error)
            frames = []
            traceback = raised.__traceback__
            while traceback is not None:
                frames.append(traceback.tb_frame.f_code.co_name)
                traceback = traceback.tb_next
        else:
            self.fail('the user callback exception did not propagate')
        self.assertIn('mousedown', frames)

    def test_loop_preserves_handler_exception_and_traceback(self):
        error = ValueError('loop callback failed')
        safety_quit = [None]

        def mousedown(location, button):
            raise error

        self.screen.registry['mousedown'] = mousedown
        self.screen._listen()
        canvas = self._canvas()
        self.screen._backend.root.after(
            1,
            lambda: canvas.event_generate('<Button-1>', x=50, y=60),
        )
        safety_quit[0] = self.screen._backend.root.after(
            250,
            self.screen._backend.root.quit,
        )
        try:
            self.screen.loop()
        except ValueError as raised:
            self.assertIs(raised, error)
            frames = []
            traceback = raised.__traceback__
            while traceback is not None:
                frames.append(traceback.tb_frame.f_code.co_name)
                traceback = traceback.tb_next
        else:
            self.fail('the loop callback exception did not propagate')
        finally:
            self.screen._backend.root.after_cancel(safety_quit[0])

        self.assertIn('mousedown', frames)

    def test_update_is_not_reentrant_from_an_input_callback(self):
        def mousedown(location, button):
            self.screen.update()

        self.screen.registry['mousedown'] = mousedown
        self.screen._listen()
        canvas = self._canvas()
        self.screen._backend.root.after_idle(
            lambda: canvas.event_generate('<Button-1>', x=50, y=60)
        )

        with self.assertRaisesRegex(PydrawError, 'not reentrant'):
            self.screen.update()
        self.assertFalse(self.screen._updating)

    def test_loop_dispatches_input_and_presents_its_mutation(self):
        rectangle = Rectangle(self.screen, 10, 10, 20, 20)
        received = []
        safety_quit = [None]
        self.screen.update()

        def mousedown(location, button):
            received.append((location, button))
            rectangle.moveto(location)
            self.screen._backend.root.after_cancel(safety_quit[0])
            self.screen._backend.root.after(5, self.screen._backend.root.quit)

        self.screen.registry['mousedown'] = mousedown
        self.screen._listen()
        canvas = self._canvas()
        self.screen._backend.root.after(
            1,
            lambda: canvas.event_generate('<Button-1>', x=90, y=65),
        )
        safety_quit[0] = self.screen._backend.root.after(
            250,
            self.screen._backend.root.quit,
        )

        self.screen.loop()

        self.assertEqual(received, [(Location(90, 65), 1)])
        item = self.screen._backend.item_for(rectangle._render_id)
        coordinates = self.screen._backend.canvas.coords(item)
        self.assertEqual(coordinates[:2], [90.0, 65.0])

    def test_deprecated_pointer_signature_remains_supported(self):
        received = []

        def mousedown(button, location):
            received.append((button, location))

        self.screen.registry['mousedown'] = mousedown
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.screen._mousedown(3, Location(25, 35))

        self.assertEqual(received, [(3, Location(25, 35))])
        self.assertIn('deprecated', output.getvalue())

    def test_single_location_pointer_signature_remains_supported(self):
        received = []
        self.screen.registry['mousedown'] = received.append

        self.screen._mousedown(2, Location(45, 55))

        self.assertEqual(received, [Location(45, 55)])


if __name__ == '__main__':
    unittest.main()
