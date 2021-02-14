from pydraw import *

screen = Screen(600, 600, 'Clocky')

frame = Oval(screen, 0, 0, screen.width(), screen.height(), border=Color('black'), fill=False)
hour_hand = Line(screen, screen.width() / 2, screen.height() / 2, screen.width(), screen.height() / 2, thickness=3)
minute_hand = Line(screen, screen.width() / 2, screen.height() / 2, screen.width() / 2, 0)

positions = frame.vertices()
count = len(positions) - 1  # we have to count down because the vertices are given counterclockwise.


twilight = count - 9
hour_position = twilight
hour_hand.pos2(positions[hour_position])

fps = 1  # Clock updates once a second ;)
running = True
while running:
    if count < 0:
        count = len(positions) - 1

    minute_hand.pos2(positions[count])

    if count == twilight - 1:
        hour_position -= 1
        if hour_position < 0:
            hour_position = len(positions) - 1

        hour_hand.pos2(positions[hour_position])

    count -= 1

    screen.update()
    screen.sleep((1000 / 1) / 1000)

