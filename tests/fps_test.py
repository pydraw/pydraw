from pydraw import Screen, Color, Rectangle, Oval, Triangle;
import time;

screen = Screen(title='An Awesome Project!');
screen.color(Color(name='black'));

bob = Rectangle(screen, 35, 50, 25, 25, Color(135, 107, 35));
alex = Rectangle(screen, screen.width() - 50, screen.height() - 50, 50, 50);
alex.color(Color(hex_value='#3b3b3b'));

phil = Oval(screen, 100, 100, 20, 30, Color(name='red'));

jessica = Triangle(screen, 200, 200, 30, 30, Color(name='white'));
jessica.rotation(90);


def mousedown(button, location):
    dx = location.x - bob.x();
    dy = location.y - bob.y();

    bob.move(dx / 10, dy / 10);


def mouseup(button, location):
    print(f'(mouseup) Button: {button}, Location: {str(location)}');


def mousedrag(button, location):
    print(f'(mousedrag) Button: {button}, Location: {str(location)}');


def keydown(key):
    if key == 'Up':
        alex.move(0, -10);
    elif key == 'Down':
        alex.move(0, 10);
    elif key == 'Left':
        alex.move(-10, 0);
    elif key == 'Right':
        alex.move(10, 0);

    alex.color(Color(alex.x() % 255, (alex.x() + alex.y()) % 255, alex.y() % 255));


screen.listen();

running = True;
while running:
    screen.update();
    time.sleep(30 / 1000);

    jessica.rotate(1);


screen.exit();
