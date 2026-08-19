from pydraw.errors import *
from typing import Tuple, Union, cast, overload as _overload


class Color:
    """
    An immutable class that contains a color values, usually by name or RGB.
    """

    NONE = None

    @_overload
    def __init__(self, __name: str) -> None: ...

    @_overload
    def __init__(self, __rgb: Tuple[int, int, int]) -> None: ...

    @_overload
    def __init__(self, __r: int, __g: int, __b: int) -> None: ...

    def __init__(self, *args):
        if len(args) == 0 or len(args) == 2 or len(args) > 3:
            raise NameError('Invalid arguments passed to color!')

        self._name = None
        self._hex_value = None

        # we should expect three arguments for RGB
        if len(args) >= 3:
            for arg in args:
                if type(arg) is not int:
                    raise NameError('Expected integer arguments, but found \'' + str(arg) + '\' instead.')

            self._r = args[0]
            self._g = args[1]
            self._b = args[2]

            self._mode = 0
        elif len(args) == 1:
            if type(args[0]) is tuple:
                if len(args[0]) != 3:
                    raise InvalidArgumentError(
                        'Color(): RGB tuples must contain exactly three values (R, G, B).'
                    )

                for arg in args[0]:
                    if type(arg) is not int:
                        raise NameError('Expected integer arguments, but found \'' + str(arg) + '\' instead.')

                self._r = args[0][0]
                self._g = args[0][1]
                self._b = args[0][2]

                self._mode = 0
                return  # done: don't fall through into name/hex string parsing
            elif type(args[0]) is not str:
                raise NameError('Expected string but instead found: ' + str(args[0]))

            string = str(args[0])
            if string.startswith('#'):
                self._hex_value = string
                self._mode = 2

                rgb = self._rgb(self)
                self._r = int(rgb[0])
                self._g = int(rgb[1])
                self._b = int(rgb[2])
            else:
                self._name = string
                self._mode = 1

                if self._name == '':
                    self._r, self._g, self._b = -1, -1, -1
                else:
                    # Resolve named colors from a baked-in table
                    rgb = _COLOR_TABLE.get(self._name.strip().lower().replace(' ', ''))
                    if rgb is not None:
                        self._r, self._g, self._b = rgb
                    else:
                        rgb = self._rgb(self)
                        self._r = int(rgb[0] / 256)
                        self._g = int(rgb[1] / 256)
                        self._b = int(rgb[2] / 256)

    def __value__(self) -> Union[Tuple[int, int, int], str]:
        """
        Retrieve the original color representation.

        :return:
        """
        if self._mode == 0:
            return self.red(), self.green(), self.blue()
        elif self._mode == 1:
            return cast(str, self._name)
        else:
            return cast(str, self._hex_value)

    def red(self):
        """
        Get the red property.

        :return: r
        """
        return self._r

    def green(self):
        """
        Get the green property

        :return: g
        """
        return self._g

    def blue(self):
        """
        Get the blue property

        :return: b
        """
        return self._b

    def rgb(self):
        """
        Get the RGB tuple

        :return: tuple (R, G, B)
        """
        return self.red(), self.green(), self.blue()

    def name(self):
        """
        Get the name of the color (only if defined)

        :return: color or None
        """

        return self._name

    def hex(self):
        """
        Get the hex of the color (only if defined)

        :return: hex_value or None
        """
        return self._hex_value

    def clone(self):
        """
        Clone this color!

        :return: a clone.
        """

        return Color(self.__value__())

    def __str__(self):
        if self._mode == 0:
            string = f'({self._r, self._g, self._b})'
        elif self._mode == 1:
            string = self._name
        else:
            string = self._hex_value

        return string

    def __eq__(self, other):
        if type(other) is not Color:
            return False

        return other.rgb() == self.rgb()

    def __hash__(self):
        return hash(self.rgb())

    @staticmethod
    def _rgb(color) -> tuple:
        """
        Convert a color to an rgb tuple.

        :param color: the color to convert
        :return: a tuple representing RGB
        """

        if color.name() is not None:
            raise PydrawError(f"Color(): unknown color name '{color.name()}'.")
        elif color.hex() is not None:
            hexval = color.hex().replace('#', '')

            if len(hexval) != 6:
                if len(hexval) == 3:
                    hexval = ''.join([char * 2 for char in hexval])  # Optimized string manipulation.
                else:
                    raise InvalidArgumentError(
                        "Color(): hex values must contain three or six characters "
                        "(for example, '#FFF' or '#FFFFFF')."
                    )

            rgb = tuple(int(hexval[i:i + 2], 16) for i in (0, 2, 4))
        else:
            rgb = (color.red(), color.green(), color.blue())

        return rgb

    @staticmethod
    def all():
        """
        Get all color values that have a string-name.

        :return: a tuple (immutable list) of all Colors.
        """

        return tuple(COLORS.copy())

    @staticmethod
    def random():
        """
        Retrieve a random Color.

        :return: returns
        """

        import random
        return random.choice(COLORS).clone()

    def __repr__(self):
        return self.__str__()


Color.NONE = Color('')

# Static normalized-name -> (r, g, b) table (0-255) covering Tk's full color
# database, generated via winfo_rgb. Keys are lowercased with spaces stripped.
_COLOR_TABLE = {
    'aliceblue': (240, 248, 255),
    'antiquewhite': (250, 235, 215),
    'antiquewhite1': (255, 239, 219),
    'antiquewhite2': (238, 223, 204),
    'antiquewhite3': (205, 192, 176),
    'antiquewhite4': (139, 131, 120),
    'aquamarine': (127, 255, 212),
    'aquamarine1': (127, 255, 212),
    'aquamarine2': (118, 238, 198),
    'aquamarine3': (102, 205, 170),
    'aquamarine4': (69, 139, 116),
    'azure': (240, 255, 255),
    'azure1': (240, 255, 255),
    'azure2': (224, 238, 238),
    'azure3': (193, 205, 205),
    'azure4': (131, 139, 139),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'bisque1': (255, 228, 196),
    'bisque2': (238, 213, 183),
    'bisque3': (205, 183, 158),
    'bisque4': (139, 125, 107),
    'black': (0, 0, 0),
    'blanchedalmond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blue1': (0, 0, 255),
    'blue2': (0, 0, 238),
    'blue3': (0, 0, 205),
    'blue4': (0, 0, 139),
    'blueviolet': (138, 43, 226),
    'brown': (165, 42, 42),
    'brown1': (255, 64, 64),
    'brown2': (238, 59, 59),
    'brown3': (205, 51, 51),
    'brown4': (139, 35, 35),
    'burlywood': (222, 184, 135),
    'burlywood1': (255, 211, 155),
    'burlywood2': (238, 197, 145),
    'burlywood3': (205, 170, 125),
    'burlywood4': (139, 115, 85),
    'cadetblue': (95, 158, 160),
    'cadetblue1': (152, 245, 255),
    'cadetblue2': (142, 229, 238),
    'cadetblue3': (122, 197, 205),
    'cadetblue4': (83, 134, 139),
    'chartreuse': (127, 255, 0),
    'chartreuse1': (127, 255, 0),
    'chartreuse2': (118, 238, 0),
    'chartreuse3': (102, 205, 0),
    'chartreuse4': (69, 139, 0),
    'chocolate': (210, 105, 30),
    'chocolate1': (255, 127, 36),
    'chocolate2': (238, 118, 33),
    'chocolate3': (205, 102, 29),
    'chocolate4': (139, 69, 19),
    'coral': (255, 127, 80),
    'coral1': (255, 114, 86),
    'coral2': (238, 106, 80),
    'coral3': (205, 91, 69),
    'coral4': (139, 62, 47),
    'cornflowerblue': (100, 149, 237),
    'cornsilk': (255, 248, 220),
    'cornsilk1': (255, 248, 220),
    'cornsilk2': (238, 232, 205),
    'cornsilk3': (205, 200, 177),
    'cornsilk4': (139, 136, 120),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'cyan1': (0, 255, 255),
    'cyan2': (0, 238, 238),
    'cyan3': (0, 205, 205),
    'cyan4': (0, 139, 139),
    'darkblue': (0, 0, 139),
    'darkcyan': (0, 139, 139),
    'darkgoldenrod': (184, 134, 11),
    'darkgoldenrod1': (255, 185, 15),
    'darkgoldenrod2': (238, 173, 14),
    'darkgoldenrod3': (205, 149, 12),
    'darkgoldenrod4': (139, 101, 8),
    'darkgray': (169, 169, 169),
    'darkgreen': (0, 100, 0),
    'darkgrey': (169, 169, 169),
    'darkkhaki': (189, 183, 107),
    'darkmagenta': (139, 0, 139),
    'darkolivegreen': (85, 107, 47),
    'darkolivegreen1': (202, 255, 112),
    'darkolivegreen2': (188, 238, 104),
    'darkolivegreen3': (162, 205, 90),
    'darkolivegreen4': (110, 139, 61),
    'darkorange': (255, 140, 0),
    'darkorange1': (255, 127, 0),
    'darkorange2': (238, 118, 0),
    'darkorange3': (205, 102, 0),
    'darkorange4': (139, 69, 0),
    'darkorchid': (153, 50, 204),
    'darkorchid1': (191, 62, 255),
    'darkorchid2': (178, 58, 238),
    'darkorchid3': (154, 50, 205),
    'darkorchid4': (104, 34, 139),
    'darkred': (139, 0, 0),
    'darksalmon': (233, 150, 122),
    'darkseagreen': (143, 188, 143),
    'darkseagreen1': (193, 255, 193),
    'darkseagreen2': (180, 238, 180),
    'darkseagreen3': (155, 205, 155),
    'darkseagreen4': (105, 139, 105),
    'darkslateblue': (72, 61, 139),
    'darkslategray': (47, 79, 79),
    'darkslategray1': (151, 255, 255),
    'darkslategray2': (141, 238, 238),
    'darkslategray3': (121, 205, 205),
    'darkslategray4': (82, 139, 139),
    'darkslategrey': (47, 79, 79),
    'darkturquoise': (0, 206, 209),
    'darkviolet': (148, 0, 211),
    'deeppink': (255, 20, 147),
    'deeppink1': (255, 20, 147),
    'deeppink2': (238, 18, 137),
    'deeppink3': (205, 16, 118),
    'deeppink4': (139, 10, 80),
    'deepskyblue': (0, 191, 255),
    'deepskyblue1': (0, 191, 255),
    'deepskyblue2': (0, 178, 238),
    'deepskyblue3': (0, 154, 205),
    'deepskyblue4': (0, 104, 139),
    'dimgray': (105, 105, 105),
    'dimgrey': (105, 105, 105),
    'dodgerblue': (30, 144, 255),
    'dodgerblue1': (30, 144, 255),
    'dodgerblue2': (28, 134, 238),
    'dodgerblue3': (24, 116, 205),
    'dodgerblue4': (16, 78, 139),
    'firebrick': (178, 34, 34),
    'firebrick1': (255, 48, 48),
    'firebrick2': (238, 44, 44),
    'firebrick3': (205, 38, 38),
    'firebrick4': (139, 26, 26),
    'floralwhite': (255, 250, 240),
    'forestgreen': (34, 139, 34),
    'gainsboro': (220, 220, 220),
    'ghostwhite': (248, 248, 255),
    'gold': (255, 215, 0),
    'gold1': (255, 215, 0),
    'gold2': (238, 201, 0),
    'gold3': (205, 173, 0),
    'gold4': (139, 117, 0),
    'goldenrod': (218, 165, 32),
    'goldenrod1': (255, 193, 37),
    'goldenrod2': (238, 180, 34),
    'goldenrod3': (205, 155, 29),
    'goldenrod4': (139, 105, 20),
    'gray': (128, 128, 128),
    'gray0': (0, 0, 0),
    'gray1': (3, 3, 3),
    'gray10': (26, 26, 26),
    'gray100': (255, 255, 255),
    'gray11': (28, 28, 28),
    'gray12': (31, 31, 31),
    'gray13': (33, 33, 33),
    'gray14': (36, 36, 36),
    'gray15': (38, 38, 38),
    'gray16': (41, 41, 41),
    'gray17': (43, 43, 43),
    'gray18': (46, 46, 46),
    'gray19': (48, 48, 48),
    'gray2': (5, 5, 5),
    'gray20': (51, 51, 51),
    'gray21': (54, 54, 54),
    'gray22': (56, 56, 56),
    'gray23': (59, 59, 59),
    'gray24': (61, 61, 61),
    'gray25': (64, 64, 64),
    'gray26': (66, 66, 66),
    'gray27': (69, 69, 69),
    'gray28': (71, 71, 71),
    'gray29': (74, 74, 74),
    'gray3': (8, 8, 8),
    'gray30': (77, 77, 77),
    'gray31': (79, 79, 79),
    'gray32': (82, 82, 82),
    'gray33': (84, 84, 84),
    'gray34': (87, 87, 87),
    'gray35': (89, 89, 89),
    'gray36': (92, 92, 92),
    'gray37': (94, 94, 94),
    'gray38': (97, 97, 97),
    'gray39': (99, 99, 99),
    'gray4': (10, 10, 10),
    'gray40': (102, 102, 102),
    'gray41': (105, 105, 105),
    'gray42': (107, 107, 107),
    'gray43': (110, 110, 110),
    'gray44': (112, 112, 112),
    'gray45': (115, 115, 115),
    'gray46': (117, 117, 117),
    'gray47': (120, 120, 120),
    'gray48': (122, 122, 122),
    'gray49': (125, 125, 125),
    'gray5': (13, 13, 13),
    'gray50': (127, 127, 127),
    'gray51': (130, 130, 130),
    'gray52': (133, 133, 133),
    'gray53': (135, 135, 135),
    'gray54': (138, 138, 138),
    'gray55': (140, 140, 140),
    'gray56': (143, 143, 143),
    'gray57': (145, 145, 145),
    'gray58': (148, 148, 148),
    'gray59': (150, 150, 150),
    'gray6': (15, 15, 15),
    'gray60': (153, 153, 153),
    'gray61': (156, 156, 156),
    'gray62': (158, 158, 158),
    'gray63': (161, 161, 161),
    'gray64': (163, 163, 163),
    'gray65': (166, 166, 166),
    'gray66': (168, 168, 168),
    'gray67': (171, 171, 171),
    'gray68': (173, 173, 173),
    'gray69': (176, 176, 176),
    'gray7': (18, 18, 18),
    'gray70': (179, 179, 179),
    'gray71': (181, 181, 181),
    'gray72': (184, 184, 184),
    'gray73': (186, 186, 186),
    'gray74': (189, 189, 189),
    'gray75': (191, 191, 191),
    'gray76': (194, 194, 194),
    'gray77': (196, 196, 196),
    'gray78': (199, 199, 199),
    'gray79': (201, 201, 201),
    'gray8': (20, 20, 20),
    'gray80': (204, 204, 204),
    'gray81': (207, 207, 207),
    'gray82': (209, 209, 209),
    'gray83': (212, 212, 212),
    'gray84': (214, 214, 214),
    'gray85': (217, 217, 217),
    'gray86': (219, 219, 219),
    'gray87': (222, 222, 222),
    'gray88': (224, 224, 224),
    'gray89': (227, 227, 227),
    'gray9': (23, 23, 23),
    'gray90': (229, 229, 229),
    'gray91': (232, 232, 232),
    'gray92': (235, 235, 235),
    'gray93': (237, 237, 237),
    'gray94': (240, 240, 240),
    'gray95': (242, 242, 242),
    'gray96': (245, 245, 245),
    'gray97': (247, 247, 247),
    'gray98': (250, 250, 250),
    'gray99': (252, 252, 252),
    'green': (0, 128, 0),
    'green1': (0, 255, 0),
    'green2': (0, 238, 0),
    'green3': (0, 205, 0),
    'green4': (0, 139, 0),
    'greenyellow': (173, 255, 47),
    'grey': (128, 128, 128),
    'grey0': (0, 0, 0),
    'grey1': (3, 3, 3),
    'grey10': (26, 26, 26),
    'grey100': (255, 255, 255),
    'grey11': (28, 28, 28),
    'grey12': (31, 31, 31),
    'grey13': (33, 33, 33),
    'grey14': (36, 36, 36),
    'grey15': (38, 38, 38),
    'grey16': (41, 41, 41),
    'grey17': (43, 43, 43),
    'grey18': (46, 46, 46),
    'grey19': (48, 48, 48),
    'grey2': (5, 5, 5),
    'grey20': (51, 51, 51),
    'grey21': (54, 54, 54),
    'grey22': (56, 56, 56),
    'grey23': (59, 59, 59),
    'grey24': (61, 61, 61),
    'grey25': (64, 64, 64),
    'grey26': (66, 66, 66),
    'grey27': (69, 69, 69),
    'grey28': (71, 71, 71),
    'grey29': (74, 74, 74),
    'grey3': (8, 8, 8),
    'grey30': (77, 77, 77),
    'grey31': (79, 79, 79),
    'grey32': (82, 82, 82),
    'grey33': (84, 84, 84),
    'grey34': (87, 87, 87),
    'grey35': (89, 89, 89),
    'grey36': (92, 92, 92),
    'grey37': (94, 94, 94),
    'grey38': (97, 97, 97),
    'grey39': (99, 99, 99),
    'grey4': (10, 10, 10),
    'grey40': (102, 102, 102),
    'grey41': (105, 105, 105),
    'grey42': (107, 107, 107),
    'grey43': (110, 110, 110),
    'grey44': (112, 112, 112),
    'grey45': (115, 115, 115),
    'grey46': (117, 117, 117),
    'grey47': (120, 120, 120),
    'grey48': (122, 122, 122),
    'grey49': (125, 125, 125),
    'grey5': (13, 13, 13),
    'grey50': (127, 127, 127),
    'grey51': (130, 130, 130),
    'grey52': (133, 133, 133),
    'grey53': (135, 135, 135),
    'grey54': (138, 138, 138),
    'grey55': (140, 140, 140),
    'grey56': (143, 143, 143),
    'grey57': (145, 145, 145),
    'grey58': (148, 148, 148),
    'grey59': (150, 150, 150),
    'grey6': (15, 15, 15),
    'grey60': (153, 153, 153),
    'grey61': (156, 156, 156),
    'grey62': (158, 158, 158),
    'grey63': (161, 161, 161),
    'grey64': (163, 163, 163),
    'grey65': (166, 166, 166),
    'grey66': (168, 168, 168),
    'grey67': (171, 171, 171),
    'grey68': (173, 173, 173),
    'grey69': (176, 176, 176),
    'grey7': (18, 18, 18),
    'grey70': (179, 179, 179),
    'grey71': (181, 181, 181),
    'grey72': (184, 184, 184),
    'grey73': (186, 186, 186),
    'grey74': (189, 189, 189),
    'grey75': (191, 191, 191),
    'grey76': (194, 194, 194),
    'grey77': (196, 196, 196),
    'grey78': (199, 199, 199),
    'grey79': (201, 201, 201),
    'grey8': (20, 20, 20),
    'grey80': (204, 204, 204),
    'grey81': (207, 207, 207),
    'grey82': (209, 209, 209),
    'grey83': (212, 212, 212),
    'grey84': (214, 214, 214),
    'grey85': (217, 217, 217),
    'grey86': (219, 219, 219),
    'grey87': (222, 222, 222),
    'grey88': (224, 224, 224),
    'grey89': (227, 227, 227),
    'grey9': (23, 23, 23),
    'grey90': (229, 229, 229),
    'grey91': (232, 232, 232),
    'grey92': (235, 235, 235),
    'grey93': (237, 237, 237),
    'grey94': (240, 240, 240),
    'grey95': (242, 242, 242),
    'grey96': (245, 245, 245),
    'grey97': (247, 247, 247),
    'grey98': (250, 250, 250),
    'grey99': (252, 252, 252),
    'honeydew': (240, 255, 240),
    'honeydew1': (240, 255, 240),
    'honeydew2': (224, 238, 224),
    'honeydew3': (193, 205, 193),
    'honeydew4': (131, 139, 131),
    'hotpink': (255, 105, 180),
    'hotpink1': (255, 110, 180),
    'hotpink2': (238, 106, 167),
    'hotpink3': (205, 96, 144),
    'hotpink4': (139, 58, 98),
    'indianred': (205, 92, 92),
    'indianred1': (255, 106, 106),
    'indianred2': (238, 99, 99),
    'indianred3': (205, 85, 85),
    'indianred4': (139, 58, 58),
    'ivory': (255, 255, 240),
    'ivory1': (255, 255, 240),
    'ivory2': (238, 238, 224),
    'ivory3': (205, 205, 193),
    'ivory4': (139, 139, 131),
    'khaki': (240, 230, 140),
    'khaki1': (255, 246, 143),
    'khaki2': (238, 230, 133),
    'khaki3': (205, 198, 115),
    'khaki4': (139, 134, 78),
    'lavender': (230, 230, 250),
    'lavenderblush': (255, 240, 245),
    'lavenderblush1': (255, 240, 245),
    'lavenderblush2': (238, 224, 229),
    'lavenderblush3': (205, 193, 197),
    'lavenderblush4': (139, 131, 134),
    'lawngreen': (124, 252, 0),
    'lemonchiffon': (255, 250, 205),
    'lemonchiffon1': (255, 250, 205),
    'lemonchiffon2': (238, 233, 191),
    'lemonchiffon3': (205, 201, 165),
    'lemonchiffon4': (139, 137, 112),
    'lightblue': (173, 216, 230),
    'lightblue1': (191, 239, 255),
    'lightblue2': (178, 223, 238),
    'lightblue3': (154, 192, 205),
    'lightblue4': (104, 131, 139),
    'lightcoral': (240, 128, 128),
    'lightcyan': (224, 255, 255),
    'lightcyan1': (224, 255, 255),
    'lightcyan2': (209, 238, 238),
    'lightcyan3': (180, 205, 205),
    'lightcyan4': (122, 139, 139),
    'lightgoldenrod': (238, 221, 130),
    'lightgoldenrod1': (255, 236, 139),
    'lightgoldenrod2': (238, 220, 130),
    'lightgoldenrod3': (205, 190, 112),
    'lightgoldenrod4': (139, 129, 76),
    'lightgoldenrodyellow': (250, 250, 210),
    'lightgray': (211, 211, 211),
    'lightgreen': (144, 238, 144),
    'lightgrey': (211, 211, 211),
    'lightpink': (255, 182, 193),
    'lightpink1': (255, 174, 185),
    'lightpink2': (238, 162, 173),
    'lightpink3': (205, 140, 149),
    'lightpink4': (139, 95, 101),
    'lightsalmon': (255, 160, 122),
    'lightsalmon1': (255, 160, 122),
    'lightsalmon2': (238, 149, 114),
    'lightsalmon3': (205, 129, 98),
    'lightsalmon4': (139, 87, 66),
    'lightseagreen': (32, 178, 170),
    'lightskyblue': (135, 206, 250),
    'lightskyblue1': (176, 226, 255),
    'lightskyblue2': (164, 211, 238),
    'lightskyblue3': (141, 182, 205),
    'lightskyblue4': (96, 123, 139),
    'lightslateblue': (132, 112, 255),
    'lightslategray': (119, 136, 153),
    'lightslategrey': (119, 136, 153),
    'lightsteelblue': (176, 196, 222),
    'lightsteelblue1': (202, 225, 255),
    'lightsteelblue2': (188, 210, 238),
    'lightsteelblue3': (162, 181, 205),
    'lightsteelblue4': (110, 123, 139),
    'lightyellow': (255, 255, 224),
    'lightyellow1': (255, 255, 224),
    'lightyellow2': (238, 238, 209),
    'lightyellow3': (205, 205, 180),
    'lightyellow4': (139, 139, 122),
    'limegreen': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'magenta1': (255, 0, 255),
    'magenta2': (238, 0, 238),
    'magenta3': (205, 0, 205),
    'magenta4': (139, 0, 139),
    'maroon': (128, 0, 0),
    'maroon1': (255, 52, 179),
    'maroon2': (238, 48, 167),
    'maroon3': (205, 41, 144),
    'maroon4': (139, 28, 98),
    'mediumaquamarine': (102, 205, 170),
    'mediumblue': (0, 0, 205),
    'mediumorchid': (186, 85, 211),
    'mediumorchid1': (224, 102, 255),
    'mediumorchid2': (209, 95, 238),
    'mediumorchid3': (180, 82, 205),
    'mediumorchid4': (122, 55, 139),
    'mediumpurple': (147, 112, 219),
    'mediumpurple1': (171, 130, 255),
    'mediumpurple2': (159, 121, 238),
    'mediumpurple3': (137, 104, 205),
    'mediumpurple4': (93, 71, 139),
    'mediumseagreen': (60, 179, 113),
    'mediumslateblue': (123, 104, 238),
    'mediumspringgreen': (0, 250, 154),
    'mediumturquoise': (72, 209, 204),
    'mediumvioletred': (199, 21, 133),
    'midnightblue': (25, 25, 112),
    'mintcream': (245, 255, 250),
    'mistyrose': (255, 228, 225),
    'mistyrose1': (255, 228, 225),
    'mistyrose2': (238, 213, 210),
    'mistyrose3': (205, 183, 181),
    'mistyrose4': (139, 125, 123),
    'moccasin': (255, 228, 181),
    'navajowhite': (255, 222, 173),
    'navajowhite1': (255, 222, 173),
    'navajowhite2': (238, 207, 161),
    'navajowhite3': (205, 179, 139),
    'navajowhite4': (139, 121, 94),
    'navy': (0, 0, 128),
    'navyblue': (0, 0, 128),
    'oldlace': (253, 245, 230),
    'olivedrab': (107, 142, 35),
    'olivedrab1': (192, 255, 62),
    'olivedrab2': (179, 238, 58),
    'olivedrab3': (154, 205, 50),
    'olivedrab4': (105, 139, 34),
    'orange': (255, 165, 0),
    'orange1': (255, 165, 0),
    'orange2': (238, 154, 0),
    'orange3': (205, 133, 0),
    'orange4': (139, 90, 0),
    'orangered': (255, 69, 0),
    'orangered1': (255, 69, 0),
    'orangered2': (238, 64, 0),
    'orangered3': (205, 55, 0),
    'orangered4': (139, 37, 0),
    'orchid': (218, 112, 214),
    'orchid1': (255, 131, 250),
    'orchid2': (238, 122, 233),
    'orchid3': (205, 105, 201),
    'orchid4': (139, 71, 137),
    'palegoldenrod': (238, 232, 170),
    'palegreen': (152, 251, 152),
    'palegreen1': (154, 255, 154),
    'palegreen2': (144, 238, 144),
    'palegreen3': (124, 205, 124),
    'palegreen4': (84, 139, 84),
    'paleturquoise': (175, 238, 238),
    'paleturquoise1': (187, 255, 255),
    'paleturquoise2': (174, 238, 238),
    'paleturquoise3': (150, 205, 205),
    'paleturquoise4': (102, 139, 139),
    'palevioletred': (219, 112, 147),
    'palevioletred1': (255, 130, 171),
    'palevioletred2': (238, 121, 159),
    'palevioletred3': (205, 104, 137),
    'palevioletred4': (139, 71, 93),
    'papayawhip': (255, 239, 213),
    'peachpuff': (255, 218, 185),
    'peachpuff1': (255, 218, 185),
    'peachpuff2': (238, 203, 173),
    'peachpuff3': (205, 175, 149),
    'peachpuff4': (139, 119, 101),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'pink1': (255, 181, 197),
    'pink2': (238, 169, 184),
    'pink3': (205, 145, 158),
    'pink4': (139, 99, 108),
    'plum': (221, 160, 221),
    'plum1': (255, 187, 255),
    'plum2': (238, 174, 238),
    'plum3': (205, 150, 205),
    'plum4': (139, 102, 139),
    'powderblue': (176, 224, 230),
    'purple': (128, 0, 128),
    'purple1': (155, 48, 255),
    'purple2': (145, 44, 238),
    'purple3': (125, 38, 205),
    'purple4': (85, 26, 139),
    'red': (255, 0, 0),
    'red1': (255, 0, 0),
    'red2': (238, 0, 0),
    'red3': (205, 0, 0),
    'red4': (139, 0, 0),
    'rosybrown': (188, 143, 143),
    'rosybrown1': (255, 193, 193),
    'rosybrown2': (238, 180, 180),
    'rosybrown3': (205, 155, 155),
    'rosybrown4': (139, 105, 105),
    'royalblue': (65, 105, 225),
    'royalblue1': (72, 118, 255),
    'royalblue2': (67, 110, 238),
    'royalblue3': (58, 95, 205),
    'royalblue4': (39, 64, 139),
    'saddlebrown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'salmon1': (255, 140, 105),
    'salmon2': (238, 130, 98),
    'salmon3': (205, 112, 84),
    'salmon4': (139, 76, 57),
    'sandybrown': (244, 164, 96),
    'seagreen': (46, 139, 87),
    'seagreen1': (84, 255, 159),
    'seagreen2': (78, 238, 148),
    'seagreen3': (67, 205, 128),
    'seagreen4': (46, 139, 87),
    'seashell': (255, 245, 238),
    'seashell1': (255, 245, 238),
    'seashell2': (238, 229, 222),
    'seashell3': (205, 197, 191),
    'seashell4': (139, 134, 130),
    'sienna': (160, 82, 45),
    'sienna1': (255, 130, 71),
    'sienna2': (238, 121, 66),
    'sienna3': (205, 104, 57),
    'sienna4': (139, 71, 38),
    'skyblue': (135, 206, 235),
    'skyblue1': (135, 206, 255),
    'skyblue2': (126, 192, 238),
    'skyblue3': (108, 166, 205),
    'skyblue4': (74, 112, 139),
    'slateblue': (106, 90, 205),
    'slateblue1': (131, 111, 255),
    'slateblue2': (122, 103, 238),
    'slateblue3': (105, 89, 205),
    'slateblue4': (71, 60, 139),
    'slategray': (112, 128, 144),
    'slategray1': (198, 226, 255),
    'slategray2': (185, 211, 238),
    'slategray3': (159, 182, 205),
    'slategray4': (108, 123, 139),
    'slategrey': (112, 128, 144),
    'snow': (255, 250, 250),
    'snow1': (255, 250, 250),
    'snow2': (238, 233, 233),
    'snow3': (205, 201, 201),
    'snow4': (139, 137, 137),
    'springgreen': (0, 255, 127),
    'springgreen1': (0, 255, 127),
    'springgreen2': (0, 238, 118),
    'springgreen3': (0, 205, 102),
    'springgreen4': (0, 139, 69),
    'steelblue': (70, 130, 180),
    'steelblue1': (99, 184, 255),
    'steelblue2': (92, 172, 238),
    'steelblue3': (79, 148, 205),
    'steelblue4': (54, 100, 139),
    'tan': (210, 180, 140),
    'tan1': (255, 165, 79),
    'tan2': (238, 154, 73),
    'tan3': (205, 133, 63),
    'tan4': (139, 90, 43),
    'thistle': (216, 191, 216),
    'thistle1': (255, 225, 255),
    'thistle2': (238, 210, 238),
    'thistle3': (205, 181, 205),
    'thistle4': (139, 123, 139),
    'tomato': (255, 99, 71),
    'tomato1': (255, 99, 71),
    'tomato2': (238, 92, 66),
    'tomato3': (205, 79, 57),
    'tomato4': (139, 54, 38),
    'turquoise': (64, 224, 208),
    'turquoise1': (0, 245, 255),
    'turquoise2': (0, 229, 238),
    'turquoise3': (0, 197, 205),
    'turquoise4': (0, 134, 139),
    'violet': (238, 130, 238),
    'violetred': (208, 32, 144),
    'violetred1': (255, 62, 150),
    'violetred2': (238, 58, 140),
    'violetred3': (205, 50, 120),
    'violetred4': (139, 34, 82),
    'wheat': (245, 222, 179),
    'wheat1': (255, 231, 186),
    'wheat2': (238, 216, 174),
    'wheat3': (205, 186, 150),
    'wheat4': (139, 126, 102),
    'white': (255, 255, 255),
    'whitesmoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellow1': (255, 255, 0),
    'yellow2': (238, 238, 0),
    'yellow3': (205, 205, 0),
    'yellow4': (139, 139, 0),
    'yellowgreen': (154, 205, 50),
}


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
          Color('gray93'), Color('gray94'), Color('gray95'), Color('gray97'), Color('gray98'), Color('gray99')]
