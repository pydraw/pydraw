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
        self.back_button = Rectangle(self._screen, 10, 10, 75, 50, border=Color('black'), fill=False)
        self.back_button_text = Text(self._screen, 'Back', self.back_button.x(), self.back_button.y())

        self.ufo = Oval(self._screen, self._screen.center().x(), self._screen.center().y(), 150, 50, Color('gray'))

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

    def mousedown(self, button: int, location: Location) -> None:
        if self.back_button.contains(location):
            self._screen.scene(StartScene())

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

            self._screen.update()
            self._screen.sleep(1 / fps)

        self._screen.stop()


class StartScene(Scene):
    text = None
    button = None
    button_text = None

    def start(self) -> None:
        self.text = Text(self._screen, 'Start Screen', self._screen.width() / 2, self._screen.height() / 2, size=22)
        self.text.move(-self.text.width() / 2, -self.text.height() / 2)

        self.button = Rectangle(self._screen, self._screen.width() / 2, self._screen.height() / 2 + 75,
                                100, 50, border=Color('black'), fill=False)
        self.button.move(-self.button.width() / 2, self.button.height() / 2);
        self.button_text = Text(self._screen, 'Start', self.button.x(), self.button.y())
        self.button_text.center(self.button.center())

    def mousedown(self, button: int, location: Location) -> None:
        print('ttest)')
        if self.button.contains(location):
            self._screen.scene(GameScene())

    def run(self):
        self._screen.listen();

        running = True
        fps = 30
        # while running:
        #     self._screen.update()
        #     self._screen.sleep(1 / fps)
        self._screen.stop();


screen = Screen(800, 600)
screen.scene(StartScene())
