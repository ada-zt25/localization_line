from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def todict_then_index(data):
    diot = OrderedDiot(data) if isinstance(data, dict) else diot
    try:
        with diot.thaw():
            return diot.to_dict()['x']['y']
    except DiotFrozenError:
        raise ValueError("Input data is frozen and cannot be modified.")