"""
pyDraw v{version}

This library is a graphics-interface library designed to make graphics in Python
easier and more simple. It was designed to be easy to teach/learn and to utilize
some of the basic concepts of OOP and functional programming in its setup.

Documentation: https://docs.pydraw.graphics
Source: https://github.com/pydraw/pydraw

(Author: Noah Coetsee)

No hiding spots here (for semicolons)
Hide and seek champion since version 0.1.0

Semicolons are my best friends.
"""


class InvalidArgumentError(ValueError):
    pass;


class UnsupportedError(NameError):
    pass;


class PydrawError(NameError):
    pass;


# from pydraw.errors import *;


def verify_type(obj, required_type):
    """
    Verifies an objects type is the passed type
    :param obj: the object to check
    :param required_type: the expected type
    :return: True if required type is present or obj is None, else False
    """

    if type(required_type) is tuple and len(required_type) > 0:
        if obj is None:
            return True;

        for allowed_type in required_type:
            if type(obj) is allowed_type:
                return True;

    return type(obj) is required_type or obj is None;


def verify(*args):
    """
    Takes a list of values and expected types and returns if all objects meet their expected types.
    :param args: a list of objects and types, ex: (some_number, float, some_location, Location)
    :return: True if all args meet their expected types, throws an error if not.
    """
    if len(args) % 2 != 0:
        raise InvalidArgumentError('The verify() method must be passed an even number of arguments, '
                                   'Ex: (some_number, float, some_location, Location).');

    for i in range(0, len(args), 2):
        obj = args[i];
        expected_type = args[i+1];
        # print(f'Obj: {obj}, Expected Type: {expected_type}, Meets: {verify_type(obj, expected_type)}');

        if not verify_type(obj, expected_type):
            raise InvalidArgumentError(f'Type does not match: {type(obj)} ({obj}) : {expected_type}');


import turtle;
import tkinter as tk;
# from pydraw.errors import *;


class Color:
    """
    An immutable class that contains a color values, usually by name or RGB
    """

    NONE = None;

    def __init__(self, *args):
        if len(args) == 0 or len(args) == 2 or len(args) > 3:
            raise NameError('Invalid arguments passed to color!');

        self._name = None;
        self._hex_value = None;

        # we should expect three-four arguments for rgb or rgba
        if len(args) >= 3:
            for arg in args:
                if type(arg) is not int:
                    raise NameError('Expected integer arguments, but found \'' + str(arg) + '\' instead.');

            self._r = args[0];
            self._g = args[1];
            self._b = args[2];

            self._mode = 0;
        elif len(args) == 1:
            if type(args[0]) is tuple:
                for arg in args[0]:
                    if type(arg) is not int:
                        raise NameError('Expected integer arguments, but found \'' + str(arg) + '\' instead.');

                self._r = args[0][0];
                self._g = args[0][1];
                self._b = args[0][2];

                self._mode = 0;
            if type(args[0]) is not str:
                raise NameError('Expected string but instead found: ' + str(args[0]));

            string = str(args[0]);
            if string.startswith('#'):
                self._hex_value = string;
                self._mode = 2;

                rgb = self._rgb(self);
                self._r = int(rgb[0]);
                self._g = int(rgb[1]);
                self._b = int(rgb[2]);
            else:
                self._name = string;
                self._mode = 1;

                if self._name != '':
                    rgb = self._rgb(self);
                    self._r = int(rgb[0] / 256);
                    self._g = int(rgb[1] / 256);
                    self._b = int(rgb[2] / 256);
                else:
                    self._r, self._g, self._b = -1, -1, -1;

    def __value__(self):
        """
        Retrieves the value to be interpreted internally by Turtle
        :return:
        """
        if self._mode == 0:
            return self.red(), self.green(), self.blue();
        elif self._mode == 1:
            return self._name;
        else:
            return self._hex_value;

    def red(self):
        """
        Get the red property.
        :return: r
        """
        return self._r;

    def green(self):
        """
        Get the green propety
        :return: g
        """
        return self._g;

    def blue(self):
        """
        Get the blue property
        :return: b
        """
        return self._b;

    def rgb(self):
        """
        Get the RGB tuple
        :return: tuple (R, G, B)
        """
        return self.red(), self.green(), self.blue();

    def name(self):
        """
        Get the name of the color (only if defined)
        :return: color or None
        """

        return self._name;

    def hex(self):
        """
        Get the hex of the color (only if defined)
        :return: hex_value or None
        """
        return self._hex_value;

    def clone(self):
        """
        Clone this color!
        :return: a clone.
        """

        return Color(self.__value__());

    def __str__(self):
        if self._mode == 0:
            string = f'({self._r, self._g, self._b})';
        elif self._mode == 1:
            string = self._name;
        else:
            string = self._hex_value;

        return string;

    def __eq__(self, other):
        if type(other) is not Color:
            return False;

        return other.rgb() == self.rgb();

    @staticmethod
    def _rgb(color) -> tuple:
        """
        Convert a color to an rgb tuple.
        :param color: the color to convert
        :return: a tuple representing RGB
        """

        if color.name() is not None:
            try:
                rgb = turtle.getcanvas().winfo_rgb(color.name());
            except tk.TclError:
                raise PydrawError('Color-string does not exist: ', color.name());
        elif color.hex() is not None:
            hexval = color.hex().replace('#', '');

            if len(hexval) != 6:
                if len(hexval) == 3:
                    hexval = ''.join([char * 2 for char in hexval]);  # Optimized string manipulation.
                else:
                    raise InvalidArgumentError('A color hex must be six or three characers long. '
                                               'Ex: "#FFFFFF" or "#FFF"');

            rgb = tuple(int(hexval[i:i + 2], 16) for i in (0, 2, 4));
        else:
            rgb = (color.red(), color.green(), color.blue());

        return rgb;
    
    @staticmethod
    def all():
        """
        Get all color values that have a string-name.
        :return: a tuple (immutable list) of all Colors.
        """

        return tuple(COLORS.copy());

    @staticmethod
    def random():
        """
        Retrieve a random Color.
        :return: returns
        """

        import random
        return random.choice(COLORS).clone();

    def __repr__(self):
        return self.__str__();


Color.NONE = Color('');

COLORS = [Color('snow'), Color('ghost white'), Color('white smoke'), Color('gainsboro'), Color('floral white'),
          Color('old lace'),
          Color('linen'), Color('antique white'), Color('papaya whip'), Color('blanched almond'), Color('bisque'),
          Color('peach puff'),
          Color('navajo white'), Color('lemon chiffon'), Color('mint cream'), Color('azure'), Color('alice blue'),
          Color('lavender'),
          Color('lavender blush'), Color('misty rose'), Color('dark slate gray'), Color('dim gray'),
          Color('slate gray'),
          Color('light slate gray'), Color('gray'), Color('light grey'), Color('midnight blue'), Color('navy'),
          Color('cornflower blue'), Color('dark slate blue'),
          Color('slate blue'), Color('medium slate blue'), Color('light slate blue'), Color('medium blue'),
          Color('royal blue'), Color('blue'),
          Color('dodger blue'), Color('deep sky blue'), Color('sky blue'), Color('light sky blue'), Color('steel blue'),
          Color('light steel blue'),
          Color('light blue'), Color('powder blue'), Color('pale turquoise'), Color('dark turquoise'),
          Color('medium turquoise'), Color('turquoise'),
          Color('cyan'), Color('light cyan'), Color('cadet blue'), Color('medium aquamarine'), Color('aquamarine'),
          Color('dark green'), Color('dark olive green'),
          Color('dark sea green'), Color('sea green'), Color('medium sea green'), Color('light sea green'),
          Color('pale green'), Color('spring green'),
          Color('lawn green'), Color('medium spring green'), Color('green yellow'), Color('lime green'),
          Color('yellow green'),
          Color('forest green'), Color('olive drab'), Color('dark khaki'), Color('khaki'), Color('pale goldenrod'),
          Color('light goldenrod yellow'),
          Color('light yellow'), Color('yellow'), Color('gold'), Color('light goldenrod'), Color('goldenrod'),
          Color('dark goldenrod'), Color('rosy brown'),
          Color('indian red'), Color('saddle brown'), Color('sandy brown'),
          Color('dark salmon'), Color('salmon'), Color('light salmon'), Color('orange'), Color('dark orange'),
          Color('coral'), Color('light coral'), Color('tomato'), Color('orange red'), Color('red'), Color('hot pink'),
          Color('deep pink'), Color('pink'), Color('light pink'),
          Color('pale violet red'), Color('maroon'), Color('medium violet red'), Color('violet red'),
          Color('medium orchid'), Color('dark orchid'), Color('dark violet'), Color('blue violet'), Color('purple'),
          Color('medium purple'),
          Color('thistle'), Color('snow2'), Color('snow3'),
          Color('snow4'), Color('seashell2'), Color('seashell3'), Color('seashell4'), Color('AntiqueWhite1'),
          Color('AntiqueWhite2'),
          Color('AntiqueWhite3'), Color('AntiqueWhite4'), Color('bisque2'), Color('bisque3'), Color('bisque4'),
          Color('PeachPuff2'),
          Color('PeachPuff3'), Color('PeachPuff4'), Color('NavajoWhite2'), Color('NavajoWhite3'), Color('NavajoWhite4'),
          Color('LemonChiffon2'), Color('LemonChiffon3'), Color('LemonChiffon4'), Color('cornsilk2'),
          Color('cornsilk3'),
          Color('cornsilk4'), Color('ivory2'), Color('ivory3'), Color('ivory4'), Color('honeydew2'), Color('honeydew3'),
          Color('honeydew4'),
          Color('LavenderBlush2'), Color('LavenderBlush3'), Color('LavenderBlush4'), Color('MistyRose2'),
          Color('MistyRose3'),
          Color('MistyRose4'), Color('azure2'), Color('azure3'), Color('azure4'), Color('SlateBlue1'),
          Color('SlateBlue2'), Color('SlateBlue3'),
          Color('SlateBlue4'), Color('RoyalBlue1'), Color('RoyalBlue2'), Color('RoyalBlue3'), Color('RoyalBlue4'),
          Color('blue2'), Color('blue4'),
          Color('DodgerBlue2'), Color('DodgerBlue3'), Color('DodgerBlue4'), Color('SteelBlue1'), Color('SteelBlue2'),
          Color('SteelBlue3'), Color('SteelBlue4'), Color('DeepSkyBlue2'), Color('DeepSkyBlue3'), Color('DeepSkyBlue4'),
          Color('SkyBlue1'), Color('SkyBlue2'), Color('SkyBlue3'), Color('SkyBlue4'), Color('LightSkyBlue1'),
          Color('LightSkyBlue2'),
          Color('LightSkyBlue3'), Color('LightSkyBlue4'), Color('SlateGray1'), Color('SlateGray2'), Color('SlateGray3'),
          Color('SlateGray4'), Color('LightSteelBlue1'), Color('LightSteelBlue2'), Color('LightSteelBlue3'),
          Color('LightSteelBlue4'), Color('LightBlue1'), Color('LightBlue2'), Color('LightBlue3'), Color('LightBlue4'),
          Color('LightCyan2'), Color('LightCyan3'), Color('LightCyan4'), Color('PaleTurquoise1'),
          Color('PaleTurquoise2'),
          Color('PaleTurquoise3'), Color('PaleTurquoise4'), Color('CadetBlue1'), Color('CadetBlue2'),
          Color('CadetBlue3'),
          Color('CadetBlue4'), Color('turquoise1'), Color('turquoise2'), Color('turquoise3'), Color('turquoise4'),
          Color('cyan2'), Color('cyan3'),
          Color('cyan4'), Color('DarkSlateGray1'), Color('DarkSlateGray2'), Color('DarkSlateGray3'),
          Color('DarkSlateGray4'),
          Color('aquamarine2'), Color('aquamarine4'), Color('DarkSeaGreen1'), Color('DarkSeaGreen2'),
          Color('DarkSeaGreen3'),
          Color('DarkSeaGreen4'), Color('SeaGreen1'), Color('SeaGreen2'), Color('SeaGreen3'), Color('PaleGreen1'),
          Color('PaleGreen2'),
          Color('PaleGreen3'), Color('PaleGreen4'), Color('SpringGreen2'), Color('SpringGreen3'), Color('SpringGreen4'),
          Color('green2'), Color('green3'), Color('green4'), Color('chartreuse2'), Color('chartreuse3'),
          Color('chartreuse4'),
          Color('OliveDrab1'), Color('OliveDrab2'), Color('OliveDrab4'), Color('DarkOliveGreen1'),
          Color('DarkOliveGreen2'),
          Color('DarkOliveGreen3'), Color('DarkOliveGreen4'), Color('khaki1'), Color('khaki2'), Color('khaki3'),
          Color('khaki4'),
          Color('LightGoldenrod1'), Color('LightGoldenrod2'), Color('LightGoldenrod3'), Color('LightGoldenrod4'),
          Color('LightYellow2'), Color('LightYellow3'), Color('LightYellow4'), Color('yellow2'), Color('yellow3'),
          Color('yellow4'),
          Color('gold2'), Color('gold3'), Color('gold4'), Color('goldenrod1'), Color('goldenrod2'), Color('goldenrod3'),
          Color('goldenrod4'),
          Color('DarkGoldenrod1'), Color('DarkGoldenrod2'), Color('DarkGoldenrod3'), Color('DarkGoldenrod4'),
          Color('RosyBrown1'), Color('RosyBrown2'), Color('RosyBrown3'), Color('RosyBrown4'), Color('IndianRed1'),
          Color('IndianRed2'),
          Color('IndianRed3'), Color('IndianRed4'), Color('sienna1'), Color('sienna2'), Color('sienna3'),
          Color('sienna4'), Color('burlywood1'),
          Color('burlywood2'), Color('burlywood3'), Color('burlywood4'), Color('wheat1'), Color('wheat2'),
          Color('wheat3'), Color('wheat4'), Color('tan1'),
          Color('tan2'), Color('tan4'), Color('chocolate1'), Color('chocolate2'), Color('chocolate3'),
          Color('firebrick1'), Color('firebrick2'),
          Color('firebrick3'), Color('firebrick4'), Color('brown1'), Color('brown2'), Color('brown3'), Color('brown4'),
          Color('salmon1'), Color('salmon2'),
          Color('salmon3'), Color('salmon4'), Color('LightSalmon2'), Color('LightSalmon3'), Color('LightSalmon4'),
          Color('orange2'),
          Color('orange3'), Color('orange4'), Color('DarkOrange1'), Color('DarkOrange2'), Color('DarkOrange3'),
          Color('DarkOrange4'),
          Color('coral1'), Color('coral2'), Color('coral3'), Color('coral4'), Color('tomato2'), Color('tomato3'),
          Color('tomato4'), Color('OrangeRed2'),
          Color('OrangeRed3'), Color('OrangeRed4'), Color('red2'), Color('red3'), Color('red4'), Color('DeepPink2'),
          Color('DeepPink3'), Color('DeepPink4'),
          Color('HotPink1'), Color('HotPink2'), Color('HotPink3'), Color('HotPink4'), Color('pink1'), Color('pink2'),
          Color('pink3'), Color('pink4'),
          Color('LightPink1'), Color('LightPink2'), Color('LightPink3'), Color('LightPink4'), Color('PaleVioletRed1'),
          Color('PaleVioletRed2'), Color('PaleVioletRed3'), Color('PaleVioletRed4'), Color('maroon1'), Color('maroon2'),
          Color('maroon3'), Color('maroon4'), Color('VioletRed1'), Color('VioletRed2'), Color('VioletRed3'),
          Color('VioletRed4'),
          Color('magenta2'), Color('magenta3'), Color('magenta4'), Color('orchid1'), Color('orchid2'), Color('orchid3'),
          Color('orchid4'), Color('plum1'),
          Color('plum2'), Color('plum3'), Color('plum4'), Color('MediumOrchid1'), Color('MediumOrchid2'),
          Color('MediumOrchid3'),
          Color('MediumOrchid4'), Color('DarkOrchid1'), Color('DarkOrchid2'), Color('DarkOrchid3'),
          Color('DarkOrchid4'),
          Color('purple1'), Color('purple2'), Color('purple3'), Color('purple4'), Color('MediumPurple1'),
          Color('MediumPurple2'),
          Color('MediumPurple3'), Color('MediumPurple4'), Color('thistle1'), Color('thistle2'), Color('thistle3'),
          Color('thistle4'),
          Color('gray1'), Color('gray2'), Color('gray3'), Color('gray4'), Color('gray5'), Color('gray6'),
          Color('gray7'), Color('gray8'), Color('gray9'), Color('gray10'),
          Color('gray11'), Color('gray12'), Color('gray13'), Color('gray14'), Color('gray15'), Color('gray16'),
          Color('gray17'), Color('gray18'), Color('gray19'),
          Color('gray20'), Color('gray21'), Color('gray22'), Color('gray23'), Color('gray24'), Color('gray25'),
          Color('gray26'), Color('gray27'), Color('gray28'),
          Color('gray29'), Color('gray30'), Color('gray31'), Color('gray32'), Color('gray33'), Color('gray34'),
          Color('gray35'), Color('gray36'), Color('gray37'),
          Color('gray38'), Color('gray39'), Color('gray40'), Color('gray42'), Color('gray43'), Color('gray44'),
          Color('gray45'), Color('gray46'), Color('gray47'),
          Color('gray48'), Color('gray49'), Color('gray50'), Color('gray51'), Color('gray52'), Color('gray53'),
          Color('gray54'), Color('gray55'), Color('gray56'),
          Color('gray57'), Color('gray58'), Color('gray59'), Color('gray60'), Color('gray61'), Color('gray62'),
          Color('gray63'), Color('gray64'), Color('gray65'),
          Color('gray66'), Color('gray67'), Color('gray68'), Color('gray69'), Color('gray70'), Color('gray71'),
          Color('gray72'), Color('gray73'), Color('gray74'),
          Color('gray75'), Color('gray76'), Color('gray77'), Color('gray78'), Color('gray79'), Color('gray80'),
          Color('gray81'), Color('gray82'), Color('gray83'),
          Color('gray84'), Color('gray85'), Color('gray86'), Color('gray87'), Color('gray88'), Color('gray89'),
          Color('gray90'), Color('gray91'), Color('gray92'),
          Color('gray93'), Color('gray94'), Color('gray95'), Color('gray97'), Color('gray98'), Color('gray99')];


# from pydraw.errors import *;


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
        Moves the location to a new location!

        Can take two coordinates (x, y), a tuple, or a Location
        :param x: the x to move to
        :param y: the y to move to
        :return: the location (after change)
        """

        diff = (0, 0);

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is diff or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and type(args[0]) is tuple or type(args[0]) is diff:
                diff = (args[0][0], args[0][1]);
            elif len(args) == 2 and [type(arg) is float or type(arg) is int for arg in args]:
                diff = (args[0], args[1]);
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
        Moves the location by a specified difference.

        Can take two numbers (dx, dy), a tuple, or a Location
        :param dx: the dx to move by
        :param dy: the dy to move by
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


import turtle;
import tkinter as tk;
import inspect;
import time;

# from pydraw import Color;
# from pydraw import Location;
# from pydraw.util import *;

INPUT_TYPES = [
    'mousedown',
    'mouseup',
    'mousedrag',
    'mousemove',
    'keydown',
    'keyup',
    'keypress'
];

ALPHABET = [
    'a',
    'b',
    'c',
    'd',
    'e',
    'f',
    'g',
    'h',
    'i',
    'j',
    'k',
    'l',
    'm',
    'n',
    'o',
    'p',
    'q',
    'r',
    's',
    't',
    'u',
    'v',
    'w',
    'x',
    'y',
    'z',
];

UPPER_ALPHABET = [];
for letter in ALPHABET:
    UPPER_ALPHABET.append(letter.upper());

KEYS = [
           '1',
           '2',
           '3',
           '4',
           '5',
           '6',
           '7',
           '8',
           '9',
           '0',

           # '!',
           # '@',
           # '#',
           # '$',
           # '%',
           # '^',
           # '&',
           # '*',
           # '(',
           # ')',

           '-',  # note: appears to be the shift key?

           # '_',
           # '=',
           # '+',
           # '\\',
           # '|',
           # ',',
           # '<',
           # '.',
           # '>'
           # '/',
           # '?',

           'Up',
           'Down',
           'Left',
           'Right',

           'space',
           'Shift_L',
           'Shift_R',
           'Control_L',
           'Control_R'
       ] + ALPHABET + UPPER_ALPHABET;

BUTTONS = [
    1,
    2,
    3
];

BORDER_CONSTANT = 10;


class Screen:
    """
    A class containing methods and values that can be manipulated in order to affect
    the window that is created. Sort of like a canvas.
    """

    def __init__(self, width=800, height=600, title="pydraw"):
        self._screen = turtle.Screen();
        self._turtle = turtle;
        self._canvas = self._screen.cv;
        self._root = self._canvas.winfo_toplevel();

        self._width = width;
        self._height = height;

        # The only thing on the canvas is itself, so we prevent anything stupid from happening.
        # self._canvas.configure(scrollregion=self._canvas.bbox("all"));
        self._turtle.mode('logo');
        self._screen.setup(width + BORDER_CONSTANT, height + BORDER_CONSTANT);
        self._screen.screensize(width, height);
        # self._screen.setup(width + BORDER_CONSTANT, height + BORDER_CONSTANT);
        # self._canvas.configure(width=self._root.winfo_width(), height=self._root.winfo_height())
        # self.update();
        # This was not necessary as the canvas will align with the window's dimensions as set in the above line.

        self._root.resizable(False, False);  # No resizing!

        self._screen.title(title);
        self._title = title;
        self._color = Color('white');

        self._objects = [];  # Store objects on the screen :)
        self._fullscreen = False;

        self._screen.colormode(255);

        # store the mouse position
        self._mouse = Location(0, 0);
        self._gridlines = [];
        self._gridstate = False;  # grid is disabled by default

        self._helpers = [];
        self._helperstate = 0;

        # By default we want to make sure that all objects are drawn instantly.
        self._screen.tracer(0);
        self._screen.update();

        # import atexit;
        # self._root.protocol('WM_DELETE_WINDOW', self._exit_handler);
        # atexit.register(self._exit_handler)

        # --- #

        self.registry = {};  # The input function registry (stores input callbacks)

    def title(self, title: str = None) -> str:
        """
        Get or set the title of the screen.
        :param title: the title to set to, if any
        :return: the title
        """

        if title is not None:
            self._title = title;
            self._screen.title(title);

        return self._title;

    def color(self, color: Color = None) -> Color:
        """
        Set the background color of the screen.
        :param color: the color to set the background to
        :return: None
        """

        if color is not None:
            self._color = color;
            self._screen.bgcolor(color.__value__());
        return self._color;

    def picture(self, pic: str) -> None:
        """
        Set the background picture of the screen.
        :param pic: the path to said picture from the file
        :return: None
        """

        self._screen.bgpic(pic);

    def resize(self, width, height) -> None:
        """
        Resize the screen to new dimensions
        :param width: the width to resize to
        :param height: the height to resize to
        :return: None
        """

        # noinspection PyBroadException
        try:
            self._screen.screensize(width, height);
        except:
            pass;

    def size(self) -> (int, int):
        """
        Get the size of the WINDOW (please note this is not the canvas, and those attributes should be
        retrieved using the width() and height() methods respectively)
        :return: a tuple containing the width and height of the WINDOW
        """

        # noinspection PyBroadException
        try:
            return self._screen.window_width(), self._screen.window_height();
        except:
            return -1, -1;  # Again, trying to avoid showing errors due to tkinter shutting down.

    def width(self) -> int:
        """
        Returns the width of the CANVAS within the screen. Important.
        :return: an integer representing the width of the canvas
        """

        # noinspection PyBroadException
        try:
            return self._screen.getcanvas().winfo_width() - BORDER_CONSTANT;
        except:
            return -1;  # Just return -1 because tkinter is shutting down

    def height(self) -> int:
        """
        Returns the height of the CANVAS within the screen. Important.
        :return:
        """

        # noinspection PyBroadException
        try:
            return self._screen.getcanvas().winfo_height() - BORDER_CONSTANT;
        except:
            return -1;  # Just return -1 because tkinter is shutting down

    def center(self) -> Location:
        """
        Gets the center of the screen.
        """
        return Location(self.width() / 2, self.height() / 2);

    # noinspection PyMethodMayBeStatic
    def top_left(self) -> Location:
        """
        Returns the top left corner of the screen
        :return: Location
        """

        return Location(0, 0);

    def top_right(self) -> Location:
        """
        Returns the top right corner of the screen
        :return: Location
        """

        return Location(self.width(), 0);

    def bottom_left(self) -> Location:
        """
        Returns the bottom left corner of the screen
        :return: Location
        """

        return Location(0, self.height());

    def bottom_right(self) -> Location:
        """
        Returns the bottom right corner of the screen
        :return: Location
        """

        return Location(self.width(), self.height());

    def mouse(self) -> Location:
        """
        Get the current mouse-position
        :return: the mouse-position in the form of a Location
        """

        return self._mouse;

    # Direct Manipulation
    def prompt(self, text: str, title: str = 'Prompt') -> str:
        """
        Prompts the user for keyboard input
        :param: text the text to prompt the user with
        :param: title the title of the dialog box
        :return: None
        """

        text = self._screen.textinput(title, text);

        self._screen.listen();  # keep us nice and listening :)
        return text;

    def grid(self, rows: int = None, cols: int = None, cellsize: tuple = (50, 50), helpers: bool = True):
        # from pydraw import Line, Text;

        if len(self._gridlines) > 0:
            [line.remove() for line in self._gridlines];
            self._gridlines.clear();
        if len(self._helpers) > 0:
            [helper.remove() for helper in self._helpers];
            self._helpers.clear();
        self._gridstate = True;

        if rows is not None:
            cellsize = (self.height() / rows, cellsize[1]);
        if cols is not None:
            cellsize = (cellsize[0], self.width() / cols);

        if helpers:
            textsize = int((self.width() + self.height() / 2) / 70);  # Text size is proportionate to screensize.

        for row in range(int(cellsize[1]), int(self.height()), int(cellsize[1])):
            line = Line(self, Location(0, row), Location(self.width(), row),
                                        color=Color('lightgray'));
            self._gridlines.append(line);
            self._objects.remove(line);  # Don't want this in our objects list :)

            if helpers:
                helper = Text(self, str(row), 15, row, color=Color('gray'), size=textsize);
                helper.move(-helper.width() / 2, -helper.height() / 2);
                self._helpers.append(helper);
                self._objects.remove(helper);

        for col in range(int(cellsize[0]), int(self.width()), int(cellsize[0])):
            line = Line(self, Location(col, 0), Location(col, self.height()),
                                        color=Color('lightgray'));
            self._gridlines.append(line);
            self._objects.remove(line);  # Don't want this in our objects list :)

            if helpers:
                helper = Text(self, str(col), col, 10, color=Color('gray'), size=textsize);
                helper.move(-helper.width() / 2, -helper.height() / 2);
                self._helpers.append(helper);
                self._objects.remove(helper);

    def toggle_grid(self, value=None):
        if value is None:
            value = not self._gridstate;

        if len(self._gridlines) == 0:
            self.grid();  # Create a grid if one does not exist.

        [line.visible(value) for line in self._gridlines];
        [helper.visible(value) for helper in self._helpers];

    def gridlines(self) -> tuple:
        """
        Allows you to retrieve the lines of the grid, but note that you cannot modify them!
        :return: a tuple (immutable list) of the gridlines.
        """

        return tuple(self._gridlines);

    def _redraw_grid(self):
        """
        An internal method to redraw the grid to the screen after screen.clear() is called.
        """
        # from pydraw import Line, Text;

        new_lines = [];
        for line in self._gridlines:
            new_line = Line(self, line.pos1(), line.pos2(), color=line.color());
            line.remove();
            self._objects.remove(new_line);  # Still don't want this in the main objects list.
            new_lines.append(new_line);

        new_helpers = [];
        for helper in self._helpers:
            new_helper = Text(self, helper.text(), helper.x(), helper.y(), color=helper.color(), size=helper.size());
            helper.remove();
            self._objects.remove(new_helper);
            new_helpers.append(new_helper);

        self._gridlines.clear();
        self._gridlines = new_lines;

        self._helpers.clear();
        self._helpers = new_helpers;

    def grab(self, filename: str = None) -> str:
        """
        Grabs a screenshot of the image and saves it to the directory with the specified filename!
        Note that if no filename is specified the file will be given a name based on the epoch time.
        :param filename: the name of the file to save the screenshot to.
        :return: the name of the file.
        """

        # noinspection PyBroadException
        try:
            from PIL import ImageGrab;

            # We need to get the exact canvas coordinates. (bruh)
            x1 = self._root.winfo_rootx() + self._canvas.winfo_x() + BORDER_CONSTANT;
            y1 = self._root.winfo_rooty() + self._canvas.winfo_y() + BORDER_CONSTANT;
            x2 = x1 + self.width() - BORDER_CONSTANT;
            y2 = y1 + self.height() - BORDER_CONSTANT;

            if filename is None:
                filename = 'pydraw' + str(time.time() % 10000);

            if not filename.endswith('.png'):
                filename += '.png';

            ImageGrab.grab().crop((x1, y1, x2, y2)).save(filename);
            return filename;
        except:
            raise UnsupportedError('As PIL is not installed, you cannot grab the screen! '
                                   'Install Pillow via: \'pip install pillow\'.');

    def fullscreen(self, fullscreen: bool = None) -> bool:
        """
        Get or set the fullscreen state of the application. Note that this will not resize your shapes, nor
        will it REPOSITION them. It is highly recommended that you call this method before creating any shapes!

        !!! EXPERIMENTAL !!!
        :param fullscreen: the new fullscreen state, if any
        :return: the current fullscreen state of the Screen
        """

        if fullscreen is not None:
            self._fullscreen = fullscreen;
            self._root.attributes("-fullscreen", fullscreen);
            self.update();

        return self._fullscreen;

    def _front(self, obj) -> None:

        self._canvas.tag_raise(obj._ref);

    def _back(self, obj) -> None:
        # from pydraw import Object;

        verify(obj, Object);
        self._canvas.tag_lower(obj._ref);

    def _add(self, obj) -> None:
        """
        Internal method which adds object to a list upon construction.
        :param obj: the object to add.
        :return: None
        """

        self._objects.append(obj);

    # noinspection PyProtectedMember
    def remove(self, obj):
        if obj in self._objects:
            self._objects.remove(obj);
            print('removed: ' + str(type(obj)));
        elif obj not in self._gridlines and obj not in self._helpers:
            raise ValueError(f'Object: {obj} is not registered with the screen? Did you call the constructor?');
        self._screen.cv.delete(obj._ref);
        del obj;

    def objects(self) -> tuple:
        """
        Retrieves all objects on the Screen!
        :return: A tuple (immutable list) of Objects (you will want to check types for certain methods!)
        """

        return tuple(self._objects);

    def clear(self) -> None:
        """
        Clears the screen.
        :return: None
        """

        try:
            for i in range(len(self._objects) - 1, -1, -1):
                self._objects[i].remove();
            # self._screen.clear();
            if self._gridstate:
                self._redraw_grid();  # Redraw the grid if it was active.
            self.color(self._color);  # Redraw the color of the screen.
        except (tk.TclError, AttributeError):
            pass;

    @staticmethod
    def sleep(delay: float) -> None:
        """
        Cause the program to sleep by calling time.sleep(delay)
        :param delay: the delay in seconds to sleep by
        :return: None
        """

        time.sleep(delay);

    def update(self) -> None:
        """
        Updates the screen.
        :return: None
        """
        try:
            # self._screen.update();
            self._canvas.update();
        except (turtle.Terminator, tk.TclError, AttributeError):
            # If we experience the termination exception, we will print the termination of the program
            # and exit the python program.
            print('Terminated.');
            exit(0);

    def stop(self) -> None:
        """
        Holds the screen and all objects and prevents the window from closing.
        (Best used in place of a while loop if the program is simply drawing shapes with no change over time)
        :return: None
        """

        self.update();
        self._turtle.done();

    def exit(self) -> None:
        """
        Called at the end of pydraw programs as an event for succesful program execution and termination.
        For something similar to turtle.done() see Screen.stop()
        :return: None
        """

        self._screen.clear();
        self._root.destroy();
        exit(0);

    def _colorstr(self, color: Color) -> str:
        """
        Takes a pydraw Color and returns a tkinter-friendly string, while also preventing errors
        from occurring after tkinter has shut down.
        :param color: the Color to convert
        :return: the converted color (tkinter-str)
        """

        try:
            # noinspection PyProtectedMember
            # noinspection PyUnresolvedReferences
            colorstr = self._screen._colorstr(color.__value__());
            return colorstr;
        except (turtle.TurtleGraphicsError, tk.TclError):
            pass;

    # ------------------------------------------------------- #

    def listen(self) -> None:
        """
        Reads the file for input functions and registers them as callbacks!
        The input-type is determined by the name of the function.

        Allowed Names:
          - mousedown
          - mouseup
          - mousedrag
          - keydown
          - keyup
          - keypress (deprecated)
        :return: None
        """

        frm = inspect.stack()[1];
        mod = inspect.getmodule(frm[0]);
        for (name, function) in inspect.getmembers(mod, inspect.isfunction):
            if name.lower() not in INPUT_TYPES:
                continue;

            self.registry[name.lower()] = function;
            # print('Registered input-function:', name);

        self._listen();

    def _listen(self):
        self._screen.listen();

        # Keyboard
        for key in KEYS:
            self._screen.onkeypress(self._create_lambda('keydown', key), key);
            self._screen.onkeyrelease(self._create_lambda('keyup', key), key);

            # custom implemented keypress
            self._onkeytype(self._create_lambda('keypress', key), key);

        # Mouse
        for btn in BUTTONS:
            self._screen.onclick(self._create_lambda('mousedown', btn), btn);  # mousedown
            self._onrelease(self._create_lambda('mouseup', btn), btn);
            self._ondrag(self._create_lambda('mousedrag', btn), btn);

            # custom implemented mouseclick
            self._onmouseclick(self._create_lambda('mouseclick', btn), btn);

        self._screen.cv.bind("<Motion>", (self._create_lambda('mousemove', None)))

    class Key:
        def __init__(self, key: str):
            self._key = key;

        def key(self) -> str:
            """
            Returns the string for the key.
            :return: the key in ascii
            """
            return self._key;

        def __repr__(self):
            return self.key();

        def __str__(self):
            return self.key();

        def __add__(self, other):
            return str(self) + other

        def __radd__(self, other):
            return other + str(self)

        def __eq__(self, obj) -> bool:
            """
            Overrides the equals operator so that we can compare with strings! Fantastic!
            :param obj: the object to compare to
            :return: if the key is equal to the object.
            """
            if type(obj) is self.__class__:
                return obj.key() == self.key();
            elif type(obj) is str:
                return obj.lower() == self.key().lower();
            else:
                return False;

    def _create_lambda(self, method: str, key):
        """
        A super-cool method to create lambdas for key-event registration.
        :param key: the key to create the lambda for
        :return: A lambda (😻) [ignore the cat]
        """

        if method == 'keydown':
            return lambda: (self._keydown(key));
        elif method == 'keyup':
            return lambda: (self._keyup(key));
        elif method == 'mousedown':
            return lambda x, y: (self._mousedown(key, self.create_location(x, y)));
        elif method == 'mouseup':
            return lambda x, y: (self._mouseup(key, self.create_location(x, y)));
        elif method == 'mousedrag':
            return lambda x, y: (self._mousedrag(key, self.create_location(x, y)));
        elif method == 'mousemove':
            return lambda event: (self._mousemove(Location(event.x, event.y)));
        else:
            return None;

    def _keydown(self, key) -> None:
        if 'keydown' not in self.registry:
            return;

        self.registry['keydown'](self.Key(key.lower()));

    def _keyup(self, key) -> None:
        if 'keyup' not in self.registry:
            return;

        self.registry['keyup'](self.Key(key.lower()));

    def _keypress(self, key) -> None:
        if 'keypress' not in self.registry:
            return;

        self.registry['keypress'](self.Key(key.lower()));

    def _mousedown(self, button, location) -> None:
        if 'mousedown' not in self.registry:
            return;

        self.registry['mousedown'](button, location);

    def _mouseup(self, button, location) -> None:
        if 'mouseup' not in self.registry:
            return;

        self.registry['mouseup'](button, location);

    def _mouseclick(self, button, location) -> None:
        if 'mouseclick' not in self.registry:
            return;

        self.registry['mouseclick'](button, location);

    def _mousedrag(self, button, location) -> None:
        if 'mousedrag' not in self.registry:
            return;

        self.registry['mousedrag'](button, location);

    def _mousemove(self, location) -> None:
        # We will update our internal storage of the mouse-location no matter what
        self._mouse = location;

        if 'mousemove' not in self.registry:
            return;

        self.registry['mousemove'](location);

    # --- Helper Methods --- #
    def create_location(self, x, y) -> Location:
        """
        Is passed turtle-based coordinates and converts them into normal coordinates
        :param x: the x component
        :param y: the y component
        :return: a location comprised of the passed x and y components
        """
        return Location(x + (self.width() / 2), -y + (self.height() / 2));

    def canvas_location(self, x, y) -> Location:
        return Location(x - self.width() / 2, y - self.height() / 2);

    # -- Internals -- #
    def _onrelease(self, fun, btn, add=None):
        """
        An internal method hooking into the TKinter canvas.
        :param fun: the function to call upon mouse release
        :param btn: the mouse button to bind to
        :param add: i have no clue what this does
        :return: None
        """

        def eventfun(event):
            x, y = (self._screen.cv.canvasx(event.x) / self._screen.xscale,
                    -self._screen.cv.canvasy(event.y) / self._screen.yscale)
            fun(x, y)

        self._screen.cv.bind("<Button%s-ButtonRelease>" % btn, eventfun, add);

    def _ondrag(self, fun, btn, add=None):
        """
        An internal method hooking into the TKinter canvas.
        :param fun: the function to call upon drag
        :param btn: the mouse button to bind to
        :param add: i have no clue
        :return: None
        """

        # noinspection PyBroadException
        def eventfun(event):
            try:
                x, y = (self._screen.cv.canvasx(event.x) / self._screen.xscale,
                        -self._screen.cv.canvasy(event.y) / self._screen.yscale)
                fun(x, y)
            except Exception:
                pass

        self._screen.cv.bind("<Button%s-Motion>" % btn, eventfun, add);

    def _onmouseclick(self, fun, btn, add=None):
        pass;

    def _onkeytype(self, fun, btn, add=None):
        pass;


"""
Objects in the PyDraw library

(Author: Noah Coetsee)
"""

# import turtle;
import tkinter as tk;
import math;
from typing import Union;
# import asyncio;

# # from pydraw.errors import *;  # util gives us our errors for us :)
# from pydraw.util import *;

# from pydraw import Screen;
# from pydraw import Location;
# from pydraw import Color;

PIXEL_RATIO = 20;


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
        self._fill = fill;
        self._angle = rotation;
        self._rotations = {};
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

    def center(self) -> Location:
        """
        Returns the location of the center
        :return: Location object representing center of Renderable
        """

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

        # return Location(self.x() + self.width() / 2, self.y() + self.height() / 2);

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

        return self._angle;

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the object by a difference, in degrees
        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        verify(angle_diff, (float, int));
        self.rotation(self._angle + angle_diff);

    def lookat(self, obj):
        if isinstance(obj, Object):
            obj = obj.location();
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError('Renderable#lookat() must be passed either a renderable or a location!')

        location = Location(obj[0], obj[1]);

        theta = math.atan2(location.y() - self.y(), location.x() - self.x()) - math.radians(self.rotation());
        theta = math.degrees(theta);

        self.rotate(theta);

    def border(self, color: Color = None, fill: bool = None) -> Color:
        """
        Add or get the border of the object
        :param color: the color to set the border too, set to Color.NONE to remove border
        :param fill: whether or not to fill the polygon.
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

        if update:
            self.update();

        return self._border;

    def fill(self, fill: bool = None) -> bool:
        """
        Returns or sets the current fill boolean
        :param fill: a new fill value, whether or not to fill the polygon
        :return: the fill value
        """

        if fill is not None:
            verify(fill, bool);
            self._fill = fill;
            self.update();

        return self._fill;

    def distance(self, obj) -> float:
        """
        Returns the distance between two objs or locations in pixels
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

    def contains(self, *args) -> bool:
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
                raise InvalidArgumentError('Passed arguments must be numbers (x, y), '
                                           'or you may pass a location/tuple.');
            x = args[0];
            y = args[1];
        else:
            raise InvalidArgumentError('You must pass in a tuple, Location, or two numbers (x, y)!');

        # If the point isn't remotely near us, we don't need to perform any calculations.
        if not isinstance(self, CustomRenderable) and self._angle == 0:
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

    def overlaps(self, renderable) -> bool:
        """
        Returns if this object is overlapping with the passed object.
        :param renderable: another Renderable instance.
        :return: true if they are overlapping, false if not.
        """

        if not isinstance(renderable, Renderable):
            raise TypeError('Passed non-renderable into Renderable#overlaps(), which takes only Renderables!');

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
            return True;

        if (min_bx >= min_ax and max_bx <= max_ax) and (min_by >= min_ay and max_by <= max_ay):
            return True;

        # Next we are going to use a sweeping line algorithm.
        # Essentially we will process the lines on the x axis, one coordinate at a time (imagine a vertical line scan).
        # Then we will look for their orientations. We will essentially make sure its impossible they do not cross.
        shape1 = self.vertices();

        # noinspection PyProtectedMember
        shape2 = renderable.vertices();

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

        min_distance = 999999;
        top_left_index = 0;
        for i, location in enumerate(real_shape):
            distance = math.sqrt((location.x()) ** 2 + (location.y()) ** 2);
            if distance < min_distance:
                min_distance = distance;
                top_left_index = i;

        real_shape = real_shape[top_left_index:] + real_shape[:top_left_index];
        real_shape.reverse();

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
            state=state
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
                state=state
            );

            self._screen._canvas.tag_lower(self._ref, old_ref);
            self._screen._canvas.delete(old_ref);
        except:
            pass;


class CustomRenderable(Renderable):
    """
    A wrapper class to distintify classes that wrap turtle and those that are built on tkinter.
    """
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

    def center(self) -> Location:
        """
        Returns the centroid for the CustomPolygon
        :return: centroid in the form of a Location
        """

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
            state=state
        );

        self._screen._screen.cv.tag_lower(self._ref, old_ref);
        self._screen._screen.cv.delete(old_ref);


class Rectangle(Renderable):
    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height), Location(x, y + height)];
        self._shape = ((10, -10), (10, 10), (-10, 10), (-10, -10));
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);


class Oval(Renderable):
    _default = ((10, 0), (9.51, 3.09), (8.09, 5.88),
                (5.88, 8.09), (3.09, 9.51), (0, 10), (-3.09, 9.51),
                (-5.88, 8.09), (-8.09, 5.88), (-9.51, 3.09), (-10, 0),
                (-9.51, -3.09), (-8.09, -5.88), (-5.88, -8.09),
                (-3.09, -9.51), (-0.00, -10.00), (3.09, -9.51),
                (5.88, -8.09), (8.09, -5.88), (9.51, -3.09));

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
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
    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible);


class Polygon(Renderable):
    def __init__(self, screen: Screen, num_sides: int, x: float = 0, y: float = 0, width: float = 10,
                 height: float = 10,
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
            state=state
        );

    def update(self):
        old_ref = self._ref;
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

        # noinspection PyAttributeOutsideInit
        self._vertices = self._rotate(self._vertices, self._angle);

        tk_vertices = [];  # we need to convert to tk's coordinate system.
        for vertex in vertices:
            tk_vertices.append((vertex.x() - (self._screen.width() / 2),
                                (vertex.y() - (self._screen.height() / 2))));

        state = tk.NORMAL if self._visible else tk.HIDDEN;

        try:
            # noinspection PyProtectedMember
            self._ref = self._screen._canvas.create_polygon(
                tk_vertices,
                fill=self._screen._colorstr(self._color),
                outline=self._screen._screen._colorstr(self._border.__value__()),
                state=state
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

    def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        self._image_name = image;
        filetype = image[len(image) - 4:len(image)];

        if filetype in self.TKINTER_TYPES:
            self._image = tk.PhotoImage(name=image, file=image);
        else:
            try:
                from PIL import Image, ImageTk;
                image = Image.open(self._image_name);
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
                         rotation=rotation, visible=visible, location=location);

        if width is not None:
            self.width(width);
        if height is not None:
            self.height(height);

        if color is not None:
            self.color(color);

        if border is not None:
            self.border(border);

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

    def frames(self):
        """
        Returns how many frames there are, returns -1 if not animated, 0 if corrupted file.
        :return:
        """

        self._frames;

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
    def _setup(self):
        real_location = self._screen.canvas_location(self.x(), self.y());
        self._ref = self._screen._canvas.create_image(real_location.x() + self._width / 2,
                                                      real_location.y() + self._height / 2, image=self._image);

    # noinspection PyProtectedMember
    def update(self, updated: bool = False):
        if updated:
            try:
                from PIL import Image, ImageTk, ImageOps;

                if not self._patched:
                    self._monkey_patch_del();  # If we do have PIL we need to monkey patch this immediately.
                    self._patched = True;

                image = Image.open(self._image_name);

                if self._frame != -1:
                    try:
                        image.seek(self._frame);
                    except EOFError:
                        raise PydrawError('No more images in GIF File!');

                image = image.convert('RGBA');

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
                image = image.resize((self.width(), self.height()), Image.ANTIALIAS);

                if self._angle != 0:
                    image = image.rotate(-self._angle, resample=Image.BILINEAR, expand=1, fillcolor=None)

                self._image = ImageTk.PhotoImage(image=image);
            except (RuntimeError, AttributeError):
                pass;  # We are catching some stupid errors from Tkinter involving images and program exiting.
            except:
                raise UnsupportedError('As PIL is not installed, you cannot modify images! '
                                       'Install Pillow via: \'pip install pillow\'.');

        try:
            old_ref = self._ref;
            real_location = self._screen.canvas_location(self.x(), self.y());

            self._ref = self._screen._canvas.create_image(real_location.x() + self._width / 2,
                                                          real_location.y() + self._height / 2, image=self._image);

            self._screen._canvas.tag_lower(self._ref, old_ref);
            self._screen._canvas.delete(old_ref);
        except tk.TclError:
            pass;


# While technically this is a normal renderable, I've grouped it with the
# CustomRenderables due to its special-case dependency on PIP.
# class Image(Renderable):
#     """
#     Image class. Supports basic formats: PNG, GIF, JPG, PPM, images.
#
#     NOTE: This class supports the basic displaying of images, but also supports much more,
#     such as image modification (width, height, color, etc) if you have PIL (Pillow) installed!
#     You can install PIL/Pillow by running: `pip install pillow` in a terminal!
#     """
#
#     TKINTER_TYPES = ['.png', '.gif', '.ppm'];
#
#     def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
#                  width: float = None,
#                  height: float = None,
#                  color: Color = None,
#                  border: Color = None,
#                  rotation: float = 0,
#                  visible: bool = True,
#                  location: Location = None):
#         self._image_name = image;
#
#         if image[len(image) - 4:len(image)] in self.TKINTER_TYPES:
#             self._image = tk.PhotoImage(name=image, file=image);
#         else:
#             try:
#                 from PIL import Image, ImageTk;
#                 image = Image.open(self._image_name);
#                 self._image = ImageTk.PhotoImage(image);
#             except:
#                 raise UnsupportedError('As PIL is not installed, only .png, .gif, and .ppm images are supported! '
#                                        'Install Pillow via: \'pip install pillow\'.');
#
#         self._width = self._image.width();
#         self._height = self._image.height();
#
#         self._mask = 123;
#
#         # We have to monkey patch PIL if we modify the image, but we don't wanna cause a RecursionError (call once)
#         self._patched = False;
#
#         shape = turtle.Shape('image', self._image);
#
#         # noinspection PyProtectedMember
#         screen._screen.register_shape(self._image_name, shape);
#
#         super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=None,
#                          rotation=rotation, visible=visible, location=location);
#         self._ref.shape(self._image_name);
#
#         if width is not None:
#             self.width(width);
#         if height is not None:
#             self.height(height);
#
#         if color is not None:
#             self.color(color);
#
#         if border is not None:
#             self.border(border);
#
#     def width(self, width: float = None) -> float:
#         """
#         Get or set the width of the image (REQUIRES: PIL or Pillow)
#         :param width: the width to set to, if any
#         :return: None
#         """
#
#         if width is not None:
#             verify(width, (float, int));
#             self._width = width;
#             self.update(True);
#
#         return self._width;
#
#     def height(self, height: float = None) -> float:
#         """
#         Get or set the height of the image
#         :param height: the height to set to, if any
#         :return: the height
#         """
#
#         if height is not None:
#             verify(height, (float, int));
#             self._height = height;
#             self.update(True);
#
#         return self._height;
#
#     def color(self, color: Color = None, alpha: int = 123) -> Color:
#         """
#         Retrieves or applies a color-mask to the image
#         :param color: the color to mask to, if any
#         :param alpha: The alpha level of the mask, defaults to 123 (half of 255)
#         :return: the mask-color of the object
#         """
#
#         if color is not None:
#             verify(color, Color);
#             self._color = color;
#             self._mask = alpha;
#             self.update(True);
#
#         return self._color;
#
#     def rotation(self, angle: float = None) -> float:
#         """
#         Get or set the rotation of the image.
#         :param angle: the angle to set the rotation to in degrees, if any
#         :return: the angle of the image's rotation in degrees
#         """
#
#         if angle is not None:
#             verify(angle, (float, int));
#             self._angle = angle;
#             self.update(True);
#
#         return self._angle;
#
#     # noinspection PyMethodOverriding
#     def rotate(self, angle_diff: float) -> None:
#         """
#         Rotate the angle of the image by a difference, in degrees
#         :param angle_diff: the angle difference to rotate by
#         :return: None
#         """
#
#         if angle_diff != 0:
#             verify(angle_diff, (float, int));
#             self._angle += angle_diff;
#             self.update(True);
#
#     # noinspection PyMethodOverriding
#     def border(self, color: Color = None) -> Color:
#         """
#         Add or get the border of the image
#         :param color: the color to set the border too, set to Color.NONE to remove border
#         :return: The Color of the border
#         """
#
#         if color is not None:
#             verify(color, Color);
#             self._border = color;
#             self.update(True);
#
#         return self._border;
#
#     def fill(self, fill: bool = None) -> bool:
#         """
#         Unsupported: This doesn't make sense for images.
#         """
#
#         raise UnsupportedError('This method is not supported for Images!');
#
#     def vertices(self) -> list:
#         """
#         Returns the list of vertices for the Renderable.
#         (The vertices will be returned clockwise, starting from the top-leftmost point)
#         :return: a list of Locations representing the vertices
#         """
#
#         vertices = [self.location(), Location(self.x() + self.width(), self.y()),
#                     Location(self.x() + self.width(), self.y() + self.height()),
#                     Location(self.x(), self.y() + self.height())];
#
#         if self._angle != 0:
#
#             # First get some values that we gonna use later
#             theta = math.radians(self._angle);
#             cosine = math.cos(theta);
#             sine = math.sin(theta);
#
#             center_x = self.center().x();
#             center_y = self.center().y();
#
#             new_vertices = []
#             for vertex in vertices:
#                 # We have to create these separately because they're ironically used in each others calculations xD
#                 old_x = vertex.x() - center_x;
#                 old_y = vertex.y() - center_y;
#
#                 new_x = (old_x * cosine - old_y * sine) + center_x;
#                 new_y = (old_x * sine + old_y * cosine) + center_y;
#                 new_vertices.append(Location(new_x, new_y));
#
#             vertices = new_vertices;
#
#         return vertices;
#
#     @staticmethod
#     def _monkey_patch_del():
#         """
#         We monkey patch the del function for PIL so it doesn't do stupid things.
#         :return:
#         """
#         from PIL import ImageTk;
#
#         # monkey patch TKinter from this dumb bug they don't catch in TK.PhotoImage
#         old_del = ImageTk.PhotoImage.__del__;
#
#         def new_del(self):
#             try:
#                 old_del(self)
#             except (AttributeError, RecursionError):
#                 pass;  # Yeah, we don't care.
#             pass;
#
#         ImageTk.PhotoImage.__del__ = new_del
#
#     def update(self, updated: bool = False):
#         if updated:
#             try:
#                 from PIL import Image, ImageTk, ImageOps;
#
#                 if not self._patched:
#                     self._monkey_patch_del();  # If we do have PIL we need to monkey patch this immediately.
#                     self._patched = True;
#
#                 image = Image.open(self._image_name).convert('RGBA');
#
#                 if self._color is not None and self._color != Color.NONE:
#                     r, g, b, alpha = image.split()
#                     gray = ImageOps.grayscale(image)
#                     result = ImageOps.colorize(gray, (0, 0, 0, 0),
#                                                (
#                                                    self._color.red(), self._color.green(), self._color.blue(),
#                                                    self._mask));
#                     result.putalpha(alpha);
#                     image = result;
#
#                 if self._border is not None:
#                     image = ImageOps.expand(image, border=10, fill=self._border.rgb())
#
#                 # Do resizing last so we can make sure the other manipulations work properly
#                 image = image.resize((self.width(), self.height()), Image.ANTIALIAS);
#
#                 if self._angle != 0:
#                     image = image.rotate(-self._angle, resample=Image.BILINEAR, expand=1, fillcolor=None)
#
#                 self._image = ImageTk.PhotoImage(image=image);
#             except (RuntimeError, AttributeError):
#                 pass;  # We are catching some stupid errors from Tkinter involving images and program exiting.
#             except:
#                 raise UnsupportedError('As PIL is not installed, you cannot modify images! '
#                                        'Install Pillow via: \'pip install pillow\'.');
#
#         try:
#             shape = turtle.Shape('image', self._image);
#
#             # noinspection PyProtectedMember
#             self._screen._screen.register_shape(self._image_name, shape);
#             self._ref.shape(self._image_name);
#         except tk.TclError:
#             pass;
#         super().update();


class Text(CustomRenderable):
    _anchor = 'nw';  # sw technically means southwest but it means bottom left anchor. (we change to top left in code)
    _aligns = {'left': tk.LEFT, 'center': tk.CENTER, 'right': tk.RIGHT};

    # noinspection PyProtectedMember
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

        import tkinter.font as tkfont;

        font = tkfont.Font(font=font_data);
        true_width = font.measure(self._text);
        true_height = font.metrics('linespace');

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
        Get or set the text. Use '\n' to separate lines.
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

        theta = math.atan2(location.y() - self.y(), location.x() - self.x()) - math.radians(self.rotation());
        theta = math.degrees(theta) + 90;

        self.rotate(theta);

    def vertices(self) -> list:
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
            import tkinter.font as tkfont;

            font = tkfont.Font(font=font_data);
            true_width = font.measure(self._text);
            true_height = font.metrics('linespace');

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
        Retrive or enable/disable the dashes for the line
        :param dashes: the visibility to set to, if any
        :return: the toggle-state of dashes
        """

        if dashes is not None:
            verify(dashes, int);
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

    # noinspection PyProtectedMember
    def update(self):
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

            self._screen._screen.cv.update();
        except tk.TclError:
            pass;  # Just catch TclErrors and throw them out.


