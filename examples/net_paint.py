"""
Shared paint -- the Tier 1 showcase for pydraw.network.

There is no Room and no server code here at all. Players just tell each other what
they drew (net.send) and listen for what everyone else drew (networkevent). This is
the whole of Tier 1: two ideas on top of an ordinary pydraw program.

Run it:

    PYTHONPATH=~/Projects/pydraw python3 net_paint.py            # hosts + draws
    PYTHONPATH=~/Projects/pydraw python3 net_paint.py <address>  # joins

Drag to draw. 1-6 pick a color, [ ] change the brush, C clears, Z undoes your
own last stroke.
"""

import sys

from pydraw import *
from pydraw.network import *

HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'

PALETTE = [Color('black'), Color('red'), Color('orange'),
           Color('green'), Color('blue'), Color('purple')]
WIDTHS = [2, 4, 8, 16]
color_index, width_index = 0, 1

# One pen per stroke, kept per player so everyone can draw at once and undo only
# their own work -- exactly like the single-player example.
active = {}     # player id -> the pen they're drawing with now
strokes = {}    # player id -> their finished pens

screen = Screen(800, 600, 'Shared Paint')
screen.color(Color('white'))

# Tier 1 needs no Room; a bare Network still gives us a host and a player id.
net = Network(screen, HOST, room=Room)   # the empty base Room = "just relay"

screen.title(f'Shared Paint -- player {net.id}')
Text(screen, f'You are player {net.id}', 10, 10, Color('black'), size=18)
Text(screen, '1-6 color   [ ] brush   C clear   Z undo', 10, 36, Color('gray'))


def current_color():
    return PALETTE[color_index]


def current_width():
    return WIDTHS[width_index]


# --- One place draws every stroke, mine or anyone else's --------------------

def apply(pid, name, data):
    if name == 'begin':
        pen = Pen(screen, data['x'], data['y'], data['c'], data['w'])
        pen.start()
        active[pid] = pen
    elif name == 'point':
        pen = active.get(pid)
        if pen is not None:
            pen.moveto(data['x'], data['y'])
    elif name == 'end':
        pen = active.pop(pid, None)
        if pen is not None:
            pen.stop()
            strokes.setdefault(pid, []).append(pen)
    elif name == 'clear':
        for pen in active.values():
            pen.stop()
            pen.clear()
        active.clear()
        for finished in strokes.values():
            for pen in finished:
                pen.clear()
        strokes.clear()
    elif name == 'undo':
        finished = strokes.get(pid)
        if finished:
            finished.pop().clear()


def do(name, **data):
    """Draw it here now, and tell everyone else (keep=True so late joiners see it)."""
    apply(net.id, name, data)
    net.send(name, keep=True, **data)


def networkevent(name, data, sender):
    apply(sender, name, data)


# --- Input: same handlers as the single-player example ----------------------

def mousedown(location, button):
    if button == 1:
        # The Color goes as itself -- no taking it apart and putting it back
        # together at the other end. See pydraw/serial.py.
        do('begin', x=location.x(), y=location.y(),
           c=current_color(), w=current_width())


def mousedrag(location, button):
    if button == 1 and net.id in active:
        do('point', x=location.x(), y=location.y())


def mouseup(location, button):
    if button == 1:
        finish_stroke()


def finish_stroke():
    if net.id in active:
        do('end')


def keydown(key):
    global color_index, width_index
    if key in ('1', '2', '3', '4', '5', '6'):
        color_index = int(str(key)) - 1
    elif key == '[':
        width_index = max(0, width_index - 1)
    elif key == ']':
        width_index = min(len(WIDTHS) - 1, width_index + 1)
    elif key == 'c':
        finish_stroke()
        do('clear')
    elif key == 'z':
        finish_stroke()
        do('undo')


screen.listen()

fps = 30
running = True
while running:
    screen.update()     # pumps the network too; loop is otherwise unchanged
    screen.sleep(1 / fps)

net.close()
screen.exit()
