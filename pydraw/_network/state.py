"""Recursive tracked and read-only containers used by pydraw.network."""

from pydraw.errors import PydrawError


class _Changes:
    """The set of top-level keys written since the server last collected them."""

    __slots__ = ('keys', '_notify')

    def __init__(self, notify=None):
        self.keys = set()
        self._notify = notify

    def mark(self, key) -> None:
        """Record one owner key and notify an optional non-server consumer."""
        self.keys.add(key)
        if self._notify is not None:
            self._notify()

    def take(self) -> set:
        """Hand over what has changed and start counting again."""
        keys, self.keys = self.keys, set()
        return keys


def _track(value, changes: _Changes, key, refusal: str = None):
    """
    Recursively wrap values for change tracking or read-only access.
    """
    if isinstance(value, dict):
        tracked = _TrackedDict(changes, key, refusal)
        for inner_key, inner in value.items():
            owner = inner_key if key is None else key
            dict.__setitem__(
                tracked, inner_key,
                _track(inner, changes, owner, refusal),
            )
        return tracked
    if isinstance(value, list):
        tracked = _TrackedList(changes, key, refusal)
        list.extend(
            tracked,
            (_track(inner, changes, key, refusal) for inner in value),
        )
        return tracked
    if isinstance(value, tuple):
        # A tuple cannot change shape, but it can contain a mutable dict/list.
        return tuple(_track(inner, changes, key, refusal) for inner in value)
    return value                                      # an atomic network value


def _readonly(value, refusal: str):
    """A recursively read-only network value, still made of dicts and lists."""
    return _track(value, None, None, refusal)


class _TrackedDict(dict):
    """
    A dict that reports writes by top-level key or refuses them.
    """

    __slots__ = ('_changes', '_key', '_refusal')

    def __init__(self, changes: _Changes, key, refusal: str = None):
        dict.__init__(self)
        self._changes = changes
        self._key = key
        self._refusal = refusal

    def _writable(self) -> None:
        if self._refusal is not None:
            raise PydrawError(self._refusal)

    def _owner(self, key):
        return key if self._key is None else self._key

    def _mark(self, key) -> None:
        if self._changes is not None:
            self._changes.mark(self._owner(key))

    def __setitem__(self, key, value):
        self._writable()
        dict.__setitem__(
            self, key,
            _track(value, self._changes, self._owner(key), self._refusal),
        )
        self._mark(key)

    def __delitem__(self, key):
        self._writable()
        dict.__delitem__(self, key)
        self._mark(key)

    def pop(self, key, *default):
        self._writable()
        had = key in self
        value = dict.pop(self, key, *default)
        if had:
            self._mark(key)
        return value

    def popitem(self):
        self._writable()
        key, value = dict.popitem(self)
        self._mark(key)
        return key, value

    def setdefault(self, key, default=None):
        self._writable()
        if key not in self:
            self[key] = default                    # wraps and marks
        return dict.__getitem__(self, key)

    def update(self, *args, **kwargs):
        self._writable()
        for key, value in dict(*args, **kwargs).items():
            self[key] = value

    def clear(self):
        self._writable()
        keys = list(self)
        dict.clear(self)
        for key in keys:
            self._mark(key)

    def __ior__(self, other):
        self._writable()
        self.update(other)
        return self


class _TrackedList(list):
    """A list that either reports writes or refuses them at every depth."""

    __slots__ = ('_changes', '_key', '_refusal')

    def __init__(self, changes: _Changes, key, refusal: str = None):
        list.__init__(self)
        self._changes = changes
        self._key = key
        self._refusal = refusal

    def _writable(self) -> None:
        if self._refusal is not None:
            raise PydrawError(self._refusal)

    def _mark(self) -> None:
        if self._changes is not None:
            self._changes.mark(self._key)

    def _wrap(self, value):
        return _track(value, self._changes, self._key, self._refusal)

    def __setitem__(self, index, value):
        self._writable()
        if isinstance(index, slice):
            value = [self._wrap(item) for item in value]
        else:
            value = self._wrap(value)
        list.__setitem__(self, index, value)
        self._mark()

    def __delitem__(self, index):
        self._writable()
        list.__delitem__(self, index)
        self._mark()

    def append(self, value):
        self._writable()
        list.append(self, self._wrap(value))
        self._mark()

    def insert(self, index, value):
        self._writable()
        list.insert(self, index, self._wrap(value))
        self._mark()

    def extend(self, values):
        self._writable()
        list.extend(self, (self._wrap(value) for value in values))
        self._mark()

    def remove(self, value):
        self._writable()
        list.remove(self, value)
        self._mark()

    def pop(self, index=-1):
        self._writable()
        value = list.pop(self, index)
        self._mark()
        return value

    def clear(self):
        self._writable()
        list.clear(self)
        self._mark()

    def sort(self, *args, **kwargs):
        self._writable()
        list.sort(self, *args, **kwargs)
        self._mark()

    def reverse(self):
        self._writable()
        list.reverse(self)
        self._mark()

    def __iadd__(self, other):
        self._writable()
        self.extend(other)
        return self

    def __imul__(self, count):
        self._writable()
        list.__imul__(self, count)
        self._mark()
        return self
