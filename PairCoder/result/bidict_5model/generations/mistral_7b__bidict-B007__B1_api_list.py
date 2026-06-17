from bidict import bidict, frozenbidict, OrderedBidict
from typing import Iterable

def roundtrip(pairs: Iterable[tuple], key):
    b = bidict()
    for k, v in pairs:
        b.forceput(k, v)
    try:
        value = b[key]
    except KeyDuplicationError:
        pass
    else:
        inverse_b = b.inv
        key_from_value = inverse_b[value]
        return frozenbidict({key: value, key_from_value: value})
    raise KeyDuplicationError(f"No entry for key '{key}'")