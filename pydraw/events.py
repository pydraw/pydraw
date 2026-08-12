"""Platform-neutral input events."""

from typing import NamedTuple


class InputEvent(NamedTuple):
    kind: str
    position: object
    button: object
    key: object


__all__ = ['InputEvent']
