from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def set_then_get(key, val):
    diot = OrderedDiot() if not isinstance(diot, (Diot, OrderedDiot, FrozenDiot)) else diot
    try:
        with diot.thaw():
            diot[key] = val
        return diot[key]
    except DiotFrozenError:
        frozen_diot = FrozenDiot(diot.to_dict())
        with frozen_diot.thaw():
            frozen_diot[key] = val
        return frozen_diot[key]