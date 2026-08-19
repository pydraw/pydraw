"""Platform runtime selection and backend contracts.

This module deliberately contains no Tk, Turtle, DOM, or PyScript imports.
Normal applications do not select a runtime.  A host may install one before
the first Screen is created; otherwise Screen supplies the built-in runtime's
lazy factory when it requests its backend.
"""

from abc import ABCMeta, abstractmethod
from typing import Callable, Iterable, NamedTuple, Optional


class ScreenConfig(NamedTuple):
    """Immutable values needed to create a platform screen."""

    width: int
    height: int
    title: str


class ScreenBackend(metaclass=ABCMeta):
    """Platform operations owned by one Screen.

    Backends translate platform input into :class:`pydraw.events.InputEvent`
    values and consume :class:`pydraw.render.RenderBatch` frames. The
    lifecycle boundary is intentionally independent of any one platform.
    """

    @abstractmethod
    def poll_events(self) -> Iterable:
        """Return pending normalized ``InputEvent`` values without blocking."""
        raise NotImplementedError

    @abstractmethod
    def listen(self) -> None:
        """Begin collecting platform input events."""
        raise NotImplementedError

    def set_handlers(self, handlers) -> None:
        """Publish the normalized input handlers registered by Screen."""
        pass

    @abstractmethod
    def present(self, frame) -> None:
        """Synchronously present or acknowledge one ``RenderBatch`` frame."""
        raise NotImplementedError

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Apply a platform title when the host supports one."""
        raise NotImplementedError

    @abstractmethod
    def set_background(self, color) -> None:
        """Apply an RGB screen background."""
        raise NotImplementedError

    @abstractmethod
    def set_background_image(self, source: str) -> None:
        """Apply a platform background image."""
        raise NotImplementedError

    @abstractmethod
    def canvas_size(self):
        """Return the drawable width and height."""
        raise NotImplementedError

    @abstractmethod
    def window_size(self):
        """Return the host window width and height."""
        raise NotImplementedError

    @abstractmethod
    def resize(self, width: int, height: int) -> None:
        """Resize the drawable area when supported."""
        raise NotImplementedError

    @abstractmethod
    def set_fullscreen(self, fullscreen: bool) -> bool:
        """Apply and return the host fullscreen state."""
        raise NotImplementedError

    @abstractmethod
    def alert(self, text, title, accept_text, cancel_text):
        """Show a host confirmation dialog and return its result."""
        raise NotImplementedError

    @abstractmethod
    def prompt(self, text, title) -> Optional[str]:
        """Show a host text prompt and return its text, or ``None``."""
        raise NotImplementedError

    @abstractmethod
    def grab(self, filename):
        """Capture the drawable area to a PNG and return its filename."""
        raise NotImplementedError

    @abstractmethod
    def measure_text(self, text, font, size, bold, italic):
        """Return the maximum line width and one line's height in pixels."""
        raise NotImplementedError

    @abstractmethod
    def measure_image(self, source):
        """Return an image's intrinsic width and height in pixels."""
        raise NotImplementedError

    @abstractmethod
    def image_frames(self, source):
        """Return an animated image's frame count."""
        raise NotImplementedError

    @abstractmethod
    def run(self, step: Callable[[], None]) -> None:
        """Run ``step`` repeatedly until the screen closes.

        ``step`` is the owning Screen's frame update. The Screen enforces that
        both ``update()`` and ``loop()`` are non-reentrant.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Release this screen's platform resources."""
        raise NotImplementedError


class Runtime(metaclass=ABCMeta):
    """Process-wide factory for independent per-Screen backends."""

    @abstractmethod
    def create_screen(self, config: ScreenConfig) -> ScreenBackend:
        """Create a new backend configured for one Screen."""
        raise NotImplementedError


class RuntimeAlreadyConfiguredError(RuntimeError):
    """Raised when code tries to replace the selected runtime."""


class BackendTerminated(RuntimeError):
    """Raised when a backend can no longer process frames or events."""


_runtime = None
_runtime_locked = False


def _require_runtime(candidate) -> Runtime:
    if not isinstance(candidate, Runtime):
        raise TypeError('runtime must be an instance of Runtime')
    return candidate


def install_runtime(runtime: Runtime) -> None:
    """Install a host runtime before the first Screen is created.

    Normal local applications never call this function.  It is the extension
    seam used by an external host, such as the website's browser bootstrap.
    """

    global _runtime

    _require_runtime(runtime)
    if _runtime_locked:
        raise RuntimeAlreadyConfiguredError(
            'the runtime is locked because a Screen has already been created'
        )
    if _runtime is not None:
        raise RuntimeAlreadyConfiguredError('a runtime is already installed')
    _runtime = runtime


def _resolve_runtime(default_factory: Callable[[], Runtime]) -> Runtime:
    """Resolve and lock the runtime used by all Screens in this process."""

    global _runtime, _runtime_locked

    if _runtime is None:
        if not callable(default_factory):
            raise TypeError('default runtime factory must be callable')
        _runtime = _require_runtime(default_factory())

    _runtime_locked = True
    return _runtime


def _create_screen_backend(
        config: ScreenConfig,
        default_runtime_factory: Callable[[], Runtime]) -> ScreenBackend:
    """Create a backend through the selected runtime.

    This is internal until Screen is connected to it in the Tk-adapter step.
    Keeping the default factory as an argument lets runtime.py stay entirely
    platform-neutral and ensures an installed host runtime wins without
    importing the local backend.
    """

    if not isinstance(config, ScreenConfig):
        raise TypeError('config must be an instance of ScreenConfig')

    backend = _resolve_runtime(default_runtime_factory).create_screen(config)
    if not isinstance(backend, ScreenBackend):
        raise TypeError('Runtime.create_screen() must return a ScreenBackend')
    return backend


__all__ = [
    'BackendTerminated',
    'Runtime',
    'RuntimeAlreadyConfiguredError',
    'ScreenBackend',
    'ScreenConfig',
    'install_runtime',
]
