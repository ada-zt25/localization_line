from diot import Diot, FrozenDiot, diot_transform, diot_nest

def nested_mutate_reflects(data, val):
    d = Diot(data, diot_transform='safe', diot_nest=True)
    result = d.get('x').get('y')
    with d.thaw() as t:
        t['x']['y'] = val
    return d.to_dict()['x']['y']