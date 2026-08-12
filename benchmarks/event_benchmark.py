#!/usr/bin/env python3
"""Measure Tk input delivery through the platform-neutral event boundary."""

import argparse
import json
import os
import statistics
import sys
import time


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from pydraw import Screen  # noqa: E402


def summarize(samples):
    values = sorted(samples)

    def percentile(fraction):
        return values[round((len(values) - 1) * fraction)]

    return {
        'samples': len(values),
        'median_ms': statistics.median(values),
        'p95_ms': percentile(0.95),
        'p99_ms': percentile(0.99),
        'max_ms': values[-1],
    }


def widget_canvas(screen):
    return screen._backend.canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--events', type=int, default=300)
    args = parser.parse_args()

    screen = Screen(320, 200, 'pyDraw event benchmark')
    canvas = widget_canvas(screen)
    started = [0]
    explicit_samples = []

    def explicit_handler(location, button):
        explicit_samples.append((time.perf_counter() - started[0]) * 1000)

    screen.registry['mousedown'] = explicit_handler
    screen._listen()
    screen.update()

    for _ in range(args.events):
        started[0] = time.perf_counter()
        canvas.event_generate('<Button-1>', x=40, y=50)
        screen.update()

    loop_samples = []

    def emit():
        started[0] = time.perf_counter()
        canvas.event_generate('<Button-1>', x=40, y=50)

    def loop_handler(location, button):
        loop_samples.append((time.perf_counter() - started[0]) * 1000)
        if len(loop_samples) == args.events:
            screen._backend.root.after(1, screen._backend.root.quit)
        else:
            screen._backend.root.after(1, emit)

    screen.registry['mousedown'] = loop_handler
    screen._listen()
    screen._backend.root.after(1, emit)
    screen.loop()

    print(json.dumps({
        'explicit_update_input': summarize(explicit_samples),
        'screen_loop_input': summarize(loop_samples),
    }, indent=2))
    screen._backend.root.destroy()


if __name__ == '__main__':
    main()
