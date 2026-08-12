import unittest
from unittest import mock

from pydraw.backends.recording import RecordingBackend
from pydraw.events import InputEvent
from pydraw.render import (EllipseNode, ImageNode, PolygonNode, PolylineNode,
                           RenderBatch, RenderQueue, TextNode)
from pydraw.runtime import ScreenConfig


def node(render_id, x=0):
    return PolylineNode(
        render_id,
        ((x, 0), (x + 10, 10)),
        (0, 0, 0),
        1,
        None,
        True,
        'butt',
        False,
    )


class RenderQueueTest(unittest.TestCase):

    def test_multiple_invalidations_produce_one_latest_node(self):
        queue = RenderQueue()
        state = {'x': 0}
        source = mock.Mock(side_effect=lambda: node(render_id, state['x']))
        render_id = queue.register(source)

        state['x'] = 20
        queue.invalidate(render_id)
        queue.invalidate(render_id)
        batch = queue.take()

        source.assert_called_once_with()
        self.assertEqual(batch.upserts, (node(render_id, 20),))
        self.assertTrue(queue.take().empty())

    def test_remove_cancels_pending_upsert(self):
        queue = RenderQueue()
        source = mock.Mock()
        render_id = queue.register(source)

        queue.remove(render_id)
        batch = queue.take()

        source.assert_not_called()
        self.assertEqual(batch.upserts, ())
        self.assertEqual(batch.removals, (render_id,))


class RecordingBackendTest(unittest.TestCase):

    def test_collects_and_drains_neutral_input_events(self):
        backend = RecordingBackend(ScreenConfig(320, 200, 'recording'))
        event = InputEvent('mousedown', (20, 30), 1, None)

        backend.listen()
        backend.events.append(event)

        self.assertTrue(backend.listening)
        self.assertEqual(backend.poll_events(), (event,))
        self.assertEqual(backend.poll_events(), ())

    def test_records_platform_services(self):
        backend = RecordingBackend(ScreenConfig(320, 200, 'recording'))

        backend.set_background_image('background.png')
        backend.resize(640, 480)
        backend.set_fullscreen(True)

        self.assertEqual(backend.background_image, 'background.png')
        self.assertEqual(backend.canvas_size(), (640, 480))
        self.assertEqual(backend.window_size(), (640, 480))
        self.assertTrue(backend.fullscreen)
        self.assertTrue(backend.alert('text', 'title', 'yes', 'no'))
        self.assertIsNone(backend.prompt('text', 'title'))
        self.assertEqual(backend.grab('frame.png'), 'frame.png')

    def test_applies_updates_removals_and_ordering(self):
        backend = RecordingBackend(ScreenConfig(320, 200, 'recording'))
        first = node(1)
        second = node(2, 20)
        backend.present(RenderBatch((first, second), (), (), ()))
        backend.present(RenderBatch((node(1, 40),), (), (1,), ()))

        self.assertEqual(tuple(backend.nodes), (2, 1))
        self.assertEqual(backend.nodes[1], node(1, 40))

        backend.present(RenderBatch((), (2,), (), ()))
        self.assertEqual(tuple(backend.nodes), (1,))

    def test_records_polygon_and_semantic_ellipse_nodes(self):
        backend = RecordingBackend(ScreenConfig(320, 200, 'recording'))
        polygon = PolygonNode(
            1,
            ((10, 10), (30, 10), (20, 30)),
            (255, 0, 0),
            None,
            1,
            True,
        )
        ellipse = EllipseNode(
            2,
            (80, 60),
            20,
            10,
            45,
            ((80, 50), (90, 60), (80, 70), (70, 60)),
            False,
            (0, 0, 255),
            (0, 0, 0),
            2,
            True,
        )

        backend.present(RenderBatch((polygon, ellipse), (), (), ()))

        self.assertEqual(backend.nodes[1], polygon)
        self.assertEqual(backend.nodes[2], ellipse)

    def test_records_text_and_screen_configuration(self):
        backend = RecordingBackend(ScreenConfig(320, 200, 'recording'))
        node = TextNode(
            1,
            (10, 20),
            'hello',
            (0, 0, 0),
            'Arial',
            16,
            'left',
            False,
            False,
            False,
            False,
            0,
            True,
        )

        backend.set_title('updated')
        backend.set_background((20, 30, 40))
        backend.present(RenderBatch((node,), (), (), ()))

        self.assertEqual(backend.title, 'updated')
        self.assertEqual(backend.background, (20, 30, 40))
        self.assertEqual(backend.nodes[1], node)
        self.assertEqual(
            backend.measure_text('abc\nde', 'Arial', 10, False, False),
            (18.0, 10),
        )

    def test_records_semantic_image_node(self):
        backend = RecordingBackend(ScreenConfig(320, 200, 'recording'))
        node = ImageNode(
            1,
            'sprite.png',
            (20, 30),
            40,
            50,
            15,
            (255, 0, 0),
            100,
            None,
            False,
            True,
            False,
            2,
            True,
        )

        backend.present(RenderBatch((node,), (), (), ()))

        self.assertEqual(backend.nodes[1], node)


if __name__ == '__main__':
    unittest.main()
