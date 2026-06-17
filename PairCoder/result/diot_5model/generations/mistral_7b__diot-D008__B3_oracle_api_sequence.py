from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def todict_then_index(data):
    try:
        d = OrderedDiot(data)
        frozen_d = FrozenDiot(d)
        return frozen_d['x']['y']
    except DiotFrozenError:
        pass