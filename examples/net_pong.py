"""Server-authoritative Pong.

The Room owns the ball, score, and paddles. Clients request paddle movement.

Run it:

    # player 1 hosts and plays the LEFT paddle
    PYTHONPATH=~/Projects/pydraw python3 net_pong.py

    # player 2 connects and plays the RIGHT paddle
    PYTHONPATH=~/Projects/pydraw python3 net_pong.py <host-address>

Move your paddle with the mouse. Extra players just watch.
"""

import sys

from pydraw import *
from pydraw.network import *

WIDTH, HEIGHT = 800, 600
PADDLE_H = 100
BALL = 16
HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'


# --- The server: the one place that decides what is true --------------------

class Pong(Room):
    def start(self):
        self.state['score'] = [0, 0]
        self.state['paddle1'] = HEIGHT / 2
        self.state['paddle2'] = HEIGHT / 2
        self.state['ball'] = [WIDTH / 2, HEIGHT / 2]
        self._vel = [260, 170]

    @action
    def paddle_move(self, player, y):
        # Extra players are spectators.
        if player.id in (1, 2):
            self.state[f'paddle{player.id}'] = max(PADDLE_H / 2,
                                                   min(HEIGHT - PADDLE_H / 2, y))

    def tick(self, dt):
        ball, vel = self.state['ball'], self._vel
        ball[0] += vel[0] * dt
        ball[1] += vel[1] * dt

        # Bounce off the top and bottom.
        if ball[1] < 0 or ball[1] > HEIGHT:
            vel[1] = -vel[1]

        # Bounce off a paddle it actually reaches.
        if ball[0] < 40 and self._near(ball[1], self.state['paddle1']):
            vel[0] = abs(vel[0])
        elif ball[0] > WIDTH - 40 and self._near(ball[1], self.state['paddle2']):
            vel[0] = -abs(vel[0])

        # Off an end: the other side scores, and the ball resets.
        if ball[0] < 0:
            self.state['score'][1] += 1
            self._reset()
        elif ball[0] > WIDTH:
            self.state['score'][0] += 1
            self._reset()

    def _near(self, ball_y, paddle_y):
        return abs(ball_y - paddle_y) < PADDLE_H / 2

    def _reset(self):
        self.state['ball'] = [WIDTH / 2, HEIGHT / 2]
        self._vel[0] = -self._vel[0]


# --- The client: ordinary pydraw, plus three networking lines ---------------

screen = Screen(WIDTH, HEIGHT, 'Pong')
screen.color(Color('black'))

net = Network(screen, HOST, room=Pong)

screen.title(f'Pong -- player {net.id}')

paddle1 = Rectangle(screen, 20, HEIGHT / 2, 12, PADDLE_H, Color('white'))
paddle2 = Rectangle(screen, WIDTH - 32, HEIGHT / 2, 12, PADDLE_H, Color('white'))
ball = Oval(screen, WIDTH / 2, HEIGHT / 2, BALL, BALL, Color('white'))
scoreboard = Text(screen, '0   0', WIDTH / 2 - 30, 20, Color('gray'), size=28)

role = {1: 'You are the LEFT paddle', 2: 'You are the RIGHT paddle'}.get(
    net.id, 'You are watching')
Text(screen, role, 20, HEIGHT - 30, Color('gray'), size=14)


def draw_from_state():
    """Every frame, make the picture match what the server says is true."""
    if 'paddle1' in net.state:
        paddle1.moveto(20, net.state['paddle1'] - PADDLE_H / 2)
        paddle2.moveto(WIDTH - 32, net.state['paddle2'] - PADDLE_H / 2)
        bx, by = net.state['ball']
        ball.moveto(bx - BALL / 2, by - BALL / 2)
        left, right = net.state['score']
        scoreboard.text(f'{left}   {right}')


def mousemove(location):
    net.call('paddle_move', y=location.y())


screen.listen()

fps = 60
running = True
while running:
    draw_from_state()
    screen.update()     # also pumps the network
    screen.sleep(1 / fps)

net.close()
screen.exit()
