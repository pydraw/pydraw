from pydraw import *;
import time;

screen = Screen(800, 600, 'Something Awesome!');
screen.color(Color('black'));

rect1 = Rectangle(screen, 0, 0, 200, 200);
rect1.border(Color('yellow'), False);

rect2 = Rectangle(screen, screen.width() / 2 - 25, screen.height() / 2 - 25, 50, 50);
rect2.border(Color('red'), False);
rect2.rotate(20);

rect3 = Rectangle(screen, 123, 150, 150, 150);
rect3.border(Color('blue'), False);

oval1 = Oval(screen, screen.width() / 2 - 50, screen.height() / 2 - 50, 100, 100);
oval1.border(Color('green'), False);

time_start = time.time();

# Basic overlapping shapes.
print(f'Overlaps: {rect1.overlaps(rect3)}');

# Testing a shape entirely contained within another.
print(f'Overlaps: {rect2.overlaps(oval1)}');

point = (screen.width() / 2, screen.height() / 2);
print(f'Contains: {rect2.contains(point)}');

time_elapsed = time.time() - time_start;
print(f'Time Elapsed: ' + '{0:.16f}'.format(time_elapsed));
screen.listen();

running = True;
while running:
    screen.update();
    time.sleep(60 / 1000);

screen.exit();
