from pydraw import *


screen = Screen(800, 600, "Pen Drawing")
screen.color(Color("white"))

Text(screen, "Drag the mouse to draw", 10, 10, Color("black"), size=20)
Text(screen, "Space: pause    C: clear", 10, 40, Color("black"))

position_text = Text(screen, "Mouse: (0, 0)", 10, 570, Color("black"))
status_text = Text(screen, "Drawing: True", 650, 570, Color("black"))

pen = Pen(screen, screen.center().x(), screen.center().y(), Color("blue"), width=4)
pen.start()


def mousemove(location):
    position_text.text(f"Mouse: {location}")


def mousedrag(location, button):
    if button == 1 and pen.drawing():
        pen.moveto(location)


def keydown(key):
    if key == "space":
        pen.toggle()
        status_text.text(f"Drawing: {pen.drawing()}")
    elif key == "c":
        pen.clear()
        pen.start()


screen.listen()
screen.loop()
