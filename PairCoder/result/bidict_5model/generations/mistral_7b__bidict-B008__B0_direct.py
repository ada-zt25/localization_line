from typing import List, Tuple
import bidict

def atomic_add(A: bidict.BidirectionalMap, batch: List[Tuple[str, str]]) -> dict:
    frozen = frozenbidict(A)
    new_dict = {}
    for key, value in batch:
        if not frozen[key] or frozen[value] is None:
            new_value = frozen[key] if frozen[key] else value
            new_dict[key] = new_value
            if new_value:
                frozen[new_value] = key
    if frozen != A:
        raise DuplicationError("Duplicate keys or values in batch")
    return dict(new_dict)