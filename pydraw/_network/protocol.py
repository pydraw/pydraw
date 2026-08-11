"""Socket framing and compression for pydraw.network."""

import json
import select
import socket
import time
import zlib

from pydraw.serial import decode as _decode_values, encode as _encode_values


# Frame: [sequence: 4][size: 4][compressed body].
HEADER = 8
MAX_FRAME = 64 << 20
MAX_DECOMPRESSED_FRAME = 64 << 20
COMPACT = (',', ':')
COMPRESSION = 1
MAX_BACKLOG = 4 << 20

# Private timestamp envelope for interpolation.
FRAME_TIME_KEY = '~pydraw-frame-time'
FRAME_MESSAGES_KEY = '~pydraw-frame-messages'


def _encode(message: dict) -> bytes:
    """Serialize a message once for any number of peers."""
    return json.dumps(message, separators=COMPACT,
                      default=_encode_values).encode()


class _FramedMessage(dict):
    """A normal message carrying private metadata from its transport frame."""

    def __init__(self, message, frame_number, frame_time):
        super().__init__(message)
        self._frame_number = frame_number
        self._frame_time = frame_time


class _Connection:
    """Turn one TCP byte stream into complete compressed JSON messages."""

    def __init__(self, sock):
        self._sock = sock
        self._buffer = b''
        self._outgoing = b''
        self._pending = []
        self._queued_bodies = []
        self._queued_keys = {}
        self.alive = True
        self.seq = 0
        self.resync_at = 0.0
        self.messages = 0
        self.bytes_received = 0
        self.counted_at = 0.0
        self.last_received = 0
        self.byte_limit_exceeded = False
        self.last_received_at = time.perf_counter()

        # Server handshake and heartbeat state.
        self.established = True
        self.handshake_deadline = None
        self.next_ping_at = 0.0
        self.awaiting_pong_at = None

        # Compression history is connection-specific and ordered.
        self._deflate = zlib.compressobj(COMPRESSION)
        self._inflate = zlib.decompressobj()

    @classmethod
    def connect(cls, host: str, port: int) -> '_Connection':
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((host, port))
        except OSError:
            sock.close()
            raise
        return cls(sock)

    def nonblocking(self) -> None:
        self._sock.setblocking(False)

    def timeout(self, seconds) -> None:
        """Set a temporary blocking-socket timeout, chiefly for the hello."""
        self._sock.settimeout(seconds)

    def send(self, message: dict) -> None:
        """Serialize and queue a message without blocking on a full socket."""
        self.send_body(_encode(message))

    def send_body(self, raw: bytes, sent_at=None) -> None:
        """Queue JSON already serialized for this peer's compressed stream."""
        if not self.alive:
            return
        if sent_at is not None:
            raw = (
                b'{' + json.dumps(FRAME_TIME_KEY).encode() + b':'
                + json.dumps(float(sent_at), separators=COMPACT).encode() + b','
                + json.dumps(FRAME_MESSAGES_KEY).encode() + b':' + raw + b'}'
            )

        self.seq += 1
        body = self._deflate.compress(raw) + self._deflate.flush(zlib.Z_SYNC_FLUSH)
        self._outgoing += (self.seq.to_bytes(4, 'big')
                           + len(body).to_bytes(4, 'big') + body)
        self.flush()

    def queue_body(self, raw: bytes, coalesce_key=None) -> None:
        """Queue one encoded message for the next server replication frame."""
        if not self.alive:
            return
        if coalesce_key is None:
            self._queued_bodies.append(raw)
            # Non-state messages are coalescing barriers.
            self._queued_keys.clear()
            return

        index = self._queued_keys.get(coalesce_key)
        if index is None:
            self._queued_keys[coalesce_key] = len(self._queued_bodies)
            self._queued_bodies.append(raw)
        else:
            self._queued_bodies[index] = raw

    def send_queued(self, sent_at=None) -> None:
        """Compress all queued messages into one length-prefixed frame."""
        if not self._queued_bodies:
            return
        bodies, self._queued_bodies = self._queued_bodies, []
        self._queued_keys.clear()
        raw = bodies[0] if len(bodies) == 1 else b'[' + b','.join(bodies) + b']'
        self.send_body(raw, sent_at=sent_at)

    def flush(self) -> None:
        """Drain what the socket accepts now and retain the rest for later."""
        while self._outgoing:
            try:
                sent = self._sock.send(self._outgoing)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                self.alive = False
                return
            if not sent:
                break
            self._outgoing = self._outgoing[sent:]

        if len(self._outgoing) > MAX_BACKLOG:
            self.alive = False

    def poll(self, max_bytes=None) -> list:
        """
        Return complete messages without blocking.

        Read at most one byte past ``max_bytes`` to detect a limit violation.
        """
        self.flush()
        self.last_received = 0
        self.byte_limit_exceeded = False

        while True:
            readable, _, _ = select.select([self._sock], [], [], 0)
            if not readable:
                break
            amount = 4096
            if max_bytes is not None:
                amount = min(amount, max(1, max_bytes - self.last_received + 1))
            data = self._sock.recv(amount)
            if not data:
                self.alive = False
                break
            self.last_received_at = time.perf_counter()
            self.last_received += len(data)
            if max_bytes is not None and self.last_received > max_bytes:
                self.byte_limit_exceeded = True
                break
            self._buffer += data
            self._collect()

        messages, self._pending = self._pending, []
        return messages

    def read_until(self, matches) -> dict:
        """Block until a message satisfying `matches` arrives, and return it."""
        while True:
            for index, message in enumerate(self._pending):
                if matches(message):
                    return self._pending.pop(index)
            data = self._sock.recv(4096)
            if not data:
                raise ConnectionError('the server closed the connection')
            self.last_received_at = time.perf_counter()
            self._buffer += data
            self._collect()

    def close(self) -> None:
        """Close once. Repeated cleanup calls are harmless."""
        if not self.alive and self._sock.fileno() < 0:
            return
        self.alive = False
        self._outgoing = b''
        self._pending.clear()
        self._queued_bodies.clear()
        self._queued_keys.clear()
        try:
            self._sock.close()
        except OSError:
            pass

    def _collect(self) -> None:
        """Take every whole frame out of the buffer, leaving any partial one."""
        while len(self._buffer) >= HEADER:
            size = int.from_bytes(self._buffer[4:8], 'big')

            if size > MAX_FRAME:
                self.alive = False
                self._buffer = b''
                raise ConnectionError(
                    f'the connection sent a {size} byte message, which cannot be '
                    f'right -- the stream is out of step')

            if len(self._buffer) < HEADER + size:
                return

            body = self._buffer[HEADER:HEADER + size]
            number = int.from_bytes(self._buffer[0:4], 'big')
            self._buffer = self._buffer[HEADER + size:]

            inflated = self._inflate.decompress(
                body, MAX_DECOMPRESSED_FRAME + 1
            )
            if len(inflated) > MAX_DECOMPRESSED_FRAME:
                self.alive = False
                raise ValueError(
                    f'a compressed network frame expanded past '
                    f'{MAX_DECOMPRESSED_FRAME} bytes'
                )
            decoded = json.loads(inflated.decode(), object_hook=_decode_values)
            frame_at = None
            if (isinstance(decoded, dict)
                    and set(decoded) == {FRAME_TIME_KEY, FRAME_MESSAGES_KEY}
                    and isinstance(decoded[FRAME_TIME_KEY], (int, float))):
                frame_at = decoded[FRAME_TIME_KEY]
                decoded = decoded[FRAME_MESSAGES_KEY]

            raw_messages = decoded if isinstance(decoded, list) else [decoded]
            if not all(isinstance(message, dict) for message in raw_messages):
                raise ValueError('a network frame must contain messages')
            messages = [
                _FramedMessage(message, number, frame_at)
                for message in raw_messages
            ]
            if number and messages:
                # Expose one public sequence per transport frame.
                messages[0]['n'] = number
            self._pending.extend(messages)
