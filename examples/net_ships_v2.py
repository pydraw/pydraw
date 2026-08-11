"""Asteroids PvP v2: the server handles combat and spawning.

Players own position through net.mine. The server owns health, kills, and spawns.

Run it:

    PYTHONPATH=~/Projects/pydraw python3 net_ships_v2.py
    PYTHONPATH=~/Projects/pydraw python3 net_ships_v2.py <address>

Run the first line again in another terminal to add a player.

WASD / arrows to fly, SPACE to fire at whoever is in front of you.
"""

import math
import sys

from pydraw import *
from pydraw.network import *

WIDTH, HEIGHT = 800, 600
RANGE = 140
ARC = 30
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


def can_hit(shooter, target):
    """Return whether a target is inside the shooter's range and firing arc."""
    aim_x, aim_y = heading(shooter['a'])
    target_x = target['x'] - shooter['x']
    target_y = target['y'] - shooter['y']
    distance = math.hypot(target_x, target_y)

    if distance == 0 or distance > RANGE:
        return False

    alignment = (target_x * aim_x + target_y * aim_y) / distance
    return alignment >= math.cos(math.radians(ARC))


# --- The server: it owns health and decides who got hit ---------------------

class Arena(Room):
    def join(self, player):
        player.state['hp'] = 100
        player.state['kills'] = 0
        x, y, a = SPAWNS[(player.id - 1) % len(SPAWNS)]
        player.seed(x=x, y=y, a=a)

    def _respawn(self, player):
        x, y, a = SPAWNS[(player.id - 1) % len(SPAWNS)]
        player.reset(x=x, y=y, a=a)
        player.state['hp'] = 100

    @action
    def fire(self, player):
        me = player.slice
        for other in self.players:
            if other.id == player.id or other.state['hp'] <= 0:
                continue
            if not can_hit(me, other.slice):
                continue

            other.state['hp'] -= 20
            if other.state['hp'] <= 0:
                player.state['kills'] += 1
                self._respawn(other)

        return {'shooter': player.id}


# --- The client: write my ship, read everyone else --------------------------

screen = Screen(WIDTH, HEIGHT, 'Asteroids PvP v2')
screen.color(Color('black'))

net = Network(screen, HOST, room=Arena)

screen.title(f'Asteroids PvP v2 -- player {net.id}')

my_ship = Polygon(screen, 3, WIDTH / 2, HEIGHT / 2, 22, 22, Color('cyan'))
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


def keydown(key):
    global fire_cooldown

    key = str(key)
    if key != 'space':
        held.add(key)
        return

    if fire_cooldown == 0:
        draw_fire_line(my_ship)
        net.call('fire')
        fire_cooldown = FIRE_DELAY


def keyup(key):
    held.discard(str(key))


def networkevent(name, data, sender):
    if name == 'fire' and data['shooter'] in sprites:
        draw_fire_line(sprites[data['shooter']][0])


def fly():
    a = net.mine['a']
    if 'a' in held or 'left' in held:  net.mine['a'] = a - 4
    if 'd' in held or 'right' in held: net.mine['a'] = a + 4
    if 'w' in held or 'up' in held:
        dx, dy = heading(net.mine['a'])
        net.mine['x'] += 4 * dx
        net.mine['y'] += 4 * dy


def update_leaderboard():
    scores = [(net.mine.get('kills', 0), net.id)]
    scores.extend((entity.get('kills', 0), pid) for pid, entity in net.others())
    scores.sort(key=lambda score: (-score[0], score[1]))

    lines = ['KILLS']
    for place, (kill_count, pid) in enumerate(scores, 1):
        marker = ' (you)' if pid == net.id else ''
        lines.append(f'{place}. Player {pid}{marker}: {kill_count}')
    leaderboard.text('\n'.join(lines))


def draw_fire_line(ship):
    """Draw a shot from a ship's nose."""
    center = ship.center()
    dx, dy = heading(ship.rotation())
    line = Line(screen,
                center.x() + 11 * dx, center.y() + 11 * dy,
                center.x() + RANGE * dx, center.y() + RANGE * dy,
                Color('yellow'), 2)
    fire_lines.append(line)


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

    my_hp = net.mine.get('hp', 100)
    my_ship.moveto(net.mine['x'] - 11, net.mine['y'] - 11)
    my_ship.rotation(net.mine['a'])
    my_ship.color(Color('cyan') if my_hp > 40 else Color('orange'))

    for pid, e in net.others():
        ship, bar = sprite_for(pid)
        place(ship, bar, e['x'], e['y'], e['a'], e.get('hp', 100))

    for pid in list(sprites):
        if pid not in net.players:
            ship, bar = sprites.pop(pid)
            ship.remove(); bar.remove()

    update_leaderboard()
    clear_fire_lines()

    screen.update()
    screen.sleep(1 / 60)

net.close()
screen.exit()
