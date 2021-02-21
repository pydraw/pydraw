from pydraw import *;

screen = Screen(800, 600);

screen.toggle_grid();
# screen.clear();
screen.grid(helpers=True);

text = Text(screen, 'Barry', 150, 150);

shape1 = Rectangle(screen, 0, 0, 150, 150, Color('black'), Color('red'));
shape2 = Rectangle(screen, 50, 50, 150, 150, Color('black'), Color('red2'));
shape2.rotate(7);
print('Overlaps (1 & 2)', shape1.overlaps(shape2));
print('Overlaps (2 & 1)', shape2.overlaps(shape1));

# assertFalse(shape3.overlaps(shape1) and shape3.overlaps(shape2));

custom_shape = CustomPolygon(screen,
                             [(150, 150), (250, 150), (300, 200), (300, 250), (250, 230), (150, 300)],
                             Color('black'), Color('red'));

image = Image(screen, '../images/cool_barry.jpg', 250, 250, 150, 150);
# assertTrue(image.overlaps(custom_shape));
# assertTrue(custom_shape.overlaps(shape2));


def mousedown(button, location):
    print('Overlaps (1 & 2)', shape1.overlaps(shape2));
    print('Overlaps (2 & 1)', shape2.overlaps(shape1));
    screen.update();


screen.listen();

while True:
    screen.update();
