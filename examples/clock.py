from pydraw import *

screen = Screen(600, 600, 'Clocky')

frame = Oval(screen, 0, 0, screen.width(), screen.height(), border=Color('black'), fill=False)

# We can set how "round" our circle is like this. We can use this to make an easy clock.
# Note that the clock will not be a REAL clock, but it will behave very similarly to one.
# Also, most clocks have 24 wedges, for each five minute marker, but I've elected to not care.
frame.wedges(40)

hour_hand = Line(screen, screen.width() / 2, screen.height() / 2,
                 screen.width() - 100, screen.height() / 2, thickness=3)
minute_hand = Line(screen, screen.width() / 2, screen.height() / 2, screen.width() / 2, 0)

positions = frame.vertices()  # Get the vertices of the circle. Will be returned clockwise starting from top-left.
twilight = 4  # Twighlight is the 4th vertice of the 40
count = twilight + 20  # since we have 40 wedges, 20 past midnigth will be the 30 minute marker!

hour_position = twilight
hour_hand.lookat(positions[hour_position])

fps = 1  # Clock updates once a second ;)
running = True
while running:
    if count >= len(positions):
        count = 0

    minute_hand.pos2(positions[count])

    if count == twilight + 2:
        hour_position += 2
        if hour_position >= len(positions):
            hour_position = 0

        hour_hand.lookat(positions[hour_position])

    count += 2

    screen.update()
    screen.sleep((1000 / 1) / 1000)
