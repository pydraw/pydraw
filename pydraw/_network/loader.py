"""Load a Room from a one-file pydraw game without running its client half."""

import builtins
import contextlib
import importlib
import importlib.util
import sys
import types

from pydraw.errors import PydrawError


CLIENT_ONLY = ('Screen', 'Network')


def _client_boundary(tree: 'ast.Module'):
    """Return the first top-level statement belonging to the client half."""
    import ast

    for position, node in enumerate(tree.body):
        if isinstance(node, (ast.While, ast.For)):
            return position
        for inner in ast.walk(node):
            if isinstance(inner, ast.Name) and inner.id in CLIENT_ONLY:
                return position
    return None


def _describe(node: 'ast.stmt', source_lines: list) -> str:
    """The source text of a statement's first line, for pointing at it."""
    return source_lines[node.lineno - 1].strip()


def _globals_read(code, seen=None):
    """Every module-level name a code object reads, including nested code."""
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
    """Raised by the stand-in Screen if a line we didn't spot opens one."""


def _window_opened(class_name: str, origin: str) -> PydrawError:
    return PydrawError(
        f'net: loading {class_name} from {origin} tried to open a game window. '
        f'Some line the loader could not see builds a Screen -- move the Room above '
        f'it, or give the Room a file of its own (arena.py) and serve that instead.'
    )


def _no_screen(*args, **kwargs):
    """Stand in for Screen while a Room is being loaded on a server."""
    raise _ClientHalfReached()


@contextlib.contextmanager
def _server_side(origin: str):
    """Run game setup with client arguments and Screen creation hidden."""
    # Imported here to avoid pulling pydraw back into itself during package import.
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
    Load a Room without running the client half of a one-file game.

    Only statements above the first Screen or Network are executed.
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
        return getattr(importlib.import_module(module_name), class_name)

    with open(origin, 'r') as source_file:
        source = source_file.read()
    tree = ast.parse(source, origin)
    source_lines = source.splitlines()

    boundary = _client_boundary(tree)
    if boundary is None:
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
    """Explain globals a Room needs but the server-side prelude cannot reach."""
    lines = _top_level_lines(tree)
    wanted = set()
    for value in vars(room_class).values():
        method = getattr(value, '__func__', value)
        method = getattr(method, 'fget', method)
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
    """`python -m pydraw.network module:RoomClass [port]`."""
    # Delay the circular import until the public module is complete.
    from pydraw.network import DEFAULT_PORT, serve

    if not argv:
        print('usage: python -m pydraw.network module:RoomClass [port]')
        return

    target = argv[0]
    port = int(argv[1]) if len(argv) > 1 else DEFAULT_PORT

    if ':' not in target:
        print('expected module:RoomClass, e.g. pong:Pong')
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
