from bidict import bidict, frozenbidict, OrderedBidict
from typing import Dict

def key_for(pairs: Dict, val):
    b = OrderedBidict()
    b.putall(pairs)
    b_inv = b.inv
    try:
        return next(b_inv[val])
    except StopIteration:
        raise KeyError(f"{val} not found in {list(pairs)}")