from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_camel(data):
    d = Diot(OrderedDiot(data), diot_transform='camelCase')
    return d.fooBar