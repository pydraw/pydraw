"""
pydraw.serial -- turning pydraw's own value types into JSON and back.

Nothing here knows about networking. json.dumps takes `default=encode` and
json.loads takes `object_hook=decode`; anything else that wants to write a value
to a file gets the same for free.
"""

__all__ = ['serializable', 'encode', 'decode', 'is_serializable', 'TAG', 'VALUE']

# Short, because these ride along with every value that uses them. '~' is not a
# character anybody puts in a state key by accident, and a game that does is still
# safe -- see decode().
TAG = '~'
VALUE = 'v'

#: tag name -> the class that answers to it, filled in by @serializable
_TYPES = {}


def serializable(cls=None, *, name: str = None):
    """
    Register a value type as something pydraw can send and rebuild.

    Usable bare (@serializable) or with a name (@serializable(name='Color')). The
    name is what travels, so it is the thing to keep stable -- renaming the class
    is free, renaming the tag is a change to the wire.
    """

    def register(target):
        for required in ('__serialize__', '__deserialize__'):
            if not hasattr(target, required):
                raise TypeError(
                    f'{target.__name__} cannot be serializable without '
                    f'{required}(); see pydraw/serial.py for the two methods.')

        tag = name if name is not None else target.__name__
        existing = _TYPES.get(tag)
        if existing is not None and existing is not target:
            raise TypeError(
                f'two classes both want to travel as {tag!r}: '
                f'{existing.__name__} and {target.__name__}. Give one of them '
                f'@serializable(name=...) of its own.')

        _TYPES[tag] = target
        return target

    return register if cls is None else register(cls)


def is_serializable(value) -> bool:
    """Whether this particular object can go on the wire and come back itself."""
    return type(value) in _TYPES.values()


def encode(value):
    """
    json.dumps(default=...): a registered value as the tagged form.

    json only calls this for what it could not handle itself, so numbers, strings
    and containers never reach here and pay nothing.
    """
    for tag, cls in _TYPES.items():
        if type(value) is cls:
            return {TAG: tag, VALUE: value.__serialize__()}

    # The thing they actually want is for each player to draw one of their own, we don't encourage
    # the lazy way of just trying to serialize the renderables themselves.
    if hasattr(value, '_screen'):
        advice = ('a sprite belongs to the screen it was drawn on, and every other '
                  'player has a screen of their own -- send what they need to draw '
                  'it (a position, a size, a color) rather than the object')
    else:
        advice = ('only numbers, strings, lists, dicts and pydraw values (Color, '
                  'Location) can go on the wire')

    raise TypeError(f'a {type(value).__name__} cannot be sent to other '
                    f'players: {advice}.')


def decode(mapping: dict):
    """
    json.loads(object_hook=...): the tagged form back into the real thing.

    Deliberately fussy. This runs on every dict that arrives, including ones a game
    made itself, so it rebuilds only what is exactly the shape encode() writes and
    names a type we actually know. A game whose own state happens to hold a '~' key
    is left alone rather than mangled.
    """
    if len(mapping) != 2 or TAG not in mapping or VALUE not in mapping:
        return mapping

    cls = _TYPES.get(mapping[TAG])
    if cls is None:
        return mapping

    try:
        return cls.__deserialize__(mapping[VALUE])
    except Exception:                                        # noqa: BLE001
        # Rebuilding failed, so the payload is not what this tag promised. Handing
        # back the plain dict keeps one odd value from ending the whole game.
        return mapping
