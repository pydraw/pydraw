"""
Integration coverage of Screen input handling registered through
Screen.listen(), which scans this module for functions named after the input
types (keydown, mousedown, ...) and wires them up as callbacks.

Events are driven directly through the Screen's internal dispatchers (the same
methods the tkinter bindings call), so no real event loop is needed.

(Rewritten from an old manual input script into real assertions.)
"""

import unittest
from pydraw import Screen, Location

# Screen.listen() discovers module-level functions by these exact names.
_events = []


def keydown(key):
    _events.append(('keydown', key))


def keyup(key):
    _events.append(('keyup', key))


def mousedown(location, button):
    _events.append(('mousedown', location, button))


def mouseup(location, button):
    _events.append(('mouseup', location, button))


def mousedrag(location, button):
    _events.append(('mousedrag', location, button))


def mousemove(location):
    _events.append(('mousemove', location))


class InputTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        _events.clear()
        # Registers the module-level handlers above into the screen's registry.
        self.screen.listen()

    def test_key_events(self):
        self.screen._keydown('A')
        self.screen._keyup('B')

        self.assertEqual(_events[0][0], 'keydown')
        self.assertEqual(_events[0][1], 'a')   # keys are normalized to lowercase
        self.assertEqual(_events[1][0], 'keyup')
        self.assertEqual(_events[1][1], 'b')

    def test_mouse_button_events(self):
        self.screen._mousedown(0, Location(10, 20))
        self.screen._mouseup(1, Location(30, 40))
        self.screen._mousedrag(0, Location(50, 60))

        self.assertEqual(_events[0], ('mousedown', Location(10, 20), 0))
        self.assertEqual(_events[1], ('mouseup', Location(30, 40), 1))
        self.assertEqual(_events[2], ('mousedrag', Location(50, 60), 0))

    def test_mousemove_updates_and_dispatches(self):
        self.screen._mousemove(Location(5, 5))

        self.assertEqual(_events[-1], ('mousemove', Location(5, 5)))
        # _mousemove also caches the position, exposed via screen.mouse().
        self.assertEqual(self.screen.mouse(), Location(5, 5))

    def test_tk_events_reach_registered_handlers(self):
        """Exercise the actual widget bindings installed by Screen.listen()."""
        # Turtle's ScrolledCanvas forwards bind(), but event_generate() itself
        # belongs to its inner Tk Canvas.
        canvas = self.screen._canvas._canvas
        canvas.event_generate('<Motion>', x=25, y=35)
        canvas.event_generate('<Button-1>', x=40, y=50)
        self.screen.update()

        event_names = [event[0] for event in _events]
        self.assertIn('mousemove', event_names)
        self.assertIn('mousedown', event_names)
        self.assertEqual(
            next(event[2] for event in _events if event[0] == 'mousedown'),
            1
        )
        self.assertNotEqual(self.screen.mouse(), Location(5, 5))

    def test_unregistered_event_is_ignored(self):
        # keypress has no handler in this module; dispatching it must be a no-op.
        self.screen._keypress('x')
        self.assertEqual(_events, [])


if __name__ == '__main__':
    unittest.main()
