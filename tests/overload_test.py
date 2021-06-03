from pydraw import *

screen = Screen(800, 600, 'Overloading Test #1')

rect = Rectangle(screen, 100, 100, 50, 50)

special_rect = Rectangle(screen, screen.center(), 50, 50)

border_rect = Rectangle(screen, 500, 500, 150, 50, color=Color('green'), fill=True, border=Color('black'))

some_location = Location(200, 100)
text = Text(screen, "Some text", some_location)
more_text = Text(screen, "Some more text", 210 + text.width(), 100)

screen.stop()
