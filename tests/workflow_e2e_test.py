"""End-to-end user workflow through Tk events, pydraw state, and rendering."""

import unittest

from pydraw import Color, Location, Rectangle, Screen, Text


_active_workflow = None


def mousedown(location, button):
    """Public-style event handler discovered by Screen.listen()."""
    if _active_workflow is not None:
        _active_workflow.handle_click(location, button)


def mousemove(location):
    """Public-style event handler discovered by Screen.listen()."""
    if _active_workflow is not None:
        _active_workflow.handle_motion(location)


class DrawingWorkflow:
    """A tiny interactive workflow representative of a pydraw program."""

    def __init__(self, screen):
        self.screen = screen
        self.player = Rectangle(screen, 10, 10, 30, 30, Color('blue'))
        self.target = Rectangle(screen, 100, 10, 30, 30, Color('red'))
        self.status = Text(screen, 'ready', 10, 60)
        self.pen = self.player.pen(Color('black'), 2)
        self.clicks = []
        self.pointer = None

    def handle_motion(self, location):
        self.pointer = location

    def handle_click(self, location, button):
        self.clicks.append((location, button))
        self.player.moveto(self.target.location())
        if self.player.overlaps(self.target):
            self.player.color(Color('green'))
            self.status.text('hit')


class WorkflowEndToEndTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.screen = Screen(320, 200, 'pydraw e2e')

    def setUp(self):
        global _active_workflow
        self.screen.reset()
        _active_workflow = DrawingWorkflow(self.screen)
        self.workflow = _active_workflow
        self.screen.listen()

    def tearDown(self):
        global _active_workflow
        _active_workflow = None
        self.screen.reset()

    def test_pointer_and_click_complete_rendered_workflow(self):
        canvas = self.screen._backend.canvas

        canvas.event_generate('<Motion>', x=25, y=35)
        canvas.event_generate('<Button-1>', x=40, y=50)
        self.screen.update()

        self.assertIsInstance(self.workflow.pointer, Location)
        self.assertEqual(len(self.workflow.clicks), 1)
        self.assertEqual(self.workflow.clicks[0][1], 1)
        self.assertEqual(
            self.workflow.player.location(),
            self.workflow.target.location()
        )
        self.assertTrue(self.workflow.player.overlaps(self.workflow.target))
        self.assertEqual(self.workflow.player.color(), Color('green'))
        self.assertEqual(self.workflow.status.text(), 'hit')
        self.assertEqual(
            self.workflow.pen.coordinates(),
            [Location(25, 25), Location(115, 25)]
        )

        self.assertEqual(
            set(self.screen.objects()),
            {
                self.workflow.player,
                self.workflow.target,
                self.workflow.status,
            }
        )
        for obj in self.screen.objects():
            with self.subTest(obj=type(obj).__name__):
                render_id = getattr(obj, '_render_id', None)
                item = (self.screen._backend.item_for(render_id)
                        if render_id is not None else obj._ref)
                self.assertIsNotNone(canvas.type(item))
