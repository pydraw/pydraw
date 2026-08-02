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
import pydraw.screen
from pydraw import Color, Location
from pydraw.errors import InvalidArgumentError, PydrawError
from pydraw.network import (HEADER, MAX_CATCHUP, RESYNC_COOLDOWN, TICK, VERIFY,
                            Network, Room, _Connection, _Server,
                            _client_boundary, _load_room, event)

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
EXAMPLES_DIR = os.path.join(REPO_ROOT, 'examples')


def free_port():
    """A port nobody is using, so parallel runs don't collide."""
    with socket.socket() as probe:
        probe.bind(('', 0))
        return probe.getsockname()[1]


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
    """Load the real net_ships.py Arena and run its actual adjudication."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, EXAMPLES_DIR)
        cls.room_class = _load_room('net_ships', 'Arena')

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(EXAMPLES_DIR)
        sys.modules.pop('net_ships', None)

    def setUp(self):
        self.room = self.room_class()

    class Player:
        def __init__(self, player_id, x, y, angle=0, hp=100):
            self.id = player_id
            self.slice = {'x': x, 'y': y, 'a': angle}
            self.state = {'hp': hp, 'kills': 0}      # what Arena.join() gives them

    def arena(self, *players):
        self.room.players = list(players)
        return players

    def test_no_window_was_opened(self):
        """The loaded module never built a Screen -- there is no screen name."""
        self.assertNotIn('net_ships', sys.modules)
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
        self.assertEqual(target.state['hp'], 0)      # still dead: it hasn't moved
        self.assertIn('spawn', target.state)         # the server chose where
        self.assertEqual(shooter.state['kills'], 1)

    def test_the_first_move_after_dying_comes_back_at_the_spawn(self):
        """accept() is where a dead player returns -- on its next write, not before."""
        shooter, target = self.arena(self.Player(1, 100, 100),
                                     self.Player(2, 100, 40, hp=20))
        self.room.fire(shooter)

        spawn = target.state['spawn']
        accepted = self.room.accept(target, {'x': 999, 'y': 999, 'a': 1.5},
                                    target.slice)
        self.assertEqual(target.state['hp'], 100)
        self.assertEqual([accepted['x'], accepted['y'], accepted['a']], list(spawn))

    def test_ignores_a_player_who_has_not_spawned(self):
        shooter, target = self.arena(self.Player(1, 100, 100),
                                     self.Player(2, 100, 40))
        target.slice = {}
        self.room.fire(shooter)                      # must not raise
        self.assertEqual(target.state['hp'], 100)

    def test_join_sets_server_owned_health(self):
        player = self.Player(3, 0, 0)
        player.state = {}
        self.room.join(player)
        self.assertEqual(player.state['hp'], 100)


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
        _, second = self.join()
        self.pump([first_screen])
        self.assertEqual(events, [('join', second.id)])

        second.close()
        self.networks.remove(second)
        self.pump([first_screen])
        self.assertEqual(events[-1], ('leave', second.id))


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


class AnnounceByReturnTest(unittest.TestCase):
    """What a Room action returns is what the other players are told happened."""

    class Announcing(Room):
        def fire(self, player):
            return {'shooter': player.id, 'hit': 7}

        def quiet(self, player):
            return None                       # a private request, like paddle_move

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

        def bump(self, player):
            self.state['score'] += 1

        def nudge(self, player):
            self.state['rocks'][0]['x'] += 1

        def rewrite(self, player):
            self.state['score'] = self.state['score']     # written, but unchanged

        def drop(self, player):
            del self.state['rocks']

        def unsendable(self, player):
            self.state['color'] = {1, 2, 3}      # a set: JSON cannot carry it

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
        screen, net = self.join(rate=None)
        frames, sent = self.spin(screen, net, 0.3)
        self.assertEqual(sent, frames)

    def test_a_nonsense_rate_is_refused(self):
        for bad in (0, -5, 'fast'):
            with self.assertRaises(InvalidArgumentError):
                Network(FakeScreen(), 'localhost', self.server._port, rate=bad)


class SmoothingTest(unittest.TestCase):
    """net.smooth() blends other players between updates; nothing else moves."""

    class Fake(Network):
        """A Network with no socket -- we drive its state directly."""

        def __init__(self):
            self.state = pydraw.network._State()
            self._owner, self._server = {}, {}
            self._conn, self._screen = None, None
            self._smooth, self._history, self._blend = (), {}, {}
            self.id, self.players = 1, [1, 2]

    def setUp(self):
        self.net = self.Fake()
        self.net.smooth('x', 'y')

    def entity(self, pid=2):
        return pydraw.network._Entity(self.net, pid)

    def arrive(self, slice_, at):
        """Stand in for an update landing at a given moment."""
        previous = self.net._history.get(2)
        if previous is None:
            self.net._history[2] = (slice_, at, slice_, at)
        else:
            _, _, newest, when = previous
            self.net._history[2] = (newest, when, slice_, at)
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

    def test_off_by_default(self):
        plain = self.Fake()
        plain._owner[2] = {'x': 100}
        self.assertEqual(pydraw.network._Entity(plain, 2)['x'], 100)
        self.assertEqual(plain._smooth, ())


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

    def test_json_never_emits_a_raw_newline(self):
        """Why the old framing was safe, so the reason is on record."""
        text = json.dumps({'text': 'hello\nworld'}, separators=(',', ':'))
        self.assertEqual(text.encode().count(b'\n'), 0)

    def test_several_messages_in_one_read_all_arrive(self):
        server = _Server(Room(), free_port())
        server.start_background()
        try:
            conn = _Connection.connect('localhost', server._port)
            conn.read_until(lambda m: m.get('t') == 'snapshot')
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
        encoded, pushed = [], []
        real_body, real_push = server._body, server._push

        def watch_body(message):
            encoded.append(message.get('t'))
            return real_body(message)

        def watch_push(conn, body):
            pushed.append(conn)
            return real_push(conn, body)

        server._body, server._push = watch_body, watch_push
        server._broadcast({'t': 'event', 'name': 'boom', 'data': {}})

        self.assertEqual(encoded, ['event'])        # serialized once...
        self.assertEqual(len(pushed), 4)            # ...and handed to all four

    def test_every_player_still_gets_its_own_number(self):
        """The count is per player, so a skipped message is not a gap for others."""
        server, conns, socks = self.room(2)

        server._broadcast({'t': 'event', 'name': 'all', 'data': {}})
        server._broadcast({'t': 'event', 'name': 'most', 'data': {}}, skip=socks[0])

        self.assertEqual(conns[0].seq, 1)              # skipped the second one
        self.assertEqual(conns[1].seq, 2)


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
        crammed = [gap for gap in gaps if gap < TICK / 4]
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
        self.assertAlmostEqual(seen[0], TICK, delta=TICK)

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
        self.assertLess(max(seen), TICK * 4)


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
        connection = self.raw()
        hello = connection.read_until(lambda m: m.get('t') == 'hello')
        snapshot = connection.read_until(lambda m: m.get('t') == 'snapshot')
        self.assertEqual(hello['n'], 1)
        self.assertEqual(snapshot['n'], 2)

    def test_each_player_is_counted_separately(self):
        """
        Plenty of what the server sends goes to everyone but one person, so a
        count shared across the room would show gaps that mean nothing.
        """
        first = self.raw()
        first.read_until(lambda m: m.get('t') == 'snapshot')
        second = self.raw()
        hello = second.read_until(lambda m: m.get('t') == 'hello')
        self.assertEqual(hello['n'], 1)         # its own count, not the room's


class ResyncTest(StateSyncFixture):
    """A player who has missed something asks for the world and gets it."""

    class Counting(Room):
        def start(self):
            self.state['score'] = 0

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
        cls.room_class = _load_room('net_ships', 'Arena')
        sys.path.remove(EXAMPLES_DIR)
        sys.modules.pop('net_ships', None)

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
        hello = connection.read_until(lambda message: message.get('t') == 'hello')
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
        self.assert_serves('net_ships:Arena', EXAMPLES_DIR)

    def test_serves_the_pong_demo(self):
        self.assert_serves('net_pong:Pong', EXAMPLES_DIR)


if __name__ == '__main__':
    unittest.main()
