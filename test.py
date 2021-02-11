from pydraw import *

screen = Screen(400, 400)

rect = Rectangle(screen, screen.width() - 25, screen.width() - 25, 25, 25)

running = True
while running:
    screen.update()

screen.exit()