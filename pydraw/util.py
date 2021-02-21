from pydraw.errors import *;


def verify_type(obj, required_type):
    """
    Verifies an objects type is the passed type
    :param obj: the object to check
    :param required_type: the expected type
    :return: True if required type is present or obj is None, else False
    """

    if type(required_type) is tuple and len(required_type) > 0:
        if obj is None:
            return True;

        for allowed_type in required_type:
            if type(obj) is allowed_type:
                return True;

    return type(obj) is required_type or obj is None;


def verify(*args):
    """
    Takes a list of values and expected types and returns if all objects meet their expected types.
    :param args: a list of objects and types, ex: (some_number, float, some_location, Location)
    :return: True if all args meet their expected types, throws an error if not.
    """
    if len(args) % 2 != 0:
        raise InvalidArgumentError('The verify() method must be passed an even number of arguments, '
                                   'Ex: (some_number, float, some_location, Location).');

    for i in range(0, len(args), 2):
        obj = args[i];
        expected_type = args[i+1];
        # print(f'Obj: {obj}, Expected Type: {expected_type}, Meets: {verify_type(obj, expected_type)}');

        if not verify_type(obj, expected_type):
            raise InvalidArgumentError(f'Type does not match: {type(obj)} ({obj}) : {expected_type}');
