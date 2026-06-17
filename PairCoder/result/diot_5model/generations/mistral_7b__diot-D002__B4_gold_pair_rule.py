from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_snake(data):
    return Diot(OrderedDiot(frozenset([('fooBar', data['fooBar'])])), diot_transform='snake_case').foo_bar