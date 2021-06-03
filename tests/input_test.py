from pydraw import *

screen = Screen(800, 600, 'Input Test')


def keydown(key):
    print(key)


screen.listen()
screen.stop()
