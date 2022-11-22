from pydraw import *

screen = Screen(800, 600)
screen.color(Color('black'))

satellite1 = Rectangle(screen, screen.width() / 2 - 150, screen.height() / 2 - 250, 50, 50, color=Color('green'))
satellite2 = Polygon(screen, 5, screen.width() / 2 - 250, screen.height() / 2 - 150, 50, 50, color=Color('green'))

line1 = Line(screen, (0, screen.height()), satellite1.center(), Color('green'))
line2 = Line(screen, (screen.width(), screen.height()), satellite1.center(), Color('green'))
line3 = Line(screen, (screen.width(), 0), satellite2.center(), Color('green'))
line4 = Line(screen, (0, 0), satellite2.center(), Color('green'))

# Communications line
connection = Line(screen, screen.center(), satellite2.center(), Color('red'))
connection.back()

earth = Image(screen, '../images/earth.png', screen.center().x(), screen.center().y(), 150, 150)
earth.move(-earth.width() / 2, -earth.height() / 2)
earth.color(Color('gray'))

status_text = Text(screen, 'Status: Disconnected', 15, 15, color=Color('red'), font='Courier New',
                   size=10)

satellite_text = Text(screen, f'Satellite 1: {satellite1.location()}\n'
                              f'Satellite 2: {satellite2.location()}', 15, 30, color=Color('white'),
                      font='Courier New', size=10)

line1.dashes(3)
line2.dashes(3)
line3.dashes(3)
line4.dashes(3)

satellite1_dx = 2
satellite1_dy = 3

satellite2_dx = -3
satellite2_dy = 2


def mousedown(location, button):
    status_text.text('Status: Connected')
    status_text.color(Color('green'))
    connection.color(Color('green'))
    earth.color(Color.NONE)


def mouseup(location, button):
    status_text.text('Status: Disconnected')
    status_text.color(Color('red'))
    connection.color(Color('red'))
    earth.color(Color('gray'))


screen.listen()

fps = 30
running = True
while running:
    satellite1.move(satellite1_dx, satellite1_dy)
    satellite2.move(satellite2_dx, satellite2_dy)

    if satellite1.x() <= 0 or satellite1.x() + satellite1.width() >= screen.width():
        satellite1.move(dx=-satellite1_dx)
        satellite1_dx = -satellite1_dx
    if satellite1.y() <= 0 or satellite1.y() + satellite1.height() >= screen.height():
        satellite1.move(dy=-satellite1_dy)
        satellite1_dy = -satellite1_dy
    if satellite2.x() <= 0 or satellite2.x() + satellite2.width() >= screen.width():
        satellite2.move(dx=-satellite2_dx)
        satellite2_dx = -satellite2_dx
    if satellite2.y() <= 0 or satellite2.y() + satellite2.height() >= screen.height():
        satellite2.move(dy=-satellite2_dy)
        satellite2_dy = -satellite2_dy

    line1.pos2(satellite1.center())
    line2.pos2(satellite1.center())
    line3.pos2(satellite2.center())
    line4.pos2(satellite2.center())

    connection.pos2(satellite2.center())

    satellite1.lookat(Location(earth.center()))
    satellite2.lookat(Location(earth.center()))

    satellite_text.text(f'Satellite 1: {satellite1.location()}\n'
                        f'Satellite 2: {satellite2.location()}')

    earth.rotate(-1)

    screen.update()
    screen.sleep(1 / fps)

screen.exit()
