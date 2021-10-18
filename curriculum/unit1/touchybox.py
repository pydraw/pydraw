from pydraw import *

screen = Screen()

box1 = Rectangle(screen, 150, 200, 100, 100, Color('red'))
box2 = Rectangle(screen, 350, 200, 100, 100, Color('green'))
box3 = Rectangle(screen, 550, 200, 100, 100, Color('blue'))


def mousedown(button, location):
    if box1.contains(location):
        box1.color(Color('orange'))

    if box2.contains(location):
        box2.color(Color('yellow'))

    if box3.contains(location):
        box3.color(Color('aqua'))


def mouseup(button, location):
    if box1.contains(location):
        box1.color(Color('red'))

    if box2.contains(location):
        box2.color(Color('green'))

    if box3.contains(location):
        box3.color(Color('blue'))


screen.listen()
screen.stop()
