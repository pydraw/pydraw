import math
import unittest
from unittest import mock

import pydraw.runtime as runtime_module
from pydraw import Image, Screen
from pydraw.backends.recording import RecordingRuntime
from pydraw.backends.tk import TkBackend
from pydraw.errors import InvalidArgumentError
from pydraw.runtime import (
    Runtime,
    RuntimeAlreadyConfiguredError,
    ScreenBackend,
    ScreenConfig,
    install_runtime,
)


class FakeBackend(ScreenBackend):

    def __init__(self, config):
        self.config = config
        self.presented = []
        self.closed = False
        self.handlers = ()
        self.frame_durations = []

    def poll_events(self):
        return ()

    def listen(self):
        pass

    def set_handlers(self, handlers):
        self.handlers = tuple(handlers)

    def present(self, frame):
        self.presented.append(frame)

    def set_title(self, title):
        self.title = title

    def set_background(self, color):
        self.background = color

    def set_background_image(self, source):
        self.background_image = source

    def canvas_size(self):
        return self.config.width, self.config.height

    def window_size(self):
        return self.canvas_size()

    def resize(self, width, height):
        pass

    def set_fullscreen(self, fullscreen):
        return fullscreen

    def alert(self, text, title, accept_text, cancel_text):
        return True

    def prompt(self, text, title):
        return None

    def grab(self, filename):
        return filename

    def measure_text(self, text, font, size, bold, italic):
        return len(text) * size, size

    def measure_image(self, source):
        return 100, 100

    def image_frames(self, source):
        return 1

    def run(self, step, frame_duration):
        self.frame_durations.append(frame_duration)
        step()

    def close(self):
        self.closed = True


class FakeRuntime(Runtime):

    def __init__(self):
        self.configs = []
        self.backends = []

    def create_screen(self, config):
        backend = FakeBackend(config)
        self.configs.append(config)
        self.backends.append(backend)
        return backend


class ScheduledRoot:
    """Small foreground scheduler used to exercise Tk pacing without Tk."""

    def __init__(self):
        self.delays = []
        self.callbacks = []
        self.quitting = False

    def after(self, delay, callback):
        handle = len(self.delays) + 1
        self.delays.append(delay)
        self.callbacks.append((handle, callback))
        return handle

    def after_cancel(self, handle):
        pass

    def mainloop(self):
        while self.callbacks and not self.quitting:
            _, callback = self.callbacks.pop(0)
            callback()

    def quit(self):
        self.quitting = True


class FakeTk:
    class TclError(Exception):
        pass


class RuntimeRegistryTest(unittest.TestCase):

    def setUp(self):
        self.runtime_state = mock.patch.multiple(
            runtime_module,
            _runtime=None,
            _runtime_locked=False,
        )
        self.runtime_state.start()

    def tearDown(self):
        self.runtime_state.stop()

    def test_installed_runtime_wins_without_calling_local_default(self):
        installed = FakeRuntime()
        install_runtime(installed)
        config = ScreenConfig(640, 480, 'browser')
        default_factory = mock.Mock(side_effect=AssertionError(
            'the local runtime must remain lazy'
        ))

        backend = runtime_module._create_screen_backend(
            config,
            default_factory,
        )

        self.assertIs(backend, installed.backends[0])
        self.assertEqual(installed.configs, [config])
        default_factory.assert_not_called()

    def test_default_runtime_is_created_lazily_once(self):
        local_runtime = FakeRuntime()
        default_factory = mock.Mock(return_value=local_runtime)

        first = runtime_module._create_screen_backend(
            ScreenConfig(320, 200, 'first'),
            default_factory,
        )
        second = runtime_module._create_screen_backend(
            ScreenConfig(800, 600, 'second'),
            default_factory,
        )

        default_factory.assert_called_once_with()
        self.assertIsNot(first, second)
        self.assertEqual(len(local_runtime.backends), 2)

    def test_runtime_locks_when_the_first_backend_is_requested(self):
        runtime_module._create_screen_backend(
            ScreenConfig(320, 200, 'local'),
            lambda: FakeRuntime(),
        )

        with self.assertRaises(RuntimeAlreadyConfiguredError):
            install_runtime(FakeRuntime())

    def test_installing_twice_is_rejected_before_screen_creation(self):
        install_runtime(FakeRuntime())

        with self.assertRaises(RuntimeAlreadyConfiguredError):
            install_runtime(FakeRuntime())

    def test_runtime_must_return_a_screen_backend(self):
        class InvalidRuntime(Runtime):
            def create_screen(self, config):
                return object()

        install_runtime(InvalidRuntime())

        with self.assertRaises(TypeError):
            runtime_module._create_screen_backend(
                ScreenConfig(320, 200, 'invalid'),
                lambda: FakeRuntime(),
            )

    def test_screen_constructs_without_tk_native_backend_aliases(self):
        installed = RecordingRuntime()
        install_runtime(installed)

        screen = Screen(320, 200, 'browser')

        self.assertFalse(hasattr(screen, '_canvas'))
        self.assertFalse(hasattr(screen, '_root'))
        self.assertEqual(screen._dims(), (320, 200))

    def test_screen_publishes_registered_handlers_to_backend(self):
        installed = FakeRuntime()
        install_runtime(installed)
        screen = Screen(320, 200, 'browser')
        screen.registry.update({
            'keydown': lambda key: None,
            'mouseup': lambda: None,
        })

        screen._listen()

        self.assertEqual(
            installed.backends[0].handlers,
            ('keydown', 'mouseup'),
        )

    def test_backend_can_resolve_non_filesystem_image_sources(self):
        installed = RecordingRuntime()
        install_runtime(installed)
        screen = Screen(320, 200, 'browser')

        image = Image(screen, 'asset://sprite', 10, 20, 30, 40)
        screen.update()

        self.assertEqual(image.width(), 30)
        self.assertEqual(image.height(), 40)
        self.assertEqual(
            installed.backends[0].nodes[image._render_id].source,
            'asset://sprite',
        )

    def test_screen_loop_passes_default_and_explicit_frame_durations(self):
        installed = FakeRuntime()
        install_runtime(installed)
        screen = Screen(320, 200, 'paced')

        screen.loop()
        screen.loop(fps=120)

        self.assertEqual(len(installed.backends[0].frame_durations), 2)
        self.assertAlmostEqual(
            installed.backends[0].frame_durations[0], 1 / 60,
        )
        self.assertAlmostEqual(
            installed.backends[0].frame_durations[1], 1 / 120,
        )

    def test_screen_loop_rejects_invalid_fps(self):
        installed = FakeRuntime()
        install_runtime(installed)
        screen = Screen(320, 200, 'paced')

        invalid_values = (
            0, -1, math.inf, -math.inf, math.nan, 10 ** 1000,
            None, True, 'fast',
        )
        for fps in invalid_values:
            with self.subTest(fps=fps):
                with self.assertRaisesRegex(
                        InvalidArgumentError, 'finite, positive number'):
                    screen.loop(fps=fps)

        self.assertEqual(installed.backends[0].frame_durations, [])

    def test_tk_loop_waits_only_for_remaining_frame_budget(self):
        backend = TkBackend.__new__(TkBackend)
        backend.closed = False
        backend.running = False
        backend.root = ScheduledRoot()
        backend.tk = FakeTk()

        with mock.patch(
                'pydraw.backends.tk.time.perf_counter',
                side_effect=(10.0, 10.005)):
            backend.run(backend.root.quit, 0.02)

        self.assertEqual(backend.root.delays[0], 1)
        self.assertGreaterEqual(backend.root.delays[1], 15)
        self.assertLessEqual(backend.root.delays[1], 16)

    def test_tk_loop_does_not_add_frame_delay_after_long_overrun(self):
        backend = TkBackend.__new__(TkBackend)
        backend.closed = False
        backend.running = False
        backend.root = ScheduledRoot()
        backend.tk = FakeTk()

        with mock.patch(
                'pydraw.backends.tk.time.perf_counter',
                side_effect=(10.0, 10.05)):
            backend.run(backend.root.quit, 0.02)

        self.assertEqual(backend.root.delays, [1, 1])


if __name__ == '__main__':
    unittest.main()
