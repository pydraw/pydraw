"""
pydraw.network -- multiplayer for pydraw, with as little networking in sight as possible.

State is a shared world where **every value has an owner**. You may change what you
own; you may only read the rest. That one rule covers every kind of game.

You own your player -- write it and it appears for everyone, instantly, no lag:

    net = Network(screen, room=Room)          # one player hosts; the rest connect
    net.mine['x'] += 5                         # move MY ship -> replicated
    for pid, other in net.others():            # everyone else -> read-only
        draw(other['x'], other['y'])

The server owns everything neutral (asteroids, score) and any player field it must
decide (health). You write a Room only for those, and only the Room can change them:

    class Arena(Room):
        def start(self):
            self.state['rocks'] = make_field()     # the world -> net.state

        def join(self, player):
            player.state['hp'] = 100               # a server-managed player field

        def hit(self, player, target):             # net.call('hit', target=..)
            self.player(target).state['hp'] -= 10

A player's server-managed fields (hp) are merged into that player's entity on the
client, so `net.mine['hp']` and `other['hp']` just work -- read-only, because the
server owns them.

Everything below the classes is plumbing (sockets, framing, threads) a game never
touches.
"""

import builtins
import contextlib
import errno
import importlib.util
import json
import select
import socket
import sys
import threading
import time
import traceback
import types
import zlib

from pydraw.errors import InvalidArgumentError, PydrawError
from pydraw.serial import decode as _decode_values, encode as _encode_values
from pydraw.serial import is_serializable
from pydraw.util import verify

__all__ = ['Network', 'Room', 'Player', 'event', 'serve']

DEFAULT_PORT = 5005
TICK = 1 / 30           # how often the server runs Room.tick()
MAX_CATCHUP = 0.25      # most game time one tick is ever told has passed. Past
                        # this a truer dt stops helping: anything fast enough
                        # steps straight over what it should have hit
OWN_RATE = 60           # times a second a player's own position goes out
MAX_BACKLOG = 4 << 20   # unsent bytes we carry for one peer before giving up

# --- framing ---------------------------------------------------------------
# Every message goes out as [sequence: 4][size: 4][body], sizes big-endian.
#
# The size is counted rather than searched for, which is what lets the body be
# compressed: zlib output is arbitrary bytes, newlines included, so a separator
# would chop a compressed message into pieces.
#
# The sequence lives in the header so one broadcast can serialize its body once
# -- the number is the only part that differs between players -- and so a gap in
# the count is readable without decompressing anything.
HEADER = 8
MAX_FRAME = 64 << 20    # a size larger than this is a corrupt stream, not a message
COMPACT = (',', ':')    # json separators; the default pads with spaces
COMPRESSION = 1         # zlib level. 0 still streams, but leaves the JSON readable
                        # in a packet capture -- the escape hatch for protocol work
WINDOW = 32 << 10       # how far back zlib can refer; see _Server._body
VERIFY = 1.0            # seconds between full re-checks of the room's state, in
                        # case a change slipped past the tracking in _Tracked
RESYNC_COOLDOWN = 1.0   # least time between two snapshots for the same client

# Prefixes that tag a state key's owner on the wire. A plain key is the neutral
# world (server-owned, read as net.state); 'player:N' is client N's own slice;
# 'server:N' is the server-managed fields of player N. Games never see these.
OWNER_PREFIX = 'player:'
SERVER_PREFIX = 'server:'

# Room method names pydraw.network reserves, so a game cannot use them as net.call
# actions (net.call('tick') would be ambiguous).
RESERVED = {'start', 'join', 'leave', 'tick', 'accept',
            'broadcast', 'state', 'players', 'player', 'clear_kept_events'}

# Building one of these means the client half of a game has begun: they need a
# window, and a server hasn't got one. When pulling a Room out of a game script to
# serve it, we run the file only as far as the first line that mentions them.
CLIENT_ONLY = ('Screen', 'Network')


# --------------------------------------------------------------------------- #
#  Client
# --------------------------------------------------------------------------- #

class Network:
    """
    A player's connection to a game. Attach it to a Screen and it runs itself
    every frame -- the game loop is exactly the same as single-player.
    """

    def __init__(self, screen, host: str = 'localhost',
                 port: int = DEFAULT_PORT, room=None, rate: int = OWN_RATE):
        verify(host, str, port, int)
        if rate is not None and (not isinstance(rate, (int, float)) or rate <= 0):
            raise InvalidArgumentError(
                f'Network: rate must be how many times a second to send your own '
                f'position, or None to send every frame; received {rate!r}.')

        self._screen = screen
        self._conn = None
        self._host_server = None

        #: Neutral world state (asteroids, score). Read like a dict; read-only.
        self.state = _State()

        # Per-player slices, keyed by player id, for everyone including us.
        self._owner = {}        # id -> the slice that player owns and writes
        self._server = {}       # id -> that player's server-managed fields
        self._mine_dirty = False

        # How often your own position goes out, whatever the frame rate. See _pump.
        self._rate = rate
        self._next_own = 0.0

        # Fields of *other* players to blend between updates -- see smooth().
        self._smooth = ()
        self._history = {}      # id -> (older, when, newer, when)
        self._blend = {}        # id -> the values this frame, computed in _pump

        # The server numbers what it sends us, so a hole in the count is proof we
        # missed something. See _dispatch.
        self._seq = None
        self._resyncing = False
        self._asked_at = None

        #: Every player's id, including your own.
        self.players = []

        #: Your own player number, assigned by the server.
        self.id = None

        # Naming a room says two things: what game this is, and -- when the address
        # is this machine -- that we are willing to host it. "Host" means "host if
        # nobody here already is": whoever claims the port first runs the room, so
        # running the same program twice on one machine gives you two players.
        room = _as_room(room) if room is not None else None
        self._expected = type(room).__name__ if room is not None else None

        if room is not None and host == 'localhost':
            server = _Server(room, port)
            try:
                server.start_background()
                self._host_server = server
            except OSError as error:
                if error.errno != errno.EADDRINUSE:
                    raise
                # Somebody beat us to the port: they host, we join.

        self._connect(host, port)

        self._owner.setdefault(self.id, {})
        #: Your entity: your own slice merged with your server-managed fields.
        #: Writing an owned field replicates instantly; writing a server field raises.
        self.mine = _Mine(self, self.id)

        # Pumped once per frame from inside screen.update(); see Screen.on_frame.
        screen.on_frame(self._pump)

    # -- what a game calls --------------------------------------------------

    def others(self):
        """Iterate (id, entity) for every *other* player. Each entity is read-only."""
        for pid in self.players:
            if pid != self.id:
                yield pid, _Entity(self, pid)

    def call(self, action: str, **data) -> None:
        """
        Ask the room to do something it arbitrates (a verified hit, a spawn).
        `action` names a Room method; keyword args become its arguments. Not for
        moving yourself -- write net.mine for that.

        Nothing comes back: this returns immediately (waiting would block the frame
        loop), and an outcome reaches you later as an event or as replicated state.
        """
        verify(action, str)
        self._send({'t': 'call', 'action': action, 'data': data})

    def send(self, name: str, keep: bool = False, **data) -> None:
        """
        Send a transient event to every other player, delivered to their
        networkevent() handler. Pass keep=True only for something a late joiner
        must still receive (an accumulating effect, e.g. a paint stroke).
        """
        verify(name, str, keep, bool)
        self._send({'t': 'event', 'name': name, 'data': data, 'keep': keep})

    def smooth(self, *fields: str) -> None:
        """
        Blend these fields of *other* players between updates, so they glide
        instead of stepping.

            net.smooth('x', 'y')

        Other players arrive at the network's rate while you draw at whatever your
        loop runs at, so without this they visibly jump. Your own ship never needs
        it: you write it locally, every frame.

        Name the fields rather than having the library guess. Position is safe to
        blend; health is not -- a smoothed `hp` would read 13.7 on its way down and
        a game asking `if hp <= 0` would be wrong for a moment. Angles are not safe
        either: blending 359 to 1 sweeps the long way round, so turn those yourself.

        The cost is one update of lag (about 17ms at the default rate), since a
        value can only be blended once the one after it has arrived.
        """
        for field in fields:
            verify(field, str)
        self._smooth = tuple(fields)
        self._history.clear()
        self._blend = {}

    def connected(self) -> bool:
        return self._conn is not None and self._conn.alive

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        if self._host_server is not None:
            self._host_server.stop()
            self._host_server = None

    # -- internals ----------------------------------------------------------

    def _connect(self, host: str, port: int) -> None:
        try:
            self._conn = _Connection.connect(host, port)
        except OSError:
            raise PydrawError(
                f"Network: couldn't find a game at {host}:{port} -- "
                f"is the server running?"
            )

        # Block just long enough to learn who we are; the game needs net.id before
        # it builds the scene. The state snapshot that follows waits for _pump().
        hello = self._conn.read_until(lambda m: m.get('t') == 'hello')

        # A mispointed address, caught here rather than as a window where nothing
        # happens.
        serving = hello.get('room')
        if self._expected is not None and serving is not None \
                and serving != self._expected:
            self._conn.close()
            self._conn = None
            raise PydrawError(
                f'Network: {host}:{port} is running {serving}, but this game is '
                f'{self._expected}. Two different games cannot share a port -- '
                f'give one of them its own, or point this at the right address.'
            )

        self.id = hello['id']
        self.players = list(hello.get('players', []))
        self._seq = hello.get('n')
        self._conn.nonblocking()

    def _send(self, message: dict) -> None:
        if self._conn is None:
            raise PydrawError('Network: not connected.')
        self._conn.send(message)

    def _pump(self) -> None:
        """Once per frame: send my latest slice, then apply what has arrived."""
        if self._conn is None:
            return

        # Coalesce a frame's worth of net.mine writes into one atomic message, so
        # x and y never arrive torn -- and hold to `rate` a second, so how fast a
        # game draws stops deciding how much it sends. Holding costs nothing: the
        # slice is read as it goes out, so a skipped frame just means the next
        # message carries a slightly newer position.
        now = time.perf_counter()
        if self._mine_dirty and (self._rate is None or now >= self._next_own):
            self._conn.send({'t': 'own', 'slice': dict(self._owner[self.id])})
            self._mine_dirty = False
            if self._rate is not None:
                self._next_own = now + 1 / self._rate

        try:
            arrived = self._conn.poll()
        except (zlib.error, ValueError, ConnectionError) as error:
            # A compressed stream has no resync point, so there is no way back.
            # Close quietly rather than raise into the game loop -- that is how a
            # server that goes away already behaves, and net.connected() is where
            # a game asks.
            print(f'net: the connection stopped making sense ({error}); '
                  f'disconnected', flush=True)
            self._conn.close()
            self._conn = None
            return

        for message in arrived:
            self._dispatch(message)

        if self._smooth:
            self._blend_others()

        if self._resyncing:
            self._ask_to_resync()     # still nothing back -- ask again when due

    def _dispatch(self, message: dict) -> None:
        kind = message.get('t')

        # One count per player, so what we see runs 1, 2, 3... with nothing
        # missing. A skipped number means everything after it may be built on a
        # state that is already wrong, so ask for the world back. The message in
        # hand is still newer than what we have, so apply it too.
        number = message.get('n')
        if number is not None:
            if self._seq is not None and number != self._seq + 1:
                self._ask_to_resync()
            self._seq = number

        if kind == 'set':
            self._apply(message['key'], message['value'])
        elif kind == 'del':
            self._remove(message['key'])
        elif kind == 'snapshot':
            self._snapshot(message)
        elif kind == 'event':
            # No 'player' key means the room sent it, so the sender is None --
            # never a magic id, since player numbers start at 1 and a 0 would read
            # like a real one.
            self._handler('networkevent', message['name'], message['data'],
                          message.get('player'))
        elif kind == 'join':
            if message['id'] not in self.players:
                self.players.append(message['id'])
            self._handler('playerjoin', message['id'])
        elif kind == 'leave':
            pid = message['id']
            if pid in self.players:
                self.players.remove(pid)
            self._owner.pop(pid, None)
            self._server.pop(pid, None)
            self._forget(pid)
            self._handler('playerquit', pid)

    def _remember(self, pid: int, slice_: dict) -> None:
        """Keep the last two poses a player sent, and when each of them landed."""
        now = time.perf_counter()
        previous = self._history.get(pid)
        if previous is None:
            self._history[pid] = (slice_, now, slice_, now)
        else:
            _, _, newest, when = previous
            self._history[pid] = (newest, when, slice_, now)

    def _blend_others(self) -> None:
        """
        Work out where every other player is *now*, once for the frame, so that
        two reads in the same frame agree with each other.

        We draw each player one update behind, which is what makes this an
        interpolation rather than a guess: the pose we are heading towards has
        already arrived. A player who stops sending settles on their last known
        pose instead of drifting off.
        """
        now = time.perf_counter()
        self._blend = {}

        for pid, (older, older_at, newer, newer_at) in self._history.items():
            span = newer_at - older_at
            if span <= 0:
                self._blend[pid] = {field: newer[field]
                                    for field in self._smooth if field in newer}
                continue

            share = (now - span - older_at) / span
            share = 0.0 if share < 0 else (1.0 if share > 1 else share)

            blended = {}
            for field in self._smooth:
                start, end = older.get(field), newer.get(field)
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    blended[field] = start + (end - start) * share
                elif end is not None:
                    blended[field] = end          # nothing sensible to blend
            self._blend[pid] = blended

    def _forget(self, pid: int) -> None:
        self._history.pop(pid, None)
        self._blend.pop(pid, None)

    def _ask_to_resync(self) -> None:
        """
        Ask the server for the whole world, because ours may be out of date.

        Asked at most once per RESYNC_COOLDOWN, so a burst of missing messages is
        one request rather than one each. The server turns down a second request
        inside the same window, so _pump keeps asking until the snapshot lands
        rather than waiting on a reply that is never coming.
        """
        now = time.perf_counter()
        if self._conn is None:
            return
        if self._asked_at is not None and now < self._asked_at + RESYNC_COOLDOWN:
            return
        self._asked_at = now
        self._resyncing = True
        self._send({'t': 'resync'})

    def _snapshot(self, message: dict) -> None:
        """
        Take the server's whole world as ours.

        Sent on join, and again whenever we notice we have missed something. It has
        to *replace* rather than merge: a key deleted while we were behind is absent
        here rather than mentioned. Our own slice is the one thing we keep -- we are
        its author, and our copy is the newer one.
        """
        state = message['state']
        if 'players' in message:
            self.players = list(message['players'])

        for key in list(self.state):
            if key not in state:
                self.state._remove(key)
        for pid in list(self._owner):
            if pid != self.id and f'{OWNER_PREFIX}{pid}' not in state:
                self._owner.pop(pid)
                self._forget(pid)
        for pid in list(self._server):
            if f'{SERVER_PREFIX}{pid}' not in state:
                self._server.pop(pid)

        for key, value in state.items():
            self._apply(key, value)

        self._resyncing = False

    def _apply(self, key: str, value) -> None:
        # Nothing is announced here: state is what you *read*, and a room that wants
        # to say something happened sends an event for it. So applying a snapshot
        # and applying a single change are the same operation.
        if key.startswith(OWNER_PREFIX):
            pid = int(key[len(OWNER_PREFIX):])
            # We are the source of truth for our OWN slice -- never let the server
            # overwrite it (that is what removes input lag). Others' slices we take.
            if pid != self.id:
                if self._smooth:
                    self._remember(pid, value)
                self._owner[pid] = value
        elif key.startswith(SERVER_PREFIX):
            self._server[int(key[len(SERVER_PREFIX):])] = value
        else:
            self.state._assign(key, value)          # neutral world

    def _remove(self, key: str) -> None:
        if key.startswith(OWNER_PREFIX):
            self._forget(int(key[len(OWNER_PREFIX):]))
            self._owner.pop(int(key[len(OWNER_PREFIX):]), None)
        elif key.startswith(SERVER_PREFIX):
            self._server.pop(int(key[len(SERVER_PREFIX):]), None)
        else:
            self.state._remove(key)

    def _handler(self, name: str, *args) -> None:
        handler = self._screen.registry.get(name)
        if handler is not None:
            handler(*args)


class _State(dict):
    """
    The neutral world, as the client sees it: readable like a dict, not writable.

    Every way in has to be closed, not just `state[key] = value`: CPython does not
    route dict.update() and friends through a subclass's __setitem__, and a write
    that quietly took effect locally while every other player saw nothing is worse
    than no protection at all. The internals go through _assign and _remove.
    """

    _REFUSAL = ("net.state is read-only -- the server owns the world. "
                "Ask it to change something with net.call('some_action', ...).")

    def __setitem__(self, key, value):
        raise PydrawError(self._REFUSAL)

    def __delitem__(self, key):
        raise PydrawError(self._REFUSAL)

    def update(self, *args, **kwargs):
        raise PydrawError(self._REFUSAL)

    def setdefault(self, key, default=None):
        raise PydrawError(self._REFUSAL)

    def pop(self, *args):
        raise PydrawError(self._REFUSAL)

    def popitem(self):
        raise PydrawError(self._REFUSAL)

    def clear(self):
        raise PydrawError(self._REFUSAL)

    def __ior__(self, other):
        raise PydrawError(self._REFUSAL)

    def _assign(self, key, value):
        dict.__setitem__(self, key, value)

    def _remove(self, key):
        dict.pop(self, key, None)


class _Entity:
    """
    A read-only view of one player: their owned slice merged with their
    server-managed fields (the server's values win on any overlap).
    """

    def __init__(self, net: Network, pid: int):
        self._net = net
        self._pid = pid

    def _merged(self) -> dict:
        server = self._net._server.get(self._pid, {})
        merged = {**self._net._owner.get(self._pid, {}), **server}

        # Smoothed fields stand in for the owner's raw values, never for a
        # server-managed one: a value on its way from 100 to 80 was never true.
        for field, value in self._net._blend.get(self._pid, {}).items():
            if field not in server:
                merged[field] = value
        return merged

    def __getitem__(self, key):
        return self._merged()[key]

    def get(self, key, default=None):
        return self._merged().get(key, default)

    def __contains__(self, key):
        return key in self._merged()

    def __iter__(self):
        return iter(self._merged())

    def keys(self):
        return self._merged().keys()

    def values(self):
        return self._merged().values()

    def items(self):
        return self._merged().items()

    def __len__(self):
        return len(self._merged())

    def __setitem__(self, key, value):
        raise PydrawError(
            "this player's state is read-only -- only its owner can move it."
        )

    def __repr__(self):
        return f'<entity {self._pid} {self._merged()}>'


class _Mine(_Entity):
    """Your own entity: owned fields are writable, server-managed fields are not."""

    def __setitem__(self, key, value):
        if key in self._net._server.get(self._pid, {}):
            raise PydrawError(
                f"net.mine[{key!r}] is managed by the server -- you can't change it."
            )
        # Applied locally at once (no lag); _pump sends the slice this frame.
        self._net._owner.setdefault(self._pid, {})[key] = value
        self._net._mine_dirty = True


# --------------------------------------------------------------------------- #
#  Server side -- Room and Player
# --------------------------------------------------------------------------- #

def event(name: str):
    """
    Mark a Room method as the reviewer for one kind of `net.send`.

        class Arena(Room):
            @event('shot')
            def review_shot(self, player, data):
                data['shooter'] = player.id     # add what only the server knows
                return data

    Without a reviewer, `net.send('shot')` is simply passed on to the other players
    -- which is what makes a game with no server code possible at all. Add one and
    the same call becomes something the room gets to inspect first. Authority is a
    dial, not a different way of writing your game.

    What you return decides what the others see:

      - nothing          the event is passed on unchanged
      - a dict           that is passed on instead of the original
      - False            it is dropped, and nobody hears it

    Nothing being the harmless case is deliberate: a reviewer written just to
    *look* at something, whose author forgot to return, still leaves a working game.

    This only means anything inside a Room.
    """
    verify(name, str)

    def mark(method):
        method._pydraw_event = name
        return method

    return mark


class Room:
    """
    The authority for one game. Subclass it to:

      - set up the neutral world in start() (self.state)
      - give joining players their server-managed fields (player.state)
      - run a server-side loop in tick(dt)
      - respond to actions (any method matching a net.call name)
      - optionally vet players' own writes in accept()

    self.state (the world) and player.state (a player's server fields) are writable
    here and only here. Clients read the results; they cannot change them.
    """

    def __init__(self):
        self._changes = _Changes()
        self._state = _TrackedDict(self._changes, None)
        self.players = []
        self._server = None

    @property
    def state(self) -> dict:
        """
        The neutral world -- asteroids, score, the clock. Write it like any dict;
        the players read the results as net.state.
        """
        return self._state

    @state.setter
    def state(self, value: dict) -> None:
        # Replacing the whole thing has to keep the tracking and remember the keys
        # that just went, so they are deleted on the clients rather than lingering.
        verify(value, dict)
        gone = set(self._state)
        self._state = _TrackedDict(self._changes, None)
        self._state.update(value)
        self._changes.keys |= gone

    def __init_subclass__(cls, **kwargs):
        """
        Collect the @event reviewers a subclass declares, so that a duplicate is
        caught when the class is written and not on the first shot fired.
        """
        super().__init_subclass__(**kwargs)

        reviewers = dict(getattr(cls, '_reviewers', {}))
        for attribute in vars(cls).values():
            name = getattr(attribute, '_pydraw_event', None)
            if name is None:
                continue
            if name in reviewers and reviewers[name].__name__ != attribute.__name__:
                raise InvalidArgumentError(
                    f'Room: {cls.__name__} has two @event({name!r}) reviewers -- '
                    f'{reviewers[name].__name__}() and {attribute.__name__}(). One '
                    f'event, one reviewer; call a shared method from both if they '
                    f'need the same logic.'
                )
            reviewers[name] = attribute
        cls._reviewers = reviewers

    #: event name -> the method reviewing it, filled in by __init_subclass__
    _reviewers = {}

    # override these
    def start(self) -> None:
        """Called once when the room opens. Seed self.state."""

    def join(self, player) -> None:
        """Called when a player connects. Give them player.state fields."""

    def leave(self, player) -> None:
        """Called when a player disconnects. Prune any world data you keyed by id."""

    def tick(self, dt: float) -> None:
        """
        Called ~30 times a second. dt is how long really passed since the last
        tick, so multiply by it rather than counting ticks -- a busy moment makes
        one longer step instead of a burst of catch-up ones.
        """

    def accept(self, player, proposed: dict, current: dict) -> dict:
        """
        Review a client's write to its own slice; return what actually sticks.
        Default: trust it. Override to clamp or reject (this is your anti-cheat).
        """
        return proposed

    # call these
    def player(self, player_id: int):
        """The Player for an id (or None)."""
        return self._server._players.get(player_id)

    def broadcast(self, name: str, **data) -> None:
        """Send a transient event to every player (from the server, player 0)."""
        verify(name, str)
        self._server._broadcast({'t': 'event', 'name': name, 'data': data})

    def clear_kept_events(self) -> int:
        """
        Forget the kept events -- the ones sent with net.send(..., keep=True), which
        every late joiner is replayed on arrival. Returns how many were dropped.

        Nothing caps that log for you, since only your game knows what its limit
        should be. Clear it when a round ends, or when it has grown past enough.
        """
        replay = self._server._replay
        dropped = len(replay)
        replay.clear()
        return dropped

    def _bind(self, server) -> None:
        self._server = server


class Player:
    """A connected player, as seen by the Room."""

    def __init__(self, player_id: int, conn, server):
        self.id = player_id
        self._changes = _Changes()
        self._state = _TrackedDict(self._changes, None)
        self._conn = conn
        self._server = server

    @property
    def state(self) -> dict:
        """
        This player's server-managed fields (hp, ammo). Write here; the client sees
        them merged into that player's entity, read-only.
        """
        return self._state

    @state.setter
    def state(self, value: dict) -> None:
        verify(value, dict)
        gone = set(self._state)
        self._state = _TrackedDict(self._changes, None)
        self._state.update(value)
        self._changes.keys |= gone

    @property
    def slice(self) -> dict:
        """
        What this player owns and writes (its position slice), as the server last
        accepted it. Read-only for the Room -- use it to adjudicate (hit tests,
        collisions). Writing it here would not replicate; the owner drives it.
        """
        return self._server._owner.get(self.id, {})

    def send(self, name: str, **data) -> None:
        """Send a transient event to just this player (from the server)."""
        verify(name, str)
        self._server._send_to(self._conn,
                              {'t': 'event', 'name': name, 'data': data})

    def resync(self) -> None:
        """
        Send this player the whole world again.

        Players ask for this themselves the moment they notice they have missed
        something, so a game never has to call it. It is here for when the server
        knows better -- it has just rebuilt the world, say.
        """
        self._server._resync(self._conn, forced=True)

    def __repr__(self):
        return f'Player({self.id})'


# --------------------------------------------------------------------------- #
#  Change tracking (plumbing -- a Room writes ordinary dicts and lists)
# --------------------------------------------------------------------------- #
#
# The server has to know which parts of the world changed since it last told the
# players. Rather than deep-copy everything and diff it every tick -- which costs
# the same whether one asteroid moved or nothing did -- self.state and
# player.state note their own changes. They are real dict and list subclasses, so
# json.dumps, len() and isinstance behave as they always did, that record which
# *top level* key was touched however deep the change was:
#
#     self.state['rocks'][3]['x'] += 1     ->  'rocks' changed
#     self.state['strokes'].append(s)      ->  'strokes' changed
#
# Top level is the right grain because that is what goes on the wire: a key and
# its whole new value.
#
# One thing worth knowing: putting a list or dict into state stores a tracked
# version of it, so `self.state['rocks']` is not the object you handed over. Keep
# your own copy and the two drift apart -- write through self.state and this never
# comes up. _Server._sync re-checks everything once a second regardless, so a
# change made some way this cannot see still gets out, just a moment later.


class _Changes:
    """The set of top-level keys written since the server last collected them."""

    __slots__ = ('keys',)

    def __init__(self):
        self.keys = set()

    def take(self) -> set:
        """Hand over what has changed and start counting again."""
        keys, self.keys = self.keys, set()
        return keys


def _track(value, changes: _Changes, key):
    """A copy of `value` whose containers report changes against `key`."""
    if isinstance(value, dict):
        tracked = _TrackedDict(changes, key)
        for inner_key, inner in value.items():
            dict.__setitem__(tracked, inner_key, _track(inner, changes, key))
        return tracked
    if isinstance(value, list):
        tracked = _TrackedList(changes, key)
        list.extend(tracked, (_track(inner, changes, key) for inner in value))
        return tracked
    return value                      # a number or a string cannot change in place


class _TrackedDict(dict):
    """
    A dict that says when it was written to.

    With `key` None it is the root -- self.state itself -- and reports the key
    being written. Nested inside a value it reports the top-level key it lives
    under, so a change any distance down still names the thing to send.
    """

    __slots__ = ('_changes', '_key')

    def __init__(self, changes: _Changes, key):
        dict.__init__(self)
        self._changes = changes
        self._key = key

    def _owner(self, key):
        return key if self._key is None else self._key

    def _mark(self, key) -> None:
        self._changes.keys.add(self._owner(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, _track(value, self._changes, self._owner(key)))
        self._mark(key)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._mark(key)

    def pop(self, key, *default):
        had = key in self
        value = dict.pop(self, key, *default)
        if had:
            self._mark(key)
        return value

    def popitem(self):
        key, value = dict.popitem(self)
        self._mark(key)
        return key, value

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default                    # wraps and marks
        return dict.__getitem__(self, key)

    def update(self, *args, **kwargs):
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    def clear(self):
        keys = list(self)
        dict.clear(self)
        for key in keys:
            self._mark(key)

    def __ior__(self, other):
        self.update(other)
        return self


class _TrackedList(list):
    """A list that says when it was changed. Always lives under a top-level key."""

    __slots__ = ('_changes', '_key')

    def __init__(self, changes: _Changes, key):
        list.__init__(self)
        self._changes = changes
        self._key = key

    def _mark(self) -> None:
        self._changes.keys.add(self._key)

    def _wrap(self, value):
        return _track(value, self._changes, self._key)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            value = [self._wrap(item) for item in value]
        else:
            value = self._wrap(value)
        list.__setitem__(self, index, value)
        self._mark()

    def __delitem__(self, index):
        list.__delitem__(self, index)
        self._mark()

    def append(self, value):
        list.append(self, self._wrap(value))
        self._mark()

    def insert(self, index, value):
        list.insert(self, index, self._wrap(value))
        self._mark()

    def extend(self, values):
        list.extend(self, (self._wrap(value) for value in values))
        self._mark()

    def remove(self, value):
        list.remove(self, value)
        self._mark()

    def pop(self, index=-1):
        value = list.pop(self, index)
        self._mark()
        return value

    def clear(self):
        list.clear(self)
        self._mark()

    def sort(self, **kwargs):
        list.sort(self, **kwargs)
        self._mark()

    def reverse(self):
        list.reverse(self)
        self._mark()

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __imul__(self, count):
        list.__imul__(self, count)
        self._mark()
        return self


def serve(room, port: int = DEFAULT_PORT) -> None:
    """
    Run a Room as a standalone server (blocks until Ctrl+C). Use this to host on a
    dedicated machine instead of inside a player's program.
    """
    server = _Server(_as_room(room), port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nserver stopped')


# --------------------------------------------------------------------------- #
#  Server engine (plumbing -- games never see this)
# --------------------------------------------------------------------------- #

class _Server:
    def __init__(self, room: Room, port: int, host: str = ''):
        self._room = room
        self._port = port
        self._host = host

        self._listener = None
        self._conns = {}          # socket -> _Connection
        self._ids = {}            # socket -> player id
        self._players = {}        # player id -> Player
        self._next_id = 1

        self._owner = {}          # id -> latest accepted owner slice
        # What we last told the clients, kept as the JSON text we sent rather than
        # a deep copy: two values that serialize the same are the same as far as
        # anyone out there can tell, and a string is cheap to keep and compare.
        self._world_shadow = {}   # world key -> JSON of the value last sent
        self._server_shadow = {}  # id -> JSON of the server slice last sent
        self._replay = []         # kept events, resent to late joiners
        self._reported = set()    # Room failures already printed, so we say each once
        self._running = False
        self._last_tick = 0.0
        self._next_tick = 0.0
        self._next_verify = 0.0

    # -- lifecycle ----------------------------------------------------------

    def listen(self) -> None:
        """
        Claim the port. Raises OSError(EADDRINUSE) if somebody already holds it --
        which is how Network tells "I am the host" from "someone else already is".
        """
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((self._host, self._port))
            listener.listen()
        except OSError:
            listener.close()      # losing the race is routine; don't leak on it
            raise
        self._listener = listener

    def start_background(self) -> None:
        # Bind here rather than on the thread: the caller has to be able to catch
        # "that port is taken", and once bind() returns, connections queue up even
        # before the thread reaches accept() -- so a racing joiner never misses us.
        self.listen()

        ready = threading.Event()
        self._thread = threading.Thread(
            target=lambda: self.serve_forever(ready), daemon=True)
        self._thread.start()
        if not ready.wait(timeout=5):
            self._listener.close()
            raise PydrawError('Network: the hosted server failed to start.')

    def stop(self, wait: float = 1.0) -> None:
        """
        Ask the room to close, and wait for it to let go of the port.

        The flag is all we set: the sockets belong to the serve thread, sitting in
        select() on them right now, so it closes its own on the way out (within one
        TICK). We wait for that because a game often opens another room on the same
        port straight after closing one, and would find it still held.
        """
        self._running = False
        thread = getattr(self, '_thread', None)
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=wait)

    def serve_forever(self, ready: 'threading.Event' = None) -> None:
        if self._listener is None:
            self.listen()

        self._room._bind(self)
        self._room.start()
        # Whatever start() seeded is already in hand for anyone who joins, so it
        # counts as told: record it and let _sync report only what happens next.
        self._world_shadow = {key: _canonical(value)
                              for key, value in self._room.state.items()}
        self._room._changes.take()

        self._running = True
        started = time.perf_counter()
        self._last_tick = started
        self._next_tick = started + TICK
        self._next_verify = started + VERIFY
        if ready is not None:
            ready.set()

        while self._running:
            now = time.perf_counter()
            timeout = max(0.0, self._next_tick - now)
            readable, _, _ = select.select(
                [self._listener] + list(self._conns), [], [], timeout)

            for sock in readable:
                if sock is self._listener:
                    self._accept()
                else:
                    self._receive(sock)

            now = time.perf_counter()
            if now >= self._next_tick:
                # dt is what really passed, and the next deadline is set from now,
                # so an overrun is one long step rather than a debt. Adding TICK to
                # a deadline already past would leave it past, and a second of
                # stall would come back as thirty ticks each told it was 1/30.
                #
                # Capped, because past a point a longer step stops being a truer
                # one -- a ball told it moved for a whole second lands on the far
                # side of a paddle it should have hit. The world falls behind the
                # clock instead, which is the smaller lie.
                self._guarded('tick()', self._room.tick,
                              min(now - self._last_tick, MAX_CATCHUP))
                self._last_tick = now
                self._next_tick = now + TICK

            # One place syncs the world and server slices; owner slices sync
            # immediately in _handle_own (so a mover feels no round-trip).
            self._sync()
            self._flush_all()

        # Ours to close, on the thread that has been using them.
        for sock in list(self._conns):
            self._conns.pop(sock, None)
            sock.close()
        self._listener.close()

    # -- connections --------------------------------------------------------

    def _accept(self) -> None:
        sock, _ = self._listener.accept()
        conn = _Connection(sock)
        conn.nonblocking()      # a slow client must never stall the serve loop
        player_id = self._next_id
        self._next_id += 1

        self._conns[sock] = conn
        self._ids[sock] = player_id
        player = Player(player_id, conn, self)
        self._players[player_id] = player
        self._owner[player_id] = {}
        self._room.players.append(player)

        # Who they are, then the room's setup for them, then the whole world -- in
        # that order, so a late joiner is correct the moment it starts drawing.
        self._send_to(conn, {'t': 'hello', 'id': player_id,
                             'players': list(self._ids.values()),
                             'room': type(self._room).__name__})
        self._guarded('join()', self._room.join, player)
        self._resync(conn, forced=True)
        for event in self._replay:
            self._send_to(conn, event)

        self._broadcast({'t': 'join', 'id': player_id}, skip=sock)

    def _receive(self, sock) -> None:
        conn = self._conns[sock]
        try:
            messages = conn.poll()
        except OSError:
            messages = None
        except (zlib.error, ValueError) as error:
            # A compressed stream has no resync point, so a connection that stops
            # making sense cannot be recovered -- drop that one player. Neither of
            # these is an OSError, so left alone it would end the game for everyone.
            self._complain(f'player {self._ids.get(sock)} sent something we could '
                           f'not read ({error}); dropping them')
            messages = None

        if messages is None or not conn.alive:
            self._drop(sock)
            return

        for message in messages:
            # A message can arrive whole and still not be what it claims to be --
            # an event with no name, a key that is not a number. Reading it is the
            # one place the serve loop touches a value a player chose, so a failure
            # here must cost that player its turn and nothing more; left alone it
            # would end the game for everybody.
            self._guarded(f"a {message.get('t')!r} message from player "
                          f'{self._ids.get(sock)}', self._handle, sock, message)

    def _drop(self, sock) -> None:
        player_id = self._ids.pop(sock, None)
        self._conns.pop(sock, None)
        player = self._players.pop(player_id, None)
        self._owner.pop(player_id, None)
        self._server_shadow.pop(player_id, None)
        if player is not None and player in self._room.players:
            self._room.players.remove(player)
        sock.close()

        if player_id is not None:
            self._guarded('leave()', self._room.leave, player)
            # Drop the departed player's two keys everywhere -> sprites despawn.
            self._broadcast({'t': 'del', 'key': f'{OWNER_PREFIX}{player_id}'})
            self._broadcast({'t': 'del', 'key': f'{SERVER_PREFIX}{player_id}'})
            self._broadcast({'t': 'leave', 'id': player_id})

    # -- message handling ---------------------------------------------------

    def _handle(self, sock, message: dict) -> None:
        kind = message.get('t')
        player = self._players.get(self._ids.get(sock))
        if player is None:
            return

        if kind == 'own':
            self._handle_own(sock, player, message.get('slice'))
        elif kind == 'call':
            self._run_action(sock, player, message.get('action'),
                             message.get('data', {}))
        elif kind == 'event':
            self._relay_event(sock, player, message)
        elif kind == 'resync':
            self._resync(self._conns[sock])

    def _resync(self, conn, forced: bool = False) -> None:
        """
        Hand one player the whole world -- what a joiner is sent, sent again.

        Rate-limited: a client that has decided it is behind and keeps saying so
        must not have us compose the world for it over and over.
        """
        now = time.perf_counter()
        if not forced and now < conn.resync_at:
            return
        conn.resync_at = now + RESYNC_COOLDOWN
        self._send_to(conn, {'t': 'snapshot', 'state': self._compose(),
                             'players': list(self._ids.values())})

    def _relay_event(self, sock, player: Player, message: dict) -> None:
        """
        Pass a client's event on to the others -- through the room, if it cares.

        With no @event reviewer this is a plain relay, which is what lets a game
        have no server code at all. With one, the room sees it first and decides.
        """
        name, data = message['name'], message['data']
        reviewer = self._room._reviewers.get(name)

        if reviewer is not None:
            verdict = self._guarded(f'@event({name!r})', reviewer,
                                    self._room, player, data)
            if verdict is False:
                return                          # the room refused it
            if isinstance(verdict, dict):
                data = verdict                  # the room rewrote it
            # Anything else, None included, passes it on as it arrived.

        out = {'t': 'event', 'player': player.id, 'name': name, 'data': data}
        if message.get('keep'):
            self._replay.append(out)
        self._broadcast(out, skip=sock)

    def _handle_own(self, sock, player: Player, proposed: dict) -> None:
        current = self._owner.get(player.id, {})

        # The one value on this path a player chose rather than the Room, so it
        # is checked before the Room sees it. Something that is not a dict would
        # sit where every other client expects one and break each of them on its
        # next read. Not a Room's mistake, so it skips the fallback below.
        if not isinstance(proposed, dict):
            self._complain(
                f'player {player.id} sent {type(proposed).__name__} where its own '
                f'slice should be, so that write was ignored')
            return

        # A broken accept() falls back to the write it was reviewing -- it sits on
        # the path of every movement any player makes, so whatever it does wrong
        # must not freeze somebody where they stand. Taking the proposal is what a
        # Room with no accept() does anyway: the anti-cheat stops, the game does not.
        try:
            accepted = self._room.accept(player, proposed, current)
        except Exception:                                    # noqa: BLE001
            self._report('accept()')
            accepted = proposed

        if not isinstance(accepted, dict):
            # Almost always a missing `return`, and storing it would replace the
            # player's whole slice with nothing -- they would vanish for everybody.
            self._complain(
                f'accept() returned {type(accepted).__name__} rather than a slice, '
                f'so the write was let through -- return `proposed` to trust it or '
                f'`current` to turn it down')
            accepted = proposed

        self._owner[player.id] = accepted
        # Tell everyone but the owner -- the owner already applied it locally, and
        # is the source of truth for its own slice (that is what removes the lag).
        self._broadcast({'t': 'set', 'key': f'{OWNER_PREFIX}{player.id}',
                         'value': accepted}, skip=sock)

    def _guarded(self, what: str, function, *args, **kwargs):
        """
        Run one step on behalf of a single player without letting it take the room
        down with it.

        Everything a game writes -- tick(), join(), an action -- is called straight
        from the serve loop, so an unhandled KeyError in one student's fire() would
        propagate out of serve_forever and disconnect *everybody*. One person's bug
        should cost that person a turn, not end the game for the room. Reading a
        player's message is wrapped for the same reason.
        """
        try:
            return function(*args, **kwargs)
        except Exception:                                    # noqa: BLE001
            self._report(what)
            return None

    def _report(self, what: str) -> None:
        """
        Print a failure in a game's Room code -- once. tick() runs 30 times a
        second, so a bug in it would otherwise bury the terminal in one traceback
        and hide everything else.
        """
        report = traceback.format_exc()
        signature = (what, report)
        if signature in self._reported:
            return

        self._reported.add(signature)
        print(f'net: {what} raised, and the room kept going --\n{report}'
              f'net: (further identical failures in {what} will not be reported)',
              flush=True)

    def _complain(self, message: str, about=None) -> None:
        """
        Say something is wrong with the room's state -- once, not every tick.

        `about` names the thing being complained about, for a message carrying a
        changing number: without it, a warning about a growing key would read as a
        new complaint at every size it passes through.
        """
        signature = message if about is None else about
        if signature in self._reported:
            return
        self._reported.add(signature)
        print(f'net: {message}', flush=True)

    def _run_action(self, sock, player: Player, action, data: dict) -> None:
        if not isinstance(action, str) or action in RESERVED or action.startswith('_'):
            print(f'net: ignoring reserved/invalid action {action!r}', flush=True)
            return

        method = getattr(self._room, action, None)
        if not callable(method):
            print(f'net: no such action {action!r} on {type(self._room).__name__}',
                  flush=True)
            return

        try:
            announcement = method(player, **data)
        except TypeError as error:
            if error.__traceback__.tb_next is None:
                print(f'net: action {action!r} rejected these arguments: {error}',
                      flush=True)
            else:
                self._report(f'action {action!r}')
            return
        except Exception:                                    # noqa: BLE001
            self._report(f'action {action!r}')
            return

        # What the method returns is what the room tells everyone else happened --
        # the outcome, not the request, so a client cannot fake it by sending the
        # announcement itself. Returning nothing keeps it private. The caller is
        # skipped: they asked for it, and drew it locally the instant they did.
        if isinstance(announcement, dict):
            self._broadcast({'t': 'event', 'player': player.id,
                             'name': action, 'data': announcement}, skip=sock)
        elif announcement is not None:
            print(f'net: action {action!r} returned {type(announcement).__name__}; '
                  f'return a dict to tell the other players, or nothing to keep it '
                  f'private', flush=True)

    # -- state sync ---------------------------------------------------------

    def _sync(self) -> None:
        """
        Send changes to the neutral world and to players' server slices.

        self.state and player.state keep their own list of what was written (see
        _Changes), so the usual pass looks only at those keys and leaves the rest
        of the world alone however large it is. Once a second every key is checked
        instead -- a backstop for a change made to an object the Room kept its own
        reference to, which tracking cannot see.
        """
        now = time.perf_counter()
        sweep = now >= self._next_verify
        if sweep:
            self._next_verify = now + VERIFY

        world = self._room.state
        written = self._room._changes.take()
        live = world.keys()

        for key in (set(live) if sweep else written & live):
            self._publish(key, world[key], self._world_shadow,
                          f'net.state[{key!r}]')
        for key in ((self._world_shadow.keys() - live) if sweep
                    else (written - live)):
            if self._world_shadow.pop(key, None) is not None:
                self._broadcast({'t': 'del', 'key': key})

        for pid, player in self._players.items():
            if player._changes.take() or sweep:
                self._publish(pid, dict(player.state), self._server_shadow,
                              f'player {pid} state',
                              key=f'{SERVER_PREFIX}{pid}')

    def _publish(self, shadow_key, value, shadow: dict, what: str,
                 key: str = None) -> None:
        """Broadcast a value if it really is not what the clients already have."""
        text = _canonical(value)
        if text is None:
            # Not something that can be sent -- a sprite, a set. Say so once and
            # carry on; sending it would take the whole room down. Name the thing
            # itself, since the key's type would only ever say 'dict'.
            culprit = _unsendable(value)
            blame = (f'a {type(culprit).__name__} ({culprit!r})'
                     if culprit is not None else 'something that cannot be sent')
            self._complain(f'{what} holds {blame}, so the players cannot be told '
                           f'about it -- room state has to be numbers, strings, '
                           f'lists and dicts')
            return
        if shadow.get(shadow_key) == text:
            return
        shadow[shadow_key] = text
        self._broadcast({'t': 'set', 'key': key if key is not None else shadow_key,
                         'value': value})

    def _compose(self) -> dict:
        """The whole replicated world, prefixed by owner, for a join snapshot."""
        snap = dict(self._room.state)
        for pid, slice in self._owner.items():
            snap[f'{OWNER_PREFIX}{pid}'] = slice
        for pid, player in self._players.items():
            snap[f'{SERVER_PREFIX}{pid}'] = dict(player.state)
        return snap

    # -- sending ------------------------------------------------------------

    def _broadcast(self, message: dict, skip=None) -> None:
        # Encode once for the whole room: only change the number before the body
        body = self._body(message)
        if body is None:
            return
        for sock, conn in list(self._conns.items()):
            if sock is skip:
                continue
            self._push(conn, body)

    def _send_to(self, conn, message: dict) -> None:
        body = self._body(message)
        if body is not None:
            self._push(conn, body)

    def _body(self, message: dict):
        """Encode a message, or say so once and drop it if it cannot be encoded."""
        try:
            raw = _encode(message)
        except (TypeError, ValueError):
            # Something in here is not JSON. Dropping one message is survivable;
            # letting it out of the serve loop would end the game for everyone.
            self._complain(f"a {message.get('t')!r} message could not be sent -- "
                           f"it holds something that is not a number, string, "
                           f"list or dict")
            return None

        # Each connection compresses against what it has already sent, which is
        # what makes a barely-changed world nearly free -- but zlib can only look
        # back WINDOW bytes. A value larger than that cannot be matched against its
        # previous copy at all, and the cost jumps sharply rather than creeping up.
        # Remembered by key, not by the size it is growing through.
        if len(raw) > WINDOW and message.get('t') == 'set':
            self._complain(
                f"net.state[{message.get('key')!r}] is {len(raw) // 1024} KB, past "
                f"the {WINDOW // 1024} KB the compressor can look back through, so "
                f"every update sends all of it. Send the players less of it -- only "
                f"what is near them, or a seed they can build it from themselves.",
                about=('oversized', message.get('key')))
        return raw

    def _push(self, conn, body: bytes) -> None:
        # Each player counts separately: plenty of what we send goes to everyone
        # *but* one person (your own ship coming back to you, an event you are the
        # author of), and a shared count would leave gaps that look like loss.
        #
        # Nothing to catch here -- flush() owns the socket, so a peer that has gone
        # is marked dead there and _flush_all sweeps it on this pass.
        conn.send_body(body)

    def _flush_all(self) -> None:
        """Push out buffered bytes, and drop anyone who has gone or fallen behind."""
        for sock, conn in list(self._conns.items()):
            conn.flush()
            if not conn.alive:
                self._drop(sock)


# --------------------------------------------------------------------------- #
#  Framing (the one genuinely networking-shaped piece)
# --------------------------------------------------------------------------- #

def _encode(message: dict) -> bytes:
    """
    A message as JSON bytes, ready for any number of peers.

    Compression deliberately does *not* happen here: each connection compresses
    into its own running stream, so what it sends can refer back to what it has
    already sent. What a broadcast shares is this step, the expensive one.
    """
    return json.dumps(message, separators=COMPACT,
                      default=_encode_values).encode()


class _Connection:
    """
    Wraps a socket and turns its byte stream into whole JSON messages.

    TCP delivers bytes, not messages: one recv() can hand back half a message or
    several at once. So every message says how long it is, and we only decode the
    parts of the buffer we have all of. See the framing constants for why the
    length is stated rather than marked with a separator.
    """

    def __init__(self, sock):
        self._sock = sock
        self._buffer = b''
        self._outgoing = b''
        self._pending = []
        self.alive = True
        self.seq = 0            # server side: how many messages this peer has been
        self.resync_at = 0.0    # sent, and when it may next ask for the world back

        # One running stream each way. The compressor remembers what it has sent,
        # so a world that barely changed costs almost nothing to send again -- zlib
        # does the differencing, in C, against the real bytes. It also puts the two
        # ends in lockstep: every message must pass through, in order.
        self._deflate = zlib.compressobj(COMPRESSION)
        self._inflate = zlib.decompressobj()

    @classmethod
    def connect(cls, host: str, port: int) -> '_Connection':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))
        except OSError:
            sock.close()      # don't leak the socket on every failed attempt
            raise
        return cls(sock)

    def nonblocking(self) -> None:
        self._sock.setblocking(False)

    def send(self, message: dict) -> None:
        """
        Queue a message and push out as much as the kernel will take.

        Never blocks and never fails on a full buffer: the server sends from inside
        its one serve loop, where waiting on a wedged client would freeze everybody
        else's game, and the client sends from inside the frame loop, where a stall
        is a visible hitch.
        """
        self.send_body(_encode(message))

    def send_body(self, raw: bytes) -> None:
        """
        Queue JSON that `_encode` already prepared, compressed into this peer's
        own stream and numbered for them.

        Split out from send() so a broadcast serializes once rather than once per
        player -- the number is the only part of the frame that differs.
        """
        self.seq += 1
        body = self._deflate.compress(raw) + self._deflate.flush(zlib.Z_SYNC_FLUSH)
        self._outgoing += (self.seq.to_bytes(4, 'big')
                           + len(body).to_bytes(4, 'big') + body)
        self.flush()

    def flush(self) -> None:
        """Drain what we can of the outgoing buffer. Safe to call at any time."""
        while self._outgoing:
            try:
                sent = self._sock.send(self._outgoing)
            except (BlockingIOError, InterruptedError):
                break                     # kernel buffer full; try again next pass
            except OSError:
                self.alive = False        # gone; the loop sweeps it up
                return
            if not sent:
                break
            self._outgoing = self._outgoing[sent:]

        # A peer this far behind is not coming back, and the backlog is now ours to
        # carry. Better to drop them than to grow forever on their behalf.
        if len(self._outgoing) > MAX_BACKLOG:
            self.alive = False

    def poll(self) -> list:
        """Return every complete message available right now; never blocks."""
        self.flush()                      # keep anything the buffer refused moving

        while True:
            readable, _, _ = select.select([self._sock], [], [], 0)
            if not readable:
                break
            data = self._sock.recv(4096)
            if not data:
                self.alive = False
                break
            self._buffer += data
            self._collect()

        messages, self._pending = self._pending, []
        return messages

    def read_until(self, matches) -> dict:
        """Block until a message satisfying `matches` arrives, and return it."""
        while True:
            for i, message in enumerate(self._pending):
                if matches(message):
                    return self._pending.pop(i)
            data = self._sock.recv(4096)
            if not data:
                raise ConnectionError('the server closed the connection')
            self._buffer += data
            self._collect()

    def close(self) -> None:
        self.alive = False
        self._sock.close()

    def _collect(self) -> None:
        """Take every whole frame out of the buffer, leaving any partial one."""
        while len(self._buffer) >= HEADER:
            size = int.from_bytes(self._buffer[4:8], 'big')

            if size > MAX_FRAME:
                # Nothing we send is this big, so the stream is not frames any
                # more. Say so instead of blocking for ever on bytes that are
                # never going to arrive.
                self.alive = False
                self._buffer = b''
                raise ConnectionError(
                    f'the connection sent a {size} byte message, which cannot be '
                    f'right -- the stream is out of step')

            if len(self._buffer) < HEADER + size:
                return                    # the rest of it has not arrived yet

            body = self._buffer[HEADER:HEADER + size]
            number = int.from_bytes(self._buffer[0:4], 'big')
            self._buffer = self._buffer[HEADER + size:]

            message = json.loads(self._inflate.decompress(body).decode(),
                                 object_hook=_decode_values)
            if number:
                # Both ends number what they send, but only the client reads it
                # back: a hole in the server's count means it missed a change and
                # must ask for the world again. The server ignores the numbers
                # coming the other way, since it is the one being told.
                message['n'] = number
            self._pending.append(message)


# --------------------------------------------------------------------------- #
#  Helpers / standalone entry point
# --------------------------------------------------------------------------- #

def _canonical(value) -> str:
    """
    A value as the one piece of text that stands for it, or None if it cannot be
    sent at all. Keys are sorted so that a dict rebuilt in a different order does
    not read as a change and go out again for nothing.

    Encodes pydraw's own values the same way the wire does -- it has to, since this
    decides whether a key *can* be sent at all.
    """
    try:
        return json.dumps(value, sort_keys=True, default=_encode_values)
    except (TypeError, ValueError):
        return None


def _unsendable(value, depth: int = 0):
    """
    The first thing inside `value` that JSON cannot carry, or None if the trouble
    is something else (a loop in the data, say). Only ever runs to explain a
    failure, so walking the whole structure is fine.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return None
    if is_serializable(value):                # a Color, a Location: these travel
        return None
    if depth > 20:                            # a loop; the caller says so instead
        return None
    if isinstance(value, dict):
        for key, inner in value.items():
            if not isinstance(key, (str, int, float, bool)) and key is not None:
                return key
            found = _unsendable(inner, depth + 1)
            if found is not None:
                return found
        return None
    if isinstance(value, (list, tuple)):
        for inner in value:
            found = _unsendable(inner, depth + 1)
            if found is not None:
                return found
        return None
    return value


def _as_room(room) -> Room:
    """Accept either a Room subclass or an already-made instance."""
    if isinstance(room, Room):
        return room
    if isinstance(room, type) and issubclass(room, Room):
        return room()
    raise InvalidArgumentError(
        f'Network: room must be a Room subclass or instance; received {room!r}.'
    )


def _client_boundary(tree: 'ast.Module'):
    """
    Where the client half of a game script begins -- the index of the first
    top-level line that builds something only a player needs.

    Returns None for a file that has no client half at all (a module holding just
    a Room), which is the signal that it can be imported the ordinary way.
    """
    import ast

    for position, node in enumerate(tree.body):
        if isinstance(node, (ast.While, ast.For)):
            return position                 # the game loop, if we somehow got here
        for inner in ast.walk(node):
            if isinstance(inner, ast.Name) and inner.id in CLIENT_ONLY:
                return position
    return None


def _describe(node: 'ast.stmt', source_lines: list) -> str:
    """The source text of a statement's first line, for pointing at it."""
    return source_lines[node.lineno - 1].strip()


def _globals_read(code, seen=None):
    """
    Every module-level name a chunk of compiled code looks up, following the code
    nested inside it. Read off the bytecode rather than the source because that is
    what is *actually* referenced -- `math.hypot` reads `math`, not `hypot`.
    """
    import dis

    seen = seen if seen is not None else set()
    names = set()
    if code in seen:
        return names
    seen.add(code)

    for instruction in dis.get_instructions(code):
        if instruction.opname in ('LOAD_GLOBAL', 'STORE_GLOBAL', 'DELETE_GLOBAL'):
            names.add(instruction.argval)
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            names |= _globals_read(constant, seen)
    return names


def _top_level_lines(tree: 'ast.Module') -> dict:
    """{name: line number} for every name bound by a top-level statement."""
    import ast

    lines = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            lines.setdefault(node.name, node.lineno)
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.Name) and isinstance(inner.ctx, ast.Store):
                lines.setdefault(inner.id, inner.lineno)
            elif isinstance(inner, ast.alias):
                bound = inner.asname or inner.name.split('.')[0]
                lines.setdefault(bound, node.lineno)
    return lines


class _ClientHalfReached(Exception):
    """Raised by the stand-in Screen if a line we didn't spot tries to open one."""


def _window_opened(class_name: str, origin: str) -> PydrawError:
    return PydrawError(
        f'net: loading {class_name} from {origin} tried to open a game window. '
        f'Some line the loader could not see builds a Screen -- move the Room above '
        f'it, or give the Room a file of its own (arena.py) and serve that instead.'
    )


def _no_screen(*args, **kwargs):
    """Stands in for Screen while a Room is being loaded. A server has no window."""
    raise _ClientHalfReached()


@contextlib.contextmanager
def _server_side(origin: str):
    """
    Run a game file the way a server has to see it.

    Two things need standing in for. sys.argv, because a game reads it to find the
    host to join and would otherwise be handed *our* command line. And Screen, as a
    backstop: reading a file cannot catch every way to build a window (an aliased
    import, a `pydraw.Screen(...)`), and if one slips through this turns "a window
    opened on your headless server" into an error we can explain.
    """
    # Imported here, not at module scope: pydraw's __init__ imports this file, so
    # reaching back up to the package at import time would be circular.
    import pydraw as pydraw_package
    from pydraw import screen as screen_module

    real_argv, real_screen = sys.argv, screen_module.Screen
    sys.argv = [origin]
    screen_module.Screen = _no_screen
    if getattr(pydraw_package, 'Screen', None) is real_screen:
        pydraw_package.Screen = _no_screen
    try:
        yield
    finally:
        sys.argv = real_argv
        screen_module.Screen = real_screen
        if getattr(pydraw_package, 'Screen', None) is _no_screen:
            pydraw_package.Screen = real_screen


def _load_room(module_name: str, class_name: str):
    """
    Fetch a Room class out of a file *without running the rest of that file*.

    A pydraw game is one script: constants and the Room, then the client half --
    a Screen, sprites, a game loop that never returns. Importing it to reach the
    Room would run all of that, so `python -m pydraw.network game:Arena` would open
    a window and play the game instead of serving it.

    So we don't import. We parse the file and run it from the top in the ordinary
    way, stopping at the first line that builds a Screen or a Network. Everything
    above that line runs exactly as it would in a real game; everything from it
    down never runs at all.

    One rule falls out of that, and it is the whole rule: the Room has to be
    written above the line that makes your Screen.
    """
    import ast

    try:
        spec = importlib.util.find_spec(module_name)
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        raise PydrawError(f'net: no module named {module_name!r} -- '
                          f'is it in the directory you are running from?')

    origin = spec.origin
    if origin is None or not origin.endswith('.py'):
        # Not source we can read (a package, a compiled module), so unlikely to be
        # a game script: an ordinary import is the right move.
        return getattr(importlib.import_module(module_name), class_name)

    with open(origin, 'r') as source_file:
        source = source_file.read()
    tree = ast.parse(source, origin)
    source_lines = source.splitlines()

    boundary = _client_boundary(tree)
    if boundary is None:
        # A module that holds a Room and nothing else, so import it properly and
        # get real import semantics. Still guarded, because "no client half" is a
        # reading of the file.
        with _server_side(origin):
            try:
                return getattr(importlib.import_module(module_name), class_name)
            except _ClientHalfReached:
                raise _window_opened(class_name, origin) from None

    index = None
    for position, node in enumerate(tree.body):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            index = position
            break

    if index is None:
        raise PydrawError(
            f'net: {class_name!r} is not a class defined at the top level of '
            f'{origin}. A served Room has to be written as a plain `class '
            f'{class_name}(Room):` in that file -- not inside a function, not '
            f'inside an `if`, and not under `if __name__ == \'__main__\':`.'
        )

    client = tree.body[boundary]
    if index >= boundary:
        raise PydrawError(
            f'net: {class_name} is defined on line {tree.body[index].lineno}, but '
            f'the client half of {origin} starts on line {client.lineno}:\n\n'
            f'    {_describe(client, source_lines)}\n\n'
            f'A Room runs on a server -- no window, no sprites, no game loop -- so '
            f'the loader stops there and never reaches your class. Either move '
            f'`class {class_name}(Room):` above that line, or give the Room a file '
            f'of its own (arena.py) and serve that instead.'
        )

    namespace = {'__name__': module_name, '__file__': origin}
    prelude = compile(ast.Module(body=tree.body[:boundary], type_ignores=[]),
                      origin, 'exec')

    with _server_side(origin):
        try:
            exec(prelude, namespace)                       # noqa: S102
        except _ClientHalfReached:
            raise _window_opened(class_name, origin) from None

    room_class = namespace[class_name]
    _check_reachable(room_class, class_name, namespace, tree, origin, client)

    print(f'net: loaded {class_name} from {origin} -- ran the {boundary} lines above '
          f'your Screen on line {client.lineno}. Nothing below it ran, so no window '
          f'opened.', flush=True)
    return room_class


def _check_reachable(room_class, class_name, namespace, tree, origin, client) -> None:
    """
    Complain now, by name and line, about anything the Room needs that lives in
    the client half -- rather than letting it fail as a NameError mid-game.
    """
    lines = _top_level_lines(tree)
    wanted = set()
    for value in vars(room_class).values():
        method = getattr(value, '__func__', value)          # classmethod/staticmethod
        method = getattr(method, 'fget', method)             # property
        if hasattr(method, '__code__'):
            wanted |= _globals_read(method.__code__)

    missing = []
    for name in sorted(wanted):
        if name in namespace or hasattr(builtins, name):
            continue
        if name in lines:
            missing.append(f'`{name}`, defined on line {lines[name]} -- that is below '
                           f'your Screen on line {client.lineno}, so the server never '
                           f'ran it. Move it above that line.')
        else:
            missing.append(f'`{name}`, which nothing in {origin} defines.')

    if missing:
        problems = '\n  - '.join(missing)
        raise PydrawError(
            f'net: {class_name} uses things the server cannot reach:\n  - {problems}\n'
            f'Move them above your Screen line, or give the Room a file of its own '
            f'(arena.py) and serve that instead.'
        )


def _main(argv) -> None:
    """`python -m pydraw.network module:RoomClass [port]` -- run a standalone server."""
    if not argv:
        print('usage: python -m pydraw.network module:RoomClass [port]')
        return

    target = argv[0]
    port = int(argv[1]) if len(argv) > 1 else DEFAULT_PORT

    if ':' not in target:
        print("expected module:RoomClass, e.g. pong:Pong")
        return

    module_name, class_name = target.split(':', 1)
    try:
        room_class = _load_room(module_name, class_name)
    except (PydrawError, AttributeError, ModuleNotFoundError,
            OSError, SyntaxError) as error:
        print(f'{error}')
        return

    print(f'serving {class_name} on port {port} -- press Ctrl+C to stop', flush=True)
    serve(room_class, port)


if __name__ == '__main__':
    # `python -m pydraw.network` runs this file as __main__, and the game we are
    # about to serve imports it *again* under its real name -- two module objects,
    # two separate Room classes, and the game's Arena subclasses the other one. So
    # hand off to the canonical module, where _as_room checks against the Room the
    # game actually imported.
    import pydraw.network

    pydraw.network._main(sys.argv[1:])
