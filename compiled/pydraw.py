"""
pyDraw v2.2.1

This library is a graphics-interface library designed to make graphics in Python
easier and more simple. It was designed to be easy to teach/learn and to utilize
some of the basic concepts of OOP and functional programming in its setup.

Documentation: https://docs.pydraw.graphics
Source: https://github.com/pydraw/pydraw

(Author: Noah Coetsee)

No hiding spots here (for semicolons)
Hide and seek champion since version 0.1.0

Semicolons are my best friends.
"""



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#       OVERLOAD UTILITY          #
# (adapted from multipledispatch) #
#     modified by Noah Coetsee    #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

"""
Creates an "@overload" annotation to allow for the dispatch of multiple various method headers.
Modified to create more accomodating error messages for pyDraw users and for small feature changes.
"""

# UTILS
from collections import OrderedDict


def raises(err, lamda):
    try:
        lamda()
        return False
    except err:
        return True


def expand_tuples(L):
    """
    >>> expand_tuples([1, (2, 3)])
    [(1, 2), (1, 3)]
    >>> expand_tuples([1, 2])
    [(1, 2)]
    """
    if not L:
        return [()]
    elif not isinstance(L[0], tuple):
        rest = expand_tuples(L[1:])
        return [(L[0],) + t for t in rest]
    else:
        rest = expand_tuples(L[1:])
        return [(item,) + t for t in rest for item in L[0]]


# Taken from theano/theano/gof/sched.py
# Avoids licensing issues because this was written by Matthew Rocklin
def _toposort(edges):
    """ Topological sort algorithm by Kahn [1] - O(nodes + vertices)
    inputs:
        edges - a dict of the form {a: {b, c}} where b and c depend on a
    outputs:
        L - an ordered list of nodes that satisfy the dependencies of edges
    >>> _toposort({1: (2, 3), 2: (3, )})
    [1, 2, 3]
    Closely follows the wikipedia page [2]
    [1] Kahn, Arthur B. (1962), "Topological sorting of large networks",
    Communications of the ACM
    [2] http://en.wikipedia.org/wiki/Toposort#Algorithms
    """
    incoming_edges = reverse_dict(edges)
    incoming_edges = OrderedDict((k, set(val))
                                 for k, val in incoming_edges.items())
    S = OrderedDict.fromkeys(v for v in edges if v not in incoming_edges)
    L = []

    while S:
        n, _ = S.popitem()
        L.append(n)
        for m in edges.get(n, ()):
            assert n in incoming_edges[m]
            incoming_edges[m].remove(n)
            if not incoming_edges[m]:
                S[m] = None
    if any(incoming_edges.get(v, None) for v in edges):
        raise ValueError("Input has cycles")
    return L


def reverse_dict(d):
    """Reverses direction of dependence dict
    >>> d = {'a': (1, 2), 'b': (2, 3), 'c':()}
    >>> reverse_dict(d)  # doctest: +SKIP
    {1: ('a',), 2: ('a', 'b'), 3: ('b',)}

    :note: dict order are not deterministic. As we iterate on the
        input dict, it make the output of this function depend on the
        dict order. So this function output order should be considered
        as undeterministic.
    """
    result = OrderedDict()
    for key in d:
        for val in d[key]:
            result[val] = result.get(val, tuple()) + (key,)
    return result


# Taken from toolz
# Avoids licensing issues because this version was authored by Matthew Rocklin
def groupby(func, seq):
    """ Group a collection by a key function
    >>> names = ['Alice', 'Bob', 'Charlie', 'Dan', 'Edith', 'Frank']
    >>> groupby(len, names)  # doctest: +SKIP
    {3: ['Bob', 'Dan'], 5: ['Alice', 'Edith', 'Frank'], 7: ['Charlie']}
    >>> iseven = lambda x: x % 2 == 0
    >>> groupby(iseven, [1, 2, 3, 4, 5, 6, 7, 8])  # doctest: +SKIP
    {False: [1, 3, 5, 7], True: [2, 4, 6, 8]}
    See Also:
        ``countby``
    """

    d = OrderedDict()
    for item in seq:
        key = func(item)
        if key not in d:
            d[key] = list()
        d[key].append(item)
    return d


def typename(type):
    """Get the name of `type`.
    Parameters
    ----------
    type : Union[Type, Tuple[Type]]
    Returns
    -------
    str
        The name of `type` or a tuple of the names of the types in `type`.
    Examples
    --------
    >>> typename(int)
    'int'
    >>> typename((int, float))
    '(int, float)'
    """
    try:
        return type.__name__
    except AttributeError:
        if len(type) == 1:
            return typename(*type)
        return '(%s)' % ', '.join(map(typename, type))


# VARIADIC


class VariadicSignatureType(type):
    # checking if subclass is a subclass of self
    def __subclasscheck__(self, subclass):
        other_type = (subclass.variadic_type if isvariadic(subclass)
                      else (subclass,))
        return subclass is self or all(
            issubclass(other, self.variadic_type) for other in other_type
        )

    def __eq__(self, other):
        """
        Return True if other has the same variadic type
        Parameters
        ----------
        other : object (type)
            The object (type) to check
        Returns
        -------
        bool
            Whether or not `other` is equal to `self`
        """
        return (isvariadic(other) and
                set(self.variadic_type) == set(other.variadic_type))

    def __hash__(self):
        return hash((type(self), frozenset(self.variadic_type)))


def isvariadic(obj):
    """Check whether the type `obj` is variadic.
    Parameters
    ----------
    obj : type
        The type to check
    Returns
    -------
    bool
        Whether or not `obj` is variadic
    Examples
    --------
    >>> isvariadic(int)
    False
    >>> isvariadic(Variadic[int])
    True
    """
    return isinstance(obj, VariadicSignatureType)


class VariadicSignatureMeta(type):
    """A metaclass that overrides ``__getitem__`` on the class. This is used to
    generate a new type for Variadic signatures. See the Variadic class for
    examples of how this behaves.
    """

    def __getitem__(self, variadic_type):
        if not (isinstance(variadic_type, (type, tuple)) or type(variadic_type)):
            raise ValueError("Variadic types must be type or tuple of types"
                             " (Variadic[int] or Variadic[(int, float)]")

        if not isinstance(variadic_type, tuple):
            variadic_type = variadic_type,
        return VariadicSignatureType(
            'Variadic[%s]' % typename(variadic_type),
            (),
            dict(variadic_type=variadic_type, __slots__=())
        )


class Variadic(metaclass=VariadicSignatureMeta):
    """A class whose getitem method can be used to generate a new type
    representing a specific variadic signature.
    Examples
    --------
    >>> Variadic[int]  # any number of int arguments
    <class 'multipledispatch.variadic.Variadic[int]'>
    >>> Variadic[(int, str)]  # any number of one of int or str arguments
    <class 'multipledispatch.variadic.Variadic[(int, str)]'>
    >>> issubclass(int, Variadic[int])
    True
    >>> issubclass(int, Variadic[(int, str)])
    True
    >>> issubclass(str, Variadic[(int, str)])
    True
    >>> issubclass(float, Variadic[(int, str)])
    False
    """


class AmbiguityWarning(Warning):
    pass


# CONFLICT


def supercedes(a, b):
    """ A is consistent and strictly more specific than B """
    if len(a) < len(b):
        # only case is if a is empty and b is variadic
        return not a and len(b) == 1 and isvariadic(b[-1])
    elif len(a) == len(b):
        return all(map(issubclass, a, b))
    else:
        # len(a) > len(b)
        p1 = 0
        p2 = 0
        while p1 < len(a) and p2 < len(b):
            cur_a = a[p1]
            cur_b = b[p2]
            if not (isvariadic(cur_a) or isvariadic(cur_b)):
                if not issubclass(cur_a, cur_b):
                    return False
                p1 += 1
                p2 += 1
            elif isvariadic(cur_a):
                assert p1 == len(a) - 1
                return p2 == len(b) - 1 and issubclass(cur_a, cur_b)
            elif isvariadic(cur_b):
                assert p2 == len(b) - 1
                if not issubclass(cur_a, cur_b):
                    return False
                p1 += 1
        return p2 == len(b) - 1 and p1 == len(a)


def consistent(a, b):
    """ It is possible for an argument list to satisfy both A and B """

    # Need to check for empty args
    if not a:
        return not b or isvariadic(b[0])
    if not b:
        return not a or isvariadic(a[0])

    # Non-empty args check for mutual subclasses
    if len(a) == len(b):
        return all(issubclass(aa, bb) or issubclass(bb, aa)
                   for aa, bb in zip(a, b))
    else:
        p1 = 0
        p2 = 0
        while p1 < len(a) and p2 < len(b):
            cur_a = a[p1]
            cur_b = b[p2]
            if not issubclass(cur_b, cur_a) and not issubclass(cur_a, cur_b):
                return False
            if not (isvariadic(cur_a) or isvariadic(cur_b)):
                p1 += 1
                p2 += 1
            elif isvariadic(cur_a):
                p2 += 1
            elif isvariadic(cur_b):
                p1 += 1
        # We only need to check for variadic ends
        # Variadic types are guaranteed to be the last element
        return (isvariadic(cur_a) and p2 == len(b) or
                isvariadic(cur_b) and p1 == len(a))


def ambiguous(a, b):
    """ A is consistent with B but neither is strictly more specific """
    return consistent(a, b) and not (supercedes(a, b) or supercedes(b, a))


def ambiguities(signatures):
    """ All signature pairs such that A is ambiguous with B """
    signatures = list(map(tuple, signatures))
    return set((a, b) for a in signatures for b in signatures
               if hash(a) < hash(b)
               and ambiguous(a, b)
               and not any(supercedes(c, a) and supercedes(c, b)
                           for c in signatures))


def super_signature(signatures):
    """ A signature that would break ambiguities """
    n = len(signatures[0])
    assert all(len(s) == n for s in signatures)

    return [max([type.mro(sig[i]) for sig in signatures], key=len)[0]
            for i in range(n)]


def edge(a, b, tie_breaker=hash):
    """ A should be checked before B
    Tie broken by tie_breaker, defaults to ``hash``
    """
    # A either supercedes B and B does not supercede A or if B does then call
    # tie_breaker
    return supercedes(a, b) and (
            not supercedes(b, a) or tie_breaker(a) > tie_breaker(b)
    )


def ordering(signatures):
    """ A sane ordering of signatures to check, first to last
    Topoological sort of edges as given by ``edge`` and ``supercedes``
    """
    signatures = list(map(tuple, signatures))
    edges = [(a, b) for a in signatures for b in signatures if edge(a, b)]
    edges = groupby(lambda x: x[0], edges)
    for s in signatures:
        if s not in edges:
            edges[s] = []
    edges = dict((k, [b for a, b in v]) for k, v in edges.items())
    return _toposort(edges)


# DISPATCHER
from warnings import warn
import inspect
import itertools as itl


class MDNotImplementedError(NotImplementedError):
    """ A NotImplementedError for multiple dispatch """


def ambiguity_warn(dispatcher, ambiguities):
    """ Raise warning when ambiguity is detected
    Parameters
    ----------
    dispatcher : Dispatcher
        The dispatcher on which the ambiguity was detected
    ambiguities : set
        Set of type signature pairs that are ambiguous within this dispatcher
    See Also:
        Dispatcher.add
        warning_text
    """
    warn(warning_text(dispatcher.name, ambiguities), AmbiguityWarning)


def halt_ordering():
    """Deprecated interface to temporarily disable ordering.
    """
    warn(
        'halt_ordering is deprecated, you can safely remove this call.',
        DeprecationWarning,
    )


def restart_ordering(on_ambiguity=ambiguity_warn):
    """Deprecated interface to temporarily resume ordering.
    """
    warn(
        'restart_ordering is deprecated, if you would like to eagerly order'
        'the dispatchers, you should call the ``reorder()`` method on each'
        ' dispatcher.',
        DeprecationWarning,
    )


def variadic_signature_matches_iter(types, full_signature):
    """Check if a set of input types matches a variadic signature.
    Notes
    -----
    The algorithm is as follows:
    Initialize the current signature to the first in the sequence
    For each type in `types`:
        If the current signature is variadic
            If the type matches the signature
                yield True
            Else
                Try to get the next signature
                If no signatures are left we can't possibly have a match
                    so yield False
        Else
            yield True if the type matches the current signature
            Get the next signature
    """
    sigiter = iter(full_signature)
    sig = next(sigiter)
    for typ in types:
        matches = issubclass(typ, sig)
        yield matches
        if not isvariadic(sig):
            # we're not matching a variadic argument, so move to the next
            # element in the signature
            sig = next(sigiter)
    else:
        try:
            sig = next(sigiter)
        except StopIteration:
            assert isvariadic(sig)
            yield True
        else:
            # We have signature items left over, so all of our arguments
            # haven't matched
            yield False


def variadic_signature_matches(types, full_signature):
    # No arguments always matches a variadic signature
    assert full_signature
    return all(variadic_signature_matches_iter(types, full_signature))


class Dispatcher(object):
    """ Dispatch methods based on type signature
    Use ``dispatch`` to add implementations
    Examples
    --------
    >>> @overload(int)
    ... def f(x):
    ...     return x + 1
    >>> @overload(float)
    ... def f(x):
    ...     return x - 1
    >>> f(3)
    4
    >>> f(3.0)
    2.0
    """
    __slots__ = '__name__', 'name', 'funcs', '_ordering', '_cache', 'doc', '_min_args'

    def __init__(self, name, doc=None):
        self.name = self.__name__ = name
        self.funcs = {}
        self.doc = doc

        self._cache = {}
        # signature -> number of leading required (non-default) parameters,
        # so a call with fewer args can still match when the omitted trailing
        # parameters are optional. See dispatch_iter().
        self._min_args = {}

    def register(self, *types, **kwargs):
        """ register dispatcher with new implementation
        >>> f = Dispatcher('f')
        >>> @f.register(int)
        ... def inc(x):
        ...     return x + 1
        >>> @f.register(float)
        ... def dec(x):
        ...     return x - 1
        >>> @f.register(list)
        ... @f.register(tuple)
        ... def reverse(x):
        ...     return x[::-1]
        >>> f(1)
        2
        >>> f(1.0)
        0.0
        >>> f([1, 2, 3])
        [3, 2, 1]
        """

        def _df(func):
            self.add(types, func, **kwargs)
            return func

        return _df

    @classmethod
    def get_func_params(cls, func):
        if hasattr(inspect, "signature"):
            sig = inspect.signature(func)
            return sig.parameters.values()

    @classmethod
    def get_func_annotations(cls, func):
        """ get annotations of function positional parameters
        """
        params = cls.get_func_params(func)
        if params:
            Parameter = inspect.Parameter

            params = (param for param in params
                      if param.kind in
                      (Parameter.POSITIONAL_ONLY,
                       Parameter.POSITIONAL_OR_KEYWORD))

            annotations = tuple(
                param.annotation
                for param in params)

            if all(ann is not Parameter.empty for ann in annotations):
                return annotations

    @classmethod
    def _required_arg_count(cls, func):
        """ Count leading positional parameters that have no default.

        These are the arguments a caller must supply; parameters after them are
        optional, which lets a shorter call match a longer signature. Returns
        None if the function's signature can't be introspected.
        """
        params = cls.get_func_params(func)
        if params is None:
            return None

        Parameter = inspect.Parameter
        count = 0
        for param in params:
            if param.kind in (Parameter.POSITIONAL_ONLY,
                              Parameter.POSITIONAL_OR_KEYWORD):
                if param.default is Parameter.empty:
                    count += 1
        return count

    def add(self, signature, func):
        """ Add new types/method pair to dispatcher
        >>> D = Dispatcher('add')
        >>> D.add((int, int), lambda x, y: x + y)
        >>> D.add((float, float), lambda x, y: x + y)
        >>> D(1, 2)
        3
        >>> D(1, 2.0)
        Traceback (most recent call last):
        ...
        NotImplementedError: Could not find signature for add: <int, float>
        When ``add`` detects a warning it calls the ``on_ambiguity`` callback
        with a dispatcher/itself, and a set of ambiguous type signature pairs
        as inputs.  See ``ambiguity_warn`` for an example.
        """
        # Handle annotations
        if not signature:
            annotations = self.get_func_annotations(func)
            if annotations:
                signature = annotations

        # Handle union types
        if any(isinstance(typ, tuple) for typ in signature):
            for typs in expand_tuples(signature):
                self.add(typs, func)
            return

        new_signature = []

        for index, typ in enumerate(signature, start=1):
            if not isinstance(typ, (type, list)):
                str_sig = ', '.join(c.__name__ if isinstance(c, type)
                                    else str(c) for c in signature)
                raise TypeError("Tried to dispatch on non-type: %s\n"
                                "In signature: <%s>\n"
                                "In function: %s" %
                                (typ, str_sig, self.name))

            # handle variadic signatures
            if isinstance(typ, list):
                if index != len(signature):
                    raise TypeError(
                        'Variadic signature must be the last element'
                    )

                if len(typ) != 1:
                    raise TypeError(
                        'Variadic signature must contain exactly one element. '
                        'To use a variadic union type place the desired types '
                        'inside of a tuple, e.g., [(int, str)]'
                    )
                new_signature.append(Variadic[typ[0]])
            else:
                new_signature.append(typ)

        sig = tuple(new_signature)
        self.funcs[sig] = func
        required = self._required_arg_count(func)
        # Fall back to the full length (exact-match only) when introspection
        # fails, so an un-inspectable func never gains looser matching.
        self._min_args[sig] = required if required is not None else len(sig)
        self._cache.clear()

        try:
            del self._ordering
        except AttributeError:
            pass

    @property
    def ordering(self):
        try:
            return self._ordering
        except AttributeError:
            return self.reorder()

    def reorder(self, on_ambiguity=ambiguity_warn):
        self._ordering = od = ordering(self.funcs)
        amb = ambiguities(self.funcs)
        if amb:
            on_ambiguity(self, amb)
        return od

    def __call__(self, *args, **kwargs):
        types = tuple([type(arg) for arg in args])
        try:
            func = self._cache[types]
        except KeyError:
            func = self.dispatch(*types)
            if not func:
                raise NotImplementedError(
                    'Could not find signature for %s: <%s>' %
                    (self.name, str_signature(types)))
            self._cache[types] = func
        try:
            return func(*args, **kwargs)

        except MDNotImplementedError:
            funcs = self.dispatch_iter(*types)
            next(funcs)  # burn first
            for func in funcs:
                try:
                    return func(*args, **kwargs)
                except MDNotImplementedError:
                    pass

            raise NotImplementedError(
                "Matching functions for "
                "%s: <%s> found, but none completed successfully" % (
                    self.name, str_signature(types),
                ),
            )

    def __str__(self):
        return "<dispatched %s>" % self.name

    __repr__ = __str__

    def dispatch(self, *types):
        """Deterimine appropriate implementation for this type signature
        This method is internal.  Users should call this object as a function.
        Implementation resolution occurs within the ``__call__`` method.
        >>> @overload(int)
        ... def inc(x):
        ...     return x + 1
        >>> implementation = inc.dispatch(int)
        >>> implementation(3)
        4
        >>> print(inc.dispatch(float))
        None
        See Also:
          ``multipledispatch.conflict`` - module to determine resolution order
        """

        if types in self.funcs:
            return self.funcs[types]

        try:
            return next(self.dispatch_iter(*types))
        except StopIteration:
            return None

    def dispatch_iter(self, *types):

        n = len(types)
        for signature in self.ordering:
            if len(signature) == n and all(map(issubclass, types, signature)):
                result = self.funcs[signature]
                yield result
            elif len(signature) and isvariadic(signature[-1]):
                if variadic_signature_matches(types, signature):
                    result = self.funcs[signature]
                    yield result

        # Default-honoring fallback: allow a call to match a *longer* signature
        # when the omitted trailing parameters are optional (have defaults) and
        # the supplied prefix matches. This is strictly additive -- it only ever
        # considers signatures longer than the call (len > n), which the passes
        # above never match, so no existing dispatch result changes.
        for signature in self.ordering:
            m = len(signature)
            if m <= n or isvariadic(signature[-1]):
                continue
            if self._min_args.get(signature, m) <= n and \
                    all(issubclass(typ, sig) for typ, sig in zip(types, signature)):
                yield self.funcs[signature]

    def resolve(self, types):
        """ Deterimine appropriate implementation for this type signature
        .. deprecated:: 0.4.4
            Use ``dispatch(*types)`` instead
        """
        warn("resolve() is deprecated, use dispatch(*types)",
             DeprecationWarning)

        return self.dispatch(*types)

    def __getstate__(self):
        return {'name': self.name,
                'funcs': self.funcs}

    def __setstate__(self, d):
        self.name = d['name']
        self.funcs = d['funcs']
        self._ordering = ordering(self.funcs)
        self._cache = dict()
        self._min_args = {}
        for sig, func in self.funcs.items():
            required = self._required_arg_count(func)
            self._min_args[sig] = required if required is not None else len(sig)

    @property
    def __doc__(self):
        docs = ["Multiply dispatched method: %s" % self.name]

        if self.doc:
            docs.append(self.doc)

        other = []
        for sig in self.ordering[::-1]:
            func = self.funcs[sig]
            if func.__doc__:
                s = 'Inputs: <%s>\n' % str_signature(sig)
                s += '-' * len(s) + '\n'
                s += func.__doc__.strip()
                docs.append(s)
            else:
                other.append(str_signature(sig))

        if other:
            docs.append('Other signatures:\n    ' + '\n    '.join(other))

        return '\n\n'.join(docs)

    def _help(self, *args):
        return self.dispatch(*map(type, args)).__doc__

    def help(self, *args, **kwargs):
        """ Print docstring for the function corresponding to inputs """
        print(self._help(*args))

    def _source(self, *args):
        func = self.dispatch(*map(type, args))
        if not func:
            raise TypeError("No function found")
        return source(func)

    def source(self, *args, **kwargs):
        """ Print source code for the function corresponding to inputs """
        print(self._source(*args))


def source(func):
    s = 'File: %s\n\n' % inspect.getsourcefile(func)
    s = s + inspect.getsource(func)
    return s


class MethodDispatcher(Dispatcher):
    """ Dispatch methods based on type signature
    See Also:
        Dispatcher
    """
    __slots__ = ('obj', 'cls')

    @classmethod
    def get_func_params(cls, func):
        if hasattr(inspect, "signature"):
            sig = inspect.signature(func)
            return itl.islice(sig.parameters.values(), 1, None)

    def __get__(self, instance, owner):
        self.obj = instance
        self.cls = owner
        return self

    def __call__(self, *args, **kwargs):
        types = tuple([type(arg) for arg in args])
        func = self.dispatch(*types)
        if not func:
            raise NotImplementedError('Could not find signature for %s: <%s>' %
                                      (self.name, str_signature(types)))
        return func(self.obj, *args, **kwargs)


def str_signature(sig):
    """ String representation of type signature
    >>> str_signature((int, float))
    'int, float'
    """
    return ', '.join(cls.__name__ for cls in sig)


def warning_text(name, amb):
    """ The text for ambiguity warnings """
    text = "\nAmbiguities exist in dispatched function %s\n\n" % (name)
    text += "The following signatures may result in ambiguous behavior:\n"
    for pair in amb:
        text += "\t" + \
                ', '.join('[' + str_signature(s) + ']' for s in pair) + "\n"
    text += "\n\nConsider making the following additions:\n\n"
    text += '\n\n'.join(['@overload(' + str_signature(super_signature(s))
                         + ')\ndef %s(...)' % name for s in amb])
    return text


# CORE
import sys

global_namespace = dict()


def overload(*types, **kwargs):
    """ Dispatch function on the types of the inputs
    Supports dispatch on all non-keyword arguments.
    Collects implementations based on the function name.  Ignores namespaces.
    If ambiguous type signatures occur a warning is raised when the function is
    defined suggesting the additional method to break the ambiguity.
    Examples
    --------
    >>> @overload(int)
    ... def f(x):
    ...     return x + 1
    >>> @overload(float)
    ... def f(x):
    ...     return x - 1
    >>> f(3)
    4
    >>> f(3.0)
    2.0
    Specify an isolated namespace with the namespace keyword argument
    >>> my_namespace = dict()
    >>> @overload(int, namespace=my_namespace)
    ... def foo(x):
    ...     return x + 1
    Dispatch on instance methods within classes
    >>> class MyClass(object):
    ...     @overload(list)
    ...     def __init__(self, data):
    ...         self.data = data
    ...     @overload(int)
    ...     def __init__(self, datum):
    ...         self.data = [datum]
    """
    namespace = kwargs.get('namespace', global_namespace)

    types = tuple(types)

    def _df(func):
        name = func.__name__

        if ismethod(func):
            dispatcher = inspect.currentframe().f_back.f_locals.get(
                name,
                MethodDispatcher(name),
            )
        else:
            if name not in namespace:
                namespace[name] = Dispatcher(name)
            dispatcher = namespace[name]

        dispatcher.add(types, func)
        return dispatcher

    return _df


def ismethod(func):
    """ Is func a method?
    Note that this has to work as the method is defined but before the class is
    defined.  At this stage methods look like functions.
    """
    if hasattr(inspect, "signature"):
        signature = inspect.signature(func)
        return signature.parameters.get('self', None) is not None
    else:
        if sys.version_info.major < 3:
            spec = inspect.getargspec(func)
        else:
            spec = inspect.getfullargspec(func)
        return spec and spec.args and spec.args[0] == 'self'

class InvalidArgumentError(ValueError):
    pass


class UnsupportedError(NameError):
    pass


class PydrawError(NameError):
    pass

# from pydraw.errors import *


def verify_type(obj, required_type):
    """
    Verifies an objects type is the passed type

    :param obj: the object to check
    :param required_type: the expected type
    :return: True if required type is present or obj is None, else False
    """

    if type(required_type) is tuple and len(required_type) > 0:
        if obj is None:
            return True

        for allowed_type in required_type:
            if type(obj) is allowed_type:
                return True

    return type(obj) is required_type or obj is None


def verify(*args):
    """
    Takes a list of values and expected types and returns if all objects meet their expected types.

    :param args: a list of objects and types, ex: (some_number, float, some_location, Location)
    :return: True if all args meet their expected types, throws an error if not.
    """
    if len(args) % 2 != 0:
        raise InvalidArgumentError(
            'verify(): arguments must be provided as object/type pairs.'
        )

    for i in range(0, len(args), 2):
        obj = args[i]
        expected_type = args[i+1]
        # print(f'Obj: {obj}, Expected Type: {expected_type}, Meets: {verify_type(obj, expected_type)}')

        if not verify_type(obj, expected_type):
            raise InvalidArgumentError(
                f'verify(): expected {expected_type}; received {type(obj)} ({obj!r}).'
            )


def verify_keywords(kwargs, allowed, method: str, case_sensitive: bool = True):
    """
    Reject keywords that are not recognized by a manually parsed API.

    :param kwargs: the keyword mapping passed to the method
    :param allowed: the supported keyword names
    :param method: the method name to include in an error
    :param case_sensitive: whether keyword-name matching is case-sensitive
    """

    allowed = set(allowed)
    for keyword in kwargs:
        comparison = keyword if case_sensitive else keyword.lower()
        if comparison not in allowed:
            raise InvalidArgumentError(f"{method}: unknown keyword '{keyword}'.")

# from pydraw.errors import *


class Color:
    """
    An immutable class that contains a color values, usually by name or RGB.
    """

    NONE = None

    def __init__(self, *args):
        if len(args) == 0 or len(args) == 2 or len(args) > 3:
            raise NameError('Invalid arguments passed to color!')

        self._name = None
        self._hex_value = None

        # we should expect three-four arguments for rgb or rgba
        if len(args) >= 3:
            for arg in args:
                if type(arg) is not int:
                    raise NameError('Expected integer arguments, but found \'' + str(arg) + '\' instead.')

            self._r = args[0]
            self._g = args[1]
            self._b = args[2]

            self._mode = 0
        elif len(args) == 1:
            if type(args[0]) is tuple:
                for arg in args[0]:
                    if type(arg) is not int:
                        raise NameError('Expected integer arguments, but found \'' + str(arg) + '\' instead.')

                self._r = args[0][0]
                self._g = args[0][1]
                self._b = args[0][2]

                self._mode = 0
                return  # done: don't fall through into name/hex string parsing
            elif type(args[0]) is not str:
                raise NameError('Expected string but instead found: ' + str(args[0]))

            string = str(args[0])
            if string.startswith('#'):
                self._hex_value = string
                self._mode = 2

                rgb = self._rgb(self)
                self._r = int(rgb[0])
                self._g = int(rgb[1])
                self._b = int(rgb[2])
            else:
                self._name = string
                self._mode = 1

                if self._name == '':
                    self._r, self._g, self._b = -1, -1, -1
                else:
                    # Resolve named colors from a baked-in table
                    rgb = _COLOR_TABLE.get(self._name.strip().lower().replace(' ', ''))
                    if rgb is not None:
                        self._r, self._g, self._b = rgb
                    else:
                        rgb = self._rgb(self)
                        self._r = int(rgb[0] / 256)
                        self._g = int(rgb[1] / 256)
                        self._b = int(rgb[2] / 256)

    def __value__(self):
        """
        Retrieves the value to be interpreted internally by Turtle

        :return:
        """
        if self._mode == 0:
            return self.red(), self.green(), self.blue()
        elif self._mode == 1:
            return self._name
        else:
            return self._hex_value

    def red(self):
        """
        Get the red property.

        :return: r
        """
        return self._r

    def green(self):
        """
        Get the green property

        :return: g
        """
        return self._g

    def blue(self):
        """
        Get the blue property

        :return: b
        """
        return self._b

    def rgb(self):
        """
        Get the RGB tuple

        :return: tuple (R, G, B)
        """
        return self.red(), self.green(), self.blue()

    def name(self):
        """
        Get the name of the color (only if defined)

        :return: color or None
        """

        return self._name

    def hex(self):
        """
        Get the hex of the color (only if defined)

        :return: hex_value or None
        """
        return self._hex_value

    def clone(self):
        """
        Clone this color!

        :return: a clone.
        """

        return Color(self.__value__())

    def __str__(self):
        if self._mode == 0:
            string = f'({self._r, self._g, self._b})'
        elif self._mode == 1:
            string = self._name
        else:
            string = self._hex_value

        return string

    def __eq__(self, other):
        if type(other) is not Color:
            return False

        return other.rgb() == self.rgb()

    def __hash__(self):
        return hash(self.rgb())

    @staticmethod
    def _rgb(color) -> tuple:
        """
        Convert a color to an rgb tuple.

        :param color: the color to convert
        :return: a tuple representing RGB
        """

        if color.name() is not None:
            raise PydrawError(f"Color(): unknown color name '{color.name()}'.")
        elif color.hex() is not None:
            hexval = color.hex().replace('#', '')

            if len(hexval) != 6:
                if len(hexval) == 3:
                    hexval = ''.join([char * 2 for char in hexval])  # Optimized string manipulation.
                else:
                    raise InvalidArgumentError(
                        "Color(): hex values must contain three or six characters "
                        "(for example, '#FFF' or '#FFFFFF')."
                    )

            rgb = tuple(int(hexval[i:i + 2], 16) for i in (0, 2, 4))
        else:
            rgb = (color.red(), color.green(), color.blue())

        return rgb

    @staticmethod
    def all():
        """
        Get all color values that have a string-name.

        :return: a tuple (immutable list) of all Colors.
        """

        return tuple(COLORS.copy())

    @staticmethod
    def random():
        """
        Retrieve a random Color.

        :return: returns
        """

        import random
        return random.choice(COLORS).clone()

    def __repr__(self):
        return self.__str__()


Color.NONE = Color('')

# Static normalized-name -> (r, g, b) table (0-255) covering Tk's full color
# database, generated via winfo_rgb. Keys are lowercased with spaces stripped.
_COLOR_TABLE = {
    'aliceblue': (240, 248, 255),
    'antiquewhite': (250, 235, 215),
    'antiquewhite1': (255, 239, 219),
    'antiquewhite2': (238, 223, 204),
    'antiquewhite3': (205, 192, 176),
    'antiquewhite4': (139, 131, 120),
    'aquamarine': (127, 255, 212),
    'aquamarine1': (127, 255, 212),
    'aquamarine2': (118, 238, 198),
    'aquamarine3': (102, 205, 170),
    'aquamarine4': (69, 139, 116),
    'azure': (240, 255, 255),
    'azure1': (240, 255, 255),
    'azure2': (224, 238, 238),
    'azure3': (193, 205, 205),
    'azure4': (131, 139, 139),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'bisque1': (255, 228, 196),
    'bisque2': (238, 213, 183),
    'bisque3': (205, 183, 158),
    'bisque4': (139, 125, 107),
    'black': (0, 0, 0),
    'blanchedalmond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blue1': (0, 0, 255),
    'blue2': (0, 0, 238),
    'blue3': (0, 0, 205),
    'blue4': (0, 0, 139),
    'blueviolet': (138, 43, 226),
    'brown': (165, 42, 42),
    'brown1': (255, 64, 64),
    'brown2': (238, 59, 59),
    'brown3': (205, 51, 51),
    'brown4': (139, 35, 35),
    'burlywood': (222, 184, 135),
    'burlywood1': (255, 211, 155),
    'burlywood2': (238, 197, 145),
    'burlywood3': (205, 170, 125),
    'burlywood4': (139, 115, 85),
    'cadetblue': (95, 158, 160),
    'cadetblue1': (152, 245, 255),
    'cadetblue2': (142, 229, 238),
    'cadetblue3': (122, 197, 205),
    'cadetblue4': (83, 134, 139),
    'chartreuse': (127, 255, 0),
    'chartreuse1': (127, 255, 0),
    'chartreuse2': (118, 238, 0),
    'chartreuse3': (102, 205, 0),
    'chartreuse4': (69, 139, 0),
    'chocolate': (210, 105, 30),
    'chocolate1': (255, 127, 36),
    'chocolate2': (238, 118, 33),
    'chocolate3': (205, 102, 29),
    'chocolate4': (139, 69, 19),
    'coral': (255, 127, 80),
    'coral1': (255, 114, 86),
    'coral2': (238, 106, 80),
    'coral3': (205, 91, 69),
    'coral4': (139, 62, 47),
    'cornflowerblue': (100, 149, 237),
    'cornsilk': (255, 248, 220),
    'cornsilk1': (255, 248, 220),
    'cornsilk2': (238, 232, 205),
    'cornsilk3': (205, 200, 177),
    'cornsilk4': (139, 136, 120),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'cyan1': (0, 255, 255),
    'cyan2': (0, 238, 238),
    'cyan3': (0, 205, 205),
    'cyan4': (0, 139, 139),
    'darkblue': (0, 0, 139),
    'darkcyan': (0, 139, 139),
    'darkgoldenrod': (184, 134, 11),
    'darkgoldenrod1': (255, 185, 15),
    'darkgoldenrod2': (238, 173, 14),
    'darkgoldenrod3': (205, 149, 12),
    'darkgoldenrod4': (139, 101, 8),
    'darkgray': (169, 169, 169),
    'darkgreen': (0, 100, 0),
    'darkgrey': (169, 169, 169),
    'darkkhaki': (189, 183, 107),
    'darkmagenta': (139, 0, 139),
    'darkolivegreen': (85, 107, 47),
    'darkolivegreen1': (202, 255, 112),
    'darkolivegreen2': (188, 238, 104),
    'darkolivegreen3': (162, 205, 90),
    'darkolivegreen4': (110, 139, 61),
    'darkorange': (255, 140, 0),
    'darkorange1': (255, 127, 0),
    'darkorange2': (238, 118, 0),
    'darkorange3': (205, 102, 0),
    'darkorange4': (139, 69, 0),
    'darkorchid': (153, 50, 204),
    'darkorchid1': (191, 62, 255),
    'darkorchid2': (178, 58, 238),
    'darkorchid3': (154, 50, 205),
    'darkorchid4': (104, 34, 139),
    'darkred': (139, 0, 0),
    'darksalmon': (233, 150, 122),
    'darkseagreen': (143, 188, 143),
    'darkseagreen1': (193, 255, 193),
    'darkseagreen2': (180, 238, 180),
    'darkseagreen3': (155, 205, 155),
    'darkseagreen4': (105, 139, 105),
    'darkslateblue': (72, 61, 139),
    'darkslategray': (47, 79, 79),
    'darkslategray1': (151, 255, 255),
    'darkslategray2': (141, 238, 238),
    'darkslategray3': (121, 205, 205),
    'darkslategray4': (82, 139, 139),
    'darkslategrey': (47, 79, 79),
    'darkturquoise': (0, 206, 209),
    'darkviolet': (148, 0, 211),
    'deeppink': (255, 20, 147),
    'deeppink1': (255, 20, 147),
    'deeppink2': (238, 18, 137),
    'deeppink3': (205, 16, 118),
    'deeppink4': (139, 10, 80),
    'deepskyblue': (0, 191, 255),
    'deepskyblue1': (0, 191, 255),
    'deepskyblue2': (0, 178, 238),
    'deepskyblue3': (0, 154, 205),
    'deepskyblue4': (0, 104, 139),
    'dimgray': (105, 105, 105),
    'dimgrey': (105, 105, 105),
    'dodgerblue': (30, 144, 255),
    'dodgerblue1': (30, 144, 255),
    'dodgerblue2': (28, 134, 238),
    'dodgerblue3': (24, 116, 205),
    'dodgerblue4': (16, 78, 139),
    'firebrick': (178, 34, 34),
    'firebrick1': (255, 48, 48),
    'firebrick2': (238, 44, 44),
    'firebrick3': (205, 38, 38),
    'firebrick4': (139, 26, 26),
    'floralwhite': (255, 250, 240),
    'forestgreen': (34, 139, 34),
    'gainsboro': (220, 220, 220),
    'ghostwhite': (248, 248, 255),
    'gold': (255, 215, 0),
    'gold1': (255, 215, 0),
    'gold2': (238, 201, 0),
    'gold3': (205, 173, 0),
    'gold4': (139, 117, 0),
    'goldenrod': (218, 165, 32),
    'goldenrod1': (255, 193, 37),
    'goldenrod2': (238, 180, 34),
    'goldenrod3': (205, 155, 29),
    'goldenrod4': (139, 105, 20),
    'gray': (128, 128, 128),
    'gray0': (0, 0, 0),
    'gray1': (3, 3, 3),
    'gray10': (26, 26, 26),
    'gray100': (255, 255, 255),
    'gray11': (28, 28, 28),
    'gray12': (31, 31, 31),
    'gray13': (33, 33, 33),
    'gray14': (36, 36, 36),
    'gray15': (38, 38, 38),
    'gray16': (41, 41, 41),
    'gray17': (43, 43, 43),
    'gray18': (46, 46, 46),
    'gray19': (48, 48, 48),
    'gray2': (5, 5, 5),
    'gray20': (51, 51, 51),
    'gray21': (54, 54, 54),
    'gray22': (56, 56, 56),
    'gray23': (59, 59, 59),
    'gray24': (61, 61, 61),
    'gray25': (64, 64, 64),
    'gray26': (66, 66, 66),
    'gray27': (69, 69, 69),
    'gray28': (71, 71, 71),
    'gray29': (74, 74, 74),
    'gray3': (8, 8, 8),
    'gray30': (77, 77, 77),
    'gray31': (79, 79, 79),
    'gray32': (82, 82, 82),
    'gray33': (84, 84, 84),
    'gray34': (87, 87, 87),
    'gray35': (89, 89, 89),
    'gray36': (92, 92, 92),
    'gray37': (94, 94, 94),
    'gray38': (97, 97, 97),
    'gray39': (99, 99, 99),
    'gray4': (10, 10, 10),
    'gray40': (102, 102, 102),
    'gray41': (105, 105, 105),
    'gray42': (107, 107, 107),
    'gray43': (110, 110, 110),
    'gray44': (112, 112, 112),
    'gray45': (115, 115, 115),
    'gray46': (117, 117, 117),
    'gray47': (120, 120, 120),
    'gray48': (122, 122, 122),
    'gray49': (125, 125, 125),
    'gray5': (13, 13, 13),
    'gray50': (127, 127, 127),
    'gray51': (130, 130, 130),
    'gray52': (133, 133, 133),
    'gray53': (135, 135, 135),
    'gray54': (138, 138, 138),
    'gray55': (140, 140, 140),
    'gray56': (143, 143, 143),
    'gray57': (145, 145, 145),
    'gray58': (148, 148, 148),
    'gray59': (150, 150, 150),
    'gray6': (15, 15, 15),
    'gray60': (153, 153, 153),
    'gray61': (156, 156, 156),
    'gray62': (158, 158, 158),
    'gray63': (161, 161, 161),
    'gray64': (163, 163, 163),
    'gray65': (166, 166, 166),
    'gray66': (168, 168, 168),
    'gray67': (171, 171, 171),
    'gray68': (173, 173, 173),
    'gray69': (176, 176, 176),
    'gray7': (18, 18, 18),
    'gray70': (179, 179, 179),
    'gray71': (181, 181, 181),
    'gray72': (184, 184, 184),
    'gray73': (186, 186, 186),
    'gray74': (189, 189, 189),
    'gray75': (191, 191, 191),
    'gray76': (194, 194, 194),
    'gray77': (196, 196, 196),
    'gray78': (199, 199, 199),
    'gray79': (201, 201, 201),
    'gray8': (20, 20, 20),
    'gray80': (204, 204, 204),
    'gray81': (207, 207, 207),
    'gray82': (209, 209, 209),
    'gray83': (212, 212, 212),
    'gray84': (214, 214, 214),
    'gray85': (217, 217, 217),
    'gray86': (219, 219, 219),
    'gray87': (222, 222, 222),
    'gray88': (224, 224, 224),
    'gray89': (227, 227, 227),
    'gray9': (23, 23, 23),
    'gray90': (229, 229, 229),
    'gray91': (232, 232, 232),
    'gray92': (235, 235, 235),
    'gray93': (237, 237, 237),
    'gray94': (240, 240, 240),
    'gray95': (242, 242, 242),
    'gray96': (245, 245, 245),
    'gray97': (247, 247, 247),
    'gray98': (250, 250, 250),
    'gray99': (252, 252, 252),
    'green': (0, 128, 0),
    'green1': (0, 255, 0),
    'green2': (0, 238, 0),
    'green3': (0, 205, 0),
    'green4': (0, 139, 0),
    'greenyellow': (173, 255, 47),
    'grey': (128, 128, 128),
    'grey0': (0, 0, 0),
    'grey1': (3, 3, 3),
    'grey10': (26, 26, 26),
    'grey100': (255, 255, 255),
    'grey11': (28, 28, 28),
    'grey12': (31, 31, 31),
    'grey13': (33, 33, 33),
    'grey14': (36, 36, 36),
    'grey15': (38, 38, 38),
    'grey16': (41, 41, 41),
    'grey17': (43, 43, 43),
    'grey18': (46, 46, 46),
    'grey19': (48, 48, 48),
    'grey2': (5, 5, 5),
    'grey20': (51, 51, 51),
    'grey21': (54, 54, 54),
    'grey22': (56, 56, 56),
    'grey23': (59, 59, 59),
    'grey24': (61, 61, 61),
    'grey25': (64, 64, 64),
    'grey26': (66, 66, 66),
    'grey27': (69, 69, 69),
    'grey28': (71, 71, 71),
    'grey29': (74, 74, 74),
    'grey3': (8, 8, 8),
    'grey30': (77, 77, 77),
    'grey31': (79, 79, 79),
    'grey32': (82, 82, 82),
    'grey33': (84, 84, 84),
    'grey34': (87, 87, 87),
    'grey35': (89, 89, 89),
    'grey36': (92, 92, 92),
    'grey37': (94, 94, 94),
    'grey38': (97, 97, 97),
    'grey39': (99, 99, 99),
    'grey4': (10, 10, 10),
    'grey40': (102, 102, 102),
    'grey41': (105, 105, 105),
    'grey42': (107, 107, 107),
    'grey43': (110, 110, 110),
    'grey44': (112, 112, 112),
    'grey45': (115, 115, 115),
    'grey46': (117, 117, 117),
    'grey47': (120, 120, 120),
    'grey48': (122, 122, 122),
    'grey49': (125, 125, 125),
    'grey5': (13, 13, 13),
    'grey50': (127, 127, 127),
    'grey51': (130, 130, 130),
    'grey52': (133, 133, 133),
    'grey53': (135, 135, 135),
    'grey54': (138, 138, 138),
    'grey55': (140, 140, 140),
    'grey56': (143, 143, 143),
    'grey57': (145, 145, 145),
    'grey58': (148, 148, 148),
    'grey59': (150, 150, 150),
    'grey6': (15, 15, 15),
    'grey60': (153, 153, 153),
    'grey61': (156, 156, 156),
    'grey62': (158, 158, 158),
    'grey63': (161, 161, 161),
    'grey64': (163, 163, 163),
    'grey65': (166, 166, 166),
    'grey66': (168, 168, 168),
    'grey67': (171, 171, 171),
    'grey68': (173, 173, 173),
    'grey69': (176, 176, 176),
    'grey7': (18, 18, 18),
    'grey70': (179, 179, 179),
    'grey71': (181, 181, 181),
    'grey72': (184, 184, 184),
    'grey73': (186, 186, 186),
    'grey74': (189, 189, 189),
    'grey75': (191, 191, 191),
    'grey76': (194, 194, 194),
    'grey77': (196, 196, 196),
    'grey78': (199, 199, 199),
    'grey79': (201, 201, 201),
    'grey8': (20, 20, 20),
    'grey80': (204, 204, 204),
    'grey81': (207, 207, 207),
    'grey82': (209, 209, 209),
    'grey83': (212, 212, 212),
    'grey84': (214, 214, 214),
    'grey85': (217, 217, 217),
    'grey86': (219, 219, 219),
    'grey87': (222, 222, 222),
    'grey88': (224, 224, 224),
    'grey89': (227, 227, 227),
    'grey9': (23, 23, 23),
    'grey90': (229, 229, 229),
    'grey91': (232, 232, 232),
    'grey92': (235, 235, 235),
    'grey93': (237, 237, 237),
    'grey94': (240, 240, 240),
    'grey95': (242, 242, 242),
    'grey96': (245, 245, 245),
    'grey97': (247, 247, 247),
    'grey98': (250, 250, 250),
    'grey99': (252, 252, 252),
    'honeydew': (240, 255, 240),
    'honeydew1': (240, 255, 240),
    'honeydew2': (224, 238, 224),
    'honeydew3': (193, 205, 193),
    'honeydew4': (131, 139, 131),
    'hotpink': (255, 105, 180),
    'hotpink1': (255, 110, 180),
    'hotpink2': (238, 106, 167),
    'hotpink3': (205, 96, 144),
    'hotpink4': (139, 58, 98),
    'indianred': (205, 92, 92),
    'indianred1': (255, 106, 106),
    'indianred2': (238, 99, 99),
    'indianred3': (205, 85, 85),
    'indianred4': (139, 58, 58),
    'ivory': (255, 255, 240),
    'ivory1': (255, 255, 240),
    'ivory2': (238, 238, 224),
    'ivory3': (205, 205, 193),
    'ivory4': (139, 139, 131),
    'khaki': (240, 230, 140),
    'khaki1': (255, 246, 143),
    'khaki2': (238, 230, 133),
    'khaki3': (205, 198, 115),
    'khaki4': (139, 134, 78),
    'lavender': (230, 230, 250),
    'lavenderblush': (255, 240, 245),
    'lavenderblush1': (255, 240, 245),
    'lavenderblush2': (238, 224, 229),
    'lavenderblush3': (205, 193, 197),
    'lavenderblush4': (139, 131, 134),
    'lawngreen': (124, 252, 0),
    'lemonchiffon': (255, 250, 205),
    'lemonchiffon1': (255, 250, 205),
    'lemonchiffon2': (238, 233, 191),
    'lemonchiffon3': (205, 201, 165),
    'lemonchiffon4': (139, 137, 112),
    'lightblue': (173, 216, 230),
    'lightblue1': (191, 239, 255),
    'lightblue2': (178, 223, 238),
    'lightblue3': (154, 192, 205),
    'lightblue4': (104, 131, 139),
    'lightcoral': (240, 128, 128),
    'lightcyan': (224, 255, 255),
    'lightcyan1': (224, 255, 255),
    'lightcyan2': (209, 238, 238),
    'lightcyan3': (180, 205, 205),
    'lightcyan4': (122, 139, 139),
    'lightgoldenrod': (238, 221, 130),
    'lightgoldenrod1': (255, 236, 139),
    'lightgoldenrod2': (238, 220, 130),
    'lightgoldenrod3': (205, 190, 112),
    'lightgoldenrod4': (139, 129, 76),
    'lightgoldenrodyellow': (250, 250, 210),
    'lightgray': (211, 211, 211),
    'lightgreen': (144, 238, 144),
    'lightgrey': (211, 211, 211),
    'lightpink': (255, 182, 193),
    'lightpink1': (255, 174, 185),
    'lightpink2': (238, 162, 173),
    'lightpink3': (205, 140, 149),
    'lightpink4': (139, 95, 101),
    'lightsalmon': (255, 160, 122),
    'lightsalmon1': (255, 160, 122),
    'lightsalmon2': (238, 149, 114),
    'lightsalmon3': (205, 129, 98),
    'lightsalmon4': (139, 87, 66),
    'lightseagreen': (32, 178, 170),
    'lightskyblue': (135, 206, 250),
    'lightskyblue1': (176, 226, 255),
    'lightskyblue2': (164, 211, 238),
    'lightskyblue3': (141, 182, 205),
    'lightskyblue4': (96, 123, 139),
    'lightslateblue': (132, 112, 255),
    'lightslategray': (119, 136, 153),
    'lightslategrey': (119, 136, 153),
    'lightsteelblue': (176, 196, 222),
    'lightsteelblue1': (202, 225, 255),
    'lightsteelblue2': (188, 210, 238),
    'lightsteelblue3': (162, 181, 205),
    'lightsteelblue4': (110, 123, 139),
    'lightyellow': (255, 255, 224),
    'lightyellow1': (255, 255, 224),
    'lightyellow2': (238, 238, 209),
    'lightyellow3': (205, 205, 180),
    'lightyellow4': (139, 139, 122),
    'limegreen': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'magenta1': (255, 0, 255),
    'magenta2': (238, 0, 238),
    'magenta3': (205, 0, 205),
    'magenta4': (139, 0, 139),
    'maroon': (128, 0, 0),
    'maroon1': (255, 52, 179),
    'maroon2': (238, 48, 167),
    'maroon3': (205, 41, 144),
    'maroon4': (139, 28, 98),
    'mediumaquamarine': (102, 205, 170),
    'mediumblue': (0, 0, 205),
    'mediumorchid': (186, 85, 211),
    'mediumorchid1': (224, 102, 255),
    'mediumorchid2': (209, 95, 238),
    'mediumorchid3': (180, 82, 205),
    'mediumorchid4': (122, 55, 139),
    'mediumpurple': (147, 112, 219),
    'mediumpurple1': (171, 130, 255),
    'mediumpurple2': (159, 121, 238),
    'mediumpurple3': (137, 104, 205),
    'mediumpurple4': (93, 71, 139),
    'mediumseagreen': (60, 179, 113),
    'mediumslateblue': (123, 104, 238),
    'mediumspringgreen': (0, 250, 154),
    'mediumturquoise': (72, 209, 204),
    'mediumvioletred': (199, 21, 133),
    'midnightblue': (25, 25, 112),
    'mintcream': (245, 255, 250),
    'mistyrose': (255, 228, 225),
    'mistyrose1': (255, 228, 225),
    'mistyrose2': (238, 213, 210),
    'mistyrose3': (205, 183, 181),
    'mistyrose4': (139, 125, 123),
    'moccasin': (255, 228, 181),
    'navajowhite': (255, 222, 173),
    'navajowhite1': (255, 222, 173),
    'navajowhite2': (238, 207, 161),
    'navajowhite3': (205, 179, 139),
    'navajowhite4': (139, 121, 94),
    'navy': (0, 0, 128),
    'navyblue': (0, 0, 128),
    'oldlace': (253, 245, 230),
    'olivedrab': (107, 142, 35),
    'olivedrab1': (192, 255, 62),
    'olivedrab2': (179, 238, 58),
    'olivedrab3': (154, 205, 50),
    'olivedrab4': (105, 139, 34),
    'orange': (255, 165, 0),
    'orange1': (255, 165, 0),
    'orange2': (238, 154, 0),
    'orange3': (205, 133, 0),
    'orange4': (139, 90, 0),
    'orangered': (255, 69, 0),
    'orangered1': (255, 69, 0),
    'orangered2': (238, 64, 0),
    'orangered3': (205, 55, 0),
    'orangered4': (139, 37, 0),
    'orchid': (218, 112, 214),
    'orchid1': (255, 131, 250),
    'orchid2': (238, 122, 233),
    'orchid3': (205, 105, 201),
    'orchid4': (139, 71, 137),
    'palegoldenrod': (238, 232, 170),
    'palegreen': (152, 251, 152),
    'palegreen1': (154, 255, 154),
    'palegreen2': (144, 238, 144),
    'palegreen3': (124, 205, 124),
    'palegreen4': (84, 139, 84),
    'paleturquoise': (175, 238, 238),
    'paleturquoise1': (187, 255, 255),
    'paleturquoise2': (174, 238, 238),
    'paleturquoise3': (150, 205, 205),
    'paleturquoise4': (102, 139, 139),
    'palevioletred': (219, 112, 147),
    'palevioletred1': (255, 130, 171),
    'palevioletred2': (238, 121, 159),
    'palevioletred3': (205, 104, 137),
    'palevioletred4': (139, 71, 93),
    'papayawhip': (255, 239, 213),
    'peachpuff': (255, 218, 185),
    'peachpuff1': (255, 218, 185),
    'peachpuff2': (238, 203, 173),
    'peachpuff3': (205, 175, 149),
    'peachpuff4': (139, 119, 101),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'pink1': (255, 181, 197),
    'pink2': (238, 169, 184),
    'pink3': (205, 145, 158),
    'pink4': (139, 99, 108),
    'plum': (221, 160, 221),
    'plum1': (255, 187, 255),
    'plum2': (238, 174, 238),
    'plum3': (205, 150, 205),
    'plum4': (139, 102, 139),
    'powderblue': (176, 224, 230),
    'purple': (128, 0, 128),
    'purple1': (155, 48, 255),
    'purple2': (145, 44, 238),
    'purple3': (125, 38, 205),
    'purple4': (85, 26, 139),
    'red': (255, 0, 0),
    'red1': (255, 0, 0),
    'red2': (238, 0, 0),
    'red3': (205, 0, 0),
    'red4': (139, 0, 0),
    'rosybrown': (188, 143, 143),
    'rosybrown1': (255, 193, 193),
    'rosybrown2': (238, 180, 180),
    'rosybrown3': (205, 155, 155),
    'rosybrown4': (139, 105, 105),
    'royalblue': (65, 105, 225),
    'royalblue1': (72, 118, 255),
    'royalblue2': (67, 110, 238),
    'royalblue3': (58, 95, 205),
    'royalblue4': (39, 64, 139),
    'saddlebrown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'salmon1': (255, 140, 105),
    'salmon2': (238, 130, 98),
    'salmon3': (205, 112, 84),
    'salmon4': (139, 76, 57),
    'sandybrown': (244, 164, 96),
    'seagreen': (46, 139, 87),
    'seagreen1': (84, 255, 159),
    'seagreen2': (78, 238, 148),
    'seagreen3': (67, 205, 128),
    'seagreen4': (46, 139, 87),
    'seashell': (255, 245, 238),
    'seashell1': (255, 245, 238),
    'seashell2': (238, 229, 222),
    'seashell3': (205, 197, 191),
    'seashell4': (139, 134, 130),
    'sienna': (160, 82, 45),
    'sienna1': (255, 130, 71),
    'sienna2': (238, 121, 66),
    'sienna3': (205, 104, 57),
    'sienna4': (139, 71, 38),
    'skyblue': (135, 206, 235),
    'skyblue1': (135, 206, 255),
    'skyblue2': (126, 192, 238),
    'skyblue3': (108, 166, 205),
    'skyblue4': (74, 112, 139),
    'slateblue': (106, 90, 205),
    'slateblue1': (131, 111, 255),
    'slateblue2': (122, 103, 238),
    'slateblue3': (105, 89, 205),
    'slateblue4': (71, 60, 139),
    'slategray': (112, 128, 144),
    'slategray1': (198, 226, 255),
    'slategray2': (185, 211, 238),
    'slategray3': (159, 182, 205),
    'slategray4': (108, 123, 139),
    'slategrey': (112, 128, 144),
    'snow': (255, 250, 250),
    'snow1': (255, 250, 250),
    'snow2': (238, 233, 233),
    'snow3': (205, 201, 201),
    'snow4': (139, 137, 137),
    'springgreen': (0, 255, 127),
    'springgreen1': (0, 255, 127),
    'springgreen2': (0, 238, 118),
    'springgreen3': (0, 205, 102),
    'springgreen4': (0, 139, 69),
    'steelblue': (70, 130, 180),
    'steelblue1': (99, 184, 255),
    'steelblue2': (92, 172, 238),
    'steelblue3': (79, 148, 205),
    'steelblue4': (54, 100, 139),
    'tan': (210, 180, 140),
    'tan1': (255, 165, 79),
    'tan2': (238, 154, 73),
    'tan3': (205, 133, 63),
    'tan4': (139, 90, 43),
    'thistle': (216, 191, 216),
    'thistle1': (255, 225, 255),
    'thistle2': (238, 210, 238),
    'thistle3': (205, 181, 205),
    'thistle4': (139, 123, 139),
    'tomato': (255, 99, 71),
    'tomato1': (255, 99, 71),
    'tomato2': (238, 92, 66),
    'tomato3': (205, 79, 57),
    'tomato4': (139, 54, 38),
    'turquoise': (64, 224, 208),
    'turquoise1': (0, 245, 255),
    'turquoise2': (0, 229, 238),
    'turquoise3': (0, 197, 205),
    'turquoise4': (0, 134, 139),
    'violet': (238, 130, 238),
    'violetred': (208, 32, 144),
    'violetred1': (255, 62, 150),
    'violetred2': (238, 58, 140),
    'violetred3': (205, 50, 120),
    'violetred4': (139, 34, 82),
    'wheat': (245, 222, 179),
    'wheat1': (255, 231, 186),
    'wheat2': (238, 216, 174),
    'wheat3': (205, 186, 150),
    'wheat4': (139, 126, 102),
    'white': (255, 255, 255),
    'whitesmoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellow1': (255, 255, 0),
    'yellow2': (238, 238, 0),
    'yellow3': (205, 205, 0),
    'yellow4': (139, 139, 0),
    'yellowgreen': (154, 205, 50),
}


COLORS = [Color('snow'), Color('ghost white'), Color('white smoke'), Color('gainsboro'), Color('floral white'),
          Color('old lace'),
          Color('linen'), Color('antique white'), Color('papaya whip'), Color('blanched almond'), Color('bisque'),
          Color('peach puff'),
          Color('navajo white'), Color('lemon chiffon'), Color('mint cream'), Color('azure'), Color('alice blue'),
          Color('lavender'),
          Color('lavender blush'), Color('misty rose'), Color('dark slate gray'), Color('dim gray'),
          Color('slate gray'),
          Color('light slate gray'), Color('gray'), Color('light grey'), Color('midnight blue'), Color('navy'),
          Color('cornflower blue'), Color('dark slate blue'),
          Color('slate blue'), Color('medium slate blue'), Color('light slate blue'), Color('medium blue'),
          Color('royal blue'), Color('blue'),
          Color('dodger blue'), Color('deep sky blue'), Color('sky blue'), Color('light sky blue'), Color('steel blue'),
          Color('light steel blue'),
          Color('light blue'), Color('powder blue'), Color('pale turquoise'), Color('dark turquoise'),
          Color('medium turquoise'), Color('turquoise'),
          Color('cyan'), Color('light cyan'), Color('cadet blue'), Color('medium aquamarine'), Color('aquamarine'),
          Color('dark green'), Color('dark olive green'),
          Color('dark sea green'), Color('sea green'), Color('medium sea green'), Color('light sea green'),
          Color('pale green'), Color('spring green'),
          Color('lawn green'), Color('medium spring green'), Color('green yellow'), Color('lime green'),
          Color('yellow green'),
          Color('forest green'), Color('olive drab'), Color('dark khaki'), Color('khaki'), Color('pale goldenrod'),
          Color('light goldenrod yellow'),
          Color('light yellow'), Color('yellow'), Color('gold'), Color('light goldenrod'), Color('goldenrod'),
          Color('dark goldenrod'), Color('rosy brown'),
          Color('indian red'), Color('saddle brown'), Color('sandy brown'),
          Color('dark salmon'), Color('salmon'), Color('light salmon'), Color('orange'), Color('dark orange'),
          Color('coral'), Color('light coral'), Color('tomato'), Color('orange red'), Color('red'), Color('hot pink'),
          Color('deep pink'), Color('pink'), Color('light pink'),
          Color('pale violet red'), Color('maroon'), Color('medium violet red'), Color('violet red'),
          Color('medium orchid'), Color('dark orchid'), Color('dark violet'), Color('blue violet'), Color('purple'),
          Color('medium purple'),
          Color('thistle'), Color('snow2'), Color('snow3'),
          Color('snow4'), Color('seashell2'), Color('seashell3'), Color('seashell4'), Color('AntiqueWhite1'),
          Color('AntiqueWhite2'),
          Color('AntiqueWhite3'), Color('AntiqueWhite4'), Color('bisque2'), Color('bisque3'), Color('bisque4'),
          Color('PeachPuff2'),
          Color('PeachPuff3'), Color('PeachPuff4'), Color('NavajoWhite2'), Color('NavajoWhite3'), Color('NavajoWhite4'),
          Color('LemonChiffon2'), Color('LemonChiffon3'), Color('LemonChiffon4'), Color('cornsilk2'),
          Color('cornsilk3'),
          Color('cornsilk4'), Color('ivory2'), Color('ivory3'), Color('ivory4'), Color('honeydew2'), Color('honeydew3'),
          Color('honeydew4'),
          Color('LavenderBlush2'), Color('LavenderBlush3'), Color('LavenderBlush4'), Color('MistyRose2'),
          Color('MistyRose3'),
          Color('MistyRose4'), Color('azure2'), Color('azure3'), Color('azure4'), Color('SlateBlue1'),
          Color('SlateBlue2'), Color('SlateBlue3'),
          Color('SlateBlue4'), Color('RoyalBlue1'), Color('RoyalBlue2'), Color('RoyalBlue3'), Color('RoyalBlue4'),
          Color('blue2'), Color('blue4'),
          Color('DodgerBlue2'), Color('DodgerBlue3'), Color('DodgerBlue4'), Color('SteelBlue1'), Color('SteelBlue2'),
          Color('SteelBlue3'), Color('SteelBlue4'), Color('DeepSkyBlue2'), Color('DeepSkyBlue3'), Color('DeepSkyBlue4'),
          Color('SkyBlue1'), Color('SkyBlue2'), Color('SkyBlue3'), Color('SkyBlue4'), Color('LightSkyBlue1'),
          Color('LightSkyBlue2'),
          Color('LightSkyBlue3'), Color('LightSkyBlue4'), Color('SlateGray1'), Color('SlateGray2'), Color('SlateGray3'),
          Color('SlateGray4'), Color('LightSteelBlue1'), Color('LightSteelBlue2'), Color('LightSteelBlue3'),
          Color('LightSteelBlue4'), Color('LightBlue1'), Color('LightBlue2'), Color('LightBlue3'), Color('LightBlue4'),
          Color('LightCyan2'), Color('LightCyan3'), Color('LightCyan4'), Color('PaleTurquoise1'),
          Color('PaleTurquoise2'),
          Color('PaleTurquoise3'), Color('PaleTurquoise4'), Color('CadetBlue1'), Color('CadetBlue2'),
          Color('CadetBlue3'),
          Color('CadetBlue4'), Color('turquoise1'), Color('turquoise2'), Color('turquoise3'), Color('turquoise4'),
          Color('cyan2'), Color('cyan3'),
          Color('cyan4'), Color('DarkSlateGray1'), Color('DarkSlateGray2'), Color('DarkSlateGray3'),
          Color('DarkSlateGray4'),
          Color('aquamarine2'), Color('aquamarine4'), Color('DarkSeaGreen1'), Color('DarkSeaGreen2'),
          Color('DarkSeaGreen3'),
          Color('DarkSeaGreen4'), Color('SeaGreen1'), Color('SeaGreen2'), Color('SeaGreen3'), Color('PaleGreen1'),
          Color('PaleGreen2'),
          Color('PaleGreen3'), Color('PaleGreen4'), Color('SpringGreen2'), Color('SpringGreen3'), Color('SpringGreen4'),
          Color('green2'), Color('green3'), Color('green4'), Color('chartreuse2'), Color('chartreuse3'),
          Color('chartreuse4'),
          Color('OliveDrab1'), Color('OliveDrab2'), Color('OliveDrab4'), Color('DarkOliveGreen1'),
          Color('DarkOliveGreen2'),
          Color('DarkOliveGreen3'), Color('DarkOliveGreen4'), Color('khaki1'), Color('khaki2'), Color('khaki3'),
          Color('khaki4'),
          Color('LightGoldenrod1'), Color('LightGoldenrod2'), Color('LightGoldenrod3'), Color('LightGoldenrod4'),
          Color('LightYellow2'), Color('LightYellow3'), Color('LightYellow4'), Color('yellow2'), Color('yellow3'),
          Color('yellow4'),
          Color('gold2'), Color('gold3'), Color('gold4'), Color('goldenrod1'), Color('goldenrod2'), Color('goldenrod3'),
          Color('goldenrod4'),
          Color('DarkGoldenrod1'), Color('DarkGoldenrod2'), Color('DarkGoldenrod3'), Color('DarkGoldenrod4'),
          Color('RosyBrown1'), Color('RosyBrown2'), Color('RosyBrown3'), Color('RosyBrown4'), Color('IndianRed1'),
          Color('IndianRed2'),
          Color('IndianRed3'), Color('IndianRed4'), Color('sienna1'), Color('sienna2'), Color('sienna3'),
          Color('sienna4'), Color('burlywood1'),
          Color('burlywood2'), Color('burlywood3'), Color('burlywood4'), Color('wheat1'), Color('wheat2'),
          Color('wheat3'), Color('wheat4'), Color('tan1'),
          Color('tan2'), Color('tan4'), Color('chocolate1'), Color('chocolate2'), Color('chocolate3'),
          Color('firebrick1'), Color('firebrick2'),
          Color('firebrick3'), Color('firebrick4'), Color('brown1'), Color('brown2'), Color('brown3'), Color('brown4'),
          Color('salmon1'), Color('salmon2'),
          Color('salmon3'), Color('salmon4'), Color('LightSalmon2'), Color('LightSalmon3'), Color('LightSalmon4'),
          Color('orange2'),
          Color('orange3'), Color('orange4'), Color('DarkOrange1'), Color('DarkOrange2'), Color('DarkOrange3'),
          Color('DarkOrange4'),
          Color('coral1'), Color('coral2'), Color('coral3'), Color('coral4'), Color('tomato2'), Color('tomato3'),
          Color('tomato4'), Color('OrangeRed2'),
          Color('OrangeRed3'), Color('OrangeRed4'), Color('red2'), Color('red3'), Color('red4'), Color('DeepPink2'),
          Color('DeepPink3'), Color('DeepPink4'),
          Color('HotPink1'), Color('HotPink2'), Color('HotPink3'), Color('HotPink4'), Color('pink1'), Color('pink2'),
          Color('pink3'), Color('pink4'),
          Color('LightPink1'), Color('LightPink2'), Color('LightPink3'), Color('LightPink4'), Color('PaleVioletRed1'),
          Color('PaleVioletRed2'), Color('PaleVioletRed3'), Color('PaleVioletRed4'), Color('maroon1'), Color('maroon2'),
          Color('maroon3'), Color('maroon4'), Color('VioletRed1'), Color('VioletRed2'), Color('VioletRed3'),
          Color('VioletRed4'),
          Color('magenta2'), Color('magenta3'), Color('magenta4'), Color('orchid1'), Color('orchid2'), Color('orchid3'),
          Color('orchid4'), Color('plum1'),
          Color('plum2'), Color('plum3'), Color('plum4'), Color('MediumOrchid1'), Color('MediumOrchid2'),
          Color('MediumOrchid3'),
          Color('MediumOrchid4'), Color('DarkOrchid1'), Color('DarkOrchid2'), Color('DarkOrchid3'),
          Color('DarkOrchid4'),
          Color('purple1'), Color('purple2'), Color('purple3'), Color('purple4'), Color('MediumPurple1'),
          Color('MediumPurple2'),
          Color('MediumPurple3'), Color('MediumPurple4'), Color('thistle1'), Color('thistle2'), Color('thistle3'),
          Color('thistle4'),
          Color('gray1'), Color('gray2'), Color('gray3'), Color('gray4'), Color('gray5'), Color('gray6'),
          Color('gray7'), Color('gray8'), Color('gray9'), Color('gray10'),
          Color('gray11'), Color('gray12'), Color('gray13'), Color('gray14'), Color('gray15'), Color('gray16'),
          Color('gray17'), Color('gray18'), Color('gray19'),
          Color('gray20'), Color('gray21'), Color('gray22'), Color('gray23'), Color('gray24'), Color('gray25'),
          Color('gray26'), Color('gray27'), Color('gray28'),
          Color('gray29'), Color('gray30'), Color('gray31'), Color('gray32'), Color('gray33'), Color('gray34'),
          Color('gray35'), Color('gray36'), Color('gray37'),
          Color('gray38'), Color('gray39'), Color('gray40'), Color('gray42'), Color('gray43'), Color('gray44'),
          Color('gray45'), Color('gray46'), Color('gray47'),
          Color('gray48'), Color('gray49'), Color('gray50'), Color('gray51'), Color('gray52'), Color('gray53'),
          Color('gray54'), Color('gray55'), Color('gray56'),
          Color('gray57'), Color('gray58'), Color('gray59'), Color('gray60'), Color('gray61'), Color('gray62'),
          Color('gray63'), Color('gray64'), Color('gray65'),
          Color('gray66'), Color('gray67'), Color('gray68'), Color('gray69'), Color('gray70'), Color('gray71'),
          Color('gray72'), Color('gray73'), Color('gray74'),
          Color('gray75'), Color('gray76'), Color('gray77'), Color('gray78'), Color('gray79'), Color('gray80'),
          Color('gray81'), Color('gray82'), Color('gray83'),
          Color('gray84'), Color('gray85'), Color('gray86'), Color('gray87'), Color('gray88'), Color('gray89'),
          Color('gray90'), Color('gray91'), Color('gray92'),
          Color('gray93'), Color('gray94'), Color('gray95'), Color('gray97'), Color('gray98'), Color('gray99')]

# from pydraw.errors import *
# from pydraw.util import verify_keywords
import math


class Location:
    __slots__ = ('_x', '_y')

    @classmethod
    def _raw(cls, x, y):
        """
        Fast internal constructor: build a Location from two numbers without any
        argument parsing. For hot paths (e.g. per-vertex construction in
        Renderable._update_coords) where the inputs are already known to be
        numbers. Not part of the public API.
        """
        location = cls.__new__(cls)
        location._x = x
        location._y = y
        return location

    def __init__(self, *args, **kwargs):
        # Fast path: Location(x, y) with two numbers is by far the most common
        # (and hottest) construction, so handle it before the general parsing.
        if len(args) == 2 and not kwargs:
            x, y = args
            if (type(x) is float or type(x) is int) and \
                    (type(y) is float or type(y) is int):
                self._x = x
                self._y = y
                return

        location = (0, 0)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                location = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                location = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Location(): expected a tuple/Location or two numbers (x, y).'
                )
        elif len(kwargs) == 0:
            raise InvalidArgumentError(
                'Location(): expected a tuple/Location or two numbers (x, y).'
            )

        verify_keywords(kwargs, ('x', 'y'), 'Location()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Location(): expected a tuple/Location or two numbers (x, y).'
                )

            name = name.lower()
            if name == 'x':
                location = (value, location[1])
            elif name == 'y':
                location = (location[0], value)

        self._x = location[0]
        self._y = location[1]

    def move(self, *args, **kwargs):
        """
        Moves the location by a specified difference.

        Can take two numbers (dx, dy), a tuple, or a Location

        :param dx: the dx to move by
        :param dy: the dy to move by
        :return: the location (after change)
        """

        # Hot paths: avoid tuple construction, keyword verification, and the
        # general parser for the overwhelmingly common complete-coordinate
        # forms used by animation loops.
        if not kwargs:
            if len(args) == 2:
                dx, dy = args
                if ((type(dx) is float or type(dx) is int)
                        and (type(dy) is float or type(dy) is int)):
                    self._x += dx
                    self._y += dy
                    return self
            elif len(args) == 1:
                value = args[0]
                if type(value) is Location:
                    self._x += value._x
                    self._y += value._y
                    return self
                if (type(value) is tuple and len(value) == 2
                        and (type(value[0]) is float or type(value[0]) is int)
                        and (type(value[1]) is float or type(value[1]) is int)):
                    self._x += value[0]
                    self._y += value[1]
                    return self

        diff = (0, 0)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                diff = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                diff = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Location#move(): expected a tuple/Location or two numbers (dx, dy).'
                )
        elif len(kwargs) == 0:
            raise InvalidArgumentError(
                'Location#move(): expected a tuple/Location or two numbers (dx, dy).'
            )

        verify_keywords(kwargs, ('dx', 'dy'), 'Location#move()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Location#move(): expected a tuple/Location or two numbers (dx, dy).'
                )

            name = name.lower()
            if name == 'dx':
                diff = (value, diff[1])
            elif name == 'dy':
                diff = (diff[0], value)

        self._x += diff[0]
        self._y += diff[1]

        return self

    def moveto(self, *args, **kwargs):
        """
        Moves the location to a new location!

        Can take two coordinates (x, y), a tuple, or a Location

        :param x: the x to move to
        :param y: the y to move to
        :return: the location (after change)
        """

        # See move(): complete positional forms dominate sprite placement and
        # can update the two slots directly without allocating an intermediate
        # tuple or running keyword validation.
        if not kwargs:
            if len(args) == 2:
                x, y = args
                if ((type(x) is float or type(x) is int)
                        and (type(y) is float or type(y) is int)):
                    self._x = x
                    self._y = y
                    return self
            elif len(args) == 1:
                value = args[0]
                if type(value) is Location:
                    self._x = value._x
                    self._y = value._y
                    return self
                if (type(value) is tuple and len(value) == 2
                        and (type(value[0]) is float or type(value[0]) is int)
                        and (type(value[1]) is float or type(value[1]) is int)):
                    self._x = value[0]
                    self._y = value[1]
                    return self

        location = (self._x, self._y)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                location = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                location = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Location#moveto(): expected a tuple/Location or two numbers (x, y).'
                )
        elif len(kwargs) == 0:
            raise InvalidArgumentError(
                'Location#moveto(): expected a tuple/Location or two numbers (x, y).'
            )

        verify_keywords(kwargs, ('x', 'y'), 'Location#moveto()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Location#moveto(): expected a tuple/Location or two numbers (x, y).'
                )

            name = name.lower()
            if name == 'x':
                location = (value, location[1])
            elif name == 'y':
                location = (location[0], value)

        self._x = location[0]
        self._y = location[1]

        return self

    def x(self, new_x: float = None) -> float:
        if new_x is not None:
            self._x = new_x

        return self._x

    def y(self, new_y: float = None) -> float:
        if new_y is not None:
            self._y = new_y

        return self._y

    def distance(self, location) -> float:
        """
        Returns the distance between this location and another

        :param location: the Location to get the distance to
        :return: a float
        """

        return math.sqrt((location.x() - self.x()) ** 2 + (location.y() - self.y()) ** 2)

    def clone(self):
        """
        Clone the Location

        :return: a new Location with the same x and y as this one.
        """

        return Location._raw(self._x, self._y)

    def __str__(self):
        return f'(X: {self._x}, Y: {self._y})'

    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        """
        Allows the location to be accessed as a tuple
        """
        yield self._x
        yield self._y

    def __getitem__(self, item):
        """
        Allows the location to be accessed as a tuple
        """

        if item == 0:
            return self._x
        elif item == 1:
            return self._y
        else:
            raise IndexError(f'Accessed index beyond x and y, index: {item}.')

    def __len__(self):
        return 2  # Always 2!

    def __eq__(self, other):
        if type(other) is not Location and type(other) is not tuple:
            return False

        if len(other) != 2:
            return False

        return self.x() == other[0] and self.y() == other[1]

    def __hash__(self):
        return hash((self._x, self._y))

"""Platform-neutral input events."""

from typing import NamedTuple


class InputEvent(NamedTuple):
    kind: str
    position: object
    button: object
    key: object


__all__ = ['InputEvent']

"""Platform-neutral retained rendering data."""

from collections import OrderedDict
from typing import Callable, NamedTuple, Tuple


class PolylineNode(NamedTuple):
    id: int
    points: Tuple[Tuple[float, float], ...]
    color: Tuple[int, int, int]
    width: float
    dash: object
    visible: bool
    cap: str
    top: bool


class PolygonNode(NamedTuple):
    id: int
    points: Tuple[Tuple[float, float], ...]
    fill: object
    outline: object
    width: float
    visible: bool


class EllipseNode(NamedTuple):
    id: int
    center: Tuple[float, float]
    radius_x: float
    radius_y: float
    rotation: float
    points: Tuple[Tuple[float, float], ...]
    render_as_polygon: bool
    fill: object
    outline: object
    width: float
    visible: bool


class TextNode(NamedTuple):
    id: int
    position: Tuple[float, float]
    text: str
    color: Tuple[int, int, int]
    font: str
    size: int
    align: str
    bold: bool
    italic: bool
    underline: bool
    strikethrough: bool
    rotation: float
    visible: bool


class ImageNode(NamedTuple):
    id: int
    source: str
    position: Tuple[float, float]
    width: float
    height: float
    rotation: float
    tint: object
    tint_alpha: int
    border: object
    smooth: bool
    flip_x: bool
    flip_y: bool
    frame: int
    visible: bool


class RenderBatch(NamedTuple):
    upserts: tuple
    removals: tuple
    fronts: tuple
    backs: tuple

    def empty(self):
        return not any(self)


class RenderQueue:

    def __init__(self):
        self._next_id = 1
        self._sources = {}
        self._dirty = OrderedDict()
        self._removals = OrderedDict()
        self._fronts = OrderedDict()
        self._backs = OrderedDict()

    def allocate(self) -> int:
        render_id = self._next_id
        self._next_id += 1
        return render_id

    def register(self, source: Callable, render_id: int = None) -> int:
        if render_id is None:
            render_id = self.allocate()
        elif render_id >= self._next_id:
            self._next_id = render_id + 1

        self._sources[render_id] = source
        self._removals.pop(render_id, None)
        self._dirty[render_id] = None
        return render_id

    def invalidate(self, render_id: int) -> None:
        if render_id in self._sources:
            self._dirty[render_id] = None

    def remove(self, render_id: int) -> None:
        self._sources.pop(render_id, None)
        self._dirty.pop(render_id, None)
        self._fronts.pop(render_id, None)
        self._backs.pop(render_id, None)
        self._removals[render_id] = None

    def front(self, render_id: int) -> None:
        if render_id in self._sources:
            self._backs.pop(render_id, None)
            self._fronts[render_id] = None

    def back(self, render_id: int) -> None:
        if render_id in self._sources:
            self._fronts.pop(render_id, None)
            self._backs[render_id] = None

    def take(self) -> RenderBatch:
        upserts = []
        for render_id in self._dirty:
            source = self._sources.get(render_id)
            if source is None:
                continue
            node = source()
            if node.id != render_id:
                raise ValueError('render source returned the wrong ID')
            upserts.append(node)

        batch = RenderBatch(
            tuple(upserts),
            tuple(self._removals),
            tuple(self._fronts),
            tuple(self._backs),
        )
        self._dirty.clear()
        self._removals.clear()
        self._fronts.clear()
        self._backs.clear()
        return batch

"""Platform runtime selection and backend contracts.

This module deliberately contains no Tk, Turtle, DOM, or PyScript imports.
Normal applications do not select a runtime.  A host may install one before
the first Screen is created; otherwise Screen supplies the built-in runtime's
lazy factory when it requests its backend.
"""

from abc import ABCMeta, abstractmethod
from typing import Callable, Iterable, NamedTuple


class ScreenConfig(NamedTuple):
    """Immutable values needed to create a platform screen."""

    width: int
    height: int
    title: str


class ScreenBackend(metaclass=ABCMeta):
    """Platform operations owned by one Screen.

    Event and render payloads remain intentionally unspecified until their
    platform-neutral data models are introduced by the corresponding migration
    slices.  The lifecycle boundary itself is stable.
    """

    @abstractmethod
    def poll_events(self) -> Iterable:
        """Return pending normalized input events without blocking."""
        raise NotImplementedError

    @abstractmethod
    def listen(self) -> None:
        """Begin collecting platform input events."""
        raise NotImplementedError

    @abstractmethod
    def present(self, frame) -> None:
        """Synchronously present or acknowledge one platform-neutral frame."""
        raise NotImplementedError

    @abstractmethod
    def set_title(self, title: str) -> None:
        """Apply a platform title when the host supports one."""
        raise NotImplementedError

    @abstractmethod
    def set_background(self, color) -> None:
        """Apply an RGB screen background."""
        raise NotImplementedError

    @abstractmethod
    def set_background_image(self, source: str) -> None:
        """Apply a platform background image."""
        raise NotImplementedError

    @abstractmethod
    def canvas_size(self):
        """Return the drawable width and height."""
        raise NotImplementedError

    @abstractmethod
    def window_size(self):
        """Return the host window width and height."""
        raise NotImplementedError

    @abstractmethod
    def resize(self, width: int, height: int) -> None:
        """Resize the drawable area when supported."""
        raise NotImplementedError

    @abstractmethod
    def set_fullscreen(self, fullscreen: bool) -> None:
        """Apply the host fullscreen state."""
        raise NotImplementedError

    @abstractmethod
    def alert(self, text, title, accept_text, cancel_text):
        """Show a host confirmation dialog and return its result."""
        raise NotImplementedError

    @abstractmethod
    def prompt(self, text, title):
        """Show a host text prompt and return its result."""
        raise NotImplementedError

    @abstractmethod
    def grab(self, filename):
        """Capture the drawable area to a PNG and return its filename."""
        raise NotImplementedError

    @abstractmethod
    def measure_text(self, text, font, size, bold, italic):
        """Return the maximum line width and one line's height in pixels."""
        raise NotImplementedError

    @abstractmethod
    def measure_image(self, source):
        """Return an image's intrinsic width and height in pixels."""
        raise NotImplementedError

    @abstractmethod
    def image_frames(self, source):
        """Return an animated image's frame count."""
        raise NotImplementedError

    @abstractmethod
    def run(self, step: Callable[[], None]) -> None:
        """Run ``step`` until the screen closes."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Release this screen's platform resources."""
        raise NotImplementedError


class Runtime(metaclass=ABCMeta):
    """Process-wide factory for independent per-Screen backends."""

    @abstractmethod
    def create_screen(self, config: ScreenConfig) -> ScreenBackend:
        """Create a new backend configured for one Screen."""
        raise NotImplementedError


class RuntimeAlreadyConfiguredError(RuntimeError):
    """Raised when code tries to replace the selected runtime."""


class BackendTerminated(RuntimeError):
    """Raised when a backend can no longer process frames or events."""


_runtime = None
_runtime_locked = False


def _require_runtime(candidate) -> Runtime:
    if not isinstance(candidate, Runtime):
        raise TypeError('runtime must be an instance of Runtime')
    return candidate


def install_runtime(runtime: Runtime) -> None:
    """Install a host runtime before the first Screen is created.

    Normal local applications never call this function.  It is the extension
    seam used by an external host, such as the website's browser bootstrap.
    """

    global _runtime

    _require_runtime(runtime)
    if _runtime_locked:
        raise RuntimeAlreadyConfiguredError(
            'the runtime is locked because a Screen has already been created'
        )
    if _runtime is not None:
        raise RuntimeAlreadyConfiguredError('a runtime is already installed')
    _runtime = runtime


def _resolve_runtime(default_factory: Callable[[], Runtime]) -> Runtime:
    """Resolve and lock the runtime used by all Screens in this process."""

    global _runtime, _runtime_locked

    if _runtime is None:
        if not callable(default_factory):
            raise TypeError('default runtime factory must be callable')
        _runtime = _require_runtime(default_factory())

    _runtime_locked = True
    return _runtime


def _create_screen_backend(
        config: ScreenConfig,
        default_runtime_factory: Callable[[], Runtime]) -> ScreenBackend:
    """Create a backend through the selected runtime.

    This is internal until Screen is connected to it in the Tk-adapter step.
    Keeping the default factory as an argument lets runtime.py stay entirely
    platform-neutral and ensures an installed host runtime wins without
    importing the local backend.
    """

    if not isinstance(config, ScreenConfig):
        raise TypeError('config must be an instance of ScreenConfig')

    backend = _resolve_runtime(default_runtime_factory).create_screen(config)
    if not isinstance(backend, ScreenBackend):
        raise TypeError('Runtime.create_screen() must return a ScreenBackend')
    return backend


__all__ = [
    'BackendTerminated',
    'Runtime',
    'RuntimeAlreadyConfiguredError',
    'ScreenBackend',
    'ScreenConfig',
    'install_runtime',
]

"""Built-in Tk backend."""

# from pydraw.runtime import BackendTerminated, Runtime, ScreenBackend
# from pydraw.events import InputEvent
# from pydraw.render import EllipseNode, ImageNode, PolygonNode, PolylineNode, TextNode


class TkBackend(ScreenBackend):

    def __init__(self, config):
        import tkinter as tk

        self.tk = tk
        self.root = tk.Tk()
        self.canvas = tk.Canvas(
            self.root,
            width=config.width,
            height=config.height,
            borderwidth=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill='both', expand=True)
        self.width = config.width
        self.height = config.height
        self.items = {}
        self.fonts = {}
        self.image_refs = {}
        self.image_keys = {}
        self.source_images = {}
        self.events = []
        self.running = False
        self.closed = False
        self._canvas_size = (config.width, config.height)
        self.background_ref = None
        self.background_item = None

        self.root.resizable(False, False)
        self.root.title(config.title)
        self.root.update_idletasks()
        self.root.protocol('WM_DELETE_WINDOW', self._window_closed)
        self.canvas.bind('<Configure>', self._configure, add='+')

    def _window_closed(self):
        self.closed = True
        self.root.destroy()

    def _configure(self, event):
        self._canvas_size = None
        self.canvas_size()

    def poll_events(self):
        if self.closed:
            raise BackendTerminated()
        try:
            if not self.running:
                self.canvas.update()
        except self.tk.TclError as error:
            raise BackendTerminated() from error
        events = tuple(self.events)
        self.events.clear()
        return events

    def listen(self):
        self.events.clear()
        self.canvas.focus_force()
        self.canvas.bind('<Key>', self._queue_keydown)
        self.canvas.bind('<KeyRelease>', self._queue_keyup)
        self.canvas.bind('<Motion>', self._queue_mousemove)
        for button in (1, 2, 3):
            self.canvas.bind(
                '<Button-{}>'.format(button),
                lambda event, button=button: self._queue_pointer(
                    'mousedown', event, button
                ),
            )
            self.canvas.bind(
                '<Button{}-ButtonRelease>'.format(button),
                lambda event, button=button: self._queue_pointer(
                    'mouseup', event, button
                ),
            )
            self.canvas.bind(
                '<B{}-Motion>'.format(button),
                lambda event, button=button: self._queue_pointer(
                    'mousedrag', event, button
                ),
            )

    def _position(self, event):
        return (
            self.canvas.canvasx(event.x),
            self.canvas.canvasy(event.y),
        )

    def _queue_pointer(self, kind, event, button=None):
        self.events.append(InputEvent(kind, self._position(event), button, None))

    def _queue_mousemove(self, event):
        self._queue_pointer('mousemove', event)

    def _key(self, event):
        key = str(event.char)
        if not key or key.strip() == '' or not key.isprintable():
            key = event.keysym
        return key.lower()

    def _queue_keydown(self, event):
        self.events.append(InputEvent('keydown', None, None, self._key(event)))

    def _queue_keyup(self, event):
        self.events.append(InputEvent('keyup', None, None, self._key(event)))

    def present(self, frame):
        if self.closed:
            raise BackendTerminated()
        try:
            return self._present(frame)
        except self.tk.TclError as error:
            raise BackendTerminated() from error

    def _present(self, frame):
        if frame is None:
            return None

        for render_id in frame.removals:
            item = self.items.pop(render_id, None)
            if item is not None:
                self.canvas.delete(item)
            self.image_refs.pop(render_id, None)
            self.image_keys.pop(render_id, None)

        for node in frame.upserts:
            if isinstance(node, PolylineNode):
                self._present_polyline(node)
            elif isinstance(node, (PolygonNode, EllipseNode)):
                self._present_polygon(node)
            elif isinstance(node, TextNode):
                self._present_text(node)
            elif isinstance(node, ImageNode):
                self._present_image(node)
            else:
                raise TypeError('TkBackend received an unsupported render node')

        for render_id in frame.backs:
            item = self.items.get(render_id)
            if item is not None:
                self.canvas.tag_lower(item)
        for render_id in frame.fronts:
            item = self.items.get(render_id)
            if item is not None:
                self.canvas.tag_raise(item)

        if not frame.empty():
            self.canvas.update_idletasks()
        return None

    def _present_polyline(self, node):
        coordinates = []
        points = node.points
        if len(points) == 1:
            points = points + points
        for x, y in points:
            coordinates.extend((x, y))

        options = {
            'fill': self._color(node.color),
            'width': node.width,
            'dash': node.dash,
            'state': 'normal' if node.visible else 'hidden',
            'capstyle': node.cap,
        }
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_line(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

        if node.top:
            self.canvas.tag_raise(item)

    def _present_polygon(self, node):
        coordinates = []
        for x, y in node.points:
            coordinates.extend((x, y))

        options = {
            'fill': '' if node.fill is None else self._color(node.fill),
            'outline': '' if node.outline is None else self._color(node.outline),
            'width': node.width,
            'state': 'normal' if node.visible else 'hidden',
            'joinstyle': self.tk.MITER,
        }
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_polygon(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

    def _present_text(self, node):
        x, y = node.position
        decorations = []
        if node.bold:
            decorations.append('bold')
        if node.italic:
            decorations.append('italic')
        if node.underline:
            decorations.append('underline')
        if node.strikethrough:
            decorations.append('overstrike')

        options = {
            'text': node.text,
            'anchor': 'nw',
            'justify': node.align,
            'fill': self._color(node.color),
            'font': (node.font, -node.size, ' '.join(decorations)),
            'state': 'normal' if node.visible else 'hidden',
            'angle': -node.rotation,
        }
        coordinates = (x, y)
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_text(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

    def _present_image(self, node):
        key = (
            node.source,
            node.width,
            node.height,
            node.rotation,
            node.tint,
            node.tint_alpha,
            node.border,
            node.smooth,
            node.flip_x,
            node.flip_y,
            node.frame,
        )
        if self.image_keys.get(node.id) != key:
            self.image_refs[node.id] = self._build_image(node)
            self.image_keys[node.id] = key

        x, y = node.position
        coordinates = (
            x + node.width / 2,
            y + node.height / 2,
        )
        options = {
            'image': self.image_refs[node.id],
            'state': 'normal' if node.visible else 'hidden',
        }
        item = self.items.get(node.id)
        if item is None:
            item = self.canvas.create_image(*coordinates, **options)
            self.items[node.id] = item
        else:
            self.canvas.coords(item, *coordinates)
            self.canvas.itemconfigure(item, **options)

    def _build_image(self, node):
        import os

        extension = os.path.splitext(node.source)[1].lower()
        intrinsic = self.measure_image(node.source)
        native = extension in ('.png', '.gif', '.ppm')
        transformed = (
            (int(node.width), int(node.height)) != intrinsic
            or node.rotation % 360 != 0
            or node.tint is not None
            or node.border is not None
            or node.flip_x
            or node.flip_y
            or node.frame >= 0
        )
        if native and not transformed:
            return self.source_images[node.source]

        try:
            from PIL import Image as PILImage, ImageOps, ImageTk
        except ImportError:
            # from pydraw.errors import UnsupportedError

            raise UnsupportedError(
                'Image rendering modifications require Pillow on the Tk backend.'
            )

        with PILImage.open(node.source) as original:
            if node.frame >= 0:
                try:
                    original.seek(node.frame)
                except EOFError:
                    # from pydraw.errors import PydrawError

                    raise PydrawError(
                        "Image: no frame {} exists for '{}'".format(
                            node.frame, node.source,
                        )
                    )
            image = original.convert('RGBA')

        if node.flip_x:
            image = ImageOps.flip(image)
        if node.flip_y:
            image = ImageOps.mirror(image)
        if node.tint is not None:
            alpha = image.getchannel('A')
            gray = ImageOps.grayscale(image)
            image = ImageOps.colorize(
                gray,
                (0, 0, 0, 0),
                node.tint + (node.tint_alpha,),
            )
            image.putalpha(alpha)
        if node.border is not None:
            image = ImageOps.expand(image, border=10, fill=node.border)

        target_size = (int(node.width), int(node.height))
        if image.size != target_size:
            image = image.resize(
                target_size,
                PILImage.LANCZOS if node.smooth else PILImage.NEAREST,
            )
        if node.rotation % 360 != 0:
            image = image.rotate(
                -node.rotation,
                resample=PILImage.BILINEAR if node.smooth else PILImage.NEAREST,
                expand=1,
                fillcolor=None,
            )
        return ImageTk.PhotoImage(image=image, master=self.root)

    def set_title(self, title):
        self.root.title(title)

    def set_background(self, color):
        self.canvas.configure(background=self._color(color))

    def set_background_image(self, source):
        self.background_ref = self.tk.PhotoImage(master=self.root, file=source)
        width, height = self.canvas_size()
        if self.background_item is None:
            self.background_item = self.canvas.create_image(
                width / 2,
                height / 2,
                image=self.background_ref,
            )
        else:
            self.canvas.coords(self.background_item, width / 2, height / 2)
            self.canvas.itemconfigure(
                self.background_item,
                image=self.background_ref,
            )
        self.canvas.tag_lower(self.background_item)

    @staticmethod
    def _color(color):
        if isinstance(color, tuple):
            return '#{:02x}{:02x}{:02x}'.format(*color)
        return color

    def canvas_size(self):
        if self._canvas_size is not None:
            return self._canvas_size
        try:
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
        except self.tk.TclError:
            return -1, -1
        if width > 1 and height > 1:
            self._canvas_size = (width, height)
            self.width = width
            self.height = height
        return width, height

    def window_size(self):
        try:
            return self.root.winfo_width(), self.root.winfo_height()
        except self.tk.TclError:
            return -1, -1

    def resize(self, width, height):
        self.canvas.configure(width=width, height=height)
        self.root.geometry('{}x{}'.format(width, height))
        self._canvas_size = None
        self.root.update_idletasks()

    def set_fullscreen(self, fullscreen):
        self.root.attributes('-fullscreen', fullscreen)

    def alert(self, text, title, accept_text, cancel_text):
        from tkinter.simpledialog import SimpleDialog

        dialog = SimpleDialog(
            self.root,
            text=text,
            buttons=[accept_text, cancel_text],
            default=0,
            cancel=1,
            title=title,
        )
        return dialog.go()

    def prompt(self, text, title):
        from tkinter.simpledialog import askstring

        return askstring(title, text, parent=self.root)

    def grab(self, filename):
        try:
            from PIL import ImageGrab

            width, height = self.canvas_size()
            x1 = self.canvas.winfo_rootx()
            y1 = self.canvas.winfo_rooty()
            x2 = x1 + width
            y2 = y1 + height
            ImageGrab.grab().crop((x1, y1, x2, y2)).save(filename)
            return filename
        except Exception as error:
            # from pydraw.errors import UnsupportedError

            raise UnsupportedError(
                "Screen#grab(): Pillow is required. Install it with 'pip install pillow'."
            ) from error

    def measure_text(self, text, font, size, bold, italic):
        import tkinter.font as tkfont

        decorations = []
        if bold:
            decorations.append('bold')
        if italic:
            decorations.append('italic')
        font_data = (font, -size, ' '.join(decorations))
        measured_font = self.fonts.get(font_data)
        if measured_font is None:
            measured_font = tkfont.Font(root=self.root, font=font_data)
            self.fonts[font_data] = measured_font

        width = max((measured_font.measure(line) for line in text.split('\n')),
                    default=0)
        return width, measured_font.metrics('linespace')

    def measure_image(self, source):
        import os

        extension = os.path.splitext(source)[1].lower()
        if not extension:
            # from pydraw.errors import PydrawError

            raise PydrawError('Image(): path must include a file extension.')
        if not os.path.isfile(source):
            # from pydraw.errors import InvalidArgumentError

            raise InvalidArgumentError(
                "Image(): path does not reference an existing file: '{}'.".format(
                    source
                )
            )
        if extension in ('.png', '.gif', '.ppm'):
            image = self.source_images.get(source)
            if image is None:
                image = self.tk.PhotoImage(master=self.root, file=source)
                self.source_images[source] = image
            return image.width(), image.height()

        try:
            from PIL import Image as PILImage
        except ImportError:
            # from pydraw.errors import UnsupportedError

            raise UnsupportedError(
                'Pillow is required for formats other than PNG, GIF, and PPM.'
            )
        with PILImage.open(source) as image:
            return image.size

    def image_frames(self, source):
        try:
            from PIL import Image as PILImage
        except ImportError:
            # from pydraw.errors import UnsupportedError

            raise UnsupportedError('Animated image control requires Pillow.')

        with PILImage.open(source) as image:
            frames = getattr(image, 'n_frames', 1)
        if frames <= 1:
            # from pydraw.errors import PydrawError

            raise PydrawError('Image#load(): image is not animated.')
        return frames

    def item_for(self, render_id):
        return self.items.get(render_id)

    def run(self, step):
        if self.closed:
            raise BackendTerminated()
        active = [True]
        scheduled = [None]
        failure = [None]

        def tick():
            if not active[0]:
                return
            try:
                step()
            except BaseException as error:
                active[0] = False
                failure[0] = (error, error.__traceback__)
                self.root.quit()
                return
            if active[0]:
                scheduled[0] = self.root.after(1, tick)

        scheduled[0] = self.root.after(1, tick)
        self.running = True
        try:
            self.root.mainloop()
        except self.tk.TclError as error:
            raise BackendTerminated() from error
        finally:
            self.running = False
            active[0] = False
            if scheduled[0] is not None:
                try:
                    self.root.after_cancel(scheduled[0])
                except self.tk.TclError:
                    pass
        if failure[0] is not None:
            error, traceback = failure[0]
            raise error.with_traceback(traceback)

    def close(self):
        self.closed = True
        self.canvas.delete('all')
        self.root.destroy()


class TkRuntime(Runtime):

    def create_screen(self, config):
        return TkBackend(config)

import inspect
import math
import time
from typing import Optional

# from pydraw import Color
# from pydraw import Location
# from pydraw.events import InputEvent
# from pydraw.render import RenderQueue
# from pydraw.runtime import BackendTerminated, ScreenConfig, _create_screen_backend
# from pydraw.util import *

INPUT_TYPES = [
    'mousedown',
    'mouseup',
    'mousedrag',
    'mousemove',
    'keydown',
    'keyup',
    'keypress'
]

def _default_runtime():
    # from pydraw.backends.tk import TkRuntime

    return TkRuntime()


class Screen:
    """
    A class containing methods and values that can be manipulated in order to affect
    the window that is created. Sort of like a canvas.
    """

    def __init__(self, width: int = 800, height: int = 600, title: str = "pydraw"):
        verify(width, int, height, int, title, str)

        self._backend = _create_screen_backend(
            ScreenConfig(width, height, title),
            _default_runtime,
        )

        self._width = width
        self._height = height

        # Timing state used by sleep(delta=True). The completed-frame timestamp
        # measures delta time; the deadline keeps frame pacing from drifting.
        self._last_frame_time = None
        self._next_frame_time = None

        self._title = title
        self._color = Color('white')
        self._backend.set_background(self._color.rgb())

        self._objects = []  # Store objects on the screen :)
        self._render_queue = RenderQueue()
        self._fullscreen = False
        self._updating = False
        self._looping = False

        # store the mouse position
        self._mouse = Location(0, 0)
        self._gridlines = []
        self._gridstate = False  # grid is disabled by default

        self._helpers = []
        self._helperstate = 0

        self._scene = None  # We store our current Scene.

        self.registry = {}  # The input function registry (stores input callbacks)

    def title(self, title: str = None) -> str:
        """
        Get or set the title of the screen.

        :param title: the title to set to, if any
        :return: the title
        """

        if title is not None:
            verify(title, str)
            self._title = title
            self._backend.set_title(title)

        return self._title

    def color(self, color: Color = None) -> Color:
        """
        Set the background color of the screen.

        :param color: the color to set the background to
        :return: None
        """

        if color is not None:
            verify(color, Color)
            self._color = color
            self._backend.set_background(color.rgb())
        return self._color

    def picture(self, pic: str) -> None:
        """
        Set the background picture of the screen.

        :param pic: the path to said picture from the file
        :return: None
        """

        verify(pic, str)
        self._backend.set_background_image(pic)

    def resize(self, width: int, height: int) -> None:
        """
        @deprecated (does not work on all OSes)

        Resize the screen to new dimensions

        :param width: the width to resize to
        :param height: the height to resize to
        :return: None
        """

        verify(width, int, height, int)
        self._backend.resize(width, height)

    def size(self) -> (int, int):
        """
        Get the size of the WINDOW (please note this is not the canvas, and those attributes should be
        retrieved using the width() and height() methods respectively)

        :return: a tuple containing the width and height of the WINDOW
        """

        return self._backend.window_size()

    def _dims(self) -> tuple:
        """
        Returns the (width, height) of the CANVAS, memoized. The cache is cleared
        by the <Configure> binding installed in __init__ whenever the canvas is
        resized, so this stays correct for resizable/fullscreen windows too.
        :return: a (width, height) tuple, or (-1, -1) while tkinter is shutting down
        """

        return self._backend.canvas_size()

    def width(self) -> int:
        """
        Returns the width of the CANVAS within the screen. Important.

        :return: an integer representing the width of the canvas
        """

        return self._dims()[0]

    def height(self) -> int:
        """
        Returns the height of the CANVAS within the screen. Important.

        :return:
        """

        return self._dims()[1]

    def center(self) -> Location:
        """
        Gets the center of the screen.
        """

        return Location(self.width() / 2, self.height() / 2)

    # noinspection PyMethodMayBeStatic
    def top_left(self) -> Location:
        """
        Returns the top left corner of the screen

        :return: Location
        """

        return Location(0, 0)

    def top_right(self) -> Location:
        """
        Returns the top right corner of the screen

        :return: Location
        """

        return Location(self.width(), 0)

    def bottom_left(self) -> Location:
        """
        Returns the bottom left corner of the screen

        :return: Location
        """

        return Location(0, self.height())

    def bottom_right(self) -> Location:
        """
        Returns the bottom right corner of the screen

        :return: Location
        """

        return Location(self.width(), self.height())

    def mouse(self) -> Location:
        """
        Get the current mouse-position

        :return: the mouse-position in the form of a Location
        """

        return self._mouse

    # Direct Manipulation
    def alert(self, text: str, title: str = 'Alert', accept_text: str = 'Ok', cancel_text: str = 'Cancel') -> bool:
        """
        Displays a dialog-box alert, and returns

        :param text: The text to display in the body of the dialog
        :param title: The title of the dialog-box
        :param accept_text: The text displayed on the accept button, defaults to 'Ok'
        :param cancel_text: The text displayed on the cancel button, defaults to 'Cancel'
        :return: True if accept was pressed, False if cancel was pressed
        """
        verify(text, str, title, str, accept_text, str, cancel_text, str)
        return self._backend.alert(text, title, accept_text, cancel_text)

    def prompt(self, text: str, title: str = 'Prompt') -> str:
        """
        Prompts the user for keyboard input

        :param: text the text to prompt the user with
        :param: title the title of the dialog box
        :return: None
        """

        verify(text, str, title, str)

        response = self._backend.prompt(text, title)
        self._backend.listen()
        return response

    def grid(self, rows: int = None, cols: int = None, cellsize: tuple = (50, 50), helpers: bool = True):
        # from pydraw import Line, Text

        verify(rows, int, cols, int, cellsize, tuple, helpers, bool)

        if len(self._gridlines) > 0:
            [line.remove() for line in self._gridlines]
            self._gridlines.clear()
        if len(self._helpers) > 0:
            [helper.remove() for helper in self._helpers]
            self._helpers.clear()
        self._gridstate = True

        if rows is not None:
            cellsize = (self.height() / rows, cellsize[1])
        if cols is not None:
            cellsize = (cellsize[0], self.width() / cols)

        if helpers:
            textsize = int((self.width() + self.height() / 2) / 70)  # Text size is proportionate to screensize.

        for row in range(int(cellsize[1]), int(self.height()), int(cellsize[1])):
            line = Line(self, Location(0, row), Location(self.width(), row),
                        color=Color('lightgray'))
            self._gridlines.append(line)
            self._objects.remove(line)  # Don't want this in our objects list :)

            if helpers:
                helper = Text(self, str(row), 15, row, color=Color('gray'), size=textsize)
                helper.move(-helper.width() / 2, -helper.height() / 2)
                self._helpers.append(helper)
                self._objects.remove(helper)

        for col in range(int(cellsize[0]), int(self.width()), int(cellsize[0])):
            line = Line(self, Location(col, 0), Location(col, self.height()),
                        color=Color('lightgray'))
            self._gridlines.append(line)
            self._objects.remove(line)  # Don't want this in our objects list :)

            if helpers:
                helper = Text(self, str(col), col, 10, color=Color('gray'), size=textsize)
                helper.move(-helper.width() / 2, -helper.height() / 2)
                self._helpers.append(helper)
                self._objects.remove(helper)

    def toggle_grid(self, value=None):
        if value == False and len(self._gridlines) == 0: # If we don't have a grid and are resetting, no need to call grid()
            return

        if value is None:
            value = not self._gridstate

        if len(self._gridlines) == 0:
            self.grid()  # Create a grid if one does not exist.

        [line.visible(value) for line in self._gridlines]
        [helper.visible(value) for helper in self._helpers]

    def gridlines(self) -> tuple:
        """
        Allows you to retrieve the lines of the grid, but note that you cannot modify them!

        :return: a tuple (immutable list) of the gridlines.
        """

        return tuple(self._gridlines)

    def _redraw_grid(self):
        """
        An internal method to redraw the grid to the screen after screen.clear() is called.
        """
        # from pydraw import Line, Text

        new_lines = []
        for line in self._gridlines:
            new_line = Line(self, line.pos1(), line.pos2(), color=line.color())
            line.remove()
            self._objects.remove(new_line)  # Still don't want this in the main objects list.
            new_lines.append(new_line)

        new_helpers = []
        for helper in self._helpers:
            new_helper = Text(self, helper.text(), helper.x(), helper.y(), color=helper.color(), size=helper.size())
            helper.remove()
            self._objects.remove(new_helper)
            new_helpers.append(new_helper)

        self._gridlines.clear()
        self._gridlines = new_lines

        self._helpers.clear()
        self._helpers = new_helpers

    def grab(self, filename: str = None) -> str:
        """
        Grabs a screenshot of the image and saves it to the directory with the specified filename!
        Note that if no filename is specified the file will be given a name based on the epoch time.

        :param filename: the name of the file to save the screenshot to.
        :return: the name of the file.
        """

        if filename is None:
            filename = 'pydraw' + str(time.time() % 10000)

        verify(filename, str)

        if not filename.endswith('.png'):
            filename += '.png'

        return self._backend.grab(filename)

    def fullscreen(self, fullscreen: bool = None) -> bool:
        """
        Get or set the fullscreen state of the application. Note that this will not resize your shapes, nor
        will it REPOSITION them. It is highly recommended that you call this method before creating any shapes!

        !!! EXPERIMENTAL !!!

        :param fullscreen: the new fullscreen state, if any
        :return: the current fullscreen state of the Screen
        """

        if fullscreen is not None:
            verify(fullscreen, bool)
            self._fullscreen = fullscreen
            self._backend.set_fullscreen(fullscreen)
            self.update()

        return self._fullscreen

    def _front(self, obj) -> None:
        # from pydraw import Object

        if not isinstance(obj, Object):
            raise InvalidArgumentError(
                f'Screen#front(): expected an Object; received {type(obj)} ({obj!r}).'
            )

        self._render_queue.front(obj._render_id)

    def _back(self, obj) -> None:
        # from pydraw import Object

        if not isinstance(obj, Object):
            raise InvalidArgumentError(
                f'Screen#back(): expected an Object; received {type(obj)} ({obj!r}).'
            )

        self._render_queue.back(obj._render_id)

    def _register_render_source(self, source, render_id=None):
        return self._render_queue.register(source, render_id)

    def _allocate_render_id(self):
        return self._render_queue.allocate()

    def _invalidate_render(self, render_id):
        self._render_queue.invalidate(render_id)

    def _remove_render(self, render_id):
        self._render_queue.remove(render_id)

    def _add(self, obj) -> None:
        """
        Internal method which adds object to a list upon construction.

        :param obj: the object to add.
        :return: None
        """

        self._objects.append(obj)

    def add(self, obj) -> None:
        """
        Add an object back to the Screen after having removed it (with Object.remove() or Screen.remove(object)

        :param obj: the Object to add back.
        :return: None
        """

        if obj in self._objects:
            raise PydrawError(
                f'Screen#add(): object is already on this Screen: {type(obj)} ({obj!r}).'
            )

        self._add(obj)
        restore_render = getattr(obj, '_restore_render', None)
        if restore_render is not None:
            restore_render()

    # noinspection PyProtectedMember
    def remove(self, obj):
        render_id = getattr(obj, '_render_id', None)
        if render_id is None:
            render_id = getattr(obj, '_ref', None)
        if render_id is not None:
            self._remove_render(render_id)
        if obj in self._objects:
            self._objects.remove(obj)

    def objects(self) -> tuple:
        """
        Retrieves all objects on the Screen!

        :return: A tuple (immutable list) of Objects (you will want to check types for certain methods!)
        """

        return tuple(self._objects)

    def contains(self, obj) -> bool:
        """
        Returns whether or not the passed object exists on the Screen (is in the objects cache)

        :param obj: the Object to check
        :return: a boolean
        """

        return obj in self._objects

    def __contains__(self, item):
        return self.contains(item)

    def clear(self) -> None:
        """
        Clears the screen.

        :return: None
        """

        for i in range(len(self._objects) - 1, -1, -1):
            self._objects[i].remove()
        self.color(self._color)

    def scene(self, scene=None):
        """
        Apply a new scene to the screen!

        Note that this will override ALL previously registered input handlers.

        :param scene: The Scene to apply!
        :return: the new scene that was set, the existing scene if no args passed, or None
        """
        # from pydraw import Scene

        if scene is None:
            return self._scene

        if not isinstance(scene, Scene):
            raise InvalidArgumentError(
                f'Screen#scene(): expected a Scene; received {type(scene)} ({scene!r}).'
            )

        if self._scene is not None:
            del self._scene # calls our delete handler

        self.reset()  # Clears screen and destroys all registered input handlers.

        # Defines all input methods from the Scene.
        for (name, function) in inspect.getmembers(scene, predicate=inspect.ismethod):
            if name.lower() not in INPUT_TYPES:
                continue

            self.registry[name.lower()] = function

        self._scene = scene
        self._listen()
        scene.activate(self)

    def reset(self) -> None:
        """
        Resets the screen, removing all objects and input methods.

        :return: None
        """

        # A reset commonly starts a new scene and therefore a new frame loop.
        self._last_frame_time = None
        self._next_frame_time = None

        # Disable callbacks before removing objects. Tk may dispatch a queued
        # input event while canvas state is being torn down; leaving the old
        # registry live would let that event reach a scene whose objects have
        # already been detached from this Screen.
        self.registry.clear()

        self.toggle_grid(False)
        for line in self._gridlines:
            line.remove()
        self._gridlines.clear()

        for obj in self._helpers:
            obj.remove()
        self._helpers.clear()
        self._helperstate = False

        self.clear()

    def sleep(self, delay: float, delta: bool = False) -> Optional[float]:
        """
        Pause execution, optionally compensating for work done during the frame.

        With ``delta=False``, this sleeps for the full delay and returns None.
        With ``delta=True``, it sleeps only until the next frame deadline and
        returns the actual duration of the completed frame in seconds. The
        returned value is intended to be used as ``dt`` in the next frame.

        The first delta-enabled call returns the requested delay because there
        is no previous frame timestamp to measure. If execution falls more than
        one frame behind, the deadline is reset so the loop does not run a burst
        of catch-up frames.

        :param delay: target frame duration in seconds
        :param delta: whether to enable compensated frame pacing and return dt
        :return: None normally, or the completed frame duration when delta=True
        """

        if type(delay) is not int and type(delay) is not float:
            raise InvalidArgumentError(
                f'Screen#sleep(): delay must be a number; received {type(delay)} ({delay!r}).'
            )
        if type(delta) is not bool:
            raise InvalidArgumentError(
                f'Screen#sleep(): delta must be a bool; received {type(delta)} ({delta!r}).'
            )

        original_delay = delay
        try:
            delay = float(delay)
        except OverflowError:
            raise InvalidArgumentError(
                f'Screen#sleep(): delay must be finite and non-negative; received {original_delay!r}.'
            )

        if delay < 0 or not math.isfinite(delay):
            raise InvalidArgumentError(
                f'Screen#sleep(): delay must be finite and non-negative; received {original_delay!r}.'
            )

        if not delta:
            # A normal sleep breaks the delta-enabled frame sequence. Resetting
            # prevents that wait from being counted as work if delta timing is
            # enabled again later.
            self._last_frame_time = None
            self._next_frame_time = None
            time.sleep(delay)
            return None

        now = time.perf_counter()
        first_frame = self._last_frame_time is None or self._next_frame_time is None

        if first_frame:
            self._next_frame_time = now + delay
        else:
            self._next_frame_time += delay

            # Retain the absolute schedule for ordinary jitter, but discard
            # accumulated timing debt after a pause or a very slow frame.
            if now - self._next_frame_time > delay:
                self._next_frame_time = now + delay

        remaining = self._next_frame_time - now
        if remaining > 0:
            time.sleep(remaining)

        completed_at = time.perf_counter()
        frame_time = delay if first_frame else completed_at - self._last_frame_time
        self._last_frame_time = completed_at
        return frame_time

    def update(self) -> None:
        """
        Updates the screen.

        :return: None
        """
        if self._updating:
            raise PydrawError('Screen#update(): update is not reentrant.')

        self._updating = True
        try:
            for event in self._backend.poll_events():
                self._dispatch_input_event(event)
            self._backend.present(self._render_queue.take())
        except BackendTerminated:
            print('Terminated.')
            exit(0)
        finally:
            self._updating = False

    def stop(self) -> None:
        """
        Deprecated. Use `screen.loop` instead.

        :return: None
        """

        self.loop()

    def loop(self) -> None:
        """
        Holds the program open and calls screen.update() for you. Must be used at the end of any pyDraw program
        unless there is a while loop with screen.update() in it instead.

        :returns: None
        """

        if self._looping:
            raise PydrawError('Screen#loop(): loop is not reentrant.')

        self._looping = True
        try:
            self._backend.run(self.update)
        finally:
            self._looping = False

    def exit(self) -> None:
        """
        Called at the end of pydraw programs as an event for successful program execution and termination.
        To keep a program open, use Screen.loop().

        :return: None
        """

        # Prevent queued Tk events from reaching callbacks while the canvas and
        # its objects are being destroyed.
        self.registry.clear()
        self._backend.close()
        exit(0)

    def listen(self) -> None:
        """
        Reads the file for input functions and registers them as callbacks!
        The input-type is determined by the name of the function.

        Allowed Names:
          - mousedown
          - mouseup
          - mousedrag
          - keydown
          - keyup
          - keypress (deprecated)

        :return: None
        """

        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        for (name, function) in inspect.getmembers(mod, inspect.isfunction):
            if name.lower() not in INPUT_TYPES:
                continue

            self.registry[name.lower()] = function
            # print('Registered input-function:', name)

        self._listen()

    def _listen(self):
        self._backend.listen()

    class Key:
        def __init__(self, key: str):
            self._key = key

        def key(self) -> str:
            """
            Returns the string for the key.

            :return: the key in ascii
            """
            return self._key

        def __repr__(self):
            return self.key()

        def __str__(self):
            return self.key()

        def __add__(self, other):
            return str(self) + other

        def __radd__(self, other):
            return other + str(self)

        def __eq__(self, obj) -> bool:
            """
            Overrides the equals operator so that we can compare with strings! Fantastic!

            :param obj: the object to compare to
            :return: if the key is equal to the object.
            """
            if type(obj) is self.__class__:
                return obj.key() == self.key()
            elif type(obj) is str:
                return obj.lower() == self.key().lower()
            else:
                return False

    def _dispatch_input_event(self, event) -> None:
        if not isinstance(event, InputEvent):
            raise TypeError('backend returned an invalid input event')

        if event.kind == 'keydown':
            self._keydown(event.key)
        elif event.kind == 'keyup':
            self._keyup(event.key)
        elif event.kind == 'keypress':
            self._keypress(event.key)
        elif event.kind == 'mousedown':
            self._mousedown(event.button, Location(*event.position))
        elif event.kind == 'mouseup':
            self._mouseup(event.button, Location(*event.position))
        elif event.kind == 'mousedrag':
            self._mousedrag(event.button, Location(*event.position))
        elif event.kind == 'mousemove':
            self._mousemove(Location(*event.position))
        else:
            raise ValueError('backend returned an unknown input event')

    def _keydown(self, key) -> None:
        if 'keydown' not in self.registry:
            return

        self.registry['keydown'](self.Key(key.lower()))

    def _keyup(self, key) -> None:
        if 'keyup' not in self.registry:
            return

        self.registry['keyup'](self.Key(key.lower()))

    def _keypress(self, key) -> None:
        if 'keypress' not in self.registry:
            return

        self.registry['keypress'](self.Key(key.lower()))

    def _mousedown(self, button, location) -> None:
        if 'mousedown' not in self.registry:
            return

        signature = inspect.signature(self.registry['mousedown'])
        keys = list(signature.parameters.keys())

        if len(keys) == 1:
            self.registry['mousedown'](location)
            return
        if keys[0] == "button" and keys[1] == "location":
            self.registry['mousedown'](button, location)
            print("[WARNING] in `mousedown` | Argument Pattern: (button, location) has been deprecated, "
                  "please use (location, button) instead.")
            return

        self.registry['mousedown'](location, button)

    def _mouseup(self, button, location) -> None:
        if 'mouseup' not in self.registry:
            return

        signature = inspect.signature(self.registry['mouseup'])
        keys = list(signature.parameters.keys())

        if len(keys) == 1:
            self.registry['mouseup'](location)
            return
        if keys[0] == "button" and keys[1] == "location":
            self.registry['mouseup'](button, location)
            print("[WARNING] in `mouseup` | Argument Pattern: (button, location) has been deprecated, "
                  "please use (location, button) instead.")
            return

        self.registry['mouseup'](location, button)

    def _mouseclick(self, button, location) -> None:
        if 'mouseclick' not in self.registry:
            return

        self.registry['mouseclick'](button, location)

    def _mousedrag(self, button, location) -> None:
        if 'mousedrag' not in self.registry:
            return

        signature = inspect.signature(self.registry['mousedrag'])
        keys = list(signature.parameters.keys())

        if len(keys) == 1:
            self.registry['mousedrag'](location)
            return
        if keys[0] == "button" and keys[1] == "location":
            self.registry['mousedrag'](button, location)
            print("[WARNING] in `mousedrag` | Argument Pattern: (button, location) has been deprecated, "
                  "please use (location, button) instead.")
            return

        self.registry['mousedrag'](location, button)

    def _mousemove(self, location) -> None:
        # We will update our internal storage of the mouse-location no matter what
        self._mouse = location

        if 'mousemove' not in self.registry:
            return

        self.registry['mousemove'](location)

# from pydraw import Screen, Location


class Scene:
    """
    An abstraction of the Screen, designed to store the Screen in a certain state while retaining registered input
    handlers and the positions and attributes of objects registered to it.

    You can use Scenes to create multi-screen games or to manage different levels easily. It works exactly like a screen
    but will not render anything until it is "applied" to a Screen via `Screen.scene(some_scene)`
    """

    def __init__(self):
        self._screen = None

    def screen(self):
        """
        Retrieve the screen that the scene is tied to

        :return: a Screen
        """
        return self._screen

    def start(self) -> None:
        """
        Run as the initializer for the scene

        :return: None
        """

    def run(self) -> None:
        """
        Run the scene (the loop should go here)

        :return: None
        """

    def mousedown(self, location: Location, button: int) -> None:
        """
        Mouse event, called when a mouse button is pressed down.

        :param location: the location that was clicked
        :param button: the button pressed (0-2)
        :return: None
        """

    def mouseup(self, location: Location, button: int) -> None:
        """
        Mouse event, called when a mouse button is released.

        :param location: the location that was clicked
        :param button: the button released (0-2)
        :return: None
        """

    def mousedrag(self, location: Location, button: int) -> None:
        """
        Mouse event, called when the mouse moves after a mousedown event (without a mouseup event)

        :param location: the Location the mouse has moved to
        :param button: the button being held (0-2)
        :return: None
        """

    def mousemove(self, location: Location) -> None:
        """
        Mouse event called when the mouse moves over the Screen

        :param location: the Location the mouse moved to
        :return: None
        """

    def keydown(self, key: Screen.Key) -> None:
        """
        Key event called when a key is pressed

        :param key: the Key that was pressed
        :return: None
        """

    def keyup(self, key: Screen.Key) -> None:
        """
        Key event called when a key is released

        :param key: the Key that was released
        :return: None
        """

    def activate(self, screen: Screen) -> None:
        """
        Activates the Scene with a Screen (called internally)

        :param screen: the Screen to display the Scene on
        :return: None
        """

        self._screen = screen
        self.start()
        self.run()

"""
Objects in the PyDraw library

(Author: Noah Coetsee)
"""

import math
from typing import Union, List
# import asyncio

# from pydraw.errors import *  # util gives us our errors for us :)
# from pydraw.util import *

# from pydraw import Screen
# from pydraw import Location
# from pydraw import Color
# from pydraw.render import EllipseNode, ImageNode, PolygonNode, PolylineNode, TextNode

# from pydraw.overload import overload

PIXEL_RATIO = 20
NoneType = type(None)


class Pen:
    # Pen for drawing a line as an object moves around on the screen
    def __init__(self, screen: Screen, x: float, y: float, color: Color = Color('black'), width: int = 2, top: bool = False):
        self._screen = screen
        self._coordinates = []  # contains all coordinates of the lines
        self._location = Location(x, y)  # used for when _drawing = False

        # self._coordinates.append(Location(x, y))

        self._color = color
        self._width = width
        self._top = top

        self._drawing = False

        self._history = []  # stores old line _refs for clearing
        self._ref = None  # currentLine
        self._strokes = {}
        self._stroke_visibility = {}

    def location(self) -> Location:
        if self._drawing and len(self._coordinates) > 0:
            return self._coordinates[-1]

        return self._location

    def move(self, *args, **kwargs):
        """
        Adds a new coordinate to the pen line with a passed difference from the previous coordinate.
        Requires coordinates to be len > 0.

        Can take two numbers (dx, dy), a tuple, or a Location

        :param dx: the dx to move by
        :param dy: the dy to move by
        :return: the location (after change)
        """

        diff = (0, 0)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                diff = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                diff = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Pen#move(): expected a tuple/Location or two numbers (dx, dy).'
                )
        elif len(kwargs) == 0:
            raise InvalidArgumentError(
                'Pen#move(): expected a tuple/Location or two numbers (dx, dy).'
            )

        verify_keywords(kwargs, ('dx', 'dy'), 'Pen#move()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Pen#move(): expected a tuple/Location or two numbers (dx, dy).'
                )

            name = name.lower()
            if name == 'dx':
                diff = (value, diff[1])
            elif name == 'dy':
                diff = (diff[0], value)

        if not len(self._coordinates) > 0:
            raise PydrawError('Pen#move(): cannot move before the Pen has been started.')

        current = self.location()
        location = Location(current.x() + diff[0], current.y() + diff[1])
        if self._drawing:
            self._coordinates.append(location)
        else:
            self._location = location

        self._update()
        return location

    def moveto(self, *args, **kwargs):
        """
        Adds a new coordinate to the pen line.

        Can take two coordinates (x, y), a tuple, or a Location

        :param x: the x to move to
        :param y: the y to move to
        :return: the location (after change)
        """

        # Seed from the effective current position so partial calls work both
        # while drawing and after the pen has stopped.
        current = self.location()
        location = (current.x(), current.y())

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                location = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                location = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Pen#moveto(): expected a tuple/Location or two numbers (x, y).'
                )
        elif len(kwargs) == 0:
            raise InvalidArgumentError(
                'Pen#moveto(): expected a tuple/Location or two numbers (x, y).'
            )

        verify_keywords(kwargs, ('x', 'y'), 'Pen#moveto()', case_sensitive=False)
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Pen#moveto(): expected a tuple/Location or two numbers (x, y).'
                )

            name = name.lower()
            if name == 'x':
                location = (value, location[1])
            elif name == 'y':
                location = (location[0], value)

        if not len(self._coordinates) > 0:
            raise PydrawError('Pen#moveto(): cannot move before the Pen has been started.')

        new_location = Location(location[0], location[1])
        if self._drawing:
            self._coordinates.append(new_location)
        else:
            self._location = new_location

        self._update()
        return new_location

    def coordinates(self, *coords) -> List[Location]:

        if len(coords) > 0:
            self._coordinates = []

            for pos in coords:
                if type(pos) is tuple or type(pos) is Location:
                    self._coordinates.append(Location(pos[0], pos[1]))
                else:
                    raise InvalidArgumentError(
                        'Pen#coordinates(): expected only tuples or Locations.'
                    )

            self._update()

        return self._coordinates

    def start(self):
        if self._drawing:
            return

        self._drawing = True
        self._coordinates = [Location(self._location)]

        self._setup()

    def stop(self):
        if not self._drawing:
            return

        if len(self._coordinates) > 0:
            self._location = self._coordinates[-1]
            # don't clear coordinates in case they get altered after we are done drawing

        if self._ref is not None:
            self._history.append(self._ref)
        self._drawing = False

    def drawing(self, drawing: bool = None) -> bool:
        if drawing is not None:
            if drawing and not self._drawing:
                self.start()
            elif not drawing and self._drawing:
                self.stop()

        return self._drawing

    def toggle(self) -> bool:
        if self._drawing:
            self.stop()
        else:
            self.start()

        return self._drawing

    # noinspection PyProtectedMember
    def clear(self):
        """
        Clear the line from the screen and all history (coordinates).
        """

        if len(self._coordinates) > 0:
            self._location = Location(self._coordinates[-1])

        for line in self._history:
            self._remove_stroke(line)
        self._history.clear()

        if self._drawing:
            self._coordinates = [Location(self._location)]
            if self._ref is not None:
                self._strokes[self._ref] = self._coordinates
                self._stroke_visibility[self._ref] = False
                self._screen._invalidate_render(self._ref)
        else:
            self._coordinates = []
            if self._ref is not None:
                self._remove_stroke(self._ref)
                self._ref = None

    def color(self, color: Color = None) -> Color:
        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            if self._ref is not None:
                self._update_all()

        return self._color

    def width(self, width: int = None) -> int:
        if width is not None:
            verify(width, int)
            self._width = width
            if self._ref is not None:
                self._update_all()

        return self._width

    def top(self, top: bool = None) -> bool:
        if top is not None:
            verify(top, bool)
            self._top = top
            if self._ref is not None:
                self._update_all()

        return self._top

    def _setup(self):
        render_id = self._screen._allocate_render_id()
        self._ref = render_id
        self._strokes[render_id] = self._coordinates
        self._stroke_visibility[render_id] = True
        self._screen._register_render_source(
            lambda render_id=render_id: self._render_stroke(render_id),
            render_id,
        )

    def _render_stroke(self, render_id):
        return PolylineNode(
            render_id,
            tuple((point.x(), point.y()) for point in self._strokes[render_id]),
            self._color.rgb(),
            self._width,
            None,
            self._stroke_visibility[render_id],
            'round',
            self._top,
        )

    def _remove_stroke(self, render_id):
        self._screen._remove_render(render_id)
        self._strokes.pop(render_id, None)
        self._stroke_visibility.pop(render_id, None)

    # noinspection PyProtectedMember
    def _update(self):
        if self._ref is None:
            raise PydrawError('Pen#update(): Pen has not been started.')

        self._strokes[self._ref] = self._coordinates
        self._stroke_visibility[self._ref] = True
        self._screen._invalidate_render(self._ref)

    def _update_all(self):
        self._update()
        for render_id in self._strokes:
            self._screen._invalidate_render(render_id)


class Object:
    """
    A base object containing a location and screen. This ensures coordinates are
    done with the root in the top left corner, and not at the center.
    """

    _PEN_SUPPORTED = True

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, location: Location = None):
        verify(screen, Screen, x, (float, int), y, (float, int), location, Location)

        self._screen = screen
        self._location = location if location is not None else Location(x, y)

        # noinspection PyProtectedMember
        self._screen._add(self)

        # Most objects never draw trails, so avoid creating an unused Pen and
        # canvas line until pen() is actually called.
        self._pen = None

    def x(self, x: float = None) -> float:
        if x is not None:
            verify(x, (float, int))
            self.moveto(x, self.y())

        return self._location.x()

    def y(self, y: float = None) -> float:
        if y is not None:
            verify(y, (float, int))
            self.moveto(self.x(), y)

        return self._location.y()

    def location(self) -> Location:
        return self._location

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        self._location.move(*args, **kwargs)
        self.update()
        self._sync_pen()

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        self._location.moveto(*args, **kwargs)
        self.update()
        self._sync_pen()

    def _get_real_location(self):
        # todo: move this to renderable
        real_x = self.x() + self.width() / 2 - (self._screen.width() / 2)
        real_y = -self.y() + self._screen.height() / 2 - self.height() / 2

        return real_x, real_y

    def front(self) -> None:
        """
        Brings the object to the front of the Screen
        (Imagine moving forward on the Z axis)

        :return: None
        """

        # noinspection PyProtectedMember
        self._screen._front(self)

    def back(self) -> None:
        """
        Brings the object to the back of the Screen
        (Imagine moving backward on the Z axis)

        :return: None
        """

        # noinspection PyProtectedMember
        self._screen._back(self)

    def remove(self) -> None:
        self._screen.remove(self)

    # Pen methods
    def _check_pen_supported(self, method: str = 'pen()') -> None:
        if not self._PEN_SUPPORTED:
            raise UnsupportedError(
                f'{type(self).__name__}#{method}: Pens are unsupported for this object.'
            )

    def _require_pen(self, method: str) -> Pen:
        self._check_pen_supported(method)
        if self._pen is None:
            raise PydrawError(
                f'{type(self).__name__}#{method}: this object has not started a Pen.'
            )

        return self._pen

    def _sync_pen(self) -> None:
        pen = getattr(self, '_pen', None)
        if pen is None or not pen.drawing():
            return

        location = Location(self.x(), self.y())
        if pen.location() != location:
            pen.moveto(location)

    def pen(self, color: Color = Color('black'), width: int = 2, top: bool = False) -> Pen:
        self._check_pen_supported('pen()')
        verify(color, Color, width, int, top, bool)

        if self._pen is None:
            self._pen = Pen(self._screen, self.x(), self.y(), color, width, top)
        else:
            self._pen.color(color)
            self._pen.width(width)
            self._pen.top(top)

        self._pen.drawing(True)
        return self._pen

    def pen_clear(self) -> None:
        self._require_pen('pen_clear()').clear()

    def pen_stop(self) -> bool:
        return self._require_pen('pen_stop()').drawing(False)

    def pen_width(self, width: int = None) -> int:
        return self._require_pen('pen_width()').width(width)

    def pen_top(self, top: bool = None) -> bool:
        return self._require_pen('pen_top()').top(top)

    # # noinspection PyProtectedMember
    # def add(self) -> None:
    #     """
    #     Should only be used to add an object that has been removed (via .remove() or Screen.clear()
    #     :return: None
    #     """
    #     if self in self._screen.objects():
    #         raise PydrawError('Error adding object: Object already in Screen.objects()')
    #
    #     self._setup()
    #     self._screen._add(self)

    def _setup(self):
        """
        To be overriden.
        """
        pass

    # noinspection PyProtectedMember
    def _check(self) -> None:
        if self._screen is None:
            return

        if not self._screen.contains(self):
            if self in self._screen._gridlines or self in self._screen._helpers:
                return

            raise PydrawError(
                f'{type(self).__name__}#update(): object is not on its Screen.'
            )

    def update(self) -> None:
        """
        To be overriden.
        """
        pass


class Renderable(Object):
    """
    Test class for new itemconfigure-based pyDraw objects.

    Update method is now only used for changes in position (and possibly changes that cannot be configured and require
    the item to be remade)
    """

    # bounds() cache. Class-level defaults so every subclass inherits them, even
    # ones like CustomPolygon that build their state without calling __init__.
    # Keyed on the transform parameters (see bounds()); the first compute on an
    # instance shadows these with per-instance values.
    _bounds_sig = None
    _bounds_cache = None
    def _render_color(self, color):
        return None if color == Color.NONE else color.rgb()

    def _render_node(self):
        return PolygonNode(
            self._render_id,
            tuple((vertex.x(), vertex.y()) for vertex in self.vertices()),
            self._render_color(self._color) if self._fill else None,
            self._render_color(self._border),
            self._border_width,
            self._visible,
        )

    def _register_render(self):
        self._render_id = self._screen._register_render_source(self._render_node)
        self._ref = self._render_id

    def _restore_render(self):
        self._screen._register_render_source(self._render_node, self._render_id)

    def _invalidate_render(self):
        self._screen._invalidate_render(self._render_id)

    def __init__(self, screen: Screen, x: float = 0, y: float = 0, width: float = 10, height: float = 10,
                 color: Color = Color('black'),
                 border: Color = Color.NONE,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 location: Location = None):
        super().__init__(screen, x, y, location)
        self._width = width
        self._height = height
        self._color = color
        self._border = border if border is not None else Color('')
        self._border_width = 1
        self._fill = fill
        self._angle = rotation
        self._last_angle = rotation
        self._visible = visible

        self._setup()

    def x(self, x: float = None) -> float:
        if x is not None:
            verify(x, (float, int))
            self.moveto(x, self.y())

        return self._location.x()

    def y(self, y: float = None) -> float:
        if y is not None:
            verify(y, (float, int))
            self.moveto(self.x(), y)

        return self._location.y()

    def location(self) -> Location:
        return self._location

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.move(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.moveto(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    def _translate(self, dx: float, dy: float) -> None:
        """
        Shift the object by (dx, dy) without rebuilding its geometry.

        A translation moves every vertex by the same delta and leaves the
        rotation untouched, so we can shift the canvas item relatively (a
        single C-level canvas op) and shift the cached vertices in place,
        rather than re-deriving them from the shape via _update_coords().
        """

        if dx == 0 and dy == 0:
            return

        for vertex in self._vertices:
            vertex._x += dx
            vertex._y += dy

        self._invalidate_render()
        self._sync_pen()

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the Renderable.

        :param width: the width to set to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int))
            self._width = width
            self._update_coords()

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the Renderable.

        :param height: the height to set to in pixels, if any
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int))
            self._height = height
            self._update_coords()

        return self._height

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center

        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Renderable
        """

        verify_keywords(kwargs, ('move_to', 'x', 'y', 'centroid'), 'Renderable#center()')

        centroid = kwargs.get('centroid', False)
        if type(centroid) is not bool:
            raise InvalidArgumentError(
                'Renderable#center(): centroid must be a bool.'
            )

        has_keyword_move = any(key in kwargs for key in ('move_to', 'x', 'y'))

        # Complete positional setters are the animation hot path. Dispatching
        # directly to _center preserves CustomPolygon specialization while
        # avoiding a current-center lookup, clone, and Location.moveto parse.
        if not has_keyword_move and len(args) == 2:
            x, y = args
            if ((type(x) is float or type(x) is int)
                    and (type(y) is float or type(y) is int)):
                return self._center(Location._raw(x, y), centroid=centroid)

        if not has_keyword_move and len(args) == 1:
            target = args[0]
            if type(target) is Location:
                return self._center(
                    Location._raw(target._x, target._y), centroid=centroid,
                )
            if (type(target) is tuple and len(target) == 2
                    and (type(target[0]) is float or type(target[0]) is int)
                    and (type(target[1]) is float or type(target[1]) is int)):
                return self._center(
                    Location._raw(target[0], target[1]), centroid=centroid,
                )

        # Complete keyword setters can skip the same current-center work. Keep
        # mixed move_to/x/y calls on the compatibility parser below, where the
        # later x/y values intentionally override move_to components.
        if len(args) == 0 and 'move_to' in kwargs \
                and 'x' not in kwargs and 'y' not in kwargs:
            target = kwargs['move_to']
            if type(target) is Location:
                return self._center(
                    Location._raw(target._x, target._y), centroid=centroid,
                )
            if (type(target) is tuple and len(target) == 2
                    and (type(target[0]) is float or type(target[0]) is int)
                    and (type(target[1]) is float or type(target[1]) is int)):
                return self._center(
                    Location._raw(target[0], target[1]), centroid=centroid,
                )

        if len(args) == 0 and 'move_to' not in kwargs \
                and 'x' in kwargs and 'y' in kwargs:
            x, y = kwargs['x'], kwargs['y']
            if ((type(x) is float or type(x) is int)
                    and (type(y) is float or type(y) is int)):
                return self._center(Location._raw(x, y), centroid=centroid)

        if len(args) == 0:
            # centroid is only a getter modifier; without an actual move request
            # (positional args or move_to/x/y) this is a pure getter.
            if not has_keyword_move:
                return self._center(centroid=centroid)

        location = Location(self._center(centroid=centroid))

        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0])
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected both x and y.'
                    )
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )

                location.moveto(args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                )

        if len(kwargs) != 0:
            # TODO: Shouldn't this be called "location", not "move_to"
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to'])
                else:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x'])
                else:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y'])
                else:
                    raise InvalidArgumentError(
                        'Renderable#center(): expected a tuple/Location or two numbers (x, y).'
                    )
        return self._center(location, centroid)

    def _center(self, move_to: Location = None, centroid: bool = False):
        if centroid:
            # This remains the historical vertex mean, not an area-weighted
            # polygon centroid.
            center_x = sum(vertex._x for vertex in self._vertices) / len(self._vertices)
            center_y = sum(vertex._y for vertex in self._vertices) / len(self._vertices)
        else:
            center_x = self._location._x + self._width / 2
            center_y = self._location._y + self._height / 2

        if move_to is not None:
            verify(move_to, Location)
            self.move(move_to._x - center_x, move_to._y - center_y)
            return move_to

        return Location._raw(center_x, center_y)

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the object.

        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the object's rotation in degrees
        """

        if angle is not None:
            verify(angle, (float, int))
            self._angle = angle
            self._update_coords()

        return self._angle % 360

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the object by a difference, in degrees

        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        verify(angle_diff, (float, int))
        self.rotation(self._angle + angle_diff)

    def angleto(self, obj) -> float:
        """
        Retrieve the angle between this object and another (based on 0 degrees at 12 o'clock)

        :param obj: the Object/Location to get the angle to.
        :return: the angle in degrees as a float
        """

        if isinstance(obj, Object):
            obj = obj.location()
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError(
                f'Renderable#angleto(): expected a Renderable or Location; received {type(obj)} ({obj!r}).'
            )

        location = Location(obj[0], obj[1])
        # theta = -math.atan2(location.x() - self.x(), location.y() - self.y()) - math.radians(self.rotation())
        theta = math.atan2(location.y() - self.center().y(), location.x() - self.center().x()) \
                - math.radians(self.rotation()) + math.pi / 2
        theta = math.degrees(theta)

        return theta

    def lookat(self, obj) -> None:
        """
        Look at another object (Objects or Locations)

        :param obj: the Object/Location to look at.
        :return: None
        """

        theta = self.angleto(obj)
        self.rotate(theta)

    def forward(self, distance: float) -> None:
        """
        Move the Renderable forward by distance at its current heading (rotation/angle)

        :param distance: the distance to move forward (hypotenuse)
        :return: None
        """

        dx = distance * math.sin(math.radians(self._angle))
        dy = distance * -math.cos(math.radians(self._angle))

        self.move(dx, dy)

    def backward(self, distance: float) -> None:
        """
        Move the Renderable backward by distance at its current heading (rotation/angle)

        :param distance: the distance to move backward (hypotenuse)
        :return: None
        """

        self.forward(-distance)

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the object

        :param color: the color to set to, if any
        :return: the color of the object
        """

        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            self._invalidate_render()

        return self._color

    def border(self, color: Color = None, width: float = None, fill: bool = None) -> Color:
        """
        Add or get the border of the object

        :param color: the color to set the border too, set to Color.NONE to remove border
        :param width: the width of the border
        :param fill: whether to fill the polygon.
        :return: The Color of the border
        """

        update = False

        if color is not None:
            verify(color, Color)
            self._border = color
            update = True
        if fill is not None:
            verify(fill, bool)
            self._fill = fill
            update = True
        if width is not None:
            verify(width, (float, int))
            self._border_width = width
            update = True

        if update:
            self._invalidate_render()

        return self._border

    def border_width(self, width: float = None) -> float:
        """
        Gets or sets the border width

        :param width: the border width to set to
        :return: the border width
        """

        if width is not None:
            verify(width, (float, int))
            self._border_width = width
            self._invalidate_render()

        return self._border_width

    def fill(self, fill: bool = None) -> bool:
        """
        Returns or sets the current fill boolean

        :param fill: a new fill value, whether to fill the polygon
        :return: the fill value
        """

        if fill is not None:
            verify(fill, bool)
            self._fill = fill
            self._invalidate_render()

        return self._fill

    def distance(self, obj) -> float:
        """
        Returns the distance between two objs or locations in pixels (center to center)

        :param obj: the Renderable/location to check distance between
        :return: the distance between this obj and the passed Renderable/Location.
        """

        if type(obj) is not Location and not isinstance(obj, Renderable):
            raise InvalidArgumentError(
                f'Renderable#distance(): expected a Renderable or Location; '
                f'received {type(obj)} ({obj!r}).'
            )

        location = obj if type(obj) is Location else obj.center()

        return math.sqrt((location.x() - self.center().x()) ** 2 + (location.y() - self.center().y()) ** 2)

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the renderable.

        :param visible: the new visibility value, if any
        :return: the visibility value
        """

        if visible is not None:
            verify(visible, bool)
            self._visible = visible
            self._invalidate_render()

        return self._visible

    def transform(self, transform: tuple = None) -> tuple:
        """
        Get or set the transform of the Renderable.
        Transforms represent the width, height, and rotation of Renderables.

        You can retrieve a Transform from a Renderable with this method and set the transform the same way.

        :param transform: the transform to set to, if any.
        :return: the transform
        """

        if transform is not None:
            verify(transform, tuple)
            if not len(transform) == 3:
                raise InvalidArgumentError(
                    'Renderable#transform(): expected (width, height, rotation).'
                )
            verify(transform[0], (float, int), transform[1], (float, int), transform[2], (float, int))

            update_width = transform[0] != self._width
            update_height = transform[1] != self._height
            update_rotation = transform[2] % 360 != self._angle % 360

            if not update_width and not update_height and not update_rotation:
                return self._width, self._height, self._angle % 360

            self._width = transform[0]
            self._height = transform[1]
            self._angle = transform[2]

            self._update_coords()

        return self._width, self._height, self._angle % 360

    def clone(self):
        """
        Clone this renderable!

        :return: a Renderable
        """

        constructor = type(self)
        return constructor(self._screen, self.x(), self.y(), self.width(), self.height(), self.color(), self.border(),
                           self.fill(), self.rotation(), self.visible())

    def vertices(self) -> list:
        """
        Returns the list of vertices for the Renderable.
        (The vertices will be returned clockwise, starting from the top-leftmost point)

        :return: a list of Locations representing the vertices
        """

        return self._get_vertices()

    # noinspection PyProtectedMember
    def bounds(self) -> (Location, float, float):
        """
        Get the location and dimensions of a bounding box that contains the entire shape

        :return: a tuple containing the Location, width, and height.
        """

        # Bounds only change when the object is moved/rotated/resized, so key a
        # cache on those transform parameters. Repeated queries between moves --
        # e.g. the same object across an all-pairs or one-vs-many overlaps() sweep
        # -- then reuse the result instead of re-querying the canvas each time.
        loc = self._location
        sig = (loc._x, loc._y, self._angle, self._width, self._height)
        if sig == self._bounds_sig:
            return self._bounds_cache

        vertices = self.vertices()
        x_values = [vertex.x() for vertex in vertices]
        y_values = [vertex.y() for vertex in vertices]
        result = (
            Location(min(x_values), min(y_values)),
            max(x_values) - min(x_values),
            max(y_values) - min(y_values),
        )

        self._bounds_sig = sig
        self._bounds_cache = result
        return result

    def contains(self, *args) -> bool:
        """
        Returns whether a Location is contained within the object.

        :param args: You may pass in either two numbers, a Location, or a tuple containing and x and y point.
        :return: a boolean value representing whether the point is within the vertices of the object.
        """

        x, y = 0, 0
        if len(args) == 1:
            verify(args[0], (tuple, Location))
            if type(args[0]) is Location:
                x = args[0].x()
                y = args[0].y()
            elif type(args[0]) is tuple and len(args[0]) == 2:
                x = args[0][0]
                y = args[0][1]
            else:
                raise InvalidArgumentError(
                    'Renderable#contains(): tuple arguments must contain exactly two values.'
                )
        elif len(args) == 2:
            verify(args[0], (float, int), args[1], (float, int))
            if type(args[0]) is not float and type(args[0]) is not int \
                    and type(args[1]) is not float and type(args[1]) is not int:
                raise InvalidArgumentError(
                    'Renderable#contains(): expected a tuple/Location or two numbers (x, y).'
                )
            x = args[0]
            y = args[1]
        else:
            raise InvalidArgumentError(
                'Renderable#contains(): expected a tuple/Location or two numbers (x, y).'
            )

        # If the point isn't remotely near us, we don't need to perform any calculations.
        if not isinstance(self, CustomRenderable) and self._angle == 0:
            if self.y() > 0 and self.x() > 0:
                if not (self.x() <= x <= (self.x() + self.width()) and self.y() <= y <= (self.y() + self.height())):
                    return False

        # the contains algorithm uses the line-intersects algorithm to determine if a point is within a polygon.
        # we are going to cast a ray from our point to the positive x. (left to right)

        # Pre-extract raw (x, y) floats once so the ray-cast loop does pure
        # float math instead of calling Location.x()/.y() on every vertex, every
        # pass. This is the single biggest cost for high-vertex shapes.
        vertices = [(vertex.x(), vertex.y()) for vertex in self.vertices()]
        return self._contains_point(vertices, x, y)

    @staticmethod
    def _contains_point(vertices: list, x: float, y: float) -> bool:
        """
        Test whether raw coordinates contain a point.

        This internal form skips public argument validation and lets collision
        checks reuse vertices that have already been converted to numeric tuples.
        """

        count = 0
        n = len(vertices)

        p1x, p1y = vertices[0]
        for i in range(1, n + 1):
            # A cool trick that gets the next index in an array, or the first index if i is the last index.
            # (since we start at index 1)
            p2x, p2y = vertices[i % n]

            # make sure we're in the ballpark on the y-axis (actually able to intersect on the x-axis)
            if y > (p1y if p1y < p2y else p2y):

                # Same thing as above
                if y <= (p1y if p1y > p2y else p2y):

                    # Make sure our x is at least less than the max x of this line. (since we're travelling right)
                    if x <= (p1x if p1x > p2x else p2x):

                        # If our y's are equal, that means this line is flat on the x, which makes us tricked until now.
                        # We now realize we were never in the ballpark in the first place.
                        if p1y != p2y:

                            # Now we get a possible intersection point from left to right.
                            intersects_x = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x

                            # if the line was vertical or we actually intersected it
                            if p1x == p2x or x <= intersects_x:
                                count += 1

            # move up the ladder next vertices and edge
            p1x, p1y = p2x, p2y

        return not (count % 2 == 0)

    def overlaps(self, other: 'Renderable') -> bool:
        """
        Returns if this object is overlapping with the passed object.

        :param other: another Renderable instance.
        :return: true if they are overlapping, false if not.
        """

        if not isinstance(other, Renderable):
            raise TypeError('Passed non-renderable into Renderable#overlaps(), which takes only Renderables!')

        if self._visible:
            bounds = self.bounds()
        else:
            bounds = Location(self.x() - self.width() * .5, self.y() - self.height() * .5), self.width() * 1.5, self.height() * 1.5

        if other._visible:
            other_bounds = other.bounds()
        else:
            other_bounds = Location(other.x() - other.width() * .5, other.y() - other.height() * .5), other.width() * 1.5, other.height() * 1.5

        min_ax = bounds[0].x()
        max_ax = min_ax + bounds[1]

        min_bx = other_bounds[0].x()
        max_bx = min_bx + other_bounds[1]

        min_ay = bounds[0].y()
        max_ay = min_ay + bounds[2]

        min_by = other_bounds[0].y()
        max_by = min_by + other_bounds[2]

        a_left_b = max_ax < min_bx
        a_right_b = min_ax > max_bx
        a_above_b = min_ay > max_by
        a_below_b = max_ay < min_by

        # Only optimize if the angle is not zero.
        # if self._angle % 360 == 0 and other._angle % 360 == 0:
        #     min_ax = x
        #     max_ax = x + width
        #
        #     min_bx = other_x
        #     max_bx = other_x + other_width
        #
        #     min_ay = y
        #     max_ay = y + height
        #
        #     min_by = other_y
        #     max_by = other_y + other_height
        #
        #     a_left_b = max_ax < min_bx
        #     a_right_b = min_ax > max_bx
        #     a_above_b = min_ay > max_by
        #     a_below_b = max_ay < min_by
        # else:
        #     hypotenuse = math.sqrt(width ** 2 + height ** 2) + 1
        #     other_hypotenuse = math.sqrt(other_width ** 2 + other_height ** 2) + 1
        #
        #     center = Location(x + width / 2, y + height / 2)
        #     other_center = Location(other_x + other_width / 2, other_y + other_height / 2)
        #
        #     min_ax = center.x() - (hypotenuse / 2)
        #     max_ax = center.x() + (hypotenuse / 2)
        #
        #     min_bx = other_center.x() - (other_hypotenuse / 2)
        #     max_bx = other_center.x() + (other_hypotenuse / 2)
        #
        #     min_ay = center.y() - (hypotenuse / 2)
        #     max_ay = center.y() + (hypotenuse / 2)
        #
        #     min_by = other_center.y() - (other_hypotenuse / 2)
        #     max_by = other_center.y() + (other_hypotenuse / 2)
        #
        #     a_left_b = max_ax < min_bx
        #     a_right_b = min_ax > max_bx
        #     a_above_b = min_ay > max_by
        #     a_below_b = max_ay < min_by

        # Do a base check to make sure they are even remotely near each other.
        # TODO: Re-optimize with rotation in mind.
        # if other._angle % 360 == 0 and self._angle % 360 == 0:
        if a_left_b or a_right_b or a_above_b or a_below_b:
            return False

        vertices1 = None
        vertices2 = None
        shape1 = None
        shape2 = None

        # Check if one shape is entirely inside the other shape
        if (min_ax >= min_bx and max_ax <= max_bx) and (min_ay >= min_by and max_ay <= max_by):
            vertices1 = self.vertices()
            point = vertices1[0]
            vertices2 = other.vertices()
            shape2 = [(vertex.x(), vertex.y()) for vertex in vertices2]
            if self._contains_point(shape2, point.x(), point.y()):
                return True

        if (min_bx >= min_ax and max_bx <= max_ax) and (min_by >= min_ay and max_by <= max_ay):
            if vertices2 is None:
                vertices2 = other.vertices()
            point = vertices2[0]
            if vertices1 is None:
                vertices1 = self.vertices()
            shape1 = [(vertex.x(), vertex.y()) for vertex in vertices1]
            if self._contains_point(shape1, point.x(), point.y()):
                return True

        # Next we are going to use a sweeping line algorithm.
        # Essentially we will process the lines on the x-axis, one coordinate at a time (imagine a vertical line scan).
        # Then we will look for their orientations. We will essentially make sure its impossible they do not cross.
        # Pre-extract raw (x, y) floats once. The edge-vs-edge test below is
        # O(n*m) and previously called Location.x()/.y() millions of times on
        # high-vertex shapes; from here on we work on plain float tuples instead.
        if shape1 is None:
            if vertices1 is None:
                vertices1 = self.vertices()
            shape1 = [(vertex.x(), vertex.y()) for vertex in vertices1]
        if shape2 is None:
            if vertices2 is None:
                # noinspection PyProtectedMember
                vertices2 = other.vertices()
            shape2 = [(vertex.x(), vertex.y()) for vertex in vertices2]

        # Orientation method that will determine if it is a triangle (and in what direction [cc or ccw]) or a line.
        def orientation(point1, point2, point3) -> int:
            """
            Internal method that will determine the orientation of three points. They can be a clockwise triangle,
            counterclockwise triangle, or a co-linear line segment.

            :param point1: the first point of the main line segment
            :param point2: the second point of the main line segment
            :param point3: the third point to check from another line segment
            :return: the orientation of the passed points (1 clockwise, -1 counter-clockwise, 0 co-linear)
            """
            result = (float(point2[1] - point1[1]) * (point3[0] - point2[0])) - \
                     (float(point2[0] - point1[0]) * (point3[1] - point2[1]))

            if result > 0:
                return 1
            elif result < 0:
                return -1
            else:
                return 0

        def point_on_segment(point1, point2, point3) -> bool:
            """
            Returns if point3 lies on the segment formed by point1 and point2.
            """

            return max(point1[0], point3[0]) >= point2[0] >= min(point1[0], point3[0]) \
                   and max(point1[1], point3[1]) >= point2[1] >= min(point1[1], point3[1])

        # Okay to begin actually detecting orientations, we want to loop through some edges. But only ones that are
        # relevant. In order to do this we will first have to turn the list of vertices into a list of edges.
        # Then we will look through the lists of edges and find the ones closest to each other.

        shape1_edges = []
        shape2_edges = []

        shape1 = tuple(shape1[:]) + (shape1[0],)
        shape2 = tuple(shape2[:]) + (shape2[0],)

        shape1_point1 = shape1[0]
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)]  # 1, 2, 3, 3 % 5
            shape1_edges.append((shape1_point1, shape1_point2))
            shape1_point1 = shape1_point2

        shape2_point1 = shape2[0]
        for i in range(1, len(shape2)):
            shape2_point2 = shape2[i % len(shape2)]
            shape2_edges.append((shape2_point1, shape2_point2))
            shape2_point1 = shape2_point2

        # Now we are going to test the four orientations that the segments form.
        # For each edge of shape1 we compute its bounding box once, then skip any
        # edge of shape2 whose bounding box cannot touch it -- this prunes the vast
        # majority of the O(n*m) pairs when the shapes only meet (or miss) in a
        # small region, which is the common case.
        for edge1 in shape1_edges:
            p1, p2 = edge1
            e1_min_x = p1[0] if p1[0] < p2[0] else p2[0]
            e1_max_x = p1[0] if p1[0] > p2[0] else p2[0]
            e1_min_y = p1[1] if p1[1] < p2[1] else p2[1]
            e1_max_y = p1[1] if p1[1] > p2[1] else p2[1]

            for edge2 in shape2_edges:
                p3, p4 = edge2

                # Reject this pair if the two edges' bounding boxes don't overlap;
                # disjoint boxes can neither cross nor share a co-linear point.
                if e1_max_x < (p3[0] if p3[0] < p4[0] else p4[0]) or \
                        (p3[0] if p3[0] > p4[0] else p4[0]) < e1_min_x or \
                        e1_max_y < (p3[1] if p3[1] < p4[1] else p4[1]) or \
                        (p3[1] if p3[1] > p4[1] else p4[1]) < e1_min_y:
                    continue

                orientation1 = orientation(edge1[0], edge1[1], edge2[0])
                orientation2 = orientation(edge1[0], edge1[1], edge2[1])
                orientation3 = orientation(edge2[0], edge2[1], edge1[0])
                orientation4 = orientation(edge2[0], edge2[1], edge1[1])

                # If orientations 1 and 2 are strictly opposite as well as 3 and 4 then they intersect!
                # (Strict opposite signs -- a plain != would count a co-linear 0 as a crossing and
                # mis-fire on floating-point-collinear edges that don't actually touch.)
                if orientation1 * orientation2 < 0 and orientation3 * orientation4 < 0:
                    return True

                # There's some special cases we should check where a point from one segment is on the other segment
                if orientation1 == 0 and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True

                if orientation2 == 0 and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True

                if orientation3 == 0 and point_on_segment(edge2[0], edge1[0], edge2[1]):
                    return True

                if orientation4 == 0 and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False

    def _get_vertices(self):
        real_shape = self._vertices
        return real_shape

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occurred while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)')

        shape = self._shape  # List of normal vertices.

        width = self._width
        height = self._height

        scale_factor = (width / PIXEL_RATIO, height / PIXEL_RATIO)

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape]

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy)

            vertex.move(self.x() + width / 2, self.y() + height / 2)

        self._vertices = vertices

        self._vertices = self._rotate(self._vertices, self._angle)
        self._register_render()

    def _rotate(self, vertices: list, angle: float, pivot: Location = None) -> list:
        # We have to update here since we cannot remember previous rotations (update method call won't cut it)!
        # vertices = self._vertices

        # First get some values that we're going to use later
        theta = math.radians(angle)
        cosine = math.cos(theta)
        sine = math.sin(theta)

        if pivot is None:
            centroid_x = self.center().x()
            centroid_y = self.center().y()
        else:
            centroid_x = pivot.x()
            centroid_y = pivot.y()

        new_vertices = []
        for vertex in vertices:
            # We have to create these separately because they're ironically used in each other's calculations xD
            old_x = vertex.x() - centroid_x
            old_y = vertex.y() - centroid_y

            new_x = (old_x * cosine - old_y * sine) + centroid_x
            new_y = (old_x * sine + old_y * cosine) + centroid_y
            new_vertices.append(Location(new_x, new_y))

        return new_vertices

    def _update_coords(self):
        shape = self._shape  # List of normal vertices.

        # Hoist per-object constants out of the vertex loops. (cx/cy were always
        # 0, so the old `(v - c) + c` was a no-op.)
        scale_x = self._width / PIXEL_RATIO
        scale_y = self._height / PIXEL_RATIO
        offset_x = self.x() + self._width / 2
        offset_y = self.y() + self._height / 2

        # Build the final vertices directly, instead of creating each Location
        # and then re-parsing args through moveto()/move() per vertex.
        vertices = [Location._raw(scale_x * vertex[0] + offset_x,
                                  -scale_y * vertex[1] + offset_y) for vertex in shape]

        if self._angle % 360 != 0:
            vertices = self._rotate(vertices, self._angle)
        self._vertices = vertices
        self._invalidate_render()

    def update(self):
        self._check()
        self._update_coords()
        self._last_angle = self._angle


class CustomRenderable(Renderable):
    """
    A wrapper class to distintify classes that extend Renderable but have some custom functionality.
    """
    pass


class RoundedRectangle(CustomRenderable):
    """
    A rectangle with rounded corners.
    """

    @overload(Screen, (int, float), (int, float), (int, float), (int, float),
              Color, Color, bool, (int, float), bool, (int, float))
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 radius: float = 10):
        self._radius = self._validate_radius(radius)
        super().__init__(screen, x, y, width, height, color, border,
                         fill, rotation, visible)

    @overload(Screen, Location, (int, float), (int, float), Color, Color,
              bool, (int, float), bool, (int, float))
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True,
                 radius: float = 10):
        self._radius = self._validate_radius(radius)
        super().__init__(screen, location.x(), location.y(), width, height,
                         color, border, fill, rotation, visible)

    def radius(self, radius: float = None) -> float:
        """
        Set the corner radius of the rounded shape in pixels.

        :param radius: the radius to set
        :return: the radius
        """

        if radius is not None:
            self._radius = self._validate_radius(radius)
            self._update_coords()

        return self._radius

    @staticmethod
    def _validate_radius(radius):
        verify(radius, (float, int))
        if radius < 0:
            raise InvalidArgumentError(
                'RoundedRectangle#radius(): radius must be non-negative.'
            )
        return radius

    def clone(self) -> 'RoundedRectangle':
        clone = RoundedRectangle(
            self._screen,
            self.x(),
            self.y(),
            self.width(),
            self.height(),
            self.color(),
            self.border(),
            self.fill(),
            self.rotation(),
            self.visible(),
            self.radius(),
        )
        clone.border_width(self.border_width())
        return clone

    def _setup(self):
        self._rebuild_vertices()
        self._register_render()

    def _rebuild_vertices(self):
        radius = min(self._radius, abs(self._width) / 2, abs(self._height) / 2)
        x = self.x()
        y = self.y()
        width = self._width
        height = self._height

        if radius == 0:
            vertices = [
                Location._raw(x, y),
                Location._raw(x + width, y),
                Location._raw(x + width, y + height),
                Location._raw(x, y + height),
            ]
        else:
            segments = max(2, min(8, int(math.ceil(radius / 4))))
            corners = (
                (x + width - radius, y + radius, -90),
                (x + width - radius, y + height - radius, 0),
                (x + radius, y + height - radius, 90),
                (x + radius, y + radius, 180),
            )
            vertices = []
            for center_x, center_y, start_angle in corners:
                for step in range(segments + 1):
                    angle = math.radians(start_angle + 90 * step / segments)
                    vertices.append(Location._raw(
                        center_x + radius * math.cos(angle),
                        center_y + radius * math.sin(angle),
                    ))

        if self._angle % 360 != 0:
            vertices = self._rotate(vertices, self._angle)
        self._vertices = vertices

    def _update_coords(self):
        self._rebuild_vertices()
        self._invalidate_render()

    def update(self):
        self._check()
        self._update_coords()


# noinspection PyProtectedMember
class CustomPolygon(CustomRenderable):
    """
    An Irregular Polygon that is passed a list of vertices that can be rotated and translated!
    """

    # The below "# noqa" removes a small inspection by pycharm as it complains we do not call the constructor.
    def __init__(self, screen: Screen, vertices: list,  # noqa
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._screen = screen
        self._color = color
        self._border = border if border is not None else Color.NONE
        self._border_width = 1
        self._fill = fill
        self._angle = rotation
        self._visible = visible

        self._screen._add(self)

        if len(vertices) < 3:
            raise InvalidArgumentError(
                'CustomPolygon(): expected at least three vertices.'
            )

        xmin = vertices[0][0]
        xmax = vertices[0][0]
        ymin = vertices[0][1]
        ymax = vertices[0][1]

        real_vertices = []
        for vertex in vertices:
            new_vertex = Location(vertex[0], vertex[1])
            real_vertices.append(new_vertex)

            if new_vertex.x() < xmin:
                xmin = new_vertex.x()
            if new_vertex.x() > xmax:
                xmax = new_vertex.x()

            if new_vertex.y() < ymin:
                ymin = new_vertex.y()
            if new_vertex.y() > ymax:
                ymax = new_vertex.y()

        self._vertices = real_vertices
        self._current_vertices = [vertex.clone() for vertex in real_vertices]

        # Pending translation not yet folded into _current_vertices. move() just
        # accumulates the delta here (O(1)); vertices() applies it once, lazily,
        # collapsing any run of moves into a single pass. See _flush_vertices().
        self._vertex_offset = [0.0, 0.0]

        self._location = Location(xmin, ymin)
        self._base_width = self._width = xmax - xmin
        self._base_height = self._height = ymax - ymin

        self._base_location = self._location.clone()
        self._base_center = Location(
            sum(vertex.x() for vertex in self._vertices) / len(self._vertices),
            sum(vertex.y() for vertex in self._vertices) / len(self._vertices),
        )

        self._register_render()

        if self._angle % 360 != 0:
            self._update_coords()

        self._pen = None

    def move(self, *args, **kwargs):
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.move(*args, **kwargs)  # Does the arg parsing for us

        # Use a relative canvas move (exact) rather than moveto(), which
        # positions by the item's bounding box and lands 1px off because the
        # outline inflates the bbox beyond the geometry coordinates.
        dx = self._location._x - before_x
        dy = self._location._y - before_y
        if dx == 0 and dy == 0:
            return
        self._vertex_offset[0] += dx
        self._vertex_offset[1] += dy
        self._invalidate_render()
        self._sync_pen()

    def moveto(self, *args, **kwargs):
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.moveto(*args, **kwargs)

        # Relative canvas move by the delta (see move() for why not moveto()).
        dx = self._location._x - before_x
        dy = self._location._y - before_y
        if dx == 0 and dy == 0:
            return
        self._vertex_offset[0] += dx
        self._vertex_offset[1] += dy
        self._invalidate_render()
        self._sync_pen()

    def width(self, width: float = None) -> float:
        """
        Get the width of the CustomPolygon

        :param width: the new width to scale to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int))

            if self._width == width:
                return width

            self._width = width
            self._update_coords()

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get the height of the Polygon

        :param height: The new height to scale to in px.
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int))

            if self._height == height:
                return height

            self._height = height
            self._update_coords()

        return self._height

    def rotate(self, angle_diff: float = 0) -> None:
        verify(angle_diff, (float, int))

        if angle_diff == 0:
            return

        self._angle += angle_diff

        if self._angle >= 360:
            self._angle = self._angle % 360

        self._update_coords()

    def rotation(self, angle: float = None) -> float:
        """
        Gets or sets the rotation of the CustomPolygon.

        :param angle: the angle to rotate the polygon to
        :return: the angle that was set
        """

        if angle is not None:
            verify(angle, (float, int))

            if angle % 360 == self._angle % 360:
                return self._angle

            self._angle = angle
            self._update_coords()

        return self._angle

    def _center(self, move_to: Location = None, centroid: bool = False) -> Location:
        if not centroid:
            center = Location(
                self._location.x() + self._width / 2,
                self._location.y() + self._height / 2,
            )

            if move_to is not None:
                verify(move_to, Location)
                self.move(move_to.x() - center.x(), move_to.y() - center.y())
                center.moveto(move_to)

            return center

        # We are going to create a centroid, so we can rotate the points around a realistic center
        # Sorry for those of you that get weird rotations..
        x_list = []
        y_list = []
        for vertex in self.vertices():
            x_list.append(vertex.x())
            y_list.append(vertex.y())

        # Create a simple centroid (not full centroid)
        centroid_x = sum(x_list) / len(y_list)
        centroid_y = sum(y_list) / len(x_list)

        center = Location(centroid_x, centroid_y)

        if move_to is not None:
            verify(move_to, Location)
            self.move(move_to.x() - center.x(), move_to.y() - center.y())
            center.moveto(move_to)

        return center

    def _flush_vertices(self) -> None:
        # Fold any pending translation into the cached vertices. Called by every
        # path that reads live geometry, so a run of moves collapses into a
        # single O(n) pass here instead of one pass per move.
        dx, dy = self._vertex_offset
        if dx or dy:
            for vertex in self._current_vertices:
                vertex._x += dx
                vertex._y += dy
            self._vertex_offset[0] = 0.0
            self._vertex_offset[1] = 0.0

    def vertices(self) -> list:
        # Collision loops (contains/overlaps) call this repeatedly. Moves only
        # accumulate an offset; we apply it here, once, then reuse the cached
        # list until the object moves again.
        self._flush_vertices()
        return self._current_vertices

    def clone(self) -> 'CustomPolygon':
        """
        Clone this CustomPolygon!

        :return: a CustomPolygon
        """

        poly = CustomPolygon(self._screen, self._vertices, self._color, self._border, self._fill, 0,
                             self._visible)
        poly.transform(self.transform())
        poly.moveto(self.location())

        return poly

    def _update_coords(self):
        """Rebuild the live geometry from the immutable base vertices and transform."""
        self._check()

        # _location already includes every lazy translation.
        self._vertex_offset[0] = 0.0
        self._vertex_offset[1] = 0.0

        scale_factor = (
            self._width / self._base_width if self._base_width != 0 else 0,
            self._height / self._base_height if self._base_height != 0 else 0,
        )

        centroid_x = self._location.x() + (
            self._base_center.x() - self._base_location.x()
        ) * scale_factor[0]
        centroid_y = self._location.y() + (
            self._base_center.y() - self._base_location.y()
        ) * scale_factor[1]

        theta = math.radians(self._angle)
        cosine = math.cos(theta)
        sine = math.sin(theta)

        rotated = self._angle % 360 != 0

        for index, vertex in enumerate(self._vertices):
            old_x = self._location.x() + (
                vertex.x() - self._base_location.x()
            ) * scale_factor[0]
            old_y = self._location.y() + (
                vertex.y() - self._base_location.y()
            ) * scale_factor[1]

            if rotated:
                relative_x = old_x - centroid_x
                relative_y = old_y - centroid_y
                new_x = relative_x * cosine - relative_y * sine + centroid_x
                new_y = relative_x * sine + relative_y * cosine + centroid_y
            else:
                new_x = old_x
                new_y = old_y

            current_vertex = self._current_vertices[index]
            current_vertex._x = new_x
            current_vertex._y = new_y

        self._invalidate_render()

    def update(self):
        self._check()
        self._update_coords()


class Rectangle(Renderable):

    # Two constructor forms: (x, y) and (location). The dispatcher honors
    # default arguments, so each full signature also covers every shorter call
    # that omits trailing optional args (color, border, fill, rotation, visible).
    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                          Location(x, y + height)]
        self._shape = ((-10, 10), (10, 10), (10, -10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    @overload(Screen, Location, (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x()
        y = location.y()

        self._vertices = [Location(x, y), Location(x + width, y), Location(x + width, y + height),
                          Location(x, y + height)]
        self._shape = ((-10, 10), (10, 10), (10, -10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)


class Oval(Renderable):

    _default = ((10, 0), (9.51, 3.09), (8.09, 5.88),
                (5.88, 8.09), (3.09, 9.51), (0, 10), (-3.09, 9.51),
                (-5.88, 8.09), (-8.09, 5.88), (-9.51, 3.09), (-10, 0),
                (-9.51, -3.09), (-8.09, -5.88), (-5.88, -8.09),
                (-3.09, -9.51), (-0.00, -10.00), (3.09, -9.51),
                (5.88, -8.09), (8.09, -5.88), (9.51, -3.09))

    # Two constructor forms: (x, y) and (location). The dispatcher honors
    # default arguments, so each full signature also covers every shorter call.
    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._width = width
        self._height = height
        self._custom_wedges = False

        vertices = self._convert_vertices()
        self._shape = vertices
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    @overload(Screen, Location, (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x()
        y = location.y()

        self._width = width
        self._height = height
        self._custom_wedges = False

        vertices = self._convert_vertices()
        self._shape = vertices
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the object.

        :param width: the width to set to in pixels, if any
        :return: the width of the object
        """

        if width is not None:
            verify(width, (float, int))
            self._width = width
            self._update_coords()

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the object.

        :param height: the width to set to in pixels, if any
        :return: the height of the object
        """

        if height is not None:
            verify(height, (float, int))
            self._height = height
            self._update_coords()

        return self._height

    def wedges(self, wedges: int = None) -> int:
        if wedges is not None:
            verify(wedges, int)
            if wedges < 20:
                raise InvalidArgumentError('Oval(): wedges must be at least 20.')
            self._shape = self._generate_vertices(PIXEL_RATIO / 2, wedges=wedges)
            self._wedges = wedges
            self._custom_wedges = True
            self._update_coords()

        return self._wedges

    def slices(self) -> list:
        """
        Gets the slices of the Oval based on wedges. Note that this generates slices that are not tied to the oval,
        these are simply slices of the oval based on its wedges. You can use them how you see fit.

        :return: a tuple (immutable list) of CustomPolygons
        """

        return self._generate_slices()

    def _generate_slices(self) -> list:
        shape = self.vertices()
        shape = tuple(shape[:]) + (shape[0],)

        slices = []
        for i in range(0, len(shape) - 1):
            vertex1 = shape[i]
            vertex2 = self.center()
            vertex3 = shape[i + 1]

            slc = CustomPolygon(self._screen, [vertex1, vertex2, vertex3], self.color())
            slices.append(slc)
        return slices

    def _convert_vertices(self):
        radius = ((self._width + self._height) / 2) / 2
        angle = 18 if radius <= 150 else (radius * 9) / 300
        shape_vertices = self._generate_vertices(PIXEL_RATIO / 2, angle)

        # Report the wedge count actually generated (size-dependent), not a fixed default.
        self._wedges = len(shape_vertices)

        return shape_vertices

    def _render_node(self):
        return EllipseNode(
            self._render_id,
            (self.x() + self._width / 2, self.y() + self._height / 2),
            self._width / 2,
            self._height / 2,
            self._angle,
            tuple((vertex.x(), vertex.y()) for vertex in self.vertices()),
            self._custom_wedges,
            self._render_color(self._color) if self._fill else None,
            self._render_color(self._border),
            self._border_width,
            self._visible,
        )

    @staticmethod
    def _generate_vertices(radius, angle: float = 18, wedges: int = None):
        relative_vertices = []

        if wedges is not None:
            angle = 360 / wedges

        for x in range(0, 360, int(angle)):
            radians = math.radians(x)
            x = radius * math.cos(radians)
            y = radius * math.sin(radians)
            relative_vertices.append((x, y))

        return relative_vertices


class Triangle(Renderable):

    # Two constructor forms: (x, y) and (location). The dispatcher honors
    # default arguments, so each full signature also covers every shorter call.
    @overload(Screen, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    @overload(Screen, Location, (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        x = location.x()
        y = location.y()

        self._shape = ((10, -10), (0, 10), (-10, -10))
        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)


class Polygon(Renderable):

    # Two constructor forms: (num_sides, x, y) and (num_sides, location). The
    # dispatcher honors default arguments, so each full signature also covers
    # every shorter call.
    @overload(Screen, int, (int, float), (int, float), (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, num_sides: int, x: float, y: float, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        if num_sides < 3:
            raise InvalidArgumentError('Polygon(): num_sides must be at least 3.')

        self._num_sides = num_sides
        radius = PIXEL_RATIO / 2
        shape_points = []
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)))
        self._shape = shape_points

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    @overload(Screen, int, Location, (int, float), (int, float), Color, Color, bool, int, bool)
    def __init__(self, screen: Screen, num_sides: int, location: Location, width: float, height: float,
                 color: Color = Color('black'),
                 border: Color = None,
                 fill: bool = True,
                 rotation: float = 0,
                 visible: bool = True):
        if num_sides < 3:
            raise InvalidArgumentError('Polygon(): num_sides must be at least 3.')

        x = location.x()
        y = location.y()

        self._num_sides = num_sides
        radius = PIXEL_RATIO / 2
        shape_points = []
        for i in range(num_sides):
            shape_points.append((radius * math.sin(2 * math.pi / num_sides * i),
                                 radius * math.cos(2 * math.pi / num_sides * i)))
        self._shape = shape_points

        super().__init__(screen, x, y, width, height, color, border, fill, rotation, visible)

    def _setup(self):
        if not hasattr(self, '_shape'):
            raise AttributeError('An error occured while initializing a Renderable: '
                                 'Is _shape set? (Advanced Users Only)')

        shape = self._shape  # List of normal vertices.

        a = math.pi * 2 / self._num_sides * (PIXEL_RATIO / 2)
        n = self._num_sides

        # Degree converted to radians
        apothem = a / (2 * math.tan((180 / n) *
                                    math.pi / 180))

        true_width = PIXEL_RATIO
        true_height = apothem * 2

        width = self._width
        height = self._height

        scale_factor = (width / true_width, height / true_height)

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape]

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy)

            vertex.move(self.x() + width / 2, self.y() + height / 2)
            vertex.move(dy=PIXEL_RATIO - true_height)

        self._vertices = vertices

        self._vertices = self._rotate(self._vertices, self._angle)
        self._register_render()

    def clone(self) -> 'Polygon':
        """
        Clone this Polygon!

        :return a Polygon
        """
        return Polygon(self._screen, self._num_sides, self.x(), self.y(), self.width(), self.height(), self.color(), self.border(), self.fill(), self.rotation(), self.visible())

    # noinspection PyProtectedMember
    def update(self):
        self._check()
        shape = self._shape  # List of normal vertices.

        a = math.pi * 2 / self._num_sides * (PIXEL_RATIO / 2)
        n = self._num_sides

        # Degree converted to radians
        apothem = a / (2 * math.tan((180 / n) *
                                    math.pi / 180))

        true_width = PIXEL_RATIO
        true_height = apothem * 2

        width = self._width
        height = self._height

        scale_factor = (width / true_width, height / true_height)

        cx = 0
        cy = 0

        vertices = [Location(vertex[0], vertex[1]) for vertex in shape]

        for vertex in vertices:
            vertex.moveto(scale_factor[0] * (vertex.x() - cx) + cx, -scale_factor[1] * (vertex.y() - cy) + cy)

            vertex.move(self.x() + width / 2, self.y() + height / 2)
            vertex.move(dy=PIXEL_RATIO - true_height)

        self._vertices = vertices

        self._vertices = self._rotate(self._vertices, self._angle)
        self._invalidate_render()


class Image(Renderable):
    """
    Image class. Supports basic formats: PNG, GIF, JPG, PPM, images.

    NOTE: This class supports the basic displaying of images, but also supports much more,
    such as image modification (width, height, color, etc) if you have PIL (Pillow) installed!
    You can install PIL/Pillow by running: `pip install pillow` in a terminal!
    """

    # (x, y) INITIALIZERS

    # Two constructor forms: (x, y) and (location). The dispatcher honors default
    # arguments, so each full signature also covers every shorter call. Only the
    # screen and image path are required; x, y, width and height all default.
    @overload(Screen, str, (int, float), (int, float), (int, float), (int, float), Color, Color, int, bool)
    def __init__(self, screen: Screen, image: str, x: float = 0, y: float = 0,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._init_image(screen, image, x, y, width, height, color, border, rotation, visible)

    @overload(Screen, str, Location, (int, float), (int, float), Color, Color, int, bool)
    def __init__(self, screen: Screen, image: str, location: Location,
                 width: float = None,
                 height: float = None,
                 color: Color = None,
                 border: Color = Color.NONE,
                 rotation: float = 0,
                 visible: bool = True):
        self._init_image(screen, image, location.x(), location.y(),
                         width, height, color, border, rotation, visible)

    def _init_image(self, screen, image, x, y, width, height, color, border, rotation, visible):
        self._image_name = image

        self._width, self._height = screen._backend.measure_image(image)

        self._frame = -1
        self._frames = -1

        self._mask = 123

        # Resample quality for resize/rotate. True (default) keeps the smooth
        # LANCZOS/BILINEAR filters; False uses NEAREST, which is ~13x cheaper on
        # rotation and ideal for pixel-art sprites in a game loop.
        self._smooth = True

        # Flips are retained as source-image state so they survive later image
        # rebuilds caused by resizing, tinting, borders, rotation, or GIF frames.
        self._flip_x = False
        self._flip_y = False

        super().__init__(screen, x, y, self._width, self._height, color=Color.NONE, border=border,
                         rotation=rotation, visible=visible)

        if width is not None and width != self._width:
            self.width(width)
        if height is not None and height != self._height:
            self.height(height)

        if color is not None:
            self.color(color)

        if border is not None and border != Color.NONE:
            self.border(border)

    # noinspection PyProtectedMember
    def _setup(self):
        self._vertices = self.vertices()
        self._register_render()

    def _render_node(self):
        return ImageNode(
            self._render_id,
            self._image_name,
            (self.x(), self.y()),
            self._width,
            self._height,
            self._angle,
            None if self._color == Color.NONE else self._color.rgb(),
            self._mask,
            None if self._border == Color.NONE else self._border.rgb(),
            self._smooth,
            self._flip_x,
            self._flip_y,
            self._frame,
            self._visible,
        )

    # def moveto(self, *args, **kwargs) -> None:
    #     """
    #     Move to a new location takes a Location, tuple, or two numbers (x, y)
    #     :return: None
    #     """
    #
    #     self._location.moveto(*args, **kwargs)
    #
    #     # self._update_coords()
    #     self.update()

    def width(self, width: float = None) -> float:
        """
        Get or set the width of the image (REQUIRES: PIL or Pillow)

        :param width: the width to set to, if any
        :return: None
        """

        if width is not None:
            verify(width, (float, int))

            if self._width == width:
                return width

            self._width = width
            self.update(True)

        return self._width

    def height(self, height: float = None) -> float:
        """
        Get or set the height of the image

        :param height: the height to set to, if any
        :return: the height
        """

        if height is not None:
            verify(height, (float, int))

            if self._height == height:
                return height

            self._height = height
            self.update(True)

        return self._height

    def color(self, color: Color = None, alpha: int = 123) -> Color:
        """
        Retrieves or applies a color-mask to the image

        :param color: the color to mask to, if any
        :param alpha: The alpha level of the mask, defaults to 123 (half of 255)
        :return: the mask-color of the object
        """

        if color is not None:
            verify(color, Color)

            if self._color == color and self._mask == alpha:
                return self._color

            self._color = color
            self._mask = alpha
            self.update(True)

        return self._color

    def smooth(self, smooth: bool = None) -> bool:
        """
        Get or set the resampling quality used when resizing/rotating the image.

        True (default) uses smooth filters (LANCZOS/BILINEAR); False uses NEAREST,
        which is dramatically faster (~13x on rotation) and crisp for pixel-art
        sprites - ideal in a game loop.

        :param smooth: True for smooth, False for fast/nearest, if setting
        :return: whether smooth resampling is enabled
        """

        if smooth is not None:
            verify(smooth, bool)
            self._smooth = smooth
            self.update(True)

        return self._smooth

    def rotation(self, angle: float = None) -> float:
        """
        Get or set the rotation of the image.

        :param angle: the angle to set the rotation to in degrees, if any
        :return: the angle of the image's rotation in degrees
        """

        if angle is not None:
            verify(angle, (float, int))

            if self._angle == angle:
                return angle % 360

            self._angle = angle
            self.update(True)

        return self._angle % 360

    # noinspection PyMethodOverriding
    def rotate(self, angle_diff: float) -> None:
        """
        Rotate the angle of the image by a difference, in degrees

        :param angle_diff: the angle difference to rotate by
        :return: None
        """

        if angle_diff != 0:
            verify(angle_diff, (float, int))
            self._angle += angle_diff
            self.update(True)

    def transform(self, transform: tuple = None) -> tuple:
        """
        Get or set the transform of the Image.
        Transforms represent the width, height, and rotation of the Image.

        You can retrieve a Transform from an Image with this method and set the transform the same way.

        :param transform: the transform to set to, if any.
        :return: the transform
        """

        if transform is not None:
            verify(transform, tuple)
            if not len(transform) == 3:
                raise InvalidArgumentError(
                    'Image#transform(): expected (width, height, rotation).'
                )
            verify(transform[0], (float, int), transform[1], (float, int), transform[2], (float, int))

            update_width = transform[0] != self._width
            update_height = transform[1] != self._height
            update_rotation = transform[2] % 360 != self._angle % 360

            if not update_width and not update_height and not update_rotation:
                return self._width, self._height, self._angle % 360

            self._width = transform[0]
            self._height = transform[1]
            self._angle = transform[2]

            self.update(True)

        return self._width, self._height, self._angle % 360



    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center

        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Image
        """

        verify_keywords(kwargs, ('move_to', 'x', 'y'), 'Image#center()')

        if len(args) == 0 and len(kwargs) == 0:
            return self._center()

        location = Location(self._center())
        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0])
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError('Image#center(): expected both x and y.')
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )

                location.moveto(args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Image#center(): expected a tuple/Location or two numbers (x, y).'
                )

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to'])
                else:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x'])
                else:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y'])
                else:
                    raise InvalidArgumentError(
                        'Image#center(): expected a tuple/Location or two numbers (x, y).'
                    )

        return self._center(location)

    def _center(self, moveto: Location = None) -> Location:
        if moveto is not None:
            verify(moveto, Location)
            self.moveto(moveto.x() - self.width() / 2, moveto.y() - self.height() / 2)

        return Location(self.x() + self.width() / 2, self.y() + self.height() / 2)

    # noinspection PyMethodOverriding
    def border(self, color: Color = None) -> Color:
        """
        Add or get the border of the image

        :param color: the color to set the border too, set to Color.NONE to remove border
        :return: The Color of the border
        """

        if color is not None:
            verify(color, Color)
            self._border = color
            self.update(True)

        return self._border

    def fill(self, fill: bool = None) -> bool:
        """
        Unsupported: This doesn't make sense for images.
        """

        raise UnsupportedError('Image#fill(): fill is unsupported for images.')

    def vertices(self) -> list:
        """
        Returns the list of vertices for the Renderable.
        (The vertices will be returned clockwise, starting from the top-leftmost point)

        :return: a list of Locations representing the vertices
        """

        # Note: the first vertex is a clone of the location, not self.location()
        # itself - _setup() caches vertices() into self._vertices, and
        # _translate() shifts every cached vertex in place. Aliasing the live
        # location here would let a move shift it twice (once via _location.move,
        # once via the vertex loop), doubling the displacement. The remaining
        # vertices are built from known numbers, so we use the _raw fast path.
        x = self.x()
        y = self.y()
        w = self.width()
        h = self.height()
        vertices = [self.location().clone(), Location._raw(x + w, y),
                    Location._raw(x + w, y + h),
                    Location._raw(x, y + h)]

        if self._angle != 0:

            # First get some values that we're going to use later
            theta = math.radians(self._angle)
            cosine = math.cos(theta)
            sine = math.sin(theta)

            center_x = x + w / 2
            center_y = y + h / 2

            new_vertices = []
            for vertex in vertices:
                # We have to create these separately because they're ironically used in each other's calculations xD
                old_x = vertex.x() - center_x
                old_y = vertex.y() - center_y

                new_x = (old_x * cosine - old_y * sine) + center_x
                new_y = (old_x * sine + old_y * cosine) + center_y
                new_vertices.append(Location._raw(new_x, new_y))

            vertices = new_vertices

        return vertices

    def flip(self, axis: str = 'y') -> None:
        """
        Flip the image across an axis.

        Flipping across the x-axis reverses the image vertically; flipping
        across the y-axis reverses it horizontally. Calling this method again
        with the same axis restores the original orientation.

        Requires PIL/Pillow.

        :param axis: the axis to flip across, either ``'x'`` or ``'y'``
        :return: None
        """

        verify(axis, str)
        axis = axis.lower()
        if axis == 'x':
            self._flip_x = not self._flip_x
        elif axis == 'y':
            self._flip_y = not self._flip_y
        else:
            raise InvalidArgumentError("Image#flip(): axis must be 'x' or 'y'.")

        self.update(True)

    def load(self) -> None:
        """
        Load animated GIF (reads frames)

        :return: None
        """

        self._frames = self._screen._backend.image_frames(self._image_name)
        self._frame = 0
        self._invalidate_render()

    def next(self) -> None:
        """
        Changes frame to the next frame (Can only be used with animated GIFs)

        :return:
        """
        self._frame += 1

        if self._frame >= self._frames:
            self._frame = 0

        self.update(True)

    def frame(self, frame: int = None) -> int:
        """
        Set the current frame.

        :param frame: the frame-index to set to
        :return: the current frame
        """

        if frame is not None:
            self._frame = frame
            self.update(True)

        return self._frame

    def frames(self) -> int:
        """
        Returns how many frames there are, returns -1 if not animated, 0 if corrupted file.

        :return:
        """

        return self._frames

    def clone(self) -> 'Image':
        constructor = type(self)
        clone = constructor(self._screen, self._image_name, self.x(), self.y(), self.width(), self.height(),
                            self.color(), self.border(), self.rotation(), self.visible())
        clone._flip_x = self._flip_x
        clone._flip_y = self._flip_y
        if clone._flip_x or clone._flip_y:
            clone._invalidate_render()

        return clone

    def _update_coords(self):
        """
        Usually used to update x/y or vertices, but in this case we just update our width and height
        """
        self._check()
        self._vertices = self.vertices()
        self._invalidate_render()


    # noinspection PyProtectedMember
    def update(self, updated: bool = False):
        self._check()
        self._vertices = self.vertices()
        self._invalidate_render()


class Text(CustomRenderable):
    _aligns = ('left', 'center', 'right')

    # Four constructor forms ((x, y)/(location), each with optional Color) defer to _init_text.
    # noinspection PyProtectedMember
    @overload(Screen, str, (int, float), (int, float))
    def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        self._init_text(screen, text, x, y, color, font, size, align,
                        bold, italic, underline, strikethrough, rotation, visible)

    @overload(Screen, str, (int, float), (int, float), Color)
    def __init__(self, screen: Screen, text: str, x: float, y: float, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        self._init_text(screen, text, x, y, color, font, size, align,
                        bold, italic, underline, strikethrough, rotation, visible)

    @overload(Screen, str, Location)
    def __init__(self, screen: Screen, text: str, location: Location, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        self._init_text(screen, text, location.x(), location.y(), color, font, size, align,
                        bold, italic, underline, strikethrough, rotation, visible)

    @overload(Screen, str, Location, Color)
    def __init__(self, screen: Screen, text: str, location: Location, color: Color = Color('black'),  # noqa
                 font: str = 'Arial', size: int = 16, align: str = 'left', bold: bool = False, italic: bool = False,
                 underline: bool = False, strikethrough: bool = False, rotation: float = 0, visible: bool = True):
        self._init_text(screen, text, location.x(), location.y(), color, font, size, align,
                        bold, italic, underline, strikethrough, rotation, visible)

    # noinspection PyProtectedMember
    def _init_text(self, screen, text, x, y, color, font, size, align,
                   bold, italic, underline, strikethrough, rotation, visible):
        self._screen = screen
        self._location = Location(x, y)
        self._screen._add(self)

        self._text = text if text is not None else ''
        self._color = color
        self._font = font
        self._size = size
        self._align = align
        self._bold = bold
        self._italic = italic
        self._underline = underline
        self._strikethrough = strikethrough
        self._angle = rotation
        self._visible = visible

        verify(screen, Screen, text, str, x, (float, int), y, (float, int), color, Color, font, str, size, int,
               align, str, bold, bool, italic, bool, underline, bool, strikethrough, bool, rotation, (float, int),
               visible, bool)

        true_width, true_height = self._calculate_transform()
        self._width = true_width
        self._height = true_height * (self._text.count('\n') + 1)
        self._register_render()

    def _place(self) -> tuple:
        # Canvas anchor (x, y); the width offset keeps rotation pivoting about the center.
        hypotenuse = self._width / 2
        radians = math.radians(self._angle)
        dx = math.cos(radians) * hypotenuse
        dy = math.sin(radians) * hypotenuse

        return self.x() + self._width / 2 - 1 - dx, self.y() - dy

    def _render_node(self):
        return TextNode(
            self._render_id,
            self._place(),
            self._text,
            self._color.rgb(),
            self._font,
            self._size,
            self._align,
            self._bold,
            self._italic,
            self._underline,
            self._strikethrough,
            self._angle,
            self._visible,
        )

    def text(self, text: str = None) -> str:
        """
        Get or set the text. Use '\n' to separate lines

        :param text: text to set to (str), if any
        :return: the text
        """

        if text is not None:
            verify(text, str)
            if self._text == text:
                return self._text
            self._text = text
            self._update_coords()

        return self._text

    def move(self, *args, **kwargs) -> None:
        """
        Can take either a tuple, Location, or two numbers (dx, dy)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.move(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    def moveto(self, *args, **kwargs) -> None:
        """
        Move to a new location takes a Location, tuple, or two numbers (x, y)

        :return: None
        """

        before_x = self._location._x
        before_y = self._location._y
        self._location.moveto(*args, **kwargs)
        self._translate(self._location._x - before_x, self._location._y - before_y)

    def _translate(self, dx: float, dy: float) -> None:
        """
        Shift the text by (dx, dy) while retaining its geometry.
        """

        if dx == 0 and dy == 0:
            return

        self._invalidate_render()
        self._sync_pen()

    # noinspection PyMethodOverriding
    def width(self) -> float:
        """
        Get the width of the text (cannot be modified)

        :return the width of the text
        """

        return self._width

    # noinspection PyMethodOverriding
    def height(self) -> float:
        """
        Get the height of the text, (cannot be modified, although technically the font-size is the text's height)

        :return: the height of the text.
        """

        return self._height

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the text

        :param color: the color to set to, if any
        :return: the color of the text
        """

        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            self._invalidate_render()

        return self._color

    def font(self, font: str = None) -> str:
        """
        Get or set the font of the text

        :param font: the font to set to, if any
        :return: the font of the text
        """

        if font is not None:
            verify(font, str)
            self._font = font
            self._update_font()
            # self.update()

        return self._font

    def size(self, size: int = None) -> int:
        """
        Get or set the size of the text

        :param size: the size to set to, if any
        :return: the size of the text
        """

        if size is not None:
            verify(size, int)
            self._size = size
            self._update_font()
            # self.update()

        return self._size

    def align(self, align: str = None) -> str:
        """
        Get or set the alignment of the text, if a new value is passed it must be 'left', 'center', or 'right'.

        :param align: the alignment to set to, if any
        :return: the alignment of the text
        """

        if align is not None:
            verify(align, str)
            if align.lower() not in self._aligns:
                raise PydrawError(
                    f"Text#align(): expected 'left', 'center', or 'right'; received '{align}'."
                )

            self._align = align.lower()
            self._invalidate_render()

        return self._align

    def bold(self, bold: bool = None) -> bool:
        """
        Get or set the bold status of the text

        :param bold: the bold status to set to, if any
        :return: the bold status of the text
        """

        if bold is not None:
            verify(bold, bool)
            self._bold = bold
            self._update_font()
            # self.update()

        return self._bold

    def italic(self, italic: bool = None) -> bool:
        """
        Get or set the italic status of the text

        :param italic: the italic status to set to, if any
        :return: the italic status of the text
        """

        if italic is not None:
            verify(italic, bool)
            self._italic = italic
            self._update_font()
            # self.update()

        return self._italic

    def underline(self, underline: bool = None) -> bool:
        """
        Get or set the underline status of the text

        :param underline: the underline status to set to, if any
        :return: the underline status of the text
        """

        if underline is not None:
            verify(underline, bool)
            self._underline = underline
            self._update_font()
            # self.update()

        return self._underline

    def strikethrough(self, strikethrough: bool = None) -> bool:
        """
        Get or set the strikethrough status of the text

        :param strikethrough: the strikethrough status to set to, if any
        :return: the strikethrough status of the text
        """

        if strikethrough is not None:
            verify(strikethrough, bool)
            self._strikethrough = strikethrough
            self._update_font()
            # self.update()

        return self._strikethrough

    def rotation(self, rotation: float = None) -> float:
        """
        Get or set the rotation of the text

        :param rotation: the strikethrough to set to, if any
        :return: the rotation of the text
        """

        if rotation is not None:
            verify(rotation, (float, int))
            self._angle = rotation
            self._invalidate_render()

        return self._angle

    def rotate(self, angle_diff: float = 0) -> None:
        """
        Rotate the angle of the text by a difference, in degrees

        :param angle_diff: the angle difference to rotate by
        :return: Nonea
        """

        verify(angle_diff, (float, int))
        self.rotation(self._angle + angle_diff)

    def lookat(self, obj):
        if isinstance(obj, Object):
            obj = obj.location()
        elif type(obj) is not Location and type(obj) is not tuple:
            raise InvalidArgumentError(
                f'Text#lookat(): expected a Renderable or Location; received {type(obj)} ({obj!r}).'
            )

        location = Location(obj[0], obj[1])

        theta = math.atan2(location.y() - self.center().y(), location.x() - self.center().x()) - math.radians(self.rotation())
        theta = math.degrees(theta) + 90

        self.rotate(theta)

    def center(self, *args, **kwargs) -> Location:
        """
        Returns the location of the center

        :param move_to: if defined, Move the center to a new Location (Easily center objects!)
        :param x: if defined, move the center x-coordinate to the specified value
        :param y: if defined, move the center y-coordinate to the specified value
        :return: Location object representing center of Renderable
        """

        verify_keywords(kwargs, ('move_to', 'x', 'y'), 'Text#center()')

        if len(args) == 0 and len(kwargs) == 0:
            return self._center()

        location = Location(self._center())
        if len(args) != 0:
            if type(args[0]) is Location or type(args[0]) is tuple:
                location.moveto(args[0])
            elif type(args[0]) == float or type(args[0]) is int:
                if len(args) != 2:
                    raise InvalidArgumentError('Text#center(): expected both x and y.')
                elif type(args[1]) is not float and type(args[1]) is not int:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )

                location.moveto(args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Text#center(): expected a tuple/Location or two numbers (x, y).'
                )

        if len(kwargs) != 0:
            if 'move_to' in kwargs:
                if type(kwargs['move_to']) is Location or type(kwargs['move_to']) is tuple:
                    location.moveto(kwargs['move_to'])
                else:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )

            if 'x' in kwargs:
                if type(kwargs['x']) is float or type(kwargs['x']) is int:
                    location.x(kwargs['x'])
                else:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )
            if 'y' in kwargs:
                if type(kwargs['y']) is float or type(kwargs['y']) is int:
                    location.y(kwargs['y'])
                else:
                    raise InvalidArgumentError(
                        'Text#center(): expected a tuple/Location or two numbers (x, y).'
                    )

        return self._center(location)

    def _center(self, move_to: Location = None):
        if move_to is not None:
            verify(move_to, Location)
            self.moveto(move_to.x() - self.width() / 2, move_to.y() - self.height() / 2)

        return Location(self.x() + self.width() / 2, self.y() + self.height() / 2)

    def vertices(self) -> list:
        """
        Get the vertices of a Rectangle superposed in the same transform of the Text

        :return: a list of Locations
        """

        vertices = [Location(self.x(), self.y()), Location(self.x() + self.width(), self.y()),
                    Location(self.x() + self.width(), self.y() + self.height()),
                    Location(self.x(), self.y() + self.height())]
        if self._angle != 0:
            # First get some values that we're going to use later
            theta = math.radians(self._angle)
            cosine = math.cos(theta)
            sine = math.sin(theta)

            centroid_x = self.center().x()
            centroid_y = self.center().y()

            new_vertices = []
            for vertex in vertices:
                # We have to create these separately because they're ironically used in each other's calculations xD
                old_x = vertex.x() - centroid_x
                old_y = vertex.y() - centroid_y

                new_x = (old_x * cosine - old_y * sine) + centroid_x
                new_y = (old_x * sine + old_y * cosine) + centroid_y
                new_vertices.append(Location(new_x, new_y))
            vertices = new_vertices

        return vertices

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the text

        :param visible: the visibility to set to, if any
        :return: the visibility of the text
        """

        if visible is not None:
            verify(visible, bool)
            self._visible = visible
            self._invalidate_render()

        return self._visible

    def transform(self, transform: tuple = None) -> tuple:
        """
        Retrieve the transform of the text

        :param transform: Unsupported.
        :return: a tuple with representing: (width, height, angle)
        """

        if transform is not None:
            raise UnsupportedError('Text#transform(): setting transforms is unsupported.')

        return self.width(), self.height(), self.rotation()

    def clone(self):
        """
        Clone this text!

        :return: A cloned text object!
        """

        return Text(self._screen, self._text, self.x(), self.y(), color=self._color, font=self._font, size=self._size,
                    align=self._align, bold=self._bold, italic=self._italic,
                    underline=self._underline, strikethrough=self._strikethrough,
                    rotation=self._angle, visible=self._visible)

    def _update_font(self):
        self._update_coords()

    def _update_coords(self):
        # For Text this just refreshes width/height (position is handled elsewhere).
        self._check()

        true_width, true_height = self._calculate_transform()
        self._width = true_width
        self._height = true_height * (self._text.count('\n') + 1)
        self._invalidate_render()

    # noinspection PyProtectedMember
    def update(self) -> None:
        self._check()
        self._update_coords()

    def _calculate_transform(self):
        return self._screen._backend.measure_text(
            self._text,
            self._font,
            self._size,
            self._bold,
            self._italic,
        )

# == NON RENDERABLES == #


class Line(Object):
    _PEN_SUPPORTED = False

    def __init__(self, screen: Screen, *args, color: Color = Color('black'), thickness: int = 1, dashes=None,
                 visible: bool = True):
        super().__init__(screen)
        self._screen = screen

        if len(args) >= 4 and all(type(arg) is float or type(arg) is int for arg in args[0:4]):
            self._pos1 = Location(args[0], args[1])
            self._pos2 = Location(args[2], args[3])
            excess = args[4:]
        elif len(args) >= 2 and all(type(arg) is tuple or type(arg) is Location for arg in args[0:2]):
            self._pos1 = Location(args[0][0], args[0][1])
            self._pos2 = Location(args[1][0], args[1][1])
            excess = args[2:]
        else:
            raise InvalidArgumentError(
                'Line(): expected two tuples/Locations or four numbers (x1, y1, x2, y2).'
            )

        if len(excess) > 0:  # noqa
            count = 0
            for arg in excess:
                if count == 0:
                    verify(arg, Color)
                    color = arg
                elif count == 1:
                    verify(arg, int)
                    thickness = arg
                elif count == 2:
                    verify(arg, (int, tuple))
                    dashes = arg
                elif count == 3:
                    verify(arg, bool)
                    visible = arg
                count += 1

        self._color = color
        self._thickness = thickness
        self._dashes = dashes
        self._visible = visible

        verify(color, Color, thickness, int, dashes, (int, tuple), visible, bool)

        if dashes is not None and type(dashes) is not tuple:
            self._dashes = (dashes, dashes)

        self._update_angle()
        self._render_id = self._screen._register_render_source(self._render_node)
        self._ref = self._render_id

    def _render_node(self):
        dash = self._dashes
        if dash is not None and type(dash) is not tuple:
            dash = (dash, dash)
        return PolylineNode(
            self._render_id,
            (
                (self._pos1.x(), self._pos1.y()),
                (self._pos2.x(), self._pos2.y()),
            ),
            self._color.rgb(),
            self._thickness,
            dash,
            self._visible,
            'butt',
            False,
        )

    def _invalidate_render(self):
        self._screen._invalidate_render(self._render_id)

    def _restore_render(self):
        self._screen._register_render_source(self._render_node, self._render_id)

    def pos1(self, *args) -> Location:
        """
        Get or set the position of the first endpoint.

        :param args: Either a location or two numbers (x, y) may be passed here.
        :return: the position of the first endpoint.
        """

        if len(args) != 0:
            if len(args) == 1 and (type(args[0]) is Location or type(args[0]) is tuple):
                self._pos1 = Location(args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                self._pos1 = Location(args[0], args[1])
            else:
                raise TypeError('Incorrect Argumentation: Requires either a location, tuple, or two numbers.')

            self._update_angle()
            self._invalidate_render()
        return self._pos1

    def pos2(self, *args) -> Location:
        """
        Get or set the position of the second endpoint.

        :param args: Either a location or two numbers (x, y) may be passed here.
        :return: the position of the second endpoint.
        """

        if len(args) != 0:
            if len(args) == 1 and (type(args[0]) is Location or type(args[0]) is tuple):
                self._pos2 = Location(args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                self._pos2 = Location(args[0], args[1])
            else:
                raise TypeError('Incorrect Argumentation: Requires either a location, tuple, or two numbers.')

            self._update_angle()
            self._invalidate_render()
        return self._pos2

    def move(self, *args, **kwargs) -> None:
        """
        Move both endpoints by the same dx and dy

        Can take either a tuple, Location, or two numbers (dx, dy)

        :param dx: the distance x to move
        :param dy: the distance y to move
        :param point: affect only one of the endpoints options: (1, 2), default=0 (Must be 1 or 2)
        :return: None
        """

        diff = (0, 0)

        # Basically we don't have an empty tuple at the start.
        if len(args) > 0 and (type(args[0]) is float or type(args[0]) is int or type(args[0]) is Location or
                              type(args[0]) is tuple and not len(args[0]) == 0):
            if len(args) == 1 and (type(args[0]) is tuple or type(args[0]) is Location):
                diff = (args[0][0], args[0][1])
            elif len(args) == 2 and all(type(arg) is float or type(arg) is int for arg in args):
                diff = (args[0], args[1])
            else:
                raise InvalidArgumentError(
                    'Line#move(): expected a tuple/Location or two numbers (dx, dy).'
                )

        verify_keywords(kwargs, ('dx', 'dy', 'point'), 'Line#move()', case_sensitive=False)
        point = 0
        for (name, value) in kwargs.items():
            if type(value) is not int and type(value) is not float:
                raise InvalidArgumentError(
                    'Line#move(): expected a tuple/Location or two numbers (dx, dy).'
                )

            name = name.lower()
            if name == 'dx':
                diff = (value, diff[1])
            elif name == 'dy':
                diff = (diff[0], value)
            elif name == 'point':
                point = value

        verify(point, int)
        if point == 1:
            self._pos1.move(diff[0], diff[1])
        elif point == 2:
            self._pos2.move(diff[0], diff[1])
        elif point == 0:
            self._pos1.move(diff[0], diff[1])
            self._pos2.move(diff[0], diff[1])
        else:
            raise InvalidArgumentError('Line#move(): point must be 0, 1, or 2.')

        if point != 0:
            self._update_angle()

        self._invalidate_render()

    def moveto(self, *args, **kwargs) -> None:
        """
        Move both of the endpoints to new locations.

        :param args: Either two locations, tuples, or four numbers (x1, y1, x2, y2).
        :return: None
        """

        verify_keywords(
            kwargs,
            ('pos1', 'pos2', 'x1', 'y1', 'x2', 'y2'),
            'Line#moveto()',
            case_sensitive=False
        )
        if len(args) == 2 and all(type(arg) is tuple or type(arg) is Location for arg in args):
            self._pos1.moveto(args[0][0], args[0][1])
            self._pos2.moveto(args[1][0], args[1][1])
        elif len(args) == 4 and all(type(arg) is int or type(arg) is float for arg in args):
            self._pos1.moveto(args[0], args[1])
            self._pos2.moveto(args[2], args[3])
        elif len(kwargs) == 0:
            raise TypeError('Incorrect Argumentation: Requires either two locations, tuples, or four numbers (x1, y1, '
                            'x2, y2)')

        if len(kwargs.keys()) > 0:
            for key, value in kwargs.items():
                key = key.lower()
                if key == 'pos1':
                    if type(value) is not tuple and type(value) is not Location:
                        raise InvalidArgumentError(
                            'Line#moveto(): pos1 must be a tuple or Location.'
                        )
                    pos1 = value
                    verify(pos1[0], (float, int), pos1[1], (float, int))
                    self._pos1 = Location(pos1[0], pos1[1])
                elif key == 'pos2':
                    if type(value) is not tuple and type(value) is not Location:
                        raise InvalidArgumentError(
                            'Line#moveto(): pos2 must be a tuple or Location.'
                        )
                    pos2 = value
                    verify(pos2[0], (float, int), pos2[1], (float, int))
                    self._pos2 = Location(pos2[0], pos2[1])
                elif type(value) is not float and type(value) is not int:
                    raise InvalidArgumentError(
                        f'Line#moveto(): {key} must be a number.'
                    )
                elif key == 'x1':
                    self._pos1.x(value)
                elif key == 'y1':
                    self._pos1.y(value)
                elif key == 'x2':
                    self._pos2.x(value)
                elif key == 'y2':
                    self._pos2.y(value)
        elif len(args) == 0:
            raise TypeError('Incorrect Argumentation: Requires either two locations, tuples, or four numbers (x1, y1, '
                            'x2, y2)')

        self._update_angle()
        self._invalidate_render()

    # noinspection PyUnusedLocal
    # TODO: Allow for point specification (center)
    def lookat(self, *args, **kwargs) -> None:
        """
        Make the line look at the given point by moving the second point.

        :return: None
        """

        verify_keywords(kwargs, ('point',), 'Line#lookat()', case_sensitive=False)
        point = 2

        if len(args) >= 1 and (type(args[0]) is tuple or type(args[0]) is Location):
            location = Location(args[0][0], args[0][1])

            if len(args) > 1 and type(args[1]) is int:
                point = args[1]
        elif len(args) >= 2 and all(type(arg) is float or type(arg) is int for arg in args[:2]):
            location = Location(args[0], args[1])

            if len(args) > 2 and type(args[2]) is int:
                point = args[2]
        else:
            raise InvalidArgumentError(
                'Line#lookat(): expected a tuple/Location or two numbers (x, y).'
            )

        for name, value in kwargs.items():
            if type(value) is not int:
                raise InvalidArgumentError('Line#lookat(): point must be an int.')

            if name.lower() == 'point':
                point = value

        # so now we have a location, but we need to shorten it to be the same length of our line right now.
        # slope = (self.pos2().y() - self.pos1().y()) / (self.pos2.x() - self.pos1.x())
        length = self.length()

        if point == 2:
            ray_length = self._length(self.pos1().x(), location.x(), self.pos1().y(), location.y())

            # hypotenuse = (ray_length - length)  # extraneous length (we need to cut this)

            theta = math.atan2(self.pos1().y() - location.y(), self.pos1().x() - location.x()) \
                    - math.atan2(self.pos1().y() - self.pos2().y(), self.pos1().x() - self.pos2().x())
        elif point == 1:
            ray_length = self._length(self.pos2().x(), location.x(), self.pos2().y(), location.y())

            # hypotenuse = (ray_length - length)  # extraneous length (we need to cut this)

            theta = math.atan2(self.pos2().y() - location.y(), self.pos2().x() - location.x()) \
                    - math.atan2(self.pos2().y() - self.pos1().y(), self.pos2().x() - self.pos1().x())
        else:
            raise InvalidArgumentError('Line#lookat(): point must be 1 or 2.')

        self.rotate(math.degrees(theta))

    def rotation(self, angle: float = None):
        """
        Get or set the rotation of the line (works via pos2()).

        :param angle: the angle in degrees to rotate by, if any
        :return: the angle of the line
        """

        if angle is not None:
            self.rotate(angle - self._angle)

        return self._angle

    def rotate(self, angle_diff: float, point: int = 1) -> float:
        """
        Rotate the line around one of its vertices (1 by default)

        :param angle_diff: the angle to rotate by
        :param point: the point to serve as the origin.
        :return: the new angle
        """

        if point not in (1, 2):
            raise InvalidArgumentError('Line#rotate(): point must be 1 or 2.')

        origin = self._pos1 if point == 1 else self._pos2
        point = self._pos2 if point == 1 else self._pos1

        theta = math.radians(angle_diff)

        cosine = math.cos(theta)
        sine = math.sin(theta)

        old_x = point.x() - origin.x()
        old_y = point.y() - origin.y()

        new_x = (old_x * cosine - old_y * sine) + origin.x()
        new_y = (old_x * sine + old_y * cosine) + origin.y()

        point.moveto(new_x, new_y)
        self._invalidate_render()

        self._angle += angle_diff
        return self._angle

    def _update_angle(self) -> float:
        """Recalculate the angle from the current endpoint locations."""

        theta = math.atan2(
            self._pos1.y() - self._pos2.y(),
            self._pos1.x() - self._pos2.x(),
        )
        self._angle = math.degrees(theta)
        return self._angle

    def location(self) -> tuple:
        """
        Returns the locations of both the endpoints

        :return: the locations of both the endpoints
        """

        return self._pos1, self._pos2

    def length(self) -> float:
        """
        Get the length of the line

        :return: the length of the line
        """

        return self._length(self.pos1().x(), self.pos2().x(), self.pos1().y(), self.pos2().y())

    @staticmethod
    def _length(x1: float, x2: float, y1: float, y2: float) -> float:
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def color(self, color: Color = None) -> Color:
        """
        Get or set the color of the line

        :param color: the color to set to, if any
        :return: the color of the line
        """

        if color is not None:
            verify(color, Color)

            if self._color == color:
                return self._color

            self._color = color
            self._invalidate_render()

        return self._color

    def thickness(self, thickness: int = None) -> int:
        """
        Get or set the thickness of the line

        :param thickness: the thickness to set to, if any
        :return: the thickness of the line
        """

        if thickness is not None:
            verify(thickness, int)
            self._thickness = thickness
            self._invalidate_render()

        return self._thickness

    def dashes(self, dashes: Union[int, tuple] = None) -> Union[int, tuple]:
        """
        Retrieve or enable/disable the dashes for the line

        On systems which support only a limited set of dash patterns, the dash pattern will be displayed as the closest
        dash pattern that is available. For example, on Windows only a few dash patterns are available, most of which
        do not allow for special dash-spacing (if passing in a tuple).

        :param dashes: the visibility to set to, if any
        :return: the toggle-state of dashes
        """

        if dashes is not None:
            verify(dashes, (int, tuple))

            if type(dashes) == tuple:
                for dash in dashes:
                    verify(dash, int)

            self._dashes = dashes
            self._invalidate_render()

        return self._dashes

    def visible(self, visible: bool = None) -> bool:
        """
        Get or set the visibility of the line

        :param visible: the visibility to set to, if any
        :return: the visibility of the line
        """

        if visible is not None:
            verify(visible, bool)
            self._visible = visible
            self._invalidate_render()

        return self._visible

    def transform(self, transform: tuple = None):
        """
        Copy the line's length and angle!

        :param transform:
        :return:
        """

        if transform is not None:
            raise UnsupportedError('Line#transform(): setting transforms is unsupported.')

        return self.length(), self.rotation()

    def clone(self):
        """
        Clone a new line!

        :return: A clone of this line
        """

        return Line(self._screen, self._pos1, self._pos2, color=self._color, thickness=self._thickness,
                    dashes=self._dashes, visible=self._visible)

    def intersects(self, obj) -> bool:
        """
        Check if a line intersects with another line or Renderable

        :param obj: Line, Renderable, or List/Tuple
        :return: Whether the line intersects with the object
        """

        shape1 = (self.pos1(), self.pos2())

        if type(obj) == Line:
            shape2 = (obj.pos1(), obj.pos2())
        elif isinstance(obj, Renderable):
            shape2 = obj.vertices()
        elif type(obj) == list or type(obj) == tuple:
            shape2 = obj
        else:
            raise InvalidArgumentError(
                f'Line#intersects(): expected a Line, Renderable, list, or tuple; '
                f'received {type(obj)} ({obj!r}).'
            )

        if len(shape2) < 2:
            raise InvalidArgumentError(
                'Line#intersects(): expected at least two vertices.'
            )

        # Orientation method that will determine if it is a triangle (and in what direction [cc or ccw]) or a line.
        def orientation(point1: Location, point2: Location, point3: Location) -> str:
            """
            Internal method that will determine the orientation of three points. They can be a clockwise triangle,
            counterclockwise triangle, or a co-linear line segment.

            :param point1: the first point of the main line segment
            :param point2: the second point of the main line segment
            :param point3: the third point to check from another line segment
            :return: the orientation of the passed points
            """
            result = (float(point2.y() - point1.y()) * (point3.x() - point2.x())) - \
                     (float(point2.x() - point1.x()) * (point3.y() - point2.y()))

            if result > 0:
                return 'clockwise'
            elif result < 0:
                return 'counter-clockwise'
            else:
                return 'co-linear'

        def point_on_segment(point1: Location, point2: Location, point3: Location) -> bool:
            """
            Returns if point3 lies on the segment formed by point1 and point2.
            """

            return max(point1.x(), point3.x()) >= point2.x() >= min(point1.x(), point3.x()) \
                   and max(point1.y(), point3.y()) >= point2.y() >= min(point1.y(), point3.y())

        # Okay to begin actually detecting orientations, we want to loop through some edges. But only ones that are
        # relevant. In order to do this we will first have to turn the list of vertices into a list of edges.
        # Then we will look through the lists of edges and find the ones closest to each other.

        shape1_edges = []
        shape2_edges = []

        shape1 = tuple(shape1[:]) + (shape1[0],)
        shape2 = tuple(shape2[:]) + (shape2[0],)

        shape1_point1 = shape1[0]
        for i in range(1, len(shape1)):
            shape1_point2 = shape1[i % len(shape1)]  # 1, 2, 3, 3 % 5
            shape1_edges.append((shape1_point1, shape1_point2))
            shape1_point1 = shape1_point2

        shape2_point1 = shape2[0]
        for i in range(1, len(shape2)):
            shape2_point2 = shape2[i % len(shape2)]
            shape2_edges.append((shape2_point1, shape2_point2))
            shape2_point1 = shape2_point2

        # Now we are going to test the four orientations that the segments form
        for edge1 in shape1_edges:
            for edge2 in shape2_edges:
                orientation1 = orientation(edge1[0], edge1[1], edge2[0])
                orientation2 = orientation(edge1[0], edge1[1], edge2[1])
                orientation3 = orientation(edge2[0], edge2[1], edge1[0])
                orientation4 = orientation(edge2[0], edge2[1], edge1[1])

                # If orientations 1 and 2 are strictly opposite (both non-co-linear) as well as 3 and 4,
                # then the segments cross. A plain != would treat a co-linear result as a crossing and
                # mis-fire on floating-point-collinear edges that don't actually touch.
                if orientation1 != orientation2 and orientation1 != 'co-linear' and orientation2 != 'co-linear' \
                        and orientation3 != orientation4 and orientation3 != 'co-linear' and orientation4 != 'co-linear':
                    return True

                # There's some special cases we should check where a point from one segment is on the other segment
                if orientation1 == 'co-linear' and point_on_segment(edge1[0], edge2[0], edge1[1]):
                    return True

                if orientation2 == 'co-linear' and point_on_segment(edge1[0], edge2[1], edge1[1]):
                    return True

                if orientation3 == 'co-linear' and point_on_segment(edge2[0], edge1[0], edge2[1]):
                    return True

                if orientation4 == 'co-linear' and point_on_segment(edge2[0], edge1[1], edge2[1]):
                    return True

        # If none of the above conditions were ever met we just return False. Hopefully we are correct xD.
        return False

    # noinspection PyProtectedMember
    def update(self):
        self._check()
        self._invalidate_render()

