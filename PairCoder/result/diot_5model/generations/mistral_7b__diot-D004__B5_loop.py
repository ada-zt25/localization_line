from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def to_plain_dict(data):
    if isinstance(data, Diot):
        with data.thaw() as d:
            return d.to_dict()
    elif isinstance(data, (list, tuple)):
        return [to_plain_dict(item) for item in data]
    elif isinstance(data, dict):
        return {k: to_plain_dict(v) for k, v in data.items()}
    else:
        return data