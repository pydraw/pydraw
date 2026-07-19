from pydraw import *
import math
import random


GRAVITY = 0.02
MAX_GRAVITY = 0.1
THRUST = 0.05
MAX_SPEED = 6
FPS = 60

screen = Screen(800, 600, "Gravity")
screen.color(Color(8, 18, 32))


# Create a world that is three screens wide and three screens tall.
left = -screen.width()
top = -screen.height()
right = screen.width() * 2
bottom = screen.height() * 2

stars = []
for i in range(1500):
    size = random.randint(1, 3)
    star = Oval(
        screen,
        random.randint(left, right),
        random.randint(top, bottom),
        size,
        size,
        Color("white"),
    )
    stars.append(star)

planets = []
for i in range(45):
    size = random.randint(20, 60)
    color = Color(
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255),
    )
    planet = Oval(
        screen,
        random.randint(left, right),
        random.randint(top, bottom),
        size,
        size,
        color,
    )
    planets.append(planet)

ship = Image(screen, "images/ship.png", screen.center().x(), screen.center().y(), 45, 30)
ship.move(-ship.width() / 2, -ship.height() / 2)

dx = 0
dy = 0
keys = set()


def keydown(key):
    keys.add(str(key))


def keyup(key):
    keys.discard(str(key))


screen.listen()

while True:
    ship_center = ship.center()
    gravity_x = 0
    gravity_y = 0

    # Add the pull from every planet.
    for planet in planets:
        planet_center = planet.center()
        distance_x = planet_center.x() - ship_center.x()
        distance_y = planet_center.y() - ship_center.y()
        distance = math.hypot(distance_x, distance_y)

        if distance > 0:
            distance = max(distance, planet.width() / 2)
            pull = GRAVITY * planet.width() * 1000 / distance ** 2
            gravity_x += distance_x / distance * pull
            gravity_y += distance_y / distance * pull

    # Keep gravity from overpowering the controls.
    gravity = math.hypot(gravity_x, gravity_y)
    if gravity > MAX_GRAVITY:
        gravity_x *= MAX_GRAVITY / gravity
        gravity_y *= MAX_GRAVITY / gravity

    dx += gravity_x
    dy += gravity_y

    # Holding a movement key gradually changes the ship's velocity.
    input_x = 0
    input_y = 0

    if "d" in keys or "right" in keys:
        input_x += 1
    if "a" in keys or "left" in keys:
        input_x -= 1
    if "s" in keys or "down" in keys:
        input_y += 1
    if "w" in keys or "up" in keys:
        input_y -= 1

    input_length = math.hypot(input_x, input_y)

    if input_length > 0:
        dx += input_x / input_length * THRUST
        dy += input_y / input_length * THRUST

    speed = math.hypot(dx, dy)
    if speed > MAX_SPEED:
        dx *= MAX_SPEED / speed
        dy *= MAX_SPEED / speed

    # Keep the ship centered and move the world in the opposite direction.
    for star in stars:
        star.move(-dx, -dy)
    for planet in planets:
        planet.move(-dx, -dy)

    screen.update()
    screen.sleep(1 / FPS)

screen.exit()
