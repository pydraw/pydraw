from pydraw.errors import *


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
    Validate a list of values against expected types.

    :param args: a list of objects and types, ex: (some_number, float, some_location, Location)
    :return: None when every object meets its expected type.
    :raises InvalidArgumentError: if the arguments are not object/type pairs or
        an object does not meet its expected type.
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
