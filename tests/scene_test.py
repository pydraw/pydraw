"""
Integration coverage of the Scene abstraction - subclassing a Scene,
applying it to a Screen via Screen.scene(), the start()/run() lifecycle, and
input handlers registered from the Scene's methods.

(Rewritten from an old design-exploration script into real assertions.)
"""

import unittest
from pydraw import Screen, Scene, Location, Color, Rectangle
from pydraw.errors import InvalidArgumentError


class RecordingScene(Scene):
    """A Scene that records its lifecycle and every input event it receives."""

    def __init__(self):
        super().__init__()
        self.started = False
        self.ran = False
        self.box = None
        self.events = []

    def start(self):
        # start() runs after the Scene is bound to a Screen, so screen() is live.
        self.box = Rectangle(self.screen(), 10, 10, 50, 50, Color('red'))
        self.started = True

    def run(self):
        self.ran = True

    def mousedown(self, location, button):
        self.events.append(('mousedown', location, button))

    def mousemove(self, location):
        self.events.append(('mousemove', location))

    def keydown(self, key):
        self.events.append(('keydown', key))


class SceneTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.screen = Screen(800, 600)

    def setUp(self) -> None:
        self.screen.reset()

    def test_apply_runs_lifecycle(self):
        scene = RecordingScene()
        self.screen.scene(scene)

        self.assertIs(scene.screen(), self.screen)
        self.assertTrue(scene.started, 'start() should have been called')
        self.assertTrue(scene.ran, 'run() should have been called')
        # The object created in start() is registered on the screen.
        self.assertIn(scene.box, self.screen.objects())

    def test_scene_receives_input(self):
        scene = RecordingScene()
        self.screen.scene(scene)

        self.screen._mousedown(0, Location(30, 40))
        self.screen._mousemove(Location(15, 25))
        self.screen._keydown('a')

        self.assertEqual(scene.events[0], ('mousedown', Location(30, 40), 0))
        self.assertEqual(scene.events[1], ('mousemove', Location(15, 25)))
        self.assertEqual(scene.events[2][0], 'keydown')
        self.assertEqual(scene.events[2][1], 'a')  # Key compares equal to its string

    def test_switching_scenes_replaces_handlers(self):
        first = RecordingScene()
        self.screen.scene(first)

        second = RecordingScene()
        self.screen.scene(second)

        # Events now go to the second scene only.
        self.screen._keydown('b')
        self.assertEqual(len(first.events), 0)
        self.assertEqual(second.events[0][1], 'b')

    def test_rejects_non_scene(self):
        self.assertRaises(InvalidArgumentError, self.screen.scene, 'not a scene')


if __name__ == '__main__':
    unittest.main()
