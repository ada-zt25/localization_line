from diot import Diot, OrderedDiot, FrozenDiot

def set_then_get(key, val):
    diot = OrderedDiot()
    diot[key] = val
    return diot[key]