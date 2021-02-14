import turtle;
import tkinter as tk;
import inspect;
import time;

from pydraw import Color;
from pydraw import Location;

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
        self._canvas = self._screen.cv;

        self._screen.screensize(width, height);
        self._screen.setup(width + BORDER_CONSTANT, height + BORDER_CONSTANT);
        # This was not necessary as the canvas will align with the window's dimensions as set in the above line.

        self._screen.title(title);
        self._title = title;

        self._screen.colormode(255);

        # store the mouse position
        self._mouse = Location(0, 0);
        self._gridlines = [];
        self._gridstate = False;  # grid is disabled by default

        # By default we want to make sure that all objects are drawn instantly.
        self._screen.tracer(0);
        self._screen.update();

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

    def color(self, color: Color) -> None:
        """
        Set the background color of the screen.
        :param color: the color to set the background to
        :return: None
        """

        self._screen.bgcolor(color.__value__());

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
        Get the size of the screen (please note this is not the canvas, and those attributes should be
        retrieved using the width() and height() methods respectively)
        :return: a tuple containing the width and height of the screen
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

    def grid(self, rows: int = None, cols: int = None, cellsize: tuple = (50, 50)):
        from pydraw import Line;

        if len(self._gridlines) > 0:
            [line.remove() for line in self._gridlines];
            self._gridlines.clear();
        self._gridstate = True;

        if rows is not None:
            cellsize = (self.height() / rows, cellsize[1]);
        if cols is not None:
            cellsize = (cellsize[0], self.width() / cols);

        for row in range(int(cellsize[1]), int(self.height()), int(cellsize[1])):
            self._gridlines.append(Line(self, Location(0, row), Location(self.width(), row), color=Color('lightgray')));

        for col in range(int(cellsize[0]), int(self.width()), int(cellsize[0])):
            self._gridlines.append(Line(self, Location(col, 0), Location(col, self.height()), color=Color('lightgray')));

    def toggle_grid(self, value=None):
        if value is None:
            value = not self._gridstate;

        [line.visible(value) for line in self._gridlines];

    # noinspection PyProtectedMember
    def remove(self, obj):
        from pydraw import Renderable, CustomRenderable;
        if isinstance(obj, Renderable) and not isinstance(obj, CustomRenderable):
            obj._ref.reset();
            obj._ref.ht();
            del obj;
        else:
            self._screen.cv.delete(obj._ref);
            del obj;

    def clear(self) -> None:
        """
        Clears the screen.
        :return: None
        """

        try:
            self._screen.clear();
        except tk.TclError:
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
        except (turtle.Terminator, tk.TclError):
            # If we experience the termination exception, we will print the termination of the program
            # and exit the python program.
            print('Terminated.');
            exit(1);

    def exit(self) -> None:
        """
        You must call this method to have the window properly exit.
        :return: None
        """
        self._screen.clear();
        turtle.done();

    def _colorstr(self, color: Color) -> str:
        """
        Takes a pydraw Color and returns a tkinter-friendly string, while also preventing errors
        from occurring after tkinter has shut down.
        :param color: the Color to convert
        :return: the converted color (tkinter-str)
        """

        try:
            # noinspection PyProtectedMember
            return self._screen._colorstr(color.__value__());
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
