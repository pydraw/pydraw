"""
Tag -- you own your player. No Room, no server code.

net_paint told everyone what you *did*. This owns what you *are*: write net.mine
and that is your position, replicated to everyone. Read net.others()
for theirs. net.smooth() blends them between updates so they glide.

    net.mine['x'] = net.mine['x'] + 4    # move ME -> everyone sees it
    for pid, other in net.others():      # everyone else -> read-only

Run it:

    PYTHONPATH=~/Projects/pydraw python3 net_tag.py            # hosts + plays
    PYTHONPATH=~/Projects/pydraw python3 net_tag.py <address>  # joins

Run the first line again in another terminal for a second player on this machine.
WASD or the arrows to run; if you are IT, touch somebody to pass it on.

Being "it" is the one thing here not really yours to own: you set your own to
False and trust the other player to set theirs to True, so two players who tag in
the same frame can both end up it. That is the shape of a game with no authority
-- net_pong.py is the same idea with a Room that decides.
"""

import random
import sys

from pydraw import *
from pydraw.network import *

WIDTH = 800
HEIGHT = 600

SIZE = 36       # how wide each player's circle is
SPEED = 4       # how many pixels you move each frame
REACH = 34      # how close you have to be to tag somebody
GRACE = 45      # frames the new IT waits before they can tag back

IT = Color('red')
RUNNER = Color('cornflowerblue')

# Which machine to join. With no address we use this one, which means we host.
if len(sys.argv) > 1:
    HOST = sys.argv[1]
else:
    HOST = 'localhost'

screen = Screen(WIDTH, HEIGHT, 'Tag')
screen.color(Color('gray20'))

# No Room subclass -- the plain base Room just passes messages along, and that is
# all this game needs.
net = Network(screen, HOST, room=Room)
net.smooth('x', 'y')

# Start somewhere random, so nobody begins on top of anybody else. Writing
# net.mine is what sends your position to everybody else.
net.mine['x'] = random.randint(SIZE, WIDTH - SIZE)
net.mine['y'] = random.randint(SIZE, HEIGHT - SIZE)

# The first player in is it. Nobody decides that -- player 1 just starts with it.
if net.id == 1:
    net.mine['it'] = True
else:
    net.mine['it'] = False

screen.title(f'Tag -- player {net.id}')
banner = Text(screen, '', 10, 10, Color('white'), size=18)

me = Oval(screen, 0, 0, SIZE, SIZE, RUNNER)
me.border(Color('white'), 3)    # so you can tell which circle is yours

circles = {}    # other player's id -> the Oval we draw them with
held = []       # the keys being held down right now
grace = 0       # frames left before I am allowed to tag


def keydown(key):
    key = str(key)
    if key not in held:
        held.append(key)


def keyup(key):
    key = str(key)
    if key in held:
        held.remove(key)


def playerquit(pid):
    """Somebody left, so take their circle off the screen."""
    if pid in circles:
        circles[pid].remove()
        del circles[pid]


def networkevent(name, data, sender):
    """Somebody tagged somebody. If it was me, then I am it now."""
    global grace

    if name == 'tag' and data['who'] == net.id:
        net.mine['it'] = True
        grace = GRACE


def run():
    """Move me around. I own my position, so I just change net.mine."""
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
    """If I am it and I am touching somebody, pass it to them."""
    global grace

    if grace > 0:
        grace = grace - 1
        return

    if not net.mine['it']:
        return

    here = Location(net.mine['x'], net.mine['y'])

    for pid, other in net.others():
        # Smoothed, so this is where they were a moment ago rather than where they
        # are. Fine for tag: nobody minds a tag landing a whisker early or late. A
        # game where it matters gives the Room the last word -- net.call('tag', ...)
        # -- because the Room reads their real position.
        there = Location(other['x'], other['y'])
        if here.distance(there) < REACH:
            # I stop being it, and I ask them to start. They set their own 'it'
            # over in networkevent, because only they can write it.
            net.mine['it'] = False
            net.send('tag', who=pid)
            return


def draw():
    """Draw my circle, then everybody else's."""
    me.moveto(net.mine['x'] - SIZE / 2, net.mine['y'] - SIZE / 2)
    if net.mine['it']:
        me.color(IT)
    else:
        me.color(RUNNER)

    for pid, other in net.others():
        # Only players there is something to draw reach here, so their position is
        # always there to read.
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

    screen.update()     # this pumps the network too
    screen.sleep(1 / 60)

net.close()
screen.exit()
