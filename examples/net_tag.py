"""Multiplayer tag with no custom Room.

Each client owns its position and trusts tag events from other players.

Run it:

    PYTHONPATH=~/Projects/pydraw python3 net_tag.py            # hosts + plays
    PYTHONPATH=~/Projects/pydraw python3 net_tag.py <address>  # joins

WASD or the arrows to run; if you are IT, touch somebody to pass it on.
"""

import random
import sys

from pydraw import *
from pydraw.network import *

WIDTH = 800
HEIGHT = 600

SIZE = 36
SPEED = 4
REACH = 34
GRACE = 45

IT = Color('red')
RUNNER = Color('cornflowerblue')

HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'

screen = Screen(WIDTH, HEIGHT, 'Tag')
screen.color(Color('gray20'))

net = Network(screen, HOST, room=Room)
net.smooth('x', 'y')

net.mine['x'] = random.randint(SIZE, WIDTH - SIZE)
net.mine['y'] = random.randint(SIZE, HEIGHT - SIZE)

if net.id == 1:
    net.mine['it'] = True
else:
    net.mine['it'] = False

screen.title(f'Tag -- player {net.id}')
banner = Text(screen, '', 10, 10, Color('white'), size=18)

me = Oval(screen, 0, 0, SIZE, SIZE, RUNNER)
me.border(Color('white'), 3)

circles = {}
held = []
grace = 0


def keydown(key):
    key = str(key)
    if key not in held:
        held.append(key)


def keyup(key):
    key = str(key)
    if key in held:
        held.remove(key)


def playerquit(pid):
    if pid in circles:
        circles[pid].remove()
        del circles[pid]


def networkevent(name, data, sender):
    global grace

    if name == 'tag' and data['who'] == net.id:
        net.mine['it'] = True
        grace = GRACE


def run():
    x = net.mine['x']
    y = net.mine['y']

    if 'a' in held or 'left' in held:
        x = x - SPEED
    if 'd' in held or 'right' in held:
        x = x + SPEED
    if 'w' in held or 'up' in held:
        y = y - SPEED
    if 's' in held or 'down' in held:
        y = y + SPEED

    # Stay inside the window.
    if x < SIZE:
        x = SIZE
    if x > WIDTH - SIZE:
        x = WIDTH - SIZE
    if y < SIZE:
        y = SIZE
    if y > HEIGHT - SIZE:
        y = HEIGHT - SIZE

    net.mine['x'] = x
    net.mine['y'] = y


def try_tag():
    global grace

    if grace > 0:
        grace = grace - 1
        return

    if not net.mine['it']:
        return

    here = Location(net.mine['x'], net.mine['y'])

    for pid, other in net.others():
        there = Location(other['x'], other['y'])
        if here.distance(there) < REACH:
            net.mine['it'] = False
            net.send('tag', who=pid)
            return


def draw():
    me.moveto(net.mine['x'] - SIZE / 2, net.mine['y'] - SIZE / 2)
    if net.mine['it']:
        me.color(IT)
    else:
        me.color(RUNNER)

    for pid, other in net.others():
        if pid not in circles:
            circles[pid] = Oval(screen, 0, 0, SIZE, SIZE, RUNNER)

        circle = circles[pid]
        circle.moveto(other['x'] - SIZE / 2, other['y'] - SIZE / 2)
        if other['it']:
            circle.color(IT)
        else:
            circle.color(RUNNER)

    if net.mine['it']:
        banner.text('YOU ARE IT -- run somebody down')
    else:
        banner.text('Run! Red is it.')


screen.listen()

running = True
while running:
    run()
    try_tag()
    draw()

    screen.update()     # also pumps the network
    screen.sleep(1 / 60)

net.close()
screen.exit()
