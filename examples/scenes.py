from pydraw import *


class MenuScene(Scene):
    def start(self):
        screen = self.screen()
        self.title = Text(screen, 'Scene example', 0, 90, size=28)
        self.title.center(x=screen.center().x())

        self.button = Rectangle(
            screen, 300, 220, 200, 70,
            Color('green'), border=Color('black'),
        )
        self.label = Text(screen, 'Start', 0, 0, size=20)
        self.label.center(self.button.center())

    def mousedown(self, location, button):
        if button == 1 and self.button.contains(location):
            self.goto(GameScene())


class GameScene(Scene):
    SPEED = 180

    def __init__(self):
        super().__init__()
        self.held = set()

    def start(self):
        screen = self.screen()
        self.back = Rectangle(
            screen, 20, 20, 100, 50,
            Color('light gray'), border=Color('black'),
        )
        self.back_label = Text(screen, 'Back', 0, 0)
        self.back_label.center(self.back.center())
        self.player = Oval(
            screen, 325, 250, 150, 60,
            Color('gray'), border=Color('black'),
        )

    def update(self, dt):
        dx = int('right' in self.held) - int('left' in self.held)
        dy = int('down' in self.held) - int('up' in self.held)
        self.player.move(dx * self.SPEED * dt, dy * self.SPEED * dt)

    def keydown(self, key):
        self.held.add(str(key))

    def keyup(self, key):
        self.held.discard(str(key))

    def mousedown(self, location, button):
        if button == 1 and self.back.contains(location):
            self.goto(MenuScene())

    def stop(self):
        self.held.clear()


screen = Screen(800, 600, 'Scenes')
screen.scene(MenuScene())
screen.loop()
