from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_snake(data):
    d = OrderedDiot(data)
    try:
        return d.get('foo_bar')
    except DiotFrozenError:
        return FrozenDiot({'foo_bar': d['fooBar']})['foo_bar']