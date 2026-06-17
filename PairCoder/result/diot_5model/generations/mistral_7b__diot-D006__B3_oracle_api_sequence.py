from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def nested_is_diot(data):
    d = Diot(data)
    return d.x