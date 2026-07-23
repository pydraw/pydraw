"""Animated sine and cosine waves on a simple Cartesian graph.

The curves are represented by short Line segments.  Every frame advances the
phase and updates the segment endpoints, which makes the waves appear to move
through the graph while the axes and grid stay in place.

Press Space to pause/resume and Q or Escape to quit.
"""

import math

from pydraw import Color, Line, Oval, Screen, Text


WIDTH = 900
HEIGHT = 600
FPS = 60
PHASE_SPEED = 2.7  # radians per second

GRAPH_LEFT = 70
GRAPH_RIGHT = WIDTH - 35
GRAPH_TOP = 90
GRAPH_BOTTOM = HEIGHT - 75
ORIGIN_X = (GRAPH_LEFT + GRAPH_RIGHT) / 2
ORIGIN_Y = (GRAPH_TOP + GRAPH_BOTTOM) / 2

# Four pi radians gives the viewer two complete cycles at once.
X_MIN = -2 * math.pi
X_MAX = 2 * math.pi
X_SCALE = (GRAPH_RIGHT - GRAPH_LEFT) / (X_MAX - X_MIN)
Y_SCALE = 105
AMPLITUDE = 1.0
SAMPLES = 130


screen = Screen(WIDTH, HEIGHT, "pydraw - Moving Sine and Cosine Waves")
screen.color(Color("midnight blue"))


def graph_x(value):
    """Convert a graph x-coordinate in radians to a screen x-coordinate."""
    return ORIGIN_X + value * X_SCALE


def graph_y(value):
    """Convert a graph y-coordinate to a screen y-coordinate."""
    return ORIGIN_Y - value * Y_SCALE


# --- Static graph -----------------------------------------------------------

grid_color = Color("gray")
axis_color = Color("white")

# Horizontal grid lines mark integer y-values; vertical lines mark pi/2 steps.
for y_value in range(-2, 3):
    y = graph_y(y_value)
    line = Line(screen, (GRAPH_LEFT, y), (GRAPH_RIGHT, y), grid_color)
    line.dashes(2)

for index in range(-4, 5):
    x_value = index * math.pi / 2
    x = graph_x(x_value)
    line = Line(screen, (x, GRAPH_TOP), (x, GRAPH_BOTTOM), grid_color)
    line.dashes(2)

x_axis = Line(screen, (GRAPH_LEFT, ORIGIN_Y), (GRAPH_RIGHT, ORIGIN_Y), axis_color, thickness=2)
y_axis = Line(screen, (ORIGIN_X, GRAPH_TOP), (ORIGIN_X, GRAPH_BOTTOM), axis_color, thickness=2)

Text(screen, "y", ORIGIN_X + 10, GRAPH_TOP - 8, color=axis_color, size=15)
Text(screen, "x (radians)", GRAPH_RIGHT - 90, ORIGIN_Y + 12, color=axis_color, size=13)
Text(screen, "Sine and cosine waves", GRAPH_LEFT, 20, color=Color("white"), size=22)
Text(screen, "phase shifts both curves over time", GRAPH_LEFT, 50,
     color=Color("light gray"), size=13)

for y_value in (-2, -1, 1, 2):
    Text(screen, str(y_value), ORIGIN_X + 8, graph_y(y_value) - 8,
         color=Color("light gray"), size=11)

for index in (-4, -2, 2, 4):
    x_value = index * math.pi / 2
    label = {-4: "-2pi", -2: "-pi", 2: "pi", 4: "2pi"}[index]
    Text(screen, label, graph_x(x_value) - 15, ORIGIN_Y + 8,
         color=Color("light gray"), size=10)

Text(screen, "sin(x + phase)", GRAPH_LEFT + 10, GRAPH_BOTTOM + 20,
     color=Color("cyan"), size=13)
Text(screen, "cos(x + phase)", GRAPH_LEFT + 155, GRAPH_BOTTOM + 20,
     color=Color("orange"), size=13)
Text(screen, "Space: pause    Q/Esc: quit", GRAPH_RIGHT - 195, GRAPH_BOTTOM + 20,
     color=Color("light gray"), size=11)


def make_segments(color):
    """Create a polyline as many short Line objects."""
    segments = []
    step = (GRAPH_RIGHT - GRAPH_LEFT) / SAMPLES
    for index in range(SAMPLES):
        x1 = GRAPH_LEFT + index * step
        x2 = x1 + step
        segments.append(Line(screen, (x1, ORIGIN_Y), (x2, ORIGIN_Y), color, thickness=2))
    return segments


sine_segments = make_segments(Color("cyan"))
cosine_segments = make_segments(Color("orange"))

# A moving probe makes the current phase easy to follow.
probe = Line(screen, (GRAPH_LEFT, GRAPH_TOP), (GRAPH_LEFT, GRAPH_BOTTOM), Color("light gray"))
probe.dashes(3)
sine_dot = Oval(screen, GRAPH_LEFT - 5, ORIGIN_Y - 5, 10, 10,
                color=Color("cyan"), border=Color("white"))
cosine_dot = Oval(screen, GRAPH_LEFT - 5, ORIGIN_Y - 5, 10, 10,
                  color=Color("orange"), border=Color("white"))
status = Text(screen, "", GRAPH_RIGHT - 190, 24, color=Color("white"), size=12)


def update_wave(segments, function, phase):
    """Move each segment endpoint to the function's current graph position."""
    step = (GRAPH_RIGHT - GRAPH_LEFT) / SAMPLES
    for index, segment in enumerate(segments):
        x1 = GRAPH_LEFT + index * step
        x2 = x1 + step
        value1 = AMPLITUDE * function((x1 - ORIGIN_X) / X_SCALE + phase)
        value2 = AMPLITUDE * function((x2 - ORIGIN_X) / X_SCALE + phase)
        segment.moveto(x1, graph_y(value1), x2, graph_y(value2))


def keydown(key):
    global running, paused
    if str(key).lower() in ("q", "escape"):
        running = False
    elif str(key).lower() == "space":
        paused = not paused


screen.listen()

running = True
paused = False
phase = 0.0
dt = 1 / FPS
last_probe_x = GRAPH_LEFT

while running:
    if not paused:
        # Advancing phase makes both curves travel leftward through the graph.
        phase += PHASE_SPEED * dt
        update_wave(sine_segments, math.sin, phase)
        update_wave(cosine_segments, math.cos, phase)

        probe_x = GRAPH_LEFT + ((phase % (X_MAX - X_MIN)) / (X_MAX - X_MIN)) * (GRAPH_RIGHT - GRAPH_LEFT)
        probe.move(probe_x - last_probe_x, 0)
        last_probe_x = probe_x

        graph_value = (probe_x - ORIGIN_X) / X_SCALE + phase
        sine_y = graph_y(AMPLITUDE * math.sin(graph_value))
        cosine_y = graph_y(AMPLITUDE * math.cos(graph_value))
        sine_dot.center(probe_x, sine_y)
        cosine_dot.center(probe_x, cosine_y)
        status.text(f"phase: {phase % (2 * math.pi):4.2f} rad")

    screen.update()
    dt = screen.sleep(1 / FPS, delta=True)

screen.exit()
