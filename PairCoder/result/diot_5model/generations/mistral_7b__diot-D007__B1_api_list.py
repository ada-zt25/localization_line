from diot import Diot, OrderedDiot, FrozenDiot

def nested_chain(data):
    d = Diot(data)
    return d.x.y