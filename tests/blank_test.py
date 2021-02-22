from pydraw import *;

screen = Screen(800, 600);

screen.toggle_grid();
# screen.clear();
screen.grid(helpers=True);

marker = Oval(screen, screen.width() / 2, screen.height() / 2);

text = Text(screen, 'Test Text', screen.width() / 2, screen.height() / 2, size=22, rotation=0);
text.move(-text.width() / 2, -text.height() / 2);

origin = Rectangle(screen, 0, 0, 10, 10)
marker2 = Rectangle(screen, screen.width() - 10, screen.height() - 10, 10, 10);


def mousedown(button, location):
    # text.lookat(location);
    print(text.contains(location))


screen.listen();

while True:
    screen.update();
