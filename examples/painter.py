from pydraw import *

screen = Screen(800, 600, 'Painter')
screen.grid()

title_text = Text(screen, 'Painter!', 10, 0, font='Calibri', size=32)
help_text = Text(screen, 'Help:\n'
                         'A: Start new poly\n'
                         'S: Stop drawing poly\n'
                         'D: Delete current poly\n'
                         'F: Select/deselect poly\n'
                         'C: Change selected poly\'s color!\n'
                         'V: Hide/Show this text\n'
                         '\n'
                         'Left-click: Place point for polygon\n'
                         'Right-click: Undo last point\n',
                 10, title_text.y() + title_text.height() + 35, font='Arial', size=17)

cursor_text = Text(screen, 'X: 0, Y: 0', 10, help_text.y() + help_text.height() + 20)
vertices_text = Text(screen, 'Vertices: None', 10, cursor_text.y() + cursor_text.height() + 15, size=12)

hint_text = Text(screen, 'Hint Text', screen.width(), screen.height())
hint_text.move(-hint_text.width(), -hint_text.height())

drawing = False  # Drawing state
selected = None  # Selected polygon
current = []  # The list of vertices we have so far
temp_lines = []  # list of lines that we draw until we can form a full polygon
cursor_line = None  # line that shows up while the user is placing vertices


polygons = []  # list of already created polygons

last_selected = None


def create_poly():
    if len(current) < 3:
        set_hint('Not enough vertices to create! (try again)')
    poly = CustomPolygon(screen, current)
    polygons.append(poly)


def set_hint(text):
    hint_text.text(text)
    hint_text.moveto(screen.width() - hint_text.width(), screen.height() - hint_text.height())


def select_poly():
    selected.color(Color('green'))


def unselect_poly():
    global last_selected

    if selected is not None:
        if selected.color() == Color('green'):
            selected.color(Color('black'))

    last_selected = selected


def mousedown(button, location):
    global cursor_line

    if button == 1 and drawing:
        current.append(location)
        if len(current) > 1:
            new_line = Line(screen, current[len(current) - 2], current[len(current) - 1])
            temp_lines.append(new_line)
    elif button == 3:
        if len(current) == 1:
            current.clear()
            set_hint('Restarting drawing of polygon!')
        elif len(current) > 1:
            current.pop()
            temp_lines[len(temp_lines) - 1].remove()
            temp_lines.pop()
            set_hint('Undid previous point!')
    if len(current) != 0:
        text = ''
        for location in current:
            text += str(location) + '\n'

        vertices_text.text(text)

    if cursor_line is not None:
        cursor_line.remove()
    cursor_line = None


def keydown(key):
    global drawing
    global selected
    global last_selected

    if key == 'a':
        if drawing:
            set_hint('Already drawing!')
        else:
            drawing = True
            set_hint('Began drawing new Poly!')
    elif key == 's':
        if not drawing:
            set_hint('You are not drawing!')
        else:
            create_poly()
            drawing = False
            current.clear()
            [line.remove() for line in temp_lines]
            temp_lines.clear()
            set_hint('Stopped drawing polygon!')
    elif key == 'd':
        if drawing:
            # we just delete the current poly
            drawing = False
            current.clear()
            [line.remove() for line in temp_lines]
            temp_lines.clear()
            vertices_text.text('Vertices: None')
            set_hint('Deleted poly-in-progress!')
        else:
            if selected is None:
                set_hint('No polygon selected or in progress!')
            else:
                selected.remove()
                polygons.remove(selected)
                vertices_text.text('Vertices: None')
                selected = None
    elif key == 'f':
        if drawing:
            set_hint('Cannot select polygons while drawing!')
        else:
            distance = None
            closest = None
            for poly in polygons:
                if poly.contains(screen.mouse()):
                    poly_distance = poly.distance(screen.mouse())
                    if distance is None:
                        distance = poly_distance
                        closest = poly
                    elif poly_distance <= distance:
                        distance = poly_distance
                        closest = poly

            unselect_poly()
            if closest is not None:
                selected = closest
                select_poly()
                set_hint('Selected polygon!')
            else:
                set_hint('Unselected polygon!')
    elif key == 'c':
        if drawing:
            set_hint('Cannot select/change polygons while drawing!')
        else:
            if selected is None:
                set_hint('No polygon selected!')
            else:
                color = Color(screen.prompt('Input Color: '))
                selected.color(color)
                set_hint('Changed polygon to specified color!')
    elif key == 'v':
        help_text.visible(not help_text.visible())


def mousemove(location):
    global cursor_line

    cursor_text.text(f'X: {location.x()}, Y: {location.y()}')
    if drawing and len(current) > 0:
        if cursor_line is None:
            cursor_line = Line(screen, current[len(current) - 1], location)
        else:
            cursor_line.moveto(current[len(current) - 1], location)
    elif cursor_line is not None:
        cursor_line.remove()
        cursor_line = None


screen.listen()

fps = 30
running = True
while running:
    screen.update()
    screen.sleep((1000 / fps) / 1000)

screen.exit()
