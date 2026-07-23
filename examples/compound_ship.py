"""
compound_ship.py — an Asteroids-style flyer that shows off some of pydraw's
less-travelled corners:

  * CompoundObject      -- group several shapes into one rigid body, then
                           move / moveto / rotate / recolor / overlap-test it
                           as a single unit (imported from pydraw.compound).
  * center(centroid=..) -- centroid vs. bounding-box center.
  * Renderable.rotate   -- spinning individual shapes (the asteroids).
  * keydown + keyup     -- tracking *held* keys for smooth, continuous control.
  * screen.toggle_grid  -- the built-in reference grid.
  * screen.sleep(delta) -- frame pacing with the delta-time feature.
  * Color.random()      -- random colors on impact.

Controls:  W / Up  thrust    A D / Left Right  turn    S / Down  brake
           Space  full stop      G  toggle grid
"""

import math
import random

from pydraw import Screen, Color, Location, Rectangle, Oval, Triangle, Polygon, Text
from pydraw.compound import CompoundObject

screen = Screen(900, 650, "pydraw — Compound Ship")
screen.color(Color("midnight blue"))

THRUST = 0.22       # velocity gained per frame while thrusting
MAX_SPEED = 7.0     # velocity magnitude cap
TURN = 4.0          # degrees rotated per frame while turning
FRICTION = 0.992    # velocity retained each frame (space drag, for playability)
FRAME = 1 / 60      # target seconds per frame

HULL = Color("steel blue")
COCKPIT = Color("light cyan")
FIN = Color("crimson")
FLAME = Color("orange")

cx, cy = screen.center().x(), screen.center().y()

hull = Triangle(screen, cx - 28, cy - 26, 56, 58, color=HULL, border=Color("white"))
hull.rotate(180)  # Triangle's apex points down by default; flip it to point up.

cockpit = Oval(screen, cx - 12, cy - 22, 24, 24, color=COCKPIT, border=Color("white"))
fin_left = Triangle(screen, cx - 40, cy + 8, 20, 26, color=FIN)
fin_right = Triangle(screen, cx + 20, cy + 8, 20, 26, color=FIN)
flame = Rectangle(screen, cx - 7, cy + 30, 14, 12, color=FLAME, visible=False)

ship = CompoundObject(
    hull=hull,
    cockpit=cockpit,
    fin_left=fin_left,
    fin_right=fin_right,
    flame=flame,
)

velocity = [0.0, 0.0]  # (vx, vy)

asteroids = []
for _ in range(5):
    sides = random.randint(5, 8)
    size = random.randint(55, 95)
    # Keep them clear of the ship's spawn point at the center.
    while True:
        ax = random.randint(40, screen.width() - 40 - size)
        ay = random.randint(40, screen.height() - 40 - size)
        if abs(ax - cx) > 140 or abs(ay - cy) > 140:
            break
    rock = Polygon(screen, sides, ax, ay, size, size,
                   color=Color("dim gray"), border=Color("gray"))
    rock.spin = random.uniform(-1.2, 1.2)  # per-frame rotation, stashed on the object
    asteroids.append(rock)

# --- HUD --------------------------------------------------------------------

Text(screen, "W/↑ thrust   A/D ←/→ turn   S/↓ brake   Space stop   G grid",
     12, 12, Color("white"), size=14)
status = Text(screen, "", 12, screen.height() - 28, Color("light yellow"), size=15)


def restore_colors():
    """Repaint the ship to its normal palette (undoes a crash flash)."""
    hull.color(HULL)
    cockpit.color(COCKPIT)
    fin_left.color(FIN)
    fin_right.color(FIN)
    flame.color(FLAME)


def facing():
    """Unit vector from the ship's centroid toward its nose (the cockpit).

    Deriving heading from the geometry means we never have to reason about
    which way a given rotation angle points — the nose always tells the truth.
    """
    c = ship.center(centroid=True)
    n = cockpit.center()
    dx, dy = n.x() - c.x(), n.y() - c.y()
    dist = math.hypot(dx, dy) or 1.0
    return dx / dist, dy / dist


def recenter():
    """Slide the whole ship so its bounding box is centered on screen."""
    box = ship.center(centroid=False)
    ship.move(cx - box.x(), cy - box.y())


held = set()
crashes = 0
crash_timer = 0  # frames of red-flash remaining after an impact


def keydown(key):
    global crash_timer
    name = str(key)

    if name == "g":
        screen.toggle_grid()
    elif name == "space":
        velocity[0] = velocity[1] = 0.0
    else:
        held.add(name)


def keyup(key):
    held.discard(str(key))


def pressed(*names):
    return any(n in held for n in names)


screen.listen()

running = True
while running:
    thrusting = False

    if crash_timer <= 0:  # controls are locked out during the crash flash
        if pressed("left", "a"):
            ship.rotate(-TURN)
        if pressed("right", "d"):
            ship.rotate(TURN)
        if pressed("up", "w"):
            fx, fy = facing()
            velocity[0] += THRUST * fx
            velocity[1] += THRUST * fy
            thrusting = True
        if pressed("down", "s"):
            velocity[0] *= 0.9
            velocity[1] *= 0.9

    flame.visible(thrusting)

    # Friction + speed cap.
    velocity[0] *= FRICTION
    velocity[1] *= FRICTION
    speed = math.hypot(velocity[0], velocity[1])
    if speed > MAX_SPEED:
        velocity[0] *= MAX_SPEED / speed
        velocity[1] *= MAX_SPEED / speed
        speed = MAX_SPEED

    ship.move(velocity[0], velocity[1])

    # Wrap around the screen edges (toroidal space).
    box = ship.center(centroid=False)
    if box.x() < 0:
        ship.move(dx=screen.width())
    elif box.x() > screen.width():
        ship.move(dx=-screen.width())
    if box.y() < 0:
        ship.move(dy=screen.height())
    elif box.y() > screen.height():
        ship.move(dy=-screen.height())

    # Drift the asteroids.
    for rock in asteroids:
        rock.rotate(rock.spin)

    # Collision handling.
    if crash_timer > 0:
        crash_timer -= 1
        if crash_timer == 0:
            restore_colors()
    else:
        for rock in asteroids:
            if ship.overlaps(rock):
                crashes += 1
                crash_timer = 30
                velocity[0] = velocity[1] = 0.0
                ship.color(Color("red"))        # flash the whole compound
                rock.color(Color.random())      # and tag the rock we clipped
                flame.visible(False)
                break

    status.text(f"heading {ship.rotation() % 360:5.0f}°     "
                f"speed {speed:4.1f}     crashes {crashes}")

    screen.update()
    screen.sleep(FRAME, delta=True)

screen.exit()
