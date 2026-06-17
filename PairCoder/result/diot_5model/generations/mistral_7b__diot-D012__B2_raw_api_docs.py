from diot import Diot, FrozenDiot, OrderedDiot
from typing import Any, Union

def thaw_is_temporary(data: Union[Diot, FrozenDiot], key: str, val: Any) -> FrozenDiot:
    with data.thaw() as d:
        d[key] = val
    return data.freeze()