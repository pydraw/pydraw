from pydraw import *


screen = Screen(800, 600, "pydraw Paint")
screen.color(Color("white"))

PALETTE = [
    Color("black"),
    Color("red"),
    Color("orange"),
    Color("green"),
    Color("blue"),
    Color("purple"),
]

WIDTHS = [2, 4, 8, 16]

color_index = 0
width_index = 1

pens = []   # every stroke is its own Pen so it keeps its own color/width
pen = None  # the pen for the stroke currently being drawn


def current_color() -> Color:
    return PALETTE[color_index]


def current_width() -> int:
    return WIDTHS[width_index]


# --- On-screen HUD ----------------------------------------------------------

Text(screen, "Drag to draw", 10, 10, Color("black"), size=18)
Text(screen, "1-6 color   [ ] brush   C clear   Z undo", 10, 36, Color("gray"))

swatch = Text(screen, "", 10, 566, current_color(), size=16)
info = Text(screen, "", 620, 566, Color("black"), size=16)


def update_hud():
    swatch.text(f"Color: {current_color()}")
    swatch.color(current_color())
    info.text(f"Brush: {current_width()}px")


update_hud()


# --- Input handlers ---------------------------------------------------------

def mousedown(location, button):
    global pen
    if button != 1:
        return

    pen = Pen(screen, location.x(), location.y(), current_color(), current_width())
    pen.start()
    pens.append(pen)


def mousedrag(location, button):
    if button == 1 and pen is not None and pen.drawing():
        pen.moveto(location)


def mouseup(location, button):
    global pen
    if button == 1:
        finish_stroke()


def finish_stroke():
    """Finalize the active pen so an in-progress drag stops extending it."""
    global pen
    if pen is not None:
        pen.stop()
        pen = None


def keydown(key):
    global color_index, width_index

    if key in ("1", "2", "3", "4", "5", "6"):
        color_index = int(str(key)) - 1
        update_hud()
    elif key == "[":   # thinner
        width_index = max(0, width_index - 1)
        update_hud()
    elif key == "]":   # thicker
        width_index = min(len(WIDTHS) - 1, width_index + 1)
        update_hud()
    elif key == "c":
        finish_stroke()  # drop the stroke being drawn, if any
        for stroke in pens:
            stroke.clear()
        pens.clear()
    elif key == "z":
        finish_stroke()
        if pens:
            pens.pop().clear()


screen.listen()
screen.loop()
