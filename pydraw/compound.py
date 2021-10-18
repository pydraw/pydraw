from pydraw import Object;
from pydraw import Location;
from pydraw.errors import *;


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
        self._objects = {};

        for arg in args:
            if not isinstance(arg, Object):
                raise InvalidArgumentError('Argument passed to CompoundObject was not an Object:', arg);

            self._objects[str(arg)] = arg;

        for (name, arg) in kwargs:
            if not isinstance(arg, Object):
                raise InvalidArgumentError('Argument passed to CompoundObject was not an Object:', arg);

            self._objects[name] = arg;

        if len(self._objects) == 0:
            raise InvalidArgumentError('You must pass at least one object to create a CompoundObject!');

        values = list(self._objects.values());

        x = values[0].x();
        y = values[0].y();
        endx = values[len(self._objects) - 1].x();
        endy = values[len(self._objects) - 1].y();

        self._location = Location(x, y);
        self._end = Location(endx, endy);

        for obj in self._objects.values():
            if obj.x() < self._location.x():
                self._location.x(obj.x());
            elif obj.x() > self._location.x():
                self._end.x(obj.x());

            if obj.y() < self._location.y():
                self._location.y(obj.y());
            elif obj.y() > self._location.y():
                self._end.y(obj.y());

    def x(self, x: float = None) -> float:
        """
        Get the x coordinate of the compound system.
        :param x: a new x, if provided
        :return: a float
        """

        if x is not None:
            dx = x - self._location.x();
            self.move(dx=dx);

        return self._location.x();

    def y(self, y: float = None) -> float:
        """
        Get the y coordinate of the compound system.
        :param y: a new y, if provided
        :return: a float
        """

        if y is not None:
            dy = y - self._location.y();
            self.move(dy=dy);

        return self._location.y();

    def move(self, *args, **kwargs) -> None:
        """
        Move the compound shape by a certain distance (dx, dy)
        :return: None
        """

        for obj in self._objects.values():
            obj.move(*args, **kwargs);
            self._location.move(*args, **kwargs);
            self._end.move(*args, **kwargs);

    def moveto(self, *args, **kwargs) -> None:
        """
        Move the compound shape to a new location (x, y)
        :return: None
        """

        old = self._location.clone();
        self._location.moveto(*args, **kwargs);

        dx = self._location.x() - old.x();
        dy = self._location.y() - old.y();
        self.move(dx, dy);

    def front(self) -> None:
        """
        Brings the compound object to the front of the Screen
        (Imagine moving forward on the Z axis)
        :return: None
        """

        for obj in self._objects:
            obj.front();

    def back(self) -> None:
        """
        Brings the compound object to the back of the Screen
        (Imagine moving backward on the Z axis)
        :return: None
        """

        for obj in self._objects:
            obj.back();

    def add(self, obj: Object, name=None) -> None:
        """
        Add another Object to the CompoundObject
        :param obj: the Object to add
        :return: None
        """

        if not isinstance(obj, Object):
            raise InvalidArgumentError('Argument passed to CompoundObject was not an Object.');

        if name is None:
            name = str(obj);

        self._objects[name] = obj;

        # Now we must check if x and y need to change
        if obj.x() < self._location.x():
            self._location.x(obj.x());

        if obj.y() < self._location.y():
            self._location.y(obj.y());

    def remove(self, obj: Object = None, name=None) -> Object:
        """
        Remove an object from the Compound Object
        :param obj: the object to remove
        :param name: the name the object is registered under
        :return: the Object that got removed (or None)
        """

        removed_obj = None;

        if obj is not None and name is None:
            removed_obj = self._objects.pop(str(obj));
        elif name is not None:
            removed_obj = self._objects.pop(name);

        return removed_obj;

    def object(self, name) -> Object:
        """
        Retrieve a specific object
        :param name: the name of the object (can be a str, or another type of object)
        :return: Object
        """

        return self._objects.get(name);

    def objects(self) -> tuple:
        """
        Retrieve a tuple of all objects in the compound shape.
        :return: a tuple
        """

        return tuple(self._objects.values());
