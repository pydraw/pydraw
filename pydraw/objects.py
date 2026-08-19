"""
Objects in the PyDraw library

(Author: Noah Coetsee)
"""

import math
from typing import TYPE_CHECKING, Optional, Tuple, Union, List, overload as _overload
# import asyncio

# from pydraw.errors import *  # util gives us our errors for us :)
from pydraw.util import *

from pydraw import Screen
from pydraw import Location
from pydraw import Color
from pydraw.render import EllipseNode, ImageNode, PolygonNode, PolylineNode, TextNode

from pydraw.overload import overload

PIXEL_RATIO = 20
NoneType = type(None)


class Pen:
    # Pen for drawing a line as an object moves around on the screen
    def __init__(self, screen: Screen, x: float, y: float, color: Color = Color('black'), width: int = 2, top: bool = False):
        self._screen = screen
        self._coordinates = []  # contains all coordinates of the lines
        self._location = Location(x, y)  # used for when _drawing = False

        # self._coordinates.append(Location(x, y))

        self._color = color
        self._width = width
        self._top = top

        self._drawing = False

        self._history = []  # stores old line _refs for clearing
        self._ref = None  # currentLine
        self._strokes = {}
        self._stroke_visibility = {}

    def location(self) -> Location:
        if self._drawing and len(self._coordinates) > 0:
            return self._coordinates[-1]

        return self._location

    @_overload
    def move(self, dx: float, dy: float) -> Location: ...

    @_overload
    def move(self, location: Location) -> Location: ...

    @_overload
    def move(self, dxy: Tuple[float, float]) -> Location: ...

    @_overload
    def move(self, *, dx: float = ..., dy: float = ...) -> Location: ...

    def move(self, *args, **kwargs):
        """
        Adds a new coordinate to the pen line with a passed difference from the previous coordinate.
        Requires coordinates to be len > 0.

        Can take two numbers (dx, dy), a tuple, or a Location

        :param dx: the dx to move by
        :param dy: the dy to move by
        :return: the location (after change)
        """

        diff = (0, 0)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                diff = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                diff = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Pen#move(): expected a tuple/Location or two numbers (dx, dy).'
                )
        elif len(kwargs) == 0:
            raise InvalidArgumentError(
                'Pen#move(): expected a tuple/Location or two numbers (dx, dy).'
            )

        verify_keywords(kwargs, ('dx', 'dy'), 'Pen#move()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Pen#move(): expected a tuple/Location or two numbers (dx, dy).'
                )

            name = name.lower()
            if name == 'dx':
                diff = (value, diff[1])
            elif name == 'dy':
                diff = (diff[0], value)

        if not len(self._coordinates) > 0:
            raise PydrawError('Pen#move(): cannot move before the Pen has been started.')

        current = self.location()
        location = Location(current.x() + diff[0], current.y() + diff[1])
        if self._drawing:
            self._coordinates.append(location)
        else:
            self._location = location

        self._update()
        return location

    @_overload
    def moveto(self, x: float, y: float) -> Location: ...

    @_overload
    def moveto(self, location: Location) -> Location: ...

    @_overload
    def moveto(self, xy: Tuple[float, float]) -> Location: ...

    @_overload
    def moveto(self, *, x: float = ..., y: float = ...) -> Location: ...

    def moveto(self, *args, **kwargs):
        """
        Adds a new coordinate to the pen line.

        Can take two coordinates (x, y), a tuple, or a Location

        :param x: the x to move to
        :param y: the y to move to
        :return: the location (after change)
        """

        # Seed from the effective current position so partial calls work both
        # while drawing and after the pen has stopped.
        current = self.location()
        location = (current.x(), current.y())

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                location = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                location = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Pen#moveto(): expected a tuple/Location or two numbers (x, y).'
                )
        elif len(kwargs) == 0:
            raise InvalidArgumentError(
                'Pen#moveto(): expected a tuple/Location or two numbers (x, y).'
            )

        verify_keywords(kwargs, ('x', 'y'), 'Pen#moveto()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Pen#moveto(): expected a tuple/Location or two numbers (x, y).'
                )

            name = name.lower()
            if name == 'x':
                location = (value, location[1])
            elif name == 'y':
                location = (location[0], value)

        if not len(self._coordinates) > 0:
            raise PydrawError('Pen#moveto(): cannot move before the Pen has been started.')

        new_location = Location(location[0], location[1])
        if self._drawing:
            self._coordinates.append(new_location)
        else:
            self._location = new_location

        self._update()
        return new_location

    def coordinates(self, *coords: Union[Location, Tuple[float, float]]) -> List[Location]:

        if len(coords) > 0:
            self._coordinates = []

            for pos in coords:
                if type(pos) is tuple or type(pos) is Location:
                    self._coordinates.append(Location(pos[0], pos[1]))
                else:
                    raise InvalidArgumentError(
                        'Pen#coordinates(): expected only tuples or Locations.'
                    )

            self._update()

        return self._coordinates

    def start(self):
        if self._drawing:
            return

        self._drawing = True
        self._coordinates = [Location(self._location)]

        self._setup()

    def stop(self):
        if not self._drawing:
            return

        if len(self._coordinates) > 0:
            self._location = self._coordinates[-1]
            # don't clear coordinates in case they get altered after we are done drawing

        if self._ref is not None:
            self._history.append(self._ref)
        self._drawing = False

    def drawing(self, drawing: bool = None) -> bool:
        if drawing is not None:
            if drawing and not self._drawing:
                self.start()
            elif not drawing and self._drawing:
                self.stop()

        return self._drawing

    def toggle(self) -> bool:
        if self._drawing:
            self.stop()
        else:
            self.start()

        return self._drawing

    # noinspection PyProtectedMember
    def clear(self):
        """
        Clear the line from the screen and all history (coordinates).
        """

        if len(self._coordinates) > 0:
            self._location = Location(self._coordinates[-1])

        for line in self._history:
            self._remove_stroke(line)
        self._history.clear()

        if self._drawing:
            self._coordinates = [Location(self._location)]
            if self._ref is not None:
                self._strokes[self._ref] = self._coordinates
                self._stroke_visibility[self._ref] = False
                self._screen._invalidate_render(self._ref)
        else:
            self._coordinates = []
            if self._ref is not None:
                self._remove_stroke(self._ref)
                self._ref = None

    def color(self, color: Color = None) -> Color:
        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            if self._ref is not None:
                self._update_all()

        return self._color

    def width(self, width: int = None) -> int:
        if width is not None:
            verify(width, int)
            self._width = width
            if self._ref is not None:
                self._update_all()

        return self._width

    def top(self, top: bool = None) -> bool:
        if top is not None:
            verify(top, bool)
            self._top = top
            if self._ref is not None:
                self._update_all()

        return self._top

    def _setup(self):
        render_id = self._screen._allocate_render_id()
        self._ref = render_id
        self._strokes[render_id] = self._coordinates
        self._stroke_visibility[render_id] = True
        self._screen._register_render_source(
            lambda render_id=render_id: self._render_stroke(render_id),
            render_id,
        )

    def _render_stroke(self, render_id):
        return PolylineNode(
            render_id,
            tuple((point.x(), point.y()) for point in self._strokes[render_id]),
            self._color.rgb(),
            self._width,
            None,
            self._stroke_visibility[render_id],
            'round',
            self._top,
        )

    def _remove_stroke(self, render_id):
        self._screen._remove_render(render_id)
        self._strokes.pop(render_id, None)
        self._stroke_visibility.pop(render_id, None)

    # noinspection PyProtectedMember
    def _update(self):
        if self._ref is None:
            raise PydrawError('Pen#update(): Pen has not been started.')

        self._strokes[self._ref] = self._coordinates
        self._stroke_visibility[self._ref] = True
        self._screen._invalidate_render(self._ref)

    def _update_all(self):
        self._update()
        for render_id in self._strokes:
            self._screen._invalidate_render(render_id)


class Object:
    """
    A base object containing a location and screen. This ensures coordinates are
    done with the root in the top left corner, and not at the center.
    """

    _PEN_SUPPORTED = True

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, location: Location = None):
        verify(screen, Screen, x, (float, int), y, (float, int), location, Location)

        self._screen = screen
        self._location = location if location is not None else Location(x, y)

        # noinspection PyProtectedMember
        self._screen._add(self)

        # Most objects never draw trails, so avoid creating an unused Pen and
        # canvas line until pen() is actually called.
        self._pen = None

    def x(self, x: float = None) -> float:
        if x is not None:
            verify(x, (float, int))
            self.moveto(x, self.y())

        return self._location.x()

    def y(self, y: float = None) -> float:
        if y is not None:
            verify(y, (float, int))
            self.moveto(self.x(), y)

        return self._location.y()

    def location(self) -> Location:
        return self._location

    @_overload
    def move(self, dx: float, dy: float) -> None: ...

    @_overload
    def move(self, location: Location) -> None: ...

    @_overload
    def move(self, dxy: Tuple[float, float]) -> None: ...

    @_overload
    def move(self, *, dx: float = ..., dy: float = ...) -> None: ...

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        self._location.move(*args, **kwargs)
        self.update()
        self._sync_pen()

    @_overload
    def moveto(self, x: float, y: float) -> None: ...

    @_overload
    def moveto(self, location: Location) -> None: ...

    @_overload
    def moveto(self, xy: Tuple[float, float]) -> None: ...

    @_overload
    def moveto(self, *, x: float = ..., y: float = ...) -> None: ...

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        self._location.moveto(*args, **kwargs)
        self.update()
        self._sync_pen()

    def front(self) -> None:
        """
        Brings the object to the front of the Screen
        (Imagine moving forward on the Z axis)

        :return: None
        """

        # noinspection PyProtectedMember
        self._screen._front(self)

    def back(self) -> None:
        """
        Brings the object to the back of the Screen
        (Imagine moving backward on the Z axis)

        :return: None
        """

        # noinspection PyProtectedMember
        self._screen._back(self)

    def remove(self) -> None:
        self._screen.remove(self)

    # Pen methods
    def _check_pen_supported(self, method: str = 'pen()') -> None:
        if not self._PEN_SUPPORTED:
            raise UnsupportedError(
                f'{type(self).__name__}#{method}: Pens are unsupported for this object.'
            )

    def _require_pen(self, method: str) -> Pen:
        self._check_pen_supported(method)
        if self._pen is None:
            raise PydrawError(
                f'{type(self).__name__}#{method}: this object has not started a Pen.'
            )

        return self._pen

    def _pen_location(self) -> Location:
        return Location(self.x(), self.y())

    def _sync_pen(self) -> None:
        pen = getattr(self, '_pen', None)
        if pen is None or not pen.drawing():
            return

        location = self._pen_location()
        if pen.location() != location:
            pen.moveto(location)

    def pen(self, color: Color = Color('black'), width: int = 2, top: bool = False) -> Pen:
        self._check_pen_supported('pen()')
        verify(color, Color, width, int, top, bool)

        if self._pen is None:
            location = self._pen_location()
            self._pen = Pen(
                self._screen, location.x(), location.y(), color, width, top
            )
        else:
            self._pen.color(color)
            self._pen.width(width)
            self._pen.top(top)

        self._pen.drawing(True)
        return self._pen

    def pen_clear(self) -> None:
        self._require_pen('pen_clear()').clear()

    def pen_stop(self) -> bool:
        return self._require_pen('pen_stop()').drawing(False)

    def pen_width(self, width: int = None) -> int:
        return self._require_pen('pen_width()').width(width)

    def pen_top(self, top: bool = None) -> bool:
        return self._require_pen('pen_top()').top(top)

    # # noinspection PyProtectedMember
    # def add(self) -> None:
    #     """
    #     Should only be used to add an object that has been removed (via .remove() or Screen.clear()
    #     :return: None
    #     """
    #     if self in self._screen.objects():
    #         raise PydrawError('Error adding object: Object already in Screen.objects()')
    #
    #     self._setup()
    #     self._screen._add(self)

    def _setup(self):
        """
        To be overriden.
        """
        pass

    # noinspection PyProtectedMember
    def _check(self) -> None:
        if self._screen is None:
            return

        if not self._screen.contains(self):
            if self in self._screen._gridlines or self in self._screen._helpers:
                return

            raise PydrawError(
                f'{type(self).__name__}#update(): object is not on its Screen.'
            )

    def update(self) -> None:
        """
        To be overriden.
        """
        pass


class Renderable(Object):
    """
    Test class for new itemconfigure-based pyDraw objects.

    Update method is now only used for changes in position (and possibly changes that cannot be configured and require
    the item to be remade)
    """

    # bounds() cache. Class-level defaults so every subclass inherits them, even
    # ones like CustomPolygon that build their state without calling __init__.
    # Keyed on the transform parameters (see bounds()); the first compute on an
    # instance shadows these with per-instance values.
    _bounds_sig = None
    _bounds_cache = None

    def _pen_location(self) -> Location:
        return self.center()

    def _render_color(self, color):
        return None if color == Color.NONE else color.rgb()

    def _render_node(self):
        return PolygonNode(
            self._render_id,
            tuple((vertex.x(), vertex.y()) for vertex in self.vertices()),
            self._render_color(self._color) if self._fill else None,
            self._render_color(self._border),
            self._border_width,
            self._visible,
        )

    def _register_render(self):
        self._render_id = self._screen._register_render_source(self._render_node)
        self._ref = self._render_id

    def _restore_render(self):
        self._screen._register_render_source(self._render_node, self._render_id)

    def _invalidate_render(self):
        self._screen._invalidate_render(self._render_id)

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = Color.NONE,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super().__init__(screen, x, y, location)
        self._width = width
        self._height = height
        self._color = color
        self._border = border if border is not None else Color('')
        self._border_width = 1
        self._fill = fill
        self._angle = rotation
        self._last_angle = rotation
        self._visible = visible

        self._setup()

    def x(self, x: float = None) -> float:
        if x is not None:
            verify(x, (float, int))
            self.moveto(x, self.y())

        return self._location.x()

    def y(self, y: float = None) -> float:
        if y is not None:
            verify(y, (float, int))
            self.moveto(self.x(), y)

        return self._location.y()

    def location(self) -> Location:
        return self._location

    @_overload
    def move(self, dx: float, dy: float) -> None: ...

    @_overload
    def move(self, location: Location) -> None: ...

    @_overload
    def move(self, dxy: Tuple[float, float]) -> None: ...

    @_overload
    def move(self, *, dx: float = ..., dy: float = ...) -> None: ...

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.move(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    @_overload
    def moveto(self, x: float, y: float) -> None: ...

    @_overload
    def moveto(self, location: Location) -> None: ...

    @_overload
    def moveto(self, xy: Tuple[float, float]) -> None: ...

    @_overload
    def moveto(self, *, x: float = ..., y: float = ...) -> None: ...

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.moveto(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    def _translate(self, dx: float, dy: float) -> None:
        """
        Shift the object by (dx, dy) without rebuilding its geometry.

        A translation moves every vertex by the same delta and leaves the
        rotation untouched, so we can shift the canvas item relatively (a
        single C-level canvas op) and shift the cached vertices in place,
        rather than re-deriving them from the shape via _update_coords().
        """

        if dx == 0 and dy == 0:
            return

        for vertex in self._vertices:
            vertex._x += dx
            vertex._y += dy

        self._invalidate_render()
        self._sync_pen()

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the Renderable.

        :param width: the width to set to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int))
            self._width = width
            self._update_coords()

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the Renderable.

        :param height: the height to set to in pixels, if any
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int))
            self._height = height
            self._update_coords()

        return self._height

    @_overload
    def center(self, x: float, y: float, *, centroid: bool = ...) -> Location: ...

    @_overload
    def center(self, location: Location, *, centroid: bool = ...) -> Location: ...

    @_overload
    def center(self, *, move_to: Location = ..., x: float = ..., y: float = ..., centroid: bool = ...) -> Location: ...

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center

        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Renderable
        """

        verify_keywords(kwargs, ('move_to', 'x', 'y', 'centroid'), 'Renderable#center()')

        centroid = kwargs.get('centroid', False)
        if type(centroid) is not bool:
            raise InvalidArgumentError(
                'Renderable#center(): centroid must be a bool.'
            )

        has_keyword_move = any(key in kwargs for key in ('move_to', 'x', 'y'))

        # Complete positional setters are the animation hot path. Dispatching
        # directly to _center preserves CustomPolygon specialization while
        # avoiding a current-center lookup, clone, and Location.moveto parse.
        if not has_keyword_move and len(args) == 2:
            x, y = args
            if ((type(x) is float or type(x) is int)
                    and (type(y) is float or type(y) is int)):
                return self._center(Location._raw(x, y), centroid=centroid)

        if not has_keyword_move and len(args) == 1:
            target = args[0]
            if type(target) is Location:
                return self._center(
                    Location._raw(target._x, target._y), centroid=centroid,
                )
            if (type(target) is tuple and len(target) == 2
                    and (type(target[0]) is float or type(target[0]) is int)
                    and (type(target[1]) is float or type(target[1]) is int)):
                return self._center(
                    Location._raw(target[0], target[1]), centroid=centroid,
                )

        # Complete keyword setters can skip the same current-center work. Keep
        # mixed move_to/x/y calls on the compatibility parser below, where the
        # later x/y values intentionally override move_to components.
        if len(args) == 0 and 'move_to' in kwargs \
                and 'x' not in kwargs and 'y' not in kwargs:
            target = kwargs['move_to']
            if type(target) is Location:
                return self._center(
                    Location._raw(target._x, target._y), centroid=centroid,
                )
            if (type(target) is tuple and len(target) == 2
                    and (type(target[0]) is float or type(target[0]) is int)
                    and (type(target[1]) is float or type(target[1]) is int)):
                return self._center(
                    Location._raw(target[0], target[1]), centroid=centroid,
                )

        if len(args) == 0 and 'move_to' not in kwargs \
                and 'x' in kwargs and 'y' in kwargs:
            x, y = kwargs['x'], kwargs['y']
            if ((type(x) is float or type(x) is int)
                    and (type(y) is float or type(y) is int)):
                return self._center(Location._raw(x, y), centroid=centroid)

        if len(args) == 0:
            # centroid is only a getter modifier; without an actual move request
            # (positional args or move_to/x/y) this is a pure getter.
            if not has_keyword_move:
                return self._center(centroid=centroid)

        location = Location(self._center(centroid=centroid))

        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0])
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected both x and y.'
                    )
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )

                location.moveto(args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                )

        if len(kwargs) != 0:
            # TODO: Shouldn't this be called "location", not "move_to"
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to'])
                else:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x'])
                else:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y'])
                else:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )
        return self._center(location, centroid)

    def _center(self, move_to: Location = None, centroid: bool = False):
        if centroid:
            # This remains the historical vertex mean, not an area-weighted
            # polygon centroid.
            center_x = sum(vertex._x for vertex in self._vertices) / len(self._vertices)
            center_y = sum(vertex._y for vertex in self._vertices) / len(self._vertices)
        else:
            center_x = self._location._x + self._width / 2
            center_y = self._location._y + self._height / 2

        if move_to is not None:
            verify(move_to, Location)
            self.move(move_to._x - center_x, move_to._y - center_y)
            return move_to

        return Location._raw(center_x, center_y)

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the object.

        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the object's rotation in degrees
        """

        if angle is not None:
            verify(angle, (float, int))
            self._angle = angle
            self._update_coords()

        return self._angle % 360

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the object by a difference, in degrees

        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        verify(angle_diff, (float, int))
        self.rotation(self._angle + angle_diff)

    def angleto(self, obj) -> float:
        """
        Retrieve the angle between this object and another (based on 0 degrees at 12 o'clock)

        :param obj: the Object/Location to get the angle to.
        :return: the angle in degrees as a float
        """

        if isinstance(obj, Object):
            obj = obj.location()
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError(
                f'Renderable#angleto(): expected a Renderable or Location; received {type(obj)} ({obj!r}).'
            )

        location = Location(obj[0], obj[1])
        # theta = -math.atan2(location.x() - self.x(), location.y() - self.y()) - math.radians(self.rotation())
        theta = math.atan2(location.y() - self.center().y(), location.x() - self.center().x()) \
                - math.radians(self.rotation()) + math.pi / 2
        theta = math.degrees(theta)

        return theta

    def lookat(self, obj) -> None:
        """
        Look at another object (Objects or Locations)

        :param obj: the Object/Location to look at.
        :return: None
        """

        theta = self.angleto(obj)
        self.rotate(theta)

    def forward(self, distance: float) -> None:
        """
        Move the Renderable forward by distance at its current heading (rotation/angle)

        :param distance: the distance to move forward (hypotenuse)
        :return: None
        """

        dx = distance * math.sin(math.radians(self._angle))
        dy = distance * -math.cos(math.radians(self._angle))

        self.move(dx, dy)

    def backward(self, distance: float) -> None:
        """
        Move the Renderable backward by distance at its current heading (rotation/angle)

        :param distance: the distance to move backward (hypotenuse)
        :return: None
        """

        self.forward(-distance)

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the object

        :param color: the color to set to, if any
        :return: the color of the object
        """

        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            self._invalidate_render()

        return self._color

    def border(self, color: Color = None, width: float = None, fill: bool = None) -> Color:
        """
        Add or get the border of the object

        :param color: the color to set the border too, set to Color.NONE to remove border
        :param width: the width of the border
        :param fill: whether to fill the polygon.
        :return: The Color of the border
        """

        update = False

        if color is not None:
            verify(color, Color)
            self._border = color
            update = True
        if fill is not None:
            verify(fill, bool)
            self._fill = fill
            update = True
        if width is not None:
            verify(width, (float, int))
            self._border_width = width
            update = True

        if update:
            self._invalidate_render()

        return self._border

    def border_width(self, width: float = None) -> float:
        """
        Gets or sets the border width

        :param width: the border width to set to
        :return: the border width
        """

        if width is not None:
            verify(width, (float, int))
            self._border_width = width
            self._invalidate_render()

        return self._border_width

    def fill(self, fill: bool = None) -> bool:
        """
        Returns or sets the current fill boolean

        :param fill: a new fill value, whether to fill the polygon
        :return: the fill value
        """

        if fill is not None:
            verify(fill, bool)
            self._fill = fill
            self._invalidate_render()

        return self._fill

    def distance(self, obj) -> float:
        """
        Returns the distance between two objs or locations in pixels (center to center)

        :param obj: the Renderable/location to check distance between
        :return: the distance between this obj and the passed Renderable/Location.
        """

        if type(obj) is not Location and not isinstance(obj, Renderable):
            raise InvalidArgumentError(
                f'Renderable#distance(): expected a Renderable or Location; '
                f'received {type(obj)} ({obj!r}).'
            )

        location = obj if type(obj) is Location else obj.center()

        return math.sqrt((location.x() - self.center().x()) ** 2 + (location.y() - self.center().y()) ** 2)

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the renderable.

        :param visible: the new visibility value, if any
        :return: the visibility value
        """

        if visible is not None:
            verify(visible, bool)
            self._visible = visible
            self._invalidate_render()

        return self._visible

    def transform(self, transform: tuple = None) -> tuple:
        """
        Get or set the transform of the Renderable.
        Transforms represent the width, height, and rotation of Renderables.

        You can retrieve a Transform from a Renderable with this method and set the transform the same way.

        :param transform: the transform to set to, if any.
        :return: the transform
        """

        if transform is not None:
            verify(transform, tuple)
            if not len(transform) == 3:
                raise InvalidArgumentError(
                    'Renderable#transform(): expected (width, height, rotation).'
                )
            verify(transform[0], (float, int), transform[1], (float, int), transform[2], (float, int))

            update_width = transform[0] != self._width
            update_height = transform[1] != self._height
            update_rotation = transform[2] % 360 != self._angle % 360

            if not update_width and not update_height and not update_rotation:
                return self._width, self._height, self._angle % 360

            self._width = transform[0]
            self._height = transform[1]
            self._angle = transform[2]

            self._update_coords()

        return self._width, self._height, self._angle % 360

    def clone(self):
        """
        Clone this renderable!

        :return: a Renderable
        """

        constructor = type(self)
        return constructor(self._screen, self.x(), self.y(), self.width(), self.height(), self.color(), self.border(),
                           self.fill(), self.rotation(), self.visible())

    def vertices(self) -> list:
        """
        Returns the list of vertices for the Renderable.
        (The vertices will be returned clockwise, starting from the top-leftmost point)

        :return: a list of Locations representing the vertices
        """

        return self._get_vertices()

    # noinspection PyProtectedMember
    def bounds(self) -> (Location, float, float):
        """
        Get the location and dimensions of a bounding box that contains the entire shape

        :return: a tuple containing the Location, width, and height.
        """

        # Bounds only change when the object is moved/rotated/resized, so key a
        # cache on those transform parameters. Repeated queries between moves --
        # e.g. the same object across an all-pairs or one-vs-many overlaps() sweep
        # -- then reuse the result instead of re-querying the canvas each time.
        loc = self._location
        sig = (loc._x, loc._y, self._angle, self._width, self._height)
        if sig == self._bounds_sig:
            return self._bounds_cache

        vertices = self.vertices()
        x_values = [vertex.x() for vertex in vertices]
        y_values = [vertex.y() for vertex in vertices]
        result = (
            Location(min(x_values), min(y_values)),
            max(x_values) - min(x_values),
            max(y_values) - min(y_values),
        )

        self._bounds_sig = sig
        self._bounds_cache = result
        return result

    @_overload
    def contains(self, __x: float, __y: float) -> bool: ...

    @_overload
    def contains(self, __location: Location) -> bool: ...

    @_overload
    def contains(self, __xy: Tuple[float, float]) -> bool: ...

    def contains(self, *args) -> bool:
        """
        Returns whether a Location is contained within the object.

        :param args: You may pass in either two numbers, a Location, or a tuple containing and x and y point.
        :return: a boolean value representing whether the point is within the vertices of the object.
        """

        x, y = 0, 0
        if len(args) == 1:
            verify(args[0], (tuple, Location))
            if type(args[0]) is Location:
                x = args[0].x()
                y = args[0].y()
            elif type(args[0]) is tuple and len(args[0]) == 2:
                x = args[0][0]
                y = args[0][1]
            else:
                raise InvalidArgumentError(
                    'Renderable#contains(): tuple arguments must contain exactly two values.'
                )
        elif len(args) == 2:
            verify(args[0], (float, int), args[1], (float, int))
            if type(args[0]) is not float and type(args[0]) is not int \
                    and type(args[1]) is not float and type(args[1]) is not int:
                raise InvalidArgumentError(
                    'Renderable#contains(): expected a tuple/Location or two numbers (x, y).'
                )
            x = args[0]
            y = args[1]
        else:
            raise InvalidArgumentError(
                'Renderable#contains(): expected a tuple/Location or two numbers (x, y).'
            )

        # If the point isn't remotely near us, we don't need to perform any calculations.
        if not isinstance(self, CustomRenderable) and self._angle == 0:
            if self.y() > 0 and self.x() > 0:
                if not (self.x() <= x <= (self.x() + self.width()) and self.y() <= y <= (self.y() + self.height())):
                    return False

        # the contains algorithm uses the line-intersects algorithm to determine if a point is within a polygon.
        # we are going to cast a ray from our point to the positive x. (left to right)

        # Pre-extract raw (x, y) floats once so the ray-cast loop does pure
        # float math instead of calling Location.x()/.y() on every vertex, every
        # pass. This is the single biggest cost for high-vertex shapes.
        vertices = [(vertex.x(), vertex.y()) for vertex in self.vertices()]
        return self._contains_point(vertices, x, y)

    @staticmethod
    def _contains_point(vertices: list, x: float, y: float) -> bool:
        """
        Test whether raw coordinates contain a point.

        This internal form skips public argument validation and lets collision
        checks reuse vertices that have already been converted to numeric tuples.
        """

        count = 0
        n = len(vertices)

        p1x, p1y = vertices[0]
        for i in range(1, n + 1):
            # A cool trick that gets the next index in an array, or the first index if i is the last index.
            # (since we start at index 1)
            p2x, p2y = vertices[i % n]

            # make sure we're in the ballpark on the y-axis (actually able to intersect on the x-axis)
            if y > (p1y if p1y < p2y else p2y):

                # Same thing as above
                if y <= (p1y if p1y > p2y else p2y):

                    # Make sure our x is at least less than the max x of this line. (since we're travelling right)
                    if x <= (p1x if p1x > p2x else p2x):

                        # If our y's are equal, that means this line is flat on the x, which makes us tricked until now.
                        # We now realize we were never in the ballpark in the first place.
                        if p1y != p2y:

                            # Now we get a possible intersection point from left to right.
                            intersects_x = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x

                            # if the line was vertical or we actually intersected it
                            if p1x == p2x or x <= intersects_x:
                                count += 1

            # move up the ladder next vertices and edge
            p1x, p1y = p2x, p2y

        return not (count % 2 == 0)

    def overlaps(self, other: 'Renderable') -> bool:
        """
        Returns if this object is overlapping with the passed object.

        :param other: another Renderable instance.
        :return: true if they are overlapping, false if not.
        """

        if not isinstance(other, Renderable):
            raise TypeError('Passed non-renderable into Renderable#overlaps(), which takes only Renderables!')

        if self._visible:
            bounds = self.bounds()
        else:
            bounds = Location(self.x() - self.width() * .5, self.y() - self.height() * .5), self.width() * 1.5, self.height() * 1.5

        if other._visible:
            other_bounds = other.bounds()
        else:
            other_bounds = Location(other.x() - other.width() * .5, other.y() - other.height() * .5), other.width() * 1.5, other.height() * 1.5

        min_ax = bounds[0].x()
        max_ax = min_ax + bounds[1]

        min_bx = other_bounds[0].x()
        max_bx = min_bx + other_bounds[1]

        min_ay = bounds[0].y()
        max_ay = min_ay + bounds[2]

        min_by = other_bounds[0].y()
        max_by = min_by + other_bounds[2]

        a_left_b = max_ax < min_bx
        a_right_b = min_ax > max_bx
        a_above_b = min_ay > max_by
        a_below_b = max_ay < min_by

        # Only optimize if the angle is not zero.
        # if self._angle % 360 == 0 and other._angle % 360 == 0:
        #     min_ax = x
        #     max_ax = x + width
        #
        #     min_bx = other_x
        #     max_bx = other_x + other_width
        #
        #     min_ay = y
        #     max_ay = y + height
        #
        #     min_by = other_y
        #     max_by = other_y + other_height
        #
        #     a_left_b = max_ax < min_bx
        #     a_right_b = min_ax > max_bx
        #     a_above_b = min_ay > max_by
        #     a_below_b = max_ay < min_by
        # else:
        #     hypotenuse = math.sqrt(width ** 2 + height ** 2) + 1
        #     other_hypotenuse = math.sqrt(other_width ** 2 + other_height ** 2) + 1
        #
        #     center = Location(x + width / 2, y + height / 2)
        #     other_center = Location(other_x + other_width / 2, other_y + other_height / 2)
        #
        #     min_ax = center.x() - (hypotenuse / 2)
        #     max_ax = center.x() + (hypotenuse / 2)
        #
        #     min_bx = other_center.x() - (other_hypotenuse / 2)
        #     max_bx = other_center.x() + (other_hypotenuse / 2)
        #
        #     min_ay = center.y() - (hypotenuse / 2)
        #     max_ay = center.y() + (hypotenuse / 2)
        #
        #     min_by = other_center.y() - (other_hypotenuse / 2)
        #     max_by = other_center.y() + (other_hypotenuse / 2)
        #
        #     a_left_b = max_ax < min_bx
        #     a_right_b = min_ax > max_bx
        #     a_above_b = min_ay > max_by
        #     a_below_b = max_ay < min_by

        # Do a base check to make sure they are even remotely near each other.
        # TODO: Re-optimize with rotation in mind.
        # if other._angle % 360 == 0 and self._angle % 360 == 0:
        if a_left_b or a_right_b or a_above_b or a_below_b:
            return False

        vertices1 = None
        vertices2 = None
        shape1 = None
        shape2 = None

        # Check if one shape is entirely inside the other shape
        if (min_ax >= min_bx and max_ax <= max_bx) and (min_ay >= min_by and max_ay <= max_by):
            vertices1 = self.vertices()
            point = vertices1[0]
            vertices2 = other.vertices()
            shape2 = [(vertex.x(), vertex.y()) for vertex in vertices2]
            if self._contains_point(shape2, point.x(), point.y()):
                return True

        if (min_bx >= min_ax and max_bx <= max_ax) and (min_by >= min_ay and max_by <= max_ay):
            if vertices2 is None:
                vertices2 = other.vertices()
            point = vertices2[0]
            if vertices1 is None:
                vertices1 = self.vertices()
            shape1 = [(vertex.x(), vertex.y()) for vertex in vertices1]
            if self._contains_point(shape1, point.x(), point.y()):
                return True

        # Next we are going to use a sweeping line algorithm.
        # Essentially we will process the lines on the x-axis, one coordinate at a time (imagine a vertical line scan).
        # Then we will look for their orientations. We will essentially make sure its impossible they do not cross.
        # Pre-extract raw (x, y) floats once. The edge-vs-edge test below is
        # O(n*m) and previously called Location.x()/.y() millions of times on
        # high-vertex shapes; from here on we work on plain float tuples instead.
        if shape1 is None:
            if vertices1 is None:
                vertices1 = self.vertices()
            shape1 = [(vertex.x(), vertex.y()) for vertex in vertices1]
        if shape2 is None:
            if vertices2 is None:
                # noinspection PyProtectedMember
                vertices2 = other.vertices()
            shape2 = [(vertex.x(), vertex.y()) for vertex in vertices2]

        # Orientation method that will determine if it is a triangle (and in what direction [cc or ccw]) or a line.
        def orientation(point1, point2, point3) -> int:
            """
            Internal method that will determine the orientation of three points. They can be a clockwise triangle,
            counterclockwise triangle, or a co-linear line segment.

            :param point1: the first point of the main line segment
            :param point2: the second point of the main line segment
            :param point3: the third point to check from another line segment
            :return: the orientation of the passed points (1 clockwise, -1 counter-clockwise, 0 co-linear)
            """
            result = (float(point2[1] - point1[1]) * (point3[0] - point2[0])) - \
                     (float(point2[0] - point1[0]) * (point3[1] - point2[1]))

            if result > 0:
                return 1
            elif result < 0:
                return -1
            else:
                return 0

        def point_on_segment(point1, point2, point3) -> bool:
            """
            Returns if point3 lies on the segment formed by point1 and point2.
            """

            return max(point1[0], point3[0]) >= point2[0] >= min(point1[0], point3[0]) \
                   and max(point1[1], point3[1]) >= point2[1] >= min(point1[1], point3[1])

        # Okay to begin actually detecting orientations, we want to loop through some edges. But only ones that are
        # relevant. In order to do this we will first have to turn the list of vertices into a list of edges.
        # Then we will look through the lists of edges and find the ones closest to each other.

        shape1_edges = []
        shape2_edges = []

        shape1 = tuple(shape1[:]) + (shape1[0],)
        shape2 = tuple(shape2[:]) + (shape2[0],)

        shape1_point1 = shape1[0]
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)]  # 1, 2, 3, 3 % 5
            shape1_edges.append((shape1_point1, shape1_point2))
            shape1_point1 = shape1_point2

        shape2_point1 = shape2[0]
        for i in range(1, len(shape2)):
            shape2_point2 = shape2[i % len(shape2)]
            shape2_edges.append((shape2_point1, shape2_point2))
            shape2_point1 = shape2_point2

        # Now we are going to test the four orientations that the segments form.
        # For each edge of shape1 we compute its bounding box once, then skip any
        # edge of shape2 whose bounding box cannot touch it -- this prunes the vast
        # majority of the O(n*m) pairs when the shapes only meet (or miss) in a
        # small region, which is the common case.
        for edge1 in shape1_edges:
            p1, p2 = edge1
            e1_min_x = p1[0] if p1[0] < p2[0] else p2[0]
            e1_max_x = p1[0] if p1[0] > p2[0] else p2[0]
            e1_min_y = p1[1] if p1[1] < p2[1] else p2[1]
            e1_max_y = p1[1] if p1[1] > p2[1] else p2[1]

            for edge2 in shape2_edges:
                p3, p4 = edge2

                # Reject this pair if the two edges' bounding boxes don't overlap;
                # disjoint boxes can neither cross nor share a co-linear point.
                if e1_max_x < (p3[0] if p3[0] < p4[0] else p4[0]) or \
                        (p3[0] if p3[0] > p4[0] else p4[0]) < e1_min_x or \
                        e1_max_y < (p3[1] if p3[1] < p4[1] else p4[1]) or \
                        (p3[1] if p3[1] > p4[1] else p4[1]) < e1_min_y:
                    continue

                orientation1 = orientation(edge1[0], edge1[1], edge2[0])
                orientation2 = orientation(edge1[0], edge1[1], edge2[1])
                orientation3 = orientation(edge2[0], edge2[1], edge1[0])
                orientation4 = orientation(edge2[0], edge2[1], edge1[1])

                # If orientations 1 and 2 are strictly opposite as well as 3 and 4 then they intersect!
                # (Strict opposite signs -- a plain != would count a co-linear 0 as a crossing and
                # mis-fire on floating-point-collinear edges that don't actually touch.)
                if orientation1 * orientation2 < 0 and orientation3 * orientation4 < 0:
                    return True

                # There's some special cases we should check where a point from one segment is on the other segment
                if orientation1 == 0 and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True

                if orientation2 == 0 and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True

                if orientation3 == 0 and point_on_segment(edge2[0], edge1[0], edge2[1]):
                    return True

                if orientation4 == 0 and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False

    def _get_vertices(self):
        real_shape = self._vertices
        return real_shape

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occurred while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)')

        shape = self._shape  # List of normal vertices.

        width = self._width
        height = self._height

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO)

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape]

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy)

            vertex.move(self.x() + width / 2, self.y() + height / 2)

        self._vertices = vertices

        self._vertices = self._rotate(self._vertices, self._angle)
        self._register_render()

    def _rotate(self, vertices: list, angle: float, pivot: Location = None) -> list:
        # We have to update here since we cannot remember previous rotations (update method call won't cut it)!
        # vertices = self._vertices

        # First get some values that we're going to use later
        theta = math.radians(angle)
        cosine = math.cos(theta)
        sine = math.sin(theta)

        if pivot is None:
            centroid_x = self.center().x()
            centroid_y = self.center().y()
        else:
            centroid_x = pivot.x()
            centroid_y = pivot.y()

        new_vertices = []
        for vertex in vertices:
            # We have to create these separately because they're ironically used in each other's calculations xD
            old_x = vertex.x() - centroid_x
            old_y = vertex.y() - centroid_y

            new_x = (old_x * cosine - old_y * sine) + centroid_x
            new_y = (old_x * sine + old_y * cosine) + centroid_y
            new_vertices.append(Location(new_x, new_y))

        return new_vertices

    def _update_coords(self):
        shape = self._shape  # List of normal vertices.

        # Hoist per-object constants out of the vertex loops. (cx/cy were always
        # 0, so the old `(v - c) + c` was a no-op.)
        scale_x = self._width / PIXEL_RATIO
        scale_y = self._height / PIXEL_RATIO
        offset_x = self.x() + self._width / 2
        offset_y = self.y() + self._height / 2

        # Build the final vertices directly, instead of creating each Location
        # and then re-parsing args through moveto()/move() per vertex.
        vertices = [Location._raw(scale_x * vertex[0] + offset_x,
                                  -scale_y * vertex[1] + offset_y) for vertex in shape]

        if self._angle % 360 != 0:
            vertices = self._rotate(vertices, self._angle)
        self._vertices = vertices
        self._invalidate_render()

    def update(self):
        self._check()
        self._update_coords()
        self._last_angle = self._angle


class CustomRenderable(Renderable):
    """
    A wrapper class to distintify classes that extend Renderable but have some custom functionality.
    """
    pass


class RoundedRectangle(CustomRenderable):
    """
    A rectangle with rounded corners.
    """

    if TYPE_CHECKING:
        @_overload
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ..., radius: float = ...) -> None: ...

        @_overload
        def __init__(self, screen: Screen, location: Location, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ..., radius: float = ...) -> None: ...

        def __init__(self, *args, **kwargs) -> None: ...

    else:
        @overload(Screen, (int, float), (int, float), (int, float), (int, float),
                  Color, Color, bool, (int, float), bool, (int, float))
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True,
                     radius: float = 10):
            self._radius = self._validate_radius(radius)
            super().__init__(screen, x, y, width, height, color, border,
                             fill, rotation, visible)

        @overload(Screen, Location, (int, float), (int, float), Color, Color,
                  bool, (int, float), bool, (int, float))
        def __init__(self, screen: Screen, location: Location, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True,
                     radius: float = 10):
            self._radius = self._validate_radius(radius)
            super().__init__(screen, location.x(), location.y(), width, height,
                             color, border, fill, rotation, visible)

    def radius(self, radius: float = None) -> float:
        """
        Set the corner radius of the rounded shape in pixels.

        :param radius: the radius to set
        :return: the radius
        """

        if radius is not None:
            self._radius = self._validate_radius(radius)
            self._update_coords()

        return self._radius

    @staticmethod
    def _validate_radius(radius):
        verify(radius, (float, int))
        if radius < 0:
            raise InvalidArgumentError(
                'RoundedRectangle#radius(): radius must be non-negative.'
            )
        return radius

    def clone(self) -> 'RoundedRectangle':
        clone = RoundedRectangle(
            self._screen,
            self.x(),
            self.y(),
            self.width(),
            self.height(),
            self.color(),
            self.border(),
            self.fill(),
            self.rotation(),
            self.visible(),
            self.radius(),
        )
        clone.border_width(self.border_width())
        return clone

    def _setup(self):
        self._rebuild_vertices()
        self._register_render()

    def _rebuild_vertices(self):
        radius = min(self._radius, abs(self._width) / 2, abs(self._height) / 2)
        x = self.x()
        y = self.y()
        width = self._width
        height = self._height

        if radius == 0:
            vertices = [
                Location._raw(x, y),
                Location._raw(x + width, y),
                Location._raw(x + width, y + height),
                Location._raw(x, y + height),
            ]
        else:
            segments = max(2, min(8, int(math.ceil(radius / 4))))
            corners = (
                (x + width - radius, y + radius, -90),
                (x + width - radius, y + height - radius, 0),
                (x + radius, y + height - radius, 90),
                (x + radius, y + radius, 180),
            )
            vertices = []
            for center_x, center_y, start_angle in corners:
                for step in range(segments + 1):
                    angle = math.radians(start_angle + 90 * step / segments)
                    vertices.append(Location._raw(
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle),
                    ))

        if self._angle % 360 != 0:
            vertices = self._rotate(vertices, self._angle)
        self._vertices = vertices

    def _update_coords(self):
        self._rebuild_vertices()
        self._invalidate_render()

    def update(self):
        self._check()
        self._update_coords()


# noinspection PyProtectedMember
class CustomPolygon(CustomRenderable):
    """
    An Irregular Polygon that is passed a list of vertices that can be rotated and translated!
    """

    # The below "# noqa" removes a small inspection by pycharm as it complains we do not call the constructor.
    def __init__(self, screen: Screen, vertices: list,  # noqa
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._screen = screen
        self._color = color
        self._border = border if border is not None else Color.NONE
        self._border_width = 1
        self._fill = fill
        self._angle = rotation
        self._visible = visible

        self._screen._add(self)

        if len(vertices) < 3:
            raise InvalidArgumentError(
                'CustomPolygon(): expected at least three vertices.'
            )

        xmin = vertices[0][0]
        xmax = vertices[0][0]
        ymin = vertices[0][1]
        ymax = vertices[0][1]

        real_vertices = []
        for vertex in vertices:
            new_vertex = Location(vertex[0], vertex[1])
            real_vertices.append(new_vertex)

            if new_vertex.x() < xmin:
                xmin = new_vertex.x()
            if new_vertex.x() > xmax:
                xmax = new_vertex.x()

            if new_vertex.y() < ymin:
                ymin = new_vertex.y()
            if new_vertex.y() > ymax:
                ymax = new_vertex.y()

        self._vertices = real_vertices
        self._current_vertices = [vertex.clone() for vertex in real_vertices]

        # Pending translation not yet folded into _current_vertices. move() just
        # accumulates the delta here (O(1)); vertices() applies it once, lazily,
        # collapsing any run of moves into a single pass. See _flush_vertices().
        self._vertex_offset = [0.0, 0.0]

        self._location = Location(xmin, ymin)
        self._base_width = self._width = xmax - xmin
        self._base_height = self._height = ymax - ymin

        self._base_location = self._location.clone()
        self._base_center = Location(
            sum(vertex.x() for vertex in self._vertices) / len(self._vertices),
            sum(vertex.y() for vertex in self._vertices) / len(self._vertices),
        )

        self._register_render()

        if self._angle % 360 != 0:
            self._update_coords()

        self._pen = None

    @_overload
    def move(self, dx: float, dy: float) -> None: ...

    @_overload
    def move(self, location: Location) -> None: ...

    @_overload
    def move(self, dxy: Tuple[float, float]) -> None: ...

    @_overload
    def move(self, *, dx: float = ..., dy: float = ...) -> None: ...

    def move(self, *args, **kwargs):
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.move(*args, **kwargs)  # Does the arg parsing for us

        # Use a relative canvas move (exact) rather than moveto(), which
        # positions by the item's bounding box and lands 1px off because the
        # outline inflates the bbox beyond the geometry coordinates.
        dx = self._location._x - before_x
        dy = self._location._y - before_y
        if dx == 0 and dy == 0:
            return
        self._vertex_offset[0] += dx
        self._vertex_offset[1] += dy
        self._invalidate_render()
        self._sync_pen()

    @_overload
    def moveto(self, x: float, y: float) -> None: ...

    @_overload
    def moveto(self, location: Location) -> None: ...

    @_overload
    def moveto(self, xy: Tuple[float, float]) -> None: ...

    @_overload
    def moveto(self, *, x: float = ..., y: float = ...) -> None: ...

    def moveto(self, *args, **kwargs):
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.moveto(*args, **kwargs)

        # Relative canvas move by the delta (see move() for why not moveto()).
        dx = self._location._x - before_x
        dy = self._location._y - before_y
        if dx == 0 and dy == 0:
            return
        self._vertex_offset[0] += dx
        self._vertex_offset[1] += dy
        self._invalidate_render()
        self._sync_pen()

    def width(self, width: float = None) -> float:
        """
        Get the width of the CustomPolygon

        :param width: the new width to scale to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int))

            if self._width == width:
                return width

            self._width = width
            self._update_coords()

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get the height of the Polygon

        :param height: The new height to scale to in px.
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int))

            if self._height == height:
                return height

            self._height = height
            self._update_coords()

        return self._height

    def rotate(self, angle_diff: float = 0) -> None:
        verify(angle_diff, (float, int))

        if angle_diff == 0:
            return

        self._angle += angle_diff

        if self._angle >= 360:
            self._angle = self._angle % 360

        self._update_coords()

    def rotation(self, angle: float = None) -> float:
        """
        Gets or sets the rotation of the CustomPolygon.

        :param angle: the angle to rotate the polygon to
        :return: the angle that was set
        """

        if angle is not None:
            verify(angle, (float, int))

            if angle % 360 == self._angle % 360:
                return self._angle

            self._angle = angle
            self._update_coords()

        return self._angle

    def _center(self, move_to: Location = None, centroid: bool = False) -> Location:
        if not centroid:
            center = Location(
                self._location.x() + self._width / 2,
                self._location.y() + self._height / 2,
            )

            if move_to is not None:
                verify(move_to, Location)
                self.move(move_to.x() - center.x(), move_to.y() - center.y())
                center.moveto(move_to)

            return center

        # We are going to create a centroid, so we can rotate the points around a realistic center
        # Sorry for those of you that get weird rotations..
        x_list = []
        y_list = []
        for vertex in self.vertices():
            x_list.append(vertex.x())
            y_list.append(vertex.y())

        # Create a simple centroid (not full centroid)
        centroid_x = sum(x_list) / len(y_list)
        centroid_y = sum(y_list) / len(x_list)

        center = Location(centroid_x, centroid_y)

        if move_to is not None:
            verify(move_to, Location)
            self.move(move_to.x() - center.x(), move_to.y() - center.y())
            center.moveto(move_to)

        return center

    def _flush_vertices(self) -> None:
        # Fold any pending translation into the cached vertices. Called by every
        # path that reads live geometry, so a run of moves collapses into a
        # single O(n) pass here instead of one pass per move.
        dx, dy = self._vertex_offset
        if dx or dy:
            for vertex in self._current_vertices:
                vertex._x += dx
                vertex._y += dy
            self._vertex_offset[0] = 0.0
            self._vertex_offset[1] = 0.0

    def vertices(self) -> list:
        # Collision loops (contains/overlaps) call this repeatedly. Moves only
        # accumulate an offset; we apply it here, once, then reuse the cached
        # list until the object moves again.
        self._flush_vertices()
        return self._current_vertices

    def clone(self) -> 'CustomPolygon':
        """
        Clone this CustomPolygon!

        :return: a CustomPolygon
        """

        poly = CustomPolygon(self._screen, self._vertices, self._color, self._border, self._fill, 0,
                             self._visible)
        poly.transform(self.transform())
        poly.moveto(self.location())

        return poly

    def _update_coords(self):
        """Rebuild the live geometry from the immutable base vertices and transform."""
        self._check()

        # _location already includes every lazy translation.
        self._vertex_offset[0] = 0.0
        self._vertex_offset[1] = 0.0

        scale_factor = (
            self._width / self._base_width if self._base_width != 0 else 0,
            self._height / self._base_height if self._base_height != 0 else 0,
        )

        centroid_x = self._location.x() + (
            self._base_center.x() - self._base_location.x()
        ) * scale_factor[0]
        centroid_y = self._location.y() + (
            self._base_center.y() - self._base_location.y()
        ) * scale_factor[1]

        theta = math.radians(self._angle)
        cosine = math.cos(theta)
        sine = math.sin(theta)

        rotated = self._angle % 360 != 0

        for index, vertex in enumerate(self._vertices):
            old_x = self._location.x() + (
                vertex.x() - self._base_location.x()
            ) * scale_factor[0]
            old_y = self._location.y() + (
                vertex.y() - self._base_location.y()
            ) * scale_factor[1]

            if rotated:
                relative_x = old_x - centroid_x
                relative_y = old_y - centroid_y
                new_x = relative_x * cosine - relative_y * sine + centroid_x
                new_y = relative_x * sine + relative_y * cosine + centroid_y
            else:
                new_x = old_x
                new_y = old_y

            current_vertex = self._current_vertices[index]
            current_vertex._x = new_x
            current_vertex._y = new_y

        self._invalidate_render()

    def update(self):
        self._check()
        self._update_coords()


class Rectangle(Renderable):

    # Two constructor forms: (x, y) and (location). The dispatcher honors
    # default arguments, so each full signature also covers every shorter call
    # that omits trailing optional args (color, border, fill, rotation, visible).
    if TYPE_CHECKING:
        @_overload
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        @_overload
        def __init__(self, screen: Screen, location: Location, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        def __init__(self, *args, **kwargs) -> None: ...

    else:
        @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                              Location(x, y + height)]
            self._shape = ((-10, 10), (10, 10), (10, -10), (-10, -10))
            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

        @overload(Screen, Location, (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, location: Location, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            x = location.x()
            y = location.y()

            self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                              Location(x, y + height)]
            self._shape = ((-10, 10), (10, 10), (10, -10), (-10, -10))
            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)


class Oval(Renderable):

    _default = ((10, 0), (9.51, 3.09), (8.09, 5.88),
                (5.88, 8.09), (3.09, 9.51), (0, 10), (-3.09, 9.51),
                (-5.88, 8.09), (-8.09, 5.88), (-9.51, 3.09), (-10, 0),
                (-9.51, -3.09), (-8.09, -5.88), (-5.88, -8.09),
                (-3.09, -9.51), (-0.00, -10.00), (3.09, -9.51),
                (5.88, -8.09), (8.09, -5.88), (9.51, -3.09))

    # Two constructor forms: (x, y) and (location). The dispatcher honors
    # default arguments, so each full signature also covers every shorter call.
    if TYPE_CHECKING:
        @_overload
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        @_overload
        def __init__(self, screen: Screen, location: Location, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        def __init__(self, *args, **kwargs) -> None: ...

    else:
        @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            self._width = width
            self._height = height
            self._custom_wedges = False

            vertices = self._convert_vertices()
            self._shape = vertices
            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

        @overload(Screen, Location, (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, location: Location, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            x = location.x()
            y = location.y()

            self._width = width
            self._height = height
            self._custom_wedges = False

            vertices = self._convert_vertices()
            self._shape = vertices
            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the object.

        :param width: the width to set to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int))
            self._width = width
            self._update_coords()

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the object.

        :param height: the width to set to in pixels, if any
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int))
            self._height = height
            self._update_coords()

        return self._height

    def wedges(self, wedges: int = None) -> int:
        if wedges is not None:
            verify(wedges, int)
            if wedges < 20:
                raise InvalidArgumentError('Oval(): wedges must be at least 20.')
            self._shape = self._generate_vertices(PIXEL_RATIO / 2, wedges=wedges)
            self._wedges = wedges
            self._custom_wedges = True
            self._update_coords()

        return self._wedges

    def slices(self) -> list:
        """
        Gets the slices of the Oval based on wedges. Note that this generates slices that are not tied to the oval,
        these are simply slices of the oval based on its wedges. You can use them how you see fit.

        :return: a tuple (immutable list) of CustomPolygons
        """

        return self._generate_slices()

    def _generate_slices(self) -> list:
        shape = self.vertices()
        shape = tuple(shape[:]) + (shape[0],)

        slices = []
        for i in range(0, len(shape) - 1):
            vertex1 = shape[i]
            vertex2 = self.center()
            vertex3 = shape[i + 1]

            slc = CustomPolygon(self._screen, [vertex1, vertex2, vertex3], self.color())
            slices.append(slc)
        return slices

    def _convert_vertices(self):
        radius = ((self._width + self._height) / 2) / 2
        angle = 18 if radius <= 150 else (radius * 9) / 300
        shape_vertices = self._generate_vertices(PIXEL_RATIO / 2, angle)

        # Report the wedge count actually generated (size-dependent), not a fixed default.
        self._wedges = len(shape_vertices)

        return shape_vertices

    def _render_node(self):
        return EllipseNode(
            self._render_id,
            (self.x() + self._width / 2, self.y() + self._height / 2),
            self._width / 2,
            self._height / 2,
            self._angle,
            tuple((vertex.x(), vertex.y()) for vertex in self.vertices()),
            self._custom_wedges,
            self._render_color(self._color) if self._fill else None,
            self._render_color(self._border),
            self._border_width,
            self._visible,
        )

    @staticmethod
    def _generate_vertices(radius, angle: float = 18, wedges: int = None):
        relative_vertices = []

        if wedges is not None:
            angle = 360 / wedges

        for x in range(0, 360, int(angle)):
            radians = math.radians(x)
            x = radius * math.cos(radians)
            y = radius * math.sin(radians)
            relative_vertices.append((x, y))

        return relative_vertices


class Triangle(Renderable):

    # Two constructor forms: (x, y) and (location). The dispatcher honors
    # default arguments, so each full signature also covers every shorter call.
    if TYPE_CHECKING:
        @_overload
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        @_overload
        def __init__(self, screen: Screen, location: Location, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        def __init__(self, *args, **kwargs) -> None: ...

    else:
        @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            self._shape = ((10, -10), (0, 10), (-10, -10))
            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

        @overload(Screen, Location, (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, location: Location, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            x = location.x()
            y = location.y()

            self._shape = ((10, -10), (0, 10), (-10, -10))
            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)


class Polygon(Renderable):

    _num_sides: int
    _shape: tuple

    # Two constructor forms: (num_sides, x, y) and (num_sides, location). The
    # dispatcher honors default arguments, so each full signature also covers
    # every shorter call.
    if TYPE_CHECKING:
        @_overload
        def __init__(self, screen: Screen, num_sides: int, x: float, y: float, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        @_overload
        def __init__(self, screen: Screen, num_sides: int, location: Location, width: float, height: float, color: Color = ..., border: Optional[Color] = ..., fill: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        def __init__(self, *args, **kwargs) -> None: ...

    else:
        @overload(Screen, int, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, num_sides: int, x: float, y: float, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            if num_sides < 3:
                raise InvalidArgumentError('Polygon(): num_sides must be at least 3.')

            self._num_sides = num_sides
            radius = PIXEL_RATIO / 2
            shape_points = []
            for i in range(num_sides):
                shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                     radius * math.cos(2 * math.pi / num_sides * i)))
            self._shape = shape_points

            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

        @overload(Screen, int, Location, (int, float), (int, float), Color, Color, bool, int, bool)
        def __init__(self, screen: Screen, num_sides: int, location: Location, width: float, height: float,
                     color: Color = Color('black'),
                     border: Color = None,
                     fill: bool = True,
                     rotation: float = 0,
                     visible: bool = True):
            if num_sides < 3:
                raise InvalidArgumentError('Polygon(): num_sides must be at least 3.')

            x = location.x()
            y = location.y()

            self._num_sides = num_sides
            radius = PIXEL_RATIO / 2
            shape_points = []
            for i in range(num_sides):
                shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                     radius * math.cos(2 * math.pi / num_sides * i)))
            self._shape = shape_points

            super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occured while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)')

        shape = self._shape  # List of normal vertices.

        a = math.pi * 2 / self._num_sides * (PIXEL_RATIO / 2)
        n = self._num_sides

        # Degree converted to radians
        apothem = a / (2 * math.tan((180 / n) *
                                    math.pi / 180))

        true_width = PIXEL_RATIO
        true_height = apothem * 2

        width = self._width
        height = self._height

        scale_factor = (width / true_width, height / true_height)

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape]

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy)

            vertex.move(self.x() + width / 2, self.y() + height / 2)
            vertex.move(dy=PIXEL_RATIO - true_height)

        self._vertices = vertices

        self._vertices = self._rotate(self._vertices, self._angle)
        self._register_render()
    
    def clone(self) -> 'Polygon':
        """
        Clone this Polygon!

        :return a Polygon
        """
        return Polygon(self._screen, self._num_sides, self.x(), self.y(), self.width(), self.height(), self.color(), self.border(), self.fill(), self.rotation(), self.visible())

    # noinspection PyProtectedMember
    def update(self):
        self._check()
        shape = self._shape  # List of normal vertices.

        a = math.pi * 2 / self._num_sides * (PIXEL_RATIO / 2)
        n = self._num_sides

        # Degree converted to radians
        apothem = a / (2 * math.tan((180 / n) *
                                    math.pi / 180))

        true_width = PIXEL_RATIO
        true_height = apothem * 2

        width = self._width
        height = self._height

        scale_factor = (width / true_width, height / true_height)

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape]

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy)

            vertex.move(self.x() + width / 2, self.y() + height / 2)
            vertex.move(dy=PIXEL_RATIO - true_height)

        self._vertices = vertices

        self._vertices = self._rotate(self._vertices, self._angle)
        self._invalidate_render()


class Image(Renderable):
    """
    Image class. Supports basic formats: PNG, GIF, JPG, PPM, images.

    NOTE: This class supports the basic displaying of images, but also supports much more,
    such as image modification (width, height, color, etc) if you have PIL (Pillow) installed!
    You can install PIL/Pillow by running: `pip install pillow` in a terminal!
    """

    # (x, y) INITIALIZERS

    # Two constructor forms: (x, y) and (location). The dispatcher honors default
    # arguments, so each full signature also covers every shorter call. Only the
    # screen and image path are required; x, y, width and height all default.
    if TYPE_CHECKING:
        @_overload
        def __init__(self, screen: Screen, image: str, x: float = ..., y: float = ..., width: Optional[float] = ..., height: Optional[float] = ..., color: Optional[Color] = ..., border: Color = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        @_overload
        def __init__(self, screen: Screen, image: str, location: Location, width: Optional[float] = ..., height: Optional[float] = ..., color: Optional[Color] = ..., border: Color = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        def __init__(self, *args, **kwargs) -> None: ...

    else:
        @overload(Screen, str, (int, float), (int, float), (int, float), (int, float), Color, Color, int, bool)
        def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
                     width: float = None,
                     height: float = None,
                     color: Color = None,
                     border: Color = Color.NONE,
                     rotation: float = 0,
                     visible: bool = True):
            self._init_image(screen, image, x, y, width, height, color, border, rotation, visible)

        @overload(Screen, str, Location, (int, float), (int, float), Color, Color, int, bool)
        def __init__(self, screen: Screen, image: str, location: Location,
                     width: float = None,
                     height: float = None,
                     color: Color = None,
                     border: Color = Color.NONE,
                     rotation: float = 0,
                     visible: bool = True):
            self._init_image(screen, image, location.x(), location.y(),
                             width, height, color, border, rotation, visible)

    def _init_image(self, screen, image, x, y, width, height, color, border, rotation, visible):
        self._image_name = image

        self._width, self._height = screen._backend.measure_image(image)

        if width is not None:
            verify(width, (float, int))
        if height is not None:
            verify(height, (float, int))

        if width is not None and height is None:
            height = self._height * width / self._width
        elif height is not None and width is None:
            width = self._width * height / self._height

        if width is not None:
            self._width = width
        if height is not None:
            self._height = height

        self._frame = -1
        self._frames = -1

        self._mask = 123

        # Resample quality for resize/rotate. True (default) keeps the smooth
        # LANCZOS/BILINEAR filters; False uses NEAREST, which is ~13x cheaper on
        # rotation and ideal for pixel-art sprites in a game loop.
        self._smooth = True

        # Flips are retained as source-image state so they survive later image
        # rebuilds caused by resizing, tinting, borders, rotation, or GIF frames.
        self._flip_x = False
        self._flip_y = False

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible)

        if color is not None:
            self.color(color)

        if border is not None and border != Color.NONE:
            self.border(border)

    # noinspection PyProtectedMember
    def _setup(self):
        self._vertices = self.vertices()
        self._register_render()

    def _render_node(self):
        return ImageNode(
            self._render_id,
            self._image_name,
            (self.x(), self.y()),
            self._width,
            self._height,
            self._angle,
            None if self._color == Color.NONE else self._color.rgb(),
            self._mask,
            None if self._border == Color.NONE else self._border.rgb(),
            self._smooth,
            self._flip_x,
            self._flip_y,
            self._frame,
            self._visible,
        )

    # def moveto(self, *args, **kwargs) -> None:
    #     """
    #     Move to a new location takes a Location, tuple, or two numbers (x, y)
    #     :return: None
    #     """
    #
    #     self._location.moveto(*args, **kwargs)
    #
    #     # self._update_coords()
    #     self.update()

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the image (REQUIRES: PIL or Pillow)

        :param width: the width to set to, if any
        :return: None
        """

        if width is not None:
            verify(width, (float, int))

            if self._width == width:
                return width

            self._width = width
            self.update(True)

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the image

        :param height: the height to set to, if any
        :return: the height
        """

        if height is not None:
            verify(height, (float, int))

            if self._height == height:
                return height

            self._height = height
            self.update(True)

        return self._height

    def color(self, color: Color = None, alpha: int = 123) -> Color:
        """
        Retrieves or applies a color-mask to the image

        :param color: the color to mask to, if any
        :param alpha: Tint intensity from 0 (original colors) to 255 (full tint), defaults to 123
        :return: the mask-color of the object
        """

        if color is not None:
            verify(color, Color, alpha, int)
            if alpha < 0 or alpha > 255:
                raise InvalidArgumentError(
                    'Image#color(): alpha must be between 0 and 255.'
                )

            if self._color == color and self._mask == alpha:
                return self._color

            self._color = color
            self._mask = alpha
            self.update(True)

        return self._color

    def smooth(self, smooth: bool = None) -> bool:
        """
        Get or set the resampling quality used when resizing/rotating the image.

        True (default) uses smooth filters (LANCZOS/BILINEAR); False uses NEAREST,
        which is dramatically faster (~13x on rotation) and crisp for pixel-art
        sprites - ideal in a game loop.

        :param smooth: True for smooth, False for fast/nearest, if setting
        :return: whether smooth resampling is enabled
        """

        if smooth is not None:
            verify(smooth, bool)
            self._smooth = smooth
            self.update(True)

        return self._smooth

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the image.

        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the image's rotation in degrees
        """

        if angle is not None:
            verify(angle, (float, int))

            if self._angle == angle:
                return angle % 360

            self._angle = angle
            self.update(True)

        return self._angle % 360

    # noinspection PyMethodOverriding
    def rotate(self, angle_diff: float) -> None:
        """
        Rotate the angle of the image by a difference, in degrees

        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        if angle_diff != 0:
            verify(angle_diff, (float, int))
            self._angle += angle_diff
            self.update(True)

    def transform(self, transform: tuple = None) -> tuple:
        """
        Get or set the transform of the Image.
        Transforms represent the width, height, and rotation of the Image.

        You can retrieve a Transform from an Image with this method and set the transform the same way.

        :param transform: the transform to set to, if any.
        :return: the transform
        """

        if transform is not None:
            verify(transform, tuple)
            if not len(transform) == 3:
                raise InvalidArgumentError(
                    'Image#transform(): expected (width, height, rotation).'
                )
            verify(transform[0], (float, int), transform[1], (float, int), transform[2], (float, int))

            update_width = transform[0] != self._width
            update_height = transform[1] != self._height
            update_rotation = transform[2] % 360 != self._angle % 360

            if not update_width and not update_height and not update_rotation:
                return self._width, self._height, self._angle % 360

            self._width = transform[0]
            self._height = transform[1]
            self._angle = transform[2]

            self.update(True)

        return self._width, self._height, self._angle % 360



    @_overload
    def center(self, x: float, y: float, *, centroid: bool = ...) -> Location: ...

    @_overload
    def center(self, location: Location, *, centroid: bool = ...) -> Location: ...

    @_overload
    def center(self, *, move_to: Location = ..., x: float = ..., y: float = ..., centroid: bool = ...) -> Location: ...

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center

        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Image
        """

        verify_keywords(kwargs, ('move_to', 'x', 'y'), 'Image#center()')

        if len(args) == 0 and len(kwargs) == 0:
            return self._center()

        location = Location(self._center())
        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0])
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError('Image#center(): expected both x and y.')
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )

                location.moveto(args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Image#center(): expected a tuple/Location or two numbers (x, y).'
                )

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to'])
                else:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x'])
                else:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y'])
                else:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )

        return self._center(location)

    def _center(self, moveto: Location = None) -> Location:
        if moveto is not None:
            verify(moveto, Location)
            self.moveto(moveto.x() - self.width() / 2, moveto.y() - self.height() / 2)

        return Location(self.x() + self.width() / 2, self.y() + self.height() / 2)

    # noinspection PyMethodOverriding
    def border(self, color: Color = None) -> Color:
        """
        Add or get the border of the image

        :param color: the color to set the border too, set to Color.NONE to remove border
        :return: The Color of the border
        """

        if color is not None:
            verify(color, Color)
            self._border = color
            self.update(True)

        return self._border

    def fill(self, fill: bool = None) -> bool:
        """
        Unsupported: This doesn't make sense for images.
        """

        raise UnsupportedError('Image#fill(): fill is unsupported for images.')

    def vertices(self) -> list:
        """
        Returns the list of vertices for the Renderable.
        (The vertices will be returned clockwise, starting from the top-leftmost point)

        :return: a list of Locations representing the vertices
        """

        # Note: the first vertex is a clone of the location, not self.location()
        # itself - _setup() caches vertices() into self._vertices, and
        # _translate() shifts every cached vertex in place. Aliasing the live
        # location here would let a move shift it twice (once via _location.move,
        # once via the vertex loop), doubling the displacement. The remaining
        # vertices are built from known numbers, so we use the _raw fast path.
        x = self.x()
        y = self.y()
        w = self.width()
        h = self.height()
        vertices = [self.location().clone(), Location._raw(x + w, y),
                    Location._raw(x + w, y + h),
                    Location._raw(x, y + h)]

        if self._angle != 0:

            # First get some values that we're going to use later
            theta = math.radians(self._angle)
            cosine = math.cos(theta)
            sine = math.sin(theta)

            center_x = x + w / 2
            center_y = y + h / 2

            new_vertices = []
            for vertex in vertices:
                # We have to create these separately because they're ironically used in each other's calculations xD
                old_x = vertex.x() - center_x
                old_y = vertex.y() - center_y

                new_x = (old_x * cosine - old_y * sine) + center_x
                new_y = (old_x * sine + old_y * cosine) + center_y
                new_vertices.append(Location._raw(new_x, new_y))

            vertices = new_vertices

        return vertices

    def flip(self, axis: str = 'y') -> None:
        """
        Flip the image across an axis.

        Flipping across the x-axis reverses the image vertically; flipping
        across the y-axis reverses it horizontally. Calling this method again
        with the same axis restores the original orientation.

        Requires PIL/Pillow.

        :param axis: the axis to flip across, either ``'x'`` or ``'y'``
        :return: None
        """

        verify(axis, str)
        axis = axis.lower()
        if axis == 'x':
            self._flip_x = not self._flip_x
        elif axis == 'y':
            self._flip_y = not self._flip_y
        else:
            raise InvalidArgumentError("Image#flip(): axis must be 'x' or 'y'.")

        self.update(True)

    def load(self) -> None:
        """
        Load animated GIF (reads frames)

        :return: None
        """

        self._frames = self._screen._backend.image_frames(self._image_name)
        self._frame = 0
        self._invalidate_render()

    def next(self) -> None:
        """
        Changes frame to the next frame (Can only be used with animated GIFs)

        :return:
        """
        self._frame += 1

        if self._frame >= self._frames:
            self._frame = 0

        self.update(True)

    def frame(self, frame: int = None) -> int:
        """
        Set the current frame.

        :param frame: the frame-index to set to
        :return: the current frame
        """

        if frame is not None:
            self._frame = frame
            self.update(True)

        return self._frame

    def frames(self) -> int:
        """
        Returns how many frames there are, returns -1 if not animated, 0 if corrupted file.

        :return:
        """

        return self._frames

    def clone(self) -> 'Image':
        constructor = type(self)
        clone = constructor(self._screen, self._image_name, self.x(), self.y(), self.width(), self.height(),
                            self.color(), self.border(), self.rotation(), self.visible())
        clone._flip_x = self._flip_x
        clone._flip_y = self._flip_y
        if clone._flip_x or clone._flip_y:
            clone._invalidate_render()

        return clone

    def _update_coords(self):
        """
        Usually used to update x/y or vertices, but in this case we just update our width and height
        """
        self._check()
        self._vertices = self.vertices()
        self._invalidate_render()


    # noinspection PyProtectedMember
    def update(self, updated: bool = False):
        self._check()
        self._vertices = self.vertices()
        self._invalidate_render()


class Text(CustomRenderable):
    _aligns = ('left', 'center', 'right')

    # Four constructor forms ((x, y)/(location), each with optional Color) defer to _init_text.
    # noinspection PyProtectedMember
    if TYPE_CHECKING:
        @_overload
        def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = ..., font: str = ..., size: int = ..., align: str = ..., bold: bool = ..., italic: bool = ..., underline: bool = ..., strikethrough: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        @_overload
        def __init__(self, screen: Screen, text: str, location: Location, color: Color = ..., font: str = ..., size: int = ..., align: str = ..., bold: bool = ..., italic: bool = ..., underline: bool = ..., strikethrough: bool = ..., rotation: float = ..., visible: bool = ...) -> None: ...

        def __init__(self, *args, **kwargs) -> None: ...

    else:
        @overload(Screen, str, (int, float), (int, float))
        def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = Color('black'),  # noqa
                     font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                     underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
            self._init_text(screen, text, x, y, color, font, size, align,
                            bold, italic, underline, strikethrough, rotation, visible)

        @overload(Screen, str, (int, float), (int, float), Color)
        def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = Color('black'),  # noqa
                     font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                     underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
            self._init_text(screen, text, x, y, color, font, size, align,
                            bold, italic, underline, strikethrough, rotation, visible)

        @overload(Screen, str, Location)
        def __init__(self, screen: Screen, text: str, location: Location, color: Color = Color('black'),  # noqa
                     font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                     underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
            self._init_text(screen, text, location.x(), location.y(), color, font, size, align,
                            bold, italic, underline, strikethrough, rotation, visible)

        @overload(Screen, str, Location, Color)
        def __init__(self, screen: Screen, text: str, location: Location, color: Color = Color('black'),  # noqa
                     font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                     underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
            self._init_text(screen, text, location.x(), location.y(), color, font, size, align,
                            bold, italic, underline, strikethrough, rotation, visible)

    # noinspection PyProtectedMember
    def _init_text(self, screen, text, x, y, color, font, size, align,
                   bold, italic, underline, strikethrough, rotation, visible):
        self._screen = screen
        self._location = Location(x, y)
        self._screen._add(self)

        self._text = text if text is not None else ''
        self._color = color
        self._font = font
        self._size = size
        self._align = align
        self._bold = bold
        self._italic = italic
        self._underline = underline
        self._strikethrough = strikethrough
        self._angle = rotation
        self._visible = visible
        self._pen = None

        verify(screen, Screen, text, str, x, (float, int), y, (float, int), color, Color, font, str, size, int,
               align, str, bold, bool, italic, bool, underline, bool, strikethrough, bool, rotation, (float, int),
               visible, bool)

        true_width, true_height = self._calculate_transform()
        self._width = true_width
        self._height = true_height * (self._text.count('\n') + 1)
        self._register_render()

    def _place(self) -> tuple:
        # Canvas anchor (x, y); the width offset keeps rotation pivoting about the center.
        hypotenuse = self._width / 2
        radians = math.radians(self._angle)
        dx = math.cos(radians) * hypotenuse
        dy = math.sin(radians) * hypotenuse

        return self.x() + self._width / 2 - 1 - dx, self.y() - dy

    def _render_node(self):
        return TextNode(
            self._render_id,
            self._place(),
            self._text,
            self._color.rgb(),
            self._font,
            self._size,
            self._align,
            self._bold,
            self._italic,
            self._underline,
            self._strikethrough,
            self._angle,
            self._visible,
        )

    def text(self, text: str = None) -> str:
        """
        Get or set the text. Use '\\n' to separate lines.

        :param text: text to set to (str), if any
        :return: the text
        """

        if text is not None:
            verify(text, str)
            if self._text == text:
                return self._text
            self._text = text
            self._update_coords()

        return self._text

    @_overload
    def move(self, dx: float, dy: float) -> None: ...

    @_overload
    def move(self, location: Location) -> None: ...

    @_overload
    def move(self, dxy: Tuple[float, float]) -> None: ...

    @_overload
    def move(self, *, dx: float = ..., dy: float = ...) -> None: ...

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.move(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    @_overload
    def moveto(self, x: float, y: float) -> None: ...

    @_overload
    def moveto(self, location: Location) -> None: ...

    @_overload
    def moveto(self, xy: Tuple[float, float]) -> None: ...

    @_overload
    def moveto(self, *, x: float = ..., y: float = ...) -> None: ...

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.moveto(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    def _translate(self, dx: float, dy: float) -> None:
        """
        Shift the text by (dx, dy) while retaining its geometry.
        """

        if dx == 0 and dy == 0:
            return

        self._invalidate_render()
        self._sync_pen()

    # noinspection PyMethodOverriding
    def width(self) -> float:
        """
        Get the width of the text (cannot be modified)

        :return the width of the text
        """

        return self._width

    # noinspection PyMethodOverriding
    def height(self) -> float:
        """
        Get the height of the text, (cannot be modified, although technically the font-size is the text's height)

        :return: the height of the text.
        """

        return self._height

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the text

        :param color: the color to set to, if any
        :return: the color of the text
        """

        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            self._invalidate_render()

        return self._color

    def font(self, font: str = None) -> str:
        """
        Get or set the font of the text

        :param font: the font to set to, if any
        :return: the font of the text
        """

        if font is not None:
            verify(font, str)
            self._font = font
            self._update_font()
            # self.update()

        return self._font

    def size(self, size: int = None) -> int:
        """
        Get or set the size of the text

        :param size: the size to set to, if any
        :return: the size of the text
        """

        if size is not None:
            verify(size, int)
            self._size = size
            self._update_font()
            # self.update()

        return self._size

    def align(self, align: str = None) -> str:
        """
        Get or set the alignment of the text, if a new value is passed it must be 'left', 'center', or 'right'.

        :param align: the alignment to set to, if any
        :return: the alignment of the text
        """

        if align is not None:
            verify(align, str)
            if align.lower() not in self._aligns:
                raise PydrawError(
                    f"Text#align(): expected 'left', 'center', or 'right'; received '{align}'."
                )

            self._align = align.lower()
            self._invalidate_render()

        return self._align

    def bold(self, bold: bool = None) -> bool:
        """
        Get or set the bold status of the text

        :param bold: the bold status to set to, if any
        :return: the bold status of the text
        """

        if bold is not None:
            verify(bold, bool)
            self._bold = bold
            self._update_font()
            # self.update()

        return self._bold

    def italic(self, italic: bool = None) -> bool:
        """
        Get or set the italic status of the text

        :param italic: the italic status to set to, if any
        :return: the italic status of the text
        """

        if italic is not None:
            verify(italic, bool)
            self._italic = italic
            self._update_font()
            # self.update()

        return self._italic

    def underline(self, underline: bool = None) -> bool:
        """
        Get or set the underline status of the text

        :param underline: the underline status to set to, if any
        :return: the underline status of the text
        """

        if underline is not None:
            verify(underline, bool)
            self._underline = underline
            self._update_font()
            # self.update()

        return self._underline

    def strikethrough(self, strikethrough: bool = None) -> bool:
        """
        Get or set the strikethrough status of the text

        :param strikethrough: the strikethrough status to set to, if any
        :return: the strikethrough status of the text
        """

        if strikethrough is not None:
            verify(strikethrough, bool)
            self._strikethrough = strikethrough
            self._update_font()
            # self.update()

        return self._strikethrough

    def rotation(self, rotation: float = None) -> float:
        """
        Get or set the rotation of the text

        :param rotation: the strikethrough to set to, if any
        :return: the rotation of the text
        """

        if rotation is not None:
            verify(rotation, (float, int))
            self._angle = rotation
            self._invalidate_render()

        return self._angle

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the text by a difference, in degrees

        :param angle_diff: the angle difference to rotate by
        :return: Nonea
        """

        verify(angle_diff, (float, int))
        self.rotation(self._angle + angle_diff)

    def lookat(self, obj):
        if isinstance(obj, Object):
            obj = obj.location()
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError(
                f'Text#lookat(): expected a Renderable or Location; received {type(obj)} ({obj!r}).'
            )

        location = Location(obj[0], obj[1])

        theta = math.atan2(location.y() - self.center().y(), location.x() - self.center().x()) - math.radians(self.rotation())
        theta = math.degrees(theta) + 90

        self.rotate(theta)

    @_overload
    def center(self, x: float, y: float, *, centroid: bool = ...) -> Location: ...

    @_overload
    def center(self, location: Location, *, centroid: bool = ...) -> Location: ...

    @_overload
    def center(self, *, move_to: Location = ..., x: float = ..., y: float = ..., centroid: bool = ...) -> Location: ...

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center

        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Renderable
        """

        verify_keywords(kwargs, ('move_to', 'x', 'y'), 'Text#center()')

        if len(args) == 0 and len(kwargs) == 0:
            return self._center()

        location = Location(self._center())
        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0])
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError('Text#center(): expected both x and y.')
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )

                location.moveto(args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Text#center(): expected a tuple/Location or two numbers (x, y).'
                )

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to'])
                else:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x'])
                else:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y'])
                else:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )

        return self._center(location)

    def _center(self, move_to: Location = None):
        if move_to is not None:
            verify(move_to, Location)
            self.moveto(move_to.x() - self.width() / 2, move_to.y() - self.height() / 2)

        return Location(self.x() + self.width() / 2, self.y() + self.height() / 2)

    def vertices(self) -> list:
        """
        Get the vertices of a Rectangle superposed in the same transform of the Text

        :return: a list of Locations
        """

        vertices = [Location(self.x(), self.y()), Location(self.x() + self.width(), self.y()),
                    Location(self.x() + self.width(), self.y() + self.height()),
                    Location(self.x(), self.y() + self.height())]
        if self._angle != 0:
            # First get some values that we're going to use later
            theta = math.radians(self._angle)
            cosine = math.cos(theta)
            sine = math.sin(theta)

            centroid_x = self.center().x()
            centroid_y = self.center().y()

            new_vertices = []
            for vertex in vertices:
                # We have to create these separately because they're ironically used in each other's calculations xD
                old_x = vertex.x() - centroid_x
                old_y = vertex.y() - centroid_y

                new_x = (old_x * cosine - old_y * sine) + centroid_x
                new_y = (old_x * sine + old_y * cosine) + centroid_y
                new_vertices.append(Location(new_x, new_y))
            vertices = new_vertices

        return vertices

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the text

        :param visible: the visibility to set to, if any
        :return: the visibility of the text
        """

        if visible is not None:
            verify(visible, bool)
            self._visible = visible
            self._invalidate_render()

        return self._visible

    def transform(self, transform: tuple = None) -> tuple:
        """
        Retrieve the transform of the text

        :param transform: Unsupported.
        :return: a tuple with representing: (width, height, angle)
        """

        if transform is not None:
            raise UnsupportedError('Text#transform(): setting transforms is unsupported.')

        return self.width(), self.height(), self.rotation()

    def clone(self):
        """
        Clone this text!

        :return: A cloned text object!
        """

        return Text(self._screen, self._text, self.x(), self.y(), color=self._color, font=self._font, size=self._size,
                    align=self._align, bold=self._bold, italic=self._italic,
                    underline=self._underline, strikethrough=self._strikethrough,
                    rotation=self._angle, visible=self._visible)

    def _update_font(self):
        self._update_coords()

    def _update_coords(self):
        # For Text this just refreshes width/height (position is handled elsewhere).
        self._check()

        true_width, true_height = self._calculate_transform()
        self._width = true_width
        self._height = true_height * (self._text.count('\n') + 1)
        self._invalidate_render()

    # noinspection PyProtectedMember
    def update(self) -> None:
        self._check()
        self._update_coords()

    def _calculate_transform(self):
        return self._screen._backend.measure_text(
            self._text,
            self._font,
            self._size,
            self._bold,
            self._italic,
        )

# == NON RENDERABLES == #


class Line(Object):
    _PEN_SUPPORTED = False

    def __init__(self, screen: Screen, *args, color: Color = Color('black'), thickness: int = 1, dashes=None,
                 visible: bool = True):
        super().__init__(screen)
        self._screen = screen

        if len(args) >= 4 and all(type(arg) is float or type(arg) is int for arg in args[0:4]):
            self._pos1 = Location(args[0], args[1])
            self._pos2 = Location(args[2], args[3])
            excess = args[4:]
        elif len(args) >= 2 and all(type(arg) is tuple or type(arg) is Location for arg in args[0:2]):
            self._pos1 = Location(args[0][0], args[0][1])
            self._pos2 = Location(args[1][0], args[1][1])
            excess = args[2:]
        else:
            raise InvalidArgumentError(
                'Line(): expected two tuples/Locations or four numbers (x1, y1, x2, y2).'
            )

        if len(excess) > 0:  # noqa
            count = 0
            for arg in excess:
                if count == 0:
                    verify(arg, Color)
                    color = arg
                elif count == 1:
                    verify(arg, int)
                    thickness = arg
                elif count == 2:
                    verify(arg, (int, tuple))
                    dashes = arg
                elif count == 3:
                    verify(arg, bool)
                    visible = arg
                count += 1

        self._color = color
        self._thickness = thickness
        self._dashes = dashes
        self._visible = visible

        verify(color, Color, thickness, int, dashes, (int, tuple), visible, bool)

        if dashes is not None and type(dashes) is not tuple:
            self._dashes = (dashes, dashes)

        self._update_angle()
        self._render_id = self._screen._register_render_source(self._render_node)
        self._ref = self._render_id

    def _render_node(self):
        dash = self._dashes
        if dash is not None and type(dash) is not tuple:
            dash = (dash, dash)
        return PolylineNode(
            self._render_id,
            (
                (self._pos1.x(), self._pos1.y()),
                (self._pos2.x(), self._pos2.y()),
            ),
            self._color.rgb(),
            self._thickness,
            dash,
            self._visible,
            'butt',
            False,
        )

    def _invalidate_render(self):
        self._screen._invalidate_render(self._render_id)

    def _restore_render(self):
        self._screen._register_render_source(self._render_node, self._render_id)

    @_overload
    def pos1(self) -> Location: ...

    @_overload
    def pos1(self, __location: Union[Location, Tuple[float, float]]) -> Location: ...

    @_overload
    def pos1(self, __x: float, __y: float) -> Location: ...

    def pos1(self, *args) -> Location:
        """
        Get or set the position of the first endpoint.

        :param args: Either a location or two numbers (x, y) may be passed here.
        :return: the position of the first endpoint.
        """

        if len(args) != 0:
            if len(args) == 1 and (type(args[0]) is Location or type(args[0]) is tuple):
                self._pos1 = Location(args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                self._pos1 = Location(args[0], args[1])
            else:
                raise TypeError('Incorrect Argumentation: Requires either a location, tuple, or two numbers.')

            self._update_angle()
            self._invalidate_render()
        return self._pos1

    @_overload
    def pos2(self) -> Location: ...

    @_overload
    def pos2(self, __location: Union[Location, Tuple[float, float]]) -> Location: ...

    @_overload
    def pos2(self, __x: float, __y: float) -> Location: ...

    def pos2(self, *args) -> Location:
        """
        Get or set the position of the second endpoint.

        :param args: Either a location or two numbers (x, y) may be passed here.
        :return: the position of the second endpoint.
        """

        if len(args) != 0:
            if len(args) == 1 and (type(args[0]) is Location or type(args[0]) is tuple):
                self._pos2 = Location(args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                self._pos2 = Location(args[0], args[1])
            else:
                raise TypeError('Incorrect Argumentation: Requires either a location, tuple, or two numbers.')

            self._update_angle()
            self._invalidate_render()
        return self._pos2

    @_overload
    def move(self, dx: float, dy: float) -> None: ...

    @_overload
    def move(self, location: Location) -> None: ...

    @_overload
    def move(self, dxy: Tuple[float, float]) -> None: ...

    @_overload
    def move(self, *, dx: float = ..., dy: float = ...) -> None: ...

    def move(self, *args, **kwargs) -> None:
        """
        Move both endpoints by the same dx and dy

        Can take either a tuple, Location, or two numbers (dx, dy)

        :param dx: the distance x to move
        :param dy: the distance y to move
        :param point: affect only one of the endpoints options: (1, 2), default=0 (Must be 1 or 2)
        :return: None
        """

        diff = (0, 0)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                diff = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                diff = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Line#move(): expected a tuple/Location or two numbers (dx, dy).'
                )

        verify_keywords(kwargs, ('dx', 'dy', 'point'), 'Line#move()', case_sensitive=False)
        point = 0
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Line#move(): expected a tuple/Location or two numbers (dx, dy).'
                )

            name = name.lower()
            if name == 'dx':
                diff = (value, diff[1])
            elif name == 'dy':
                diff = (diff[0], value)
            elif name == 'point':
                point = value

        verify(point, int)
        if point == 1:
            self._pos1.move(diff[0], diff[1])
        elif point == 2:
            self._pos2.move(diff[0], diff[1])
        elif point == 0:
            self._pos1.move(diff[0], diff[1])
            self._pos2.move(diff[0], diff[1])
        else:
            raise InvalidArgumentError('Line#move(): point must be 0, 1, or 2.')

        if point != 0:
            self._update_angle()

        self._invalidate_render()

    @_overload
    def moveto(self, x: float, y: float) -> None: ...

    @_overload
    def moveto(self, location: Location) -> None: ...

    @_overload
    def moveto(self, xy: Tuple[float, float]) -> None: ...

    @_overload
    def moveto(self, *, x: float = ..., y: float = ...) -> None: ...

    def moveto(self, *args, **kwargs) -> None:
        """
        Move both of the endpoints to new locations.

        :param args: Either two locations, tuples, or four numbers (x1, y1, x2, y2).
        :return: None
        """

        verify_keywords(
            kwargs,
            ('pos1', 'pos2', 'x1', 'y1', 'x2', 'y2'),
            'Line#moveto()',
            case_sensitive=False
        )
        if len(args) == 2 and all(type(arg) is tuple or type(arg) is Location for arg in args):
            self._pos1.moveto(args[0][0], args[0][1])
            self._pos2.moveto(args[1][0], args[1][1])
        elif len(args) == 4 and all(type(arg) is int or type(arg) is float for arg in args):
            self._pos1.moveto(args[0], args[1])
            self._pos2.moveto(args[2], args[3])
        elif len(kwargs) == 0:
            raise TypeError('Incorrect Argumentation: Requires either two locations, tuples, or four numbers (x1, y1, '
                            'x2, y2)')

        if len(kwargs.keys()) > 0:
            for key, value in kwargs.items():
                key = key.lower()
                if key == 'pos1':
                    if type(value) is not tuple and type(value) is not Location:
                        raise InvalidArgumentError(
                            'Line#moveto(): pos1 must be a tuple or Location.'
                        )
                    pos1 = value
                    verify(pos1[0], (float, int), pos1[1], (float, int))
                    self._pos1 = Location(pos1[0], pos1[1])
                elif key == 'pos2':
                    if type(value) is not tuple and type(value) is not Location:
                        raise InvalidArgumentError(
                            'Line#moveto(): pos2 must be a tuple or Location.'
                        )
                    pos2 = value
                    verify(pos2[0], (float, int), pos2[1], (float, int))
                    self._pos2 = Location(pos2[0], pos2[1])
                elif type(value) is not float and type(value) is not int:
                    raise InvalidArgumentError(
                        f'Line#moveto(): {key} must be a number.'
                    )
                elif key == 'x1':
                    self._pos1.x(value)
                elif key == 'y1':
                    self._pos1.y(value)
                elif key == 'x2':
                    self._pos2.x(value)
                elif key == 'y2':
                    self._pos2.y(value)
        elif len(args) == 0:
            raise TypeError('Incorrect Argumentation: Requires either two locations, tuples, or four numbers (x1, y1, '
                            'x2, y2)')

        self._update_angle()
        self._invalidate_render()

    # noinspection PyUnusedLocal
    # TODO: Allow for point specification (center)
    @_overload
    def lookat(self, location: Union[Location, Tuple[float, float]], point: int = ...) -> None: ...

    @_overload
    def lookat(self, x: float, y: float, point: int = ...) -> None: ...

    def lookat(self, *args, **kwargs) -> None:
        """
        Make the line look at the given point by moving the second point.

        :return: None
        """

        verify_keywords(kwargs, ('point',), 'Line#lookat()', case_sensitive=False)
        point = 2

        if len(args) >= 1 and (type(args[0]) is tuple or type(args[0]) is Location):
            location = Location(args[0][0], args[0][1])

            if len(args) > 1 and type(args[1]) is int:
                point = args[1]
        elif len(args) >= 2 and all(type(arg) is float or type(arg) is int for arg in args[:2]):
            location = Location(args[0], args[1])

            if len(args) > 2 and type(args[2]) is int:
                point = args[2]
        else:
            raise InvalidArgumentError(
                'Line#lookat(): expected a tuple/Location or two numbers (x, y).'
            )

        for name, value in kwargs.items():
            if type(value) is not int:
                raise InvalidArgumentError('Line#lookat(): point must be an int.')

            if name.lower() == 'point':
                point = value

        # so now we have a location, but we need to shorten it to be the same length of our line right now.
        # slope = (self.pos2().y() - self.pos1().y()) / (self.pos2.x() - self.pos1.x())
        length = self.length()

        if point == 2:
            ray_length = self._length(self.pos1().x(), location.x(), self.pos1().y(), location.y())

            # hypotenuse = (ray_length - length)  # extraneous length (we need to cut this)

            theta = math.atan2(self.pos1().y() - location.y(), self.pos1().x() - location.x()) \
                    - math.atan2(self.pos1().y() - self.pos2().y(), self.pos1().x() - self.pos2().x())
        elif point == 1:
            ray_length = self._length(self.pos2().x(), location.x(), self.pos2().y(), location.y())

            # hypotenuse = (ray_length - length)  # extraneous length (we need to cut this)

            theta = math.atan2(self.pos2().y() - location.y(), self.pos2().x() - location.x()) \
                    - math.atan2(self.pos2().y() - self.pos1().y(), self.pos2().x() - self.pos1().x())
        else:
            raise InvalidArgumentError('Line#lookat(): point must be 1 or 2.')

        self.rotate(math.degrees(theta))

    def rotation(self, angle: float = None):
        """
        Get or set the rotation of the line (works via pos2()).

        :param angle: the angle in degrees to rotate by, if any
        :return: the angle of the line
        """

        if angle is not None:
            self.rotate(angle - self._angle)

        return self._angle

    def rotate(self, angle_diff: float, point: int = 1) -> float:
        """
        Rotate the line around one of its vertices (1 by default)

        :param angle_diff: the angle to rotate by
        :param point: the point to serve as the origin.
        :return: the new angle
        """

        if point not in (1, 2):
            raise InvalidArgumentError('Line#rotate(): point must be 1 or 2.')

        origin = self._pos1 if point == 1 else self._pos2
        point = self._pos2 if point == 1 else self._pos1

        theta = math.radians(angle_diff)

        cosine = math.cos(theta)
        sine = math.sin(theta)

        old_x = point.x() - origin.x()
        old_y = point.y() - origin.y()

        new_x = (old_x * cosine - old_y * sine) + origin.x()
        new_y = (old_x * sine + old_y * cosine) + origin.y()

        point.moveto(new_x, new_y)
        self._invalidate_render()

        self._angle += angle_diff
        return self._angle

    def _update_angle(self) -> float:
        """Recalculate the angle from the current endpoint locations."""

        theta = math.atan2(
            self._pos1.y() - self._pos2.y(),
            self._pos1.x() - self._pos2.x(),
        )
        self._angle = math.degrees(theta)
        return self._angle

    def location(self) -> tuple:
        """
        Returns the locations of both the endpoints

        :return: the locations of both the endpoints
        """

        return self._pos1, self._pos2

    def length(self) -> float:
        """
        Get the length of the line

        :return: the length of the line
        """

        return self._length(self.pos1().x(), self.pos2().x(), self.pos1().y(), self.pos2().y())

    @staticmethod
    def _length(x1: float, x2: float, y1: float, y2: float) -> float:
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the line

        :param color: the color to set to, if any
        :return: the color of the line
        """

        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            self._invalidate_render()

        return self._color

    def thickness(self, thickness: int = None) -> int:
        """
        Get or set the thickness of the line

        :param thickness: the thickness to set to, if any
        :return: the thickness of the line
        """

        if thickness is not None:
            verify(thickness, int)
            self._thickness = thickness
            self._invalidate_render()

        return self._thickness

    def dashes(self, dashes: Union[int, tuple] = None) -> Union[int, tuple]:
        """
        Retrieve or enable/disable the dashes for the line

        On systems which support only a limited set of dash patterns, the dash pattern will be displayed as the closest
        dash pattern that is available. For example, on Windows only a few dash patterns are available, most of which
        do not allow for special dash-spacing (if passing in a tuple).

        :param dashes: the visibility to set to, if any
        :return: the toggle-state of dashes
        """

        if dashes is not None:
            verify(dashes, (int, tuple))

            if type(dashes) == tuple:
                for dash in dashes:
                    verify(dash, int)

            self._dashes = dashes
            self._invalidate_render()

        return self._dashes

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the line

        :param visible: the visibility to set to, if any
        :return: the visibility of the line
        """

        if visible is not None:
            verify(visible, bool)
            self._visible = visible
            self._invalidate_render()

        return self._visible

    def transform(self, transform: tuple = None):
        """
        Copy the line's length and angle!

        :param transform:
        :return:
        """

        if transform is not None:
            raise UnsupportedError('Line#transform(): setting transforms is unsupported.')

        return self.length(), self.rotation()

    def clone(self):
        """
        Clone a new line!

        :return: A clone of this line
        """

        return Line(self._screen, self._pos1, self._pos2, color=self._color, thickness=self._thickness,
                    dashes=self._dashes, visible=self._visible)

    def intersects(self, obj) -> bool:
        """
        Check if a line intersects with another line or Renderable

        :param obj: Line, Renderable, or List/Tuple
        :return: Whether the line intersects with the object
        """

        shape1 = (self.pos1(), self.pos2())

        if type(obj) == Line:
            shape2 = (obj.pos1(), obj.pos2())
        elif isinstance(obj, Renderable):
            shape2 = obj.vertices()
        elif type(obj) == list or type(obj) == tuple:
            shape2 = obj
        else:
            raise InvalidArgumentError(
                f'Line#intersects(): expected a Line, Renderable, list, or tuple; '
                f'received {type(obj)} ({obj!r}).'
            )

        if len(shape2) < 2:
            raise InvalidArgumentError(
                'Line#intersects(): expected at least two vertices.'
            )

        # Orientation method that will determine if it is a triangle (and in what direction [cc or ccw]) or a line.
        def orientation(point1: Location, point2: Location, point3: Location) -> str:
            """
            Internal method that will determine the orientation of three points. They can be a clockwise triangle,
            counterclockwise triangle, or a co-linear line segment.

            :param point1: the first point of the main line segment
            :param point2: the second point of the main line segment
            :param point3: the third point to check from another line segment
            :return: the orientation of the passed points
            """
            result = (float(point2.y() - point1.y()) * (point3.x() - point2.x())) - \
                     (float(point2.x() - point1.x()) * (point3.y() - point2.y()))

            if result > 0:
                return 'clockwise'
            elif result < 0:
                return 'counter-clockwise'
            else:
                return 'co-linear'

        def point_on_segment(point1: Location, point2: Location, point3: Location) -> bool:
            """
            Returns if point3 lies on the segment formed by point1 and point2.
            """

            return max(point1.x(), point3.x()) >= point2.x() >= min(point1.x(), point3.x()) \
                   and max(point1.y(), point3.y()) >= point2.y() >= min(point1.y(), point3.y())

        # Okay to begin actually detecting orientations, we want to loop through some edges. But only ones that are
        # relevant. In order to do this we will first have to turn the list of vertices into a list of edges.
        # Then we will look through the lists of edges and find the ones closest to each other.

        shape1_edges = []
        shape2_edges = []

        shape1 = tuple(shape1[:]) + (shape1[0],)
        shape2 = tuple(shape2[:]) + (shape2[0],)

        shape1_point1 = shape1[0]
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)]  # 1, 2, 3, 3 % 5
            shape1_edges.append((shape1_point1, shape1_point2))
            shape1_point1 = shape1_point2

        shape2_point1 = shape2[0]
        for i in range(1, len(shape2)):
            shape2_point2 = shape2[i % len(shape2)]
            shape2_edges.append((shape2_point1, shape2_point2))
            shape2_point1 = shape2_point2

        # Now we are going to test the four orientations that the segments form
        for edge1 in shape1_edges:
            for edge2 in shape2_edges:
                orientation1 = orientation(edge1[0], edge1[1], edge2[0])
                orientation2 = orientation(edge1[0], edge1[1], edge2[1])
                orientation3 = orientation(edge2[0], edge2[1], edge1[0])
                orientation4 = orientation(edge2[0], edge2[1], edge1[1])

                # If orientations 1 and 2 are strictly opposite (both non-co-linear) as well as 3 and 4,
                # then the segments cross. A plain != would treat a co-linear result as a crossing and
                # mis-fire on floating-point-collinear edges that don't actually touch.
                if orientation1 != orientation2 and orientation1 != 'co-linear' and orientation2 != 'co-linear' \
                        and orientation3 != orientation4 and orientation3 != 'co-linear' and orientation4 != 'co-linear':
                    return True

                # There's some special cases we should check where a point from one segment is on the other segment
                if orientation1 == 'co-linear' and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True

                if orientation2 == 'co-linear' and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True

                if orientation3 == 'co-linear' and point_on_segment(edge2[0], edge1[0], edge2[1]):
                    return True

                if orientation4 == 'co-linear' and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False

    # noinspection PyProtectedMember
    def update(self):
        self._check()
        self._invalidate_render()
