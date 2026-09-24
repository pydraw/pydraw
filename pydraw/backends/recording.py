"""In-memory backend for render contract tests."""

from collections import OrderedDict

from pydraw.runtime import Runtime, ScreenBackend
from pydraw.render import EllipseNode, ImageNode, PolygonNode, PolylineNode, TextNode


def _translated(node, dx, dy):
    def point(value):
        return value[0] + dx, value[1] + dy

    if isinstance(node, (PolygonNode, PolylineNode)):
        return node._replace(points=tuple(point(value) for value in node.points))
    if isinstance(node, EllipseNode):
        return node._replace(center=point(node.center),
                             points=tuple(point(value) for value in node.points))
    if isinstance(node, (TextNode, ImageNode)):
        return node._replace(position=point(node.position))
    raise TypeError('RecordingBackend received an unsupported render node')


class RecordingBackend(ScreenBackend):

    def supports_group_translation(self):
        return True

    def __init__(self, config):
        self.config = config
        self.nodes = OrderedDict()
        self.batches = []
        self.closed = False
        self.title = config.title
        self.background = (255, 255, 255)
        self.events = []
        self.listening = False
        self.drawable_size = (config.width, config.height)
        self.fullscreen = False
        self.background_image = None

    def poll_events(self):
        events = tuple(self.events)
        self.events.clear()
        return events

    def listen(self):
        self.listening = True
        self.events.clear()

    def present(self, batch):
        self.batches.append(batch)
        for render_id in batch.removals:
            self.nodes.pop(render_id, None)
        for node in batch.upserts:
            self.nodes[node.id] = node
        for _, render_ids, dx, dy in batch.translations:
            for render_id in render_ids:
                node = self.nodes.get(render_id)
                if node is not None:
                    self.nodes[render_id] = _translated(node, dx, dy)
        for render_id in batch.backs:
            node = self.nodes.pop(render_id, None)
            if node is not None:
                nodes = OrderedDict(((render_id, node),))
                nodes.update(self.nodes)
                self.nodes = nodes
        for render_id in batch.fronts:
            node = self.nodes.pop(render_id, None)
            if node is not None:
                self.nodes[render_id] = node

    def run(self, step, frame_duration):
        step()

    def set_title(self, title):
        self.title = title

    def set_background(self, color):
        self.background = color

    def set_background_image(self, source):
        self.background_image = source

    def canvas_size(self):
        return self.drawable_size

    def window_size(self):
        return self.drawable_size

    def resize(self, width, height):
        self.drawable_size = (width, height)

    def set_fullscreen(self, fullscreen):
        self.fullscreen = fullscreen
        return self.fullscreen

    def alert(self, text, title, accept_text, cancel_text):
        return True

    def prompt(self, text, title):
        return None

    def grab(self, filename):
        return filename

    def measure_text(self, text, font, size, bold, italic):
        width = max((len(line) for line in text.split('\n')), default=0)
        return width * size * 0.6, size

    def measure_image(self, source):
        return 0, 0

    def image_frames(self, source):
        return 1

    def close(self):
        self.closed = True


class RecordingRuntime(Runtime):

    def __init__(self):
        self.backends = []

    def create_screen(self, config):
        backend = RecordingBackend(config)
        self.backends.append(backend)
        return backend
