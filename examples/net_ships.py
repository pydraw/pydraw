"""
Asteroids PvP -- the v2 flagship: owned-replicated ships + server-owned health.

This is the game most students actually want, and it shows all three ideas at once:

  - You OWN your ship. You write net.mine and it moves instantly (no lag) and
    replicates to everyone.
  - The SERVER owns health and respawns. Health lives in player.state and appears
    merged into each ship's entity on the client -- read-only, because a player
    can't set their own hp. Firing is a net.call() the server adjudicates.
  - Kills live beside health in player.state, so clients can display the leaderboard
    but cannot award themselves points.

Run it:

    PYTHONPATH=~/Projects/pydraw python3 net_ships.py            # host + play
    PYTHONPATH=~/Projects/pydraw python3 net_ships.py <address>  # join another machine

Run the first line again in a second terminal for a second player on this machine:
whoever starts first hosts the room, and everyone launched after joins it.

WASD / arrows to fly, SPACE to fire at whoever is in front of you.
"""

import math
import sys

from pydraw import *
from pydraw.network import *

WIDTH, HEIGHT = 800, 600
RANGE = 140                     # how far a shot reaches
ARC = 30                        # how far off the nose a shot can still hit, in degrees
FIRE_DELAY = 30                 # frames before the player can fire again
HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'

# Fixed server-side spawn cycle: position plus an angle facing into the arena.
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
    """
    The unit vector a ship at angle `a` (degrees) points along -- 0 is straight up.

    One definition, used by everyone: the server aims shots with it, the client
    flies with it and draws the tracer with it. If they disagreed, the line you
    see and the shot the server scores would point different ways.
    """
    rad = math.radians(a)
    return math.sin(rad), -math.cos(rad)


# --- The server: it owns health and decides who got hit ---------------------

class Arena(Room):
    def join(self, player):
        player.state['hp'] = 100                 # server-managed, per player
        player.state['kills'] = 0

    def accept(self, player, proposed, current):
        # The player still owns ordinary movement. After a spawn, however, the
        # server replaces the first proposed pose with the one it selected.
        if player.state['hp'] > 0:
            return proposed

        x, y, a = player.state['spawn']
        player.state['hp'] = 100
        return {**proposed, 'x': x, 'y': y, 'a': a}

    def _respawn(self, player):
        # Player id chooses a base slot; each respawn advances around the same
        # fixed cycle. Only the server computes and publishes this pose.
        generation = player.state.get('spawn_generation', 0) + 1

        player.state['spawn'] = \
            SPAWNS[(player.id - 1 + generation) % len(SPAWNS)]
        player.state['spawn_generation'] = generation

    @action
    def fire(self, player):                      # net.call('fire')
        # What this returns is what everyone else is told happened. Return nothing
        # and the shot stays private -- so an unspawned player announces nothing.
        me = player.slice
        if 'x' not in me:
            return
        dx, dy = heading(me.get('a', 0))
        for other in self.players:
            if other.id == player.id or other.state['hp'] <= 0:
                continue
            o = other.slice
            if 'x' not in o:
                continue

            ox, oy = o['x'] - me['x'], o['y'] - me['y']
            distance = math.hypot(ox, oy)
            if distance == 0 or distance > RANGE:
                continue

            # In front of me? The dot product of my heading with the direction to
            # the target is the cosine of the angle between them, so comparing it
            # to cos(ARC) is "is the target inside the cone the tracer draws".
            if (ox * dx + oy * dy) / distance < math.cos(math.radians(ARC)):
                continue

            other.state['hp'] -= 20
            if other.state['hp'] <= 0:
                player.state['kills'] += 1
                self._respawn(other)

        # Everyone but the shooter draws a tracer from this. The shooter already
        # drew theirs the moment they pressed the key -- see keydown().
        return {'shooter': player.id}


# --- The client: write my ship, read everyone else --------------------------

screen = Screen(WIDTH, HEIGHT, 'Asteroids PvP')
screen.color(Color('black'))

# Naming the room says "this is an Arena game" -- so joining the wrong address
# is caught immediately -- and, when the address is this machine, "I'll host it
# if nobody else has."
net = Network(screen, HOST, room=Arena)

screen.title(f'Asteroids PvP -- player {net.id}')
net.mine['x'], net.mine['y'], net.mine['a'] = WIDTH / 2, HEIGHT / 2, 0

my_ship = Polygon(screen, 3, WIDTH / 2, HEIGHT / 2, 22, 22, Color('cyan'))
sprites = {}     # other player id -> (Polygon, hp-bar Rectangle)
held = set()
leaderboard = Text(screen, 'KILLS', WIDTH - 170, 15, Color('white'), size=14)

fire_lines = []
fire_cooldown = 0
last_spawn_generation = 0


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
        net.call('fire')          # the server decides if anyone was in range,
                                  # and tells everyone else to draw the tracer
        fire_cooldown = FIRE_DELAY


def keyup(key):
    held.discard(str(key))


def networkevent(name, data, sender):
    # The server settled somebody else's shot and is telling us it happened. All
    # we do is draw the streak, from their sprite. Note this is what Arena.fire()
    # returned -- a client cannot fake it by announcing a shot it never took.
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


def apply_spawn():
    """Apply each server-selected spawn pose to our owned movement slice once."""
    global last_spawn_generation

    generation = net.mine.get('spawn_generation', 0)
    spawn = net.mine.get('spawn')
    if spawn is None or generation == last_spawn_generation:
        return

    net.mine['x'], net.mine['y'], net.mine['a'] = spawn
    last_spawn_generation = generation


def update_leaderboard():
    """Show the server-owned kill count for every connected player."""
    scores = [(net.mine.get('kills', 0), net.id)]
    scores.extend((entity.get('kills', 0), pid) for pid, entity in net.others())
    scores.sort(key=lambda score: (-score[0], score[1]))

    lines = ['KILLS']
    for place, (kill_count, pid) in enumerate(scores, 1):
        marker = ' (you)' if pid == net.id else ''
        lines.append(f'{place}. Player {pid}{marker}: {kill_count}')
    leaderboard.text('\n'.join(lines))


def draw_fire_line(ship):
    """
    Draw one shot: a streak from a ship's nose out to RANGE, along its facing.

    Purely a picture -- the hit was decided by Arena.fire(). We take the ship
    rather than a player id so the same call works for my ship and for anyone
    else's sprite.
    """
    center = ship.center()
    dx, dy = heading(ship.rotation())
    line = Line(screen,
                center.x() + 11 * dx, center.y() + 11 * dy,      # the nose
                center.x() + RANGE * dx, center.y() + RANGE * dy,
                Color('yellow'), 2)
    fire_lines.append(line)


def clear_fire_lines():
    """Remove the tracers drawn during the previous frame."""
    for line in fire_lines:
        line.remove()
    fire_lines.clear()


screen.listen()

running = True
while running:
    if fire_cooldown > 0:
        fire_cooldown -= 1

    apply_spawn()
    fly()

    # my ship (I own x/y/a; hp is merged in from the server, read-only)
    my_hp = net.mine.get('hp', 100)
    my_ship.moveto(net.mine['x'] - 11, net.mine['y'] - 11)
    my_ship.rotation(net.mine['a'])
    my_ship.color(Color('cyan') if my_hp > 40 else Color('orange'))

    # everyone else
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
