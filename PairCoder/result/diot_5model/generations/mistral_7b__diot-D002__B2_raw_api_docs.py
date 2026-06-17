from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_snake(data):
    d = OrderedDiot(diot_transform='safe')
    for key, value in data.items():
        if isinstance(value, dict):
            d[key] = access_snake(value)
        else:
            d[snake_case(key)] = value
    return d.get('foo_bar', None)