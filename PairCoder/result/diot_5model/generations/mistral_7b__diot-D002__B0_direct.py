from diot import Diot, OrderedDiot, FrozenDiot

def access_snake(data):
    od = OrderedDiot()
    for key, value in data.items():
        camel_key = '_'.join(c.capitalize() for c in key.replace('_', '').split())
        od[camel_key] = value
    return od['foo_bar']