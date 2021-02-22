import turtle;
import tkinter as tk;
import inspect;
import time;

from pydraw import Color;
from pydraw import Location;
from pydraw.errors import *;

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

        self._root.resizable(False, False);  # No resizing!

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
        self._screen.tracer(False);
        self._screen.update();

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
        from pydraw import Line, Text;

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
        from pydraw import Line, Text;

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
        :param fullscreen: the new fullscreen state, if any
        :return: the current fullscreen state of the Screen
        """

        if fullscreen is not None:
            self._fullscreen = fullscreen;
            self._root.attributes("-fullscreen", fullscreen);
            self.update();

        return self._fullscreen;

    def _add(self, obj) -> None:
        """
        Internal method which adds object to a list upon construction.
        :param obj: the object to add.
        :return: None
        """

        self._objects.append(obj);

    # noinspection PyProtectedMember
    def remove(self, obj):
        from pydraw import Renderable, CustomRenderable;
        if isinstance(obj, Renderable) and not isinstance(obj, CustomRenderable):
            obj._ref.reset();
            obj._ref.ht();
            self._objects.remove(obj);
            del obj;
        else:
            self._screen.cv.delete(obj._ref);
            if obj in self._objects:
                self._objects.remove(obj);
            elif obj not in self._gridlines and obj not in self._helpers:
                raise ValueError(f'Object: {obj} is not registered with the screen? Did you call the constructor?');
            del obj;

    def objects(self) -> tuple:
        """
        Retrieves all objects on the Screen!
        :return: A tuple (immutable list) of Objects (you will want to check types for certain methods!)
        """

        return tuple(self._objects);

    # noinspection PyProtectedMember
    def front(self, obj):
        from pydraw import Renderable, CustomRenderable;
        if isinstance(obj, Renderable) and not isinstance(obj, CustomRenderable):
            obj._ref.forward(0);
        else:
            self._canvas.tag_raise(obj._ref);

    def clear(self) -> None:
        """
        Clears the screen.
        :return: None
        """

        try:
            self._screen.clear();
            if self._gridstate:
                self._redraw_grid();  # Redraw the grid if it was active.
            self.color(self._color);  # Redraw the color of the screen.
        except (tk.TclError, AttributeError):
            pass;  # We silently stop TclErrors from appearing to users.

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
            self._screen.update();
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
        self.stop();
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
