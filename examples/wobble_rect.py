from pydraw import *
import random

screen = Screen(800, 600, 'Wobbly Rect!')

speed = 5

rect = Rectangle(screen, screen.width() / 2, screen.height() / 2, 50, 50, Color('red'))
rect.move(-rect.width(), -rect.height())

foods = []
score = 0

score_text = Text(screen, f'Score: {score}', 10, 10, font='Calibri')

up = False
down = False
left = False
right = False


def keydown(key):
    global up, down, left, right

    if key == 'w' or key == 'up':
        up = True
    if key == 's' or key == 'down':
        down = True
    if key == 'a' or key == 'left':
        left = True
    elif key == 'd' or key == 'right':
        right = True


def keyup(key):
    global up, down, left, right

    if key == 'w' or key == 'up':
        up = False
    if key == 's' or key == 'down':
        down = False
    if key == 'a' or key == 'left':
        left = False
    if key == 'd' or key == 'right':
        right = False


screen.listen()


count = 0
fps = 30
running = True
while running:
    if up:
        rect.move(dy=-speed)
    if down:
        rect.move(dy=speed)
    if left:
        rect.move(dx=-speed)
    if right:
        rect.move(dx=speed)

    for food in foods:
        if rect.overlaps(food):
            food.remove()
            foods.remove(food)

            score += 1
            score_text.text(f'Score: {score}')
            rect.rotate(5)

    if count == 30 and not len(foods) > 20:
        count = 0
        foods.append(Oval(screen, random.randint(0, screen.width() - 10), random.randint(0, screen.height() - 10), 10, 10, Color('yellow')))
    count += 1

    screen.update()
    screen.sleep(1 / fps)

