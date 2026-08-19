from typing import Union, Tuple, overload as _overload

from pydraw import Object, Renderable, verify
from pydraw import Location, Color
from pydraw.errors import *

import math


class CompoundObject(Object):
    """
    A compound group of objects that can be moved or modified together.
    """

    _PEN_SUPPORTED = False

    def __init__(self, *args: Object, **kwargs: Object):
        """
        Pass in the shapes/objects to be used to create the CompoundObject

        :param args: the shapes/objects to use
        :param kwargs: shapes/objects to use that along with identifiers
        """
        self._objects = {}

        for arg in args:
            if not isinstance(arg, Object):
                raise InvalidArgumentError(
                    f'CompoundObject(): expected Object values; received {type(arg)} ({arg!r}).'
                )

            self._objects[str(arg)] = arg

        for (name, arg) in kwargs.items():
            if not isinstance(arg, Object):
                raise InvalidArgumentError(
                    f'CompoundObject(): expected Object values; received {type(arg)} ({arg!r}).'
                )

            self._objects[name] = arg

        if len(self._objects) == 0:
            raise InvalidArgumentError('CompoundObject(): expected at least one Object.')

        self._location, self._end = self._calculate_bounds()

        self._angle = 0

    def x(self, x: float = None) -> float:
        """
        Get the x coordinate of the compound system.

        :param x: a new x, if provided
        :return: a float
        """

        if x is not None:
            dx = x - self._location.x()
            self.move(dx=dx)

        return self._location.x()

    def y(self, y: float = None) -> float:
        """
        Get the y coordinate of the compound system.

        :param y: a new y, if provided
        :return: a float
        """

        if y is not None:
            dy = y - self._location.y()
            self.move(dy=dy)

        return self._location.y()

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
        Move the compound shape by a certain distance (dx, dy)

        :return: None
        """

        for obj in self._objects.values():
            obj.move(*args, **kwargs)

        # Shift the tracked bounds once (not once per child, which would
        # multiply the delta by the number of objects).
        self._location.move(*args, **kwargs)
        self._end.move(*args, **kwargs)

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
        Move the compound shape to a new location (x, y)

        :return: None
        """

        current_x = self._location._x
        current_y = self._location._y

        if not kwargs and len(args) == 2 \
                and all(type(value) is int or type(value) is float for value in args):
            target_x, target_y = args
        else:
            target = Location._raw(current_x, current_y)
            target.moveto(*args, **kwargs)
            target_x, target_y = target._x, target._y

        dx = target_x - current_x
        dy = target_y - current_y
        if dx == 0 and dy == 0:
            return
        self.move(dx, dy)

    def width(self, width: float = None) -> float:
        """
        Return the compound object's bounding width.

        This is a getter only; setting the width is unsupported.

        :param width: unsupported legacy argument; omit it when reading width
        :return: a float
        """

        if width is not None:
            raise UnsupportedError('CompoundObject#width(): setting width is unsupported.')

        return self._end.x() - self._location.x()

    def height(self, height: float = None) -> float:
        """
        Return the compound object's bounding height.

        This is a getter only; setting the height is unsupported.

        :param height: unsupported legacy argument; omit it when reading height
        :return: a float
        """

        if height is not None:
            raise UnsupportedError('CompoundObject#height(): setting height is unsupported.')

        return self._end.y() - self._location.y()

    def rotate(self, angle_diff: float, pivot: Location = None) -> None:
        """
        Rotate the angle of the compound object by a difference, around a pivot point, in degrees

        :param angle_diff: the angle difference to rotate by
        :param pivot: the pivot point to rotate around
        :return: None
        """

        verify(angle_diff, (float, int), pivot, Location)

        pivot = self.center(centroid=True) if pivot is None else pivot

        # Convert the angle_diff to radians
        angle_diff_rad = math.radians(angle_diff)
        cosine = math.cos(angle_diff_rad)
        sine = math.sin(angle_diff_rad)

        for obj in self._objects.values():
            # An object's location is its unrotated top-left anchor, but
            # Object#rotate() spins it around its center.  Revolving that anchor
            # and then spinning around the center applies two incompatible
            # transforms: differently sized children drift apart and the
            # compound no longer behaves as a rigid body.
            #
            # Revolve the same point that the child uses for its own rotation,
            # then translate the rotated child until that point reaches its
            # destination.  Calculating the translation after obj.rotate()
            # also accommodates child implementations whose reported center
            # changes slightly while rebuilding their rotated geometry.
            center = obj.center()
            dx = center.x() - pivot.x()
            dy = center.y() - pivot.y()

            new_center_x = (dx * cosine) - (dy * sine) + pivot.x()
            new_center_y = (dx * sine) + (dy * cosine) + pivot.y()

            obj.rotate(angle_diff)
            rotated_center = obj.center()
            obj.move(new_center_x - rotated_center.x(), new_center_y - rotated_center.y())

        # Update the angle
        self._angle += angle_diff

        # Update the values
        self.update()

    def rotation(self, angle: float = None) -> float:
        """
        Get the rotation of the compound object

        :param angle: a new rotation, if provided
        :return: a float
        """

        if angle is not None:
            self.rotate(angle - self._angle)

        return self._angle

    def center(self, centroid: bool = True) -> Location:
        """
        Calculate the center point of the CompoundObject.

        With the default ``centroid=True``, this is the arithmetic mean of the
        child centers. With ``centroid=False``, it is the midpoint of the
        compound's axis-aligned bounding box.
        :param centroid: whether to average child centers instead of using the
            bounding-box midpoint
        :return: Location of the center
        """

        if not centroid:
            return Location((self._location.x() + self._end.x()) / 2, (self._location.y() + self._end.y()) / 2)

        centers = [obj.center() for obj in self._objects.values()]
        center_x = sum(center.x() for center in centers) / len(centers)
        center_y = sum(center.y() for center in centers) / len(centers)

        return Location(center_x, center_y)

    @_overload
    def contains(self, __x: float, __y: float) -> bool: ...

    @_overload
    def contains(self, __location: Location) -> bool: ...

    @_overload
    def contains(self, __xy: Tuple[float, float]) -> bool: ...

    def contains(self, *args) -> bool:
        """
        Check if the CompoundObject contains a certain Location

        :param args: the Location to check
        :return: True if the CompoundObject contains the Location, False otherwise
        """

        x, y = 0, 0

        if len(args) == 1:
            verify(args, (tuple, Location))
            if type(args[0]) is Location:
                x = args[0].x()
                y = args[0].y()
            elif type(args[0]) is tuple and len(args[0]) == 2:
                x = args[0][0]
                y = args[0][1]
        elif len(args) == 2:
            verify(args[0], (float, int), args[1], (float, int))
            if type(args[0]) is not float and type(args[0]) is not int \
                    and type(args[1]) is not float and type(args[1]) is not int:
                raise InvalidArgumentError(
                    'CompoundObject#contains(): expected a tuple/Location or two numbers (x, y).'
                )
            x = args[0]
            y = args[1]
        else:
            raise InvalidArgumentError(
                'CompoundObject#contains(): expected a tuple/Location or two numbers (x, y).'
            )

        for obj in self._objects.values():
            if not isinstance(obj, Renderable):
                continue

            if obj.contains(x, y):
                return True

        return False

    def overlaps(self, other: 'Renderable') -> bool:
        """
        Returns if this compound object is overlapping with the passed object.

        :param other: another Renderable instance.
        :return: true if they are overlapping, false if not.
        """

        if not isinstance(other, Renderable):
            raise TypeError('Passed non-renderable into Renderable#overlaps(), which takes only Renderables!')

        for obj in self._objects.values():
            if not isinstance(obj, Renderable):
                continue

            if obj.overlaps(other):
                return True

        return False

    def front(self) -> None:
        """
        Brings the compound object to the front of the Screen
        (Imagine moving forward on the Z axis)

        :return: None
        """

        for obj in self._objects.values():
            obj.front()

    def back(self) -> None:
        """
        Brings the compound object to the back of the Screen
        (Imagine moving backward on the Z axis)

        :return: None
        """

        for obj in self._objects.values():
            obj.back()

    def add(self, obj: Object, name=None) -> None:
        """
        Add another Object to the CompoundObject

        :param obj: the Object to add
        :param name: optional registry key; when omitted, ``str(obj)`` is used
        :return: None
        """

        if not isinstance(obj, Object):
            raise InvalidArgumentError(
                f'CompoundObject#add(): expected an Object; received {type(obj)} ({obj!r}).'
            )

        if name is None:
            name = str(obj)

        self._objects[name] = obj

        # Now we must check if x and y need to change
        if obj.x() < self._location.x():
            self._location.x(obj.x())

        if obj.y() < self._location.y():
            self._location.y(obj.y())

        if obj.x() + obj.width() > self._end.x():
            self._end.x(obj.x() + obj.width())

        if obj.y() + obj.height() > self._end.y():
            self._end.y(obj.y() + obj.height())

    def remove(self, obj: Object = None, name=None) -> Object:
        """
        Remove an object from the Compound Object

        :param obj: the object to remove
        :param name: the name the object is registered under
        :return: the Object that got removed (or None)
        """

        removed_obj = None

        if obj is not None and name is None:
            removed_obj = self._objects.pop(str(obj))
        elif name is not None:
            removed_obj = self._objects.pop(name)

        return removed_obj

    def object(self, name) -> Object:
        """
        Retrieve a specific object

        :param name: the registry key. Positional constructor objects and
            unnamed additions are keyed by ``str(obj)``; keyword constructor
            arguments and named additions use the supplied name.
        :return: the registered Object, or ``None`` when the key is absent
        """

        return self._objects.get(name)

    def objects(self) -> tuple:
        """
        Retrieve a tuple of all objects in the compound shape.

        :return: a tuple
        """

        return tuple(self._objects.values())

    def color(self, color: Color):
        """Change the color of all the objects in the compound object."""

        for obj in self._objects.values():
            if not hasattr(obj, 'color'):
                continue

            obj.color(color)

    def update(self):
        """Updates values of the compound object."""

        self._location, self._end = self._calculate_bounds()

    def _calculate_bounds(self) -> Tuple[Location, Location]:
        """Return the axis-aligned bounds of the children's live geometry."""

        bounds = []
        for obj in self._objects.values():
            if isinstance(obj, Renderable):
                vertices = obj.vertices()
                if vertices:
                    xs = [vertex.x() for vertex in vertices]
                    ys = [vertex.y() for vertex in vertices]
                    bounds.append((min(xs), min(ys), max(xs), max(ys)))
                    continue

            # CompoundObject and other dimensioned Object implementations do
            # not necessarily expose vertices. Their own location/dimensions
            # are the best available bounds.
            x = obj.x()
            y = obj.y()
            bounds.append((x, y, x + obj.width(), y + obj.height()))

        return (
            Location(min(bound[0] for bound in bounds), min(bound[1] for bound in bounds)),
            Location(max(bound[2] for bound in bounds), max(bound[3] for bound in bounds)),
        )
