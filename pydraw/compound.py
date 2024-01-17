from typing import Union, Tuple

from pydraw import Object, Renderable, verify
from pydraw import Location, Color
from pydraw.errors import *

import math


class CompoundObject(Object):
    """
    A compound group of objects that can be moved or modified together.
    """

    def __init__(self, *args, **kwargs):
        """
        Pass in the shapes/objects to be used to create the CompoundObject
        :param args: the shapes/objects to use
        :param kwargs: shapes/objects to use that along with identifiers
        """
        self._objects = {}

        for arg in args:
            if not isinstance(arg, Object):
                raise InvalidArgumentError('Argument passed to CompoundObject was not an Object:', arg)

            self._objects[str(arg)] = arg

        for (name, arg) in kwargs:
            if not isinstance(arg, Object):
                raise InvalidArgumentError('Argument passed to CompoundObject was not an Object:', arg)

            self._objects[name] = arg

        if len(self._objects) == 0:
            raise InvalidArgumentError('You must pass at least one object to create a CompoundObject!')

        values = list(self._objects.values())

        x = values[0].x()
        y = values[0].y()
        endx = values[len(self._objects) - 1].x()
        endy = values[len(self._objects) - 1].y()

        self._location = Location(x, y)
        self._end = Location(endx, endy)

        self._angle = 0

        for obj in self._objects.values():
            if obj.x() < self._location.x():
                self._location.x(obj.x())
            elif obj.x() > self._location.x():
                self._end.x(obj.x())

            if obj.y() < self._location.y():
                self._location.y(obj.y())
            elif obj.y() > self._location.y():
                self._end.y(obj.y())

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

    def move(self, *args, **kwargs) -> None:
        """
        Move the compound shape by a certain distance (dx, dy)
        :return: None
        """

        for obj in self._objects.values():
            obj.move(*args, **kwargs)
            self._location.move(*args, **kwargs)
            self._end.move(*args, **kwargs)

    def moveto(self, *args, **kwargs) -> None:
        """
        Move the compound shape to a new location (x, y)
        :return: None
        """

        old = self._location.clone()
        self._location.moveto(*args, **kwargs)

        dx = self._location.x() - old.x()
        dy = self._location.y() - old.y()
        self.move(dx, dy)
        self.update()

    def width(self, width: float = None) -> float:
        """
        Get the width of the compound object
        :param width: a new width, if provided
        :return: a float
        """

        if width is not None:
            raise UnsupportedError('Cannot set width of a CompoundObject')

        return self._end.x() - self._location.x()

    def height(self, height: float = None) -> float:
        """
        Get the height of the compound object
        :param height: a new height, if provided
        :return: a float
        """

        if height is not None:
            raise UnsupportedError('Cannot set height of a CompoundObject')

        return self._end.y() - self._location.y()

    def rotate(self, angle_diff: float, pivot: Location = None) -> None:
        """
        Rotate the angle of the compound object by a difference, around a pivot point, in degrees
        :param angle_diff: the angle difference to rotate by
        :param pivot: the pivot point to rotate around
        :return: None
        """

        pivot = self.center(centroid=True) if pivot is None else pivot

        # Convert the angle_diff to radians
        angle_diff_rad = math.radians(angle_diff)

        for obj in self._objects.values():
            # Calculate new position
            dx = obj.x() - pivot.x()
            dy = obj.y() - pivot.y()

            new_x = (dx * math.cos(angle_diff_rad)) - (dy * math.sin(angle_diff_rad)) + pivot.x()
            new_y = (dx * math.sin(angle_diff_rad)) + (dy * math.cos(angle_diff_rad)) + pivot.y()

            # Move the object to the new position
            obj.moveto(new_x, new_y)

            # Rotate the object
            obj.rotate(angle_diff)

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
        Calculate the center point of the CompoundObject
        :centroid: whether to use the centroid or the center of the bounding box
        :return: Location of the center
        """

        if not centroid:
            return Location((self._location.x() + self._end.x()) / 2, (self._location.y() + self._end.y()) / 2)

        total_x = 0
        total_y = 0
        num_objects = len(self._objects)

        for obj in self._objects.values():
            total_x += obj.x()
            total_y += obj.y()

        center_x = total_x / num_objects
        center_y = total_y / num_objects

        return Location(center_x, center_y)

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
                raise InvalidArgumentError('Passed arguments must be numbers (x, y), '
                                           'or you may pass a location/tuple.')
            x = args[0]
            y = args[1]
        else:
            raise InvalidArgumentError('You must pass in a tuple, Location, or two numbers (x, y)!')

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

        for obj in self._objects:
            obj.front()

    def back(self) -> None:
        """
        Brings the compound object to the back of the Screen
        (Imagine moving backward on the Z axis)
        :return: None
        """

        for obj in self._objects:
            obj.back()

    def add(self, obj: Object, name=None) -> None:
        """
        Add another Object to the CompoundObject
        :param obj: the Object to add
        :return: None
        """

        if not isinstance(obj, Object):
            raise InvalidArgumentError('Argument passed to CompoundObject was not an Object.')

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
        :param name: the name of the object (can be a str, or another type of object)
        :return: Object
        """

        return self._objects.get(name)

    def objects(self) -> tuple:
        """
        Retrieve a tuple of all objects in the compound shape.
        :return: a tuple
        """

        return tuple(self._objects.values())

    def color(self, color: Color) -> Color:
        """Change the color of all the objects in the compound object."""

        for obj in self._objects.values():
            if not hasattr(obj, 'color'):
                continue

            obj.color(color)

    def update(self):
        """Updates values of the compound object."""

        values = list(self._objects.values())

        x = values[0].x()
        y = values[0].y()
        endx = values[len(self._objects) - 1].x()
        endy = values[len(self._objects) - 1].y()

        self._location = Location(x, y)
        self._end = Location(endx, endy)

        for obj in self._objects.values():
            if obj.x() < self._location.x():
                self._location.x(obj.x())
            elif obj.x() > self._location.x():
                self._end.x(obj.x())

            if obj.y() < self._location.y():
                self._location.y(obj.y())
            elif obj.y() > self._location.y():
                self._end.y(obj.y())
