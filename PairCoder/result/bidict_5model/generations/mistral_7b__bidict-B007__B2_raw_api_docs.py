from bidict import bidict, frozenbidict, OrderedBidict
from typing import Union

def roundtrip(pairs: bidict, key: Union[str, int]) -> Union[str, int]:
    b = pairs.copy()
    b.putall({key: None})
    value = b[key]
    return b.inv[value]