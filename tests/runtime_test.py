import unittest
from unittest import mock

import pydraw.runtime as runtime_module
from pydraw import Image, Screen
from pydraw.backends.recording import RecordingRuntime
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

    def poll_events(self):
        return ()

    def listen(self):
        pass

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
        pass

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

    def run(self, step):
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

        self.assertIsNone(screen._screen)
        self.assertIsNone(screen._canvas)
        self.assertIsNone(screen._root)
        self.assertEqual(screen._dims(), (320, 200))

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


if __name__ == '__main__':
    unittest.main()
