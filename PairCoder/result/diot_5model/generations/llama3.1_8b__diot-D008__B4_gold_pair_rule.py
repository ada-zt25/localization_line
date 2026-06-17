def todict_then_index(data):
    d = Diot(data, diot_transform='safe', diot_nest=True)
    return d.to_dict()['x']['y']