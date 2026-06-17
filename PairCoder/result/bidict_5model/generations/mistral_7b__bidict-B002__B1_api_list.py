from collections.abc import Mapping
import sys

def invert(pairs):
    if not isinstance(pairs, Mapping):
        raise TypeError("'{}' object is not a mapping".format(type(pairs).__name__))

    bidict_obj = OrderedBidict()
    for key, value in pairs.items():
        try:
            bidict_obj.putall({value: key})
        except DuplicationError as e:
            if str(e) not in sys.stderr.getbuffer().getvalue():
                print(str(e), file=sys.stderr)

    return dict(bidict_obj.inv)