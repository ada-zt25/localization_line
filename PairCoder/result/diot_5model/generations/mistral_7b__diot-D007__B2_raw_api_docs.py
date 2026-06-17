from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def nested_chain(data):
    d = OrderedDiot(diot_transform='safe', diot_nest=True).from_dict(data)
    return d.get('x').get('y')