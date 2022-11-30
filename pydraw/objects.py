"""
Objects in the PyDraw library

(Author: Noah Coetsee)
"""

# import turtle;
import tkinter as tk;
import math;
from typing import Union, List;
# import asyncio;

# from pydraw.errors import *;  # util gives us our errors for us :)
from pydraw.util import *;

from pydraw import Screen;
from pydraw import Location;
from pydraw import Color;

from pydraw.overload import overload;

PIXEL_RATIO = 20;
NoneType = type(None);


class Pen:
    # Pen for drawing a line as an object moves around on the screen
    def __init__(self, screen: Screen, x: float, y: float, color: Color = Color('black'), width: int = 2, top: bool = False):
        self._screen = screen;
        self._object = None;  # Set internally for Object's Pens.
        self._coordinates = [];  # contains all coordinates of the lines
        self._location = Location(x, y)  # used for when _drawing = False

        # self._coordinates.append(Location(x, y));

        self._color = color;
        self._width = width;
        self._top = top;

        self._drawing = False

        self._history = [];  # stores old line _refs for clearing
        self._ref = None;  # currentLine
        self._setup();

    def move(self, *args, **kwargs):
        """
        Adds a new coordinate to the pen line with a passed difference from the previous coordinate.
        Requires coordinates to be len > 0.

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

        if not len(self._coordinates) > 0:
            raise PydrawError('No starting coordinate to move Pen from.');

        if self._drawing:
            location = Location(self._coordinates[-1].x() + diff[0], self._coordinates[-1].y() + diff[1])
            self._coordinates.append(location)
        else:
            self._location = Location(self._coordinates[-1].x() + diff[0], self._coordinates[-1].y() + diff[1])

        self._update()

    def moveto(self, *args, **kwargs):
        """
        Adds a new coordinate to the pen line.

        Can take two coordinates (x, y), a tuple, or a Location
        :param x: the x to move to
        :param y: the y to move to
        :return: the location (after change)
        """

        location = None;

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and type(args[0]) is tuple or type(args[0]) is Location:
                location = (args[0][0], args[0][1]);
            elif len(args) == 2 and [type(arg) is float or type(arg) is int for arg in args]:
                location = (args[0], args[1]);
            else:
                raise InvalidArgumentError('move() takes a tuple/Location '
                                           'or two numbers (dx, dy)!');
        elif len(kwargs) == 0:
            raise InvalidArgumentError('moveto() takes a tuple/location '
                                       'or two numbers (dx, dy)!');

        for (name, value) in kwargs.items():
            if len(kwargs) == 0 or type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('moveto() takes a tuple/location '
                                           'or two numbers (dx, dy)!');

            if name.lower() == 'x':
                location = (value, location[1]);
            if name.lower() == 'y':
                location = (location[0], value);

        if not len(self._coordinates) > 0:
            raise PydrawError('No starting coordinate to move Pen from.');

        if self._drawing:
            location = Location(location[0], location[1])
            self._coordinates.append(location)
        else:
            self._location = Location(location[0], location[1])

        self._update()

    def coordinates(self, *coords) -> List[Location]:

        if len(coords) > 0:
            self._coordinates = [];

            for pos in coords:
                if type(pos) is tuple or type(pos) is Location:
                    self._coordinates.append(Location(pos[0], pos[1]));
                else:
                    raise InvalidArgumentError('coordinates() takes tuples/Locations only!');

            self._update();

        return self._coordinates;

    def start(self):
        self._drawing = True
        self._coordinates = [Location(self._location)]

        self._setup();

    def stop(self):
        if len(self._coordinates) > 0:
            self._location = self._coordinates[-1]
            # don't clear coordinates in case they get altered after we are done drawing

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
            self._location = self._coordinates[-1]
        self._coordinates = []

        # self._screen._canvas.itemconfigure(self._ref, style=tk.HIDDEN)
        if self._ref is not None: self._screen._canvas.coords(self._ref, 0, 0, 0, 0);
        for line in self._history:
            self._screen._canvas.coords(line, 0, 0, 0, 0);

        self._history.clear()

    def color(self, color: Color = None) -> Color:
        if color is not None:
            verify(color, Color);
            self._color = color;
            self._update();

        return self._color;

    def width(self, width: int = None) -> int:
        if width is not None:
            verify(width, int);
            self._width = width;
            self._update();

        return self._width;

    def top(self, top: bool = None) -> bool:
        if top is not None:
            verify(top, bool);
            self._top = top;
            self._update();

        return self._top();

    def _setup(self):
        # noinspection PyProtectedMember
        self._ref = self._screen._canvas.create_line(0, 0, 0, 0, fill="", width=2, capstyle=tk.ROUND)

    # noinspection PyProtectedMember
    def _update(self):
        if self._ref is None:
            raise PydrawError('Pen has not been started yet!');

        if self._coordinates is not None:
            cl = []
            for loc in self._coordinates:
                x = loc[0];
                y = loc[1];

                cl.append(x - (self._screen.width() / 2))
                cl.append(y - (self._screen.height() / 2))

            self._screen._canvas.coords(self._ref, *cl)

        if self._color is not None:
            self._screen._canvas.itemconfigure(self._ref,
                                               fill=self._screen._colorstr(self._color if self._color is not None else Color.NONE))
            if len(self._history) > 0:
                for line in self._history:
                    self._screen._canvas.itemconfigure(line,
                                                       fill=self._screen._colorstr(self._color if self._color is not None else Color.NONE))
        if self._width is not None:
            self._screen._canvas.itemconfigure(self._ref, width=self._width)

            if len(self._history) > 0:
                for line in self._history:
                    self._screen._canvas.itemconfigure(line, width=self._width)
        if self._top:
            self._screen._canvas.tag_raise(self._ref)

            if len(self._history) > 0:
                for line in self._history:
                    self._screen._canvas.tag_raise(line)


class Object:
    """
    A base object containing a location and screen. This ensures coordinates are
    done with the root at the top left corner, and not at the center.
    """

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, location: Location = None):
        verify(screen, Screen, x, (float, int), y, (float, int), location, Location);

        self._screen = screen;
        self._location = location if location is not None else Location(x, y);

        # noinspection PyProtectedMember
        self._screen._add(self);

        self._pen = Pen(screen, self._location.x(), self._location.y())
        self._pen._object = self;

    def x(self, x: float = None) -> float:
        if x is not None:
            verify(x, (float, int));
            self.moveto(x, self.y());

        return self._location.x();

    def y(self, y: float = None) -> float:
        if y is not None:
            verify(y, (float, int));
            self.moveto(self.x(), y);

        return self._location.y();

    def location(self) -> Location:
        return self._location;

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)
        :return: None
        """

        self._location.move(*args, **kwargs);
        self.update();

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location; takes a Location, tuple, or two numbers (x, y)
        :return: None
        """

        self._location.moveto(*args, **kwargs);
        self.update();

    def _get_real_location(self):
        real_x = self.x() + self.width() / 2 - (self._screen.width() / 2);
        real_y = -self.y() + self._screen.height() / 2 - self.height() / 2;

        return real_x, real_y;

    def front(self) -> None:
        """
        Brings the object to the front of the Screen
        (Imagine moving forward on the Z axis)
        :return: None
        """

        # noinspection PyProtectedMember
        self._screen._front(self);

    def back(self) -> None:
        """
        Brings the object to the back of the Screen
        (Imagine moving backward on the Z axis)
        :return: None
        """

        # noinspection PyProtectedMember
        self._screen._back(self);

    def remove(self) -> None:
        self._screen.remove(self);

    # Pen methods
    def pen(self, color: Color = Color('black'), width: int = 2, top: bool = False):
        pass

    def pen_clear(self):
        pass

    def pen_stop(self):
        pass

    def pen_width(self, width: int = None) -> int:
        pass

    def pen_top(self, top: bool = None) -> bool:
        pass

    # # noinspection PyProtectedMember
    # def add(self) -> None:
    #     """
    #     Should only be used to add an object that has been removed (via .remove() or Screen.clear()
    #     :return: None
    #     """
    #     if self in self._screen.objects():
    #         raise PydrawError('Error adding object: Object alraedy in Screen.objects()');
    #
    #     self._setup();
    #     self._screen._add(self);

    def _setup(self):
        """
        To be overriden.
        """
        pass;

    # noinspection PyProtectedMember
    def _check(self) -> None:
        if self._screen is None or Screen._TERMINATING:
            return;  # We don't wanna mess with how stupid tk and turtle are.

        if not self._screen.contains(self):
            if self in self._screen._gridlines or self in self._screen._helpers:
                return;

            raise PydrawError('Cannot update or draw object that is not on the Screen!');

    def update(self) -> None:
        """
        To be overriden.
        """
        pass;


class Renderable(Object):
    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = Color.NONE,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super().__init__(screen, x, y, location);
        self._width = width;
        self._height = height;
        self._color = color;
        self._border = border if border is not None else Color('');
        self._borderwidth = 1;
        self._fill = fill;
        self._angle = rotation;
        self._last_angle = rotation;
        self._visible = visible;

        self._setup();

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the object.
        :param width: the width to set to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int));
            self._width = width;
            self.update();

        return self._width;

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the object
        :param height: the height to set to in pixels, if any
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int));
            self._height = height;
            self.update();

        return self._height;

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center
        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Renderable
        """

        centroid = False
        if len(args) == 0:
            if len(kwargs) > 0:
                if 'centroid' in kwargs:
                    if type(kwargs['centroid']) is bool:
                        centroid = kwargs['centroid'];
                    else:
                        raise InvalidArgumentError(
                            ".center() requires a boolean for centroid (whether to return a bounds "
                            "center or a calculated centroid).");
            return self._center(centroid=centroid);

        location = Location(self._center())

        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0]);
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError(".center() requires both x and y passed unless using keywords.");
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

                location.moveto(args[0], args[1]);
            else:
                raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");
            if 'centroid' in kwargs:
                if type(kwargs['centroid']) is bool:
                    centroid = kwargs['centroid'];
                else:
                    raise InvalidArgumentError(".center() requires a boolean for centroid (whether to return a bounds "
                                               "center or a calculated centroid).");

        return self._center(location, centroid);

    def _center(self, move_to: Location = None, centroid: bool = False):
        if move_to is not None:
            verify(move_to, Location);
            self.moveto(move_to.x() - self.width() / 2, move_to.y() - self.height() / 2);

        if centroid:
            return Location(self.x() + self.width() / 2, self.y() + self.height() / 2);

        # We gonna create a centroid so we can rotate the points around a realistic center
        # Sorry for those of you that get weird rotations..
        x_list = [];
        y_list = [];

        for vertex in self._vertices:
            x_list.append(vertex.x());
            y_list.append(vertex.y());

        # Create a simple centroid (not full centroid)
        centroid_x = sum(x_list) / len(y_list);
        centroid_y = sum(y_list) / len(x_list);

        return Location(centroid_x, centroid_y);

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the object.
        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the object's rotation in degrees
        """

        if angle is not None:
            verify(angle, (float, int));
            self._angle = angle;
            self.update();

        return self._angle % 360;

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the object by a difference, in degrees
        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        verify(angle_diff, (float, int));
        self.rotation(self._angle + angle_diff);

    def angleto(self, obj) -> float:
        """
        Retrieve the angle between this object and another (based on 0 degrees at 12 o'clock)
        :param obj: the Object/Location to get the angle to.
        :return: the angle in degrees as a float
        """

        if isinstance(obj, Object):
            obj = obj.location();
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError('Renderable#lookat() must be passed either a renderable or a location!');

        location = Location(obj[0], obj[1]);
        # theta = -math.atan2(location.x() - self.x(), location.y() - self.y()) - math.radians(self.rotation());
        theta = math.atan2(location.y() - self.center().y(), location.x() - self.center().x()) \
            - math.radians(self.rotation()) + math.pi / 2;
        theta = math.degrees(theta);

        return theta;

    def lookat(self, obj) -> None:
        """
        Look at another object (Objects or Locations)
        :param obj: the Object/Location to look at.
        :return: None
        """

        theta = self.angleto(obj);
        self.rotate(theta);

    def forward(self, distance: float) -> None:
        """
        Move the Renderable forward by distance at its current heading (rotation/angle)
        :param distance: the distance to move forward (hypotenuse)
        :return: None
        """

        dx = distance * math.sin(math.radians(self._angle));
        dy = distance * -math.cos(math.radians(self._angle));

        self.move(dx, dy);

    def backward(self, distance: float) -> None:
        """
        Move the Renderable backward by distance at its current heading (rotation/angle)
        :param distance: the distance to move backward (hypotenuse)
        :return: None
        """

        self.forward(-distance);

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the object
        :param color: the color to set to, if any
        :return: the color of the object
        """

        if color is not None:
            verify(color, Color);
            self._color = color;
            self.update();

        return self._color;

    def border(self, color: Color = None, width: float = None, fill: bool = None) -> Color:
        """
        Add or get the border of the object
        :param color: the color to set the border too, set to Color.NONE to remove border
        :param width: the width of the border
        :param fill: whether to fill the polygon.
        :return: The Color of the border
        """

        update = False;

        if color is not None:
            verify(color, Color);
            self._border = color;
            update = True;
        if fill is not None:
            verify(fill, bool);
            self._fill = fill;
            update = True;
        if width is not None:
            verify(width, (float, int));
            self._borderwidth = width;
            update = True;

        if update:
            self.update();

        return self._border;

    def border_width(self, width: float = None) -> float:
        """
        Gets or sets the border width
        :param width: the border width to set to
        :return: the border width
        """

        if width is not None:
            verify(width, (float, int));
            self._borderwidth = width;
            self.update();

        return self._borderwidth;

    def fill(self, fill: bool = None) -> bool:
        """
        Returns or sets the current fill boolean
        :param fill: a new fill value, whether to fill the polygon
        :return: the fill value
        """

        if fill is not None:
            verify(fill, bool);
            self._fill = fill;
            self.update();

        return self._fill;

    def distance(self, obj) -> float:
        """
        Returns the distance between two objs or locations in pixels (center to center)
        :param obj: the Renderable/location to check distance between
        :return: the distance between this obj and the passed Renderable/Location.
        """

        if type(obj) is not Location and not isinstance(obj, Renderable):
            raise InvalidArgumentError(f'.distance() must be passed a Renderable or a Location! '
                                       f'(Passed: {type(obj)}');

        location = obj if type(obj) is Location else obj.center();

        return math.sqrt((location.x() - self.center().x()) ** 2 + (location.y() - self.center().y()) ** 2);

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the renderable.
        :param visible: the new visibility value, if any
        :return: the visibility value
        """

        if visible is not None:
            verify(visible, bool);
            self._visible = visible;
            self.update();

        return self._visible;

    def transform(self, transform: tuple = None) -> tuple:
        """
        Get or set the transform of the Renderable.
        Transforms represent the width, height, and rotation of Renderables.

        You can retrieve a Transform from a Renderable with this method and set the transform the same way.
        :param transform: the transform to set to, if any.
        :return: the transform
        """

        if transform is not None:
            verify(transform, tuple);
            if not len(transform) == 3:
                raise InvalidArgumentError('Ensure you are passing in a Transform from another object or a '
                                           'tuple in the following order: (width, height, rotation)');
            verify(transform[0], (float, int), transform[1], (float, int), transform[2], (float, int));
            self.width(transform[0]);
            self.height(transform[1]);
            self.rotation(transform[2]);

        return self.width(), self.height(), self.rotation();

    def clone(self):
        """
        Clone this renderable!
        :return: a Renderable
        """

        constructor = type(self);

        return constructor(self._screen, self.x(), self.y(), self.width(), self.height(), self.color(), self.border(),
                           self.fill(), self.rotation(), self.visible());

    def vertices(self) -> list:
        """
        Returns the list of vertices for the Renderable.
        (The vertices will be returned clockwise, starting from the top-leftmost point)
        :return: a list of Locations representing the vertices
        """
        return self._get_vertices();

    def bounds(self) -> (Location, float, float):
        """
        Get the location and dimensions of a bounding box that contains the entire shape
        :return: a tuple containing the Location, width, and height.
        """

        x0, y0, x1, y1 = self._screen._screen.cv.bbox(self._ref);
        location = self._screen.create_location(x0, y0, canvas=True);

        return location, (x1 - x0), (y1 - y0);

    def contains(self, *args) -> bool:
        """
        Returns whether or not a Location is contained within the object.
        :param args: You may pass in either two numbers, a Location, or a tuple containing and x and y point.
        :return: a boolean value representing whether or not the point is within the vertices of the object.
        """

        x, y = 0, 0;
        count = 0;

        if len(args) == 1:
            verify(args, (tuple, Location));
            if type(args[0]) is Location:
                x = args[0].x();
                y = args[0].y();
            elif type(args[0]) is tuple and len(args[0]) == 2:
                x = args[0][0];
                y = args[0][1];
        elif len(args) == 2:
            verify(args[0], (float, int), args[1], (float, int));
            if type(args[0]) is not float and type(args[0]) is not int \
                    and type(args[1]) is not float and type(args[1]) is not int:
                raise InvalidArgumentError('Passed arguments must be numbers (x, y), '
                                           'or you may pass a location/tuple.');
            x = args[0];
            y = args[1];
        else:
            raise InvalidArgumentError('You must pass in a tuple, Location, or two numbers (x, y)!');

        # If the point isn't remotely near us, we don't need to perform any calculations.
        if not isinstance(self, CustomRenderable) and self._angle == 0:
            if self.y() > 0 and self.x() > 0:
                if not (self.x() <= x <= (self.x() + self.width()) and self.y() <= y <= (self.y() + self.height())):
                    return False;

        # the contains algorithm uses the line-intersects algorithm to determine if a point is within a polygon.
        # we are going to cast a ray from our point to the positive x. (left to right)

        shape = self.vertices();
        shape = tuple(shape[:]) + (shape[0],);  # Add the first vertex back again to get the last edge.

        point1 = shape[0];
        for i in range(1, len(shape)):
            # A cool trick that gets the next index in an array, or the first index if i is the last index.
            # (since we start at index 1)
            point2 = shape[i % len(shape)];

            # make sure we're in the ballpark on the y axis (actually able to intersect on the x axis)
            if y > min(point1.y(), point2.y()):

                # Same thing as above
                if y <= max(point1.y(), point2.y()):

                    # Make sure our x is at least less than the max x of this line. (since we're travelling right)
                    if x <= max(point1.x(), point2.x()):

                        # If our y's are equal, that means this line is flat on the x, which makes us tricked until now.
                        # (We now realize we were never in the ballpark in the first place.
                        if point1.y() != point2.y():

                            # Now we get a possible intersection point from left to right.
                            intersects_x = (y - point1.y()) * (point2.x() - point1.x()) / \
                                           (point2.y() - point1.y()) + point1.x();

                            # if the line was vertical or we actually intersected it
                            if point1.x() == point2.x() or x <= intersects_x:
                                count += 1;

            # move up the ladder; next vertices and edge
            point1 = point2;

        return not (count % 2 == 0);

    def overlaps(self, other: 'Renderable') -> bool:
        """
        Returns if this object is overlapping with the passed object.
        :param other: another Renderable instance.
        :return: true if they are overlapping, false if not.
        """

        if not isinstance(other, Renderable):
            raise TypeError('Passed non-renderable into Renderable#overlaps(), which takes only Renderables!');

        x = self.x();
        y = self.y();
        width = self.width();
        height = self.height();

        other_x = other.x();
        other_y = other.y();
        other_width = other.width();
        other_height = other.height();

        # Only optimize if the angle is not zero.
        if self._angle % 360 == 0 and other._angle % 360 == 0:
            min_ax = x;
            max_ax = x + width;

            min_bx = other_x;
            max_bx = other_x + other_width;

            min_ay = y;
            max_ay = y + height;

            min_by = other_y;
            max_by = other_y + other_height;

            a_left_b = max_ax < min_bx;
            a_right_b = min_ax > max_bx;
            a_above_b = min_ay > max_by;
            a_below_b = max_ay < min_by;
        else:
            hypotenuse = math.sqrt(width ** 2 + height ** 2) + 1;
            other_hypotenuse = math.sqrt(other_width ** 2 + other_height ** 2) + 1;

            center = Location(x + width / 2, y + height / 2);
            other_center = Location(other_x + other_width / 2, other_y + other_height / 2);

            min_ax = center.x() - (hypotenuse / 2);
            max_ax = center.x() + (hypotenuse / 2);

            min_bx = other_center.x() - (other_hypotenuse / 2);
            max_bx = other_center.x() + (other_hypotenuse / 2);

            min_ay = center.y() - (hypotenuse / 2);
            max_ay = center.y() + (hypotenuse / 2);

            min_by = other_center.y() - (other_hypotenuse / 2);
            max_by = other_center.y() + (other_hypotenuse / 2);

            a_left_b = max_ax < min_bx;
            a_right_b = min_ax > max_bx;
            a_above_b = min_ay > max_by;
            a_below_b = max_ay < min_by;

        # Do a base check to make sure they are even remotely near each other.
        # TODO: Re-optimize with rotation in mind.
        # if other._angle % 360 == 0 and self._angle % 360 == 0:
        if a_left_b or a_right_b or a_above_b or a_below_b:
            return False;

        # Check if one shape is entirely inside the other shape
        if (min_ax >= min_bx and max_ax <= max_bx) and (min_ay >= min_by and max_ay <= max_by):
            return True;

        if (min_bx >= min_ax and max_bx <= max_ax) and (min_by >= min_ay and max_by <= max_ay):
            return True;

        # Next we are going to use a sweeping line algorithm.
        # Essentially we will process the lines on the x axis, one coordinate at a time (imagine a vertical line scan).
        # Then we will look for their orientations. We will essentially make sure its impossible they do not cross.
        shape1 = self.vertices();

        # noinspection PyProtectedMember
        shape2 = other.vertices();

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
                     (float(point2.x() - point1.x()) * (point3.y() - point2.y()));

            if result > 0:
                return 'clockwise';
            elif result < 0:
                return 'counter-clockwise';
            else:
                return 'co-linear';

        def point_on_segment(point1: Location, point2: Location, point3: Location) -> bool:
            """
            Returns if point3 lies on the segment formed by point1 and point2.
            """

            return max(point1.x(), point3.x()) >= point2.x() >= min(point1.x(), point3.x()) \
                   and max(point1.y(), point3.y()) >= point2.y() >= min(point1.y(), point3.y());

        # Okay to begin actually detecting orientations, we want to loop through some edges. But only ones that are
        # relevant. In order to do this we will first have to turn the list of vertices into a list of edges.
        # Then we will look through the lists of edges and find the ones closest to each other.

        shape1_edges = [];
        shape2_edges = [];

        shape1 = tuple(shape1[:]) + (shape1[0],);
        shape2 = tuple(shape2[:]) + (shape2[0],);

        shape1_point1 = shape1[0];
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)];  # 1, 2, 3, 3 % 5
            shape1_edges.append((shape1_point1, shape1_point2));
            shape1_point1 = shape1_point2;

        shape2_point1 = shape2[0];
        for i in range(1, len(shape2)):
            shape2_point2 = shape2[i % len(shape2)];
            shape2_edges.append((shape2_point1, shape2_point2));
            shape2_point1 = shape2_point2;

        # Now we are going to test the four orientations that the segments form
        for edge1 in shape1_edges:
            for edge2 in shape2_edges:
                orientation1 = orientation(edge1[0], edge1[1], edge2[0]);
                orientation2 = orientation(edge1[0], edge1[1], edge2[1]);
                orientation3 = orientation(edge2[0], edge2[1], edge1[0]);
                orientation4 = orientation(edge2[0], edge2[1], edge1[1]);

                # If orientations 1 and 2 are different as well as 3 and 4 then they intersect!
                if orientation1 != orientation2 and orientation3 != orientation4:
                    return True;

                # There's some special cases we should check where a point from one segment is on the other segment
                if orientation1 == 'co-linear' and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True;

                if orientation2 == 'co-linear' and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True;

                if orientation3 == 'co-linear' and point_on_segment(edge2[0], edge1[0], edge2[1]):
                    return True;

                if orientation4 == 'co-linear' and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True;

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False;

    # noinspection PyProtectedMember
    # noinspection PyUnresolvedReferences
    def _get_vertices(self):
        real_shape = self._vertices;
        # real_shape.reverse();
        #
        # min_distance = 999999;
        # top_left_index = 0;
        # for i, location in enumerate(real_shape):
        #     distance = math.sqrt((location.x()) ** 2 + (location.y()) ** 2);
        #     if distance < min_distance:
        #         min_distance = distance;
        #         top_left_index = i;
        #
        # real_shape = real_shape[top_left_index:] + real_shape[:top_left_index];

        return real_shape;

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occured while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)');

        shape = self._shape;  # List of normal vertices.

        width = self._width;
        height = self._height;

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);

        self._vertices = vertices;

        self._vertices = self._rotate(self._vertices, self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        color_state = self._color if self._fill else Color.NONE;

        # noinspection PyProtectedMember
        self._ref = self._screen._canvas.create_polygon(
            tk_vertices,
            fill=self._screen._colorstr(color_state),
            outline=self._screen._screen._colorstr(self._border.__value__()),
            width=self._borderwidth,
            state=state,
            joinstyle=tk.MITER
        );
        # self.update(); # CustomPolygon(self._screen, vertices);

    def _rotate(self, vertices: list, angle: float, pivot: Location = None) -> list:
        # We have to update here since we cannot remember previous rotations (update method call won't cut it)!
        # vertices = self._vertices;

        # First get some values that we gonna use later
        theta = math.radians(angle);
        cosine = math.cos(theta);
        sine = math.sin(theta);

        if pivot is None:
            centroid_x = self.center().x();
            centroid_y = self.center().y();
        else:
            centroid_x = pivot.x();
            centroid_y = pivot.y();

        new_vertices = []
        for vertex in vertices:
            # We have to create these separately because they're ironically used in each others calculations xD
            old_x = vertex.x() - centroid_x;
            old_y = vertex.y() - centroid_y;

            new_x = (old_x * cosine - old_y * sine) + centroid_x;
            new_y = (old_x * sine + old_y * cosine) + centroid_y;
            new_vertices.append(Location(new_x, new_y));

        return new_vertices;

    def update(self):
        self._check();

        old_ref = self._ref;
        shape = self._shape;  # List of normal vertices.

        width = self._width;
        height = self._height;

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];
        self._vertices = vertices;

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);

        self._vertices = self._rotate(self._vertices, self._angle);
        self._last_angle = self._angle;

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        color_state = self._color if self._fill else Color.NONE;
            
        try:
            # noinspection PyProtectedMember
            self._ref = self._screen._canvas.create_polygon(
                tk_vertices,
                fill=self._screen._colorstr(color_state),
                outline=self._screen._screen._colorstr(self._border.__value__()),
                width=self._borderwidth,
                state=state,
                joinstyle=tk.MITER
            );

            self._screen._canvas.tag_lower(self._ref, old_ref);
            self._screen._canvas.delete(old_ref);
        except:
            pass;


class FRenderable(Object):
    """
    Test class for new itemconfigure-based pyDraw objects.

    Update method is now only used for changes in position (and possibly changes that cannot be configured and require
    the item to be remade)
    """

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = Color.NONE,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super().__init__(screen, x, y, location);
        self._width = width;
        self._height = height;
        self._color = color;
        self._border = border if border is not None else Color('');
        self._border_width = 1;
        self._fill = fill;
        self._angle = rotation;
        self._last_angle = rotation;
        self._visible = visible;

        self._setup();

    def x(self, x: float = None) -> float:
        if x is not None:
            verify(x, (float, int));
            self.moveto(x, self.y());

        return self._location.x();

    def y(self, y: float = None) -> float:
        if y is not None:
            verify(y, (float, int));
            self.moveto(self.x(), y);

        return self._location.y();

    def location(self) -> Location:
        return self._location;

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)
        :return: None
        """

        self._location.move(*args, **kwargs);

        new_location = self._screen.canvas_location(self._location.x(), self._location.y())
        self._screen._canvas.moveto(self._ref, new_location.x(), new_location.y())
        # self.update();

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location; takes a Location, tuple, or two numbers (x, y)
        :return: None
        """

        self._location.moveto(*args, **kwargs);

        new_location = self._screen.canvas_location(self._location.x(), self._location.y())
        self._screen._canvas.moveto(self._ref, new_location.x(), new_location.y())
        # self.update();

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the object.
        :param width: the width to set to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int));
            self._width = width;
            new_location = self._screen.canvas_location(self._location.x(), self._location.y())
            new_location2 = self._screen.canvas_location(self._location.x() + self._width,
                                                         self._location.y() + self._height)
            print(f'old coords {self._screen._canvas.coords(self._ref)}')
            new_coords = [new_location[0], new_location[1], new_location2[0], new_location[1],
                          new_location2[0], new_location2[1], new_location[0], new_location2[1]]

            if self._angle % 360 != 0:
                self._update_coords()
            else:
                self._screen._canvas.coords(self._ref, new_coords)
            # self.update();

        return self._width;

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the object
        :param height: the height to set to in pixels, if any
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int));
            self._height = height;


            new_location = self._screen.canvas_location(self._location.x(), self._location.y())
            new_location2 = self._screen.canvas_location(self._location.x() + self._width,
                                                         self._location.y() + self._height)
            new_coords = [new_location[0], new_location[1], new_location2[0], new_location[1],
                          new_location2[0], new_location2[1], new_location[0], new_location2[1]]

            if self._angle % 360 != 0:
                self._update_coords()
            else:
                self._screen._canvas.coords(self._ref, new_coords)
            # self.update();

        return self._height;

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center
        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Renderable
        """

        centroid = False
        if len(args) == 0:
            if len(kwargs) > 0:
                if 'centroid' in kwargs:
                    if type(kwargs['centroid']) is bool:
                        centroid = kwargs['centroid'];
                    else:
                        raise InvalidArgumentError(
                            ".center() requires a boolean for centroid (whether to return a bounds "
                            "center or a calculated centroid).");
            return self._center(centroid=centroid);

        location = Location(self._center(centroid=centroid))

        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0]);
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError(".center() requires both x and y passed unless using keywords.");
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

                location.moveto(args[0], args[1]);
            else:
                raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        if len(kwargs) != 0:
            # TODO: Shouldn't this be called "location", not "move_to"
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");
            if 'centroid' in kwargs:
                if type(kwargs['centroid']) is bool:
                    centroid = kwargs['centroid'];
                else:
                    raise InvalidArgumentError(".center() requires a boolean for centroid (whether to return a bounds "
                                               "center or a calculated centroid).");

        return self._center(location, centroid);

    def _center(self, move_to: Location = None, centroid: bool = False):
        if move_to is not None:
            verify(move_to, Location);
            self.moveto(move_to.x() - self.width() / 2, move_to.y() - self.height() / 2);

        if not centroid:
            return Location(self.x() + self.width() / 2, self.y() + self.height() / 2);

        # We gonna create a centroid so we can rotate the points around a realistic center
        # Sorry for those of you that get weird rotations..
        x_list = [];
        y_list = [];

        for vertex in self._vertices:
            x_list.append(vertex.x());
            y_list.append(vertex.y());

        # Create a simple centroid (not full centroid)
        centroid_x = sum(x_list) / len(y_list);
        centroid_y = sum(y_list) / len(x_list);

        return Location(centroid_x, centroid_y);

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the object.
        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the object's rotation in degrees
        """

        if angle is not None:
            verify(angle, (float, int));
            self._angle = angle;
            self._update_coords()
            # self.update();

        return self._angle % 360;

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the object by a difference, in degrees
        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        verify(angle_diff, (float, int));
        self.rotation(self._angle + angle_diff);

    def angleto(self, obj) -> float:
        """
        Retrieve the angle between this object and another (based on 0 degrees at 12 o'clock)
        :param obj: the Object/Location to get the angle to.
        :return: the angle in degrees as a float
        """

        if isinstance(obj, Object):
            obj = obj.location();
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError('Renderable#lookat() must be passed either a renderable or a location!');

        location = Location(obj[0], obj[1]);
        # theta = -math.atan2(location.x() - self.x(), location.y() - self.y()) - math.radians(self.rotation());
        theta = math.atan2(location.y() - self.center().y(), location.x() - self.center().x()) \
                - math.radians(self.rotation()) + math.pi / 2;
        theta = math.degrees(theta);

        return theta;

    def lookat(self, obj) -> None:
        """
        Look at another object (Objects or Locations)
        :param obj: the Object/Location to look at.
        :return: None
        """

        theta = self.angleto(obj);
        self.rotate(theta);

    def forward(self, distance: float) -> None:
        """
        Move the Renderable forward by distance at its current heading (rotation/angle)
        :param distance: the distance to move forward (hypotenuse)
        :return: None
        """

        dx = distance * math.sin(math.radians(self._angle));
        dy = distance * -math.cos(math.radians(self._angle));

        self.move(dx, dy);

    def backward(self, distance: float) -> None:
        """
        Move the Renderable backward by distance at its current heading (rotation/angle)
        :param distance: the distance to move backward (hypotenuse)
        :return: None
        """

        self.forward(-distance);

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the object
        :param color: the color to set to, if any
        :return: the color of the object
        """

        if color is not None:
            verify(color, Color);
            self._color = color;
            # TODO: Can probably improve this speed with a custom _colorstr function on declaration
            color_state = self._color if self._fill else Color.NONE;
            self._screen._canvas.itemconfigure(self._ref,
                                               fill=self._screen._colorstr(color_state))
            # self.update();

        return self._color;

    def border(self, color: Color = None, width: float = None, fill: bool = None) -> Color:
        """
        Add or get the border of the object
        :param color: the color to set the border too, set to Color.NONE to remove border
        :param width: the width of the border
        :param fill: whether to fill the polygon.
        :return: The Color of the border
        """

        update = False;

        if color is not None:
            verify(color, Color);
            self._border = color;
            update = True;
        if fill is not None:
            verify(fill, bool);
            self._fill = fill;
            update = True;
        if width is not None:
            verify(width, (float, int));
            self._border_width = width;
            update = True;

        if update:
            color_state = self._color if self._fill else Color.NONE;
            self._screen._canvas.itemconfigure(self._ref, fill=self._screen._colorstr(color_state),
                                               outline=self._screen._screen._colorstr(self._border.__value__()),
                                               width=self._border_width)
            # self.update();

        return self._border;

    def border_width(self, width: float = None) -> float:
        """
        Gets or sets the border width
        :param width: the border width to set to
        :return: the border width
        """

        if width is not None:
            verify(width, (float, int));
            self._border_width = width;
            self._screen._canvas.itemconfigure(self._ref, width=self._border_width)
            # self.update();

        return self._border_width;

    def fill(self, fill: bool = None) -> bool:
        """
        Returns or sets the current fill boolean
        :param fill: a new fill value, whether to fill the polygon
        :return: the fill value
        """

        if fill is not None:
            verify(fill, bool);
            self._fill = fill;

            color_state = self._color if self._fill else Color.NONE;
            self._screen._canvas.itemconfigure(self._ref, fill=self._screen._colorstr(color_state))
            # self.update();

        return self._fill;

    def distance(self, obj) -> float:
        """
        Returns the distance between two objs or locations in pixels (center to center)
        :param obj: the Renderable/location to check distance between
        :return: the distance between this obj and the passed Renderable/Location.
        """

        if type(obj) is not Location and not isinstance(obj, Renderable):
            raise InvalidArgumentError(f'.distance() must be passed a Renderable or a Location! '
                                       f'(Passed: {type(obj)}');

        location = obj if type(obj) is Location else obj.center();

        return math.sqrt((location.x() - self.center().x()) ** 2 + (location.y() - self.center().y()) ** 2);

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the renderable.
        :param visible: the new visibility value, if any
        :return: the visibility value
        """

        if visible is not None:
            verify(visible, bool);
            self._visible = visible;

            state = tk.NORMAL if self._visible else tk.HIDDEN;
            self._screen._canvas.itemconfigure(self._ref, state=state)
            # self.update();

        return self._visible;

    def transform(self, transform: tuple = None) -> tuple:
        """
        Get or set the transform of the Renderable.
        Transforms represent the width, height, and rotation of Renderables.

        You can retrieve a Transform from a Renderable with this method and set the transform the same way.
        :param transform: the transform to set to, if any.
        :return: the transform
        """

        if transform is not None:
            verify(transform, tuple);
            if not len(transform) == 3:
                raise InvalidArgumentError('Ensure you are passing in a Transform from another object or a '
                                           'tuple in the following order: (width, height, rotation)');
            verify(transform[0], (float, int), transform[1], (float, int), transform[2], (float, int));
            self.width(transform[0]);
            self.height(transform[1]);
            self.rotation(transform[2]);

        return self.width(), self.height(), self.rotation();

    def clone(self):
        """
        Clone this renderable!
        :return: a Renderable
        """

        constructor = type(self);

        return constructor(self._screen, self.x(), self.y(), self.width(), self.height(), self.color(), self.border(),
                           self.fill(), self.rotation(), self.visible());

    def vertices(self) -> list:
        """
        Returns the list of vertices for the Renderable.
        (The vertices will be returned clockwise, starting from the top-leftmost point)
        :return: a list of Locations representing the vertices
        """

        return self._get_vertices();

    # noinspection PyProtectedMember
    def bounds(self) -> (Location, float, float):
        """
        Get the location and dimensions of a bounding box that contains the entire shape
        :return: a tuple containing the Location, width, and height.
        """

        x0, y0, x1, y1 = self._screen._screen.cv.bbox(self._ref);
        location = self._screen.create_location(x0, y0, canvas=True);

        return location, (x1 - x0), (y1 - y0);

    def contains(self, *args) -> bool:
        """
        Returns whether or not a Location is contained within the object.
        :param args: You may pass in either two numbers, a Location, or a tuple containing and x and y point.
        :return: a boolean value representing whether or not the point is within the vertices of the object.
        """

        x, y = 0, 0;
        count = 0;

        if len(args) == 1:
            verify(args, (tuple, Location));
            if type(args[0]) is Location:
                x = args[0].x();
                y = args[0].y();
            elif type(args[0]) is tuple and len(args[0]) == 2:
                x = args[0][0];
                y = args[0][1];
        elif len(args) == 2:
            verify(args[0], (float, int), args[1], (float, int));
            if type(args[0]) is not float and type(args[0]) is not int \
                    and type(args[1]) is not float and type(args[1]) is not int:
                raise InvalidArgumentError('Passed arguments must be numbers (x, y), '
                                           'or you may pass a location/tuple.');
            x = args[0];
            y = args[1];
        else:
            raise InvalidArgumentError('You must pass in a tuple, Location, or two numbers (x, y)!');

        # If the point isn't remotely near us, we don't need to perform any calculations.
        if not isinstance(self, CustomRenderable) and self._angle == 0:
            if self.y() > 0 and self.x() > 0:
                if not (self.x() <= x <= (self.x() + self.width()) and self.y() <= y <= (self.y() + self.height())):
                    return False;

        # the contains algorithm uses the line-intersects algorithm to determine if a point is within a polygon.
        # we are going to cast a ray from our point to the positive x. (left to right)

        shape = self.vertices();
        shape = tuple(shape[:]) + (shape[0],);  # Add the first vertex back again to get the last edge.

        point1 = shape[0];
        for i in range(1, len(shape)):
            # A cool trick that gets the next index in an array, or the first index if i is the last index.
            # (since we start at index 1)
            point2 = shape[i % len(shape)];

            # make sure we're in the ballpark on the y axis (actually able to intersect on the x axis)
            if y > min(point1.y(), point2.y()):

                # Same thing as above
                if y <= max(point1.y(), point2.y()):

                    # Make sure our x is at least less than the max x of this line. (since we're travelling right)
                    if x <= max(point1.x(), point2.x()):

                        # If our y's are equal, that means this line is flat on the x, which makes us tricked until now.
                        # (We now realize we were never in the ballpark in the first place.
                        if point1.y() != point2.y():

                            # Now we get a possible intersection point from left to right.
                            intersects_x = (y - point1.y()) * (point2.x() - point1.x()) / \
                                           (point2.y() - point1.y()) + point1.x();

                            # if the line was vertical or we actually intersected it
                            if point1.x() == point2.x() or x <= intersects_x:
                                count += 1;

            # move up the ladder; next vertices and edge
            point1 = point2;

        return not (count % 2 == 0);

    def overlaps(self, other: 'Renderable') -> bool:
        """
        Returns if this object is overlapping with the passed object.
        :param other: another Renderable instance.
        :return: true if they are overlapping, false if not.
        """

        if not isinstance(other, Renderable):
            raise TypeError('Passed non-renderable into Renderable#overlaps(), which takes only Renderables!');

        x = self.x();
        y = self.y();
        width = self.width();
        height = self.height();

        other_x = other.x();
        other_y = other.y();
        other_width = other.width();
        other_height = other.height();

        # Only optimize if the angle is not zero.
        if self._angle % 360 == 0 and other._angle % 360 == 0:
            min_ax = x;
            max_ax = x + width;

            min_bx = other_x;
            max_bx = other_x + other_width;

            min_ay = y;
            max_ay = y + height;

            min_by = other_y;
            max_by = other_y + other_height;

            a_left_b = max_ax < min_bx;
            a_right_b = min_ax > max_bx;
            a_above_b = min_ay > max_by;
            a_below_b = max_ay < min_by;
        else:
            hypotenuse = math.sqrt(width ** 2 + height ** 2) + 1;
            other_hypotenuse = math.sqrt(other_width ** 2 + other_height ** 2) + 1;

            center = Location(x + width / 2, y + height / 2);
            other_center = Location(other_x + other_width / 2, other_y + other_height / 2);

            min_ax = center.x() - (hypotenuse / 2);
            max_ax = center.x() + (hypotenuse / 2);

            min_bx = other_center.x() - (other_hypotenuse / 2);
            max_bx = other_center.x() + (other_hypotenuse / 2);

            min_ay = center.y() - (hypotenuse / 2);
            max_ay = center.y() + (hypotenuse / 2);

            min_by = other_center.y() - (other_hypotenuse / 2);
            max_by = other_center.y() + (other_hypotenuse / 2);

            a_left_b = max_ax < min_bx;
            a_right_b = min_ax > max_bx;
            a_above_b = min_ay > max_by;
            a_below_b = max_ay < min_by;

        # Do a base check to make sure they are even remotely near each other.
        # TODO: Re-optimize with rotation in mind.
        # if other._angle % 360 == 0 and self._angle % 360 == 0:
        if a_left_b or a_right_b or a_above_b or a_below_b:
            return False;

        # Check if one shape is entirely inside the other shape
        if (min_ax >= min_bx and max_ax <= max_bx) and (min_ay >= min_by and max_ay <= max_by):
            return True;

        if (min_bx >= min_ax and max_bx <= max_ax) and (min_by >= min_ay and max_by <= max_ay):
            return True;

        # Next we are going to use a sweeping line algorithm.
        # Essentially we will process the lines on the x axis, one coordinate at a time (imagine a vertical line scan).
        # Then we will look for their orientations. We will essentially make sure its impossible they do not cross.
        shape1 = self.vertices();

        # noinspection PyProtectedMember
        shape2 = other.vertices();

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
                     (float(point2.x() - point1.x()) * (point3.y() - point2.y()));

            if result > 0:
                return 'clockwise';
            elif result < 0:
                return 'counter-clockwise';
            else:
                return 'co-linear';

        def point_on_segment(point1: Location, point2: Location, point3: Location) -> bool:
            """
            Returns if point3 lies on the segment formed by point1 and point2.
            """

            return max(point1.x(), point3.x()) >= point2.x() >= min(point1.x(), point3.x()) \
                   and max(point1.y(), point3.y()) >= point2.y() >= min(point1.y(), point3.y());

        # Okay to begin actually detecting orientations, we want to loop through some edges. But only ones that are
        # relevant. In order to do this we will first have to turn the list of vertices into a list of edges.
        # Then we will look through the lists of edges and find the ones closest to each other.

        shape1_edges = [];
        shape2_edges = [];

        shape1 = tuple(shape1[:]) + (shape1[0],);
        shape2 = tuple(shape2[:]) + (shape2[0],);

        shape1_point1 = shape1[0];
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)];  # 1, 2, 3, 3 % 5
            shape1_edges.append((shape1_point1, shape1_point2));
            shape1_point1 = shape1_point2;

        shape2_point1 = shape2[0];
        for i in range(1, len(shape2)):
            shape2_point2 = shape2[i % len(shape2)];
            shape2_edges.append((shape2_point1, shape2_point2));
            shape2_point1 = shape2_point2;

        # Now we are going to test the four orientations that the segments form
        for edge1 in shape1_edges:
            for edge2 in shape2_edges:
                orientation1 = orientation(edge1[0], edge1[1], edge2[0]);
                orientation2 = orientation(edge1[0], edge1[1], edge2[1]);
                orientation3 = orientation(edge2[0], edge2[1], edge1[0]);
                orientation4 = orientation(edge2[0], edge2[1], edge1[1]);

                # If orientations 1 and 2 are different as well as 3 and 4 then they intersect!
                if orientation1 != orientation2 and orientation3 != orientation4:
                    return True;

                # There's some special cases we should check where a point from one segment is on the other segment
                if orientation1 == 'co-linear' and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True;

                if orientation2 == 'co-linear' and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True;

                if orientation3 == 'co-linear' and point_on_segment(edge2[0], edge1[0], edge2[1]):
                    return True;

                if orientation4 == 'co-linear' and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True;

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False;

    def _get_vertices(self):
        real_shape = self._vertices;
        return real_shape;

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occurred while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)');

        shape = self._shape;  # List of normal vertices.

        width = self._width;
        height = self._height;

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);

        self._vertices = vertices;

        self._vertices = self._rotate(self._vertices, self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        color_state = self._color if self._fill else Color.NONE;

        # noinspection PyProtectedMember
        self._ref = self._screen._canvas.create_polygon(
            tk_vertices,
            fill=self._screen._colorstr(color_state),
            outline=self._screen._screen._colorstr(self._border.__value__()),
            width=self._border_width,
            state=state,
            joinstyle=tk.MITER
        );
        # self.update(); # CustomPolygon(self._screen, vertices);

    def _rotate(self, vertices: list, angle: float, pivot: Location = None) -> list:
        # We have to update here since we cannot remember previous rotations (update method call won't cut it)!
        # vertices = self._vertices;

        # First get some values that we gonna use later
        theta = math.radians(angle);
        cosine = math.cos(theta);
        sine = math.sin(theta);

        if pivot is None:
            centroid_x = self.center().x();
            centroid_y = self.center().y();
        else:
            centroid_x = pivot.x();
            centroid_y = pivot.y();

        new_vertices = []
        for vertex in vertices:
            # We have to create these separately because they're ironically used in each others calculations xD
            old_x = vertex.x() - centroid_x;
            old_y = vertex.y() - centroid_y;

            new_x = (old_x * cosine - old_y * sine) + centroid_x;
            new_y = (old_x * sine + old_y * cosine) + centroid_y;
            new_vertices.append(Location(new_x, new_y));

        return new_vertices;

    def _update_coords(self):
        shape = self._shape;  # List of normal vertices.

        width = self._width;
        height = self._height;

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);

        self._vertices = vertices;

        if self._angle % 360 != 0:
            self._vertices = self._rotate(self._vertices, self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append(vertex.x() - (self._screen.width() / 2));
            tk_vertices.append((vertex.y() - (self._screen.height() / 2)));

        self._screen._canvas.coords(self._ref, tk_vertices)

    def update(self):
        self._check();

        old_ref = self._ref;
        shape = self._shape;  # List of normal vertices.

        width = self._width;
        height = self._height;

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];
        self._vertices = vertices;

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);

        self._vertices = self._rotate(self._vertices, self._angle);
        self._last_angle = self._angle;

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        color_state = self._color if self._fill else Color.NONE;

        try:
            # noinspection PyProtectedMember
            self._ref = self._screen._canvas.create_polygon(
                tk_vertices,
                fill=self._screen._colorstr(color_state),
                outline=self._screen._screen._colorstr(self._border.__value__()),
                width=self._border_width,
                state=state,
                joinstyle=tk.MITER
            );

            self._screen._canvas.tag_lower(self._ref, old_ref);
            self._screen._canvas.delete(old_ref);
        except:
            pass;


class FRectangle(FRenderable):
    @overload(Screen, (int, float), (int, float), (int, float), (int, float))
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height), Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);


class CustomRenderable(Renderable):
    """
    A wrapper class to distintify classes that extend Renderable but have some custom functionality.
    """
    pass;


class RoundedRectangle(CustomRenderable):
    """
    CustomRenderable that creates a rounded rectangle utilizing the border system.
    As a result borders are unavailable and immutable in this Object.
    """

    @overload(Screen, (int, float), (int, float), (int, float), (int, float))
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 radius: float = 10,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._screen = screen;
        self._screen.add(self);

        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                          Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));

        self._location = Location(x, y);
        self._width = width;
        self._height = height;
        self._color = color;
        self._border = color;
        self._fill = fill;
        self._angle = rotation;
        self._visible = visible;
        self._borderwidth = radius;

        self._setup();

    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 radius: float = 10,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._screen = screen;
        self._screen.add(self);

        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                          Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));

        self._location = Location(x, y);
        self._width = width;
        self._height = height;
        self._color = color;
        self._border = color;
        self._fill = fill;
        self._angle = rotation;
        self._visible = visible;
        self._borderwidth = radius;

        self._setup();

    @overload(Screen, Location, (int, float), (int, float))
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 radius: float = 10,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._screen = screen;
        self._screen.add(self);

        self._vertices = [Location(location.x(), location.y()), Location(location.x() + width, location.y()), Location(location.x() + width, location.y() + height),
                          Location(location.x(), location.y() + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));

        self._location = location.clone();
        self._width = width;
        self._height = height;
        self._color = color;
        self._border = color;
        self._fill = fill;
        self._angle = rotation;
        self._visible = visible;
        self._borderwidth = radius;

        self._setup();

    @overload(Screen, Location, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 radius: float = 10,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._screen = screen;
        self._screen.add(self);

        self._vertices = [Location(location.x(), location.y()), Location(location.x() + width, location.y()), Location(location.x() + width, location.y() + height),
                          Location(location.x(), location.y() + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));

        self._location = location.clone();
        self._width = width;
        self._height = height;
        self._color = color;
        self._border = color;
        self._fill = fill;
        self._angle = rotation;
        self._visible = visible;
        self._borderwidth = radius;

        self._setup();

    # We redefine the border method to do nothing
    # def border(self, color: Color = None, width: float = 1, fill: bool = None) -> Color:
    #     raise NotImplemented("This method is not allowed for `Rounded` shapes.")
    border = property(doc='(!) Disallowed inherited')

    def radius(self, radius: float = None) -> float:
        """
        Set the border radius of the rounded shape.
        :param radius: the radius to set to (not pixel accurate)
        :return: the radius
        """

        if radius is not None:
            self._borderwidth = radius;
            self._update();

        return self._borderwidth;

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occured while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)');

        shape = self._shape;  # List of normal vertices.

        width = self._width;
        height = self._height;

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);

        self._vertices = vertices;

        self._vertices = self._rotate(self._vertices, self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        color_state = self._color if self._fill else Color.NONE;

        print(self._borderwidth)
        # noinspection PyProtectedMember
        self._ref = self._screen._canvas.create_polygon(
            tk_vertices,
            fill=self._screen._colorstr(color_state),
            outline=self._screen._colorstr(self._color),  # self._screen._screen._colorstr(self._border.__value__()),
            width=self._borderwidth,
            state=state,
            joinstyle=tk.ROUND
        );
        # self.update(); # CustomPolygon(self._screen, vertices);

    def update(self):
        self._check();

        old_ref = self._ref;
        shape = self._shape;  # List of normal vertices.

        width = self._width;
        height = self._height;

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];
        self._vertices = vertices;

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);

        self._vertices = self._rotate(self._vertices, self._angle);
        self._last_angle = self._angle;

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        color_state = self._color if self._fill else Color.NONE;

        try:
            # noinspection PyProtectedMember
            self._ref = self._screen._canvas.create_polygon(
                tk_vertices,
                fill=self._screen._colorstr(color_state),
                outline=self._screen._screen._colorstr(self._border.__value__()),
                width=self._borderwidth,
                state=state,
                joinstyle=tk.ROUND
            );

            self._screen._canvas.tag_lower(self._ref, old_ref);
            self._screen._canvas.delete(old_ref);
        except:
            pass;


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
        self._screen = screen;
        self._color = color;
        self._border = border if border is not None else Color('');
        self._borderwidth = 1;
        self._fill = fill;
        self._angle = rotation;
        self._visible = visible;

        self._screen._add(self);

        if len(vertices) <= 2:
            raise InvalidArgumentError('Must pass at least 3 vertices to CustomPolygon!');

        xmin = vertices[0][0];
        xmax = vertices[0][0];
        ymin = vertices[0][1];
        ymax = vertices[0][1];

        real_vertices = [];
        for vertex in vertices:
            new_vertex = Location(vertex[0], vertex[1]);
            real_vertices.append(new_vertex);

            if new_vertex.x() < xmin:
                xmin = new_vertex.x();
            if new_vertex.x() > xmax:
                xmax = new_vertex.x();

            if new_vertex.y() < ymin:
                ymin = new_vertex.y();
            if new_vertex.y() > ymax:
                ymax = new_vertex.y();

        self._numsides = len(real_vertices);
        self._vertices = real_vertices;
        self._current_vertices = self._vertices;
        self._location = Location(xmin, ymin);
        self._width = xmax - xmin;
        self._height = ymax - ymin;

        color_state = self._color if self._fill else Color.NONE;

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in real_vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));
            # tk_vertices.append((self.x() - ((self._screen.width() / 2) + 1),
            #                                 (self.y() - (self._screen.height() / 2)) + self.height()));

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        self._ref = self._screen._screen.cv.create_polygon(
            tk_vertices,
            fill=self._screen._colorstr(color_state),
            outline=self._screen._screen._colorstr(self._border.__value__()),
            width=self._borderwidth,
            state=state
        );

    def move(self, *args, **kwargs):
        """
        Can take either a tuple, Location, or two numbers (dx, dy)
        :return: None
        """

        for vertice in self._vertices:
            vertice.move(*args, **kwargs);

        self._location.move(*args, **kwargs);
        self.update();

    def moveto(self, *args, **kwargs):
        """
        Move to a new location; takes a Location, tuple, or two numbers (x, y)
        :return: None
        """

        location = self._location;

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and type(args[0]) is tuple or type(args[0]) is Location:
                location = Location(args[0][0], args[0][1]);
            elif len(args) == 2 and [type(arg) is float or type(arg) is int for arg in args]:
                location = Location(args[0], args[1]);

        for (name, value) in kwargs.items():
            if len(kwargs) == 0 or type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('Object#move() must take either a tuple/location '
                                           'or two numbers (dx, dy)!');

            if name.lower() == 'x':
                location = Location(value, location.y());
            if name.lower() == 'y':
                location = Location(location.x(), value);

        diff = (location.x() - self._location.x(), location.y() - self._location.y());
        self.move(diff);

    def width(self, width: float = None) -> float:
        """
        Get the width of the CustomPolygon
        :param width: Unsupported.
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int));
            self._width = width;
            self.update();
            # raise UnsupportedError('Modifying the width/height of CustomPolygons is not currently possible');

        return self._width;

    def height(self, height: float = None) -> float:
        """
        Get the height of the Polygon
        :param height: Unsupported.
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int))
            self._height = height;
            self.update();
            # raise UnsupportedError('Modifying the width/height of CustomPolygons is not currently possible');

        return self._height;

    def rotate(self, angle_diff: float = 0) -> None:
        verify(angle_diff, (float, int));

        self._angle += angle_diff;

        if self._angle >= 360:
            self._angle = self._angle - 360;

        self.update();

    def rotation(self, angle: float = None) -> float:
        if angle is not None:
            verify(angle, (float, int));
            self._angle = angle;
            self.update();

        return self._angle;

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center
        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing centroid of CustomRenderable
        """

        if len(args) == 0 and len(kwargs) == 0:
            return self._center();

        location = Location(self._center())
        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0]);
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError(".center() requires both x and y passed unless using keywords.");
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

                location.moveto(args[0], args[1]);
            else:
                raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        return self._center(location);

    def _center(self, moveto: Location = None) -> Location:

        # We gonna create a centroid so we can rotate the points around a realistic center
        # Sorry for those of you that get weird rotations..
        x_list = [];
        y_list = [];
        for vertex in self._vertices:
            x_list.append(vertex.x());
            y_list.append(vertex.y());

        # Create a simple centroid (not full centroid)
        centroid_x = sum(x_list) / len(y_list);
        centroid_y = sum(y_list) / len(x_list);

        diff_x = 0
        diff_y = 0

        if moveto is not None:
            verify(moveto, Location);
            diff_x = moveto.x() - centroid_x
            diff_y = moveto.y() - centroid_y
            self.move(diff_x, diff_y);

        return Location(centroid_x + diff_x, centroid_y + diff_y);

    def vertices(self) -> list:
        return self._current_vertices.copy();

    def clone(self):
        """
        Clone this CustomPolygon!
        :return: a CustomPolygon
        """
        return CustomPolygon(self._screen, self._vertices, self._color, self._border, self._fill, self._angle,
                             self._visible);

    def transform(self, transform: tuple = None) -> tuple:
        if transform is not None:
            raise UnsupportedError('Setting Renderable#transform() is not supported for CustomPolygon!');

        return self.width(), self.height(), self.rotation();

    def _rotate(self, angle: float) -> list:
        # We have to update here since we cannot remember previous rotations (update method call won't cut it)!
        vertices = self._current_vertices;

        # First get some values that we gonna use later
        theta = math.radians(angle);
        cosine = math.cos(theta);
        sine = math.sin(theta);

        centroid_x = self.center().x();
        centroid_y = self.center().y();

        new_vertices = []
        for vertex in vertices:
            # We have to create these separately because they're ironically used in each others calculations xD
            old_x = vertex.x() - centroid_x;
            old_y = vertex.y() - centroid_y;

            new_x = (old_x * cosine - old_y * sine) + centroid_x;
            new_y = (old_x * sine + old_y * cosine) + centroid_y;
            new_vertices.append(Location(new_x, new_y));

        return new_vertices;

    def update(self):
        self._check();

        old_ref = self._ref;

        xmin = self._vertices[0][0];
        xmax = self._vertices[0][0];
        ymin = self._vertices[0][1];
        ymax = self._vertices[0][1];

        for vertex in self._vertices:
            if vertex.x() < xmin:
                xmin = vertex.x();
            if vertex.x() > xmax:
                xmax = vertex.x();

            if vertex.y() < ymin:
                ymin = vertex.y();
            if vertex.y() > ymax:
                ymax = vertex.y();

        self._numsides = len(self._vertices);
        self._location = Location(xmin, ymin);

        width = xmax - xmin;
        height = ymax - ymin;

        cx = xmin + (width / 2);
        cy = ymin + (height / 2);

        # calculate the scaling factor
        scale_factor = (self._width / width, self._height / height);

        self._current_vertices = self._vertices.copy();
        for vertex in self._current_vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, scale_factor[1] * (vertex.y() - cy) + cy);
            vertex.move(dx=(self._width - width) / 2);
            vertex.move(dy=(self._height - height) / 2);

        self._current_vertices = self._rotate(self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._current_vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        color_state = self._color if self._fill else Color.NONE;

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        self._ref = self._screen._screen.cv.create_polygon(
            tk_vertices,
            fill=self._screen._colorstr(color_state),
            outline=self._screen._screen._colorstr(self._border.__value__()),
            width=self._borderwidth,
            state=state
        );

        self._screen._screen.cv.tag_lower(self._ref, old_ref);
        self._screen._screen.cv.delete(old_ref);


class Rectangle(Renderable):
    @overload(Screen, (int, float), (int, float), (int, float), (int, float))
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height), Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height), Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height), Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float))
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                          Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();


        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                          Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                          Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);


class Oval(Renderable):
    _default = ((10, 0), (9.51, 3.09), (8.09, 5.88),
                (5.88, 8.09), (3.09, 9.51), (0, 10), (-3.09, 9.51),
                (-5.88, 8.09), (-8.09, 5.88), (-9.51, 3.09), (-10, 0),
                (-9.51, -3.09), (-8.09, -5.88), (-5.88, -8.09),
                (-3.09, -9.51), (-0.00, -10.00), (3.09, -9.51),
                (5.88, -8.09), (8.09, -5.88), (9.51, -3.09));

    @overload(Screen, (int, float), (int, float), (int, float), (int, float))
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._width = width;
        self._height = height;

        self._wedges = PIXEL_RATIO;

        vertices = self._convert_vertices();
        self._shape = vertices;
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._width = width;
        self._height = height;

        self._wedges = PIXEL_RATIO;

        vertices = self._convert_vertices();
        self._shape = vertices;
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._width = width;
        self._height = height;

        self._wedges = PIXEL_RATIO;

        vertices = self._convert_vertices();
        self._shape = vertices;
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float))
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._width = width;
        self._height = height;

        self._wedges = PIXEL_RATIO;

        vertices = self._convert_vertices();
        self._shape = vertices;
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._width = width;
        self._height = height;

        self._wedges = PIXEL_RATIO;

        vertices = self._convert_vertices();
        self._shape = vertices;
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._width = width;
        self._height = height;

        self._wedges = PIXEL_RATIO;

        vertices = self._convert_vertices();
        self._shape = vertices;
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    def wedges(self, wedges: int = None) -> int:
        verify(wedges, int);
        if wedges < 20:
            raise InvalidArgumentError('Ovals can be at least 20 wedges. If you need less, '
                                       'just multiply your desired amount by 2 until it is above 20!');

        if wedges is not None:
            self._shape = self._generate_vertices(PIXEL_RATIO / 2, wedges=wedges);
            self._wedges = wedges;
            self.update();

        return self._wedges;

    def slices(self) -> list:
        """
        Gets the slices of the Oval based on wedges. Note that this generates slices that are not tied to the oval,
        these are simply slices of the oval based on its wedges. You can use them how you see fit.
        :return: a tuple (immutable list) of CustomPolygons
        """

        return self._generate_slices();

    def _generate_slices(self) -> list:
        shape = self.vertices();
        shape = tuple(shape[:]) + (shape[0],);

        slices = [];
        for i in range(0, len(shape) - 1):
            vertex1 = shape[i];
            vertex2 = self.center();
            vertex3 = shape[i + 1];

            slc = CustomPolygon(self._screen, [vertex1, vertex2, vertex3], self.color());
            slices.append(slc);
        return slices;

    def _convert_vertices(self):
        radius = ((self._width + self._height) / 2) / 2;
        angle = 18 if radius <= 150 else (radius * 9) / 300;
        shape_vertices = self._generate_vertices(PIXEL_RATIO / 2, angle);

        return shape_vertices;

    @staticmethod
    def _generate_vertices(radius, angle: float = 18, wedges: int = None):
        relative_vertices = []

        if wedges is not None:
            angle = 360 / wedges;

        for x in range(0, 360, int(angle)):
            radians = math.radians(x);
            x = radius * math.cos(radians);
            y = radius * math.sin(radians);
            relative_vertices.append((x, y));

        return relative_vertices;


class Triangle(Renderable):
    @overload(Screen, (int, float), (int, float), (int, float), (int, float))
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float))
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, Location, (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);


class Polygon(Renderable):

    @overload(Screen, int, (int, float), (int, float), (int, float), (int, float))
    def __init__(self, screen: Screen, num_sides: int, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._num_sides = num_sides;
        radius = PIXEL_RATIO / 2;
        shape_points = [];
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)));
        self._shape = shape_points;

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, int, (int, float), (int, float), (int, float), (int, float), Color)
    def __init__(self, screen: Screen, num_sides: int, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._num_sides = num_sides;
        radius = PIXEL_RATIO / 2;
        shape_points = [];
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)));
        self._shape = shape_points;

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, int, (int, float), (int, float), (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, num_sides: int, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._num_sides = num_sides;
        radius = PIXEL_RATIO / 2;
        shape_points = [];
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)));
        self._shape = shape_points;

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, int, Location, (int, float), (int, float))
    def __init__(self, screen: Screen, num_sides: int, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._num_sides = num_sides;
        radius = PIXEL_RATIO / 2;
        shape_points = [];
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)));
        self._shape = shape_points;

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, int, Location, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, num_sides: int, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._num_sides = num_sides;
        radius = PIXEL_RATIO / 2;
        shape_points = [];
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)));
        self._shape = shape_points;

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    @overload(Screen, int, Location, (int, float), (int, float), Color, Color)
    def __init__(self, screen: Screen, num_sides: int, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x();
        y = location.y();

        self._num_sides = num_sides;
        radius = PIXEL_RATIO / 2;
        shape_points = [];
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)));
        self._shape = shape_points;

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occured while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)');

        shape = self._shape;  # List of normal vertices.

        a = math.pi * 2 / self._num_sides * (PIXEL_RATIO / 2);
        n = self._num_sides;

        # Degree converted to radians
        apothem = a / (2 * math.tan((180 / n) *
                                    math.pi / 180));

        true_width = PIXEL_RATIO;
        true_height = apothem * 2;

        width = self._width;
        height = self._height;

        scale_factor = (width / true_width, height / true_height);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);
            vertex.move(dy=PIXEL_RATIO - true_height);

        self._vertices = vertices;

        self._vertices = self._rotate(self._vertices, self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        # noinspection PyProtectedMember
        self._ref = self._screen._canvas.create_polygon(
            tk_vertices,
            fill=self._screen._colorstr(self._color),
            outline=self._screen._screen._colorstr(self._border.__value__()),
            width=self._borderwidth,
            state=state
        );

    # noinspection PyProtectedMember
    def update(self):
        self._check();

        old_ref = self._ref;
        shape = self._shape;  # List of normal vertices.

        a = math.pi * 2 / self._num_sides * (PIXEL_RATIO / 2);
        n = self._num_sides;

        # Degree converted to radians
        apothem = a / (2 * math.tan((180 / n) *
                                    math.pi / 180));

        true_width = PIXEL_RATIO;
        true_height = apothem * 2;

        width = self._width;
        height = self._height;

        scale_factor = (width / true_width, height / true_height);

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape];

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy);

            vertex.move(self.x() + width / 2, self.y() + height / 2);
            vertex.move(dy=PIXEL_RATIO - true_height);

        self._vertices = vertices;

        self._vertices = self._rotate(self._vertices, self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in self._vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        color_state = self._color if self._fill else Color.NONE;

        try:
            # noinspection PyProtectedMember
            self._ref = self._screen._canvas.create_polygon(
                tk_vertices,
                fill=self._screen._colorstr(color_state),
                outline=self._screen._screen._colorstr(self._border.__value__()),
                width=self._borderwidth,
                state=state,
                joinstyle=tk.MITER
            );

            self._screen._canvas.tag_lower(self._ref, old_ref);
            self._screen._canvas.delete(old_ref);
        except:
            pass;


class Image(Renderable):
    """
    Image class. Supports basic formats: PNG, GIF, JPG, PPM, images.

    NOTE: This class supports the basic displaying of images, but also supports much more,
    such as image modification (width, height, color, etc) if you have PIL (Pillow) installed!
    You can install PIL/Pillow by running: `pip install pillow` in a terminal!
    """

    TKINTER_TYPES = ['.png', '.gif', '.ppm'];

    # (x, y) INITIALIZERS

    @overload(Screen, str, (int, float), (int, float))
    def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._image_name = image;
        self._original = None;

        # Filetype Checking
        split = image.split('.');
        if len(split) <= 1:
            raise PydrawError('File must have extension filetype:', self._image_name);

        filetype = split[len(split) - 1]

        import os;
        if not os.path.isfile(image):
            raise InvalidArgumentError(f'Image does not exist or is directory: {image}');

        if filetype in self.TKINTER_TYPES:
            self._image = tk.PhotoImage(name=image, file=image);
        else:
            try:
                from PIL import Image, ImageTk;
                image = Image.open(self._image_name);
                self._original = image;  # We save the originally loaded image for easy modification

                self._image = ImageTk.PhotoImage(image);
            except:
                raise UnsupportedError('As PIL is not installed, only .png, .gif, and .ppm images are supported! '
                                       'Install Pillow via: \'pip install pillow\'.');

        self._width = self._image.width();
        self._height = self._image.height();

        self._frame = -1;
        self._frames = -1;

        self._mask = 123;

        # We have to monkey patch PIL if we modify the image, but we don't wanna cause a RecursionError (call once)
        self._patched = False;

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible);
        self._setup()

        if width is not None:
            self.width(width);
        if height is not None:
            self.height(height);

        if color is not None:
            self.color(color);

        if border is not None:
            self.border(border);

    @overload(Screen, str, (int, float), (int, float), (int, float), (int, float))
    def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._image_name = image;
        self._original = None;

        # Filetype Checking
        split = image.split('.');
        if len(split) <= 1:
            raise PydrawError('File must have extension filetype:', self._image_name);

        filetype = split[len(split) - 1]

        import os;
        if not os.path.isfile(image):
            raise InvalidArgumentError(f'Image does not exist or is directory: {image}');

        if filetype in self.TKINTER_TYPES:
            self._image = tk.PhotoImage(name=image, file=image);
        else:
            try:
                from PIL import Image, ImageTk;
                image = Image.open(self._image_name);
                self._original = image;  # We save the originally loaded image for easy modification

                self._image = ImageTk.PhotoImage(image);
            except:
                raise UnsupportedError('As PIL is not installed, only .png, .gif, and .ppm images are supported! '
                                       'Install Pillow via: \'pip install pillow\'.');

        self._width = self._image.width();
        self._height = self._image.height();

        self._frame = -1;
        self._frames = -1;

        self._mask = 123;

        # We have to monkey patch PIL if we modify the image, but we don't wanna cause a RecursionError (call once)
        self._patched = False;

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible);
        self._setup()

        if width is not None:
            self.width(width);
        if height is not None:
            self.height(height);

        if color is not None:
            self.color(color);

        if border is not None:
            self.border(border);

    @overload(Screen, str, (int, float), (int, float), (int, float), (int, float), Color)
    def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._image_name = image;
        self._original = None;

        # Filetype Checking
        split = image.split('.');
        if len(split) <= 1:
            raise PydrawError('File must have extension filetype:', self._image_name);

        filetype = split[len(split) - 1]

        import os;
        if not os.path.isfile(image):
            raise InvalidArgumentError(f'Image does not exist or is directory: {image}');

        if filetype in self.TKINTER_TYPES:
            self._image = tk.PhotoImage(name=image, file=image);
        else:
            try:
                from PIL import Image, ImageTk;
                image = Image.open(self._image_name);
                self._original = image;  # We save the originally loaded image for easy modification

                self._image = ImageTk.PhotoImage(image);
            except:
                raise UnsupportedError('As PIL is not installed, only .png, .gif, and .ppm images are supported! '
                                       'Install Pillow via: \'pip install pillow\'.');

        self._width = self._image.width();
        self._height = self._image.height();

        self._frame = -1;
        self._frames = -1;

        self._mask = 123;

        # We have to monkey patch PIL if we modify the image, but we don't wanna cause a RecursionError (call once)
        self._patched = False;

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible);
        self._setup()

        if width is not None:
            self.width(width);
        if height is not None:
            self.height(height);

        if color is not None:
            self.color(color);

        if border is not None:
            self.border(border);

    # Location INITIALIZERS

    @overload(Screen, str, Location)
    def __init__(self, screen: Screen, image: str, location: Location,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._image_name = image;
        self._original = None;

        x = location.x();
        y = location.y();

        # Filetype Checking
        split = image.split('.');
        if len(split) <= 1:
            raise PydrawError('File must have extension filetype:', self._image_name);

        filetype = split[len(split) - 1]

        import os;
        if not os.path.isfile(image):
            raise InvalidArgumentError(f'Image does not exist or is directory: {image}');

        if filetype in self.TKINTER_TYPES:
            self._image = tk.PhotoImage(name=image, file=image);
        else:
            try:
                from PIL import Image, ImageTk;
                image = Image.open(self._image_name);
                self._original = image;  # We save the originally loaded image for easy modification

                self._image = ImageTk.PhotoImage(image);
            except:
                raise UnsupportedError('As PIL is not installed, only .png, .gif, and .ppm images are supported! '
                                       'Install Pillow via: \'pip install pillow\'.');

        self._width = self._image.width();
        self._height = self._image.height();

        self._frame = -1;
        self._frames = -1;

        self._mask = 123;

        # We have to monkey patch PIL if we modify the image, but we don't wanna cause a RecursionError (call once)
        self._patched = False;

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible);
        self._setup()

        if width is not None:
            self.width(width);
        if height is not None:
            self.height(height);

        if color is not None:
            self.color(color);

        if border is not None:
            self.border(border);

    @overload(Screen, str, Location, (int, float), (int, float))
    def __init__(self, screen: Screen, image: str, location: Location,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._image_name = image;
        self._original = None;

        x = location.x();
        y = location.y();

        # Filetype Checking
        split = image.split('.');
        if len(split) <= 1:
            raise PydrawError('File must have extension filetype:', self._image_name);

        filetype = split[len(split) - 1]

        import os;
        if not os.path.isfile(image):
            raise InvalidArgumentError(f'Image does not exist or is directory: {image}');

        if filetype in self.TKINTER_TYPES:
            self._image = tk.PhotoImage(name=image, file=image);
        else:
            try:
                from PIL import Image, ImageTk;
                image = Image.open(self._image_name);
                self._original = image;  # We save the originally loaded image for easy modification

                self._image = ImageTk.PhotoImage(image);
            except:
                raise UnsupportedError('As PIL is not installed, only .png, .gif, and .ppm images are supported! '
                                       'Install Pillow via: \'pip install pillow\'.');

        self._width = self._image.width();
        self._height = self._image.height();

        self._frame = -1;
        self._frames = -1;

        self._mask = 123;

        # We have to monkey patch PIL if we modify the image, but we don't wanna cause a RecursionError (call once)
        self._patched = False;

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible);
        self._setup()

        if width is not None:
            self.width(width);
        if height is not None:
            self.height(height);

        if color is not None:
            self.color(color);

        if border is not None:
            self.border(border);

    @overload(Screen, str, Location, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, image: str, location: Location,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._image_name = image;
        self._original = None;

        x = location.x();
        y = location.y();

        # Filetype Checking
        split = image.split('.');
        if len(split) <= 1:
            raise PydrawError('File must have extension filetype:', self._image_name);

        filetype = split[len(split) - 1]

        import os;
        if not os.path.isfile(image):
            raise InvalidArgumentError(f'Image does not exist or is directory: {image}');

        if filetype in self.TKINTER_TYPES:
            self._image = tk.PhotoImage(name=image, file=image);
        else:
            try:
                from PIL import Image, ImageTk;
                image = Image.open(self._image_name);
                self._original = image;  # We save the originally loaded image for easy modification

                self._image = ImageTk.PhotoImage(image);
            except:
                raise UnsupportedError('As PIL is not installed, only .png, .gif, and .ppm images are supported! '
                                       'Install Pillow via: \'pip install pillow\'.');

        self._width = self._image.width();
        self._height = self._image.height();

        self._frame = -1;
        self._frames = -1;

        self._mask = 123;

        # We have to monkey patch PIL if we modify the image, but we don't wanna cause a RecursionError (call once)
        self._patched = False;

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible);
        self._setup()

        if width is not None:
            self.width(width);
        if height is not None:
            self.height(height);

        if color is not None:
            self.color(color);

        if border is not None:
            self.border(border);

    # noinspection PyProtectedMember
    def _setup(self):
        # Pre-register the vertices so we don't have issues with .center()
        self._vertices = self.vertices();

        real_location = self._screen.canvas_location(self.x(), self.y());
        self._ref = self._screen._canvas.create_image(real_location.x() + self._width / 2,
                                                      real_location.y() + self._height / 2, image=self._image);

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the image (REQUIRES: PIL or Pillow)
        :param width: the width to set to, if any
        :return: None
        """

        if width is not None:
            verify(width, (float, int));
            self._width = width;
            self.update(True);

        return self._width;

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the image
        :param height: the height to set to, if any
        :return: the height
        """

        if height is not None:
            verify(height, (float, int));
            self._height = height;
            self.update(True);

        return self._height;

    def color(self, color: Color = None, alpha: int = 123) -> Color:
        """
        Retrieves or applies a color-mask to the image
        :param color: the color to mask to, if any
        :param alpha: The alpha level of the mask, defaults to 123 (half of 255)
        :return: the mask-color of the object
        """

        if color is not None:
            verify(color, Color);
            self._color = color;
            self._mask = alpha;
            self.update(True);

        return self._color;

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the image.
        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the image's rotation in degrees
        """

        if angle is not None:
            verify(angle, (float, int));
            self._angle = angle;
            self.update(True);

        return self._angle;

    # noinspection PyMethodOverriding
    def rotate(self, angle_diff: float) -> None:
        """
        Rotate the angle of the image by a difference, in degrees
        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        if angle_diff != 0:
            verify(angle_diff, (float, int));
            self._angle += angle_diff;
            self.update(True);

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center
        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Image
        """

        if len(args) == 0 and len(kwargs) == 0:
            return self._center();

        location = Location(self._center())
        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0]);
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError(".center() requires both x and y passed unless using keywords.");
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

                location.moveto(args[0], args[1]);
            else:
                raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        return self._center(location);

    def _center(self, moveto: Location = None) -> Location:
        if moveto is not None:
            verify(moveto, Location);
            self.moveto(moveto.x() - self.width() / 2, moveto.y() - self.height() / 2);

        return Location(self.x() + self.width() / 2, self.y() + self.height() / 2);

    # noinspection PyMethodOverriding
    def border(self, color: Color = None) -> Color:
        """
        Add or get the border of the image
        :param color: the color to set the border too, set to Color.NONE to remove border
        :return: The Color of the border
        """

        if color is not None:
            verify(color, Color);
            self._border = color;
            self.update(True);

        return self._border;

    def fill(self, fill: bool = None) -> bool:
        """
        Unsupported: This doesn't make sense for images.
        """

        raise UnsupportedError('This method is not supported for Images!');

    def vertices(self) -> list:
        """
        Returns the list of vertices for the Renderable.
        (The vertices will be returned clockwise, starting from the top-leftmost point)
        :return: a list of Locations representing the vertices
        """

        vertices = [self.location(), Location(self.x() + self.width(), self.y()),
                    Location(self.x() + self.width(), self.y() + self.height()),
                    Location(self.x(), self.y() + self.height())];

        if self._angle != 0:

            # First get some values that we gonna use later
            theta = math.radians(self._angle);
            cosine = math.cos(theta);
            sine = math.sin(theta);

            center_x = self.x() + self.width() / 2;
            center_y = self.y() + self.width() / 2;

            new_vertices = []
            for vertex in vertices:
                # We have to create these separately because they're ironically used in each others calculations xD
                old_x = vertex.x() - center_x;
                old_y = vertex.y() - center_y;

                new_x = (old_x * cosine - old_y * sine) + center_x;
                new_y = (old_x * sine + old_y * cosine) + center_y;
                new_vertices.append(Location(new_x, new_y));

            vertices = new_vertices;

        return vertices;

    def flip(self, axis: str = 'y'):
        # TODO: Finish this noah
        pass;

    def load(self) -> None:
        """
        Load animated GIF (reads frames)
        :return: None
        """

        from PIL import Image;
        from PIL import GifImagePlugin;

        image = Image.open(self._image_name);
        if hasattr(image, 'n_frames'):
            self._frames = image.n_frames;
            self._frame = 0;
        else:
            raise PydrawError('GIF is not animated, so it cannot be loaded!');

    def next(self) -> None:
        """
        Changes frame to the next frame (Can only be used with animated GIFs)
        :return:
        """
        self._frame += 1;

        if self._frame >= self._frames:
            self._frame = 0;

        self.update(True);

    def frame(self, frame: int = None) -> int:
        """
        Set the current frame.
        :param frame: the frame-index to set to
        :return: the current frame
        """

        if frame is not None:
            self._frame = frame;
            self.update(True);

        return self._frame;

    def frames(self) -> int:
        """
        Returns how many frames there are, returns -1 if not animated, 0 if corrupted file.
        :return:
        """

        return self._frames;

    @staticmethod
    def _monkey_patch_del():
        """
        We monkey patch the del function for PIL so it doesn't do stupid things.
        :return:
        """
        from PIL import ImageTk;

        # monkey patch TKinter from this dumb bug they don't catch in TK.PhotoImage
        old_del = ImageTk.PhotoImage.__del__;

        def new_del(self):
            try:
                old_del(self)
            except (AttributeError, RecursionError):
                pass;  # Yeah, we don't care.
            pass;

        ImageTk.PhotoImage.__del__ = new_del

    # noinspection PyProtectedMember
    def update(self, updated: bool = False):
        self._check();

        if updated:
            try:
                from PIL import Image, ImageTk, ImageOps;

                if not self._patched:
                    self._monkey_patch_del();  # If we do have PIL we need to monkey patch this immediately.
                    self._patched = True;

                # Optimized (only read file once, caching everything else)
                # TODO: In the future, caching images by filename could increase efficiency, but have serious pitfalls.
                # ^ Perhaps if we hash the image we could then compare against future hashes to check if the file
                # has been modified or not. (Noah)
                if self._original is not None:
                    image = self._original.copy();
                else:
                    image = Image.open(self._image_name);
                    self._original = image.copy();

                if self._frame != -1:
                    try:
                        self._original.seek(self._frame);  # we have to seek on original for some reason.
                    except EOFError:
                        raise PydrawError(f'No more frames in GIF: {self._image_name}!');

                image = image.convert('RGBA');  # Convert so we can color-filter the image

                if self._color is not None and self._color != Color.NONE:
                    r, g, b, alpha = image.split()
                    gray = ImageOps.grayscale(image)
                    result = ImageOps.colorize(gray, (0, 0, 0, 0),
                                               (
                                                   self._color.red(), self._color.green(), self._color.blue(),
                                                   self._mask));
                    result.putalpha(alpha);
                    image = result;

                if self._border is not None and self._border is not Color.NONE:
                    image = ImageOps.expand(image, border=10, fill=self._border.rgb())

                # Do resizing last so we can make sure the other manipulations work properly
                image = image.resize((int(self.width()), int(self.height())), Image.ANTIALIAS);

                if self._angle != 0:
                    image = image.rotate(-self._angle, resample=Image.BILINEAR, expand=1, fillcolor=None)

                self._image = ImageTk.PhotoImage(image=image);
            except (RuntimeError, AttributeError) as e:
                pass;  # We are catching some stupid errors from Tkinter involving images and program exiting.
            except ImportError:
                raise UnsupportedError('As PIL is not installed, you cannot modify images! '
                                       'Install Pillow via: \'pip install pillow\'.');

        try:
            old_ref = self._ref;
            real_location = self._screen.canvas_location(self.x(), self.y());

            state = tk.NORMAL if self._visible else tk.HIDDEN;

            self._ref = self._screen._canvas.create_image(real_location.x() + self._width / 2,
                                                          real_location.y() + self._height / 2, image=self._image,
                                                          state=state);

            self._screen._canvas.tag_lower(self._ref, old_ref);
            self._screen._canvas.delete(old_ref);
        except tk.TclError:
            pass;


class Text(CustomRenderable):
    _anchor = 'nw';  # sw technically means southwest but it means bottom left anchor. (we change to top left in code)
    _aligns = {'left': tk.LEFT, 'center': tk.CENTER, 'right': tk.RIGHT};

    # noinspection PyProtectedMember
    @overload(Screen, str, (int, float), (int, float))
    def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        self._screen = screen;
        self._location = Location(x, y);
        self._screen._add(self);

        self._text = text if text is not None else '';
        self._color = color;
        self._font = font;
        self._size = size;
        self._align = align;
        self._bold = bold;
        self._italic = italic;
        self._underline = underline;
        self._strikethrough = strikethrough;
        self._angle = rotation;
        self._visible = visible;

        verify(screen, Screen, text, str, x, (float, int), y, (float, int), color, Color, font, str, size, int,
               align, str, bold, bool, italic, bool, underline, bool, strikethrough, bool, rotation, (float, int),
               visible, bool);

        # Handle font and decorations
        decorations = '';
        if self.bold():
            decorations += 'bold ';
        if self.italic():
            decorations += 'italic ';
        if self.underline():
            decorations += 'underline ';
        if self.strikethrough():
            decorations += 'overstrike ';

        # we use negative font size to change from point font-size to pixel font-size.
        font_data = (self.font(), -self.size(), decorations);

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        # import tkinter.font as tkfont;
        #
        # font = tkfont.Font(font=font_data);
        # true_width = font.measure(self._text);
        # true_height = font.metrics('linespace');

        true_width, true_height = self._calculate_transform(font_data);

        hypotenuse = true_width / 2;
        radians = math.radians(self._angle);

        dx = math.cos(radians) * hypotenuse;
        dy = math.sin(radians) * hypotenuse;

        real_x = (self.x() + (true_width / 2) - ((self._screen.width() / 2) + 1)) - dx;
        real_y = (self.y() - (self._screen.height() / 2)) - dy;

        self._ref = self._screen._screen.cv.create_text(real_x,
                                                        real_y,
                                                        text=self.text(),
                                                        anchor=Text._anchor,
                                                        justify=Text._aligns[self.align()],
                                                        fill=self._screen._screen._colorstr(self.color().__value__()),
                                                        font=font_data,
                                                        state=state,
                                                        angle=-self._angle);

        # x0, y0, x1, y1 = screen._screen.cv.bbox(self._ref);
        # self._width = x1 - x0;
        # self._height = y1 - y0;

        self._width = true_width;
        self._height = true_height * (self._text.count('\n') + 1);

    @overload(Screen, str, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        self._screen = screen;
        self._location = Location(x, y);
        self._screen._add(self);

        self._text = text if text is not None else '';
        self._color = color;
        self._font = font;
        self._size = size;
        self._align = align;
        self._bold = bold;
        self._italic = italic;
        self._underline = underline;
        self._strikethrough = strikethrough;
        self._angle = rotation;
        self._visible = visible;

        verify(screen, Screen, text, str, x, (float, int), y, (float, int), color, Color, font, str, size, int,
               align, str, bold, bool, italic, bool, underline, bool, strikethrough, bool, rotation, (float, int),
               visible, bool);

        # Handle font and decorations
        decorations = '';
        if self.bold():
            decorations += 'bold ';
        if self.italic():
            decorations += 'italic ';
        if self.underline():
            decorations += 'underline ';
        if self.strikethrough():
            decorations += 'overstrike ';

        # we use negative font size to change from point font-size to pixel font-size.
        font_data = (self.font(), -self.size(), decorations);

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        # import tkinter.font as tkfont;
        #
        # font = tkfont.Font(font=font_data);
        # true_width = font.measure(self._text);
        # true_height = font.metrics('linespace');

        true_width, true_height = self._calculate_transform(font_data);

        hypotenuse = true_width / 2;
        radians = math.radians(self._angle);

        dx = math.cos(radians) * hypotenuse;
        dy = math.sin(radians) * hypotenuse;

        real_x = (self.x() + (true_width / 2) - ((self._screen.width() / 2) + 1)) - dx;
        real_y = (self.y() - (self._screen.height() / 2)) - dy;

        self._ref = self._screen._screen.cv.create_text(real_x,
                                                        real_y,
                                                        text=self.text(),
                                                        anchor=Text._anchor,
                                                        justify=Text._aligns[self.align()],
                                                        fill=self._screen._screen._colorstr(self.color().__value__()),
                                                        font=font_data,
                                                        state=state,
                                                        angle=-self._angle);

        # x0, y0, x1, y1 = screen._screen.cv.bbox(self._ref);
        # self._width = x1 - x0;
        # self._height = y1 - y0;

        self._width = true_width;
        self._height = true_height * (self._text.count('\n') + 1);

    @overload(Screen, str, Location)
    def __init__(self, screen: Screen, text: str, location: Location, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        x = location.x();
        y = location.y();

        self._screen = screen;
        self._location = Location(x, y);
        self._screen._add(self);

        self._text = text if text is not None else '';
        self._color = color;
        self._font = font;
        self._size = size;
        self._align = align;
        self._bold = bold;
        self._italic = italic;
        self._underline = underline;
        self._strikethrough = strikethrough;
        self._angle = rotation;
        self._visible = visible;

        verify(screen, Screen, text, str, x, (float, int), y, (float, int), color, Color, font, str, size, int,
               align, str, bold, bool, italic, bool, underline, bool, strikethrough, bool, rotation, (float, int),
               visible, bool);

        # Handle font and decorations
        decorations = '';
        if self.bold():
            decorations += 'bold ';
        if self.italic():
            decorations += 'italic ';
        if self.underline():
            decorations += 'underline ';
        if self.strikethrough():
            decorations += 'overstrike ';

        # we use negative font size to change from point font-size to pixel font-size.
        font_data = (self.font(), -self.size(), decorations);

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        # import tkinter.font as tkfont;
        #
        # font = tkfont.Font(font=font_data);
        # true_width = font.measure(self._text);
        # true_height = font.metrics('linespace');

        true_width, true_height = self._calculate_transform(font_data);

        hypotenuse = true_width / 2;
        radians = math.radians(self._angle);

        dx = math.cos(radians) * hypotenuse;
        dy = math.sin(radians) * hypotenuse;

        real_x = (self.x() + (true_width / 2) - ((self._screen.width() / 2) + 1)) - dx;
        real_y = (self.y() - (self._screen.height() / 2)) - dy;

        self._ref = self._screen._screen.cv.create_text(real_x,
                                                        real_y,
                                                        text=self.text(),
                                                        anchor=Text._anchor,
                                                        justify=Text._aligns[self.align()],
                                                        fill=self._screen._screen._colorstr(self.color().__value__()),
                                                        font=font_data,
                                                        state=state,
                                                        angle=-self._angle);

        # x0, y0, x1, y1 = screen._screen.cv.bbox(self._ref);
        # self._width = x1 - x0;
        # self._height = y1 - y0;

        self._width = true_width;
        self._height = true_height * (self._text.count('\n') + 1);

    @overload(Screen, str, Location, Color)
    def __init__(self, screen: Screen, text: str, location: Location, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        x = location.x();
        y = location.y();

        self._screen = screen;
        self._location = Location(x, y);
        self._screen._add(self);

        self._text = text if text is not None else '';
        self._color = color;
        self._font = font;
        self._size = size;
        self._align = align;
        self._bold = bold;
        self._italic = italic;
        self._underline = underline;
        self._strikethrough = strikethrough;
        self._angle = rotation;
        self._visible = visible;

        verify(screen, Screen, text, str, x, (float, int), y, (float, int), color, Color, font, str, size, int,
               align, str, bold, bool, italic, bool, underline, bool, strikethrough, bool, rotation, (float, int),
               visible, bool);

        # Handle font and decorations
        decorations = '';
        if self.bold():
            decorations += 'bold ';
        if self.italic():
            decorations += 'italic ';
        if self.underline():
            decorations += 'underline ';
        if self.strikethrough():
            decorations += 'overstrike ';

        # we use negative font size to change from point font-size to pixel font-size.
        font_data = (self.font(), -self.size(), decorations);

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        # import tkinter.font as tkfont;
        #
        # font = tkfont.Font(font=font_data);
        # true_width = font.measure(self._text);
        # true_height = font.metrics('linespace');

        true_width, true_height = self._calculate_transform(font_data);

        hypotenuse = true_width / 2;
        radians = math.radians(self._angle);

        dx = math.cos(radians) * hypotenuse;
        dy = math.sin(radians) * hypotenuse;

        real_x = (self.x() + (true_width / 2) - ((self._screen.width() / 2) + 1)) - dx;
        real_y = (self.y() - (self._screen.height() / 2)) - dy;

        self._ref = self._screen._screen.cv.create_text(real_x,
                                                        real_y,
                                                        text=self.text(),
                                                        anchor=Text._anchor,
                                                        justify=Text._aligns[self.align()],
                                                        fill=self._screen._screen._colorstr(self.color().__value__()),
                                                        font=font_data,
                                                        state=state,
                                                        angle=-self._angle);

        # x0, y0, x1, y1 = screen._screen.cv.bbox(self._ref);
        # self._width = x1 - x0;
        # self._height = y1 - y0;

        self._width = true_width;
        self._height = true_height * (self._text.count('\n') + 1);

    def text(self, text: str = None) -> str:
        """
        Get or set the text. Use '\n' to separate lines
        :param text: text to set to (str), if any
        :return: the text
        """

        if text is not None:
            verify(text, str);
            self._text = text;
            self.update();

        return self._text;

    # noinspection PyMethodOverriding
    def width(self) -> float:
        """
        Get the width of the text (cannot be modified)
        :return the width of the text
        """

        return self._width;

    # noinspection PyMethodOverriding
    def height(self) -> float:
        """
        Get the height of the text, (cannot be modified, although technically the font-size is the text's height)
        :return: the height of the text.
        """

        return self._height;

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the text
        :param color: the color to set to, if any
        :return: the color of the text
        """

        if color is not None:
            verify(color, Color);
            self._color = color;
            self.update();

        return self._color;

    def font(self, font: str = None) -> str:
        """
        Get or set the font of the text
        :param font: the font to set to, if any
        :return: the font of the text
        """

        if font is not None:
            verify(font, str);
            self._font = font;
            self.update();

        return self._font;

    def size(self, size: int = None) -> int:
        """
        Get or set the size of the text
        :param size: the size to set to, if any
        :return: the size of the text
        """

        if size is not None:
            verify(size, int);
            self._size = size;
            self.update();

        return self._size;

    def align(self, align: str = None) -> str:
        """
        Get or set the alignment of the text, if a new value is passed it must be 'left', 'center', or 'right'.
        :param align: the alignment to set to, if any
        :return: the alignment of the text
        """

        if align is not None:
            verify(align, str);
            self._align = align.lower();
            self.update();

        return self._align;

    def bold(self, bold: bool = None) -> bool:
        """
        Get or set the bold status of the text
        :param bold: the bold status to set to, if any
        :return: the bold status of the text
        """

        if bold is not None:
            verify(bold, bool);
            self._bold = bold;
            self.update();

        return self._bold;

    def italic(self, italic: bool = None) -> bool:
        """
        Get or set the italic status of the text
        :param italic: the italic status to set to, if any
        :return: the italic status of the text
        """

        if italic is not None:
            verify(italic, bool);
            self._italic = italic;
            self.update();

        return self._italic;

    def underline(self, underline: bool = None) -> bool:
        """
        Get or set the underline status of the text
        :param underline: the underline status to set to, if any
        :return: the underline status of the text
        """

        if underline is not None:
            verify(underline, bool);
            self._underline = underline;
            self.update();

        return self._underline;

    def strikethrough(self, strikethrough: bool = None) -> bool:
        """
        Get or set the strikethrough status of the text
        :param strikethrough: the strikethrough status to set to, if any
        :return: the strikethrough status of the text
        """

        if strikethrough is not None:
            verify(strikethrough, bool);
            self._strikethrough = strikethrough;
            self.update();

        return self._strikethrough;

    def rotation(self, rotation: float = None) -> float:
        """
        Get or set the rotation of the text
        :param rotation: the strikethrough to set to, if any
        :return: the rotation of the text
        """

        if rotation is not None:
            verify(rotation, (float, int));
            self._angle = rotation;
            self.update();

        return self._angle;

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the text by a difference, in degrees
        :param angle_diff: the angle difference to rotate by
        :return: Nonea
        """

        verify(angle_diff, (float, int));
        self.rotation(self._angle + angle_diff);

    def lookat(self, obj):
        if isinstance(obj, Object):
            obj = obj.location();
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError('Text#lookat() must be passed either a renderable or a location!')

        location = Location(obj[0], obj[1]);

        theta = math.atan2(location.y() - self.center().y(), location.x() - self.center().x()) - math.radians(self.rotation());
        theta = math.degrees(theta) + 90;

        self.rotate(theta);

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center
        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Renderable
        """

        if len(args) == 0 and len(kwargs) == 0:
            return self._center();

        location = Location(self._center())
        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0]);
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError(".center() requires both x and y passed unless using keywords.");
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

                location.moveto(args[0], args[1]);
            else:
                raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y']);
                else:
                    raise InvalidArgumentError(".center() requires either a Location/tuple or two numbers!");

        return self._center(location);

    def _center(self, move_to: Location = None):
        if move_to is not None:
            verify(move_to, Location);
            self.moveto(move_to.x() - self.width() / 2, move_to.y() - self.height() / 2);

        return Location(self.x() + self.width() / 2, self.y() + self.height() / 2);

    def vertices(self) -> list:
        """
        Get the vertices of a Rectangle superposed in the same transform of the Text
        :return: a list of Locations
        """

        # First get some values that we gonna use later
        theta = math.radians(self._angle);
        cosine = math.cos(theta);
        sine = math.sin(theta);

        centroid_x = self.center().x();
        centroid_y = self.center().y();

        vertices = [Location(self.x(), self.y()), Location(self.x() + self.width(), self.y()),
                    Location(self.x() + self.width(), self.y() + self.height()),
                    Location(self.x(), self.y() + self.height())];

        new_vertices = []
        for vertex in vertices:
            # We have to create these separately because they're ironically used in each others calculations xD
            old_x = vertex.x() - centroid_x;
            old_y = vertex.y() - centroid_y;

            new_x = (old_x * cosine - old_y * sine) + centroid_x;
            new_y = (old_x * sine + old_y * cosine) + centroid_y;
            new_vertices.append(Location(new_x, new_y));

        if self._angle != 0:
            vertices = new_vertices;

        return vertices;

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the text
        :param visible: the visibility to set to, if any
        :return: the visibility of the text
        """

        if visible is not None:
            verify(visible, bool);
            self._visible = visible;
            self.update();

        return self._visible;

    def transform(self, transform: tuple = None) -> tuple:
        """
        Retrieve the transform of the text
        :param transform: Unsupported.
        :return: a tuple with representing: (width, height, angle)
        """

        if transform is not None:
            raise UnsupportedError('This feature has yet to be implemented for Text');

        return self.width(), self.height(), self.rotation();

    def clone(self):
        """
        Clone this text!
        :return: A cloned text object!
        """

        return Text(self._screen, self._text, self.x(), self.y(), color=self._color, font=self._font, size=self._size,
                    align=self._align, bold=self._bold, italic=self._italic,
                    underline=self._underline, strikethrough=self._strikethrough,
                    rotation=self._angle, visible=self._visible);

    # noinspection PyProtectedMember
    def update(self) -> None:
        self._check();
        # super().update(); | JUST FOR RENDERABLES - DO NOT USE
        # we are going to delete and re-add text to the screen. You cannot alter a text object.
        old_ref = self._ref;

        # Handle font and decorations
        decorations = '';
        if self.bold():
            decorations += 'bold ';
        if self.italic():
            decorations += 'italic ';
        if self.underline():
            decorations += 'underline ';
        if self.strikethrough():
            decorations += 'overstrike ';

        # we use negative font size to change from point font-size to pixel font-size.
        font_data = (self.font(), -self.size(), decorations);

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        try:
            # import tkinter.font as tkfont;
            #
            # font = tkfont.Font(font=font_data);
            # true_width = font.measure(self._text);
            # true_height = font.metrics('linespace');

            try:
                true_width, true_height = self._calculate_transform(font_data);
            except RuntimeError:
                return

            hypotenuse = true_width / 2;
            radians = math.radians(self._angle);

            dx = math.cos(radians) * hypotenuse;
            dy = math.sin(radians) * hypotenuse;

            real_x = (self.x() + (true_width / 2) - ((self._screen.width() / 2) + 1)) - dx;
            real_y = (self.y() - (self._screen.height() / 2)) - dy;

            self._ref = self._screen._screen.cv.create_text(real_x,
                                                            real_y,
                                                            text=self.text(),
                                                            anchor=Text._anchor,
                                                            justify=Text._aligns[self.align()],
                                                            fill=self._screen._colorstr(self._color),
                                                            font=font_data,
                                                            state=state,
                                                            angle=-self._angle);
            self._screen._screen.cv.tag_lower(self._ref, old_ref);
            self._screen._screen.cv.delete(old_ref);

            self._width = true_width;
            self._height = true_height * (self._text.count('\n') + 1);
        except (tk.TclError, AttributeError):
            pass;

    def _calculate_transform(self, font_data):
        import tkinter.font as tkfont;
        lines = self._text.split('\n');
        true_width = 0;

        font = tkfont.Font(font=font_data);
        for line in lines:
            true_width = max(font.measure(line), true_width);
        true_height = font.metrics('linespace');

        return true_width, true_height;

# == NON RENDERABLES == #


class Line(Object):
    def __init__(self, screen: Screen, *args, color: Color = Color('black'), thickness: int = 1, dashes=None,
                 visible: bool = True):
        super().__init__(screen);
        self._screen = screen;

        if len(args) >= 2:
            if len(args) >= 4 and [type(arg) is float or type(arg) is int for arg in args[0:4]]:
                self._pos1 = Location(args[0], args[1]);
                self._pos2 = Location(args[2], args[3]);
                excess = args[4:];
            elif [type(arg) is tuple or type(arg) is Location for arg in args[0:2]]:
                self._pos1 = Location(args[0][0], args[0][1]);
                self._pos2 = Location(args[1][0], args[1][1]);
                excess = args[2:];
        else:
            raise InvalidArgumentError(
                'Incorrect Argumentation: Line requires either two Locations, tuples, or four '
                'numbers (x1, y1, x2, y2).');

        if len(excess) > 0:  # noqa
            count = 0;
            for arg in excess:
                if count == 0:
                    verify(arg, Color);
                    color = arg;
                elif count == 1:
                    verify(arg, int);
                    thickness = arg;
                elif count == 2:
                    verify(arg, (int, tuple));
                    dashes = arg;
                elif count == 3:
                    verify(arg, bool);
                    visible = arg;
                count += 1;

        self._color = color
        self._thickness = thickness;
        self._dashes = dashes;
        self._visible = visible;

        verify(color, Color, thickness, int, dashes, (int, tuple), visible, bool);

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        if dashes is not None and type(dashes) is not tuple:
            self._dashes = (dashes, dashes)

        # noinspection PyProtectedMember
        self._ref = self._screen._screen.cv.create_line(self._pos1.x() - screen.width() / 2,
                                                        self._pos1.y() - screen.height() / 2,
                                                        self._pos2.x() - screen.width() / 2,
                                                        self._pos2.y() - screen.height() / 2,
                                                        fill=self._screen._screen._colorstr(self._color.__value__()),
                                                        width=self._thickness, dash=self._dashes, state=state);

    def pos1(self, *args) -> Location:
        """
        Get or set the position of the first endpoint.
        :param args: Either a location or two numbers (x, y) may be passed here.
        :return: the position of the first endpoint.
        """

        if len(args) != 0:
            if len(args) == 1 and type(args[0]) is Location or type(args[0]) is tuple:
                self._pos1 = Location(args[0][0], args[0][1]);
            elif len(args) == 2 and [(type(arg) is float or type(arg) is int for arg in args)]:
                self._pos1 = Location(args[0], args[1]);
            else:
                raise TypeError('Incorrect Argumentation: Requires either a location, tuple, or two numbers.');

        self.update();
        return self._pos1;

    def pos2(self, *args) -> Location:
        """
        Get or set the position of the second endpoint.
        :param args: Either a location or two numbers (x, y) may be passed here.
        :return: the position of the second endpoint.
        """

        if len(args) != 0:
            if len(args) == 1 and type(args[0]) is Location or type(args[0]) is tuple:
                self._pos2 = Location(args[0][0], args[0][1]);
                self.update();
            elif len(args) == 2 and (type(arg) is float or type(arg) is int for arg in args):
                self._pos2 = Location(args[0], args[1]);
                self.update();
            else:
                raise TypeError('Incorrect Argumentation: Requires either a location, tuple, or two numbers.');

        self.update();
        return self._pos2;

    def move(self, *args, **kwargs) -> None:
        """
        Move both endpoints by the same dx and dy

        Can take either a tuple, Location, or two numbers (dx, dy)

        :param dx: the distance x to move
        :param dy: the distance y to move
        :param point: affect only one of the endpoints; options: (1, 2), default=0 (Must be 1 or 2)
        :return: None
        """

        diff = (0, 0);

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and type(args[0]) is tuple or type(args[0]) is Location:
                diff = (args[0][0], args[0][1]);
            elif len(args) == 2 and [type(arg) is float or type(arg) is int for arg in args]:
                diff = (args[0], args[1]);
            else:
                raise InvalidArgumentError('Object#move() must take either a tuple/location or two numbers (dx, dy)!');

        for (name, value) in kwargs.items():
            if len(kwargs) == 0 or type(value) is not int and type(value) is not float:
                raise InvalidArgumentError('Object#move() must take either a tuple/location '
                                           'or two numbers (dx, dy)!');

            if name.lower() == 'dx':
                diff = (value, diff[1]);
            if name.lower() == 'dy':
                diff = (diff[0], value);

        if 'point' in kwargs:
            point = kwargs['point'];
            verify(point, int);
            if point == 1:
                self._pos1.move(diff[0], diff[1]);
            elif point == 2:
                self._pos2.move(diff[0], diff[1]);
            elif point != 0:
                raise InvalidArgumentError('You must pass either 1 or 2 in as a point, or 0 for both points!');
        else:
            self._pos1.move(diff[0], diff[1]);
            self._pos2.move(diff[0], diff[1]);

        self.update();

    def moveto(self, *args, **kwargs) -> None:
        """
        Move both of the endpoints to new locations.
        :param args: Either two locations, tuples, or four numbers (x1, y1, x2, y2).
        :return: None
        """

        if len(args) == 2 and (type(arg) is tuple or type(arg) is Location for arg in args):
            self._pos1.moveto(args[0][0], args[0][1]);
            self._pos2.moveto(args[1][0], args[1][1]);
        elif len(args) == 4 and (type(arg) is int or type(arg) is float for arg in args):
            self._pos1.moveto(args[0], args[1]);
            self._pos2.moveto(args[2], args[3]);
        elif len(kwargs) == 0:
            raise TypeError('Incorrect Argumentation: Requires either two locations, tuples, or four numbers (x1, y1, '
                            'x2, y2)');

        if len(kwargs.keys()) > 0:
            for key, value in kwargs.items():
                if key.lower() == 'pos1' and type(value) is tuple or type(value) is Location:
                    pos1 = value;
                    verify(pos1[0], (float, int), pos1[1], (float, int));
                    self._pos1 = Location(pos1[0], pos1[1]);
                elif key.lower() == 'pos2' and type(value) is tuple or type(value) is Location:
                    pos2 = value;
                    verify(pos2[0], (float, int), pos2[1], (float, int));
                    self._pos2 = Location(pos2[0], pos2[1]);
                elif key.lower() == 'x1' and type(value) is float or type(value) is int:
                    self._pos1.x(value);
                elif key.lower() == 'y1' and type(value) is float or type(value) is int:
                    self._pos1.y(value);
                elif key.lower() == 'x2' and type(value) is float or type(value) is int:
                    self._pos2.x(value);
                elif key.lower() == 'y2' and type(value) is float or type(value) is int:
                    self._pos2.y(value);
        elif len(args) == 0:
            raise TypeError('Incorrect Argumentation: Requires either two locations, tuples, or four numbers (x1, y1, '
                            'x2, y2)');

        self.update();

    # noinspection PyUnusedLocal
    # TODO: Allow for point specification.
    def lookat(self, *args, **kwargs) -> None:
        """
        Make the line look at the given point by moving the second point.
        :return: None
        """

        point = 2;

        if len(args) >= 1 and (type(args[0]) is tuple or type(args[0]) is Location):
            location = Location(args[0][0], args[0][1]);

            if len(args) > 1 and type(args[1]) is int:
                point = args[1];
        elif len(args) >= 2 and (type(arg) is float or type(arg) is int for arg in args[:2]):
            location = Location(args[0], args[1]);

            if len(args) > 2 and type(args[2]) is int:
                point = args[2];
        else:
            raise InvalidArgumentError('You must pass either two numbers (x, y), or a tuple/Location!');

        if 'point' in kwargs:
            if type(kwargs['point']) is not int:
                raise InvalidArgumentError('Point must be an int.');

            point = kwargs['point'];

        # so now we have a location but we need to shorten it to be the same length of our line right now.
        # slope = (self.pos2().y() - self.pos1().y()) / (self.pos2.x() - self.pos1.x());
        length = self.length();

        if point == 2:
            ray_length = self._length(self.pos1().x(), location.x(), self.pos1().y(), location.y());

            # hypotenuse = (ray_length - length);  # extraneous length (we need to cut this)

            theta = math.atan2(self.pos1().y() - location.y(), self.pos1().x() - location.x()) \
                    - math.atan2(self.pos1().y() - self.pos2().y(), self.pos1().x() - self.pos2().x());
        elif point == 1:
            ray_length = self._length(self.pos2().x(), location.x(), self.pos2().y(), location.y());

            # hypotenuse = (ray_length - length);  # extraneous length (we need to cut this)

            theta = math.atan2(self.pos2().y() - location.y(), self.pos2().x() - location.x()) \
                    - math.atan2(self.pos2().y() - self.pos1().y(), self.pos2().x() - self.pos1().x());
        else:
            raise InvalidArgumentError('Point is not 1 or 2! (2 by default)');

        self.rotate(math.degrees(theta));

    def rotation(self, angle: float = None):
        """
        Get or set the rotation of the line (works via pos2().
        :param angle: the angle in degrees to rotate by, if any
        :return: the angle of the line
        """

        theta = math.atan2(self.pos1().y() - self.pos2().y(), self.pos1().x() - self.pos2().x());
        theta = math.degrees(theta);
        if angle is not None:
            self.rotate(angle + theta);

        return theta;

    def rotate(self, angle_diff: float, point: int = 1):
        """
        Rotate the line around one of the vertices (1 by default)
        :param angle_diff: the angle to rotate by
        :param point: the point to serve as the origin.
        :return:
        """

        origin = self._pos1 if point == 1 else self._pos2;
        point = self._pos2 if point == 1 else self._pos1;

        theta = math.radians(angle_diff);

        cosine = math.cos(theta);
        sine = math.sin(theta);

        old_x = point.x() - origin.x();
        old_y = point.y() - origin.y();

        new_x = (old_x * cosine - old_y * sine) + origin.x();
        new_y = (old_x * sine + old_y * cosine) + origin.y();

        point.moveto(new_x, new_y);
        self.update();

    def location(self) -> tuple:
        """
        Returns the locations of both the endpoints
        :return: the locations of both the endpoints
        """

        return self._pos1, self._pos2;

    def length(self) -> float:
        """
        Get the length of the line
        :return: the length of the line
        """

        return self._length(self.pos1().x(), self.pos2().x(), self.pos1().y(), self.pos2().y());

    @staticmethod
    def _length(x1: float, x2: float, y1: float, y2: float) -> float:
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the line
        :param color: the color to set to, if any
        :return: the color of the line
        """

        if color is not None:
            verify(color, Color);
            self._color = color;
            self.update();

        return self._color;

    def thickness(self, thickness: int = None) -> int:
        """
        Get or set the thickness of the line
        :param thickness: the thickness to set to, if any
        :return: the thickness of the line
        """

        if thickness is not None:
            verify(thickness, int);
            self._thickness = thickness;
            self.update();

        return self._thickness;

    def dashes(self, dashes: int = None) -> Union[int, tuple]:
        """
        Retrieve or enable/disable the dashes for the line

        On systems which support only a limited set of dash patterns, the dash pattern will be displayed as the closest
        dash pattern that is available. For example, on Windows only a few dash patterns are available, most of which
        do not allow for special dash-spacing (if passing in a tuple).

        :param dashes: the visibility to set to, if any
        :return: the toggle-state of dashes
        """

        if dashes is not None:
            verify(dashes, (int, tuple));

            if type(dashes) == tuple:
                for dash in dashes:
                    verify(dash, int);

            self._dashes = dashes;
            self.update();

        return self._dashes;

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the line
        :param visible: the visibility to set to, if any
        :return: the visibility of the line
        """

        if visible is not None:
            verify(visible, bool);
            self._visible = visible;
            self.update();

        return self._visible;

    def transform(self, transform: tuple = None):
        """
        Copy the line's length and angle!
        :param transform:
        :return:
        """

        if transform is not None:
            raise UnsupportedError('This feature has yet to be implemented!');

        return self.length(), self.rotation();

    def clone(self):
        """
        Clone a new line!
        :return: A clone of this line
        """

        return Line(self._screen, self._pos1, self._pos2, color=self._color, thickness=self._thickness,
                    dashes=self._dashes, visible=self._visible);

    def intersects(self, obj) -> bool:
        """
        Check if a line intersects with another line or Renderable
        :param obj: Line, Renderable, or List/Tuple
        :return: Whether or not the line intersects with the object
        """

        shape1 = (self.pos1(), self.pos2());

        if type(obj) == Line:
            shape2 = (obj.pos1(), obj.pos2());
        elif type(obj) == Renderable:
            shape2 = obj.vertices();
        elif type(obj) == list or type(obj) == tuple:
            shape2 = obj;
        else:
            raise InvalidArgumentError('Line.intersects() accepts only: Lines, Renderables, Lists or Tuples');

        if len(shape2) < 2:
            raise InvalidArgumentError('Passed object did not have more than 1 vertice!');

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
                     (float(point2.x() - point1.x()) * (point3.y() - point2.y()));

            if result > 0:
                return 'clockwise';
            elif result < 0:
                return 'counter-clockwise';
            else:
                return 'co-linear';

        def point_on_segment(point1: Location, point2: Location, point3: Location) -> bool:
            """
            Returns if point3 lies on the segment formed by point1 and point2.
            """

            return max(point1.x(), point3.x()) >= point2.x() >= min(point1.x(), point3.x()) \
                   and max(point1.y(), point3.y()) >= point2.y() >= min(point1.y(), point3.y());

        # Okay to begin actually detecting orientations, we want to loop through some edges. But only ones that are
        # relevant. In order to do this we will first have to turn the list of vertices into a list of edges.
        # Then we will look through the lists of edges and find the ones closest to each other.

        shape1_edges = [];
        shape2_edges = [];

        shape1 = tuple(shape1[:]) + (shape1[0],);
        shape2 = tuple(shape2[:]) + (shape2[0],);

        shape1_point1 = shape1[0];
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)];  # 1, 2, 3, 3 % 5
            shape1_edges.append((shape1_point1, shape1_point2));
            shape1_point1 = shape1_point2;

        shape2_point1 = shape2[0];
        for i in range(1, len(shape2)):
            shape2_point2 = shape2[i % len(shape2)];
            shape2_edges.append((shape2_point1, shape2_point2));
            shape2_point1 = shape2_point2;

        # Now we are going to test the four orientations that the segments form
        for edge1 in shape1_edges:
            for edge2 in shape2_edges:
                orientation1 = orientation(edge1[0], edge1[1], edge2[0]);
                orientation2 = orientation(edge1[0], edge1[1], edge2[1]);
                orientation3 = orientation(edge2[0], edge2[1], edge1[0]);
                orientation4 = orientation(edge2[0], edge2[1], edge1[1]);

                # If orientations 1 and 2 are different as well as 3 and 4 then they intersect!
                if orientation1 != orientation2 and orientation3 != orientation4:
                    return True;

                # There's some special cases we should check where a point from one segment is on the other segment
                if orientation1 == 'co-linear' and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True;

                if orientation2 == 'co-linear' and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True;

                if orientation3 == 'co-linear' and point_on_segment(edge2[0], edge1[0], edge2[1]):
                    return True;

                if orientation4 == 'co-linear' and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True;

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False;

    # noinspection PyProtectedMember
    def update(self):
        self._check();

        try:
            old_ref = self._ref;

            if self._dashes is not None and type(self._dashes) is not tuple:
                self._dashes = (self._dashes, self._dashes)

            state = tk.NORMAL if self._visible else tk.HIDDEN;
            self._ref = self._screen._screen.cv.create_line(self._pos1.x() - self._screen.width() / 2,
                                                            self._pos1.y() - self._screen.height() / 2,
                                                            self._pos2.x() - self._screen.width() / 2,
                                                            self._pos2.y() - self._screen.height() / 2,
                                                            fill=self._screen._colorstr(self.color()),
                                                            width=self._thickness, dash=self._dashes, state=state);

            self._screen._screen.cv.tag_lower(self._ref, old_ref);
            self._screen._screen.cv.delete(old_ref);

            # self._screen._screen.cv.update();
        except tk.TclError:
            pass;  # Just catch TclErrors and throw them out.
