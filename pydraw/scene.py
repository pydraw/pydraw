import inspect

from pydraw import Screen, Location
from pydraw.errors import PydrawError


class Scene:
    """A reusable Screen state with lifecycle and input hooks.

    ``Screen`` owns the application loop. A Scene creates its objects in
    :meth:`start`, advances one frame in :meth:`update`, and releases any
    external state in :meth:`stop`. Input methods are registered automatically
    when the Scene is applied with ``screen.scene(scene)``.
    """

    def __init__(self):
        self._screen = None
        self._update_accepts_dt = True

    def screen(self):
        """Return the bound Screen, or ``None`` before activation."""

        return self._screen

    def start(self) -> None:
        """Initialize the Scene after it has been bound to a Screen."""

    def update(self, dt: float = None) -> None:
        """Advance the Scene by one frame.

        Subclasses may define either ``update(self)`` or ``update(self, dt)``.

        :param dt: optional elapsed seconds since the previous frame; ``0.0``
                   on the first frame after activation
        """

    def stop(self) -> None:
        """Release Scene state immediately before deactivation."""

    def goto(self, scene: 'Scene') -> 'Scene':
        """Request another Scene.

        During an input callback or frame update, the transition is deferred
        until the safe frame boundary. Outside an update, it is applied
        immediately.

        :param scene: the Scene to activate next
        :return: the requested Scene
        """

        if self._screen is None:
            raise PydrawError('Scene#goto(): the Scene is not active.')
        return self._screen.scene(scene)

    def mousedown(self, location: Location, button: int) -> None:
        """Handle a pointer-button press.

        :param location: the pressed location
        :param button: left, middle, or right button (1-3)
        """

    def mouseup(self, location: Location, button: int) -> None:
        """Handle a pointer-button release.

        :param location: the released location
        :param button: left, middle, or right button (1-3)
        """

    def mousedrag(self, location: Location, button: int) -> None:
        """Handle pointer movement while a button is held.

        :param location: the current pointer location
        :param button: held left, middle, or right button (1-3)
        """

    def mousemove(self, location: Location) -> None:
        """Handle pointer movement without a held button."""

    def keydown(self, key: Screen.Key) -> None:
        """Handle a normalized key press."""

    def keyup(self, key: Screen.Key) -> None:
        """Handle a normalized key release."""

    def _activate(self, screen: Screen) -> None:
        signature = inspect.signature(self.update)
        try:
            signature.bind(0.0)
            self._update_accepts_dt = True
        except TypeError:
            try:
                signature.bind()
                self._update_accepts_dt = False
            except TypeError as error:
                raise PydrawError(
                    'Scene#update(): expected update(self) or update(self, dt).'
                ) from error

        self._screen = screen
        self.start()

    def _step(self, dt: float) -> None:
        if self._update_accepts_dt:
            self.update(dt)
        else:
            self.update()

    def _deactivate(self) -> None:
        try:
            self.stop()
        finally:
            self._screen = None
