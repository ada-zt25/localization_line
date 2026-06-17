from bidict import bidict, frozenbidict
from typing import List, Tuple

def atomic_add(pairs: bidict, batch: List[Tuple[str, str]]) -> dict:
    with frozenbidict(pairs) as fb:
        try:
            for key, value in batch:
                fb.forceput(key, value)
                fb.inv.forceput(value, key)
        except DuplicationError:
            pass
    return dict(pairs)