from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def nested_is_diot(data):
    d = Diot(data, diot_nest=True)
    with d.thaw() as td:
        return td['x']