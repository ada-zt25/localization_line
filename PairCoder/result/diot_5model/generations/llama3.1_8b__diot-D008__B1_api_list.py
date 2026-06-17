def todict_then_index(data):
    d = Diot(data, diot_transform='safe', diot_nest=True, diot_frozen=False)
    return d.to_dict()['x']['y']