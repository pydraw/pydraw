from pydraw import *
import random

GRAVITY = 1

screen = Screen(800, 600, "Gravity")
screen.color(Color(8, 18, 32))

class World:
    def __init__(self, bounds=None):
        self.objects = {}  # key: type, value: list of objects
        if bounds is None:
            self.bounds = [0, 0, screen.width(), screen.height()]

    def add(self, o_type, obj):
        if o_type not in self.objects:
            self.objects[o_type] = []

        self.objects[o_type].append(obj)

    def remove(self, obj):
        flist: list = None
        for objs in self.objects.values():
            for other in objs:
                if obj == other:
                    flist = objs

        if flist is not None:
            flist.remove(obj)

    def move(self, dx, dy):
        for o_type, objs in self.objects.items():
            for obj in objs:
                obj.move(dx, dy)

    def move_type(self, o_type, dx, dy):
        for obj in self.objects.get(o_type):
            obj.move(dx, dy)


class Planet:
    MASS_MULTIPLIER = 1000
    def __init__(self, screen, x, y, size, color, mass=None):
        self.size = size
        self.ref = Oval(screen, x, y, size, size, color)
        self.mass = mass if mass is not None else size * self.MASS_MULTIPLIER


class Ship:
    SPEED = 5
    def __init__(self, screen, x, y):
        self.ref = Image(screen, "images/ship.png", x, y, 45, 30)  # stretch to 45x30
        self.dx = 0
        self.dy = 0







def create_stars(world, bounds=None):
    coverage = random.randint(5, 8)
    bounds = [0, 0, screen.width(), screen.height()]
    # create stars covering x percentage of the screen
    for i in range(coverage * bounds[2] * bounds[3] // 10000):
        x = random.randint(0, bounds[2])
        y = random.randint(0, bounds[3])
        size = random.randint(1, 3)
        star = Oval(screen, x, y, size, size, Color(255, 255, 255))
        world.add("star", star)


def create_planets(world, bounds=None):
    for i in range(5):
        x = random.randint(0, screen.width())
        y = random.randint(0, screen.height())
        size = random.randint(20, 60)
        color = Color(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        planet = Planet(screen, x, y, size, color)
        world.add("planet", planet)



world = World()
create_stars(world)
create_planets(world)

ship = Ship(screen, screen.center().x(), screen.center().y())
world.add("ship", ship)


### INPUT

# the keydown event from pydraw will naturally rate limit our velocity changes unless the user spams the keys
def keydown(key):
    if key == 'w' or key == 'up':
        ship.dy -= Ship.SPEED
    elif key == 's' or key == 'down':
        ship.dy += Ship.SPEED
    elif key == 'a' or key == 'left':
        ship.dx -= Ship.SPEED
    elif key == 'd' or key == 'right':
        ship.dx += Ship.SPEED



screen.listen()

running = True
FPS = 60
while running:
    screen.update()
    screen.sleep(1 / FPS)

screen.exit()