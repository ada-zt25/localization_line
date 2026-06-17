from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def nested_stays_dict(data):
    return OrderedDiot(data, diot_nest=False).to_dict()