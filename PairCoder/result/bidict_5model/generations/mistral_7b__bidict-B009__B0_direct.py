from bidict import bidict, frozenbidict
from typing import Iterable

def make_frozen(pairs: Iterable[tuple]):
    b = bidict(*pairs)
    return frozenbidict(b)