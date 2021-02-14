from pydraw import *

screen = Screen(800, 600, 'My First Project!')

# Here we create a rectangle at x=50, y=50 that is 50 pixels wide and 50 pixels tall.
# It is top-left anchored. This means that the position is the location of the top left corner.
# It's important to know that pydraw's canvas has the origin in the top left, with
# positive-y at the bottom of the screen, and positive-x to the right of the screen.
box = Triangle(screen, 50, 50, 50, 50)
polygon = Polygon(screen, 5, 100, 100, 50, 50);


running = True
while running:
    screen.update()
    screen.sleep(30 / 1000)

screen.exit();
