from diot import Diot, FrozenDiot, OrderedDiot
from typing import Dict, Any

def to_plain_dict(data: Dict[str, Any]):
    d = OrderedDiot(data)
    d.diot_nest = False
    d.diot_transform = 'safe'
    return d.to_dict()