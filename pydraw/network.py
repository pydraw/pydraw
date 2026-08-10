"""Multiplayer state, events, and server Rooms for pydraw.

Clients write their own ``net.mine`` fields and read the rest. A Room owns shared
``state`` and each player's server-managed ``state``.
"""

from collections import deque
from collections.abc import Mapping
import errno
import json
import select
import socket
import sys
import threading
import time
import traceback
import zlib

from pydraw._network.loader import (
    CLIENT_ONLY, _ClientHalfReached, _check_reachable, _client_boundary,
    _describe, _globals_read, _load_room, _main, _no_screen, _server_side,
    _top_level_lines, _window_opened,
)
from pydraw._network.protocol import (
    COMPACT, COMPRESSION, FRAME_MESSAGES_KEY, FRAME_TIME_KEY, HEADER,
    MAX_BACKLOG, MAX_DECOMPRESSED_FRAME, MAX_FRAME, _Connection, _FramedMessage,
    _encode,
)
from pydraw._network.state import (
    _Changes, _readonly, _track, _TrackedDict, _TrackedList,
)
from pydraw.errors import InvalidArgumentError, PydrawError
from pydraw.serial import encode as _encode_values
from pydraw.serial import is_serializable
from pydraw.util import verify

__all__ = ['Network', 'Room', 'Player', 'action', 'event', 'serve']

DEFAULT_PORT = 5005
TICK_RATE = 30          # Room ticks per second
REPLICATION_RATE = 60   # replication frames per second
MAX_CATCHUP = 0.25      # largest dt passed to Room.tick()
OWN_RATE = 60           # client updates per second
MESSAGE_LIMIT = 600     # incoming messages per player per second
BYTE_LIMIT = 4 << 20    # incoming compressed bytes per player per second
HANDSHAKE_TIMEOUT = 5.0
HEARTBEAT_INTERVAL = 5.0
CONNECTION_TIMEOUT = 15.0
WINDOW = 32 << 10       # how far back zlib can refer; see _Server._body
VERIFY = 1.0            # seconds between full re-checks of the room's state, in
                        # case a change slipped past the tracking in _Tracked
RESYNC_COOLDOWN = 1.0   # least time between two snapshots for the same client
SMOOTH_SNAPSHOTS = 3    # render this many replication intervals behind the room
SMOOTH_HISTORY = 12     # enough room for jitter without unbounded pose retention
CLOCK_WINDOW = 15.0     # seconds per clock-offset sample window

# Wire prefixes distinguish owner and server player slices.
OWNER_PREFIX = 'player:'
SERVER_PREFIX = 'server:'

# Room methods unavailable to net.call().
RESERVED = {'start', 'stop', 'join', 'leave', 'tick', 'accept',
            'broadcast', 'state', 'players', 'player', 'clear_kept_events'}

# --------------------------------------------------------------------------- #
#  Client
# --------------------------------------------------------------------------- #

class Network:
    """A player's Screen-driven connection to a game."""

    def __init__(self, screen, host: str = 'localhost',
                 port: int = DEFAULT_PORT, room=None, rate: int = OWN_RATE,
                 precision: dict = None):
        verify(host, str, port, int)
        if rate is not None and (not isinstance(rate, (int, float)) or rate <= 0):
            raise InvalidArgumentError(
                f'Network: rate must be how many times a second to send your own '
                f'position, or None to send every frame; received {rate!r}.')
        if precision is not None and not isinstance(precision, Mapping):
            raise InvalidArgumentError(
                'Network: precision must map owned field names to non-negative '
                f'decimal places, or be None; received {precision!r}.'
            )
        precision = {} if precision is None else dict(precision)
        for field, places in precision.items():
            if (not isinstance(field, str)
                    or not isinstance(places, int)
                    or isinstance(places, bool)
                    or places < 0):
                raise InvalidArgumentError(
                    'Network: precision must map owned field names to '
                    'non-negative decimal places; '
                    f'received {field!r}: {places!r}.'
                )

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
        # Quantize only the wire copy; local state stays exact.
        self._precision = precision

        # Fields of *other* players to blend between updates -- see smooth().
        self._smooth = ()
        self._smooth_angles = ()
        self._history = {}      # id -> deque[(server time, complete owner slice)]
        self._blend = {}        # id -> the values this frame, computed in _pump
        self._pending_pose_samples = None
        self._rebasing = set()  # ids whose timeline restarts at their next pose
        self._server_clock_offset = None
        self._clock_window_min = None      # best sample in the window now filling
        self._clock_window_started = None
        # Pose cadence is limited by both client and replication rates.
        self._interpolation_delay = SMOOTH_SNAPSHOTS / (rate or OWN_RATE)

        # A sequence gap triggers a full resync.
        self._seq = None
        self._resyncing = False
        self._asked_at = None

        #: Every player's id, including your own.
        self.players = []

        #: Your own player number, assigned by the server.
        self.id = None

        # A local Room hosts only when this process wins the port.
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

        try:
            self._connect(host, port)
        except Exception:
            # Do not leak a hosted Room after a failed handshake.
            server, self._host_server = self._host_server, None
            if server is not None:
                server.stop()
            raise

        # Nested writes mark the owned slice dirty.
        self._mine_changes = _Changes(
            lambda: setattr(self, '_mine_dirty', True)
        )
        self._owner[self.id] = _track(
            self._owner.get(self.id, {}), self._mine_changes, None
        )
        #: Your entity: your own slice merged with your server-managed fields.
        #: Writing an owned field replicates instantly; writing a server field raises.
        self.mine = _Mine(self, self.id)

        # Pumped once per frame from inside screen.update(); see Screen.on_frame.
        screen.on_frame(self._pump)

    # -- what a game calls --------------------------------------------------

    def others(self):
        """Iterate over drawable ``(id, entity)`` pairs for other players."""
        for pid in self.players:
            if pid != self.id and (self._owner.get(pid) or self._server.get(pid)):
                yield pid, _Entity(self, pid)

    def call(self, action: str, **data) -> None:
        """
        Call an exposed Room action. Results arrive later through events or state;
        use ``net.mine`` for player-owned movement.
        """
        verify(action, str)
        self._send({'t': 'call', 'action': action, 'data': data})

    def send(self, name: str, keep: bool = False, **data) -> None:
        """
        Send an event to every other player. ``keep=True`` replays it to late
        joiners until the Room clears its kept events.
        """
        verify(name, str, keep, bool)
        self._send({'t': 'event', 'name': name, 'data': data, 'keep': keep})

    def smooth(self, *fields: str) -> None:
        """
        Interpolate numeric fields of other players between updates.

            net.smooth('x', 'y')

        Calls add fields; they do not replace earlier ones. Use ``smooth_angle``
        for headings, and do not smooth gameplay state such as health.
        """
        for field in fields:
            verify(field, str)
        self._set_smoothing(smooth=fields)

    def smooth_angle(self, *fields: str) -> None:
        """
        Interpolate degree fields along the shortest path.

            net.smooth_angle('a')

        Values are normalized to [0, 360). A field cannot use both smoothing
        modes.
        """
        for field in fields:
            verify(field, str)
        self._set_smoothing(angles=fields)

    def _set_smoothing(self, smooth=(), angles=()) -> None:
        smoothed = tuple(dict.fromkeys(self._smooth + tuple(smooth)))
        angled = tuple(dict.fromkeys(self._smooth_angles + tuple(angles)))

        both = set(smoothed) & set(angled)
        if both:
            raise InvalidArgumentError(
                f'Network: {", ".join(sorted(both))} cannot be smoothed both as a '
                f'number and as an angle -- a field is one or the other.')

        if (smoothed, angled) == (self._smooth, self._smooth_angles):
            return                          # nothing new; keep the timelines
        self._smooth, self._smooth_angles = smoothed, angled
        self.clear_smoothing()

    def clear_smoothing(self, player: int = None) -> None:
        """
        Reset interpolation after a remote player teleports.

            net.clear_smoothing(player_id)

        Omit ``player`` to reset every remote player.
        """
        if player is None:
            self._history.clear()
            self._blend = {}
            if self._pending_pose_samples is not None:
                self._pending_pose_samples.clear()
            self._rebasing.update(pid for pid in self.players if pid != self.id)
            return
        verify(player, int)
        self._forget(player)
        self._rebasing.add(player)

    def connected(self) -> bool:
        return self._conn is not None and self._conn.alive

    def close(self) -> None:
        """End this client and any Room it hosts. Safe to call more than once."""
        conn, self._conn = self._conn, None
        server, self._host_server = self._host_server, None
        if conn is not None:
            conn.close()
        if server is not None:
            server.stop()

    # -- internals ----------------------------------------------------------

    def _connect(self, host: str, port: int) -> None:
        try:
            conn = _Connection.connect(host, port)
        except OSError:
            raise PydrawError(
                f"Network: couldn't find a game at {host}:{port} -- "
                f"is the server running?"
            )

        try:
            # The server creates a Player only after `ready`.
            conn.timeout(HANDSHAKE_TIMEOUT)
            hello = conn.read_until(lambda m: m.get('t') == 'hello')

            serving = hello.get('room')
            if self._expected is not None and serving is not None \
                    and serving != self._expected:
                raise PydrawError(
                    f'Network: {host}:{port} is running {serving}, but this game is '
                    f'{self._expected}. Two different games cannot share a port -- '
                    f'give one of them its own, or point this at the right address.'
                )

            self.id = hello['id']
            self.players = list(hello.get('players', []))
            self._seq = hello.get('n')
            replication_rate = hello.get('replication_rate')
            if (isinstance(replication_rate, (int, float))
                    and not isinstance(replication_rate, bool)
                    and replication_rate > 0):
                cadence = min(replication_rate, self._rate or OWN_RATE)
                self._interpolation_delay = SMOOTH_SNAPSHOTS / cadence

            # Commit the handshake and trigger join().
            conn.send({'t': 'ready'})
            conn.read_until(lambda m: m.get('t') == 'connected')
            conn.nonblocking()
        except PydrawError:
            conn.close()
            raise
        except (OSError, ConnectionError, zlib.error, ValueError, KeyError) as error:
            conn.close()
            raise PydrawError(
                f'Network: {host}:{port} accepted a connection but did not '
                f'complete the hello ({error}).'
            ) from error

        self._conn = conn

    def _send(self, message: dict) -> None:
        if self._conn is None or not self._conn.alive:
            raise PydrawError('Network: not connected.')
        self._conn.send(message)

    def _pump(self) -> None:
        """Once per frame: send my latest slice, then apply what has arrived."""
        if self._conn is None:
            return

        # Send the latest complete owned slice at the configured rate.
        now = time.perf_counter()
        if self._mine_dirty and (self._rate is None or now >= self._next_own):
            slice_ = dict(self._owner[self.id])
            for key, places in self._precision.items():
                value = slice_.get(key)
                if isinstance(value, float):
                    slice_[key] = round(value, places)
            self._conn.send({'t': 'own', 'slice': slice_})
            self._mine_dirty = False
            if self._rate is not None:
                self._next_own = now + 1 / self._rate

        try:
            arrived = self._conn.poll()
        except (zlib.error, ValueError, ConnectionError) as error:
            # A corrupt compressed stream cannot be recovered.
            print(f'net: the connection stopped making sense ({error}); '
                  f'disconnected', flush=True)
            self._disconnect()
            return

        if not self._conn.alive:
            self._disconnect()
            return

        # Only the last pose per transport frame advances interpolation.
        smoothing = bool(self._smooth or self._smooth_angles)
        if smoothing:
            received_at = time.perf_counter()
            observed_frames = set()
            for message in arrived:
                frame_number = getattr(message, '_frame_number', None)
                frame_at = getattr(message, '_frame_time', None)
                if frame_number not in observed_frames:
                    self._observe_server_clock(frame_at, received_at)
                    observed_frames.add(frame_number)

            self._pending_pose_samples = {}
            for message in arrived:
                self._dispatch(message)
            self._commit_pose_samples()
            self._pending_pose_samples = None
            self._blend_others()
        else:
            for message in arrived:
                self._dispatch(message)

        if self._resyncing:
            self._ask_to_resync()     # still nothing back -- ask again when due

        if time.perf_counter() - self._conn.last_received_at > CONNECTION_TIMEOUT:
            print('net: the server stopped responding; disconnected', flush=True)
            self._disconnect()

    def _disconnect(self) -> None:
        """Forget and close the current transport once."""
        conn, self._conn = self._conn, None
        if conn is not None:
            conn.close()

    def _dispatch(self, message: dict) -> None:
        kind = message.get('t')
        frame_at = getattr(message, '_frame_time', None)
        frame_number = getattr(message, '_frame_number', None)

        # Apply the current message even when its sequence gap requests a resync.
        number = message.get('n')
        if number is not None:
            if self._seq is not None and number != self._seq + 1:
                self._ask_to_resync()
            self._seq = number

        if kind == 'ping':
            self._send({'t': 'pong'})
        elif kind == 'set':
            self._apply(message['key'], message['value'], frame_at, frame_number)
        elif kind == 'del':
            self._remove(message['key'])
        elif kind == 'snapshot':
            self._snapshot(message, frame_at, frame_number)
        elif kind == 'event':
            # Room events have no player id.
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

    def _observe_server_clock(self, sent_at, received_at) -> None:
        """Map the server's monotonic clock onto this process's clock."""
        if (not isinstance(sent_at, (int, float))
                or isinstance(sent_at, bool)):
            return
        candidate = received_at - sent_at

        # Windowed minima reject latency without ignoring clock drift forever.
        if self._clock_window_started is None:
            self._clock_window_started = received_at
        elif received_at - self._clock_window_started >= CLOCK_WINDOW:
            self._server_clock_offset = self._clock_window_min
            self._clock_window_min = None
            self._clock_window_started = received_at

        if (self._clock_window_min is None
                or candidate < self._clock_window_min):
            self._clock_window_min = candidate
        if (self._server_clock_offset is None
                or candidate < self._server_clock_offset):
            self._server_clock_offset = candidate

    def _stage_pose(self, pid: int, slice_: dict, sample_at, frame_number) -> None:
        if self._pending_pose_samples is None:
            self._remember(pid, slice_, sample_at)
            return
        # Group poses by their private transport-frame number.
        group = frame_number if frame_number is not None else 'this-pump'
        self._pending_pose_samples[(group, pid)] = (pid, slice_, sample_at)

    def _commit_pose_samples(self) -> None:
        for pid, slice_, sample_at in self._pending_pose_samples.values():
            self._remember(pid, slice_, sample_at)

    def _remember(self, pid: int, slice_: dict, sample_at=None) -> None:
        """Append one complete owner slice to a player's snapshot timeline."""
        if sample_at is None:
            return

        if pid in self._rebasing:
            # Seed teleports at the render cursor so motion resumes immediately.
            self._rebasing.discard(pid)
            at = sample_at if self._server_clock_offset is None else self._render_at()
            self._history[pid] = deque([(at, slice_)], maxlen=SMOOTH_HISTORY)
            return

        history = self._history.setdefault(pid, deque(maxlen=SMOOTH_HISTORY))
        if history and sample_at <= history[-1][0]:
            if sample_at == history[-1][0]:
                history[-1] = (sample_at, slice_)
            # Never rewind a timeline with a stale timestamp.
            return
        history.append((sample_at, slice_))

    def _blend_others(self) -> None:
        """
        Interpolate remote players on one delayed timeline for this frame.
        """
        render_at = self._render_at()
        self._blend = {}

        fields = tuple(dict.fromkeys(self._smooth + self._smooth_angles))
        angle_fields = set(self._smooth_angles)
        for pid, history in self._history.items():
            if not history:
                continue

            # Retain one sample before the render cursor.
            while len(history) > 2 and history[1][0] <= render_at:
                history.popleft()

            older_at, older = history[0]
            newer_at, newer = history[-1]
            if render_at <= older_at or len(history) == 1:
                newer_at, newer = older_at, older
                share = 0.0
            elif render_at >= newer_at:
                older_at, older = newer_at, newer
                share = 1.0
            else:
                for index in range(1, len(history)):
                    candidate_at, candidate = history[index]
                    if render_at <= candidate_at:
                        older_at, older = history[index - 1]
                        newer_at, newer = candidate_at, candidate
                        break
                span = newer_at - older_at
                share = ((render_at - older_at) / span) if span > 0 else 1.0

            blended = {}
            for field in fields:
                start, end = older.get(field), newer.get(field)
                if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                    if field in angle_fields:
                        delta = (end - start + 180) % 360 - 180
                        blended[field] = (start + delta * share) % 360
                    else:
                        blended[field] = start + (end - start) * share
                elif end is not None:
                    blended[field] = end          # nothing sensible to blend
            self._blend[pid] = blended

    def _render_at(self) -> float:
        """The moment on the server's timeline that this frame draws."""
        now = time.perf_counter()
        server_now = (
            now if self._server_clock_offset is None
            else now - self._server_clock_offset
        )
        return server_now - self._interpolation_delay

    def _forget(self, pid: int) -> None:
        self._rebasing.discard(pid)     # they have gone, not teleported
        self._history.pop(pid, None)
        self._blend.pop(pid, None)
        if self._pending_pose_samples is not None:
            for key, sample in tuple(self._pending_pose_samples.items()):
                if sample[0] == pid:
                    self._pending_pose_samples.pop(key)

    def _ask_to_resync(self) -> None:
        """Request a rate-limited full snapshot until one arrives."""
        now = time.perf_counter()
        if self._conn is None:
            return
        if self._asked_at is not None and now < self._asked_at + RESYNC_COOLDOWN:
            return
        self._asked_at = now
        self._resyncing = True
        self._send({'t': 'resync'})

    def _snapshot(self, message: dict, frame_at=None, frame_number=None) -> None:
        """
        Replace local replicated state with a full server snapshot.

        Keep the locally authored owner slice.
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
            self._apply(key, value, frame_at, frame_number)

        self._resyncing = False

    def _apply(self, key: str, value, frame_at=None, frame_number=None) -> None:
        if key.startswith(OWNER_PREFIX):
            pid = int(key[len(OWNER_PREFIX):])
            # Never overwrite the locally authored owner slice.
            if pid != self.id:
                value = _readonly(value, _Entity._REFUSAL)
                if self._smooth or self._smooth_angles:
                    self._stage_pose(pid, value, frame_at, frame_number)
                self._owner[pid] = value
        elif key.startswith(SERVER_PREFIX):
            self._server[int(key[len(SERVER_PREFIX):])] = \
                _readonly(value, _Entity._REFUSAL)
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
    """The client's read-only view of neutral world state."""

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
        # Freeze nested values too.
        dict.__setitem__(self, key, _readonly(value, self._REFUSAL))

    def _remove(self, key):
        dict.pop(self, key, None)


class _Entity:
    """A read-only merged view of one player's state."""

    _REFUSAL = "this player's state is read-only -- only its owner can move it."

    def __init__(self, net: Network, pid: int):
        self._net = net
        self._pid = pid

    def _sources(self):
        """Return player sources in precedence order."""
        return (self._net._server.get(self._pid) or {},
                self._net._blend.get(self._pid) or {},
                self._net._owner.get(self._pid) or {})

    def _merged(self) -> dict:
        """Every field at once, for the reads that want the whole player."""
        server, blend, owner = self._sources()
        merged = {**owner, **server}
        for field, value in blend.items():
            if field not in server:
                merged[field] = value
        return merged

    def __getitem__(self, key):
        for source in self._sources():
            if key in source:
                return source[key]
        raise KeyError(key)

    def get(self, key, default=None):
        for source in self._sources():
            if key in source:
                return source[key]
        return default

    def __contains__(self, key):
        return any(key in source for source in self._sources())

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
        raise PydrawError(self._REFUSAL)

    def __delitem__(self, key):
        raise PydrawError(self._REFUSAL)

    def __repr__(self):
        return f'<entity {self._pid} {self._merged()}>'


class _Mine(_Entity):
    """Your own entity: owned fields are writable, server-managed fields are not."""

    def _owned(self):
        return self._net._owner.setdefault(self._pid, {})

    def _server_managed(self, key):
        if key in self._net._server.get(self._pid, {}):
            raise PydrawError(
                f"net.mine[{key!r}] is managed by the server -- you can't change it."
            )

    def __setitem__(self, key, value):
        self._server_managed(key)
        # Applied locally at once (no lag); _pump sends the slice this frame.
        owned = self._owned()
        owned[key] = value
        # Fallback for test doubles without tracked state.
        if not isinstance(owned, _TrackedDict):
            self._net._mine_dirty = True

    def __delitem__(self, key):
        self._server_managed(key)
        owned = self._owned()
        del owned[key]
        if not isinstance(owned, _TrackedDict):
            self._net._mine_dirty = True

    def update(self, *args, **kwargs):
        incoming = dict(*args, **kwargs)
        for key in incoming:
            self._server_managed(key)       # refuse before making a partial update
        for key, value in incoming.items():
            self[key] = value

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return self[key]

    def pop(self, key, *default):
        if len(default) > 1:
            raise TypeError(f'pop expected at most 2 arguments, got {len(default) + 1}')
        self._server_managed(key)
        owned = self._owned()
        if key not in owned:
            if default:
                return default[0]
            raise KeyError(key)
        value = owned[key]
        del self[key]
        return value

    def popitem(self):
        owned = self._owned()
        if not owned:
            if self._net._server.get(self._pid):
                raise PydrawError(
                    "net.mine only has server-managed fields, which you can't remove."
                )
            raise KeyError('popitem(): dictionary is empty')
        key = next(reversed(tuple(owned)))
        return key, self.pop(key)

    def clear(self):
        owned = self._owned()
        if isinstance(owned, _TrackedDict):
            owned.clear()
        else:
            owned.clear()
            self._net._mine_dirty = True

    def __ior__(self, other):
        self.update(other)
        return self


# --------------------------------------------------------------------------- #
#  Server side -- Room and Player
# --------------------------------------------------------------------------- #

def action(method):
    """Expose a Room method through ``net.call``."""
    if not callable(method):
        raise InvalidArgumentError(
            f'Room: @action must decorate a method; received {method!r}.'
        )
    method._pydraw_action = True
    return method


def event(name: str):
    """
    Register a Room method to review one ``net.send`` event.

    Return ``None`` to relay it, a dict to replace its data, or ``False`` to drop
    it.
    """
    verify(name, str)

    def mark(method):
        method._pydraw_event = name
        return method

    return mark


class Room:
    """
    Server authority for a game.

    Override lifecycle hooks and actions here. ``self.state`` and
    ``player.state`` are server-owned and read-only on clients.
    """

    #: Calls to tick() per second.
    tick_rate = TICK_RATE

    #: Replication frames per second.
    replication_rate = REPLICATION_RATE

    #: Incoming messages allowed per player per second.
    message_limit = MESSAGE_LIMIT

    #: Incoming compressed bytes allowed per player per second.
    byte_limit = BYTE_LIMIT

    def __init__(self):
        self._changes = _Changes()
        self._state = _TrackedDict(self._changes, None)
        self.players = []
        self._server = None

    @property
    def state(self) -> dict:
        """Writable neutral world state, exposed to clients as ``net.state``."""
        return self._state

    @state.setter
    def state(self, value: dict) -> None:
        # Preserve tracking and publish removed keys.
        verify(value, dict)
        gone = set(self._state)
        self._state = _TrackedDict(self._changes, None)
        self._state.update(value)
        self._changes.keys |= gone

    def __init_subclass__(cls, **kwargs):
        """Collect decorated actions and event reviewers."""
        super().__init_subclass__(**kwargs)

        actions = dict(getattr(cls, '_actions', {}))
        for name, attribute in vars(cls).items():
            # Overrides must opt in again.
            actions.pop(name, None)
            if not getattr(attribute, '_pydraw_action', False):
                continue
            if name in RESERVED or name.startswith('_'):
                raise InvalidArgumentError(
                    f'Room: {name!r} is reserved by pydraw.network and cannot be '
                    f'an @action.'
                )
            actions[name] = attribute
        cls._actions = actions

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
    #: action name -> exposed method, filled in by __init_subclass__
    _actions = {}

    # override these
    def start(self) -> None:
        """Called once when the room opens. Seed self.state."""

    def stop(self) -> None:
        """Called after every Player leaves when the room closes."""

    def join(self, player) -> None:
        """Called when a player connects. Give them player.state fields."""

    def leave(self, player) -> None:
        """Called when a player disconnects. Prune any world data you keyed by id."""

    def tick(self, dt: float) -> None:
        """Advance the room by elapsed time ``dt`` at ``tick_rate``."""

    def accept(self, player, proposed: dict, current: dict) -> dict:
        """Return the accepted version of a player's proposed owner slice."""
        return proposed

    # call these
    def player(self, player_id: int):
        """The Player for an id (or None)."""
        return self._server._players.get(player_id)

    def broadcast(self, name: str, **data) -> None:
        """Send a transient event to every connected player."""
        verify(name, str)
        self._server._broadcast({'t': 'event', 'name': name, 'data': data})

    def clear_kept_events(self) -> int:
        """Discard kept events and return how many were removed."""
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
        """This player's writable, server-managed fields."""
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
        """The player's last accepted, read-only owner slice."""
        return self._server._owner.get(self.id, {})

    def send(self, name: str, **data) -> None:
        """Send a transient event to this player if still connected."""
        verify(name, str)
        if self._conn is not None and self._conn.alive:
            self._server._send_to(self._conn,
                                  {'t': 'event', 'name': name, 'data': data})

    def resync(self) -> None:
        """Send this player a full snapshot."""
        if self._conn is not None and self._conn.alive:
            self._server._resync(self._conn, forced=True)

    def __repr__(self):
        return f'Player({self.id})'


def serve(room, port: int = DEFAULT_PORT) -> None:
    """Run a Room until interrupted."""
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
        # Canonical JSON shadows avoid deep copies and false ordering changes.
        self._world_shadow = {}   # world key -> JSON of the value last sent
        self._server_shadow = {}  # id -> JSON of the server slice last sent
        self._replay = []         # kept events, resent to late joiners
        self._reported = set()    # Room failures already printed, so we say each once
        self._running = False
        self._stop_requested = threading.Event()
        self._room_started = False
        self._room_stopped = False
        self._finished = False
        self._startup_error = None
        self._last_tick = 0.0
        self._next_tick = 0.0
        self._next_verify = 0.0
        tick_rate = _rate('tick_rate', getattr(room, 'tick_rate', TICK_RATE))
        replication_rate = _rate(
            'replication_rate', getattr(room, 'replication_rate', REPLICATION_RATE))
        self._message_limit = _rate(
            'message_limit', getattr(room, 'message_limit', MESSAGE_LIMIT))
        self._byte_limit = _byte_limit(
            'byte_limit', getattr(room, 'byte_limit', BYTE_LIMIT))
        self._tick_interval = 1 / tick_rate
        self._replication_interval = 1 / replication_rate
        self._replication_rate = replication_rate
        self._next_replication = 0.0

    # -- lifecycle ----------------------------------------------------------

    def listen(self) -> None:
        """Claim the port, raising ``EADDRINUSE`` if it is taken."""
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
        # Bind synchronously so the caller can handle a port race.
        self.listen()

        ready = threading.Event()
        self._startup_error = None

        def run():
            try:
                self.serve_forever(ready)
            except BaseException as error:                       # noqa: BLE001
                self._startup_error = error
                ready.set()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        if not ready.wait(timeout=5):
            self.stop(wait=0)
            raise PydrawError('Network: the hosted server failed to start.')
        if self._startup_error is not None:
            self._thread.join(timeout=1)
            raise PydrawError(
                f'Network: the hosted Room failed to start '
                f'({self._startup_error}).'
            ) from self._startup_error

    def stop(self, wait: float = 1.0) -> None:
        """Ask the serve thread to stop and release its sockets."""
        self._stop_requested.set()
        self._running = False
        thread = getattr(self, '_thread', None)
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=wait)

    def serve_forever(self, ready: 'threading.Event' = None) -> None:
        try:
            if self._listener is None:
                self.listen()

            self._room._bind(self)
            self._room_started = True
            self._room.start()
            # Treat start() state as the initial published state.
            self._world_shadow = {key: _canonical(value)
                                  for key, value in self._room.state.items()}
            self._room._changes.take()

            self._running = not self._stop_requested.is_set()
            started = time.perf_counter()
            self._last_tick = started
            self._next_tick = started + self._tick_interval
            self._next_verify = started + VERIFY
            self._next_replication = started + self._replication_interval
            if ready is not None:
                ready.set()

            while self._running and not self._stop_requested.is_set():
                now = time.perf_counter()
                timeout = max(0.0, min(self._next_tick,
                                       self._next_replication) - now)
                readable, _, _ = select.select(
                    [self._listener] + list(self._conns), [], [], timeout)

                for sock in readable:
                    if sock is self._listener:
                        self._accept()
                    elif sock in self._conns:
                        self._receive(sock)

                now = time.perf_counter()
                if now >= self._next_tick:
                    # Skip catch-up bursts after an overrun.
                    self._guarded('tick()', self._room.tick,
                                  min(now - self._last_tick, MAX_CATCHUP))
                    self._last_tick = now
                    self._next_tick = now + self._tick_interval

                self._sync()
                self._maintain_connections(now)
                self._flush_all()
        finally:
            self._finish()

    def _finish(self) -> None:
        """Run the server's final lifecycle exactly once, on its serve thread."""
        if self._finished:
            return
        self._finished = True
        self._running = False

        # Pending handshakes have no Player lifecycle.
        for sock in list(self._conns):
            self._drop(sock, announce=False)

        if self._room_started and not self._room_stopped:
            self._room_stopped = True
            self._guarded('stop()', self._room.stop)

        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass

    # -- connections --------------------------------------------------------

    def _accept(self) -> None:
        sock, _ = self._listener.accept()
        conn = _Connection(sock)
        conn.nonblocking()      # a slow client must never stall the serve loop
        conn.established = False
        conn.handshake_deadline = time.perf_counter() + HANDSHAKE_TIMEOUT
        player_id = self._next_id
        self._next_id += 1

        self._conns[sock] = conn
        self._ids[sock] = player_id

        # Reserve the id; `ready` creates the Player.
        players = list(self._players)
        players.append(player_id)
        self._send_to(conn, {'t': 'hello', 'id': player_id,
                             'players': players,
                             'room': type(self._room).__name__,
                             'replication_rate': self._replication_rate})
        conn.send_queued(sent_at=time.perf_counter())

    def _establish(self, sock) -> None:
        """Commit a completed hello and begin exactly one Player lifecycle."""
        conn = self._conns.get(sock)
        if conn is None or conn.established:
            return

        conn.established = True
        conn.handshake_deadline = None
        conn.next_ping_at = time.perf_counter() + HEARTBEAT_INTERVAL
        player_id = self._ids[sock]
        player = Player(player_id, conn, self)
        self._players[player_id] = player
        self._owner[player_id] = _readonly(
            {}, 'player.slice is read-only -- the connected player owns it.'
        )
        self._room.players.append(player)

        # join() completes before snapshots and announcements.
        self._guarded('join()', self._room.join, player)
        self._resync(conn, forced=True)
        for event in self._replay:
            self._send_to(conn, event)
        self._send_to(conn, {'t': 'connected'})

        # The client blocks until this handshake batch arrives.
        conn.send_queued(sent_at=time.perf_counter())

        self._broadcast({'t': 'join', 'id': player_id}, skip=sock)

    def _receive(self, sock) -> None:
        conn = self._conns[sock]
        now = time.perf_counter()
        if now - conn.counted_at >= 1.0:
            conn.counted_at = now
            conn.messages = 0
            conn.bytes_received = 0
        remaining = max(0, self._byte_limit - conn.bytes_received)
        try:
            messages = conn.poll(max_bytes=remaining)
            conn.bytes_received += conn.last_received
        except OSError:
            messages = None
        except (zlib.error, ValueError) as error:
            # Compressed streams cannot recover from corruption.
            self._complain(f'player {self._ids.get(sock)} sent something we could '
                           f'not read ({error}); dropping them')
            messages = None

        if messages is None or not conn.alive:
            self._drop(sock)
            return

        if conn.byte_limit_exceeded:
            self._complain(
                f'player {self._ids.get(sock)} sent more than '
                f'{self._byte_limit} compressed bytes in a second, so they were '
                f'dropped -- a game that really needs that much incoming traffic '
                f'can raise Room.byte_limit')
            self._drop(sock)
            return

        if self._flooding(conn, len(messages)):
            self._complain(
                f'player {self._ids.get(sock)} sent more than '
                f'{self._message_limit} messages in a second, so they were '
                f'dropped -- a game that really needs that many can raise '
                f'Room.message_limit')
            self._drop(sock)
            return

        for message in messages:
            # Isolate malformed messages to their sender.
            if sock not in self._conns:
                break
            self._guarded(f"a {message.get('t')!r} message from player "
                          f'{self._ids.get(sock)}', self._handle, sock, message)

    def _flooding(self, conn, arrived: int) -> bool:
        """Return whether this player exceeded its message rate."""
        conn.messages += arrived
        return conn.messages > self._message_limit

    def _maintain_connections(self, now: float) -> None:
        """Expire unfinished hellos and peers that no longer read the stream."""
        for sock, conn in list(self._conns.items()):
            if not conn.established:
                if now >= conn.handshake_deadline:
                    self._complain(
                        f'connection {self._ids.get(sock)} did not finish its '
                        f'hello in {HANDSHAKE_TIMEOUT:g} seconds; dropping it')
                    self._drop(sock)
                continue

            if (conn.awaiting_pong_at is not None
                    and now - conn.awaiting_pong_at >= CONNECTION_TIMEOUT):
                self._complain(
                    f'player {self._ids.get(sock)} stopped reading network data; '
                    f'dropping them')
                self._drop(sock)
                continue

            if conn.awaiting_pong_at is None and now >= conn.next_ping_at:
                self._send_to(conn, {'t': 'ping'})
                conn.awaiting_pong_at = now

    def _drop(self, sock, announce: bool = True) -> None:
        """Remove one pending socket or active Player. Repeated calls do nothing."""
        player_id = self._ids.pop(sock, None)
        conn = self._conns.pop(sock, None)
        player = self._players.pop(player_id, None)
        self._owner.pop(player_id, None)
        self._server_shadow.pop(player_id, None)
        if player is not None and player in self._room.players:
            self._room.players.remove(player)
        if player is not None:
            player._conn = None
        if conn is not None:
            conn.close()
        else:
            try:
                sock.close()
            except OSError:
                pass

        if player is not None:
            self._guarded('leave()', self._room.leave, player)
            if announce:
                # leave() finishes before other clients hear playerquit.
                self._broadcast({'t': 'del', 'key': f'{OWNER_PREFIX}{player_id}'})
                self._broadcast({'t': 'del', 'key': f'{SERVER_PREFIX}{player_id}'})
                self._broadcast({'t': 'leave', 'id': player_id})

    # -- message handling ---------------------------------------------------

    def _handle(self, sock, message: dict) -> None:
        kind = message.get('t')
        conn = self._conns.get(sock)
        if conn is None:
            return
        if not conn.established:
            if kind == 'ready':
                self._establish(sock)
            else:
                self._complain(
                    f'connection {self._ids.get(sock)} sent {kind!r} before it '
                    f'finished its hello; dropping it')
                self._drop(sock)
            return

        if kind == 'pong':
            conn.awaiting_pong_at = None
            conn.next_ping_at = time.perf_counter() + HEARTBEAT_INTERVAL
            return

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
            self._resync(conn)

    def _resync(self, conn, forced: bool = False) -> None:
        """Send one player a rate-limited full snapshot."""
        now = time.perf_counter()
        if not forced and now < conn.resync_at:
            return
        conn.resync_at = now + RESYNC_COOLDOWN
        self._send_to(conn, {'t': 'snapshot', 'state': self._compose(),
                             'players': list(self._players)})

    def _relay_event(self, sock, player: Player, message: dict) -> None:
        """Review and relay a client's event."""
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

        # Validate client-owned data before the Room sees it.
        if not isinstance(proposed, dict):
            self._complain(
                f'player {player.id} sent {type(proposed).__name__} where its own '
                f'slice should be, so that write was ignored')
            return

        # A broken accept() falls back to the default policy.
        try:
            accepted = self._room.accept(player, proposed, current)
        except Exception:                                    # noqa: BLE001
            self._report('accept()')
            accepted = proposed

        if not isinstance(accepted, dict):
            # Do not replace a player's slice with a bad return value.
            self._complain(
                f'accept() returned {type(accepted).__name__} rather than a slice, '
                f'so the write was let through -- return `proposed` to trust it or '
                f'`current` to turn it down')
            accepted = proposed

        accepted = _readonly(
            accepted,
            'player.slice is read-only -- the connected player owns it.',
        )
        self._owner[player.id] = accepted
        # The owner already applied this slice locally.
        self._broadcast({'t': 'set', 'key': f'{OWNER_PREFIX}{player.id}',
                         'value': accepted}, skip=sock)

    def _guarded(self, what: str, function, *args, **kwargs):
        """Run one callback without taking down the serve loop."""
        try:
            return function(*args, **kwargs)
        except Exception:                                    # noqa: BLE001
            self._report(what)
            return None

    def _report(self, what: str) -> None:
        """Print each Room failure once."""
        report = traceback.format_exc()
        signature = (what, report)
        if signature in self._reported:
            return

        self._reported.add(signature)
        print(f'net: {what} raised, and the room kept going --\n{report}'
              f'net: (further identical failures in {what} will not be reported)',
              flush=True)

    def _complain(self, message: str, about=None) -> None:
        """Print a warning once, optionally deduplicated by ``about``."""
        signature = message if about is None else about
        if signature in self._reported:
            return
        self._reported.add(signature)
        print(f'net: {message}', flush=True)

    def _run_action(self, sock, player: Player, action, data: dict) -> None:
        if not isinstance(action, str) or action in RESERVED or action.startswith('_'):
            print(f'net: ignoring reserved/invalid action {action!r}', flush=True)
            return

        exposed = self._room._actions.get(action)
        if exposed is None:
            # Avoid executing descriptors while diagnosing a hidden method.
            hidden = next(
                (base.__dict__[action] for base in type(self._room).__mro__
                 if action in base.__dict__),
                None,
            )
            if callable(hidden):
                print(f'net: {action!r} is a Room method but not an action; add '
                      f'@action above {action}() to expose it to net.call',
                      flush=True)
                return
            print(f'net: no such action {action!r} on {type(self._room).__name__}',
                  flush=True)
            return
        method = getattr(self._room, action)

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

        # Broadcast the Room's outcome, not the client's request.
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
        Publish tracked changes, periodically checking all replicated state.
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
            # Name the first unsendable nested value in the warning.
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
        coalesce_key = self._coalesce_key(message)
        for sock, conn in list(self._conns.items()):
            if sock is not skip and conn.established:
                conn.queue_body(body, coalesce_key)

    def _send_to(self, conn, message: dict) -> None:
        body = self._body(message)
        if body is not None:
            conn.queue_body(body, self._coalesce_key(message))

    @staticmethod
    def _coalesce_key(message: dict):
        """Identify state writes that can replace one another inside a batch."""
        if message.get('t') not in ('set', 'del'):
            return None
        key = message.get('key')
        try:
            hash(key)
        except TypeError:
            return None
        return 'state', key

    def _body(self, message: dict):
        """Encode a message, or say so once and drop it if it cannot be encoded."""
        try:
            raw = _encode(message)
        except (TypeError, ValueError):
            # Drop one bad message without ending the room.
            self._complain(f"a {message.get('t')!r} message could not be sent -- "
                           f"it holds something that is not a number, string, "
                           f"list or dict")
            return None

        # Warn when a value is too large for zlib's history window.
        if len(raw) > WINDOW and message.get('t') == 'set':
            self._complain(
                f"net.state[{message.get('key')!r}] is {len(raw) // 1024} KB, past "
                f"the {WINDOW // 1024} KB the compressor can look back through, so "
                f"every update sends all of it. Send the players less of it -- only "
                f"what is near them, or a seed they can build it from themselves.",
                about=('oversized', message.get('key')))
        return raw

    def _flush_all(self, force_batch: bool = False) -> None:
        """Push out buffered bytes, and drop anyone who has gone or fallen behind."""
        now = time.perf_counter()
        if force_batch or now >= self._next_replication:
            for conn in self._conns.values():
                conn.send_queued(sent_at=now)
            self._next_replication = now + self._replication_interval

        for sock, conn in list(self._conns.items()):
            conn.flush()
            if not conn.alive:
                self._drop(sock)


# --------------------------------------------------------------------------- #
#  Helpers / standalone entry point
# --------------------------------------------------------------------------- #

def _canonical(value) -> str:
    """Return canonical wire JSON, or ``None`` for an unsendable value."""
    try:
        return json.dumps(value, sort_keys=True, default=_encode_values)
    except (TypeError, ValueError):
        return None


def _unsendable(value, depth: int = 0):
    """Return the first value JSON cannot carry, if identifiable."""
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


def _rate(name: str, value):
    """Validate a positive Room rate."""
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or value <= 0):
        raise InvalidArgumentError(
            f'Room.{name} must be a positive number of times a second; '
            f'received {value!r}.'
        )
    return value


def _byte_limit(name: str, value):
    """Validate a positive whole-byte limit."""
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InvalidArgumentError(
            f'Room.{name} must be a positive whole number of bytes a second; '
            f'received {value!r}.'
        )
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


if __name__ == '__main__':
    # Use the canonical module so loaded games share its Room class.
    import pydraw.network

    pydraw.network._main(sys.argv[1:])
