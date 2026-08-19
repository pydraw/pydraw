"""Platform-neutral retained rendering data."""

from collections import OrderedDict
from typing import Callable, NamedTuple, Tuple


class PolylineNode(NamedTuple):
    id: int
    points: Tuple[Tuple[float, float], ...]
    color: Tuple[int, int, int]
    width: float
    dash: object
    visible: bool
    cap: str
    top: bool


class PolygonNode(NamedTuple):
    id: int
    points: Tuple[Tuple[float, float], ...]
    fill: object
    outline: object
    width: float
    visible: bool


class EllipseNode(NamedTuple):
    id: int
    center: Tuple[float, float]
    radius_x: float
    radius_y: float
    rotation: float
    points: Tuple[Tuple[float, float], ...]
    render_as_polygon: bool
    fill: object
    outline: object
    width: float
    visible: bool


class TextNode(NamedTuple):
    id: int
    position: Tuple[float, float]
    text: str
    color: Tuple[int, int, int]
    font: str
    size: int
    align: str
    bold: bool
    italic: bool
    underline: bool
    strikethrough: bool
    rotation: float
    visible: bool


class ImageNode(NamedTuple):
    id: int
    source: str
    position: Tuple[float, float]
    width: float
    height: float
    rotation: float
    tint: object
    tint_alpha: int
    border: object
    smooth: bool
    flip_x: bool
    flip_y: bool
    frame: int
    visible: bool


class RenderBatch(NamedTuple):
    upserts: tuple
    removals: tuple
    fronts: tuple
    backs: tuple

    def empty(self):
        return not any(self)


class RenderQueue:

    def __init__(self):
        self._next_id = 1
        self._sources = {}
        self._dirty = OrderedDict()
        self._removals = OrderedDict()
        self._fronts = OrderedDict()
        self._backs = OrderedDict()

    def allocate(self) -> int:
        render_id = self._next_id
        self._next_id += 1
        return render_id

    def register(self, source: Callable, render_id: int = None) -> int:
        if render_id is None:
            render_id = self.allocate()
        elif render_id >= self._next_id:
            self._next_id = render_id + 1

        self._sources[render_id] = source
        self._removals.pop(render_id, None)
        self._dirty[render_id] = None
        return render_id

    def invalidate(self, render_id: int) -> None:
        if render_id in self._sources:
            self._dirty[render_id] = None

    def remove(self, render_id: int) -> None:
        self._sources.pop(render_id, None)
        self._dirty.pop(render_id, None)
        self._fronts.pop(render_id, None)
        self._backs.pop(render_id, None)
        self._removals[render_id] = None

    def front(self, render_id: int) -> None:
        if render_id in self._sources:
            self._backs.pop(render_id, None)
            self._fronts[render_id] = None

    def back(self, render_id: int) -> None:
        if render_id in self._sources:
            self._fronts.pop(render_id, None)
            self._backs[render_id] = None

    def take(self) -> RenderBatch:
        upserts = []
        for render_id in self._dirty:
            source = self._sources.get(render_id)
            if source is None:
                continue
            node = source()
            if node.id != render_id:
                raise ValueError('render source returned the wrong ID')
            upserts.append(node)

        batch = RenderBatch(
            tuple(upserts),
            tuple(self._removals),
            tuple(self._fronts),
            tuple(self._backs),
        )
        self._dirty.clear()
        self._removals.clear()
        self._fronts.clear()
        self._backs.clear()
        return batch


__all__ = [
    'EllipseNode',
    'ImageNode',
    'PolygonNode',
    'PolylineNode',
    'RenderBatch',
    'RenderQueue',
    'TextNode',
]
