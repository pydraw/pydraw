"""
Objects in the PyDraw library

No hiding spots here (for semicolons)
"""
import turtle;
import tkinter as tk;
import math;

from pydraw import Screen;
from pydraw import Location;
from pydraw import Color;

PIXEL_RATIO = 20;


class Object:
    """
    A base object containing a location and screen. This ensures coordinates are
    done with the root at the top left corner, and not at the center.
    """

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, location: Location = None):
        self._screen = screen;
        self._location = location if location is not None else Location(x, y);

        if isinstance(self, Renderable):
            self._ref = turtle.Turtle();
            self._ref.hideturtle();
            self._ref.penup();

    def x(self, x: float = None) -> float:
        if x is not None:
            self.moveto(x, self.y());

        return self._location.x();

    def y(self, y: float = None) -> float:
        if y is not None:
            self.moveto(self.x(), y);

        return self._location.y();

    def location(self) -> Location:
        return self._location;

    def move(self, dx: float, dy: float) -> None:
        self._location.move(dx, dy);
        self.update();

    def moveto(self, x: float, y: float) -> None:
        self._location.moveto(x, y);
        self.update();

    def _get_real_location(self):
        real_x = self.x() + self.width() / 2 - (self._screen.width() / 2);
        real_y = -self.y() + self._screen.height() / 2 - self.height() / 2;

        return real_x, real_y;

    def update(self) -> None:
        real_x, real_y = self._get_real_location();

        if isinstance(self, Renderable):
            self._ref.goto(real_x, real_y);


class Renderable(Object):
    """
    A base class storing most useful methods for 2D Renderable objects.
    """

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super(Renderable, self).__init__(screen, x, y, location);

        # TODO: check_parameters(x, y, width, height)

        self._width = width;
        self._height = height;

        self._angle = rotation;  # default angle to zero degrees

        self._ref.shape('square');
        self._ref.shapesize(stretch_wid=height / PIXEL_RATIO, stretch_len=width / PIXEL_RATIO);

        self._color = color;
        self._border = border;
        self._ref.color(color.__value__());

        self._fill = fill;
        self._visible = visible;

        if self._visible:
            self._ref.showturtle();
        else:
            self._ref.hideturtle();
        self.update();

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the object.
        :param width: the width to set to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
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
            self._height = height;
            self.update();

        return self._height;

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the object
        :param color: the color to set to, if any
        :return: the color of the object
        """

        if color is not None:
            self._color = color;
            self.update();

        return self._color;

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the object.
        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the object's rotation in degrees
        """

        if angle is not None:
            self._angle = angle;
            self.update();

        return self._angle;

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the object by a difference, in degrees
        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        # TODO: Changed this from '-' to '+' because we don't want to move negatively by default.
        self.rotation(self._angle + angle_diff);

    def border(self, color: Color = None, fill: bool = None) -> Color:
        """
        Add or get the border of the object
        :param color: the color to set the border too, set to None to remove border
        :param fill: whether or not to fill the polygon.
        :return: The Color of the border
        """

        update = False;

        if color is not None:
            self._border = color;
            update = True;
        if fill is not None:
            self._fill = fill;
            update = True;

        if update:
            self.update();

        # TODO: We can create a second object here to act as a "border", or we can see what tkinter has in store...
        return self._border;

    def fill(self, fill: bool = None):
        """
        Returns or sets the current fill boolean
        :param fill: a new fill value, whether or not to fill the polygon
        :return: the fill value
        """

        if fill is not None:
            self._fill = fill;
            self.update();

        return self._fill;

    def distance(self, renderable) -> float:
        """
        Returns the distance between two objects in pixels
        :param renderable: the Renderable to check distance between
        :return: the distance between this object and the passed Renderable.
        """

        return self._ref.distance(renderable.ref) * PIXEL_RATIO;

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the renderable.
        :param visible: the new visibility value, if any
        :return: the visibility value
        """

        if visible is not None:
            self._visible = visible;
            self.update();

        return self._visible;

    def contains(self, *args):
        """
        Returns whether or not a point is contained within the object.
        :param args: You may pass in either two numbers, a Location, or a tuple containing and x and y point.
        :return: a boolean value representing whether or not the point is within the bounds of the object.
        """
        x, y = 0, 0;
        count = 0;

        if len(args) == 1:
            if type(args[0]) is Location:
                x = args[0].x();
                y = args[0].y();
            elif type(args[0]) is tuple and len(args[0]) == 2:
                x = args[0][0];
                y = args[0][1];
        elif len(args) == 2:
            if type(args[0]) is not float and type(args[0]) is not int \
                    and type(args[1]) is not float and type(args[1]) is not int:
                raise NameError('Passed arguments must be numbers (x, y), or you may pass a location/tuple.');
            x = args[0];
            y = args[1];

        # If the point isn't remotely near us, we don't need to perform any calculations.
        if not (self.x() <= x <= (self.x() + self.width()) and self.y() <= y <= (self.y() + self.height())):
            return False;

        # the contains algorithm uses the line-intersects algorithm to determine if a point is within a polygon.
        # we are going to cast a ray from our point to the positive x. (left to right)

        shape = self._get_vertices();
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

    def overlaps(self, renderable) -> bool:
        """
        Returns if this object is overlapping with the passed object.
        :param renderable: another Renderable instance.
        :return: true if they are overlapping, false if not.
        """

        min_ax = self.x();
        max_ax = self.x() + self.width();

        min_bx = renderable.x();
        max_bx = renderable.x() + renderable.width();

        min_ay = self.y();
        max_ay = self.y() + self.height();

        min_by = renderable.y();
        max_by = renderable.y() + renderable.height();

        a_left_b = max_ax < min_bx;
        a_right_b = min_ax > max_bx;
        a_above_b = min_ay > max_by;
        a_below_b = max_ay < min_by;

        # Do a base check to make sure they are even remotely near each other.
        if a_left_b or a_right_b or a_above_b or a_below_b:
            return False;

        # Check if one shape is entirely inside the other shape
        if (min_ax >= min_bx and max_ax <= max_bx) and (min_ay >= min_by and max_ay <= max_by):
            print('One inside another?');
            return True;

        if (min_bx >= min_ax and max_bx <= max_ax) and (min_by >= min_ay and max_by <= max_ay):
            print('One inside another?');
            return True;

        # Next we are going to use a sweeping line algorithm.
        # Essentially we will process the lines on the x axis, one coordinate at a time (imagine a vertical line scan).
        # Then we will look for their orientations. We will essentially make sure its impossible they do not cross.
        shape1 = self._get_vertices(self);
        # noinspection PyProtectedMember
        shape2 = renderable._get_vertices();

        print('Overlaps Debug: ');
        print(f'Shape #1: {shape1}');
        print(f'Shape #2: {shape2}');

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
            result = (point2.y() - point1.y() * (point3.x() - point2.x())) - \
                     ((point2.x() - point1.x()) * (point3.y() - point2.y()));

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

        shape1_point1 = shape1[0];
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)];
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
                if orientation1 == 0 and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True;

                if orientation2 == 0 and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True;

                if orientation3 == 0 and point_on_segment(edge2[0], edge1[0], edge1[1]):
                    return True;

                if orientation4 == 0 and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True;

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False;

    # noinspection PyProtectedMember
    def _get_vertices(self):
        shape_data = self._screen._screen._shapes[self._ref.turtle.shapeIndex]._data;

        shape = self._ref._polytrafo(self._ref._getshapepoly(shape_data));

        real_shape = [];

        # Now we loop through and modify the coordinates so that they fit the coordinates of our system.
        # this is an unnecessary calculation but I'm doing it now to ensure that the algorithm is correct.

        for (x2, y2) in shape:
            real_shape.append(Location(x2 + self._screen.width() / 2, -y2 + self._screen.height() / 2));

        return real_shape;

    def update(self) -> None:
        """
        Update the internal reference of the object.
        :return: None
        """

        # noinspection PyBroadException
        try:
            super().update();
            self._ref.shapesize(stretch_wid=self.height() / PIXEL_RATIO, stretch_len=self.width() / PIXEL_RATIO);
            self._ref.setheading(self._angle);

            if self._visible:
                self._ref.showturtle();
            elif not self._visible:
                self._ref.hideturtle();

            if self._fill is True:
                if self._border is not None:
                    self._ref.color(self._border.__value__(), self._color.__value__());
                else:
                    self._ref.color(self._color.__value__());
            elif self._border is not None:
                # Fill must be passed as an empty string
                FILL_CONSTANT = '';
                self._ref.color(FILL_CONSTANT);
                self._ref.color(self._border.__value__(), FILL_CONSTANT);
            else:
                raise NameError('Fill was set to false but no border was passed.');

        except:
            pass;  # debug('Termination likely, but an internal error may have occurred');


class Rectangle(Renderable):
    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super(Rectangle, self).__init__(screen, x, y, width, height, color, border, fill, rotation, visible, location);
        self._ref.shape('square');


class Oval(Renderable):
    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super(Oval, self).__init__(screen, x, y, width, height, color, border, fill, rotation, visible, location);
        self._ref.shape('circle');


class Triangle(Renderable):
    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super(Triangle, self).__init__(screen, x, y, width, height, color, border, fill, rotation, visible, location);
        self._ref.shape('triangle');


class Polygon(Renderable):
    def __init__(self, screen: Screen, num_sides: int, x: float = 0, y: float = 0,
                 width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super(Polygon, self).__init__(screen, x, y, width, height, color, border, fill, rotation, visible, location);

        # We need to generate a list of points relative to the center of the polygon
        # the angle between any two vertices in a regular polygon is 2pi / n (where n is num_sides)

        # The "radius" of an imaginary circle that surrounds the shape. Turtle expects the radius of its pixel modifier.
        radius = PIXEL_RATIO / 2;
        shape_points = [];
        for i in range(num_sides):
            shape_points.append((radius * math.cos(2 * math.pi * i / num_sides),
                                 radius * math.sin(2 * math.pi * i / num_sides)));

        import uuid;
        self._id = uuid.uuid4();

        shape = turtle.Shape('polygon', shape_points);

        # noinspection PyProtectedMember
        self._screen._screen.register_shape(str(self._id), shape);
        self._ref.shape(str(self._id));


# noinspection PyProtectedMember
class CustomPolygon(Renderable):
    """
    Warning: This class is unfinished and if used improperly can have unintended sid effects.
    """

    def __init__(self, screen: Screen, vertices: list,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 visible: bool = True,
                 rotation: float = 0):
        self._screen = screen;
        self._color = color;
        self._border = border if border is not None else Color('');
        self._fill = fill;
        self._angle = rotation;
        self._visible = visible;

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
        self._location = Location(xmin, ymin);
        self._width = xmin + (xmax - xmin) / 2;
        self._height = ymin + (ymax - ymin) / 2;

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in real_vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));
            # tk_vertices.append((self.x() - ((self._screen.width() / 2) + 1),
            #                                 (self.y() - (self._screen.height() / 2)) + self.height()));

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        self._ref = self._screen._screen.cv.create_polygon(
            tk_vertices,
            fill=self._screen._screen._colorstr(self._color.__value__()),
            outline=self._screen._screen._colorstr(self._border.__value__()),
            state=state
        );

    def rotate(self, angle_diff: float) -> None:
        self._angle += angle_diff;
        self.rotation(self._angle);

    def rotation(self, angle: float = None) -> float:
        if angle is not None:
            self._angle = angle;
            self.update();

        return self._angle;

    def _set_angle(self):
        # get centroid

        pass;

    def update(self):
        # Update stuffs here
        pass;


# class Image(Renderable):
#     def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
#                  width: float = None, height: float = None,
#                  color: Color = Color('black'),
#                  border: Color = None,
#                  fill: bool = True,
#                  rotation: float = 0,
#                  visible: bool = True,
#                  location: Location = None):
#         self._image_name = image;
#         pil_image = PIL.Image.open(image);
#         self._image = PIL.ImageTk.PhotoImage(pil_image);
#         screen._screen.addshape(self._image);
#
#         # If the width is not defined then we will use the images default width.
#         if width is None:
#             width = self._image.width();
#
#         if height is None:
#             height = self._image.height();
#
#         super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible, location);
#         self._ref.shape(self._image_name);


# == NON RENDERABLES == #


class Text(Object):
    _anchor = 'sw';  # sw technically means southwest but it means bottom left anchor. (we change to top left in code)
    _aligns = {'left': tk.LEFT, 'center': tk.CENTER, 'right': tk.RIGHT};

    # noinspection PyProtectedMember
    def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = Color('black'),
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        super(Text, self).__init__(screen, x, y);
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

        self._ref = self._screen._screen.cv.create_text(self.x() - ((self._screen.width() / 2) + 1),
                                                        (self.y() - (self._screen.height() / 2)) + self.size(),
                                                        text=self.text(),
                                                        anchor=Text._anchor,
                                                        justify=Text._aligns[self.align()],
                                                        fill=self._screen._screen._colorstr(self.color().__value__()),
                                                        font=font_data,
                                                        state=state,
                                                        angle=self._angle);

        x0, y0, x1, y1 = screen._screen.cv.bbox(self._ref);
        self._width = x1 - x0;
        self._height = y1 - y0;
        screen._screen.cv.update();

    def text(self, text: str = None) -> str:
        """
        Get or set the text. Use '\n' to separate lines.
        :param text: text to set to (str), if any
        :return: the text
        """

        if text is not None:
            self._text = text;
            self.update();

        return self._text;

    def width(self) -> float:
        """
        Get the width of the text (cannot be modified)
        :return the width of the text
        """

        return self._width;

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
            self._angle = rotation;
            self.update();

        return self._angle;

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the text by a difference, in degrees
        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        self.rotation(self._angle + angle_diff);

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the text
        :param visible: the visibility to set to, if any
        :return: the visibility of the text
        """

        if visible is not None:
            self._visible = visible;
            self.update();

        return self._visible;

    # noinspection PyProtectedMember
    def update(self) -> None:
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

        self._ref = self._screen._screen.cv.create_text(self.x() - ((self._screen.width() / 2) + 1),
                                                        (self.y() - (self._screen.height() / 2)) + self.size(),
                                                        text=self.text(),
                                                        anchor=Text._anchor,
                                                        justify=Text._aligns[self.align()],
                                                        fill=self._screen._screen._colorstr(self.color().__value__()),
                                                        font=font_data,
                                                        state=state,
                                                        angle=self._angle);
        self._screen._screen.cv.tag_lower(self._ref, old_ref);
        self._screen._screen.cv.delete(old_ref);

        x0, y0, x1, y1 = self._screen._screen.cv.bbox(self._ref);
        self._width = x1 - x0;
        self._height = y1 - y0;

        self._screen._screen.cv.update();


class Line(Object):
    def __init__(self, screen: Screen, *args, color: Color = Color('black'), thickness: int = 1, dashes=None,
                 visible: bool = True):
        super().__init__(screen);
        self._screen = screen;

        if len(args) == 2 and (type(arg) is tuple or type(arg) is Location for arg in args):
            self._pos1 = Location(args[0][0], args[0][1]);
            self._pos2 = Location(args[1][0], args[1][1]);
        elif len(args) == 4 and (type(arg) is float or type(arg) is int for arg in args):
            self._pos1 = Location(args[0], args[1]);
            self._pos2 = Location(args[2], args[3]);
        else:
            raise TypeError('Incorrect Argumentation: Line requires either two Locations, tuples, or four '
                            'numbers (x1, y1, x2, y2).');

        self._color = color;
        self._thickness = thickness;
        self._dashes = dashes;
        self._visible = visible;

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        if dashes is not None and type(dashes) is not tuple:
            self._dashes = (dashes, dashes)

        print(f'Created line: Pos1: {self._pos1}, Pos2: {self._pos2}');

        # noinspection PyProtectedMember
        self._ref = self._screen._screen.cv.create_line(self._pos1.x(),
                                                        self._pos1.y(),
                                                        self._pos2.x(),
                                                        self._pos2.y(),
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
            elif len(args) == 2 and (type(arg) is float or type(arg) is int for arg in args):
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

    def move(self, dx: float, dy: float, point: int = 0) -> None:
        """
        Move both endpoints by the same dx and dy
        :param dx: the distance x to move
        :param dy: the distance y to move
        :param point: affect only one of the endpoints; options: (1, 2)
        :return: None
        """

        if point != 0:
            if point == 1:
                self._pos1.move(dx, dy);
            else:
                self._pos2.move(dx, dy);
        else:
            self._pos1.move(dx, dy);
            self._pos2.move(dx, dy);

        self.update();

    def moveto(self, *args) -> None:
        """
        Move both of the endpoints to new locations.
        :param args: Either two locations, tuples, or four numbers (x1, y1, x2, y2).
        :return: None
        """

        if len(args) == 2 and (type(arg) is tuple or type(arg) is Location for arg in args):
            self._pos1.moveto(args[0][0], args[0][1]);
            self._pos2.moveto(args[1][0], args[1][0]);
        elif len(args) == 4 and (type(arg) is int or type(arg) is float for arg in args):
            self._pos1.moveto(args[0], args[1]);
            self._pos2.moveto(args[2], args[3]);
        else:
            raise TypeError('Incorrect Argumentation: Requires either two locations, tuples, or four numbers (x1, y1, '
                            'x2, y2)');

        self.update();

    def location(self) -> tuple[Location, Location]:
        """
        Returns the locations of both the endpoints
        :return: the locations of both the endpoints
        """

        return self._pos1, self._pos2;

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the line
        :param color: the color to set to, if any
        :return: the color of the line
        """

        if color is not None:
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
            self._thickness = thickness;
            self.update();

        return self._thickness;

    def dashes(self, dashes: bool = None) -> bool:
        """
        Retrive or enable/disable the dashes for the line
        :param dashes: the visibility to set to, if any
        :return: the toggle-state of dashes
        """

        if dashes is not None:
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
            self._visible = visible;
            self.update();

        return self._visible;

    # noinspection PyProtectedMember
    def update(self):
        old_ref = self._ref;

        if self._dashes is not None and type(self._dashes) is not tuple:
            self._dashes = (self._dashes, self._dashes)

        state = tk.NORMAL if self._visible else tk.HIDDEN;
        self._ref = self._screen._screen.cv.create_line(self._pos1.x(), self._pos1.y(), self._pos2.x(), self._pos2.y(),
                                                        fill=self._screen._screen._colorstr(self.color().__value__()),
                                                        width=self._thickness, dash=self._dashes, state=state);

        self._screen._screen.cv.tag_lower(self._ref, old_ref);
        self._screen._screen.cv.delete(old_ref);

        self._screen._screen.cv.update();
