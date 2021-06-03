from pydraw import *

screen = Screen()

text = Text(screen, "Press me!", 400, 300)


def mousedown(button, location):
    text.text("I'm pressed!")


def mouseup(button, location):
    text.text("Press me!");


screen.listen()
screen.stop()
