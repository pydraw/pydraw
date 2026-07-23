from pydraw.errors import *
from pydraw.util import verify_keywords
import math


class Location:
    __slots__ = ('_x', '_y')

    @classmethod
    def _raw(cls, x, y):
        """
        Fast internal constructor: build a Location from two numbers without any
        argument parsing. For hot paths (e.g. per-vertex construction in
        Renderable._update_coords) where the inputs are already known to be
        numbers. Not part of the public API.
        """
        location = cls.__new__(cls)
        location._x = x
        location._y = y
        return location

    def __init__(self, *args, **kwargs):
        # Fast path: Location(x, y) with two numbers is by far the most common
        # (and hottest) construction, so handle it before the general parsing.
        if len(args) == 2 and not kwargs:
            x, y = args
            if (type(x) is float or type(x) is int) and \
                    (type(y) is float or type(y) is int):
                self._x = x
                self._y = y
                return

        location = (0, 0)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                location = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                location = (args[0], args[1])
            else:
                raise InvalidArgumentError('Location constructor takes a tuple/location '
                                           'or two numbers (x, y)!')
        elif len(kwargs) == 0:
            raise InvalidArgumentError('Location constructor takes a tuple/location '
                                       'or two numbers (x, y)!')

        verify_keywords(kwargs, ('x', 'y'), 'Location()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('Location constructor takes a tuple/location '
                                           'or two numbers (x, y)!')

            name = name.lower()
            if name == 'x':
                location = (value, location[1])
            elif name == 'y':
                location = (location[0], value)

        self._x = location[0]
        self._y = location[1]

    def move(self, *args, **kwargs):
        """
        Moves the location by a specified difference.

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
                raise InvalidArgumentError('move() takes a tuple/Location '
                                           'or two numbers (dx, dy)!')
        elif len(kwargs) == 0:
            raise InvalidArgumentError('move() takes a tuple/Location '
                                       'or two numbers (dx, dy)!')

        verify_keywords(kwargs, ('dx', 'dy'), 'Location#move()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('move() takes a tuple/Location '
                                           'or two numbers (dx, dy)!')

            name = name.lower()
            if name == 'dx':
                diff = (value, diff[1])
            elif name == 'dy':
                diff = (diff[0], value)

        self._x += diff[0]
        self._y += diff[1]

        return self

    def moveto(self, *args, **kwargs):
        """
        Moves the location to a new location!

        Can take two coordinates (x, y), a tuple, or a Location

        :param x: the x to move to
        :param y: the y to move to
        :return: the location (after change)
        """

        location = (self._x, self._y)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                location = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                location = (args[0], args[1])
            else:
                raise InvalidArgumentError('moveto() takes a tuple/Location '
                                           'or two numbers (x, y)!')
        elif len(kwargs) == 0:
            raise InvalidArgumentError('moveto() takes a tuple/location '
                                       'or two numbers (x, y)!')

        verify_keywords(kwargs, ('x', 'y'), 'Location#moveto()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('moveto() takes a tuple/location '
                                           'or two numbers (x, y)!')

            name = name.lower()
            if name == 'x':
                location = (value, location[1])
            elif name == 'y':
                location = (location[0], value)

        self._x = location[0]
        self._y = location[1]

        return self

    def x(self, new_x: float = None) -> float:
        if new_x is not None:
            self._x = new_x

        return self._x

    def y(self, new_y: float = None) -> float:
        if new_y is not None:
            self._y = new_y

        return self._y

    def distance(self, location) -> float:
        """
        Returns the distance between this location and another

        :param location: the Location to get the distance to
        :return: a float
        """

        return math.sqrt((location.x() - self.x()) ** 2 + (location.y() - self.y()) ** 2)

    def clone(self):
        """
        Clone the Location

        :return: a new Location with the same x and y as this one.
        """

        return Location._raw(self._x, self._y)

    def __str__(self):
        return f'(X: {self._x}, Y: {self._y})'

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        """
        Allows the location to be accessed as a tuple
        """
        yield self._x
        yield self._y

    def __getitem__(self, item):
        """
        Allows the location to be accessed as a tuple
        """

        if item == 0:
            return self._x
        elif item == 1:
            return self._y
        else:
            raise IndexError(f'Accessed index beyond x and y, index: {item}.')

    def __len__(self):
        return 2  # Always 2!

    def __eq__(self, other):
        if type(other) is not Location and type(other) is not tuple:
            return False

        if len(other) != 2:
            return False

        return self.x() == other[0] and self.y() == other[1]

    def __hash__(self):
        return hash((self._x, self._y))
