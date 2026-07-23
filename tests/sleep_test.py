"""Headless tests for Screen.sleep() frame pacing and delta timing."""

import math
import unittest
from unittest.mock import patch

from pydraw import Screen
from pydraw.errors import InvalidArgumentError


class FakeClock:
    """Controllable monotonic clock whose sleep advances simulated time."""

    def __init__(self, now=0.0):
        self.now = now
        self.sleeps = []
        self.oversleep = 0.0

    def perf_counter(self):
        return self.now

    def sleep(self, delay):
        self.sleeps.append(delay)
        self.now += delay + self.oversleep
        self.oversleep = 0.0

    def advance(self, duration):
        self.now += duration


class ScreenSleepTest(unittest.TestCase):

    def setUp(self):
        # sleep() only needs its two timing fields, so no Tk window is required.
        self.screen = Screen.__new__(Screen)
        self.screen._last_frame_time = None
        self.screen._next_frame_time = None
        self.clock = FakeClock(10.0)
        self.perf_counter_patch = patch(
            'pydraw.screen.time.perf_counter',
            side_effect=self.clock.perf_counter
        )
        self.sleep_patch = patch(
            'pydraw.screen.time.sleep',
            side_effect=self.clock.sleep
        )
        self.perf_counter_patch.start()
        self.sleep_patch.start()

    def tearDown(self):
        self.sleep_patch.stop()
        self.perf_counter_patch.stop()

    def test_regular_sleep_waits_full_delay_and_resets_delta_state(self):
        self.screen._last_frame_time = 8.0
        self.screen._next_frame_time = 10.5

        result = self.screen.sleep(0.25)

        self.assertIsNone(result)
        self.assertEqual(self.clock.sleeps, [0.25])
        self.assertIsNone(self.screen._last_frame_time)
        self.assertIsNone(self.screen._next_frame_time)

    def test_first_delta_sleep_returns_nominal_frame_time(self):
        result = self.screen.sleep(0.02, delta=True)

        self.assertAlmostEqual(result, 0.02)
        self.assertEqual(len(self.clock.sleeps), 1)
        self.assertAlmostEqual(self.clock.sleeps[0], 0.02)
        self.assertAlmostEqual(self.screen._last_frame_time, 10.02)
        self.assertAlmostEqual(self.screen._next_frame_time, 10.02)

    def test_delta_sleep_uses_only_remaining_frame_budget(self):
        self.screen.sleep(0.02, delta=True)
        self.clock.advance(0.005)

        result = self.screen.sleep(0.02, delta=True)

        self.assertAlmostEqual(self.clock.sleeps[-1], 0.015)
        self.assertAlmostEqual(result, 0.02)

    def test_small_overrun_is_corrected_by_the_next_deadline(self):
        self.screen.sleep(0.01, delta=True)
        self.clock.advance(0.015)

        late_frame = self.screen.sleep(0.01, delta=True)

        self.assertEqual(len(self.clock.sleeps), 1)
        self.assertAlmostEqual(self.clock.sleeps[0], 0.01)
        self.assertAlmostEqual(late_frame, 0.015)

        self.clock.advance(0.002)
        corrected_frame = self.screen.sleep(0.01, delta=True)

        self.assertAlmostEqual(self.clock.sleeps[-1], 0.003)
        self.assertAlmostEqual(corrected_frame, 0.005)

    def test_long_overrun_resets_deadline_without_catch_up_burst(self):
        self.screen.sleep(0.01, delta=True)
        self.clock.advance(0.025)

        result = self.screen.sleep(0.01, delta=True)

        self.assertAlmostEqual(self.clock.sleeps[-1], 0.01)
        self.assertAlmostEqual(self.screen._next_frame_time, 10.045)
        self.assertAlmostEqual(result, 0.035)

    def test_returned_delta_includes_clock_oversleep(self):
        self.screen.sleep(0.01, delta=True)
        self.clock.advance(0.002)
        self.clock.oversleep = 0.003

        result = self.screen.sleep(0.01, delta=True)

        self.assertAlmostEqual(self.clock.sleeps[-1], 0.008)
        self.assertAlmostEqual(result, 0.013)

    def test_regular_sleep_starts_a_new_delta_sequence(self):
        self.screen.sleep(0.01, delta=True)
        self.screen.sleep(0.5)
        result = self.screen.sleep(0.02, delta=True)

        self.assertAlmostEqual(result, 0.02)
        self.assertAlmostEqual(self.clock.sleeps[-1], 0.02)

    def test_invalid_arguments_are_rejected(self):
        for delay in (-1, math.inf, -math.inf, math.nan, 10 ** 1000, None, 'fast'):
            with self.subTest(delay=delay):
                with self.assertRaises(InvalidArgumentError):
                    self.screen.sleep(delay)

        for delta in (None, 0, 1, 'yes'):
            with self.subTest(delta=delta):
                with self.assertRaises(InvalidArgumentError):
                    self.screen.sleep(0.01, delta=delta)


if __name__ == '__main__':
    unittest.main()
