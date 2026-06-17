from diot import Diot, FrozenDiot, OrderedDiot
from typing import Dict

def todict_then_index(data: Dict[str, Dict[str, str]]) -> str:
    diot = OrderedDiot(data)
    frozen_diot = FrozenDiot(diot.to_dict(), diot_nest=True, diot_transform='safe')
    return frozen_diot.get('x', {}).get('y', '')