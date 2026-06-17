from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def todict_then_index(data):
    diot = OrderedDiot(data)
    try:
        frozen_diot = FrozenDiot(diot.to_dict())
    except DiotFrozenError:
        with frozen_diot.thaw():
            frozen_diot['x']['y']
    else:
        frozen_diot['x']['y']