from pydraw.errors import *;
import math;


class Location:
    def __init__(self, *args, **kwargs):
        location = (0, 0);

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and type(args[0]) is tuple or type(args[0]) is Location:
                location = (args[0][0], args[0][1]);
            elif len(args) == 2 and [type(arg) is float or type(arg) is int for arg in args]:
                location = (args[0], args[1]);
            else:
                raise InvalidArgumentError('Location constructor takes a tuple/location '
                                           'or two numbers (x, y)!');
        elif len(kwargs) == 0:
            raise InvalidArgumentError('Location constructor takes a tuple/location '
                                       'or two numbers (x, y)!');

        for (name, value) in kwargs.items():
            if len(kwargs) == 0 or type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('Location constructor takes a tuple/location '
                                           'or two numbers (x, y)!');

            if name.lower() == 'x':
                location = (value, location[1]);
            if name.lower() == 'y':
                location = (location[0], value);

        self._x = location[0];
        self._y = location[1];

    def move(self, *args, **kwargs):
        """
        Moves the location by a specified difference.

        Can take two numbers (dx, dy), a tuple, or a Location
        :param dx: the dx to move by
        :param dy: the dy to move by
        :return: the location (after change)
        """

        diff = (0, 0);

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is diff or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and type(args[0]) is tuple or type(args[0]) is Location:
                diff = (args[0][0], args[0][1]);
            elif len(args) == 2 and [type(arg) is float or type(arg) is int for arg in args]:
                diff = (args[0], args[1]);
            else:
                raise InvalidArgumentError('move() takes a tuple/Location '
                                           'or two numbers (dx, dy)!');
        elif len(kwargs) == 0:
            raise InvalidArgumentError('move() takes a tuple/Location '
                                       'or two numbers (dx, dy)!');

        for (name, value) in kwargs.items():
            if len(kwargs) == 0 or type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('move() takes a tuple/Location '
                                           'or two numbers (dx, dy)!');

            if name.lower() == 'dx':
                diff = (value, diff[1]);
            if name.lower() == 'dy':
                diff = (diff[0], value);

        self._x += diff[0];
        self._y += diff[1];

        return self;

    def moveto(self, *args, **kwargs):
        """
        Moves the location to a new location!

        Can take two coordinates (x, y), a tuple, or a Location
        :param x: the x to move to
        :param y: the y to move to
        :return: the location (after change)
        """

        location = (self._x, self._y);

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and type(args[0]) is tuple or type(args[0]) is Location:
                location = (args[0][0], args[0][1]);
            elif len(args) == 2 and [type(arg) is float or type(arg) is int for arg in args]:
                location = (args[0], args[1]);
            else:
                raise InvalidArgumentError('moveto() takes a tuple/Location '
                                           'or two numbers (x, y)!');
        elif len(kwargs) == 0:
            raise InvalidArgumentError('moveto() takes a tuple/location '
                                       'or two numbers (x, y)!');

        for (name, value) in kwargs.items():
            if len(kwargs) == 0 or type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('moveto() takes a tuple/location '
                                           'or two numbers (x, y)!');

            if name.lower() == 'x':
                location = (value, location[1]);
            if name.lower() == 'y':
                location = (location[0], value);

        self._x = location[0];
        self._y = location[1];

        return self;

    def x(self, new_x: float = None) -> float:
        if new_x is not None:
            self._x = new_x;

        return self._x;

    def y(self, new_y: float = None) -> float:
        if new_y is not None:
            self._y = new_y;

        return self._y;

    def distance(self, location) -> float:
        """
        Returns the distance between this location and another
        :param location: the Location to get the distance to
        :return: a float
        """

        return math.sqrt((location.x() - self.x()) ** 2 + (location.y() - self.y()) ** 2);

    def clone(self):
        """
        Clone the Location
        :return: a new Location with the same x and y as this one.
        """

        return Location(self._x, self._y);

    def __str__(self):
        return f'(X: {self._x}, Y: {self._y})';

    def __repr__(self):
        return self.__str__();

    def __iter__(self):
        """
        Allows the location to be accessed as a tuple
        """
        yield self._x;
        yield self._y;

    def __getitem__(self, item):
        """
        Allows the location to be accessed as a tuple
        """

        if item == 0:
            return self._x;
        elif item == 1:
            return self._y;
        else:
            raise IndexError(f'Accessed index beyond x and y, index: {item}.');

    def __len__(self):
        return 2;  # Always 2!

    def __eq__(self, other):
        if type(other) is not Location and type(other) is not tuple:
            return False;

        if len(other) != 2:
            return False;

        return self.x() == other[0] and self.y() == other[1];

    def __hash__(self):
        return hash((self._x, self._y));
