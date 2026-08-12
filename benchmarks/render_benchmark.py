#!/usr/bin/env python3
"""Measure native retained-render workloads."""

import argparse
import json
import os
import statistics
import sys
import time


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from pydraw import Image, Line, Pen, Rectangle, Screen, Text  # noqa: E402


IMAGE_PATH = os.path.join(REPO_ROOT, 'images', 'earth.png')


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
        'total_ms': sum(values),
    }


def measure(repetitions, operation):
    samples = []
    for index in range(repetitions):
        started = time.perf_counter()
        operation(index)
        samples.append((time.perf_counter() - started) * 1000)
    return summarize(samples)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frames', type=int, default=300)
    parser.add_argument('--objects', type=int, default=500)
    args = parser.parse_args()

    screen = Screen(640, 480, 'pyDraw render benchmark')
    screen.update()

    idle = measure(args.frames, lambda index: screen.update())

    canvas = screen._backend.canvas
    direct_item = canvas.create_line(-100, 0, 100, 0)

    def direct_frame(index):
        offset = index % 2
        canvas.coords(direct_item, -100 + offset, 0, 100 + offset, 0)
        screen.update()

    direct_line = measure(args.frames, direct_frame)
    canvas.delete(direct_item)

    line = Line(screen, 220, 240, 420, 240)
    screen.update()

    def retained_frame(index):
        line.move(1 if index % 2 == 0 else -1, 0)
        screen.update()

    retained_line = measure(args.frames, retained_frame)
    line.remove()
    screen.update()

    direct_item = canvas.create_polygon(-100, -20, 100, -20, 100, 20, -100, 20)

    def direct_polygon_frame(index):
        offset = index % 2
        canvas.coords(
            direct_item,
            -100 + offset, -20,
            100 + offset, -20,
            100 + offset, 20,
            -100 + offset, 20,
        )
        screen.update()

    direct_polygon = measure(args.frames, direct_polygon_frame)
    canvas.delete(direct_item)

    rectangle = Rectangle(screen, 220, 220, 200, 40)
    screen.update()

    def retained_polygon_frame(index):
        rectangle.move(1 if index % 2 == 0 else -1, 0)
        screen.update()

    retained_polygon = measure(args.frames, retained_polygon_frame)
    rectangle.remove()
    screen.update()

    direct_item = canvas.create_text(
        -100,
        0,
        text='retained text',
        anchor='nw',
        font=('Arial', -16),
    )

    def direct_text_frame(index):
        offset = index % 2
        canvas.coords(direct_item, -100 + offset, 0)
        screen.update()

    direct_text = measure(args.frames, direct_text_frame)
    canvas.delete(direct_item)

    text = Text(screen, 'retained text', 220, 240)
    screen.update()

    def retained_text_frame(index):
        text.move(1 if index % 2 == 0 else -1, 0)
        screen.update()

    retained_text = measure(args.frames, retained_text_frame)
    text.remove()
    screen.update()

    direct_image_ref = screen._backend.tk.PhotoImage(file=IMAGE_PATH)
    direct_item = canvas.create_image(0, 0, image=direct_image_ref)

    def direct_image_frame(index):
        offset = index % 2
        canvas.coords(direct_item, offset, 0)
        screen.update()

    direct_image = measure(args.frames, direct_image_frame)
    canvas.delete(direct_item)

    image = Image(screen, IMAGE_PATH, 220, 180)
    screen.update()

    def retained_image_frame(index):
        image.move(1 if index % 2 == 0 else -1, 0)
        screen.update()

    retained_image = measure(args.frames, retained_image_frame)
    image.remove()
    screen.update()

    lines = [
        Line(screen, 0, index % 480, 40, index % 480)
        for index in range(args.objects)
    ]
    started = time.perf_counter()
    screen.update()
    create_many_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    for line in lines:
        line.move(1, 0)
    mutate_many_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    screen.update()
    present_many_ms = (time.perf_counter() - started) * 1000

    for line in lines:
        line.remove()
    screen.update()

    rectangles = [
        Rectangle(screen, index % 600, index % 440, 20, 20)
        for index in range(args.objects)
    ]
    started = time.perf_counter()
    screen.update()
    create_many_rectangles_ms = (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    for rectangle in rectangles:
        rectangle.move(1, 0)
    mutate_many_rectangles_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    screen.update()
    present_many_rectangles_ms = (time.perf_counter() - started) * 1000

    for rectangle in rectangles:
        rectangle.remove()
    screen.update()

    pen = Pen(screen, 10, 10)
    pen.start()
    screen.update()

    def pen_frame(index):
        pen.moveto(10 + index % 620, 10 + index % 460)
        screen.update()

    pen_growth = measure(min(args.frames, 500), pen_frame)
    pen.clear()
    screen.update()

    print(json.dumps({
        'idle_update': idle,
        'direct_canvas_line_frame': direct_line,
        'retained_pydraw_line_frame': retained_line,
        'direct_canvas_polygon_frame': direct_polygon,
        'retained_pydraw_rectangle_frame': retained_polygon,
        'direct_canvas_text_frame': direct_text,
        'retained_pydraw_text_frame': retained_text,
        'direct_canvas_image_frame': direct_image,
        'retained_pydraw_image_frame': retained_image,
        'create_many_lines': {
            'objects': args.objects,
            'present_ms': create_many_ms,
        },
        'move_many_lines_one_frame': {
            'objects': args.objects,
            'mutation_ms': mutate_many_ms,
            'present_ms': present_many_ms,
            'total_ms': mutate_many_ms + present_many_ms,
        },
        'create_many_rectangles': {
            'objects': args.objects,
            'present_ms': create_many_rectangles_ms,
        },
        'move_many_rectangles_one_frame': {
            'objects': args.objects,
            'mutation_ms': mutate_many_rectangles_ms,
            'present_ms': present_many_rectangles_ms,
            'total_ms': mutate_many_rectangles_ms + present_many_rectangles_ms,
        },
        'growing_pen_frame': pen_growth,
    }, indent=2))

    screen._backend.root.destroy()


if __name__ == '__main__':
    main()
