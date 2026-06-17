def todict_then_index(data):
    d = Diot(data, diot_transform='safe', diot_nest=True, diot_frozen=False)
    d_dict = d.to_dict()
    return d_dict['x']['y']