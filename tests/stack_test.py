from pydraw import *

screen = Screen(400, 400, 'PyDraw is kinda cool')
screen.color(Color('black'))

rect1 = Rectangle(screen, 50, 50, 50, 50)
rect1.color('red')


def mousedown(button, location):
    shape_class = Triangle
    print(f'Button: {button}, Location: {location}')
    shape = None;
    shape_class(screen, 100, 100, 100, 100, Color('yellow'))


screen.listen();

running = True
while running:
    screen.update()

screen.exit()
