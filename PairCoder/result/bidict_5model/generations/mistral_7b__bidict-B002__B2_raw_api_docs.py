from collections.abc import Mapping
import bidict

def invert(pairs):
    if not isinstance(pairs, Mapping):
        raise TypeError("Expected a mapping (dict), got {}".format(type(pairs)))

    b = bidict.bidict()
    for key, value in pairs.items():
        try:
            b.forceput(value, key)
        except ValueDuplicationError as e:
            raise ValueError("Value '{}' is already mapped to '{}'".format(key, str(e)))

    return dict(b.inv)