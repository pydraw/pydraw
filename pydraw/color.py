import turtle;
import tkinter as tk;
from pydraw.errors import *;


class Color:
    """
    An immutable class that contains a color values, usually by name or RGB.
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
        Get the green property
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
            except turtle.Terminator:
                return 255, 255, 255;  # Just return black if Program is shutting down.
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
