from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def to_plain_dict(data):
    if isinstance(data, (Diot, OrderedDiot, FrozenDiot)):
        with data.thaw() as d:
            return d.to_dict()
    return data