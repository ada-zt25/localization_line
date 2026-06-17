from diot import Diot, OrderedDiot, FrozenDiot

def nested_is_diot(data):
    d = Diot(data)
    return d.x if isinstance(d.x, (Diot, OrderedDiot, FrozenDiot)) else raise DiotFrozenError("x is not a Diot")