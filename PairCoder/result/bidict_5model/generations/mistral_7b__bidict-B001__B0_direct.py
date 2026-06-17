from bidict import bidict, frozenbidict
from typing import Dict

def key_for(pairs: Dict[str, str], val: str) -> str:
    b = bidict(pairs)
    try:
        return b.inv[val]
    except KeyError:
        raise ValueError(f"Value {val} not found in the given pairs.") from None