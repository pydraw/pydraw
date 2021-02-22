from pydraw import *;

screen = Screen(800, 600);

screen.toggle_grid();
# screen.clear();
screen.grid(helpers=True);

poly = Rectangle(screen, 50, 50, 100, 100);


def keydown(key):
    if key == 'r':
        poly.rotate(1);
    elif key == 'w':
        poly.width(poly.width() + 10)
    elif key == 'h':
        poly.height(poly.height() + 10)
    elif key == 'x':
        poly.x(poly.x() + 10)
    elif key == 'y':
        poly.y(poly.y() + 10)


screen.listen();

while True:
    screen.update();
