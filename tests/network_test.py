"""
Net Test: serving a Room out of a game script, and the server that runs it.

None of this opens a Tk window -- that is largely the point. The loader's job is
to pull a Room out of a one-file game *without* running the client half, so these
tests assert on the negative as much as the positive.
"""

import ast
import base64
import contextlib
import io
import json
import os
import socket
import zlib
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import tkinter as tk
import types
import unittest

import pydraw.network
import pydraw._network.protocol as network_protocol
import pydraw.screen
from pydraw import Color, Location
from pydraw.errors import InvalidArgumentError, PydrawError
from pydraw.network import (CONNECTION_TIMEOUT, HEADER, MAX_BACKLOG, MAX_CATCHUP,
                            RESYNC_COOLDOWN, TICK_RATE, VERIFY,
                            Network, Room, _Connection, _Server,
                            _client_boundary, _load_room, action, event)

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
EXAMPLES_DIR = os.path.join(REPO_ROOT, 'examples')


def free_port():
    """A port nobody is using, so parallel runs don't collide."""
    with socket.socket() as probe:
        probe.bind(('', 0))
        return probe.getsockname()[1]


def finish_handshake(connection):
    """Complete the private hello -> ready exchange for a raw test client."""
    hello = connection.read_until(lambda message: message.get('t') == 'hello')
    connection.send({'t': 'ready'})
    connection.read_until(lambda message: message.get('t') == 'connected')
    return hello


class LoaderFixture(unittest.TestCase):
    """Writes game scripts to a temp directory and loads Rooms out of them."""

    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.directory = self._directory.name
        sys.path.insert(0, self.directory)
        self._modules = set(sys.modules)

    def tearDown(self):
        sys.path.remove(self.directory)
        for name in set(sys.modules) - self._modules:
            del sys.modules[name]
        self._directory.cleanup()

    def write(self, name, source):
        path = os.path.join(self.directory, f'{name}.py')
        with open(path, 'w') as handle:
            handle.write(textwrap.dedent(source).lstrip())
        return name


class ClientBoundaryTest(unittest.TestCase):
    """Where does the loader think the client half starts?"""

    @staticmethod
    def boundary(source):
        return _client_boundary(ast.parse(textwrap.dedent(source).lstrip()))

    def test_screen_after_class(self):
        self.assertEqual(self.boundary("""
            X = 1
            class Arena: pass
            screen = Screen(800, 600)
        """), 2)

    def test_screen_first(self):
        self.assertEqual(self.boundary("""
            screen = Screen(800, 600)
            class Arena: pass
        """), 0)

    def test_network_without_screen(self):
        self.assertEqual(self.boundary("""
            class Arena: pass
            net = Network(None)
        """), 1)

    def test_bare_loop_is_a_boundary(self):
        self.assertEqual(self.boundary("""
            class Arena: pass
            while True: pass
        """), 1)

    def test_no_client_half_at_all(self):
        self.assertIsNone(self.boundary("""
            X = 1
            class Arena: pass
        """))


class LoadRoomTest(LoaderFixture):
    """The rule: everything above your Screen line is the server half."""

    GAME = """
        from pydraw import *
        from pydraw.network import *

        SIZE = 10
        {above}

        class Arena(Room):
            def join(self, player):
                player.state['hp'] = bonus() + SIZE

        {below}

        screen = Screen(800, 600, 'game')
        net = Network(screen, room=Arena)
        while True:
            screen.update()
    """

    HELPER = 'def bonus(): return 90'

    def game(self, above='', below=''):
        """The same game twice over, with the helper on either side of the Room."""
        return textwrap.dedent(self.GAME).format(above=above, below=below)

    def test_helper_above_the_class(self):
        module = self.write('above', self.game(above=self.HELPER))
        self.assertEqual(self.hp(_load_room(module, 'Arena')), 100)

    def test_helper_below_the_class(self):
        """The whole point of the change: this used to fail."""
        module = self.write('below', self.game(below=self.HELPER))
        self.assertEqual(self.hp(_load_room(module, 'Arena')), 100)

    def test_both_orders_agree(self):
        above = self.write('order_a', self.game(above=self.HELPER))
        below = self.write('order_b', self.game(below=self.HELPER))
        self.assertEqual(self.hp(_load_room(above, 'Arena')),
                         self.hp(_load_room(below, 'Arena')))

    @staticmethod
    def hp(room_class):
        """Run the loaded Room's join() and report the hp it set."""
        class Player:
            id = 1
            state = {}

        player = Player()
        room_class().join(player)
        return player.state['hp']


class LoaderRefusalTest(LoaderFixture):
    """When it cannot serve the file, it has to say exactly why."""

    def test_room_below_the_screen_line(self):
        module = self.write('late_room', """
            from pydraw import *
            from pydraw.network import *

            screen = Screen(800, 600, 'game')

            class Arena(Room):
                pass
        """)
        with self.assertRaises(PydrawError) as caught:
            _load_room(module, 'Arena')

        message = str(caught.exception)
        self.assertIn('Arena is defined on line 6', message)
        self.assertIn('starts on line 4', message)
        self.assertIn("screen = Screen(800, 600, 'game')", message)
        self.assertIn('arena.py', message)

    def test_helper_below_the_screen_line(self):
        module = self.write('late_helper', """
            from pydraw import *
            from pydraw.network import *

            class Arena(Room):
                def join(self, player):
                    player.state['hp'] = bonus()

            screen = Screen(800, 600, 'game')

            def bonus():
                return 100
        """)
        with self.assertRaises(PydrawError) as caught:
            _load_room(module, 'Arena')

        message = str(caught.exception)
        self.assertIn('`bonus`, defined on line 10', message)
        self.assertIn('below your Screen on line 8', message)

    def test_name_that_exists_nowhere(self):
        module = self.write('typo', """
            from pydraw import *
            from pydraw.network import *

            class Arena(Room):
                def join(self, player):
                    player.state['hp'] = MAXHP

            screen = Screen(800, 600, 'game')
        """)
        with self.assertRaises(PydrawError) as caught:
            _load_room(module, 'Arena')
        self.assertIn('nothing in', str(caught.exception))
        self.assertIn('MAXHP', str(caught.exception))

    def test_class_not_at_top_level(self):
        module = self.write('nested', """
            from pydraw import *
            from pydraw.network import *

            def build():
                class Arena(Room):
                    pass

            screen = Screen(800, 600, 'game')
        """)
        with self.assertRaises(PydrawError) as caught:
            _load_room(module, 'Arena')
        self.assertIn('not a class defined at the top level', str(caught.exception))

    def test_aliased_screen_is_caught_by_the_backstop(self):
        """Static detection can't see this; the stand-in Screen must."""
        module = self.write('aliased', """
            from pydraw.screen import Screen as Display
            from pydraw.network import Room

            window = Display(800, 600, 'game')

            class Arena(Room):
                pass
        """)
        with self.assertRaises(PydrawError) as caught:
            _load_room(module, 'Arena')
        self.assertIn('tried to open a game window', str(caught.exception))

    def test_missing_module(self):
        with self.assertRaises(PydrawError) as caught:
            _load_room('no_such_game_module', 'Arena')
        self.assertIn('no module named', str(caught.exception))


class LoaderEnvironmentTest(LoaderFixture):
    """What the file sees while it is being loaded."""

    def test_argv_is_hidden_and_restored(self):
        module = self.write('argv_game', """
            import sys
            from pydraw import *
            from pydraw.network import *

            HOST = sys.argv[1] if len(sys.argv) > 1 else 'localhost'

            class Arena(Room):
                def join(self, player):
                    player.state['host'] = HOST

            screen = Screen(800, 600, 'game')
        """)
        before = list(sys.argv)
        sys.argv = ['prog', 'argv_game:Arena', '5005']
        try:
            room_class = _load_room(module, 'Arena')
        finally:
            sys.argv = before

        class Player:
            state = {}

        player = Player()
        room_class().join(player)
        self.assertEqual(player.state['host'], 'localhost')
        self.assertEqual(sys.argv, before)

    def test_room_only_module_is_imported_normally(self):
        module = self.write('room_only', """
            from pydraw.network import Room

            MARKER = []
            MARKER.append('ran')

            class Arena(Room):
                pass

            def helper():
                return 1
        """)
        room_class = _load_room(module, 'Arena')
        self.assertTrue(issubclass(room_class, Room))
        self.assertEqual(sys.modules[module].MARKER, ['ran'])


class FlagshipDemoTest(unittest.TestCase):
    """Load the authoritative ships Arena and run its adjudication."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, EXAMPLES_DIR)
        cls.room_class = _load_room('net_ships_v2', 'Arena')

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(EXAMPLES_DIR)
        sys.modules.pop('net_ships_v2', None)

    def setUp(self):
        self.room = self.room_class()
        self.room.start()

    class Player:
        def __init__(self, player_id, x, y, angle=0, hp=100):
            self.id = player_id
            self.slice = {'x': x, 'y': y, 'a': angle}
            self.state = {'hp': hp, 'kills': 0}

        def seed(self, **fields):
            self.slice = dict(fields)

        def reset(self, **fields):
            self.slice.update(fields)

    def arena(self, *players):
        self.room.players = list(players)
        return players

    def test_no_window_was_opened(self):
        """The loaded module never built a Screen -- there is no screen name."""
        self.assertNotIn('net_ships_v2', sys.modules)
        self.assertTrue(issubclass(self.room_class, Room))

    def test_hits_a_ship_in_front(self):
        shooter, target = self.arena(self.Player(1, 100, 100),
                                     self.Player(2, 100, 40))
        self.room.fire(shooter)
        self.assertEqual(target.state['hp'], 80)

    def test_misses_a_ship_out_of_range(self):
        shooter, target = self.arena(self.Player(1, 100, 100),
                                     self.Player(2, 400, 400))
        self.room.fire(shooter)
        self.assertEqual(target.state['hp'], 100)

    def test_misses_a_ship_outside_the_cone(self):
        """60px to the side is well within range but well outside the arc."""
        shooter, target = self.arena(self.Player(1, 100, 100),
                                     self.Player(2, 160, 100))
        self.room.fire(shooter)
        self.assertEqual(target.state['hp'], 100)

    def test_a_kill_picks_a_spawn_and_scores_it(self):
        shooter, target = self.arena(self.Player(1, 100, 100),
                                     self.Player(2, 100, 40, hp=20))
        self.room.fire(shooter)
        self.assertEqual(target.state['hp'], 100)
        self.assertEqual(target.slice, {'x': 700, 'y': 500, 'a': 315})
        self.assertEqual(shooter.state['kills'], 1)

    def test_a_respawn_resets_the_owned_pose_immediately(self):
        shooter, target = self.arena(self.Player(1, 100, 100),
                                     self.Player(2, 100, 40, hp=20))
        self.room.fire(shooter)

        self.assertEqual(target.state['hp'], 100)
        self.assertEqual(target.slice, {'x': 700, 'y': 500, 'a': 315})

    def test_join_sets_server_owned_health(self):
        player = self.Player(3, 0, 0)
        player.state = {}
        self.room.join(player)
        self.assertEqual(player.state['hp'], 100)
        self.assertEqual(player.slice, {'x': 700, 'y': 100, 'a': 225})


class FakeScreen:
    """Just enough Screen for a Network: a frame hook and a handler registry."""

    def __init__(self, **handlers):
        self.registry = dict(handlers)
        self._frame = None

    def on_frame(self, function):
        self._frame = function

    def update(self):
        self._frame()


class HandlerDispatchTest(unittest.TestCase):
    """The handlers a game defines are found by name, and actually fire."""

    def setUp(self):
        self.server = _Server(Room(), free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', self.server._port)
        self.networks.append(network)
        return screen, network

    def pump(self, screens, frames=30):
        for _ in range(frames):
            for screen in screens:
                screen.update()
            time.sleep(1 / 60)

    def test_networkevent_reaches_the_other_player(self):
        """net.send() on one machine fires networkevent() on the others."""
        received = []
        sender_screen, sender = self.join()
        listener_screen, listener = self.join(
            networkevent=lambda name, data, sender: received.append((sender, name, data)))

        sender.send('shot', angle=90)
        self.pump([sender_screen, listener_screen])

        self.assertEqual(received, [(sender.id, 'shot', {'angle': 90})])

    def test_sender_does_not_hear_its_own_event(self):
        heard = []
        screen, network = self.join(
            networkevent=lambda name, data, sender: heard.append(name))
        network.send('shot')
        self.pump([screen])
        self.assertEqual(heard, [])

    def test_a_payload_larger_than_the_socket_buffer_arrives_intact(self):
        """
        The kernel send buffer is tens of KB; this is megabytes. It has to be
        queued and drained across several passes rather than sent in one go.

        The payload is random on purpose. Two megabytes of 'x' would compress to
        almost nothing on the wire and the test would quietly stop reaching the
        drain path it exists to cover.
        """
        received = []
        sender_screen, sender = self.join()
        listener_screen, listener = self.join(
            networkevent=lambda name, data, sender: received.append(data))

        payload = base64.b64encode(os.urandom(2 << 20)).decode()   # ~2.8 MB, ~incompressible
        sender.send('blob', body=payload)
        self.pump([sender_screen, listener_screen], frames=240)

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['body'], payload)

    def test_playerjoin_and_playerquit_fire(self):
        events = []
        first_screen, first = self.join(
            playerjoin=lambda pid: events.append(('join', pid)),
            playerquit=lambda pid: events.append(('leave', pid)))
        second_screen, second = self.join()
        self.pump([first_screen, second_screen])
        self.assertEqual(events, [('join', second.id)])

        second.close()
        self.networks.remove(second)
        self.pump([first_screen])
        self.assertEqual(events[-1], ('leave', second.id))


class PublicationTest(unittest.TestCase):
    """Client lifecycle begins when the first owner slice is published."""

    def setUp(self):
        self.servers = []
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        for server in self.servers:
            server.stop()

    def server(self, room=None):
        server = _Server(room or Room(), free_port())
        server.start_background()
        self.servers.append(server)
        return server

    def join(self, server, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', server._port)
        self.networks.append(network)
        return screen, network

    @staticmethod
    def pump(screens, frames=30):
        for _ in range(frames):
            for screen in screens:
                screen.update()
            time.sleep(1 / 120)

    def test_first_frame_publishes_even_an_empty_slice(self):
        server = self.server()
        events = []
        first_screen, first = self.join(
            server, playerjoin=lambda pid: events.append(('join', pid)),
            networkevent=lambda name, data, sender:
                events.append((name, sender)))
        self.pump([first_screen])

        second_screen, second = self.join(server)
        second.send('hello')                 # waits behind the initial owner slice
        self.pump([first_screen], frames=5)
        self.assertNotIn(second.id, first.players)
        self.assertEqual(events, [])

        self.pump([second_screen, first_screen])
        self.assertIn(second.id, first.players)
        self.assertEqual(events, [('join', second.id), ('hello', second.id)])
        self.assertEqual(dict(first.others())[second.id]._merged(), {})

    def test_an_unpublished_disconnect_has_no_client_lifecycle(self):
        server = self.server()
        events = []
        first_screen, first = self.join(
            server, playerjoin=lambda pid: events.append(('join', pid)),
            playerquit=lambda pid: events.append(('quit', pid)))
        self.pump([first_screen])

        _, second = self.join(server)
        self.assertNotIn(second.id, first.players)
        second.close()
        self.networks.remove(second)
        self.pump([first_screen])

        self.assertEqual(events, [])

    def test_seed_is_available_before_network_returns(self):
        class Seeded(Room):
            def join(self, player):
                player.state['hp'] = 100
                player.seed(x=20, y=30)

        server = self.server(Seeded())
        seen = []
        first_screen, first = self.join(
            server,
            playerjoin=lambda pid: seen.append(dict(first.others())[pid]._merged()),
        )
        self.assertEqual(dict(first.mine), {'x': 20, 'y': 30})

        _, second = self.join(server)
        self.assertEqual(dict(second.mine), {'x': 20, 'y': 30})
        self.pump([first_screen])

        self.assertEqual(seen, [{'x': 20, 'y': 30, 'hp': 100}])

    def test_empty_seed_publishes_a_server_owned_entity(self):
        class ServerOwned(Room):
            def join(self, player):
                player.state.update(x=10, y=15)
                player.seed()

        server = self.server(ServerOwned())
        first_screen, first = self.join(server)
        _, second = self.join(server)
        self.pump([first_screen])

        self.assertEqual(dict(first.others())[second.id]._merged(),
                         {'x': 10, 'y': 15})


class OwnerResetTest(unittest.TestCase):
    """Authoritative replacements correct the owner and reject stale movement."""

    class Correcting(Room):
        def join(self, player):
            player.seed(x=0, y=0, a=90)

        def accept(self, player, proposed, current):
            if proposed.get('x', 0) < 0:
                return current
            if proposed.get('x', 0) > 10:
                corrected = dict(proposed)
                corrected['x'] = 10
                return corrected
            return proposed

        @action
        def respawn(self, player):
            player.reset(x=2, y=3)

    def setUp(self):
        self.room = self.Correcting()
        self.server = _Server(self.room, free_port())
        self.server.start_background()
        self.networks = []
        self.screens = []
        for _ in range(2):
            screen = FakeScreen()
            net = Network(screen, 'localhost', self.server._port)
            self.screens.append(screen)
            self.networks.append(net)
        self.pump()

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def pump(self, frames=40):
        for _ in range(frames):
            for screen in self.screens:
                screen.update()
            time.sleep(1 / 120)

    def remote(self):
        owner, watcher = self.networks
        return dict(watcher.others())[owner.id]

    def test_returning_proposed_does_not_reset_the_owner(self):
        owner = self.networks[0]
        owner.mine['x'] = 5
        self.pump()

        self.assertEqual(owner.mine['x'], 5)
        self.assertEqual(self.remote()['x'], 5)
        self.assertEqual(owner._generation, 0)

    def test_rejection_and_correction_reset_the_owner(self):
        owner = self.networks[0]
        owner.mine['x'] = 20
        self.pump()
        self.assertEqual(owner.mine['x'], 10)
        self.assertEqual(self.remote()['x'], 10)
        corrected_generation = owner._generation

        owner.mine['x'] = -5
        self.pump()
        self.assertEqual(owner.mine['x'], 10)
        self.assertEqual(self.remote()['x'], 10)
        self.assertGreater(owner._generation, corrected_generation)

    def test_player_reset_ignores_old_generation_updates(self):
        owner, watcher = self.networks
        watcher.smooth('x')
        owner.call('respawn')
        deadline = time.perf_counter() + 2
        while (time.perf_counter() < deadline
               and self.server._generations[owner.id] == 0):
            self.pump(frames=1)

        owner._conn.send({'t': 'own', 'slice': {'x': 999, 'y': 999},
                          'generation': 0})
        self.pump()

        self.assertEqual(dict(owner.mine), {'x': 2, 'y': 3, 'a': 90})
        self.assertEqual(dict(self.server._owner[owner.id]),
                         {'x': 2, 'y': 3, 'a': 90})
        self.assertEqual(self.remote()['x'], 2)
        self.assertEqual(len(watcher._history[owner.id]), 1)


class InterceptionTest(unittest.TestCase):
    """A Room with an @event reviewer gets to see net.send before the others do."""

    class Reviewed(Room):
        @event('shot')
        def review_shot(self, player, data):
            data['shooter'] = player.id           # add what only the server knows
            return data

        @event('cheat')
        def refuse(self, player, data):
            return False                          # nobody hears it

        @event('peek')
        def only_looking(self, player, data):
            self.seen = data                      # forgot to return -- must still relay

    def setUp(self):
        self.room = self.Reviewed()
        self.server = _Server(self.room, free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', self.server._port)
        self.networks.append(network)
        return screen, network

    def exchange(self, name, **data):
        """Send one event and return whatever the other player heard."""
        heard = []
        sender_screen, sender = self.join()
        listener_screen, _ = self.join(
            networkevent=lambda n, d, s: heard.append((n, d, s)))

        sender.send(name, **data)
        for _ in range(30):
            sender_screen.update()
            listener_screen.update()
            time.sleep(1 / 60)
        return heard, sender.id

    def test_reviewer_can_add_what_only_the_server_knows(self):
        heard, sender_id = self.exchange('shot', angle=90)
        self.assertEqual(heard, [('shot', {'angle': 90, 'shooter': sender_id},
                                  sender_id)])

    def test_reviewer_can_refuse(self):
        heard, _ = self.exchange('cheat', amount=999)
        self.assertEqual(heard, [])

    def test_reviewer_that_returns_nothing_still_relays(self):
        """The likeliest mistake in the feature must leave a working game."""
        heard, sender_id = self.exchange('peek', note='hello')
        self.assertEqual(heard, [('peek', {'note': 'hello'}, sender_id)])
        self.assertEqual(self.room.seen, {'note': 'hello'})

    def test_unreviewed_events_relay_untouched(self):
        heard, sender_id = self.exchange('anything', x=1)
        self.assertEqual(heard, [('anything', {'x': 1}, sender_id)])

    def test_a_broken_reviewer_does_not_kill_the_room(self):
        class Broken(Room):
            @event('boom')
            def explode(self, player, data):
                raise KeyError('bug in a reviewer')

        server = _Server(Broken(), free_port())
        server.start_background()
        try:
            screen = FakeScreen()
            sender = Network(screen, 'localhost', server._port)
            sender.send('boom')
            for _ in range(20):
                screen.update()
                time.sleep(1 / 60)
            self.assertTrue(sender.connected())
            sender.close()
        finally:
            server.stop()

    def test_two_reviewers_for_one_event_is_refused(self):
        with self.assertRaises(InvalidArgumentError) as caught:
            class Ambiguous(Room):
                @event('shot')
                def first(self, player, data):
                    pass

                @event('shot')
                def second(self, player, data):
                    pass

        self.assertIn('two @event', str(caught.exception))

    def test_event_outside_a_room_is_inert(self):
        """The bare name is safe: it marks, and only a Room ever reads the mark."""
        class NotARoom:
            @event('shot')
            def review(self, player, data):
                return False

        self.assertEqual(NotARoom.review._pydraw_event, 'shot')


class HandshakeTest(unittest.TestCase):
    """A game that names its room finds out when it dialled the wrong one."""

    class Pong(Room):
        pass

    class Arena(Room):
        pass

    def setUp(self):
        self.port = free_port()
        self.server = _Server(self.Pong(), self.port)
        self.server.start_background()

    def tearDown(self):
        self.server.stop()

    def test_a_different_game_on_the_port_is_refused(self):
        with self.assertRaises(PydrawError) as caught:
            Network(FakeScreen(), 'localhost', self.port, room=self.Arena)

        message = str(caught.exception)
        self.assertIn('is running Pong', message)
        self.assertIn('this game is Arena', message)

    def test_the_right_game_connects(self):
        net = Network(FakeScreen(), 'localhost', self.port, room=self.Pong)
        self.assertEqual(net.id, 1)
        self.assertIsNone(net._host_server)      # joined; did not try to host
        net.close()

    def test_a_game_with_no_room_still_connects(self):
        """net_paint has no Room at all, so it declares nothing and checks nothing."""
        net = Network(FakeScreen(), 'localhost', self.port)
        self.assertEqual(net.id, 1)
        net.close()


class LifecycleTest(unittest.TestCase):
    """A socket has one bounded path into and out of one Player lifecycle."""

    class Recording(Room):
        def __init__(self):
            super().__init__()
            self.events = []
            self.departed = []

        def start(self):
            self.events.append('start')

        def join(self, player):
            assert player in self.players
            self.events.append(('join', player.id))

        def leave(self, player):
            assert player not in self.players
            self.departed.append(player)
            self.events.append(('leave', player.id))

        def stop(self):
            assert self.players == []
            self.events.append('stop')

    @staticmethod
    def wait_until(test, seconds=2):
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            if test():
                return
            time.sleep(0.01)
        raise AssertionError('lifecycle condition did not become true')

    def test_close_is_idempotent_and_callbacks_have_one_order(self):
        room = self.Recording()
        server = _Server(room, free_port())
        server.start_background()
        network = Network(FakeScreen(), 'localhost', server._port)
        self.wait_until(lambda: len(room.events) >= 2)

        network.close()
        network.close()
        self.wait_until(lambda: any(
            isinstance(item, tuple) and item[0] == 'leave'
            for item in room.events
        ))
        server.stop()
        server.stop()

        self.assertEqual(room.events, [
            'start', ('join', network.id), ('leave', network.id), 'stop',
        ])

    def test_server_shutdown_leaves_every_player_before_stop(self):
        room = self.Recording()
        server = _Server(room, free_port())
        server.start_background()
        first = Network(FakeScreen(), 'localhost', server._port)
        second = Network(FakeScreen(), 'localhost', server._port)
        self.wait_until(lambda: len(room.players) == 2)

        server.stop()
        first.close()
        second.close()

        self.assertEqual(
            [item[0] for item in room.events if isinstance(item, tuple)],
            ['join', 'join', 'leave', 'leave'],
        )
        self.assertEqual(room.events[-1], 'stop')
        self.assertEqual(len(room.departed), 2)

    def test_an_unfinished_hello_never_becomes_a_player(self):
        room = self.Recording()
        server = _Server(room, free_port())
        server.start_background()
        connection = _Connection.connect('localhost', server._port)
        connection.read_until(lambda message: message.get('t') == 'hello')
        self.wait_until(lambda: len(server._conns) == 1)

        sock = next(iter(server._conns))
        server._conns[sock].handshake_deadline = 0
        self.wait_until(lambda: not server._conns)
        connection.close()
        server.stop()

        self.assertEqual(room.events, ['start', 'stop'])

    def test_ready_is_the_point_that_creates_the_player(self):
        room = self.Recording()
        server = _Server(room, free_port())
        server.start_background()
        connection = _Connection.connect('localhost', server._port)
        hello = connection.read_until(lambda message: message.get('t') == 'hello')
        self.assertEqual(room.players, [])

        connection.send({'t': 'ready'})
        connection.read_until(lambda message: message.get('t') == 'snapshot')
        self.wait_until(lambda: len(room.players) == 1)
        self.assertEqual(room.events, ['start', ('join', hello['id'])])

        connection.close()
        self.wait_until(lambda: len(room.departed) == 1)
        server.stop()

    def test_a_peer_that_does_not_answer_heartbeat_is_released(self):
        room = self.Recording()
        server = _Server(room, free_port())
        server.start_background()
        network = Network(FakeScreen(), 'localhost', server._port)
        self.wait_until(lambda: len(room.players) == 1)

        conn = next(conn for conn in server._conns.values() if conn.established)
        conn.awaiting_pong_at = time.perf_counter() - CONNECTION_TIMEOUT
        self.wait_until(lambda: not room.players)

        # A stale Player reference cannot resurrect a transient message.
        room.departed[0].send('too_late', value=1)
        network.close()
        server.stop()
        self.assertEqual(
            [item for item in room.events if isinstance(item, tuple)
             and item[0] == 'leave'],
            [('leave', network.id)],
        )

    def test_connection_close_is_idempotent_and_releases_queues(self):
        left, right = socket.socketpair()
        connection = _Connection(left)
        connection._outgoing = b'x' * (MAX_BACKLOG + 1)
        connection._pending.append({'t': 'event'})
        connection._queued_bodies.append(b'{}')

        connection.close()
        connection.close()
        right.close()

        self.assertFalse(connection.alive)
        self.assertEqual(connection._outgoing, b'')
        self.assertEqual(connection._pending, [])
        self.assertEqual(connection._queued_bodies, [])

    def test_a_failed_start_still_gets_one_stop_and_releases_the_port(self):
        events = []

        class Broken(Room):
            def start(self):
                events.append('start')
                raise RuntimeError('broken setup')

            def stop(self):
                events.append('stop')

        port = free_port()
        server = _Server(Broken(), port)
        with self.assertRaises(PydrawError):
            server.start_background()
        server.stop()

        self.assertEqual(events, ['start', 'stop'])
        replacement = _Server(Room(), port)
        replacement.start_background()
        replacement.stop()

class AnnounceByReturnTest(unittest.TestCase):
    """What a Room action returns is what the other players are told happened."""

    class Announcing(Room):
        @action
        def fire(self, player):
            return {'shooter': player.id, 'hit': 7}

        @action
        def quiet(self, player):
            return None                       # a private request, like paddle_move

        @action
        def confused(self, player):
            return 'not a dict'               # should be reported, not broadcast

    def setUp(self):
        self.server = _Server(self.Announcing(), free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', self.server._port)
        self.networks.append(network)
        return screen, network

    def call(self, action):
        """One player calls; report what the caller and the other player heard."""
        caller_heard, other_heard = [], []
        caller_screen, caller = self.join(
            networkevent=lambda n, d, s: caller_heard.append((n, d, s)))
        other_screen, _ = self.join(
            networkevent=lambda n, d, s: other_heard.append((n, d, s)))

        caller.call(action)
        for _ in range(30):
            caller_screen.update()
            other_screen.update()
            time.sleep(1 / 60)
        return caller_heard, other_heard, caller.id

    def test_a_returned_dict_reaches_the_others(self):
        _, other_heard, caller_id = self.call('fire')
        self.assertEqual(other_heard,
                         [('fire', {'shooter': caller_id, 'hit': 7}, caller_id)])

    def test_the_caller_is_skipped(self):
        """They asked for it and drew it locally; an echo would double the tracer."""
        caller_heard, _, _ = self.call('fire')
        self.assertEqual(caller_heard, [])

    def test_returning_nothing_stays_private(self):
        _, other_heard, _ = self.call('quiet')
        self.assertEqual(other_heard, [])

    def test_returning_a_non_dict_announces_nothing(self):
        _, other_heard, _ = self.call('confused')
        self.assertEqual(other_heard, [])


class ActionDecoratorTest(unittest.TestCase):
    """Only deliberately exposed Room methods are reachable from a client."""

    class Arena(Room):
        def __init__(self):
            super().__init__()
            self.called = []

        @action
        def fire(self, player, power=1):
            self.called.append(('fire', power))

        def helper(self, player):
            self.called.append(('helper', player.id))

        @property
        def dangerous(self):
            self.called.append(('property', None))
            raise RuntimeError('a client should never run this getter')

    def setUp(self):
        self.room = self.Arena()
        self.server = _Server(self.room, free_port())
        self.player = types.SimpleNamespace(id=7)

    def test_a_decorated_method_is_an_action(self):
        self.server._run_action(None, self.player, 'fire', {'power': 3})
        self.assertEqual(self.room.called, [('fire', 3)])

    def test_an_ordinary_room_method_is_not_remotely_callable(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.server._run_action(None, self.player, 'helper', {})

        self.assertEqual(self.room.called, [])
        self.assertIn('add @action', output.getvalue())

    def test_looking_up_an_action_does_not_run_room_properties(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.server._run_action(None, self.player, 'dangerous', {})
        self.assertEqual(self.room.called, [])

    def test_actions_are_inherited(self):
        class Child(self.Arena):
            pass

        self.assertIn('fire', Child._actions)

    def test_an_override_has_to_opt_in_again(self):
        class Child(self.Arena):
            def fire(self, player, power=1):
                self.called.append(('replacement', power))

        self.assertNotIn('fire', Child._actions)

    def test_reserved_methods_cannot_be_actions(self):
        with self.assertRaises(InvalidArgumentError):
            class Broken(Room):
                @action
                def tick(self, player):
                    pass


class TrackedStateTest(unittest.TestCase):
    """self.state notices its own changes, however far down they happen."""

    def setUp(self):
        self.room = Room()

    def written(self):
        """The top-level keys changed since the last time we looked."""
        return self.room._changes.take()

    def test_a_new_key_is_noticed(self):
        self.room.state['score'] = 0
        self.assertEqual(self.written(), {'score'})

    def test_an_untouched_world_reports_nothing(self):
        self.room.state['score'] = 0
        self.written()
        self.assertEqual(self.written(), set())

    def test_a_change_deep_inside_names_the_top_level_key(self):
        self.room.state['rocks'] = [{'x': 0}, {'x': 5}]
        self.written()

        self.room.state['rocks'][1]['x'] += 1
        self.assertEqual(self.written(), {'rocks'})

    def test_appending_is_noticed(self):
        self.room.state['strokes'] = []
        self.written()

        self.room.state['strokes'].append({'x': 1})
        self.assertEqual(self.written(), {'strokes'})

    def test_a_value_read_out_and_kept_is_still_tracked(self):
        """net_pong does exactly this: `ball = self.state['ball']`, then moves it."""
        self.room.state['ball'] = [0, 0]
        self.written()

        ball = self.room.state['ball']
        ball[0] += 3
        self.assertEqual(self.written(), {'ball'})

    def test_setdefault_hands_back_something_tracked(self):
        """net_ships writes through setdefault('kills', {})[...] = 0."""
        self.room.state.setdefault('kills', {})['1'] = 0
        self.assertEqual(self.written(), {'kills'})
        self.assertEqual(self.room.state['kills'], {'1': 0})

    def test_deleting_is_noticed(self):
        self.room.state['rocks'] = []
        self.written()

        del self.room.state['rocks']
        self.assertEqual(self.written(), {'rocks'})

    def test_replacing_the_whole_world_keeps_tracking(self):
        self.room.state['old'] = 1
        self.written()

        self.room.state = {'new': 2}
        self.assertEqual(self.written(), {'old', 'new'})   # one gone, one arrived

        self.room.state['new'] = 3                         # still tracked afterwards
        self.assertEqual(self.written(), {'new'})

    def test_tracked_containers_are_ordinary_dicts_and_lists(self):
        """A Room must not be able to tell. isinstance and json both have to hold."""
        self.room.state['rocks'] = [{'x': 1}]
        rocks = self.room.state['rocks']

        self.assertIsInstance(rocks, list)
        self.assertIsInstance(rocks[0], dict)
        self.assertEqual(len(rocks), 1)
        self.assertEqual(json.loads(json.dumps(self.room.state)), {'rocks': [{'x': 1}]})

    def test_player_state_is_tracked_too(self):
        server = _Server(Room(), free_port())
        player = pydraw.network.Player(1, None, server)
        player.state['hp'] = 100
        self.assertEqual(player._changes.take(), {'hp'})


class StateSyncFixture(unittest.TestCase):
    """A live room and clients that pump themselves, for watching state arrive."""

    ROOM = Room

    def setUp(self):
        self.room = self.ROOM()
        self.server = _Server(self.room, free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', self.server._port)
        self.networks.append(network)
        return screen, network

    def pump(self, screens, seconds=0.5):
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            for screen in screens:
                screen.update()
            time.sleep(1 / 60)


class StateSyncTest(StateSyncFixture):
    """What the room writes reaches net.state, and only what changed is sent."""

    class Counting(Room):
        def start(self):
            self.state['score'] = 0
            self.state['rocks'] = [{'x': 0}]

        @action
        def bump(self, player):
            self.state['score'] += 1

        @action
        def nudge(self, player):
            self.state['rocks'][0]['x'] += 1

        @action
        def rewrite(self, player):
            self.state['score'] = self.state['score']     # written, but unchanged

        @action
        def drop(self, player):
            del self.state['rocks']

        @action
        def unsendable(self, player):
            self.state['color'] = {1, 2, 3}      # a set: JSON cannot carry it

        @action
        def sneak(self, player):
            # A change made behind the tracking's back, standing in for a Room that
            # kept its own reference to something it put in state. Only the sweep
            # can find this one.
            dict.__setitem__(self.state, 'hidden', 7)

    ROOM = Counting

    def test_a_late_joiner_gets_the_whole_world(self):
        screen, net = self.join()
        self.pump([screen])

        self.assertEqual(net.state['score'], 0)
        self.assertEqual(net.state['rocks'], [{'x': 0}])

    def test_a_change_reaches_net_state(self):
        screen, net = self.join()
        self.pump([screen], 0.2)

        net.call('bump')
        self.pump([screen])

        self.assertEqual(net.state['score'], 1)

    def test_a_change_deep_inside_replicates(self):
        screen, net = self.join()
        self.pump([screen], 0.2)

        net.call('nudge')
        self.pump([screen])

        self.assertEqual(net.state['rocks'], [{'x': 1}])

    def test_writing_the_same_value_again_sends_nothing(self):
        """
        Tracking says it was written; only a real difference goes on the wire.

        Observed through the message count rather than the state, since the point
        is that nothing was sent at all -- the state would look identical either way.
        """
        screen, net = self.join()
        self.pump([screen], 0.2)

        quiet = net._seq
        net.call('rewrite')
        self.pump([screen])
        self.assertEqual(net._seq, quiet)

        net.call('bump')                              # a real change still does
        self.pump([screen])
        self.assertGreater(net._seq, quiet)

    def test_a_deleted_key_disappears(self):
        screen, net = self.join()
        self.pump([screen], 0.2)

        net.call('drop')
        self.pump([screen])

        self.assertNotIn('rocks', net.state)

    def test_state_that_cannot_be_sent_does_not_end_the_game(self):
        """
        Putting a Color or a set in self.state is an easy mistake, and it used to
        take the whole room down: json.dumps raised straight out of the serve loop.
        """
        screen, net = self.join()
        self.pump([screen], 0.2)

        net.call('unsendable')
        self.pump([screen])

        self.assertTrue(self.server._running)
        self.assertTrue(net.connected())
        self.assertNotIn('color', net.state)
        net.call('bump')                          # and the room still works
        self.pump([screen])
        self.assertEqual(net.state['score'], 1)

    def test_the_sweep_catches_what_tracking_missed(self):
        """
        The backstop. A change tracking cannot see is late, but it is not lost --
        so a Room that keeps its own reference to something in state has a slow
        game, not a broken one.
        """
        screen, net = self.join()
        self.pump([screen], 0.2)

        net.call('sneak')
        self.pump([screen], 0.2)
        self.assertNotIn('hidden', net.state)          # tracking never saw it

        self.pump([screen], VERIFY + 0.5)
        self.assertEqual(net.state['hidden'], 7)       # the sweep did


class DeepOwnershipTest(StateSyncFixture):
    """Ownership holds through every dict/list nested inside replicated state."""

    class Nested(Room):
        def start(self):
            self.state['world'] = {
                'rocks': [{'x': 1}],
                'route': ({'x': 2},),
            }

        def join(self, player):
            player.state['profile'] = {
                'badges': ['rookie'],
                'stats': {'wins': 0},
            }

    ROOM = Nested

    def two_players(self):
        first_screen, first = self.join()
        second_screen, second = self.join()
        self.pump([first_screen, second_screen], 0.25)
        return first_screen, first, second_screen, second

    @staticmethod
    def entity(net, player_id):
        return dict(net.others())[player_id]

    def test_world_and_server_player_state_are_read_only_all_the_way_down(self):
        screen, net = self.join()
        self.pump([screen], 0.2)

        attempts = (
            lambda: net.state['world']['rocks'][0].__setitem__('x', 999),
            lambda: net.state['world']['rocks'].append({'x': 2}),
            lambda: net.state['world']['route'][0].__setitem__('x', 999),
            lambda: net.mine['profile']['badges'].append('admin'),
            lambda: net.mine['profile']['stats'].__setitem__('wins', 999),
        )
        for attempt in attempts:
            with self.subTest(attempt=attempt), self.assertRaises(PydrawError):
                attempt()

        self.assertEqual(net.state['world']['rocks'], [{'x': 1}])
        # JSON carries tuples as lists; the dict nested inside is still frozen.
        self.assertEqual(net.state['world']['route'], [{'x': 2}])
        self.assertEqual(net.mine['profile'], {
            'badges': ['rookie'], 'stats': {'wins': 0},
        })

    def test_nested_owned_changes_replicate_and_remote_copies_are_read_only(self):
        owner_screen, owner, watcher_screen, watcher = self.two_players()

        original = {'weapons': [{'name': 'starter'}]}
        owner.mine['loadout'] = original
        original['weapons'].append({'name': 'changed behind its back'})
        self.assertEqual(owner.mine['loadout'], {
            'weapons': [{'name': 'starter'}],
        })
        self.pump([owner_screen, watcher_screen], 0.25)

        owner.mine['loadout']['weapons'].append({'name': 'laser'})
        self.assertTrue(owner._mine_dirty)
        self.pump([owner_screen, watcher_screen], 0.25)

        remote = self.entity(watcher, owner.id)
        self.assertEqual(remote['loadout']['weapons'], [
            {'name': 'starter'}, {'name': 'laser'},
        ])
        with self.assertRaises(PydrawError):
            remote['loadout']['weapons'][0]['name'] = 'hacked'
        with self.assertRaises(PydrawError):
            remote['loadout']['weapons'].clear()

    def test_player_slice_is_deeply_read_only_on_the_server(self):
        screen, net = self.join()
        net.mine['pose'] = {'position': [10, 20]}
        self.pump([screen], 0.25)

        slice_ = self.room.player(net.id).slice
        with self.assertRaises(PydrawError):
            slice_['pose']['position'][0] = 999
        with self.assertRaises(PydrawError):
            slice_['pose'] = {}
        self.assertEqual(slice_['pose'], {'position': [10, 20]})

    def test_owned_fields_can_be_updated_and_deleted_as_a_mapping(self):
        owner_screen, owner, watcher_screen, watcher = self.two_players()
        owner.mine.update(x=10, y=20)
        self.pump([owner_screen, watcher_screen], 0.25)

        del owner.mine['x']
        owner.mine.setdefault('name', 'Ada')
        self.assertEqual(owner.mine.pop('y'), 20)
        self.pump([owner_screen, watcher_screen], 0.25)

        remote = self.entity(watcher, owner.id)
        self.assertEqual(dict(remote), {'name': 'Ada', 'profile': {
            'badges': ['rookie'], 'stats': {'wins': 0},
        }})


class SendRateTest(unittest.TestCase):
    """How fast a game draws must not decide how much it sends."""

    def setUp(self):
        self.server = _Server(Room(), free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **kwargs):
        screen = FakeScreen()
        network = Network(screen, 'localhost', self.server._port, **kwargs)
        self.networks.append(network)
        return screen, network

    def spin(self, screen, net, seconds, moves_per_frame=1):
        """Draw as fast as we can for a while, moving every frame."""
        sent = []
        real = net._conn.send

        def counted(message):
            if message.get('t') == 'own':
                sent.append(message)
            return real(message)

        net._conn.send = counted
        deadline = time.perf_counter() + seconds
        frames = 0
        while time.perf_counter() < deadline:
            for _ in range(moves_per_frame):
                net.mine['x'] = frames
            screen.update()
            frames += 1
        return frames, len(sent)

    def test_a_fast_loop_does_not_send_faster_than_the_rate(self):
        screen, net = self.join(rate=20)
        frames, sent = self.spin(screen, net, 1.0)

        self.assertGreater(frames, 200)          # we really did draw fast
        self.assertLessEqual(sent, 26)           # ~20/s, with room for scheduling
        self.assertGreater(sent, 12)

    def test_the_slice_sent_is_the_newest_one(self):
        """Holding a frame costs nothing -- the slice is read when it goes out."""
        screen, net = self.join(rate=20)
        for value in range(50):
            net.mine['x'] = value
            screen.update()

        self.assertEqual(net.mine['x'], 49)      # local value is always current
        self.assertEqual(net._owner[net.id]['x'], 49)

    def test_rate_none_sends_every_frame(self):
        """
        A fixed number of frames rather than a spin: a spin here draws hundreds of
        thousands of times a second, and rate=None would turn every one of those
        into a message -- which is the flood Room.message_limit exists to stop.
        """
        screen, net = self.join(rate=None)
        sent = []
        real = net._conn.send
        net._conn.send = lambda message: (
            sent.append(message) if message.get('t') == 'own' else None,
            real(message))[1]

        for frame in range(100):
            net.mine['x'] = frame
            screen.update()

        self.assertEqual(len(sent), 100)

    def test_a_nonsense_rate_is_refused(self):
        for bad in (0, -5, 'fast'):
            with self.assertRaises(InvalidArgumentError):
                Network(FakeScreen(), 'localhost', self.server._port, rate=bad)

    def test_precision_quantizes_the_wire_but_not_the_local_slice(self):
        screen, net = self.join(
            rate=None,
            precision={'x': 1, 'a': 0},
        )
        net.mine['x'] = 123.4567
        net.mine['a'] = 89.9876
        net.mine['charge'] = 0.0047
        screen.update()

        deadline = time.perf_counter() + 1
        while (time.perf_counter() < deadline
               and not self.server._owner.get(net.id)):
            time.sleep(1 / 120)

        self.assertEqual(net.mine['x'], 123.4567)
        self.assertEqual(net.mine['a'], 89.9876)
        self.assertEqual(net.mine['charge'], 0.0047)
        self.assertEqual(self.server._owner[net.id]['x'], 123.5)
        self.assertEqual(self.server._owner[net.id]['a'], 90.0)
        self.assertEqual(self.server._owner[net.id]['charge'], 0.0047)

    def test_invalid_precisions_are_refused(self):
        for bad in (
                -1, 0.5, 'tenths', True,
                {'x': -1}, {'x': 0.5}, {'x': True}, {1: 1}):
            with self.subTest(precision=bad):
                with self.assertRaises(InvalidArgumentError):
                    Network(
                        FakeScreen(), 'localhost', self.server._port,
                        precision=bad,
                    )


class SmoothingTest(unittest.TestCase):
    """net.smooth() blends other players between updates; nothing else moves."""

    class Fake(Network):
        """A Network with no socket -- we drive its state directly."""

        def __init__(self):
            self.state = pydraw.network._State()
            self._owner, self._server = {}, {}
            self._conn, self._screen = None, None
            self._smooth, self._smooth_angles = (), ()
            self._history, self._blend = {}, {}
            self._pending_pose_samples = None
            self._rebasing = set()
            self._server_clock_offset = None
            self._clock_window_min = None
            self._clock_window_started = None
            self._interpolation_delay = 0.1
            self.id, self.players = 1, [1, 2]

    def setUp(self):
        self.net = self.Fake()
        self.net.smooth('x', 'y')

    def entity(self, pid=2):
        return pydraw.network._Entity(self.net, pid)

    def arrive(self, slice_, at):
        """Stand in for a server-timestamped snapshot."""
        self.net._remember(2, slice_, at)
        self.net._owner[2] = slice_

    def test_a_player_is_drawn_between_its_last_two_poses(self):
        # Drawn one interval behind, so half an interval after the newer pose
        # landed we should be halfway between the two.
        now = time.perf_counter()
        self.arrive({'x': 0, 'y': 0}, now - 0.15)
        self.arrive({'x': 100, 'y': 200}, now - 0.05)

        self.net._blend_others()
        entity = self.entity()
        self.assertGreater(entity['x'], 0)
        self.assertLess(entity['x'], 100)
        self.assertAlmostEqual(entity['y'], entity['x'] * 2, places=6)

    def test_it_settles_on_the_newest_pose_rather_than_drifting(self):
        """A player who stops sending must stop, not carry on into the distance."""
        old = time.perf_counter() - 5
        self.arrive({'x': 0, 'y': 0}, old)
        self.arrive({'x': 100, 'y': 100}, old + 0.1)

        self.net._blend_others()
        self.assertEqual(self.entity()['x'], 100)

    def test_angles_take_the_short_path_across_zero(self):
        self.net.smooth_angle('a')
        now = time.perf_counter()
        self.arrive({'a': 350}, now - 0.15)
        self.arrive({'a': 10}, now - 0.05)

        self.net._blend_others()
        angle = self.entity()['a']
        self.assertTrue(angle > 350 or angle < 10)

    def test_reverse_angles_also_take_the_short_path(self):
        self.net.smooth_angle('a')
        now = time.perf_counter()
        self.arrive({'a': 10}, now - 0.15)
        self.arrive({'a': 350}, now - 0.05)

        self.net._blend_others()
        angle = self.entity()['a']
        self.assertTrue(angle > 350 or angle < 10)

    def test_server_managed_fields_are_never_blended(self):
        """A smoothed hp would read 13.7 on its way down, and a game may ask."""
        self.net.smooth('x', 'hp')
        now = time.perf_counter()
        self.arrive({'x': 0, 'hp': 100}, now - 0.15)
        self.arrive({'x': 100, 'hp': 80}, now - 0.05)
        self.net._server[2] = {'hp': 80}

        self.net._blend_others()
        self.assertEqual(self.entity()['hp'], 80)     # snapped, not blended
        self.assertLess(self.entity()['x'], 100)      # position still blended

    def test_unsmoothed_fields_and_your_own_entity_are_exact(self):
        now = time.perf_counter()
        self.arrive({'x': 0, 'y': 0, 'a': 350}, now - 0.2)
        self.arrive({'x': 100, 'y': 0, 'a': 10}, now - 0.1)
        self.net._blend_others()

        self.assertEqual(self.entity()['a'], 10)      # angles are not blended
        self.net._owner[1] = {'x': 42}
        self.assertEqual(pydraw.network._Mine(self.net, 1)['x'], 42)

    def test_clearing_one_players_smoothing_snaps_to_the_latest_pose(self):
        now = time.perf_counter()
        self.arrive({'x': 0, 'y': 0}, now - 0.15)
        self.arrive({'x': 100, 'y': 200}, now - 0.05)
        self.net._blend_others()
        self.assertLess(self.entity()['x'], 100)

        self.net.clear_smoothing(2)

        self.assertEqual(self.entity()['x'], 100)
        self.assertNotIn(2, self.net._history)
        self.assertNotIn(2, self.net._blend)

    def test_clearing_all_smoothing_discards_every_timeline(self):
        now = time.perf_counter()
        self.arrive({'x': 10}, now)
        self.net._history[3] = [(now, {'x': 30})]
        self.net._blend = {2: {'x': 10}, 3: {'x': 30}}

        self.net.clear_smoothing()

        self.assertEqual(self.net._history, {})
        self.assertEqual(self.net._blend, {})

    def test_clearing_during_dispatch_drops_the_pending_old_pose(self):
        now = time.perf_counter()
        self.net._pending_pose_samples = {
            (7, 2): (2, {'x': 100}, now),
            (7, 3): (3, {'x': 300}, now),
        }

        self.net.clear_smoothing(2)
        self.net._commit_pose_samples()
        self.net._pending_pose_samples = None

        self.assertNotIn(2, self.net._history)
        self.assertEqual(self.net._history[3][-1][1]['x'], 300)

    def test_only_the_final_pose_in_one_server_frame_advances_history(self):
        """An event barrier may preserve two raw poses, but not two samples."""
        now = time.perf_counter()
        self.net._pending_pose_samples = {}
        for x in (10, 20):
            message = pydraw.network._FramedMessage(
                {'t': 'set', 'key': 'player:2', 'value': {'x': x}},
                frame_number=7, frame_time=now,
            )
            self.net._dispatch(message)
        self.net._commit_pose_samples()
        self.net._pending_pose_samples = None

        history = self.net._history[2]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0][1]['x'], 20)
        self.assertEqual(self.net._owner[2]['x'], 20)

    def test_distinct_server_frames_in_one_pump_remain_distinct_samples(self):
        now = time.perf_counter()
        self.net._pending_pose_samples = {}
        for frame, x in ((7, 10), (8, 20)):
            self.net._dispatch(pydraw.network._FramedMessage(
                {'t': 'set', 'key': 'player:2', 'value': {'x': x}},
                frame_number=frame, frame_time=now + (frame - 7) / 30,
            ))
        self.net._commit_pose_samples()
        self.net._pending_pose_samples = None

        history = self.net._history[2]
        self.assertEqual([sample[1]['x'] for sample in history], [10, 20])

    def test_server_timeline_not_packet_arrival_spacing_drives_blend(self):
        """Bursty delivery cannot collapse a regularly timestamped path."""
        now = time.perf_counter()
        self.net._interpolation_delay = 0.1
        self.arrive({'x': 0}, now - 0.15)
        self.arrive({'x': 100}, now - 0.05)

        self.net._blend_others()
        self.assertAlmostEqual(self.entity()['x'], 50, delta=1)

    def test_naming_more_fields_adds_to_the_list(self):
        """Smoothing a field is permanent, so a second call cannot undo the first."""
        net = self.Fake()
        net.smooth('x')
        net.smooth('y')
        net.smooth_angle('a')

        self.assertEqual(net._smooth, ('x', 'y'))
        self.assertEqual(net._smooth_angles, ('a',))

    def test_naming_the_same_field_twice_changes_nothing(self):
        self.net.smooth('x', 'y')
        self.net._remember(2, {'x': 1}, time.perf_counter())

        self.net.smooth('x')                    # already smoothed

        self.assertEqual(self.net._smooth, ('x', 'y'))
        self.assertIn(2, self.net._history)     # the timeline survives

    def test_a_field_cannot_be_both_a_number_and_an_angle(self):
        self.net.smooth('a')
        with self.assertRaises(InvalidArgumentError):
            self.net.smooth_angle('a')

        plain = self.Fake()
        plain.smooth_angle('a')
        with self.assertRaises(InvalidArgumentError):
            plain.smooth('a')

    def test_a_refused_field_leaves_the_lists_alone(self):
        net = self.Fake()
        net.smooth('x')
        net.smooth_angle('a')
        with self.assertRaises(InvalidArgumentError):
            net.smooth('a', 'y')            # 'y' is fine, 'a' is not

        self.assertEqual(net._smooth, ('x',))
        self.assertEqual(net._smooth_angles, ('a',))

    def test_a_pose_with_no_server_time_is_dropped(self):
        """Our clock and the server's have no relation, so a guess is worse."""
        self.net.smooth('x')
        self.net._pending_pose_samples = {}
        self.net._stage_pose(2, {'x': 1}, None, 7)
        self.net._commit_pose_samples()

        self.assertNotIn(2, self.net._history)

    def test_off_by_default(self):
        plain = self.Fake()
        plain._owner[2] = {'x': 100}
        self.assertEqual(pydraw.network._Entity(plain, 2)['x'], 100)
        self.assertEqual(plain._smooth, ())
        self.assertEqual(plain._smooth_angles, ())


class ServerClockTest(unittest.TestCase):
    """
    The client draws on the server's clock, so it has to keep working out what
    that clock reads over here. Both ends call perf_counter(), but on two machines
    those are two crystals, and two crystals walk apart.
    """

    def setUp(self):
        self.net = SmoothingTest.Fake()

    def observe(self, seconds, drift=0.0, latency=0.005, rate=20):
        """
        Play for `seconds`, with this machine's clock gaining `drift` a second on
        the server's. Returns what the client believes the offset is.
        """
        started = self.net._clock_window_started or 0.0
        step = 1 / rate
        elapsed = 0.0
        while elapsed < seconds:
            elapsed += step
            here = started + elapsed
            # The server's clock reads a little less than ours by now, so the same
            # instant carries a smaller stamp -- which makes our subtraction look
            # like a longer and longer trip.
            there = here - latency - elapsed * drift
            self.net._observe_server_clock(there, here)
        return self.net._server_clock_offset

    def test_the_least_delayed_sample_wins_inside_a_window(self):
        """A slow packet says nothing about the clocks -- only about the wire."""
        self.net._observe_server_clock(100.000, 100.005)     # 5ms trip
        self.net._observe_server_clock(100.050, 100.090)     # 40ms: congestion
        self.net._observe_server_clock(100.100, 100.107)     # 7ms

        self.assertAlmostEqual(self.net._server_clock_offset, 0.005, places=6)

    def test_the_estimate_can_rise_again_when_this_clock_runs_fast(self):
        """
        The failure this replaces: the minimum was kept for the whole session, so
        a client whose clock gained on the server's held its opening estimate for
        ever. The render cursor walked toward the newest pose and then past it,
        and smoothing stopped -- silently, half an hour in.
        """
        drift = 50e-6                       # 50ppm: an ordinary crystal
        self.observe(seconds=1.0, drift=drift)
        opening = self.net._server_clock_offset

        after_an_hour = self.observe(seconds=3600, drift=drift)

        # Truth after an hour: the same 5ms trip now measures 5ms + 180ms of drift.
        self.assertAlmostEqual(after_an_hour, 0.005 + 3600 * drift, delta=0.002)
        self.assertGreater(after_an_hour - opening, 0.15)

    def test_the_estimate_is_never_more_than_two_windows_stale(self):
        """What a window costs: the drift that accrues while a sample is alive."""
        drift = 50e-6
        self.observe(seconds=600, drift=drift)

        truth = 0.005 + 600 * drift
        behind = truth - self.net._server_clock_offset
        self.assertGreaterEqual(behind, 0)
        self.assertLess(behind, 2 * pydraw.network.CLOCK_WINDOW * drift)

    def test_a_clock_that_runs_slow_is_still_followed_at_once(self):
        """This direction always worked: every sample beats the one before it."""
        self.observe(seconds=60, drift=-50e-6)

        self.assertAlmostEqual(self.net._server_clock_offset,
                               0.005 - 60 * 50e-6, delta=0.001)

    def test_a_stamp_that_is_not_a_number_is_ignored(self):
        for bad in (None, 'soon', True, [1]):
            with self.subTest(sent_at=bad):
                self.net._observe_server_clock(bad, 100.0)
        self.assertIsNone(self.net._server_clock_offset)


class RebaseTest(unittest.TestCase):
    """
    clear_smoothing() is for a deliberate teleport. The timeline starts again at
    the point the screen is drawing, so the player sets off at their real speed
    instead of standing still while it refills.
    """

    def setUp(self):
        self.net = SmoothingTest.Fake()
        self.net.smooth('x')
        self.net._interpolation_delay = 0.15
        self.net._server_clock_offset = 0.0

    def entity(self, pid=2):
        return pydraw.network._Entity(self.net, pid)

    def arrive(self, x, at):
        self.net._remember(2, {'x': x}, at)
        self.net._owner[2] = {'x': x}

    def test_the_next_pose_starts_the_timeline_at_the_render_cursor(self):
        now = time.perf_counter()
        self.arrive(0, now - 0.30)
        self.arrive(20, now - 0.15)

        self.net.clear_smoothing(2)
        self.assertNotIn(2, self.net._history)
        self.arrive(500, now)               # the respawn, one packet later

        (sample_at, pose), = self.net._history[2]
        self.assertEqual(pose, {'x': 500})
        self.assertAlmostEqual(sample_at, self.net._render_at(), delta=0.01)

    def test_a_teleport_is_never_slid_across_the_world(self):
        """
        The pose being cleared for is usually still in flight: a game calls this
        from the event that announced the respawn. Rebasing on what is in hand at
        that moment would start the new timeline at the death position and walk
        the ship back across the map.
        """
        now = time.perf_counter()
        self.arrive(0, now - 0.30)
        self.arrive(20, now - 0.15)

        self.net.clear_smoothing(2)         # net._owner[2] is still the old pose
        self.net._blend_others()
        self.assertEqual(self.entity()['x'], 20)      # the last real pose, exactly

        self.arrive(500, now)
        for _ in range(4):
            self.net._blend_others()
            self.assertEqual(self.entity()['x'], 500)  # at the spawn, never between

    def test_the_player_moves_off_the_teleport_instead_of_standing_still(self):
        now = time.perf_counter()
        self.arrive(0, now - 0.30)
        self.net.clear_smoothing(2)
        self.arrive(500, now - 0.001)
        self.arrive(520, now)               # moving again, 20 units on

        self.net._blend_others()
        first = self.entity()['x']
        time.sleep(0.03)
        self.net._blend_others()
        second = self.entity()['x']

        self.assertGreater(second, first)   # before the fix: pinned at 500
        self.assertLessEqual(second, 520)

    def test_clearing_everyone_rebases_everyone_but_you(self):
        self.net.players = [1, 2, 3]
        self.net.clear_smoothing()

        self.assertEqual(self.net._rebasing, {2, 3})

    def test_changing_the_smoothed_fields_rebases_rather_than_freezes(self):
        """
        smooth() throws every timeline away. It has to leave them rebasing like
        clear_smoothing() does, or the one call a game makes at setup costs every
        remote player the freeze this fix removed.
        """
        self.net.players = [1, 2, 3]
        self.arrive(10, time.perf_counter() - 0.2)

        self.net.smooth('x', 'y')

        self.assertEqual(self.net._history, {})
        self.assertEqual(self.net._rebasing, {2, 3})

    def test_changing_the_smoothed_angles_rebases_too(self):
        self.net.players = [1, 2]
        self.net.smooth_angle('a')

        self.assertEqual(self.net._rebasing, {2})

    def test_a_rebase_before_the_server_clock_is_known_uses_the_sample(self):
        """Two clocks in one timeline is worse than no head start."""
        self.net._server_clock_offset = None
        self.net.clear_smoothing(2)

        self.net._remember(2, {'x': 1}, 12345.0)

        self.assertEqual(self.net._history[2][0][0], 12345.0)

    def test_a_player_who_leaves_takes_their_pending_rebase_with_them(self):
        """A rebase waits for a pose. Somebody who has gone will not send one."""
        self.net._screen = FakeScreen()
        self.net.clear_smoothing(2)
        self.assertIn(2, self.net._rebasing)

        self.net._dispatch({'t': 'leave', 'id': 2})

        self.assertNotIn(2, self.net._rebasing)


class EntityReadTest(unittest.TestCase):
    """
    One player is three dictionaries: what they own, what the server manages for
    them, and what the blend says this frame. Reading one field takes the first
    of the three that has it; only reading the whole player merges them.
    """

    def setUp(self):
        self.net = SmoothingTest.Fake()
        self.net.smooth('x')
        self.net._owner[2] = {'x': 100, 'y': 5, 'hp': 999, 'name': 'ada'}
        self.net._server[2] = {'hp': 80, 'score': 3}
        self.net._blend[2] = {'x': 97.5, 'hp': 91.2}

    def entity(self, pid=2):
        return pydraw.network._Entity(self.net, pid)

    def test_one_field_reads_the_same_as_the_whole_player(self):
        entity, merged = self.entity(), self.entity()._merged()
        self.assertEqual(set(merged), set(entity.keys()))
        for field, value in merged.items():
            with self.subTest(field=field):
                self.assertEqual(entity[field], value)
                self.assertEqual(entity.get(field), value)
                self.assertIn(field, entity)

    def test_the_server_wins_over_a_blended_value(self):
        """hp is the room's to say. 91.2 was never true on the way from 999."""
        self.assertEqual(self.entity()['hp'], 80)

    def test_a_blended_value_wins_over_the_owners_raw_one(self):
        self.assertEqual(self.entity()['x'], 97.5)

    def test_an_unblended_owned_field_is_exact(self):
        self.assertEqual(self.entity()['y'], 5)
        self.assertEqual(self.entity()['name'], 'ada')

    def test_a_field_nobody_has(self):
        with self.assertRaises(KeyError):
            self.entity()['fuel']
        self.assertIsNone(self.entity().get('fuel'))
        self.assertEqual(self.entity().get('fuel', 12), 12)
        self.assertNotIn('fuel', self.entity())

    def test_a_player_who_has_not_sent_a_position_yet(self):
        """They join before they move, and every game guards with `in`."""
        self.net.players.append(3)
        empty = self.entity(3)

        self.assertNotIn('x', empty)
        self.assertEqual(len(empty), 0)
        self.assertEqual(empty.get('x', 0), 0)
        with self.assertRaises(KeyError):
            empty['x']

    def test_your_own_write_reads_back_in_the_same_frame(self):
        """net.mine['x'] = net.mine['x'] + 4 runs every frame in every game."""
        self.net._owner[1] = {'x': 10}
        mine = pydraw.network._Mine(self.net, 1)

        mine['x'] = mine['x'] + 4

        self.assertEqual(mine['x'], 14)
        self.assertEqual(self.net._owner[1]['x'], 14)

    def test_another_player_is_still_read_only(self):
        with self.assertRaises(PydrawError):
            self.entity()['x'] = 0


class FramingTest(unittest.TestCase):
    """
    Messages say how long they are rather than ending in a newline.

    That is what lets the body be compressed: zlib output is arbitrary bytes and
    contains newline bytes regularly, so splitting on newlines would cut a single
    compressed message into pieces.
    """

    def setUp(self):
        left, right = socket.socketpair()
        right.setblocking(False)
        self.sender, self.receiver = _Connection(left), _Connection(right)
        self.addCleanup(left.close)
        self.addCleanup(right.close)

    @staticmethod
    def rocks(n=200):
        return [{'x': i * 1.7, 'y': i * 3.1, 'vx': 1.0, 'vy': 1.0, 'r': 8, 'id': i}
                for i in range(n)]

    def sent(self, message) -> bytes:
        """Send one message and return the bytes that actually reached the wire."""
        self.sender.send(message)
        data = b''
        while True:
            try:
                chunk = self.receiver._sock.recv(1 << 16)
            except BlockingIOError:
                break
            if not chunk:
                break
            data += chunk
        return data

    def test_the_second_copy_of_a_world_costs_almost_nothing(self):
        """
        The whole point of a stream: what it sends can refer back to what it
        already sent, so a world that barely changed is nearly free to resend.
        """
        rocks = self.rocks()
        message = {'t': 'set', 'key': 'rocks', 'value': rocks}

        raw = len(json.dumps(message, separators=(',', ':')))
        first = len(self.sent(message))
        rocks[0]['x'] += 1                       # one rock out of two hundred moved
        second = len(self.sent(message))

        self.assertLess(first, raw / 2)          # ~11.9 KB of json -> ~2.4 KB cold
        self.assertLess(second, first / 4)       # ~2.4 KB -> ~0.4 KB once warm

    def test_a_body_round_trips_through_the_stream(self):
        message = {'t': 'set', 'key': 'rocks', 'value': self.rocks()}
        self.receiver._buffer = self.sent(message)
        self.receiver._collect()

        got = self.receiver._pending.pop()
        got.pop('n', None)
        self.assertEqual(got, message)

    def test_many_messages_round_trip_in_order(self):
        """A stream is stateful, so every message must arrive and stay in step."""
        for i in range(40):
            self.receiver._buffer += self.sent(
                {'t': 'event', 'name': f'e{i}', 'data': {'pad': 'x' * 300}})
        self.receiver._collect()

        self.assertEqual([m['name'] for m in self.receiver._pending],
                         [f'e{i}' for i in range(40)])

    def test_a_batch_is_one_frame_but_many_messages(self):
        messages = [
            {'t': 'set', 'key': f'player:{i}', 'value': {'x': i}}
            for i in range(1, 8)
        ]
        for message in messages:
            self.sender.queue_body(pydraw.network._encode(message))
        self.sender.send_queued()

        arrived = self.receiver.poll()
        self.assertEqual(self.sender.seq, 1)
        self.assertEqual(
            [{key: value for key, value in message.items() if key != 'n'}
             for message in arrived],
            messages,
        )
        self.assertEqual(arrived[0]['n'], 1)
        self.assertTrue(all('n' not in message for message in arrived[1:]))

    def test_timestamped_batch_shares_one_private_server_time(self):
        messages = [
            {'t': 'set', 'key': 'player:2', 'value': {'x': 1}},
            {'t': 'event', 'name': 'fire', 'data': {}},
            {'t': 'set', 'key': 'player:2', 'value': {'x': 2}},
        ]
        for message in messages:
            self.sender.queue_body(pydraw.network._encode(message))
        self.sender.send_queued(sent_at=1234.5)

        arrived = self.receiver.poll()
        self.assertEqual(len(arrived), 3)
        self.assertEqual(
            [message._frame_number for message in arrived], [1, 1, 1],
        )
        self.assertEqual(
            [message._frame_time for message in arrived], [1234.5] * 3,
        )

    def test_state_coalescing_stops_at_an_event_barrier(self):
        def queue(message, key=None):
            self.sender.queue_body(pydraw.network._encode(message), key)

        state_key = ('state', 'player:2')
        queue({'t': 'set', 'key': 'player:2', 'value': {'x': 1}}, state_key)
        queue({'t': 'set', 'key': 'player:2', 'value': {'x': 2}}, state_key)
        queue({'t': 'event', 'name': 'fire', 'data': {'x': 2}})
        queue({'t': 'set', 'key': 'player:2', 'value': {'x': 3}}, state_key)
        queue({'t': 'set', 'key': 'player:2', 'value': {'x': 4}}, state_key)
        self.sender.send_queued()

        arrived = self.receiver.poll()
        self.assertEqual(
            [(message['t'], message.get('value', {}).get('x'))
             for message in arrived],
            [('set', 2), ('event', None), ('set', 4)],
        )

    def test_frames_really_do_contain_newline_bytes(self):
        """The reason for length-prefixed framing, asserted rather than assumed."""
        wire = self.sent({'t': 'set', 'key': 'rocks', 'value': self.rocks()})
        self.assertGreater(wire.count(b'\n'), 0)

    def test_a_stream_out_of_step_is_refused(self):
        """A flipped byte must fail loudly rather than decode to something wrong."""
        wire = bytearray(self.sent({'t': 'set', 'key': 'rocks',
                                    'value': self.rocks()}))
        wire[HEADER + 40] ^= 0xFF
        self.receiver._buffer = bytes(wire)
        with self.assertRaises((zlib.error, ValueError)):
            self.receiver._collect()

    def test_a_small_compressed_frame_cannot_expand_without_bound(self):
        wire = self.sent({'t': 'event', 'name': 'blob',
                          'data': {'body': 'x' * 1000}})
        self.receiver._buffer = wire
        old_limit = network_protocol.MAX_DECOMPRESSED_FRAME
        network_protocol.MAX_DECOMPRESSED_FRAME = 128
        try:
            with self.assertRaisesRegex(ValueError, 'expanded past'):
                self.receiver._collect()
        finally:
            network_protocol.MAX_DECOMPRESSED_FRAME = old_limit

    def test_json_never_emits_a_raw_newline(self):
        """Why the old framing was safe, so the reason is on record."""
        text = json.dumps({'text': 'hello\nworld'}, separators=(',', ':'))
        self.assertEqual(text.encode().count(b'\n'), 0)

    def test_several_messages_in_one_read_all_arrive(self):
        server = _Server(Room(), free_port())
        server.start_background()
        try:
            conn = _Connection.connect('localhost', server._port)
            finish_handshake(conn)
            conn.read_until(lambda m: m.get('t') == 'snapshot')
            conn.send({'t': 'own', 'slice': {}, 'generation': 0})
            for i in range(20):
                conn.send({'t': 'event', 'name': f'e{i}', 'data': {}})

            heard = []
            screen = FakeScreen(
                networkevent=lambda n, d, s: heard.append(n))
            listener = Network(screen, 'localhost', server._port)
            for i in range(20):
                conn.send({'t': 'event', 'name': f'x{i}', 'data': {'i': i}})

            deadline = time.perf_counter() + 3
            while time.perf_counter() < deadline and len(heard) < 20:
                screen.update()
                time.sleep(1 / 120)

            self.assertEqual(heard, [f'x{i}' for i in range(20)])
            listener.close()
            conn.close()
        finally:
            server.stop()

    def test_a_nonsense_length_is_refused_rather_than_waited_on(self):
        """A stream out of step must fail loudly, not block for ever."""
        conn = _Connection(socket.socket())
        conn._buffer = (1).to_bytes(4, 'big') + (1 << 30).to_bytes(4, 'big') + b'junk'
        with self.assertRaises(ConnectionError) as caught:
            conn._collect()
        self.assertIn('out of step', str(caught.exception))


class BroadcastEncodingTest(unittest.TestCase):
    """One broadcast encodes its body once, however many players are listening."""

    def room(self, players):
        """
        A server with connections attached but its loop never started.

        Deliberately not a live room: a running one broadcasts joins and state of
        its own, and both tests here count what a single broadcast does. Against a
        real server they race it and fail perhaps one run in ten.
        """
        server = _Server(Room(), free_port())
        conns, socks = [], []
        for player_id in range(1, players + 1):
            mine, _theirs = socket.socketpair()
            self.addCleanup(mine.close)
            self.addCleanup(_theirs.close)
            conn = _Connection(mine)
            server._conns[mine] = conn
            server._ids[mine] = player_id
            conns.append(conn)
            socks.append(mine)
        return server, conns, socks

    def test_the_body_is_built_once_not_once_per_player(self):
        """
        Counted on this server object rather than by patching the module: other
        tests leave servers shutting down in background threads, and a global
        patch catches their traffic too.
        """
        server, _, _ = self.room(4)
        encoded, queued = [], []
        real_body = server._body

        def watch_body(message):
            encoded.append(message.get('t'))
            return real_body(message)

        server._body = watch_body
        for conn in server._conns.values():
            real_queue = conn.queue_body
            conn.queue_body = lambda body, key=None, c=conn, q=real_queue: (
                queued.append(c), q(body, key))[1]
        server._broadcast({'t': 'event', 'name': 'boom', 'data': {}})

        self.assertEqual(encoded, ['event'])        # serialized once...
        self.assertEqual(len(queued), 4)            # ...and handed to all four

    def test_every_player_still_gets_its_own_number(self):
        """The count is per player, so a skipped message is not a gap for others."""
        server, conns, socks = self.room(2)

        server._broadcast({'t': 'event', 'name': 'all', 'data': {}})
        server._flush_all(force_batch=True)
        server._broadcast({'t': 'event', 'name': 'most', 'data': {}}, skip=socks[0])
        server._flush_all(force_batch=True)

        self.assertEqual(conns[0].seq, 1)              # skipped the second one
        self.assertEqual(conns[1].seq, 2)


class OthersTest(unittest.TestCase):
    """
    net.others() and net.players expose only players whose owner slice is published.
    """

    def setUp(self):
        self.net = SmoothingTest.Fake()
        self.net.players = [1, 2, 3]

    def ids(self):
        return [pid for pid, _ in self.net.others()]

    def test_an_empty_published_slice_is_included(self):
        self.net._owner[2] = {}

        self.assertEqual(self.ids(), [2])

    def test_a_player_appears_as_soon_as_they_send_anything(self):
        self.net._owner[2] = {'x': 10, 'y': 20}

        self.assertEqual(self.ids(), [2])

    def test_room_fields_need_an_explicit_empty_owner_slice(self):
        self.net._server[3] = {'hp': 100}

        self.assertEqual(self.ids(), [])
        self.net._owner[3] = {}
        self.assertEqual(self.ids(), [3])

    def test_you_are_never_one_of_the_others(self):
        self.net._owner[1] = {'x': 1}
        self.net._owner[2] = {'x': 2}

        self.assertEqual(self.ids(), [2])

    def test_what_is_yielded_reads_without_a_guard(self):
        self.net._owner[2] = {'x': 10, 'y': 20}

        for _, other in self.net.others():
            self.assertEqual((other['x'], other['y']), (10, 20))


class MessageLimitTest(unittest.TestCase):
    """
    The server pays for every message it reads, and what it reads is the one thing
    a player chooses. A client that will not stop is dropped rather than served.
    """

    class Strict(Room):
        message_limit = 20

    def setUp(self):
        self.server = _Server(self.Strict(), free_port())
        self.server.start_background()
        self.connections = []

    def tearDown(self):
        for connection in self.connections:
            connection.close()
        self.server.stop()

    def raw(self):
        connection = _Connection.connect('localhost', self.server._port)
        finish_handshake(connection)
        self.connections.append(connection)
        return connection

    def wait_for(self, players, seconds=1.0):
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            if len(self.server._conns) == players:
                return
            time.sleep(0.01)
        self.fail(f'expected {players} connected, got {len(self.server._conns)}')

    def test_a_flood_costs_that_player_the_game(self):
        flooder = self.raw()
        self.wait_for(1)

        for _ in range(200):
            flooder.send({'t': 'own', 'slice': {'x': 1}})

        self.wait_for(0)

    def test_a_busy_but_reasonable_client_is_left_alone(self):
        player = self.raw()
        self.wait_for(1)

        for _ in range(10):
            player.send({'t': 'own', 'slice': {'x': 1}})
        time.sleep(0.2)

        self.assertEqual(len(self.server._conns), 1)

    def test_the_count_starts_again_each_second(self):
        """Fifteen a second for an hour is a game. Two hundred at once is not."""
        player = self.raw()
        self.wait_for(1)

        for _ in range(15):
            player.send({'t': 'own', 'slice': {'x': 1}})
        time.sleep(1.05)                    # a new second, a new count
        for _ in range(15):
            player.send({'t': 'own', 'slice': {'x': 1}})
        time.sleep(0.2)

        self.assertEqual(len(self.server._conns), 1)

    def test_one_players_flood_does_not_cost_anyone_else_theirs(self):
        quiet = self.raw()
        flooder = self.raw()
        self.wait_for(2)

        for _ in range(200):
            flooder.send({'t': 'own', 'slice': {'x': 1}})

        self.wait_for(1)
        self.assertTrue(quiet.alive)

    def test_an_invalid_limit_is_refused(self):
        for bad in (0, -1, 'lots', True, None):
            with self.subTest(limit=bad):
                room = type('Invalid', (Room,), {'message_limit': bad})()
                with self.assertRaises(InvalidArgumentError):
                    _Server(room, free_port())


class ByteLimitTest(unittest.TestCase):
    """A few huge messages are bounded separately from a flood of tiny ones."""

    class Strict(Room):
        byte_limit = 2048

    def setUp(self):
        self.server = _Server(self.Strict(), free_port())
        self.server.start_background()
        self.connections = []

    def tearDown(self):
        for connection in self.connections:
            connection.close()
        self.server.stop()

    def raw(self):
        connection = _Connection.connect('localhost', self.server._port)
        finish_handshake(connection)
        self.connections.append(connection)
        return connection

    def wait_for(self, players, seconds=1.0):
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            if len(self.server._conns) == players:
                return
            time.sleep(0.01)
        self.fail(f'expected {players} connected, got {len(self.server._conns)}')

    def test_a_large_wire_burst_drops_only_its_sender(self):
        quiet = self.raw()
        sender = self.raw()
        self.wait_for(2)

        body = base64.b64encode(os.urandom(4096)).decode()
        sender.send({'t': 'event', 'name': 'blob', 'data': {'body': body}})

        self.wait_for(1)
        self.assertTrue(quiet.alive)

    def test_a_small_message_is_left_alone(self):
        player = self.raw()
        self.wait_for(1)
        player.send({'t': 'event', 'name': 'hello', 'data': {}})
        time.sleep(0.1)
        self.assertEqual(len(self.server._conns), 1)

    def test_an_invalid_byte_limit_is_refused(self):
        for bad in (0, -1, 1.5, 'lots', True, None):
            with self.subTest(limit=bad):
                room = type('Invalid', (Room,), {'byte_limit': bad})()
                with self.assertRaises(InvalidArgumentError):
                    _Server(room, free_port())


class InterpolationDelayTest(unittest.TestCase):
    """
    Poses arrive at the slower of two rates -- how often a client sends, and how
    often the room replicates. The delay has to follow whichever that is, or the
    render cursor sits past the newest pose and the smoothing it asked for stops.
    """

    class Batched(Room):
        replication_rate = 30

    def setUp(self):
        self.servers, self.networks = [], []

    def tearDown(self):
        for network in self.networks:
            network.close()
        for server in self.servers:
            server.stop()

    def join(self, room, **kwargs):
        server = _Server(room, free_port())
        server.start_background()
        self.servers.append(server)
        network = Network(FakeScreen(), 'localhost', server._port, **kwargs)
        self.networks.append(network)
        return network

    def test_an_unbatched_room_follows_the_clients_own_rate(self):
        for rate, cadence in ((60, 60), (10, 10), (None, pydraw.network.OWN_RATE)):
            with self.subTest(rate=rate):
                network = self.join(Room(), rate=rate)
                self.assertAlmostEqual(network._interpolation_delay, 3 / cadence)

    def test_a_batched_room_caps_the_rate_it_can_deliver(self):
        """Sending at 60 through a room that replicates at 30 arrives at 30."""
        network = self.join(self.Batched(), rate=60)
        self.assertAlmostEqual(network._interpolation_delay, 3 / 30)

    def test_a_slow_client_is_slower_than_the_room_it_joins(self):
        network = self.join(self.Batched(), rate=10)
        self.assertAlmostEqual(network._interpolation_delay, 3 / 10)


class ReplicationBatchTest(unittest.TestCase):
    """A Room can opt into paced, transparent server-to-client batches."""

    class Batched(Room):
        replication_rate = 30

    def setUp(self):
        self.server = _Server(self.Batched(), free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', self.server._port, rate=None)
        self.networks.append(network)
        return screen, network

    def pump(self, screens, seconds=0.3):
        deadline = time.perf_counter() + seconds
        while time.perf_counter() < deadline:
            for screen in screens:
                screen.update()
            time.sleep(1 / 120)

    def test_handshake_state_and_events_are_transparent(self):
        heard = []
        mover_screen, mover = self.join()
        watcher_screen, watcher = self.join(
            networkevent=lambda *args: heard.append(args),
        )

        for x in range(40):
            mover.mine['x'] = x
            mover_screen.update()
        mover.send('wave', x=39)
        self.pump([mover_screen, watcher_screen])

        other = next(entity for pid, entity in watcher.others() if pid == mover.id)
        self.assertEqual(other['x'], 39)
        self.assertEqual([(name, data) for name, data, _ in heard],
                         [('wave', {'x': 39})])

    def test_many_owner_writes_use_far_fewer_server_frames(self):
        mover_screen, mover = self.join()
        watcher_screen, watcher = self.join()
        self.pump([mover_screen, watcher_screen], 0.1)

        watcher_connection = next(
            conn for sock, conn in self.server._conns.items()
            if self.server._ids[sock] == watcher.id
        )
        starting_sequence = watcher_connection.seq
        for x in range(100):
            mover.mine['x'] = x
            mover_screen.update()
        self.pump([mover_screen, watcher_screen], 0.25)

        other = next(entity for pid, entity in watcher.others() if pid == mover.id)
        self.assertEqual(other['x'], 99)
        self.assertLess(watcher_connection.seq - starting_sequence, 15)

    def test_room_cadence_sets_three_snapshot_interpolation_delay(self):
        _, network = self.join()
        self.assertAlmostEqual(network._interpolation_delay, 3 / 30)

    def test_event_barriers_do_not_collapse_remote_motion(self):
        mover_screen, mover = self.join()
        watcher_screen, watcher = self.join()
        watcher.smooth('x')
        self.pump([mover_screen, watcher_screen], 0.15)

        rendered = []
        snapshot_times = set()
        started = time.perf_counter()
        frame = 0
        while time.perf_counter() - started < 0.8:
            mover.mine['x'] = frame
            mover_screen.update()
            if frame % 3 == 0:
                mover.send('wave', frame=frame)
            watcher_screen.update()

            history = watcher._history.get(mover.id, ())
            snapshot_times.update(sample_at for sample_at, _ in history)
            if time.perf_counter() - started > 0.25:
                other = next(
                    entity for pid, entity in watcher.others()
                    if pid == mover.id
                )
                if 'x' in other:
                    rendered.append(other['x'])
            frame += 1
            time.sleep(1 / 120)

        spacings = [
            newer - older
            for older, newer in zip(
                sorted(snapshot_times), sorted(snapshot_times)[1:],
            )
        ]
        self.assertTrue(spacings)
        self.assertGreater(min(spacings), 0.01)
        self.assertGreater(len(rendered), 10)
        self.assertLess(
            max(abs(newer - older)
                for older, newer in zip(rendered, rendered[1:])),
            3,
        )

    def test_invalid_cadences_are_refused(self):
        """Both are a number of times a second. None is no longer one of them."""
        for setting in ('replication_rate', 'tick_rate'):
            for bad in (0, -1, 'fast', True, None):
                with self.subTest(setting=setting, rate=bad):
                    room = type('Invalid', (Room,), {setting: bad})()
                    with self.assertRaises(InvalidArgumentError):
                        _Server(room, free_port())

    def test_the_defaults_pace_every_room(self):
        """A room that says nothing still batches -- there is no unpaced path."""
        server = _Server(Room(), free_port())

        self.assertAlmostEqual(server._replication_interval, 1 / 60)
        self.assertAlmostEqual(server._tick_interval, 1 / 30)

    def test_a_room_sets_its_own_two_cadences(self):
        """How finely the world is simulated, and how often players hear of it."""
        class Slow(Room):
            tick_rate = 10
            replication_rate = 20

        server = _Server(Slow(), free_port())

        self.assertAlmostEqual(server._tick_interval, 1 / 10)
        self.assertAlmostEqual(server._replication_interval, 1 / 20)


class BrokenAcceptTest(unittest.TestCase):
    """
    accept() sits on the path of every movement every player makes, so whatever it
    gets wrong has to cost the anti-cheat rather than the game.
    """

    class Exploding(Room):
        def accept(self, player, proposed, current):
            raise KeyError('a bug in the anti-cheat')

    class Forgetful(Room):
        def accept(self, player, proposed, current):
            pass                                         # meant to return proposed

    class ForgetfulClamp(Room):
        def accept(self, player, proposed, current):
            proposed['x'] = min(proposed['x'], 100)      # clamped it in place, then
                                                         # forgot to return anything

    def move(self, room_class):
        """Send one owned write and report what the server stored for that player."""
        server = _Server(room_class(), free_port())
        server.start_background()
        try:
            screen = FakeScreen()
            net = Network(screen, 'localhost', server._port)
            net.mine['x'], net.mine['y'] = 250, 30

            deadline = time.perf_counter() + 2
            while time.perf_counter() < deadline and not server._owner.get(net.id):
                screen.update()
                time.sleep(1 / 60)

            stored = dict(server._owner.get(net.id, {}))
            self.assertTrue(net.connected())
            self.assertTrue(server._running)
            net.close()
            return stored
        finally:
            server.stop()

    def test_a_raising_accept_lets_the_write_through(self):
        self.assertEqual(self.move(self.Exploding), {'x': 250, 'y': 30})

    def test_an_accept_that_forgets_to_return_lets_the_write_through(self):
        """Storing None would erase the slice and the player would vanish."""
        self.assertEqual(self.move(self.Forgetful), {'x': 250, 'y': 30})

    def test_falling_back_keeps_edits_made_to_proposed_in_place(self):
        """
        The fallback is `proposed` itself, not a copy of what arrived -- so an
        accept() that clamped in place and then forgot to return still clamps.
        """
        self.assertEqual(self.move(self.ForgetfulClamp), {'x': 100, 'y': 30})


class ValueSerializationTest(unittest.TestCase):
    """
    A Color is its three numbers and a Location is its two, so a game should be
    able to put one in its state and have it arrive as itself. Sending them as a
    bare string or list would mean you write a Color and everyone else reads a
    str -- and `other['color'].rgb()` raising AttributeError on somebody else's
    machine is exactly the bug this module exists to prevent.
    """

    def round_trip(self, value):
        """Through a real framed, compressed connection -- not just json."""
        left, right = socket.socketpair()
        sender, receiver = _Connection(left), _Connection(right)
        try:
            sender.send({'t': 'set', 'key': 'k', 'value': value})
            return receiver.poll()[0]['value']
        finally:
            sender.close()
            receiver.close()

    def test_a_color_arrives_as_a_color(self):
        for original in (Color('red'), Color('#ff8800'), Color(9, 8, 7)):
            with self.subTest(original=original):
                arrived = self.round_trip(original)
                self.assertIsInstance(arrived, Color)
                self.assertEqual(arrived, original)
                self.assertEqual(arrived.rgb(), original.rgb())

    def test_a_color_keeps_the_form_it_was_written_in(self):
        """
        Named and rgb colors compare equal, so sending everything as rgb would
        pass a test of equality -- and then print as '(255, 0, 0)' on every other
        machine. That difference is a long afternoon for whoever meets it.
        """
        self.assertEqual(str(self.round_trip(Color('red'))), 'red')
        self.assertEqual(str(self.round_trip(Color('#ff8800'))), '#ff8800')
        self.assertEqual(str(self.round_trip(Color(9, 8, 7))), '(9, 8, 7)')

    def test_a_location_arrives_as_a_location(self):
        arrived = self.round_trip(Location(40, 90))
        self.assertIsInstance(arrived, Location)
        self.assertEqual((arrived.x(), arrived.y()), (40, 90))

    def test_they_survive_nested_in_ordinary_state(self):
        arrived = self.round_trip({'brush': {'color': Color('blue'), 'width': 4},
                                   'trail': [Location(1, 2), Location(3, 4)]})
        self.assertEqual(arrived['brush']['color'], Color('blue'))
        self.assertEqual(arrived['brush']['width'], 4)
        self.assertEqual([point.x() for point in arrived['trail']], [1, 3])

    def test_a_game_dict_that_looks_like_a_tag_is_left_alone(self):
        """
        The decoder runs on every dict that arrives, including ones a game built
        itself. It has to rebuild only what it really wrote.
        """
        for lookalike in ({'~': 'Color'},                       # no value
                          {'~': 'Wombat', 'v': [1]},            # unknown type
                          {'~': 'Color', 'v': [1], 'x': 2},     # wrong shape
                          {'~': 'tilde', 'other': 1}):
            with self.subTest(lookalike=lookalike):
                self.assertEqual(self.round_trip(lookalike), lookalike)

    def test_a_payload_that_lies_about_its_type_does_not_end_the_game(self):
        arrived = self.round_trip({'~': 'Location', 'v': 'not a pair'})
        self.assertEqual(arrived, {'~': 'Location', 'v': 'not a pair'})

    def test_a_sprite_is_still_refused_and_says_why(self):
        """A Rectangle belongs to one screen. There is nothing to rebuild."""
        class FakeSprite:
            def __init__(self):
                self._screen = object()

        with self.assertRaises(TypeError) as caught:
            pydraw.network._encode({'t': 'set', 'value': FakeSprite()})
        self.assertIn('belongs to the screen', str(caught.exception))

    def test_room_state_may_hold_one(self):
        """
        _canonical decides whether a key can be sent at all, so it has to see the
        same values the wire does -- or the room is told off for a good color.
        """
        self.assertIsNotNone(pydraw.network._canonical({'color': Color('red')}))
        self.assertIsNone(pydraw.network._unsendable(Color('red')))
        self.assertIsNone(pydraw.network._unsendable({'at': Location(1, 2)}))
        self.assertIsNotNone(pydraw.network._unsendable({1, 2, 3}))

    def test_a_color_replicates_through_a_running_room(self):
        """End to end: room state on the server, a Color on the client."""
        server = _Server(Room(), free_port())
        server._room._bind(server)
        server._room.state['brush'] = Color('purple')
        server.start_background()
        try:
            screen = FakeScreen()
            network = Network(screen, 'localhost', server._port)
            deadline = time.perf_counter() + 2
            while time.perf_counter() < deadline and 'brush' not in network.state:
                screen.update()
                time.sleep(1 / 60)

            self.assertIsInstance(network.state['brush'], Color)
            self.assertEqual(network.state['brush'], Color('purple'))
            network.close()
        finally:
            server.stop()

    def test_a_color_survives_a_trip_through_net_mine(self):
        """What a game actually writes: net.mine['color'] = Color('red')."""
        server = _Server(Room(), free_port())
        server.start_background()
        try:
            mover_screen = FakeScreen()
            mover = Network(mover_screen, 'localhost', server._port)
            watcher_screen = FakeScreen()
            watcher = Network(watcher_screen, 'localhost', server._port)

            mover.mine['color'] = Color('lime')
            mover.mine['at'] = Location(12, 34)

            deadline = time.perf_counter() + 2
            seen = None
            while time.perf_counter() < deadline and seen is None:
                mover_screen.update()
                watcher_screen.update()
                for _, entity in watcher.others():
                    if 'color' in entity:
                        seen = entity
                time.sleep(1 / 60)

            self.assertIsNotNone(seen, 'the color never arrived')
            self.assertIsInstance(seen['color'], Color)
            self.assertEqual(seen['color'], Color('lime'))
            self.assertEqual(seen['at'].x(), 12)

            mover.close()
            watcher.close()
        finally:
            server.stop()


class EventValueTest(unittest.TestCase):
    """
    net_paint's exact shape: a stroke event carrying a Color, kept so that a late
    joiner is replayed it. The server decodes the value, holds it, and encodes it
    again for whoever turns up -- so the round trip happens twice, on two machines.
    """

    def setUp(self):
        self.server = _Server(Room(), free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', self.server._port)
        self.networks.append(network)
        return screen, network

    def pump(self, screens, frames=30):
        for _ in range(frames):
            for screen in screens:
                screen.update()
            time.sleep(1 / 60)

    def test_a_color_in_an_event_arrives_as_a_color(self):
        heard = []
        painter_screen, painter = self.join()
        watcher_screen, _ = self.join(networkevent=lambda *a: heard.append(a))

        painter.send('begin', keep=True, c=Color(255, 128, 0), w=4)
        self.pump([painter_screen, watcher_screen])

        self.assertEqual(len(heard), 1)
        _, data, _ = heard[0]
        self.assertIsInstance(data['c'], Color)
        self.assertEqual(data['c'].rgb(), (255, 128, 0))

    def test_a_late_joiner_is_replayed_the_color_too(self):
        """
        The kept event sits on the server between the two trips. This is the path
        that used to force net_paint to send str(color) and rebuild it by hand --
        which quietly only worked for named colors.
        """
        painter_screen, painter = self.join()
        painter.send('begin', keep=True, c=Color(255, 128, 0), w=4)
        self.pump([painter_screen], frames=15)

        heard = []
        latecomer_screen, _ = self.join(networkevent=lambda *a: heard.append(a))
        self.pump([painter_screen, latecomer_screen])

        self.assertEqual(len(heard), 1)
        _, data, _ = heard[0]
        self.assertIsInstance(data['c'], Color)
        self.assertEqual(data['c'].rgb(), (255, 128, 0))

    def test_every_color_form_survives_the_round_trip(self):
        heard = []
        painter_screen, painter = self.join()
        watcher_screen, _ = self.join(networkevent=lambda *a: heard.append(a))

        palette = [Color('black'), Color('#ff8800'), Color(255, 128, 0)]
        for color in palette:
            painter.send('begin', c=color)
        self.pump([painter_screen, watcher_screen])

        arrived = [data['c'] for _, data, _ in heard]
        self.assertEqual(arrived, palette)
        self.assertEqual([str(color) for color in arrived],
                         ['black', '#ff8800', '(255, 128, 0)'])


class HousekeepingTest(unittest.TestCase):
    """Small things that were quietly wrong."""

    def test_a_room_class_is_built_once(self):
        """
        Naming a Room says which game this is *and* offers to host it. Asking
        _as_room() separately for each ran a student's __init__ twice.
        """
        built = []

        class Counted(Room):
            def __init__(self):
                super().__init__()
                built.append(1)

        network = Network(FakeScreen(), 'localhost', free_port(), room=Counted)
        try:
            self.assertEqual(len(built), 1)
        finally:
            network.close()

    def test_a_growing_key_is_complained_about_once(self):
        """
        The warning carries the size, and complaints used to be remembered by
        their whole text -- so a key that grew announced itself at every KB.
        """
        server = _Server(Room(), free_port())
        server._room._bind(server)

        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            for kilobytes in range(40, 140, 10):
                server._body({'t': 'set', 'key': 'map',
                              'value': ['x' * 1000] * kilobytes})

        warnings = [line for line in printed.getvalue().splitlines()
                    if 'look back through' in line]
        self.assertEqual(len(warnings), 1, f'said it {len(warnings)} times')

    def test_a_second_oversized_key_is_still_worth_saying(self):
        server = _Server(Room(), free_port())
        server._room._bind(server)

        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            for key in ('map', 'strokes'):
                server._body({'t': 'set', 'key': key,
                              'value': ['x' * 1000] * 40})

        warnings = [line for line in printed.getvalue().splitlines()
                    if 'look back through' in line]
        self.assertEqual(len(warnings), 2)

    def test_both_ends_number_what_they_send(self):
        """The client numbers too; the server simply has no use for it."""
        left, right = socket.socketpair()
        client, server = _Connection(left), _Connection(right)
        try:
            client.send({'t': 'own', 'slice': {'x': 1}})
            client.send({'t': 'own', 'slice': {'x': 2}})
            self.assertEqual([m['n'] for m in server.poll()], [1, 2])
        finally:
            client.close()
            server.close()


class ReadOnlyStateTest(unittest.TestCase):
    """
    net.state is the server's. Blocking `state[key] = value` was never enough:
    CPython does not route update() and the rest through __setitem__ for a dict
    subclass, so they all used to work. A write that took effect on one machine
    while every other player saw nothing is worse than no protection at all.
    """

    def setUp(self):
        self.state = pydraw.network._State()
        self.state._assign('score', 7)

    def assert_refused(self, description, change):
        with self.assertRaises(PydrawError, msg=f'{description} was allowed') as caught:
            change()
        self.assertIn('read-only', str(caught.exception))
        self.assertEqual(self.state['score'], 7, f'{description} changed it anyway')

    def test_every_way_in_is_closed(self):
        for description, change in (
            ('state[key] = value', lambda: self.state.__setitem__('score', 0)),
            ('del state[key]', lambda: self.state.__delitem__('score')),
            ('state.update()', lambda: self.state.update({'score': 0})),
            ('state.setdefault()', lambda: self.state.setdefault('score', 0)),
            ('state.pop()', lambda: self.state.pop('score')),
            ('state.popitem()', lambda: self.state.popitem()),
            ('state.clear()', lambda: self.state.clear()),
            ('state |= other', lambda: self.state.__ior__({'score': 0})),
        ):
            with self.subTest(description):
                self.assert_refused(description, change)

    def test_it_is_still_an_ordinary_dict_to_read(self):
        self.state._assign('rocks', [1, 2])
        self.assertEqual(self.state['score'], 7)
        self.assertEqual(dict(self.state), {'score': 7, 'rocks': [1, 2]})
        self.assertIn('rocks', self.state)
        self.assertEqual(sorted(self.state), ['rocks', 'score'])
        self.assertEqual(self.state.get('nothing', 'default'), 'default')
        self.assertEqual(json.loads(json.dumps(self.state)), {'score': 7,
                                                              'rocks': [1, 2]})

    def test_nested_containers_are_ordinary_to_read_but_refuse_every_mutator(self):
        self.state._assign('world', {'things': [{'x': 1}]})
        world = self.state['world']

        self.assertIsInstance(world, dict)
        self.assertIsInstance(world['things'], list)
        self.assertIsInstance(world['things'][0], dict)
        self.assertEqual(json.loads(json.dumps(world)), {'things': [{'x': 1}]})

        attempts = (
            lambda: world.__setitem__('new', 1),
            lambda: world.update(new=1),
            lambda: world['things'].append({'x': 2}),
            lambda: world['things'].__setitem__(slice(None), []),
            lambda: world['things'][0].pop('x'),
        )
        for attempt in attempts:
            with self.subTest(attempt=attempt), self.assertRaises(PydrawError):
                attempt()

        self.assertEqual(world, {'things': [{'x': 1}]})

    def test_the_server_can_still_write_it(self):
        """The refusal is for the game. Arriving state goes in the other way."""
        self.state._assign('score', 8)
        self.assertEqual(self.state['score'], 8)
        self.state._remove('score')
        self.assertNotIn('score', self.state)

    def test_a_real_snapshot_still_lands(self):
        server = _Server(Room(), free_port())
        server._room._bind(server)
        server._room.state['score'] = 3
        server.start_background()
        try:
            screen = FakeScreen()
            network = Network(screen, 'localhost', server._port)
            deadline = time.perf_counter() + 2
            while time.perf_counter() < deadline and 'score' not in network.state:
                screen.update()
                time.sleep(1 / 60)
            self.assertEqual(network.state['score'], 3)
            network.close()
        finally:
            server.stop()


class FrameHookErrorTest(unittest.TestCase):
    """
    Screen.update() used to run the frame hooks inside the try that catches a
    closing window. Network handlers are dispatched from a hook, so a typo in a
    student's networkevent() read as 'the window shut' -- printing 'Terminated.',
    calling exit(0), and discarding the traceback.

    These drive Screen.update() against a stand-in, so they need no window.
    """

    class Canvas:
        def __init__(self, error=None):
            self.error = error
            self.updated = 0

        def update(self):
            self.updated += 1
            if self.error is not None:
                raise self.error

    def screen(self, *hooks, canvas_error=None):
        stub = types.SimpleNamespace()
        stub._frame_hooks = list(hooks)
        stub._canvas = self.Canvas(canvas_error)
        return stub

    def update(self, stub):
        """Run the real Screen.update() against the stand-in."""
        return pydraw.screen.Screen.update(stub)

    def setUp(self):
        self.was_terminating = pydraw.screen.Screen._TERMINATING
        pydraw.screen.Screen._TERMINATING = False

    def tearDown(self):
        pydraw.screen.Screen._TERMINATING = self.was_terminating

    def test_a_handler_bug_reaches_the_programmer(self):
        def broken():
            raise AttributeError("'NoneType' object has no attribute 'moveto'")

        with self.assertRaises(AttributeError):
            self.update(self.screen(broken))

    def test_any_other_mistake_reaches_them_too(self):
        def broken():
            raise KeyError('shooter')

        with self.assertRaises(KeyError):
            self.update(self.screen(broken))

    def test_an_ordinary_frame_still_runs_every_hook_then_redraws(self):
        order = []
        stub = self.screen(lambda: order.append('first'),
                           lambda: order.append('second'))
        self.update(stub)
        self.assertEqual(order, ['first', 'second'])
        self.assertEqual(stub._canvas.updated, 1)

    def test_a_closing_window_still_exits_before_any_hook_runs(self):
        """
        The ordering that makes the hoist safe. onclose() sets _TERMINATING before
        it destroys the root, so a hook never meets a dead canvas.
        """
        ran = []
        pydraw.screen.Screen._TERMINATING = True
        stub = self.screen(lambda: ran.append('hook'))

        printed = io.StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(printed):
            self.update(stub)

        self.assertEqual(ran, [], 'a hook ran after the window had gone')
        self.assertIn('Terminated.', printed.getvalue())

    def test_a_dying_canvas_is_still_a_clean_shutdown(self):
        stub = self.screen(canvas_error=tk.TclError('invalid command name'))
        printed = io.StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(printed):
            self.update(stub)
        self.assertIn('Terminated.', printed.getvalue())


class TickPacingTest(unittest.TestCase):
    """
    A tick that overran must not become a debt. The room used to owe one tick for
    every one it missed and repay them back to back, all still claiming to be
    1/30 of a second -- so a second of stall arrived as a second of game time
    crammed into a few milliseconds.
    """

    def run_room(self, room, seconds):
        server = _Server(room, free_port())
        server.start_background()
        try:
            time.sleep(seconds)
        finally:
            server.stop()
            server._thread.join(timeout=2)
        return server

    def test_a_stall_does_not_come_back_as_a_burst(self):
        stamps = []
        stalled = threading.Event()

        class Stalling(Room):
            def tick(self, dt):
                stamps.append(time.perf_counter())
                if not stalled.is_set():
                    stalled.set()
                    time.sleep(0.5)          # a debugger, a big rebuild, a swap

        self.run_room(Stalling(), 1.5)

        self.assertTrue(stalled.is_set(), 'the stalling tick never ran')
        gaps = [later - earlier for earlier, later in zip(stamps, stamps[1:])]
        crammed = [gap for gap in gaps if gap < 1 / TICK_RATE / 4]
        self.assertEqual(crammed, [], f'{len(crammed)} ticks ran back to back')

    def test_the_stalled_tick_is_told_how_long_it_really_took(self):
        """dt is measured, not assumed -- that is what keeps the world honest."""
        seen = []
        stalled = threading.Event()

        class Stalling(Room):
            def tick(self, dt):
                seen.append(dt)
                if not stalled.is_set():
                    stalled.set()
                    time.sleep(0.2)

        self.run_room(Stalling(), 1.0)

        self.assertGreaterEqual(max(seen), 0.2)
        self.assertAlmostEqual(seen[0], 1 / TICK_RATE, delta=1 / TICK_RATE)

    def test_no_tick_is_ever_told_more_than_the_cap(self):
        """Past the cap a truer dt stops helping and starts skipping collisions."""
        seen = []
        stalled = threading.Event()

        class Stalling(Room):
            def tick(self, dt):
                seen.append(dt)
                if not stalled.is_set():
                    stalled.set()
                    time.sleep(1.0)

        self.run_room(Stalling(), 2.0)

        self.assertLessEqual(max(seen), MAX_CATCHUP)

    def test_an_untroubled_room_still_ticks_at_the_ordinary_rate(self):
        seen = []

        class Counting(Room):
            def tick(self, dt):
                seen.append(dt)

        self.run_room(Counting(), 1.0)

        self.assertGreater(len(seen), 20)            # ~30, with slack for load
        self.assertLess(max(seen), 4 / TICK_RATE)


class ServerShutdownTest(unittest.TestCase):
    """stop() only sets a flag. The serve thread owns the sockets and closes them."""

    def test_the_player_sockets_are_closed(self):
        server = _Server(Room(), free_port())
        server.start_background()
        network = Network(FakeScreen(), 'localhost', server._port)
        try:
            deadline = time.perf_counter() + 2
            while time.perf_counter() < deadline and not server._conns:
                time.sleep(1 / 60)
            sockets = list(server._conns)
            self.assertEqual(len(sockets), 1)

            server.stop()
            server._thread.join(timeout=2)

            self.assertFalse(server._thread.is_alive())
            for sock in sockets:
                self.assertEqual(sock.fileno(), -1, 'a player socket was left open')
        finally:
            network.close()

    def test_the_port_is_free_again_afterwards(self):
        """What a second game on the same machine depends on."""
        port = free_port()
        first = _Server(Room(), port)
        first.start_background()
        first.stop()
        first._thread.join(timeout=2)

        second = _Server(Room(), port)
        second.start_background()          # raises EADDRINUSE if the listener leaked
        second.stop()
        second._thread.join(timeout=2)


class MalformedMessageTest(unittest.TestCase):
    """
    Everything above assumes the players are pydraw. These are the messages a
    pydraw client never sends -- a truncated event, a slice that is not a slice.

    One bad client must cost that client its turn. It must never end the game for
    the room, and it must never leave the world in a shape that breaks everyone
    *else* the next time they read it.
    """

    def setUp(self):
        self.server = _Server(Room(), free_port())
        self.server.start_background()
        self.networks = []
        self.printed = io.StringIO()

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self):
        screen = FakeScreen()
        network = Network(screen, 'localhost', self.server._port)
        self.networks.append(network)
        return screen, network

    def send_raw(self, network, message, screens, frames=25):
        """Post a message no real client would send, then let the room chew on it."""
        with contextlib.redirect_stdout(self.printed):
            network._conn.send(message)
            for _ in range(frames):
                for screen in screens:
                    screen.update()
                time.sleep(1 / 60)

    def assert_room_survived(self):
        """The serve thread is still up, and still willing to take a new player."""
        self.assertTrue(self.server._running)
        self.assertTrue(self.server._thread.is_alive())

        latecomer = Network(FakeScreen(), 'localhost', self.server._port)
        self.networks.append(latecomer)
        self.assertIsNotNone(latecomer.id)

    def test_an_event_with_no_name_does_not_end_the_game(self):
        """
        The message is well framed and decodes cleanly -- it just has no 'name'.
        That KeyError used to leave serve_forever and take everybody with it.
        """
        screen, sender = self.join()
        other_screen, other = self.join()

        self.send_raw(sender, {'t': 'event'}, [screen, other_screen])

        self.assertTrue(sender.connected())
        self.assertTrue(other.connected())
        self.assert_room_survived()

    def test_the_others_keep_playing_after_it(self):
        """The cost lands on the sender's turn, not on the room."""
        screen, sender = self.join()
        heard = []
        other_screen = FakeScreen(networkevent=lambda *a: heard.append(a))
        other = Network(other_screen, 'localhost', self.server._port)
        self.networks.append(other)

        self.send_raw(sender, {'t': 'event'}, [screen, other_screen])
        with contextlib.redirect_stdout(self.printed):
            sender.send('shot', x=1)
            for _ in range(30):
                screen.update()
                other_screen.update()
                time.sleep(1 / 60)

        self.assertEqual([name for name, _, _ in heard], ['shot'])

    def test_a_slice_that_is_not_a_slice_is_refused(self):
        """
        Storing this used to put a string where every other client expects a dict,
        so each of them raised TypeError the next time it read that player.
        """
        screen, sender = self.join()
        other_screen, other = self.join()

        self.send_raw(sender, {'t': 'own', 'slice': 'not-a-dict'},
                      [screen, other_screen])

        self.assertEqual(self.server._owner[sender.id], {})
        for _, entity in other.others():
            self.assertEqual(dict(entity.items()), {})       # readable, not a crash
        self.assertIn('where its own slice should be', self.printed.getvalue())

    def test_an_own_message_with_no_slice_leaves_the_player_where_it_was(self):
        """An absent slice used to store {} -- and the sender vanished for everyone."""
        screen, sender = self.join()
        sender.mine['x'], sender.mine['y'] = 40, 90

        deadline = time.perf_counter() + 2
        while time.perf_counter() < deadline and not self.server._owner.get(sender.id):
            screen.update()
            time.sleep(1 / 60)

        self.send_raw(sender, {'t': 'own'}, [screen])

        self.assertEqual(self.server._owner[sender.id], {'x': 40, 'y': 90})

    def test_a_room_that_never_wrote_accept_still_gets_the_protection(self):
        """
        The check sits before accept(), so it holds for the empty base Room -- the
        one a Tier 1 game uses, which has no server code of its own at all.
        """
        screen, sender = self.join()
        self.send_raw(sender, {'t': 'own', 'slice': [1, 2, 3]}, [screen])

        self.assertEqual(self.server._owner[sender.id], {})
        self.assert_room_survived()


class SequenceTest(unittest.TestCase):
    """Every message a player is sent is numbered, so a hole in the count shows."""

    def setUp(self):
        self.server = _Server(Room(), free_port())
        self.server.start_background()
        self.connections = []

    def tearDown(self):
        for connection in self.connections:
            connection.close()
        self.server.stop()

    def raw(self):
        connection = _Connection.connect('localhost', self.server._port)
        self.connections.append(connection)
        return connection

    def test_the_first_messages_are_numbered_from_one(self):
        """The provisional hello and established snapshot are separate frames."""
        connection = self.raw()
        hello = finish_handshake(connection)
        snapshot = connection.read_until(lambda m: m.get('t') == 'snapshot')
        self.assertEqual(hello['n'], 1)
        self.assertEqual(snapshot['n'], 2)

    def test_each_player_is_counted_separately(self):
        """
        Plenty of what the server sends goes to everyone but one person, so a
        count shared across the room would show gaps that mean nothing.
        """
        first = self.raw()
        finish_handshake(first)
        first.read_until(lambda m: m.get('t') == 'snapshot')
        second = self.raw()
        hello = finish_handshake(second)
        self.assertEqual(hello['n'], 1)         # its own count, not the room's


class ResyncTest(StateSyncFixture):
    """A player who has missed something asks for the world and gets it."""

    class Counting(Room):
        def start(self):
            self.state['score'] = 0

        @action
        def bump(self, player):
            self.state['score'] += 1

    ROOM = Counting

    def test_a_gap_is_noticed_and_repaired(self):
        screen, net = self.join()
        self.pump([screen], 0.2)

        # Stand in for a message that never arrived: the next one the server sends
        # will be two ahead of what we think we last saw.
        net._seq -= 1
        net.state._assign('ghost', 'left over from before the gap')

        net.call('bump')
        self.pump([screen], RESYNC_COOLDOWN + 0.5)

        self.assertIsNotNone(net._asked_at)          # it did notice and ask
        self.assertFalse(net._resyncing)             # and the snapshot came back
        self.assertEqual(net.state['score'], 1)
        self.assertNotIn('ghost', net.state)         # replaced, not merged

    def test_the_server_can_push_one(self):
        screen, net = self.join()
        self.pump([screen], 0.2)
        net.state._assign('ghost', 1)

        self.room.player(net.id).resync()
        self.pump([screen])

        self.assertNotIn('ghost', net.state)

    def conn_for(self, net):
        """The server's side of one player's connection."""
        sock = next(sock for sock, pid in self.server._ids.items() if pid == net.id)
        return self.server._conns[sock]

    def test_asking_over_and_over_does_not_make_the_server_do_it(self):
        """One confused client must not have the room rebuilt on every message."""
        screen, net = self.join()
        self.pump([screen], 0.2)

        conn = self.conn_for(net)
        before = conn.seq
        for _ in range(50):
            net._send({'t': 'resync'})
        self.pump([screen], 0.3)

        self.assertEqual(conn.seq, before)          # all of them turned down

    def test_the_limit_is_a_wait_and_not_a_refusal(self):
        """Turning a request down has to be temporary, or a real gap never heals."""
        screen, net = self.join()
        self.pump([screen], 0.2)

        conn = self.conn_for(net)
        net._send({'t': 'resync'})
        self.pump([screen], 0.2)
        before = conn.seq                           # turned down: still cooling

        time.sleep(RESYNC_COOLDOWN)
        net._send({'t': 'resync'})
        self.pump([screen], 0.3)
        self.assertGreater(conn.seq, before)        # now it answers


class ClearHistoryTest(unittest.TestCase):
    """keep=True grows a log; a Room has to be able to empty it."""

    def setUp(self):
        self.room = Room()
        self.server = _Server(self.room, free_port())
        self.server.start_background()
        self.networks = []

    def tearDown(self):
        for network in self.networks:
            network.close()
        self.server.stop()

    def join(self, **handlers):
        screen = FakeScreen(**handlers)
        network = Network(screen, 'localhost', self.server._port)
        self.networks.append(network)
        return screen, network

    def test_kept_events_replay_until_they_are_cleared(self):
        screen, net = self.join()
        net.send('stroke', keep=True, x=1)
        for _ in range(30):
            screen.update()
            time.sleep(1 / 60)

        heard = []
        late_screen, _ = self.join(
            networkevent=lambda n, d, s: heard.append(n))
        for _ in range(30):
            late_screen.update()
            time.sleep(1 / 60)
        self.assertEqual(heard, ['stroke'])

        self.assertEqual(self.room.clear_kept_events(), 1)

        later = []
        last_screen, _ = self.join(
            networkevent=lambda n, d, s: later.append(n))
        for _ in range(30):
            last_screen.update()
            time.sleep(1 / 60)
        self.assertEqual(later, [])


class ServedArenaTest(unittest.TestCase):
    """The loaded Room, over a real socket, with no Screen and no Network."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, EXAMPLES_DIR)
        cls.room_class = _load_room('net_ships_v2', 'Arena')
        sys.path.remove(EXAMPLES_DIR)
        sys.modules.pop('net_ships_v2', None)

    def setUp(self):
        self.server = _Server(self.room_class(), free_port())
        self.server.start_background()
        self.connections = []

    def tearDown(self):
        for connection in self.connections:
            connection.close()
        self.server.stop()

    def join(self, x, y, angle=0):
        connection = _Connection.connect('localhost', self.server._port)
        self.connections.append(connection)
        hello = finish_handshake(connection)
        connection.send({'t': 'own', 'slice': {'x': x, 'y': y, 'a': angle}})
        return connection, hello['id']

    def test_players_get_ids_and_server_owned_health(self):
        connection, player_id = self.join(100, 100)
        self.assertEqual(player_id, 1)
        snapshot = connection.read_until(lambda m: m.get('t') == 'snapshot')
        self.assertEqual(snapshot['state']['server:1'], {'hp': 100, 'kills': 0})

    def test_firing_is_adjudicated_by_the_server(self):
        shooter, _ = self.join(100, 100)
        victim, victim_id = self.join(100, 40)
        time.sleep(0.2)                       # let both slices reach the server
        shooter.send({'t': 'call', 'action': 'fire'})

        deadline = time.perf_counter() + 2
        hp = None
        while time.perf_counter() < deadline and hp != 80:
            for message in victim.poll():
                if (message.get('t') == 'set'
                        and message.get('key') == f'server:{victim_id}'):
                    hp = message['value']['hp']
            time.sleep(1 / 60)
        self.assertEqual(hp, 80)

    def test_reserved_actions_are_ignored(self):
        connection, _ = self.join(100, 100)
        connection.send({'t': 'call', 'action': 'tick'})
        connection.send({'t': 'call', 'action': '_bind'})
        time.sleep(0.2)
        self.assertTrue(self.server._running)      # the server shrugged them off


class CommandLineTest(unittest.TestCase):
    """`python -m pydraw.network game:Room` really does serve, and really does not play."""

    def serve(self, target, port, directory):
        environment = dict(os.environ, PYTHONPATH=REPO_ROOT)
        return subprocess.Popen(
            [sys.executable, '-m', 'pydraw.network', target, str(port)],
            cwd=directory, env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def assert_serves(self, target, directory):
        port = free_port()
        process = self.serve(target, port, directory)
        try:
            deadline = time.perf_counter() + 10
            while time.perf_counter() < deadline:
                try:
                    connection = _Connection.connect('localhost', port)
                except OSError:
                    time.sleep(0.1)
                    continue
                hello = connection.read_until(lambda m: m.get('t') == 'hello')
                self.assertEqual(hello['id'], 1)
                connection.close()
                return
            self.fail(f'{target} never answered -- did it enter the game loop?')
        finally:
            process.terminate()
            process.wait(timeout=5)
            process.stdout.close()

    def test_serves_the_ships_demo(self):
        self.assert_serves('net_ships_v2:Arena', EXAMPLES_DIR)

    def test_serves_the_pong_demo(self):
        self.assert_serves('net_pong:Pong', EXAMPLES_DIR)


if __name__ == '__main__':
    unittest.main()
