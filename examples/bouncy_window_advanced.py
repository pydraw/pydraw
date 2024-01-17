from pydraw import *

screen = Screen(800, 600)

box1 = Rectangle(screen, screen.width() / 2 - 150, screen.height() / 2 - 250, 50, 50, color=Color('red'))
box2 = Rectangle(screen, screen.width() / 2 - 250, screen.height() / 2 - 150, 50, 50, color=Color('blue'))

box1_dx = 2
box1_dy = 3

box2_dx = -3
box2_dy = 2

reset = list()
overlapping = False

skip = True

fps = 30
running = True
while running:
    box1.move(box1_dx, box1_dy)
    box2.move(box2_dx, box2_dy)

    # after we move but before anything else we can reset the "elastic" boxes
    for box in reset:
        if not skip:
            box.width(50)
            box.height(50)
            reset.remove(box)
            skip = True
        skip = False

    if box1.x() <= 0 or box1.x() + box1.width() >= screen.width():
        box1.move(dx=-box1_dx)
        box1_dx = -box1_dx

        box1.width(45)
        reset.append(box1)
        skip = True

    if box1.y() <= 0 or box1.y() + box1.height() >= screen.height():
        box1.move(dy=-box1_dy)
        box1_dy = -box1_dy

        box1.height(45)
        reset.append(box1)
        skip = True

    if box2.x() <= 0 or box2.x() + box2.width() >= screen.width():
        box2.move(dx=-box2_dx)
        box2_dx = -box2_dx

        box2.width(45)
        reset.append(box2)
        skip = True

    if box2.y() <= 0 or box2.y() + box2.height() >= screen.height():
        box2.move(dy=-box2_dy)
        box2_dy = -box2_dy

        box2.height(45)
        reset.append(box2)
        skip = True

    if box1.overlaps(box2):
        if not overlapping:
            box1.color(Color.random())
            box2.color(Color.random())
            overlapping = True
    else:
        overlapping = False

    screen.update()
    screen.sleep(fps / 1000)

screen.exit()
