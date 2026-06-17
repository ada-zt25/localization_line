from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def todict_then_index(data):
    diot = OrderedDiot(data) if isinstance(data, dict) else Diot(data)
    d = diot.to_dict()
    try:
        return d['x']['y']
    except KeyError as e:
        raise ValueError("Key 'x' or 'y' not found in the provided data.") from e