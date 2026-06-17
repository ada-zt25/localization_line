from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def nested_stays_dict(data):
    return Diot(OrderedDiot(data), frozen=False).get('x')