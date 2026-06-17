from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def nested_chain(data):
    d = Diot(data)
    return d.ordered().get('x').get('y')