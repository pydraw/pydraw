# PyDraw Demonstration
# Noah Coetsee

# List:
# [x] Change color to take list of arguments and interpret type.
# [x] Border for filled/framed option is good. (see below)
# - Color alpha needs to be finished. ** = custom alpha isn't possible
# [1/2] Custom method / distance(object: Object) - Returns the distance between the centers of two objects.
# [1/2] .overlaps(object: Object) method
# - Mouseclick and Keypress. | not doing it.
# [x] 'shift_left', 'shift_right'
# [x] object.x(x: float) -> None | Change x coordinate directly (any object);
# [x] Change coordinate access in Location class to method
# [x] Ensure canvas sizing is correct.

import time;
from pydraw import Screen, Color, Location, Rectangle, Oval, Triangle, Text, Polygon, CustomPolygon, Image, Line;

screen = Screen(800, 600, 'Something Awesome!');
screen.color(Color('black'));

noah = Triangle(screen, 23, 45, 35, 60, Color('green'));
noah.rotation(90);

barry = Rectangle(screen, 600, 450, 75, 75, Color('red'));
barry.border(Color('yellow'), fill=False);
print(barry.visible());
mustachio = Oval(screen, screen.width() - 20, screen.height() - 20, 20, 20);
mustachio.color(Color('red'));

print(f'Screen | Width: {screen.width()}, Height: {screen.height()}');
print(Color.random());
print(Color.all())

height = mustachio.width(135);
width = mustachio.height(135);

print(f'Mustachio\'s Color: ' + str(mustachio.color()));

pos1 = Location(0, 0);
pos2 = Location(0, 0);
time_between = 0;

text = Text(screen, 'barry', 0, 0, color=Color('white'), italic=True, bold=True)
print(f'Text Width: {text.width()}, Text Height: {text.height()}')
text.color(Color(155, 155, 155));
text.rotation(32);

barry.overlaps(noah);

waffle = Polygon(screen, 6, screen.width() - (screen.width() / 3), 100, 50, 50, color=Color('blue'));

# tester = Rectangle(screen, 50, 350, 50, 50, Color('purple'));

crazy_waffle = CustomPolygon(screen, [(50, 350), (100, 350), (100, 400), (75, 450), (50, 400)], color=Color('green'));

maui = Line(screen, 50, 50, 150, 150, color=Color('magenta'));
mrspace = Image(screen, 'featuredspace_logo.png', screen.width() / 2, screen.height() / 2, 150, 150);
mrspace.move(-mrspace.width() / 2, -mrspace.height() / 2);

#
# print(f'Turtle Pos: {crazy_waffle._ref.pos()}');
# print(f'Pydraw Pos: {crazy_waffle.location()}');
# print(f'Supposed Location: {crazy_waffle._get_real_location()}')

state = True;


def mousedown(button, location):
    global state;
    print('Mousedown detected', button, location);
    crazy_waffle.rotate(5 if state else -5);

    state = not state;


def keydown(key):
    print('Keydown: ' + key);

    if key == 'up':
        barry.move(0, -10);
    elif key == 'Down':
        barry.move(0, 10);
    elif key == 'Left':
        barry.move(-10, 0);
    elif key == 'Right':
        barry.move(10, 0);

    if key == 't':
        print('Removing mrspace...');
        screen.remove(mrspace);


def keyup(key):
    print('Keyup: ' + key);


# mousedown, mouseup, mousedrag, mouseclick, keydown, keyup, keypress
screen.listen();

running = True;
while running:
    screen.update();
    screen.sleep(30 / 1000);

screen.exit();
