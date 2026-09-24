#!/usr/bin/env python3
"""Compare compound movement with individual updates on the real Tk canvas."""

import argparse
import json
import math
import os
import statistics
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydraw import Rectangle, Screen  # noqa: E402
from pydraw.compound import CompoundObject  # noqa: E402


def summarize(samples):
    samples = sorted(samples)
    return {
        'median_ms': statistics.median(samples),
        'p95_ms': samples[round((len(samples) - 1) * 0.95)],
        'total_ms': sum(samples),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--objects', type=int, default=200)
    parser.add_argument('--frames', type=int, default=120)
    parser.add_argument('--repeats', type=int, default=4)
    args = parser.parse_args()
    if args.objects < 1 or args.frames < 2 or args.repeats < 1:
        parser.error('objects and repeats must be positive; frames must be at least 2')

    screen = Screen(640, 480, 'pyDraw compound benchmark')
    try:
        columns = math.ceil(math.sqrt(args.objects * 640 / 480))
        rows = math.ceil(args.objects / columns)
        cell_width = 620 / columns
        cell_height = 460 / rows
        rectangles = [
            Rectangle(screen, 10 + (index % columns) * cell_width,
                      10 + (index // columns) * cell_height,
                      cell_width * 0.6, cell_height * 0.6)
            for index in range(args.objects)
        ]
        compound = CompoundObject(*rectangles)
        screen.update()
        backend_samples = []
        present = screen._backend.present

        def timed_present(batch):
            started = time.perf_counter()
            present(batch)
            backend_samples.append((time.perf_counter() - started) * 1000)

        screen._backend.present = timed_present

        def measure(grouped, frames):
            mutation = []
            presentation = []
            backend_start = len(backend_samples)
            for frame in range(frames):
                dx = 1 if frame % 2 == 0 else -1
                started = time.perf_counter()
                if grouped:
                    compound.move(dx, 0)
                else:
                    for rectangle in rectangles:
                        rectangle.move(dx, 0)
                mutated = time.perf_counter()
                screen.update()
                finished = time.perf_counter()
                mutation.append((mutated - started) * 1000)
                presentation.append((finished - mutated) * 1000)
            return mutation, presentation, backend_samples[backend_start:]

        measure(True, 20)
        measure(False, 20)

        results = {'compound': [[], [], []], 'individual': [[], [], []]}
        for repeat in range(args.repeats):
            modes = ('compound', 'individual') if repeat % 2 == 0 else ('individual', 'compound')
            for mode in modes:
                mutation, presentation, backend = measure(mode == 'compound', args.frames)
                results[mode][0].extend(mutation)
                results[mode][1].extend(presentation)
                results[mode][2].extend(backend)

        output = {'objects': args.objects, 'frames_per_mode': args.frames * args.repeats}
        for mode, (mutation, presentation, backend) in results.items():
            output[mode] = {
                'mutation': summarize(mutation),
                'screen_update': summarize(presentation),
                'backend_present': summarize(backend),
                'combined': summarize([a + b for a, b in zip(mutation, presentation)]),
            }
        print(json.dumps(output, indent=2))
    finally:
        screen._backend.close()


if __name__ == '__main__':
    main()
