from pydraw import *

screen = Screen()

text = Text(screen, "Press me!", 400, 300)


def mousedown(location, button):
    text.text("I'm pressed!")


def mouseup(location, button):
    text.text("Press me!")


screen.listen()
screen.stop()
