from diot import Diot, OrderedDiot, FrozenDiot

def nested_chain(data):
    d = Diot(data, diot_nest=True)
    if isinstance(d, FrozenDiot):
        with d.thaw():
            return d.get(*list(reversed(d.keys()))[1:])
    else:
        return d.get(*list(reversed(d.keys()))[1:])