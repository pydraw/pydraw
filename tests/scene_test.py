"""Scene lifecycle, frame dispatch, input, and transition coverage."""

import unittest
from unittest import mock

from pydraw import Color, Location, Rectangle, Scene, Screen
from pydraw.errors import InvalidArgumentError, PydrawError
from pydraw.events import InputEvent


class RecordingScene(Scene):
    def __init__(self, name='scene'):
        super().__init__()
        self.name = name
        self.started = 0
        self.stopped = 0
        self.frames = []
        self.events = []
        self.box = None
        self.next_from_update = None
        self.next_from_input = None

    def start(self):
        self.started += 1
        self.box = Rectangle(
            self.screen(), 10, 10, 50, 50, Color('red'),
        )

    def update(self, dt):
        self.frames.append(dt)
        if self.next_from_update is not None:
            scene = self.next_from_update
            self.next_from_update = None
            self.goto(scene)

    def stop(self):
        self.stopped += 1
        self.events.append(('stop', self.screen()))

    def mousedown(self, location, button):
        self.events.append(('mousedown', location, button))
        if self.next_from_input is not None:
            scene = self.next_from_input
            self.next_from_input = None
            self.goto(scene)

    def mousemove(self, location):
        self.events.append(('mousemove', location))

    def keydown(self, key):
        self.events.append(('keydown', key))


class NoDeltaScene(Scene):
    def __init__(self):
        super().__init__()
        self.frames = 0

    def update(self):
        self.frames += 1


class InvalidUpdateScene(Scene):
    def update(self, first, second):
        pass


class SceneTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.screen._backend.root.destroy()
        except Exception:
            pass

    def setUp(self) -> None:
        self.screen.reset()
        self.screen.update()

    def test_activation_and_frame_timing(self):
        scene = RecordingScene()

        self.assertIs(self.screen.scene(scene), scene)
        self.assertIs(self.screen.scene(), scene)
        self.assertIs(scene.screen(), self.screen)
        self.assertEqual(scene.started, 1)
        self.assertEqual(scene.frames, [])
        self.assertIn(scene.box, self.screen.objects())

        with mock.patch(
                'pydraw.screen.time.perf_counter',
                side_effect=(10.0, 10.25)):
            self.screen.update()
            self.screen.update()

        self.assertEqual(scene.frames, [0.0, 0.25])

    def test_scene_receives_input(self):
        scene = RecordingScene()
        self.screen.scene(scene)

        self.screen._mousedown(1, Location(30, 40))
        self.screen._mousemove(Location(15, 25))
        self.screen._keydown('a')

        self.assertEqual(
            scene.events[0], ('mousedown', Location(30, 40), 1),
        )
        self.assertEqual(scene.events[1], ('mousemove', Location(15, 25)))
        self.assertEqual(scene.events[2][0], 'keydown')
        self.assertEqual(scene.events[2][1], 'a')

    def test_update_may_omit_delta_time(self):
        scene = NoDeltaScene()
        self.screen.scene(scene)

        self.screen.update()
        self.screen.update()

        self.assertEqual(scene.frames, 2)

    def test_immediate_switch_stops_and_detaches_previous_scene(self):
        first = RecordingScene('first')
        second = RecordingScene('second')
        self.screen.scene(first)
        first_box = first.box

        self.assertIs(self.screen.scene(second), second)

        self.assertEqual(first.stopped, 1)
        self.assertIs(first.events[0][1], self.screen)
        self.assertIsNone(first.screen())
        self.assertNotIn(first_box, self.screen.objects())
        self.assertEqual(second.started, 1)
        self.assertIs(second.screen(), self.screen)
        self.assertIs(self.screen.scene(), second)

        self.screen._keydown('b')
        self.assertFalse(any(event[0] == 'keydown' for event in first.events))
        self.assertEqual(second.events[-1][1], 'b')

    def test_input_transition_is_deferred_to_frame_boundary(self):
        first = RecordingScene('first')
        second = RecordingScene('second')
        first.next_from_input = second
        self.screen.scene(first)

        event = InputEvent('mousedown', (30, 40), 1, None)
        with mock.patch.object(
                self.screen._backend, 'poll_events', return_value=(event,)):
            self.screen.update()

        self.assertEqual(first.events[0][0], 'mousedown')
        self.assertEqual(first.stopped, 1)
        self.assertEqual(second.started, 1)
        self.assertEqual(second.frames, [0.0])
        self.assertIs(self.screen.scene(), second)

    def test_update_transition_starts_next_scene_before_present(self):
        first = RecordingScene('first')
        second = RecordingScene('second')
        first.next_from_update = second
        self.screen.scene(first)

        self.screen.update()

        self.assertEqual(first.frames, [0.0])
        self.assertEqual(first.stopped, 1)
        self.assertEqual(second.started, 1)
        self.assertEqual(second.frames, [])
        self.assertIs(self.screen.scene(), second)

        self.screen.update()
        self.assertEqual(second.frames, [0.0])

    def test_reset_stops_and_detaches_scene(self):
        scene = RecordingScene()
        self.screen.scene(scene)

        self.screen.reset()

        self.assertEqual(scene.stopped, 1)
        self.assertIsNone(scene.screen())
        self.assertIsNone(self.screen.scene())
        self.assertEqual(self.screen.objects(), ())
        self.assertEqual(self.screen.registry, {})

    def test_inactive_scene_cannot_request_transition(self):
        with self.assertRaisesRegex(PydrawError, 'not active'):
            RecordingScene().goto(RecordingScene())

    def test_invalid_update_signature_is_rejected(self):
        with self.assertRaisesRegex(
                PydrawError, r'update\(self\) or update\(self, dt\)'):
            self.screen.scene(InvalidUpdateScene())
        self.assertIsNone(self.screen.scene())
        self.assertEqual(self.screen.registry, {})

    def test_rejects_non_scene(self):
        with self.assertRaises(InvalidArgumentError):
            self.screen.scene('not a scene')


if __name__ == '__main__':
    unittest.main()
