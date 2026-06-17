from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_camel(data):
    d = OrderedDiot(diot_transform='camelCase', diot_nest=True).from_dict(data)
    return d.get('fooBar') if isinstance(d, FrozenDiot) else d.fooBar