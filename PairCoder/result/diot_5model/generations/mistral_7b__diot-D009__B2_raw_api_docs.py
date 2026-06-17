from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def set_then_get(key, val):
    diot = OrderedDiot()
    diot[key] = val
    return diot.get(key)