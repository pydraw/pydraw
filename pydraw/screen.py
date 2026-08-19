import inspect
import math
import time
from typing import Optional

from pydraw import Color
from pydraw import Location
from pydraw.events import InputEvent
from pydraw.render import RenderQueue
from pydraw.runtime import BackendTerminated, ScreenConfig, _create_screen_backend
from pydraw.util import *

INPUT_TYPES = [
    'mousedown',
    'mouseup',
    'mousedrag',
    'mousemove',
    'keydown',
    'keyup',
    'keypress'
]

def _default_runtime():
    from pydraw.backends.tk import TkRuntime

    return TkRuntime()


class Screen:
    """
    A class containing methods and values that can be manipulated in order to affect
    the window that is created. Sort of like a canvas.
    """

    def __init__(self, width: int = 800, height: int = 600, title: str = "pydraw"):
        verify(width, int, height, int, title, str)

        self._backend = _create_screen_backend(
            ScreenConfig(width, height, title),
            _default_runtime,
        )

        self._width = width
        self._height = height

        # Timing state used by sleep(delta=True). The completed-frame timestamp
        # measures delta time; the deadline keeps frame pacing from drifting.
        self._last_frame_time = None
        self._next_frame_time = None

        self._title = title
        self._color = Color('white')
        self._backend.set_background(self._color.rgb())

        self._objects = []  # Store objects on the screen :)
        self._render_queue = RenderQueue()
        self._fullscreen = False
        self._updating = False
        self._looping = False

        # store the mouse position
        self._mouse = Location(0, 0)
        self._gridlines = []
        self._gridstate = False  # grid is disabled by default

        self._helpers = []
        self._helperstate = 0

        self._scene = None  # We store our current Scene.
        self._pending_scene = None
        self._scene_frame_time = None

        self.registry = {}  # The input function registry (stores input callbacks)

    def title(self, title: str = None) -> str:
        """
        Get or set the title of the screen.

        :param title: the title to set to, if any
        :return: the title
        """

        if title is not None:
            verify(title, str)
            self._title = title
            self._backend.set_title(title)

        return self._title

    def color(self, color: Color = None) -> Color:
        """
        Set the background color of the screen.

        :param color: the color to set the background to
        :return: None
        """

        if color is not None:
            verify(color, Color)
            self._color = color
            self._backend.set_background(color.rgb())
        return self._color

    def picture(self, pic: str) -> None:
        """
        Set the background picture of the screen.

        :param pic: the path to said picture from the file
        :return: None
        """

        verify(pic, str)
        self._backend.set_background_image(pic)

    def resize(self, width: int, height: int) -> None:
        """
        @deprecated (does not work on all OSes)

        Resize the screen to new dimensions

        :param width: the width to resize to
        :param height: the height to resize to
        :return: None
        """

        verify(width, int, height, int)
        self._backend.resize(width, height)

    def size(self) -> (int, int):
        """
        Get the size of the WINDOW (please note this is not the canvas, and those attributes should be
        retrieved using the width() and height() methods respectively)

        :return: a tuple containing the width and height of the WINDOW
        """

        return self._backend.window_size()

    def _dims(self) -> tuple:
        """
        Returns the (width, height) of the CANVAS, memoized. The cache is cleared
        by the <Configure> binding installed in __init__ whenever the canvas is
        resized, so this stays correct for resizable/fullscreen windows too.
        :return: a (width, height) tuple, or (-1, -1) while tkinter is shutting down
        """

        return self._backend.canvas_size()

    def width(self) -> int:
        """
        Returns the width of the CANVAS within the screen. Important.

        :return: an integer representing the width of the canvas
        """

        return self._dims()[0]

    def height(self) -> int:
        """
        Returns the height of the CANVAS within the screen. Important.

        :return:
        """

        return self._dims()[1]

    def center(self) -> Location:
        """
        Gets the center of the screen.
        """

        return Location(self.width() / 2, self.height() / 2)

    # noinspection PyMethodMayBeStatic
    def top_left(self) -> Location:
        """
        Returns the top left corner of the screen

        :return: Location
        """

        return Location(0, 0)

    def top_right(self) -> Location:
        """
        Returns the top right corner of the screen

        :return: Location
        """

        return Location(self.width(), 0)

    def bottom_left(self) -> Location:
        """
        Returns the bottom left corner of the screen

        :return: Location
        """

        return Location(0, self.height())

    def bottom_right(self) -> Location:
        """
        Returns the bottom right corner of the screen

        :return: Location
        """

        return Location(self.width(), self.height())

    def mouse(self) -> Location:
        """
        Get the current mouse-position

        :return: the mouse-position in the form of a Location
        """

        return self._mouse

    # Direct Manipulation
    def alert(self, text: str, title: str = 'Alert', accept_text: str = 'Ok', cancel_text: str = 'Cancel') -> bool:
        """
        Displays a dialog-box alert, and returns

        :param text: The text to display in the body of the dialog
        :param title: The title of the dialog-box
        :param accept_text: The text displayed on the accept button, defaults to 'Ok'
        :param cancel_text: The text displayed on the cancel button, defaults to 'Cancel'
        :return: True if accept was pressed, False if cancel was pressed
        """
        verify(text, str, title, str, accept_text, str, cancel_text, str)
        return self._backend.alert(text, title, accept_text, cancel_text)

    def prompt(self, text: str, title: str = 'Prompt') -> Optional[str]:
        """
        Prompts the user for keyboard input

        :param: text the text to prompt the user with
        :param: title the title of the dialog box
        :return: the entered text, or None if the prompt was cancelled
        """

        verify(text, str, title, str)

        response = self._backend.prompt(text, title)
        self._backend.listen()
        return response

    def grid(self, rows: int = None, cols: int = None, cellsize: tuple = (50, 50), helpers: bool = True):
        from pydraw import Line, Text

        verify(rows, int, cols, int, cellsize, tuple, helpers, bool)

        if len(self._gridlines) > 0:
            [line.remove() for line in self._gridlines]
            self._gridlines.clear()
        if len(self._helpers) > 0:
            [helper.remove() for helper in self._helpers]
            self._helpers.clear()
        self._gridstate = True

        if rows is not None:
            cellsize = (self.height() / rows, cellsize[1])
        if cols is not None:
            cellsize = (cellsize[0], self.width() / cols)

        if helpers:
            textsize = int((self.width() + self.height() / 2) / 70)  # Text size is proportionate to screensize.

        for row in range(int(cellsize[1]), int(self.height()), int(cellsize[1])):
            line = Line(self, Location(0, row), Location(self.width(), row),
                        color=Color('lightgray'))
            self._gridlines.append(line)
            self._objects.remove(line)  # Don't want this in our objects list :)

            if helpers:
                helper = Text(self, str(row), 15, row, color=Color('gray'), size=textsize)
                helper.move(-helper.width() / 2, -helper.height() / 2)
                self._helpers.append(helper)
                self._objects.remove(helper)

        for col in range(int(cellsize[0]), int(self.width()), int(cellsize[0])):
            line = Line(self, Location(col, 0), Location(col, self.height()),
                        color=Color('lightgray'))
            self._gridlines.append(line)
            self._objects.remove(line)  # Don't want this in our objects list :)

            if helpers:
                helper = Text(self, str(col), col, 10, color=Color('gray'), size=textsize)
                helper.move(-helper.width() / 2, -helper.height() / 2)
                self._helpers.append(helper)
                self._objects.remove(helper)

    def toggle_grid(self, value=None):
        if value == False and len(self._gridlines) == 0: # If we don't have a grid and are resetting, no need to call grid()
            return

        if value is None:
            value = not self._gridstate

        if len(self._gridlines) == 0:
            self.grid()  # Create a grid if one does not exist.

        [line.visible(value) for line in self._gridlines]
        [helper.visible(value) for helper in self._helpers]

    def gridlines(self) -> tuple:
        """
        Allows you to retrieve the lines of the grid, but note that you cannot modify them!

        :return: a tuple (immutable list) of the gridlines.
        """

        return tuple(self._gridlines)

    def _redraw_grid(self):
        """
        An internal method to redraw the grid to the screen after screen.clear() is called.
        """
        from pydraw import Line, Text

        new_lines = []
        for line in self._gridlines:
            new_line = Line(self, line.pos1(), line.pos2(), color=line.color())
            line.remove()
            self._objects.remove(new_line)  # Still don't want this in the main objects list.
            new_lines.append(new_line)

        new_helpers = []
        for helper in self._helpers:
            new_helper = Text(self, helper.text(), helper.x(), helper.y(), color=helper.color(), size=helper.size())
            helper.remove()
            self._objects.remove(new_helper)
            new_helpers.append(new_helper)

        self._gridlines.clear()
        self._gridlines = new_lines

        self._helpers.clear()
        self._helpers = new_helpers

    def grab(self, filename: str = None) -> str:
        """
        Grabs a screenshot of the image and saves it to the directory with the specified filename!
        Note that if no filename is specified the file will be given a name based on the epoch time.

        :param filename: the name of the file to save the screenshot to.
        :return: the name of the file.
        """

        if filename is None:
            filename = 'pydraw' + str(time.time() % 10000)

        verify(filename, str)

        if not filename.endswith('.png'):
            filename += '.png'

        return self._backend.grab(filename)

    def fullscreen(self, fullscreen: bool = None) -> bool:
        """
        Get or set the fullscreen state of the application. Note that this will not resize your shapes, nor
        will it REPOSITION them. It is highly recommended that you call this method before creating any shapes!

        !!! EXPERIMENTAL !!!

        :param fullscreen: the new fullscreen state, if any
        :return: the current fullscreen state of the Screen
        """

        if fullscreen is not None:
            verify(fullscreen, bool)
            self._fullscreen = self._backend.set_fullscreen(fullscreen)
            self.update()

        return self._fullscreen

    def _front(self, obj) -> None:
        from pydraw import Object

        if not isinstance(obj, Object):
            raise InvalidArgumentError(
                f'Screen#front(): expected an Object; received {type(obj)} ({obj!r}).'
            )

        self._render_queue.front(obj._render_id)

    def _back(self, obj) -> None:
        from pydraw import Object

        if not isinstance(obj, Object):
            raise InvalidArgumentError(
                f'Screen#back(): expected an Object; received {type(obj)} ({obj!r}).'
            )

        self._render_queue.back(obj._render_id)

    def _register_render_source(self, source, render_id=None):
        return self._render_queue.register(source, render_id)

    def _allocate_render_id(self):
        return self._render_queue.allocate()

    def _invalidate_render(self, render_id):
        self._render_queue.invalidate(render_id)

    def _remove_render(self, render_id):
        self._render_queue.remove(render_id)

    def _add(self, obj) -> None:
        """
        Internal method which adds object to a list upon construction.

        :param obj: the object to add.
        :return: None
        """

        self._objects.append(obj)

    def add(self, obj) -> None:
        """
        Add an object back to the Screen after having removed it (with Object.remove() or Screen.remove(object)

        :param obj: the Object to add back.
        :return: None
        """

        if obj in self._objects:
            raise PydrawError(
                f'Screen#add(): object is already on this Screen: {type(obj)} ({obj!r}).'
            )

        self._add(obj)
        restore_render = getattr(obj, '_restore_render', None)
        if restore_render is not None:
            restore_render()

    # noinspection PyProtectedMember
    def remove(self, obj):
        render_id = getattr(obj, '_render_id', None)
        if render_id is None:
            render_id = getattr(obj, '_ref', None)
        if render_id is not None:
            self._remove_render(render_id)
        if obj in self._objects:
            self._objects.remove(obj)

    def objects(self) -> tuple:
        """
        Retrieves all objects on the Screen!

        :return: A tuple (immutable list) of Objects (you will want to check types for certain methods!)
        """

        return tuple(self._objects)

    def contains(self, obj) -> bool:
        """
        Returns whether or not the passed object exists on the Screen (is in the objects cache)

        :param obj: the Object to check
        :return: a boolean
        """

        return obj in self._objects

    def __contains__(self, item):
        return self.contains(item)

    def clear(self) -> None:
        """
        Remove all registered user objects from the Screen.

        Screen decorations such as grid lines and coordinate helpers are
        preserved, as are the background color or image, input handlers, and
        the active Scene. Use :meth:`reset` to also clear lifecycle, handler,
        and decoration state.

        :return: None
        """

        for i in range(len(self._objects) - 1, -1, -1):
            self._objects[i].remove()
        self.color(self._color)

    def scene(self, scene=None):
        """
        Get or apply a Scene.

        Applying a Scene stops the current Scene, removes its registered user
        objects, grid/helper decorations, and input handlers, then starts the
        replacement. Screen background configuration is preserved. A
        transition requested from an input handler or Scene update is deferred
        until the frame boundary.

        :param scene: the Scene to apply, if any
        :return: the requested Scene, or the active Scene when called without one
        """
        from pydraw import Scene

        if scene is None:
            return self._scene

        if not isinstance(scene, Scene):
            raise InvalidArgumentError(
                f'Screen#scene(): expected a Scene; received {type(scene)} ({scene!r}).'
            )

        if self._updating:
            self._pending_scene = scene
            return scene

        return self._apply_scene(scene)

    def _apply_scene(self, scene):
        self.reset()

        for (name, function) in inspect.getmembers(scene, predicate=inspect.ismethod):
            if name.lower() not in INPUT_TYPES:
                continue

            self.registry[name.lower()] = function

        self._scene = scene
        self._listen()
        try:
            scene._activate(self)
        except BaseException:
            self.registry.clear()
            self._scene = None
            self._scene_frame_time = None
            if scene.screen() is self:
                scene._screen = None
            self.clear()
            raise
        return scene

    def _apply_pending_scene(self):
        scene = self._pending_scene
        if scene is None:
            return False

        self._pending_scene = None
        self._apply_scene(scene)
        return True

    def _update_scene(self):
        if self._scene is None:
            return

        now = time.perf_counter()
        if self._scene_frame_time is None:
            dt = 0.0
        else:
            dt = now - self._scene_frame_time
        self._scene_frame_time = now
        self._scene._step(dt)

    def _deactivate_scene(self):
        scene = self._scene
        self._scene = None
        self._scene_frame_time = None
        if scene is not None:
            scene._deactivate()

    def reset(self) -> None:
        """
        Reset lifecycle state, deactivating the Scene and removing registered
        user objects, grid/helper decorations, and input handlers. Screen
        background configuration is preserved.

        :return: None
        """

        self._deactivate_scene()
        self._pending_scene = None

        self._last_frame_time = None
        self._next_frame_time = None

        # Disable callbacks before removing objects. Tk may dispatch a queued
        # input event while canvas state is being torn down; leaving the old
        # registry live would let that event reach a scene whose objects have
        # already been detached from this Screen.
        self.registry.clear()

        self.toggle_grid(False)
        for line in self._gridlines:
            line.remove()
        self._gridlines.clear()

        for obj in self._helpers:
            obj.remove()
        self._helpers.clear()
        self._helperstate = False

        self.clear()

    def sleep(self, delay: float, delta: bool = False) -> Optional[float]:
        """
        Pause execution, optionally compensating for work done during the frame.

        With ``delta=False``, this sleeps for the full delay and returns None.
        With ``delta=True``, it sleeps only until the next frame deadline and
        returns the actual duration of the completed frame in seconds. The
        returned value is intended to be used as ``dt`` in the next frame.

        The first delta-enabled call returns the requested delay because there
        is no previous frame timestamp to measure. If execution falls more than
        one frame behind, the deadline is reset so the loop does not run a burst
        of catch-up frames.

        :param delay: target frame duration in seconds
        :param delta: whether to enable compensated frame pacing and return dt
        :return: None normally, or the completed frame duration when delta=True
        """

        if type(delay) is not int and type(delay) is not float:
            raise InvalidArgumentError(
                f'Screen#sleep(): delay must be a number; received {type(delay)} ({delay!r}).'
            )
        if type(delta) is not bool:
            raise InvalidArgumentError(
                f'Screen#sleep(): delta must be a bool; received {type(delta)} ({delta!r}).'
            )

        original_delay = delay
        try:
            delay = float(delay)
        except OverflowError:
            raise InvalidArgumentError(
                f'Screen#sleep(): delay must be finite and non-negative; received {original_delay!r}.'
            )

        if delay < 0 or not math.isfinite(delay):
            raise InvalidArgumentError(
                f'Screen#sleep(): delay must be finite and non-negative; received {original_delay!r}.'
            )

        if not delta:
            # A normal sleep breaks the delta-enabled frame sequence. Resetting
            # prevents that wait from being counted as work if delta timing is
            # enabled again later.
            self._last_frame_time = None
            self._next_frame_time = None
            time.sleep(delay)
            return None

        now = time.perf_counter()
        first_frame = self._last_frame_time is None or self._next_frame_time is None

        if first_frame:
            self._next_frame_time = now + delay
        else:
            self._next_frame_time += delay

            # Retain the absolute schedule for ordinary jitter, but discard
            # accumulated timing debt after a pause or a very slow frame.
            if now - self._next_frame_time > delay:
                self._next_frame_time = now + delay

        remaining = self._next_frame_time - now
        if remaining > 0:
            time.sleep(remaining)

        completed_at = time.perf_counter()
        frame_time = delay if first_frame else completed_at - self._last_frame_time
        self._last_frame_time = completed_at
        return frame_time

    def update(self) -> None:
        """
        Process and present one complete frame.

        The frame order is: poll pending input, run each input callback
        synchronously, advance the active Scene once, and present the render
        batch produced by that work. Input callbacks and the Scene step are
        therefore visible in the same frame. Scene transitions requested by
        either stage are applied at a safe frame boundary before presentation.
        This method is not reentrant; calling ``update()`` from a callback (or
        another update) raises ``PydrawError``.

        :return: None
        """
        if self._updating:
            raise PydrawError('Screen#update(): update is not reentrant.')

        self._updating = True
        try:
            for event in self._backend.poll_events():
                self._dispatch_input_event(event)
            self._apply_pending_scene()
            self._update_scene()
            self._apply_pending_scene()
            self._backend.present(self._render_queue.take())
        except BackendTerminated:
            print('Terminated.')
            exit(0)
        finally:
            self._updating = False

    def stop(self) -> None:
        """
        Deprecated. Use `screen.loop` instead.

        :return: None
        """

        self.loop()

    def loop(self) -> None:
        """
        Hold the program open while the backend calls ``update()`` per frame.

        The backend owns the platform loop, but each frame follows the same
        poll, synchronous callback, Scene-step, and present order as an
        explicit ``update()`` call. ``loop()`` is not reentrant and cannot be
        called while another loop is running.

        :returns: None
        """

        if self._looping:
            raise PydrawError('Screen#loop(): loop is not reentrant.')

        self._looping = True
        try:
            self._backend.run(self.update)
        finally:
            self._looping = False
            self._pending_scene = None
            self._deactivate_scene()

    def exit(self) -> None:
        """
        Called at the end of pydraw programs as an event for successful program execution and termination.
        To keep a program open, use Screen.loop().

        :return: None
        """

        # Prevent queued Tk events from reaching callbacks while the canvas and
        # its objects are being destroyed.
        self._pending_scene = None
        self._deactivate_scene()
        self.registry.clear()
        self._backend.close()
        exit(0)

    def listen(self) -> None:
        """
        Inspect the caller's module for input functions and register them as
        callbacks. The input type is determined by each function's name.

        Allowed Names:
          - mousedown
          - mouseup
          - mousedrag
          - mousemove
          - keydown
          - keyup
          - keypress (deprecated legacy/custom-backend event; Tk does not emit it)

        :return: None
        """

        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        for (name, function) in inspect.getmembers(mod, inspect.isfunction):
            if name.lower() not in INPUT_TYPES:
                continue

            self.registry[name.lower()] = function
            # print('Registered input-function:', name)

        self._listen()

    def _listen(self):
        self._backend.set_handlers(tuple(self.registry))
        self._backend.listen()

    class Key:
        def __init__(self, key: str):
            self._key = key

        def key(self) -> str:
            """
            Returns the string for the key.

            :return: the key in ascii
            """
            return self._key

        def __repr__(self):
            return self.key()

        def __str__(self):
            return self.key()

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
                return obj.key() == self.key()
            elif type(obj) is str:
                return obj.lower() == self.key().lower()
            else:
                return False

    def _dispatch_input_event(self, event) -> None:
        if not isinstance(event, InputEvent):
            raise TypeError('backend returned an invalid input event')

        if event.kind == 'keydown':
            self._keydown(event.key)
        elif event.kind == 'keyup':
            self._keyup(event.key)
        elif event.kind == 'keypress':
            self._keypress(event.key)
        elif event.kind == 'mousedown':
            self._mousedown(event.button, Location(*event.position))
        elif event.kind == 'mouseup':
            self._mouseup(event.button, Location(*event.position))
        elif event.kind == 'mousedrag':
            self._mousedrag(event.button, Location(*event.position))
        elif event.kind == 'mousemove':
            self._mousemove(Location(*event.position))
        else:
            raise ValueError('backend returned an unknown input event')

    def _keydown(self, key) -> None:
        if 'keydown' not in self.registry:
            return

        self.registry['keydown'](self.Key(key.lower()))

    def _keyup(self, key) -> None:
        if 'keyup' not in self.registry:
            return

        self.registry['keyup'](self.Key(key.lower()))

    def _keypress(self, key) -> None:
        if 'keypress' not in self.registry:
            return

        self.registry['keypress'](self.Key(key.lower()))

    def _mousedown(self, button, location) -> None:
        self._mouse = location

        if 'mousedown' not in self.registry:
            return

        signature = inspect.signature(self.registry['mousedown'])
        keys = list(signature.parameters.keys())

        if len(keys) == 1:
            self.registry['mousedown'](location)
            return
        if keys[0] == "button" and keys[1] == "location":
            self.registry['mousedown'](button, location)
            print("[WARNING] in `mousedown` | Argument Pattern: (button, location) has been deprecated, "
                  "please use (location, button) instead.")
            return

        self.registry['mousedown'](location, button)

    def _mouseup(self, button, location) -> None:
        self._mouse = location

        if 'mouseup' not in self.registry:
            return

        signature = inspect.signature(self.registry['mouseup'])
        keys = list(signature.parameters.keys())

        if len(keys) == 1:
            self.registry['mouseup'](location)
            return
        if keys[0] == "button" and keys[1] == "location":
            self.registry['mouseup'](button, location)
            print("[WARNING] in `mouseup` | Argument Pattern: (button, location) has been deprecated, "
                  "please use (location, button) instead.")
            return

        self.registry['mouseup'](location, button)

    def _mouseclick(self, button, location) -> None:
        if 'mouseclick' not in self.registry:
            return

        self.registry['mouseclick'](button, location)

    def _mousedrag(self, button, location) -> None:
        self._mouse = location

        if 'mousedrag' not in self.registry:
            return

        signature = inspect.signature(self.registry['mousedrag'])
        keys = list(signature.parameters.keys())

        if len(keys) == 1:
            self.registry['mousedrag'](location)
            return
        if keys[0] == "button" and keys[1] == "location":
            self.registry['mousedrag'](button, location)
            print("[WARNING] in `mousedrag` | Argument Pattern: (button, location) has been deprecated, "
                  "please use (location, button) instead.")
            return

        self.registry['mousedrag'](location, button)

    def _mousemove(self, location) -> None:
        # We will update our internal storage of the mouse-location no matter what
        self._mouse = location

        if 'mousemove' not in self.registry:
            return

        self.registry['mousemove'](location)
