# Networking with pydraw

`pydraw.network` adds small-room multiplayer to an ordinary pydraw program. It
works without custom server code, but a `Room` can take authority over rules such
as health, scoring, and respawning.

```python
from pydraw import *
from pydraw.network import *
```

## A first multiplayer program

This complete example gives every player a movable circle. The first copy hosts;
later copies connect to it.

```python
import sys

from pydraw import *
from pydraw.network import *

HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'

screen = Screen(800, 600, 'Multiplayer Dots')
net = Network(screen, HOST, room=Room)
net.mine.update(x=400, y=300)
net.smooth('x', 'y')

me = Oval(screen, 0, 0, 30, 30, Color('blue'))
circles = {}


def keydown(key):
    key = str(key)
    if key == 'left':  net.mine['x'] -= 10
    if key == 'right': net.mine['x'] += 10
    if key == 'up':    net.mine['y'] -= 10
    if key == 'down':  net.mine['y'] += 10


def playerquit(player_id):
    if player_id in circles:
        circles.pop(player_id).remove()


screen.listen()

running = True
while running:
    me.moveto(net.mine['x'], net.mine['y'])

    for player_id, player in net.others():
        if player_id not in circles:
            circles[player_id] = Oval(screen, 0, 0, 30, 30, Color('red'))
        circles[player_id].moveto(player['x'], player['y'])

    screen.update()
    screen.sleep(1 / 60)

net.close()
screen.exit()
```

Run it twice on one computer:

```sh
python3 dots.py
python3 dots.py
```

From another computer, pass the host computer's address:

```sh
python3 dots.py 192.168.1.20
```

The main pattern is simply:

```python
net.mine['x'] += 4

for player_id, player in net.others():
    draw(player['x'], player['y'])
```

## State and ownership

Every network value has one writer:

| Value | Written by | Read by clients |
| --- | --- | --- |
| `net.mine` | This client | As `net.mine` and through `net.others()` |
| `player.state` | The Room | Merged into that player's entity |
| `Room.state` | The Room | As `net.state` |

A client might own `x`, `y`, and `angle`, while the Room owns `health`. Client
code reads all four fields from the same entity. Remote and server-managed fields
are read-only, including nested dictionaries and lists.

## Publishing and lifecycle

A player becomes visible after its first `net.mine` state is published. This
happens automatically on its first frame, even when that state is empty.

```python
def playerjoin(player_id):
    print('joined:', player_id)


def playerquit(player_id):
    print('left:', player_id)
```

`net.players` contains your id and visible remote player ids. `net.others()` yields
only remote players whose owner state is ready to read.

## Events

State describes what remains true. Events describe something that happened.

```python
net.send('wave', message='Hello!')


def networkevent(name, data, sender):
    if name == 'wave':
        print(f"Player {sender}: {data['message']}")
```

Events go to the other connected clients. They are transient unless `keep=True`
is used to replay them to later joiners:

```python
net.send('line', keep=True, x=100, y=80)
```

The Room can discard that replay history with `clear_kept_events()`.

## Smoothing

Local movement is immediate. Remote visual movement can be interpolated:

```python
net.smooth('x', 'y')
net.smooth_angle('angle')
```

Do not smooth health, score, inventory, or other gameplay state. Use
`net.clear_smoothing(player_id)` after drawing a teleport yourself. Resets from the
server clear remote smoothing automatically.

## An authoritative Room

This Room chooses spawns, owns health and score, keeps movement on-screen, reviews
chat, and handles respawning:

```python
from pydraw.network import *

WIDTH, HEIGHT = 800, 600
SPAWNS = ((100, 100), (700, 500), (700, 100), (100, 500))


class Arena(Room):
    tick_rate = 30

    def start(self):
        self.state['time_left'] = 60

    def join(self, player):
        player.state['health'] = 100
        player.state['score'] = 0
        x, y = SPAWNS[(player.id - 1) % len(SPAWNS)]
        player.seed(x=x, y=y)

    def leave(self, player):
        print('left:', player.id)

    def tick(self, dt):
        self.state['time_left'] = max(0, self.state['time_left'] - dt)

    def accept(self, player, proposed, current):
        x = max(0, min(WIDTH, proposed.get('x', WIDTH / 2)))
        y = max(0, min(HEIGHT, proposed.get('y', HEIGHT / 2)))
        if x == proposed.get('x') and y == proposed.get('y'):
            return proposed
        return {**proposed, 'x': x, 'y': y}

    @action
    def respawn(self, player):
        x, y = SPAWNS[(player.id - 1) % len(SPAWNS)]
        player.state['health'] = 100
        player.reset(x=x, y=y)
        return {'player': player.id}

    @event('chat')
    def review_chat(self, player, data):
        message = str(data.get('message', ''))[:100]
        if not message:
            return False
        return {'message': message}
```

The client selects the Room and calls its exposed action by name:

```python
net = Network(screen, HOST, room=Arena)
net.call('respawn')
```

An action runs later on the server. Returning a dictionary announces its result to
the other clients through `networkevent`; returning nothing keeps it private.

### `player.seed()`

`seed()` publishes the initial client-owned state during `join()`. Those fields are
already in `net.mine` when `Network(...)` returns, and the client owns them after
initialization.

A Room that does not call `seed()` still works: the client's first frame publishes
its initial `net.mine` instead. Call `seed()` only once, before publication.

### `Room.accept()`

`accept()` reviews every state proposed by a client:

```python
def accept(self, player, proposed, current):
    if proposed.get('speed', 0) > 10:
        return current
    return proposed
```

- Return `proposed` to accept it.
- Return `current` to reject it.
- Return another dictionary to correct it.

The library checks object identity instead of deep-comparing state. Returning
`proposed` keeps ordinary updates inexpensive even when it is large.

### `player.reset()`

`reset()` changes client-owned fields after publication:

```python
player.reset(x=400, y=300)
```

Only the supplied fields change. It is intended for respawns, teleports, and server
corrections. Older client movement cannot undo it.

### Server-owned state

`player.state` holds server-managed fields for one player. Clients read those fields
beside client-owned fields through `net.mine` and `net.others()`.

`self.state` holds shared world state. Clients read it through `net.state`:

```python
timer.text(f"{net.state['time_left']:.1f}")
health.text(str(net.mine['health']))
```

The Room can also send events itself:

```python
self.broadcast('round_started', number=2)
player.send('warning', message='Return to the arena')
```

An `@event` reviewer returns a dictionary to replace the event, `False` to block
it, or nothing to relay it unchanged.

## API reference

Client API:

| API | Purpose |
| --- | --- |
| `net.id` | This player's numeric id |
| `net.mine` | Merged entity; client-owned fields are writable |
| `net.state` | Read-only shared Room state |
| `net.players` | This player and visible remote player ids |
| `net.others()` | Iterate over read-only remote entities |
| `net.send(name, **data)` | Send an event to other clients |
| `net.call(action, **data)` | Call an `@action` on the Room |
| `net.smooth(*fields)` | Interpolate remote numeric fields |
| `net.smooth_angle(*fields)` | Interpolate remote degree fields |
| `net.connected()` | Check whether the connection is alive |
| `net.close()` | Close the client and any Room it hosts |

Room and Player API:

| API | Purpose |
| --- | --- |
| `self.state` | Writable shared world state |
| `self.players` | Every connected `Player`, including unpublished players |
| `self.player(id)` | Find a connected player |
| `self.broadcast(name, **data)` | Send an event to everyone |
| `player.state` | Writable server-managed fields for one player |
| `player.slice` | Last accepted, read-only client-owned state |
| `player.seed(**fields)` | Publish initial client-owned state |
| `player.reset(**fields)` | Correct published client-owned fields |
| `player.send(name, **data)` | Send an event to one player |
| `player.resync()` | Send one player a fresh snapshot |

Useful configuration:

```python
class Game(Room):
    tick_rate = 30
    replication_rate = 60
    message_limit = 600
    byte_limit = 4 << 20

net = Network(screen, HOST, room=Game, rate=30,
              precision={'x': 2, 'y': 2, 'angle': 1})
```

`precision` rounds only the wire copy; local values remain exact.

## Lifecycle order

1. `start()` runs when the Room opens.
2. `join(player)` runs after a client completes its handshake.
3. `tick(dt)` runs while the Room is active.
4. `leave(player)` runs once when that player disconnects.
5. `stop()` runs after the remaining players leave during shutdown.

`Room.players` can briefly contain an unpublished player, but clients do not see
that player or receive `playerjoin` until its first owner state exists.

## Running a separate server

Normally the first graphical client hosts. The same Room can run without a window:

```sh
python3 -m pydraw.network my_game:Arena
```

In a one-file game, the Room and anything it uses must appear above the first
`Screen` or `Network`. A Room can also live in its own module.

## Technical overview

`screen.update()` pumps the client connection. Local writes take effect immediately,
and the latest complete owner state is sent at the configured `rate`.

The server batches changes at `Room.replication_rate`. Repeated writes to the same
state key collapse to the latest value, while events remain ordered. Snapshots
initialize late joiners and repair missed frames. Resets carry generation numbers so
stale movement is ignored.

Connections use TCP with framed JSON and streaming compression. Handshake timeouts,
heartbeats, traffic limits, and bounded outgoing buffers prevent one bad connection
from stalling the Room.

Physics, collision detection, lag compensation, persistence, matchmaking, and
hostile-internet security remain game or application concerns.

## Examples

- [`net_paint.py`](../examples/net_paint.py): events with no custom Room.
- [`net_tag.py`](../examples/net_tag.py): player-owned state.
- [`net_pong.py`](../examples/net_pong.py): server-owned state and actions.
- [`net_ships.py`](../examples/net_ships.py): a trust-based multiplayer game.
- [`net_ships_v2.py`](../examples/net_ships_v2.py): authoritative combat and spawns.
