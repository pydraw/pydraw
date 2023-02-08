from pydraw import *


class GameScene(Scene):
    back_button = None
    back_button_text = None

    ufo = None

    up = False
    down = False
    left = False
    right = False

    SPEED = 5

    def start(self):
        self.back_button = Rectangle(self.screen(), 10, 10, 75, 50, border=Color('black'), fill=False)
        self.back_button_text = Text(self.screen(), 'Back', self.back_button.x(), self.back_button.y())

        self.ufo = Oval(self.screen(), self.screen().center().x(), self.screen().center().y(), 150, 50, Color('gray'))

    def keydown(self, key: Screen.Key) -> None:
        if key == 'up':
            self.up = True
        elif key == 'down':
            self.down = True
        elif key == 'left':
            self.left = True
        elif key == 'right':
            self.right = True

    def keyup(self, key: Screen.Key) -> None:
        if key == 'up':
            self.up = False
        elif key == 'down':
            self.down = False
        elif key == 'left':
            self.left = False
        elif key == 'right':
            self.right = False

    def mousedown(self, location: Location, button: int) -> None:
        if self.back_button.contains(location):
            self.screen().scene(StartScene())

    def run(self) -> None:
        running = True
        fps = 30
        while running:
            dx = 0
            dy = 0

            if self.up:
                dy -= self.SPEED
            if self.down:
                dy += self.SPEED
            if self.left:
                dx -= self.SPEED
            if self.right:
                dx += self.SPEED

            self.ufo.move(dx, dy)
            print('moving')

            self.screen().update()
            self.screen().sleep(1 / fps)

        self.screen().stop()


class StartScene(Scene):
    text = None
    button = None
    button_text = None

    def start(self) -> None:
        self.text = Text(self.screen(), 'Start Screen', self.screen().width() / 2, self.screen().height() / 2, size=22)
        self.text.move(-self.text.width() / 2, -self.text.height() / 2)

        self.button = Rectangle(self.screen(), self.screen().width() / 2, self.screen().height() / 2 + 75,
                                100, 50, border=Color('black'), fill=False)
        self.button.move(-self.button.width() / 2, self.button.height() / 2)
        self.button_text = Text(self.screen(), 'Start', self.button.x(), self.button.y())
        self.button_text.center(self.button.center())

    def mousedown(self, location: Location, button: int) -> None:
        print('ttest)')
        if self.button.contains(location):
            self.screen().scene(GameScene())

    def run(self):
        self.screen().listen()

        running = True
        fps = 30
        # while running:
        #     self.screen().update()
        #     self.screen().sleep(1 / fps)
        self.screen().stop()


screen = Screen(800, 600)
screen.scene(StartScene())
