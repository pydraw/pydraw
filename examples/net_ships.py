"""Asteroids PvP: a simple multiplayer game where players trust each other.

Each client owns its ship, health, and score. There is no custom Room.

Run it:

    PYTHONPATH=~/Projects/pydraw python3 net_ships.py
    PYTHONPATH=~/Projects/pydraw python3 net_ships.py <address>

WASD / arrows to fly. SPACE fires.
"""

import math
import sys

from pydraw import *
from pydraw.network import *

WIDTH, HEIGHT = 800, 600
RANGE = 140
FIRE_DELAY = 30
HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'

SPAWNS = (
    (100, 100, 135),
    (700, 500, 315),
    (700, 100, 225),
    (100, 500, 45),
    (400, 100, 180),
    (400, 500, 0),
    (100, 300, 90),
    (700, 300, 270),
)


def heading(a):
    """Return the direction a ship is facing."""
    rad = math.radians(a)
    return math.sin(rad), -math.cos(rad)


screen = Screen(WIDTH, HEIGHT, 'Asteroids PvP')
screen.color(Color('black'))

net = Network(screen, HOST, room=Room)
net.smooth('x', 'y')
net.smooth_angle('a')

x, y, a = SPAWNS[(net.id - 1) % len(SPAWNS)]
net.mine.update(x=x, y=y, a=a, hp=100, kills=0)

screen.title(f'Asteroids PvP -- player {net.id}')

my_ship = Polygon(screen, 3, x, y, 22, 22, Color('cyan'))
sprites = {}
held = set()
leaderboard = Text(screen, 'KILLS', WIDTH - 170, 15, Color('white'), size=14)

fire_lines = []
fire_cooldown = 0


def sprite_for(pid):
    if pid not in sprites:
        ship = Polygon(screen, 3, 0, 0, 22, 22, Color('red'))
        bar = Rectangle(screen, 0, 0, 30, 4, Color('lime'))
        sprites[pid] = (ship, bar)
    return sprites[pid]


def place(ship, bar, x, y, a, hp):
    ship.moveto(x - 11, y - 11)
    ship.rotation(a)
    bar.moveto(x - 15, y - 20)
    bar.width(max(0, 30 * hp / 100))
    bar.color(Color('lime') if hp > 40 else Color('red'))


def target_hit_by(line):
    closest = None
    closest_distance = RANGE + 1

    for pid, (ship, _) in sprites.items():
        if not line.intersects(ship):
            continue
        distance = my_ship.distance(ship)
        if distance < closest_distance:
            closest = pid
            closest_distance = distance

    return closest


def respawn():
    x, y, a = SPAWNS[(net.id - 1) % len(SPAWNS)]
    net.mine.update(x=x, y=y, a=a, hp=100)


def keydown(key):
    global fire_cooldown

    key = str(key)
    if key != 'space':
        held.add(key)
        return

    if fire_cooldown == 0:
        line = draw_fire_line(my_ship)
        net.send('fire', target=target_hit_by(line))
        fire_cooldown = FIRE_DELAY


def keyup(key):
    held.discard(str(key))


def networkevent(name, data, sender):
    if name == 'fire':
        if sender in sprites:
            draw_fire_line(sprites[sender][0])

        # Each player trusts the others and updates their own health.
        if data['target'] == net.id:
            net.mine['hp'] -= 20
            if net.mine['hp'] <= 0:
                net.send('score', player=sender)
                respawn()

    elif name == 'score' and data['player'] == net.id:
        net.mine['kills'] += 1


def fly():
    a = net.mine['a']
    if 'a' in held or 'left' in held:  net.mine['a'] = a - 4
    if 'd' in held or 'right' in held: net.mine['a'] = a + 4
    if 'w' in held or 'up' in held:
        dx, dy = heading(net.mine['a'])
        net.mine['x'] += 4 * dx
        net.mine['y'] += 4 * dy


def update_leaderboard():
    scores = [(net.mine['kills'], net.id)]
    scores.extend((other['kills'], pid) for pid, other in net.others())
    scores.sort(key=lambda score: (-score[0], score[1]))

    lines = ['KILLS']
    for place, (kills, pid) in enumerate(scores, 1):
        marker = ' (you)' if pid == net.id else ''
        lines.append(f'{place}. Player {pid}{marker}: {kills}')
    leaderboard.text('\n'.join(lines))


def draw_fire_line(ship):
    center = ship.center()
    dx, dy = heading(ship.rotation())
    line = Line(screen,
                center.x() + 11 * dx, center.y() + 11 * dy,
                center.x() + RANGE * dx, center.y() + RANGE * dy,
                Color('yellow'), 2)
    fire_lines.append(line)
    return line


def clear_fire_lines():
    for line in fire_lines:
        line.remove()
    fire_lines.clear()


screen.listen()

running = True
while running:
    if fire_cooldown > 0:
        fire_cooldown -= 1

    fly()

    my_ship.moveto(net.mine['x'] - 11, net.mine['y'] - 11)
    my_ship.rotation(net.mine['a'])
    my_ship.color(Color('cyan') if net.mine['hp'] > 40 else Color('orange'))

    for pid, other in net.others():
        ship, bar = sprite_for(pid)
        place(ship, bar, other['x'], other['y'], other['a'], other['hp'])

    for pid in list(sprites):
        if pid not in net.players:
            ship, bar = sprites.pop(pid)
            ship.remove()
            bar.remove()

    update_leaderboard()
    clear_fire_lines()

    screen.update()
    screen.sleep(1 / 60)

net.close()
screen.exit()
